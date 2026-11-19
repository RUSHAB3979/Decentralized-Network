"""Registers enrolled machines and sends provider telemetry with bounded retries."""

from __future__ import annotations

import os
import re
import threading

import httpx

from agent import __version__, identity
from agent.enrolment import Enrolment
from agent.runtime import blender
from agent.state import Link, ProviderState
from agent.telemetry import Telemetry, snapshot

DEFAULT_ORCHESTRATOR = "http://localhost:8080"

# Comfortably above the orchestrator's 5s database connect timeout plus query
# time. See the module docstring.
REQUEST_TIMEOUT_S = 15.0

DEFAULT_INTERVAL_S = 15.0
NODE_TOKEN_FORMAT = re.compile(r"nf_node_[A-Za-z0-9_-]{43}")

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

    def __init__(
        self,
        state: ProviderState,
        base_url: str | None = None,
        enrolment: Enrolment | None = None,
    ) -> None:
        self.state = state
        self.base_url = (base_url or orchestrator_url()).rstrip("/")
        self.node_id = identity.node_id()
        self.enrolment = enrolment or Enrolment(state, self.base_url)
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
            follow_redirects=False,
        )

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

    def enrol(self, key: str) -> str | None:
        def exchange(secret: str) -> str:
            with httpx.Client() as client:
                response = self._post(
                    client, "/providers/enrol", self._registration_payload(snapshot(self.state)),
                    headers={"Authorization": f"Bearer {secret}"},
                )
                response.raise_for_status()
                body = response.json()
                if not isinstance(body, dict) or body.get("node_id") != self.node_id:
                    raise ValueError("unexpected enrolled node")
                token = body.get("node_token")
                if not isinstance(token, str) or not NODE_TOKEN_FORMAT.fullmatch(token):
                    raise ValueError("missing node credential")
                return token

        return self.enrolment.submit(key, exchange)

    def _registration_payload(self, telemetry: Telemetry) -> dict:
        return {
            "node_id": self.node_id,
            "capability": capability_payload(telemetry),
        }

    def register(self, client: httpx.Client, telemetry: Telemetry) -> bool:
        token = self.enrolment.token()
        if not token:
            self.registered = False
            return False
        response = self._post(
            client, "/providers/register", self._registration_payload(telemetry),
            headers={"Authorization": f"Bearer {token}"},
        )
        self.ever_connected = True
        if response.status_code == 401:
            self.enrolment.reject(token)
            self.registered = False
            return False
        if response.status_code == 422:
            self.record_failure("the orchestrator rejected this node's details")
            return False
        response.raise_for_status()
        body = response.json()
        self.interval_s = float(body.get("heartbeat_interval_s") or DEFAULT_INTERVAL_S)
        self.registered = True
        self._online("registered")
        return True

    def heartbeat(self, client: httpx.Client, telemetry: Telemetry) -> bool:
        node = telemetry.node
        token = self.enrolment.token()
        if not token:
            self.registered = False
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
            headers={"Authorization": f"Bearer {token}"},
        )
        self.ever_connected = True
        if response.status_code == 401:
            self.enrolment.reject(token)
            self.registered = False
            return False
        if response.status_code == 404:
            self.registered = False
            self.state.set_link(Link.CONNECTING, self.base_url, "Restoring node telemetry.")
            return False
        if response.status_code == 422:
            self.record_failure("the orchestrator rejected this node's heartbeat")
            return False
        response.raise_for_status()
        self._online("heartbeat accepted")
        return True


def run(
    state: ProviderState,
    stop: threading.Event,
    base_url: str | None = None,
    *,
    reporter: Reporter | None = None,
) -> None:
    """Thread entry point. Returns only when `stop` is set.

    Failures are logged and retried; they never end the loop and they never
    change the node's local status. That separation is deliberate: the tray
    icon reports whether this machine can do work, and losing contact with the
    orchestrator does not stop Ollama from running. Conflating the two would
    tell a provider their GPU had failed because our server was down.
    """
    reporter = reporter or Reporter(state, base_url)
    backoff = reporter.interval_s

    with httpx.Client() as client:
        while not stop.is_set():
            try:
                if not reporter.enrolment.token():
                    reporter.registered = False
                    if stop.wait(2.0):
                        return
                    continue
                telemetry = snapshot(state)
                ok = (
                    reporter.heartbeat(client, telemetry)
                    if reporter.registered
                    else reporter.register(client, telemetry)
                )
            except (httpx.HTTPError, ValueError, OSError) as exc:
                ok = False
                detail = type(exc).__name__
                if isinstance(exc, httpx.HTTPStatusError):
                    detail = f"Orchestrator returned HTTP {exc.response.status_code}"
                print(f"[reporter] {detail}")
                reporter.record_failure(detail)

            if state.link in (Link.UNENROLLED, Link.CREDENTIAL_ERROR):
                wait = 2.0
            elif ok:
                backoff = reporter.interval_s
                wait = reporter.interval_s
            else:
                # Grows on consecutive failures, resets on the next success.
                wait = backoff
                backoff = min(backoff * 2, MAX_BACKOFF_S)

            if stop.wait(wait):
                return
