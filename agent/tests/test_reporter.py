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
from pathlib import Path

import httpx
import pytest

from agent import identity, reporter, worker
from agent.core import creds
from agent.state import ProviderState
from agent.telemetry import Gpu, Host, Model, Node, Ollama, Orchestrator, Telemetry

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
        # Required rather than defaulted, so that a new construction site has to
        # say what the orchestrator link is instead of silently inheriting a
        # healthy-looking placeholder. What this field reports is asserted in
        # agent/tests/test_link_state.py.
        orchestrator=Orchestrator(
            status="online", detail="heartbeat accepted", url="http://localhost:8080"
        ),
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

    rep = reporter.Reporter(ProviderState(), "https://orchestrator.invalid")
    rep.registered = True
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        rep.heartbeat(client, telemetry(rentable=False, accepts=True))

    assert sent["accepts_work"] is False


def test_unknown_node_triggers_re_registration():
    # The recovery path for a restored or wiped database. Without it, agents
    # heartbeat successfully into a registry that has no row for them and the
    # marketplace silently shows nothing.
    rep = reporter.Reporter(ProviderState(), "https://orchestrator.invalid")
    rep.registered = True

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "unknown node"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert rep.heartbeat(client, telemetry()) is False
    assert rep.registered is False


def test_server_dictates_the_heartbeat_interval():
    rep = reporter.Reporter(ProviderState(), "https://orchestrator.invalid")

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
        args=(ProviderState(), stop, "https://orchestrator.invalid"),
        daemon=True,
    )
    thread.start()
    thread.join(timeout=10)

    assert attempts, "reporter never attempted a request"
    assert not thread.is_alive(), "reporter thread did not exit when stopped"


def test_a_machine_without_blender_advertises_no_render_version(monkeypatch):
    """None, not a guess and not an empty string.

    The orchestrator matches a job's requested release series against this
    column. A node that reported "" or "unknown" would still not match anything
    -- but a node that reported a guessed version WOULD match, take a frame, and
    render it on the wrong Blender. The output would be plausible, subtly
    different, and nothing anywhere would raise.
    """
    monkeypatch.setattr(reporter.blender, "find_binary", lambda: None)
    assert reporter.metrics_payload(telemetry())["blender_version"] is None


def test_the_reported_version_is_the_one_the_worker_would_actually_run(monkeypatch):
    """The reporter and the worker must not be able to disagree.

    If they did, the orchestrator would be told this node serves 4.3 while the
    worker held a 4.2 binary: every frame matched to it would be claimed and
    then rejected, burning an attempt each time against a job that was never
    going to render here. Both read the same cached probe, so this is structural
    rather than a convention somebody has to remember.
    """
    monkeypatch.setattr(reporter.blender, "find_binary", lambda: Path("blender.exe"))
    monkeypatch.setattr(reporter.blender, "detect_version", lambda binary: "4.3.2")

    reported = reporter.metrics_payload(telemetry())["blender_version"]
    assert reported == "4.3.2"
    # A bare object() for the supervisor: this test is about the version
    # probe, and Worker does not touch the runtime to construct itself.
    assert reported == worker.Worker(ProviderState(), object()).blender_version


def test_having_blender_is_not_the_same_as_being_allowed_to_render(monkeypatch):
    """The agent reports a capability and never a permission.

    Eligibility lives in provider_nodes.render_eligible, defaults FALSE, and is
    set by an operator. A .blend can carry embedded Python, so agreeing to run
    one is the machine owner's decision -- it must not be something the software
    can grant itself by noticing an installed binary.
    """
    monkeypatch.setattr(reporter.blender, "find_binary", lambda: Path("blender.exe"))
    monkeypatch.setattr(reporter.blender, "detect_version", lambda binary: "4.3.2")
    payload = reporter.metrics_payload(telemetry())
    assert "render_eligible" not in payload
    assert not any("eligib" in key for key in payload)


def test_heartbeat_carries_the_node_credential():
    """Unauthenticated heartbeats let anyone who learns a node id impersonate it.

    node_id is not a secret -- it appears in the marketplace listing and in the
    agent's own logs -- so before the credential was required, a stranger could
    post metrics for someone else's machine: mark it idle when it was busy,
    advertise models it does not have, or hold it visible after it went dark.
    """
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["authorization"] = request.headers.get("authorization")
        return httpx.Response(
            200,
            json={
                "node_id": "x",
                "received_at": "2026-08-11T12:00:00Z",
                "heartbeat_interval_s": 15,
            },
        )

    rep = reporter.Reporter(ProviderState(), "https://orchestrator.invalid")
    rep.registered = True
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert rep.heartbeat(client, telemetry()) is True

    assert seen["authorization"] == "Bearer test-node-token"


def test_rejected_credential_requires_a_new_enrolment_key(monkeypatch):
    cleared = []

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "bad credential"})

    rep = reporter.Reporter(ProviderState(), "https://orchestrator.invalid")
    rep.registered = True
    monkeypatch.setattr(
        creds, "clear", lambda: cleared.append(True)
    )
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert rep.heartbeat(client, telemetry()) is False

    assert cleared, "the rejected token was kept"
    assert rep.registered is False
    assert rep.state.link.value == "unenrolled"


def test_a_node_with_no_credential_waits_for_enrolment(monkeypatch):
    monkeypatch.setattr(creds, "load", lambda: None)
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url)
        return httpx.Response(200, json={})

    rep = reporter.Reporter(ProviderState(), "https://orchestrator.invalid")
    rep.registered = True
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert rep.heartbeat(client, telemetry()) is False

    assert calls == [], "heartbeated without a credential"
    assert rep.state.link.value == "unenrolled"
    assert rep.registered is False


def test_enrolment_persists_only_the_node_credential_and_restart_registers(monkeypatch, capsys):
    key = "nf_enrol_" + "A" * 43
    node_token = "nf_node_" + "B" * 43
    stored = []
    calls = []
    state = ProviderState()
    rep = reporter.Reporter(state, "https://orchestrator.invalid")
    monkeypatch.setattr(reporter, "snapshot", lambda _state: telemetry())
    monkeypatch.setattr(creds, "load", lambda: stored[-1] if stored else None)
    monkeypatch.setattr(creds, "store", stored.append)

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        expected = key if request.url.path == "/providers/enrol" else node_token
        assert request.headers["Authorization"] == f"Bearer {expected}"
        assert json.loads(request.content)["node_id"] == rep.node_id
        assert expected.encode() not in request.content
        if request.url.path == "/providers/enrol":
            return httpx.Response(201, json={"node_id": rep.node_id, "node_token": node_token})
        return httpx.Response(200, json={"heartbeat_interval_s": 15})

    real_client = httpx.Client
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(reporter.httpx, "Client", lambda: real_client(transport=transport))
    assert rep.enrol(key) is None
    assert stored == [node_token]
    restarted = reporter.Reporter(ProviderState(), rep.base_url)
    with httpx.Client() as client:
        assert restarted.register(client, telemetry())
        assert restarted.heartbeat(client, telemetry())
    assert calls == ["/providers/enrol", "/providers/register", "/providers/heartbeat"]
    output = capsys.readouterr().out + state.link_detail
    assert key not in output and node_token not in output


def test_enrolment_does_not_spend_a_key_when_the_vault_is_unavailable(monkeypatch):
    def unavailable():
        raise NotImplementedError

    monkeypatch.setattr(creds, "load", unavailable)

    def unexpectedly_called():
        pytest.fail("A key was spent without a credential store")

    monkeypatch.setattr(reporter.httpx, "Client", unexpectedly_called)
    rep = reporter.Reporter(ProviderState(), "https://orchestrator.invalid")
    assert "credential store is unavailable" in rep.enrol("nf_enrol_" + "A" * 43)
    assert rep.enrolment.token() is None
    assert rep.state.link.value == "credential_error"


def test_store_failure_blocks_work_even_if_the_vault_returns_partial_data(monkeypatch):
    rep = reporter.Reporter(ProviderState(), "https://orchestrator.invalid")
    stored = []
    token = "nf_node_" + "B" * 43
    monkeypatch.setattr(creds, "load", lambda: stored[-1] if stored else None)

    def fail_after_write(credential):
        stored.append(credential)
        raise OSError("synthetic vault write failure")

    monkeypatch.setattr(creds, "store", fail_after_write)
    error = rep.enrolment.submit("nf_enrol_" + "A" * 43, lambda _key: token)
    assert "Windows could not save" in error
    assert rep.enrolment.token() is None
    assert rep.state.link.value == "credential_error"


def test_rejection_of_an_earlier_credential_preserves_the_current_one(monkeypatch):
    rep = reporter.Reporter(ProviderState(), "https://orchestrator.invalid")
    monkeypatch.setattr(creds, "load", lambda: "current-token")

    def unexpectedly_cleared():
        pytest.fail("An earlier response cleared a newer credential")

    monkeypatch.setattr(creds, "clear", unexpectedly_cleared)
    rep.enrolment.reject("earlier-token")
    assert rep.enrolment.token() == "current-token"


def test_enrolment_refuses_to_send_credentials_over_remote_plain_http():
    rep = reporter.Reporter(ProviderState(), "http://orchestrator.invalid")
    assert "HTTPS" in rep.enrol("nf_enrol_" + "A" * 43)
    assert rep.enrolment.token() is None
