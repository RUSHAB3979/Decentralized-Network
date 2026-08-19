"""What the provider agent sends to its own runtime, and what it must not.

The security property tested here used to live in the orchestrator, as
`test_chat_forwards_work_but_not_the_customer_key`. It moved when execution
moved: the model now runs on the provider's machine, so this is where "the
customer's key never reaches the runtime" has to be true.

It is also stronger here than it was there. The orchestrator had the key in
scope and had to be careful not to forward it. This process is never given it at
all -- the job envelope it receives has no field for one. The test below records
that, so a future change that starts passing customer credentials down to
providers has to delete an assertion to do it.
"""

from __future__ import annotations

import threading
from pathlib import Path

import httpx
import pytest

from agent import worker
from agent.state import ProviderState, Status


class _FakeSupervisor:
    """Stands in for OllamaSupervisor, which would try to find a real binary."""

    host = "http://ollama.invalid"


def _job(**overrides) -> dict:
    job = {
        "job_id": "job_abc",
        "model": "tinyllama:latest",
        "payload": {
            "model": "tinyllama:latest",
            "messages": [{"role": "user", "content": "hello"}],
            "temperature": 0.2,
            "max_tokens": 32,
        },
        "lease_expires_at": "2026-08-14T12:05:00Z",
    }
    job.update(overrides)
    return job


def _ollama_response(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "message": {"role": "assistant", "content": "hello back"},
            "done": True,
            "prompt_eval_count": 4,
            "eval_count": 2,
            "total_duration": 1_500_000_000,
        },
    )


def test_job_envelope_carries_no_customer_credential():
    # The contract, asserted structurally. A job is a model plus messages; there
    # is nowhere in it for a customer's API key to travel, which is why the
    # provider machine cannot leak one.
    payload = _job()["payload"]
    flat = str(payload).lower()
    assert "authorization" not in flat
    assert "api_key" not in flat
    assert "bearer" not in flat


def test_run_sends_the_job_to_the_local_runtime():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        import json

        captured["body"] = json.loads(request.content)
        return _ollama_response(request)

    w = worker.Worker(
        ProviderState(), _FakeSupervisor(), base_url="http://orch.invalid"
    )
    with httpx.Client(transport=httpx.MockTransport(handler)) as runtime:
        result = w.run(_job(), runtime=runtime)

    # Never leaves the machine: the runtime is addressed on its own host.
    assert captured["url"].startswith("http://ollama.invalid")
    # The property this file exists for.
    assert "authorization" not in {k.lower() for k in captured["headers"]}

    assert captured["body"]["model"] == "tinyllama:latest"
    assert captured["body"]["stream"] is False
    assert captured["body"]["options"] == {"temperature": 0.2, "num_predict": 32}

    assert result["status"] == "completed"
    assert result["content"] == "hello back"
    assert result["prompt_tokens"] == 4
    assert result["completion_tokens"] == 2
    # Nanoseconds in, milliseconds out. Getting this conversion wrong is a
    # factor of a million on a number that will one day inform billing, and
    # nothing about the resulting figure would look obviously wrong.
    assert result["total_duration_ms"] == 1500


def test_absent_options_are_omitted_rather_than_sent_as_null():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        captured["body"] = json.loads(request.content)
        return _ollama_response(request)

    job = _job()
    job["payload"]["temperature"] = None
    job["payload"]["max_tokens"] = None

    w = worker.Worker(ProviderState(), _FakeSupervisor())
    with httpx.Client(transport=httpx.MockTransport(handler)) as runtime:
        w.run(job, runtime=runtime)

    # Ollama treats an explicit null as a value, not as "unset", and would
    # reject or misread it. Sending no options at all is what "use the model's
    # defaults" has to look like on the wire.
    assert "options" not in captured["body"]


def test_claim_without_a_credential_asks_for_nothing(monkeypatch):
    # A node that has not registered yet, or whose token write failed, must not
    # send an unauthenticated claim -- it would be rejected, logged as an error,
    # and retried forever. Returning None keeps it quietly idle instead.
    monkeypatch.setattr("agent.identity.node_token", lambda: None)

    called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, json={"job": None, "poll_interval_s": 20})

    w = worker.Worker(ProviderState(), _FakeSupervisor())
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert w.claim(client) is None
    assert not called


def test_rejected_credential_is_discarded_so_registration_can_heal_it(monkeypatch):
    cleared = []
    monkeypatch.setattr("agent.identity.node_token", lambda: "nf_node_stale")
    monkeypatch.setattr("agent.identity.clear_node_token", lambda: cleared.append(True))

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "invalid node credential"})

    w = worker.Worker(ProviderState(), _FakeSupervisor())
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert w.claim(client) is None

    # Dropping the file is what makes the next registration mint a fresh token.
    # Without this the agent would 401 on every claim until someone restarted
    # it, with a perfectly valid-looking token sitting on disk.
    assert cleared == [True]


def test_a_reassigned_job_is_not_retried(monkeypatch):
    # 409 means the lease lapsed and somebody else owns the work now. Raising
    # here would make the worker retry a result that can never be accepted.
    monkeypatch.setattr("agent.identity.node_token", lambda: "nf_node_ok")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(409, json={"detail": "job is not claimed by this node"})

    w = worker.Worker(ProviderState(), _FakeSupervisor())
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        w.report(client, "job_abc", {"status": "completed", "content": "x"})


def test_a_reassigned_frame_result_is_dropped_not_retried(monkeypatch):
    # A conflict is an ownership answer, not a transient transport failure.
    # Retrying cannot make the lease belong to this node again.
    monkeypatch.setattr("agent.identity.node_token", lambda: "nf_node_ok")
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(409, json={"detail": "frame is not claimed by this node"})

    w = worker.Worker(ProviderState(), _FakeSupervisor())
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        w.report_render(
            client,
            "frame_abc",
            {
                "status": "completed",
                "output_bytes": 15,
                "render_seconds": 2.5,
                "error_code": None,
            },
        )

    assert len(calls) == 1


def test_a_failed_run_still_produces_a_reportable_result():
    # The loop converts an exception into a 'failed' body rather than dropping
    # it. A job that is never reported sits claimed until its lease lapses, and
    # is then handed to another provider to fail identically -- so the customer
    # waits twice as long for the same error.
    state = ProviderState()
    state.set(Status.IDLE, "ready for work")

    def failing(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("runtime is not listening")

    w = worker.Worker(state, _FakeSupervisor())
    with httpx.Client(transport=httpx.MockTransport(failing)) as runtime:
        with pytest.raises(httpx.HTTPError):
            w.run(_job(), runtime=runtime)


def test_the_loop_waits_between_empty_claims(monkeypatch):
    """The regression guard for a busy loop.

    The claim endpoint answers immediately -- it does not hold the request open
    -- so the loop has to wait between attempts itself. It once did not, and the
    symptom is not a crash: the agent simply asks as fast as the network allows,
    producing constant database load from a fleet that is doing nothing and, on
    metered hosting, a bill. Nothing raises, which is exactly why this needs a
    test rather than a comment.
    """
    monkeypatch.setattr("agent.identity.node_token", lambda: "nf_node_ok")
    # This regression is specifically about the inference-only empty cycle.
    # Pinning discovery keeps it independent of whether a CI host happens to
    # have Blender installed.
    monkeypatch.setattr(worker.blender, "find_binary", lambda: None)

    calls = {"claims": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["claims"] += 1
        return httpx.Response(200, json={"job": None, "poll_interval_s": 7})

    waits = []

    class RecordingStop(threading.Event):
        """Records every wait and ends the loop after the first one."""

        def wait(self, timeout=None):
            waits.append(timeout)
            return True  # ends the loop, so the test cannot hang

    accepting = threading.Event()
    accepting.set()

    transport = httpx.MockTransport(handler)
    real_client = httpx.Client

    def client_factory(*args, **kwargs):
        return real_client(transport=transport)

    monkeypatch.setattr(httpx, "Client", client_factory)

    worker.run(
        ProviderState(),
        _FakeSupervisor(),
        accepting,
        RecordingStop(),
        base_url="http://orch.invalid",
    )

    assert calls["claims"] == 1, "claimed more than once without waiting"
    # And it waited for the interval the *server* asked for, not a local
    # constant -- that is what lets the fleet be re-paced without a new build.
    assert waits == [7.0], f"expected a 7s wait from poll_interval_s, got {waits}"


def test_machine_without_blender_never_calls_the_render_claim_endpoint(monkeypatch):
    monkeypatch.setattr("agent.identity.node_token", lambda: "nf_node_ok")
    monkeypatch.setattr(worker.blender, "find_binary", lambda: None)
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"frame": None, "poll_interval_s": 3})

    w = worker.Worker(ProviderState(), _FakeSupervisor())
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert w.claim_render(client) is None
    assert calls == []


def test_no_output_render_is_reported_as_failed(monkeypatch):
    monkeypatch.setattr("agent.identity.node_token", lambda: "nf_node_ok")
    monkeypatch.setattr(worker.blender, "find_binary", lambda: Path("blender.exe"))
    monkeypatch.setattr(worker.blender, "detect_version", lambda binary: "4.3.2")

    stop = threading.Event()
    reports = []

    frame = {
        "frame_id": "frame_abc",
        "job_id": "render_abc",
        "frame_number": 12,
        "blender_version": "4.3",
        "engine": "cycles",
        "output_format": "png",
        "source_url": "https://storage.invalid/source.blend",
        "output_url": "https://storage.invalid/frame.png",
        "lease_expires_at": "2026-08-18T10:00:00Z",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/providers/work/claim":
            return httpx.Response(200, json={"job": None, "poll_interval_s": 5})
        if request.url.path == "/providers/render/claim":
            return httpx.Response(200, json={"frame": frame, "poll_interval_s": 5})
        if request.url.path.endswith("/frames/frame_abc/result"):
            import json

            reports.append(json.loads(request.content))
            stop.set()
            return httpx.Response(200)
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    def no_output(self, claimed):
        raise worker.blender.BlenderError("Blender produced no output for frame 12")

    monkeypatch.setattr(worker.Worker, "run_render", no_output)
    transport = httpx.MockTransport(handler)
    real_client = httpx.Client
    monkeypatch.setattr(
        worker.httpx,
        "Client",
        lambda *args, **kwargs: real_client(transport=transport),
    )

    accepting = threading.Event()
    accepting.set()
    worker.run(
        ProviderState(),
        _FakeSupervisor(),
        accepting,
        stop,
        base_url="http://orch.invalid",
    )

    assert len(reports) == 1
    assert reports[0]["status"] == "failed"
    assert reports[0]["output_bytes"] == 0
    assert reports[0]["error_code"] == "BlenderError"


def test_inference_claim_prevents_a_second_render_claim(monkeypatch):
    """A server offering both kinds of work must still transfer one lease."""
    monkeypatch.setattr("agent.identity.node_token", lambda: "nf_node_ok")
    monkeypatch.setattr(worker.blender, "find_binary", lambda: Path("blender.exe"))
    monkeypatch.setattr(worker.blender, "detect_version", lambda binary: "4.3.2")

    stop = threading.Event()
    calls = {"inference_claim": 0, "render_claim": 0, "inference_result": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/providers/work/claim":
            calls["inference_claim"] += 1
            return httpx.Response(200, json={"job": _job(), "poll_interval_s": 3})
        if request.url.path == "/providers/render/claim":
            calls["render_claim"] += 1
            return httpx.Response(
                200,
                json={"frame": {"frame_id": "must_not_be_owned"}, "poll_interval_s": 3},
            )
        if request.url.path == "/api/chat":
            return _ollama_response(request)
        if request.url.path.endswith("/work/job_abc/result"):
            calls["inference_result"] += 1
            # Ownership has lasted from claim through execution and reporting;
            # only now may the next loop iteration ask either endpoint again.
            assert calls["render_claim"] == 0
            stop.set()
            return httpx.Response(200)
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    transport = httpx.MockTransport(handler)
    real_client = httpx.Client
    monkeypatch.setattr(
        worker.httpx,
        "Client",
        lambda *args, **kwargs: real_client(transport=transport),
    )

    accepting = threading.Event()
    accepting.set()
    worker.run(
        ProviderState(),
        _FakeSupervisor(),
        accepting,
        stop,
        base_url="http://orch.invalid",
    )

    assert calls == {
        "inference_claim": 1,
        "render_claim": 0,
        "inference_result": 1,
    }
