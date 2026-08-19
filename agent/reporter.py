"""Tells the orchestrator this node exists and is still alive.

This is M1 item 4. It runs on its own thread, owns no UI, and imports nothing
from agent.ui -- deliberately, so it can be imported and tested in CI, which
has no pystray, pywebview or Pillow installed.

Design notes that are easy to get wrong and expensive to get wrong:

*It never gives up.* The loop retries forever with backoff. The obvious
alternative -- return on an unrecoverable-looking error -- is the shape of an
existing defect in this app (docs/PROVIDER-APP.md §8.1), where a supervisor
thread exits permanently and the only symptom is that nothing ever happens
again. A provider whose router rebooted must come back on their own.

*A 404 is a re-registration, not a failure.* If the orchestrator has no row for
this node -- restored backup, wiped development database -- heartbeating into
it would succeed forever while the fleet appeared empty. Treating 404 as "go
register again" makes that self-healing.

*A 401 is a re-registration too, but a destructive one.* The heartbeat carries
the node credential, so the orchestrator can tell this node from anyone who
learned its id. When the credential is refused, the local copy is deleted
before re-registering: keeping it would make every subsequent heartbeat fail
identically, forever, with the fix sitting unused on disk.

*Every request has an explicit timeout, and it is larger than the server's.*
The orchestrator's database connect timeout is 5 seconds, so a slow-but-honest
response can legitimately take longer than that. A client timeout below the
server's worst honest response turns healthy-but-slow into an error and, with
retries, into load amplification at exactly the wrong moment.
"""

from __future__ import annotations

import os
import threading

import httpx

from agent import __version__, identity
from agent.runtime import blender
from agent.state import Link, ProviderState
from agent.telemetry import Telemetry, snapshot

DEFAULT_ORCHESTRATOR = "http://localhost:8080"

# Comfortably above the orchestrator's 5s database connect timeout plus query
# time. See the module docstring.
REQUEST_TIMEOUT_S = 15.0

DEFAULT_INTERVAL_S = 15.0

# Backoff ceiling. Long enough that a node with nowhere to report is not
# hammering a dead endpoint; short enough that recovery is measured in minutes,
# not hours, so a provider does not have to restart the app after an outage.
MAX_BACKOFF_S = 120.0


def orchestrator_url() -> str:
    """Base URL, without a trailing slash.

    The slash matters: `f"{url}/providers/heartbeat"` against a URL that
    already ends in one produces a double slash, which some proxies 404 and
    others silently redirect. Neither failure points at its cause.
    """
    return (os.getenv("ORCHESTRATOR_URL") or DEFAULT_ORCHESTRATOR).rstrip("/")


def capability_payload(telemetry: Telemetry) -> dict:
    """The hardware half of the contract. See orchestrator/models.py."""
    host = telemetry.host
    gpu = telemetry.gpu
    return {
        "hostname": host.hostname,
        "os_version": host.os_version,
        "cpu": host.cpu,
        "logical_cores": host.logical_cores,
        "ram_total_mb": host.ram_total_mb,
        "gpu_name": gpu.name if gpu else None,
        "vram_total_mb": gpu.vram_total_mb if gpu else None,
        "gpu_driver": gpu.driver if gpu else None,
        "agent_version": __version__,
    }


def metrics_payload(telemetry: Telemetry) -> dict:
    """The live half of the contract.

    `local_models` excludes Ollama Cloud entries. Those are pointers to
    ollama.com that appear in /api/tags looking exactly like local weights, and
    a node that advertised `deepseek-v3.1:671b-cloud` would be claiming
    capacity no consumer GPU has.

    Caveat worth carrying forward: model residency is a hand-built area under
    ADR 0002, and this filter is not the residency logic. It answers "what is
    on this disk", not "what can this node actually serve right now", which
    additionally depends on VRAM, what is already loaded, and cold-start cost.
    For M1 this list is display-only -- nothing schedules against it. It must
    not become a scheduling input without Rushab writing the real thing.
    """
    gpu = telemetry.gpu
    ollama = telemetry.ollama
    return {
        "gpu_utilisation_pct": gpu.utilisation_pct if gpu else None,
        "vram_used_mb": gpu.vram_used_mb if gpu else None,
        "temperature_c": gpu.temperature_c if gpu else None,
        "ollama_reachable": ollama.reachable,
        "ollama_version": ollama.version,
        "local_models": [m.name for m in ollama.available if not m.remote][:200],
        # A capability, not a permission. Saying "this machine has Blender 4.3.2"
        # does not make it eligible to render: that is provider_nodes
        # .render_eligible, which defaults FALSE and is only ever set by an
        # operator. Rendering a stranger's .blend means executing code we did
        # not write on hardware we do not own, and the sandbox that would
        # contain it is still an unwritten hand-built task -- so the decision
        # belongs to the machine's owner, not to its software's self-report.
        "blender_version": blender.installed_version(),
    }


class Reporter:
    """Registers this node, then heartbeats until asked to stop."""

    def __init__(self, state: ProviderState, base_url: str | None = None) -> None:
        self.state = state
        self.base_url = (base_url or orchestrator_url()).rstrip("/")
        self.node_id = identity.node_id()
        self.interval_s = DEFAULT_INTERVAL_S
        self.registered = False
        # Set once the first request of any kind has been answered, so the
        # log can distinguish "never reached the orchestrator" from "reached
        # it and then lost it". Those need different debugging.
        self.ever_connected = False
        # Publish the address before the first request rather than after it.
        # Until this line existed, the only record of where a node reported was
        # a print() into a console that the packaged build does not create
        # (`console=False` in packaging/GPUProvider.spec), so a provider had no
        # way to discover they were heartbeating into the localhost default.
        self.state.set_link(
            Link.CONNECTING, self.base_url, "contacting the orchestrator"
        )

    def _post(
        self,
        client: httpx.Client,
        path: str,
        payload: dict,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        return client.post(
            f"{self.base_url}{path}",
            json=payload,
            headers=headers,
            timeout=REQUEST_TIMEOUT_S,
        )

    def _auth_header(self) -> dict[str, str] | None:
        """Bearer credential for authenticated node endpoints, or None.

        Read from disk on each use, for the same reason `agent/worker.py` does:
        registration rewrites the token file, and a copy cached in memory at
        construction would be stale from the moment the node re-registers.
        """
        token = identity.node_token()
        return {"Authorization": f"Bearer {token}"} if token else None

    def _online(self, detail: str) -> None:
        self.state.set_link(Link.ONLINE, self.base_url, detail)

    def record_failure(self, detail: str) -> None:
        """Publish a failed exchange, preserving why it failed.

        `ever_connected` is what separates the two cases, and the separation is
        the useful part: a node that has never got through is almost always
        pointed at the wrong address, while one that connected and stopped has
        a network problem or is waiting out an outage. The provider does
        different things about each.
        """
        self.state.set_link(
            Link.OFFLINE if self.ever_connected else Link.CONNECTING,
            self.base_url,
            detail,
        )

    def register(self, client: httpx.Client, telemetry: Telemetry) -> bool:
        response = self._post(
            client,
            "/providers/register",
            {
                "node_id": self.node_id,
                "capability": capability_payload(telemetry),
            },
        )
        self.ever_connected = True
        if response.status_code == 422:
            # The agent and orchestrator disagree about the contract. Retrying
            # cannot fix it and the body names the offending field, so say so
            # loudly rather than looping silently on a permanent error.
            print(f"[reporter] registration rejected as invalid: {response.text}")
            # Reachable but refusing us, which leaves the node absent from the
            # marketplace just as surely as an outage would. Reported as a
            # failure so the dashboard does not show a healthy link for a node
            # that will never appear in the registry.
            self.record_failure("the orchestrator rejected this node's details")
            return False
        response.raise_for_status()
        body = response.json()
        self.interval_s = float(body.get("heartbeat_interval_s") or DEFAULT_INTERVAL_S)

        # The credential is returned exactly once, here. Persisting it is what
        # lets agent/worker.py claim jobs; without it the node registers,
        # heartbeats, and is visible on the marketplace but can never be given
        # work. An orchestrator too old to issue one sends nothing, and the
        # worker degrades to idling rather than erroring.
        token = body.get("node_token")
        if token:
            if not identity.store_node_token(token):
                print(
                    "[reporter] could not save the node credential; "
                    "this machine will not be offered work"
                )
        self.registered = True
        self._online("registered")
        print(
            f"[reporter] registered {self.node_id} with {self.base_url} "
            f"(heartbeat every {self.interval_s:.0f}s)"
        )
        return True

    def heartbeat(self, client: httpx.Client, telemetry: Telemetry) -> bool:
        node = telemetry.node
        headers = self._auth_header()
        if headers is None:
            # The heartbeat is authenticated, so a node with no stored
            # credential cannot heartbeat at all -- and it also cannot be given
            # work, because agent/worker.py refuses to claim without one. Going
            # back through registration is the only path that produces a token,
            # and it is the same self-healing route a 401 takes.
            print("[reporter] no node credential on disk; registering again")
            self.registered = False
            self.record_failure("this node has no credential; registering again")
            return False
        response = self._post(
            client,
            "/providers/heartbeat",
            {
                "node_id": self.node_id,
                "status": node.status,
                "detail": node.detail,
                # The node's own claim about whether it wants work. It is not
                # the same as `rentable`: a provider can be perfectly capable
                # and have chosen to drain.
                "accepts_work": node.accepts_work and telemetry.rentable,
                "metrics": metrics_payload(telemetry),
            },
            headers=headers,
        )
        self.ever_connected = True
        if response.status_code == 401:
            # The orchestrator has a row for this node but not this token: the
            # node re-registered from another install, or the database was
            # restored from a backup taken before this credential was issued.
            # Discarding the local copy is what makes the next registration mint
            # a fresh one; keeping it would 401 forever with no visible cause.
            # Same handling as agent/worker.py's claim path, deliberately -- a
            # credential that is dead for one endpoint is dead for both.
            print("[reporter] node credential rejected; discarding it to re-register")
            identity.clear_node_token()
            self.registered = False
            return False
        if response.status_code == 404:
            print("[reporter] orchestrator does not know this node; re-registering")
            self.registered = False
            # The link is left exactly as it was on purpose. The server
            # answered, so contact is healthy; this is the self-healing
            # re-registration path and the next loop iteration fixes it. Marking
            # it offline here would flicker the dashboard once per wiped
            # database for no reason a provider could act on.
            return False
        if response.status_code == 422:
            print(f"[reporter] heartbeat rejected as invalid: {response.text}")
            self.record_failure("the orchestrator rejected this node's heartbeat")
            return False
        response.raise_for_status()
        self._online("heartbeat accepted")
        return True


def run(state: ProviderState, stop: threading.Event, base_url: str | None = None) -> None:
    """Thread entry point. Returns only when `stop` is set.

    Failures are logged and retried; they never end the loop and they never
    change the node's local status. That separation is deliberate: the tray
    icon reports whether this machine can do work, and losing contact with the
    orchestrator does not stop Ollama from running. Conflating the two would
    tell a provider their GPU had failed because our server was down.
    """
    reporter = Reporter(state, base_url)
    backoff = reporter.interval_s

    with httpx.Client() as client:
        while not stop.is_set():
            try:
                telemetry = snapshot(state)
                ok = (
                    reporter.heartbeat(client, telemetry)
                    if reporter.registered
                    else reporter.register(client, telemetry)
                )
            except (httpx.HTTPError, ValueError, OSError) as exc:
                ok = False
                where = "lost contact with" if reporter.ever_connected else "cannot reach"
                print(
                    f"[reporter] {where} {reporter.base_url}: "
                    f"{exc.__class__.__name__}: {exc}"
                )
                # Same information, on a surface the provider actually has. The
                # print above goes to a console the packaged build never
                # creates, which is why this failure could run for hours
                # looking like success.
                reporter.record_failure(f"{exc.__class__.__name__}: {exc}")

            if ok:
                backoff = reporter.interval_s
                wait = reporter.interval_s
            else:
                # Grows on consecutive failures, resets on the next success.
                wait = backoff
                backoff = min(backoff * 2, MAX_BACKOFF_S)

            if stop.wait(wait):
                return
