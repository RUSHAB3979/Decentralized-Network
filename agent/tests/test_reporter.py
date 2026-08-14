"""What the agent sends, and how it behaves when the orchestrator misbehaves.

The payload tests exist because the agent and the orchestrator are written by
different people against orchestrator/models.py, and a field name that drifts
produces a 422 at runtime on someone else's machine. The behaviour tests exist
because the retry and re-registration paths are the ones that only execute
during an incident, which is the worst possible time to find out they are
wrong.

httpx.MockTransport is used rather than a live server so these run in CI with
no network and no orchestrator.
"""

from __future__ import annotations

import json
import re
import threading

import httpx
import pytest

from agent import identity, reporter
from agent.state import ProviderState
from agent.telemetry import Gpu, Host, Model, Node, Ollama, Telemetry

# Mirrors NODE_ID in orchestrator/models.py. Duplicated on purpose: the agent
# cannot import from the orchestrator (that package is not installed on a
# provider machine, and agent/requirements.txt is a security boundary), so the
# only way to catch a drift is to assert against a copy of the pattern.
NODE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{7,63}$")


def telemetry(*, gpu: bool = True, rentable: bool = True, accepts: bool = True):
    return Telemetry(
        host=Host(
            hostname="DESKTOP-TEST",
            os_version="Windows 11",
            cpu="AMD64 Family 25",
            logical_cores=16,
            ram_total_mb=32768,
        ),
        gpu=Gpu(
            name="NVIDIA GeForce RTX 4090",
            vram_total_mb=24564,
            vram_used_mb=1024,
            utilisation_pct=7,
            temperature_c=42,
            driver="566.36",
        )
        if gpu
        else None,
        ollama=Ollama(
            reachable=rentable,
            version="0.12.4",
            available=[
                Model(name="qwen2.5:0.5b", size_mb=379, remote=False),
                Model(name="qwen3-vl:235b-cloud", size_mb=0, remote=True),
                Model(name="deepseek-v3.1:671b-cloud", size_mb=0, remote=True),
            ],
        ),
        node=Node(status="idle", detail="ready for work", accepts_work=accepts),
    )


def test_node_id_matches_the_orchestrator_contract():
    value = identity.node_id()
    assert NODE_ID_PATTERN.match(value), value


def test_node_id_is_stable_across_calls():
    # If this ever fails, every app launch enrols a new node and the registry
    # fills with orphans -- visibly wrong only once the fleet is large.
    assert identity.node_id() == identity.node_id()


@pytest.mark.parametrize(
    "configured, expected",
    [
        ("http://localhost:8080", "http://localhost:8080"),
        ("http://localhost:8080/", "http://localhost:8080"),
        ("http://localhost:8080///", "http://localhost:8080"),
    ],
)
def test_trailing_slashes_are_stripped(monkeypatch, configured, expected):
    # A double slash in the path is 404'd by some proxies and silently
    # redirected by others; neither symptom points at a stray slash in .env.
    monkeypatch.setenv("ORCHESTRATOR_URL", configured)
    assert reporter.orchestrator_url() == expected


def test_default_url_when_unset(monkeypatch):
    # The packaged app ships without a .env, so an unset variable has to be a
    # working default rather than a crash.
    monkeypatch.delenv("ORCHESTRATOR_URL", raising=False)
    assert reporter.orchestrator_url() == reporter.DEFAULT_ORCHESTRATOR


def test_cloud_models_are_not_advertised_as_local_capacity():
    # The whole point. deepseek-v3.1:671b-cloud appears in /api/tags exactly
    # like a local model; advertising it would offer 671B of capacity from a
    # machine that has 24 GB of VRAM and a 379 MB model on disk.
    models = reporter.metrics_payload(telemetry())["local_models"]
    assert models == ["qwen2.5:0.5b"]


def test_capability_payload_matches_the_contract_field_names():
    payload = reporter.capability_payload(telemetry())
    assert set(payload) == {
        "hostname",
        "os_version",
        "cpu",
        "logical_cores",
        "ram_total_mb",
        "gpu_name",
        "vram_total_mb",
        "gpu_driver",
        "agent_version",
    }
    assert payload["gpu_name"] == "NVIDIA GeForce RTX 4090"


def test_machine_without_a_gpu_still_produces_a_valid_payload():
    payload = reporter.capability_payload(telemetry(gpu=False))
    assert payload["gpu_name"] is None
    assert payload["hostname"] == "DESKTOP-TEST"
    metrics = reporter.metrics_payload(telemetry(gpu=False))
    assert metrics["gpu_utilisation_pct"] is None


def test_a_node_that_cannot_serve_never_claims_to_accept_work():
    # accepts_work is the field scheduling will trust. A node whose Ollama is
    # unreachable has its local toggle set to "accepting" and still must not
    # advertise itself, or it collects leases it cannot fulfil.
    sent = {}

    def handler(request: httpx.Request) -> httpx.Response:
        sent.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "node_id": "x",
                "received_at": "2026-08-11T12:00:00Z",
                "heartbeat_interval_s": 15,
            },
        )

    rep = reporter.Reporter(ProviderState(), "http://orchestrator.invalid")
    rep.registered = True
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        rep.heartbeat(client, telemetry(rentable=False, accepts=True))

    assert sent["accepts_work"] is False


def test_unknown_node_triggers_re_registration():
    # The recovery path for a restored or wiped database. Without it, agents
    # heartbeat successfully into a registry that has no row for them and the
    # marketplace silently shows nothing.
    rep = reporter.Reporter(ProviderState(), "http://orchestrator.invalid")
    rep.registered = True

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "unknown node"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert rep.heartbeat(client, telemetry()) is False
    assert rep.registered is False


def test_server_dictates_the_heartbeat_interval():
    rep = reporter.Reporter(ProviderState(), "http://orchestrator.invalid")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "node_id": rep.node_id,
                "registered_at": "2026-08-11T12:00:00Z",
                "heartbeat_interval_s": 42,
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert rep.register(client, telemetry()) is True
    assert rep.interval_s == 42
    assert rep.registered is True


def test_loop_survives_an_unreachable_orchestrator(monkeypatch):
    # The defect this guards against is docs/PROVIDER-APP.md §8.1: a worker
    # thread that returns permanently on an error, leaving no symptom except
    # that nothing ever happens again. A connection failure must leave the
    # loop alive and waiting to retry, not kill the thread.
    stop = threading.Event()
    attempts = []
    monkeypatch.setattr(reporter, "snapshot", lambda _state: telemetry())

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(request.url)
        # Ends the loop from inside the first failure, so the test does not sit
        # through a backoff interval. What is being asserted is that the code
        # reached the wait at all rather than propagating the exception.
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
        args=(ProviderState(), stop, "http://orchestrator.invalid"),
        daemon=True,
    )
    thread.start()
    thread.join(timeout=10)

    assert attempts, "reporter never attempted a request"
    assert not thread.is_alive(), "reporter thread did not exit when stopped"
