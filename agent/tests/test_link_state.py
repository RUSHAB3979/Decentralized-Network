"""Whether the app can tell the provider where it is reporting, and if anyone answered.

This file exists because of a real incident on 2026-08-15. A provider ran the
packaged app, the tray went green, the dashboard said "accepting work", and the
marketplace answered every customer request with 503 "no provider is currently
online". The node had never registered with the hosted orchestrator at all: the
packaged build carries no .env, so `ORCHESTRATOR_URL` was unset and
`agent/reporter.py` fell back to `http://localhost:8080`. The agent spent hours
registering into a dead local port, retrying forever exactly as designed, while
every local surface reported perfect health.

Nothing raised, and nothing could have. `accepts_work` is a local decision, and
the app had no field anywhere that meant "the orchestrator has answered us". The
reporter already knew -- `Reporter.ever_connected` distinguishes "never reached
it" from "reached it and then lost it" -- but that lived on an object created
inside the reporter thread and reachable from nowhere else. The window could not
have shown it if it had wanted to.

That is the failure shape ADR 0002 is written against: a wrong answer that keeps
working. So the tests below are mostly about the *distinctions* being preserved,
not about the happy path:

- the URL is surfaced even when the link is healthy, because the whole incident
  was a wrong URL that no surface displayed;
- "never connected" and "lost contact" stay distinguishable, because they need
  different debugging;
- losing the orchestrator must NOT change the node's own status, which
  `reporter.run`'s docstring has always insisted on -- our server being down is
  not the provider's GPU failing.
"""

from __future__ import annotations

import threading

import httpx
import pytest

from agent import reporter, telemetry
from agent.state import Link, ProviderState, Status
from agent.telemetry import Gpu, Host, Node, Ollama, Telemetry


def sample() -> Telemetry:
    return Telemetry(
        host=Host(
            hostname="test-box",
            os_version="Windows-11",
            cpu="Test CPU",
            logical_cores=8,
            ram_total_mb=16384,
        ),
        gpu=Gpu(
            name="NVIDIA GeForce RTX 3050",
            vram_total_mb=4096,
            vram_used_mb=512,
            utilisation_pct=3,
            temperature_c=41,
            driver="580.00",
        ),
        ollama=Ollama(reachable=True, version="0.12.0"),
        node=Node(status="idle", detail="ready for work", accepts_work=True),
        orchestrator=telemetry.Orchestrator(
            status="connecting", detail="not contacted yet", url=""
        ),
    )


# -- the state object itself ---------------------------------------------


def test_a_fresh_node_has_not_reached_the_orchestrator_yet():
    # Not ONLINE and not OFFLINE. Starting up is a third thing, and defaulting
    # to either of the other two would be a claim we have not earned: ONLINE is
    # a lie, and OFFLINE would show every provider an error for the first few
    # seconds of every launch and teach them to ignore it.
    state = ProviderState()
    assert state.link is Link.CONNECTING


def test_setting_the_link_records_where_we_are_reporting():
    state = ProviderState()
    state.set_link(Link.ONLINE, "https://example.invalid", "heartbeat accepted")
    assert state.link is Link.ONLINE
    assert state.link_url == "https://example.invalid"
    assert state.link_detail == "heartbeat accepted"


def test_link_changes_notify_listeners():
    # The tray tooltip and the window both redraw from this. A link change that
    # did not notify would sit stale until some unrelated status change
    # happened to repaint it.
    state = ProviderState()
    seen = []
    state.on_change(lambda: seen.append(state.link))
    state.set_link(Link.OFFLINE, "http://localhost:8080", "ConnectError")
    assert seen == [Link.OFFLINE]


def test_repeating_the_same_link_does_not_churn_listeners():
    state = ProviderState()
    state.set_link(Link.ONLINE, "http://x.invalid", "ok")
    seen = []
    state.on_change(lambda: seen.append(1))
    state.set_link(Link.ONLINE, "http://x.invalid", "ok")
    assert seen == [], "an unchanged link must not repaint the tray"


def test_the_link_is_independent_of_the_node_status():
    # The load-bearing separation. `reporter.run` promises that losing contact
    # with the orchestrator never changes the node's local status, because the
    # tray reports whether this machine can do work and our server being down
    # does not stop Ollama running. Conflating them would tell a provider their
    # GPU had failed because we had an outage.
    state = ProviderState()
    state.set(Status.IDLE, "ready for work")
    state.set_link(Link.OFFLINE, "http://localhost:8080", "ConnectError")
    assert state.status is Status.IDLE
    assert state.detail == "ready for work"


# -- what the reporter records -------------------------------------------


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_a_successful_register_marks_the_link_online(monkeypatch):
    state = ProviderState()
    monkeypatch.setattr(reporter.identity, "store_node_token", lambda _t: True)
    rep = reporter.Reporter(state, "http://orchestrator.invalid")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "node_id": rep.node_id,
                "heartbeat_interval_s": 15,
                "node_token": "tok",
            },
        )

    with _client(handler) as client:
        assert rep.register(client, sample()) is True

    assert state.link is Link.ONLINE
    assert state.link_url == "http://orchestrator.invalid"


def test_the_url_is_visible_even_when_the_link_is_healthy(monkeypatch):
    # The regression guard for the 2026-08-15 incident. A green light that does
    # not say WHERE it is green is what let a node report happily into
    # localhost for hours. The address has to be on the surface at all times,
    # not only in an error message.
    state = ProviderState()
    monkeypatch.setattr(reporter.identity, "store_node_token", lambda _t: True)
    rep = reporter.Reporter(state, reporter.DEFAULT_ORCHESTRATOR)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"node_id": rep.node_id, "heartbeat_interval_s": 15}
        )

    with _client(handler) as client:
        rep.register(client, sample())

    assert state.link is Link.ONLINE
    assert state.link_url == "http://localhost:8080"

    payload = telemetry.to_dict(telemetry.snapshot(state))
    assert payload["orchestrator"]["url"] == "http://localhost:8080"


def test_a_successful_heartbeat_marks_the_link_online():
    state = ProviderState()
    rep = reporter.Reporter(state, "http://orchestrator.invalid")
    rep.registered = True

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"node_id": rep.node_id, "accepted": True})

    with _client(handler) as client:
        assert rep.heartbeat(client, sample()) is True

    assert state.link is Link.ONLINE


@pytest.mark.parametrize(
    "ever_connected, expected",
    [
        # Never reached it: almost always a misconfigured URL or a backend that
        # was never started. The provider needs to check the address.
        (False, Link.CONNECTING),
        # Reached it before: the address is right and something broke since.
        # The provider needs to check their network, or wait us out.
        (True, Link.OFFLINE),
    ],
)
def test_failures_distinguish_never_reached_from_lost_contact(ever_connected, expected):
    state = ProviderState()
    rep = reporter.Reporter(state, "http://orchestrator.invalid")
    rep.ever_connected = ever_connected

    rep.record_failure("ConnectError: connection refused")

    assert state.link is expected
    assert "connection refused" in state.link_detail


def test_the_loop_reports_an_unreachable_orchestrator_to_the_ui(monkeypatch):
    # End to end through the real thread entry point: a node that cannot reach
    # the orchestrator must say so on a surface a provider can actually see,
    # rather than only in a console the packaged build does not have.
    stop = threading.Event()
    state = ProviderState()
    monkeypatch.setattr(reporter, "snapshot", lambda _state: sample())

    def handler(request: httpx.Request) -> httpx.Response:
        stop.set()
        raise httpx.ConnectError("connection refused", request=request)

    transport = httpx.MockTransport(handler)
    real_client = httpx.Client
    monkeypatch.setattr(
        reporter.httpx,
        "Client",
        lambda *a, **kw: real_client(*a, **{**kw, "transport": transport}),
    )

    thread = threading.Thread(
        target=reporter.run,
        args=(state, stop, "http://orchestrator.invalid"),
        daemon=True,
    )
    thread.start()
    thread.join(timeout=10)

    assert not thread.is_alive()
    assert state.link is Link.CONNECTING
    assert state.link_url == "http://orchestrator.invalid"
    assert "ConnectError" in state.link_detail


# -- what reaches the window ---------------------------------------------


def test_the_snapshot_carries_the_link_across_the_bridge():
    state = ProviderState()
    state.set_link(Link.OFFLINE, "https://api.invalid", "ReadTimeout")
    payload = telemetry.to_dict(telemetry.snapshot(state))

    assert payload["orchestrator"] == {
        "status": "offline",
        "detail": "ReadTimeout",
        "url": "https://api.invalid",
    }


def test_the_link_does_not_change_whether_the_machine_is_rentable():
    # `rentable` answers "is this hardware capable of paid work", which is a
    # question about the GPU and Ollama. Folding the orchestrator into it would
    # make an outage on our side look like a fault on the provider's, and would
    # feed back into the heartbeat's own accepts_work field.
    t = sample()
    assert t.rentable is True
    t.orchestrator = telemetry.Orchestrator(
        status="offline", detail="ConnectError", url="http://localhost:8080"
    )
    assert t.rentable is True
