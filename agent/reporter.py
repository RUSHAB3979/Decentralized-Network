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
from agent.state import ProviderState
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

    def _post(self, client: httpx.Client, path: str, payload: dict) -> httpx.Response:
        return client.post(
            f"{self.base_url}{path}", json=payload, timeout=REQUEST_TIMEOUT_S
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
            return False
        response.raise_for_status()
        body = response.json()
        self.interval_s = float(body.get("heartbeat_interval_s") or DEFAULT_INTERVAL_S)
        self.registered = True
        print(
            f"[reporter] registered {self.node_id} with {self.base_url} "
            f"(heartbeat every {self.interval_s:.0f}s)"
        )
        return True

    def heartbeat(self, client: httpx.Client, telemetry: Telemetry) -> bool:
        node = telemetry.node
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
        )
        self.ever_connected = True
        if response.status_code == 404:
            print("[reporter] orchestrator does not know this node; re-registering")
            self.registered = False
            return False
        if response.status_code == 422:
            print(f"[reporter] heartbeat rejected as invalid: {response.text}")
            return False
        response.raise_for_status()
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

            if ok:
                backoff = reporter.interval_s
                wait = reporter.interval_s
            else:
                # Grows on consecutive failures, resets on the next success.
                wait = backoff
                backoff = min(backoff * 2, MAX_BACKOFF_S)

            if stop.wait(wait):
                return
