"""Claims inference jobs from the orchestrator and runs them on this machine.

This is the thread that makes a provider actually earn. Everything before it --
registration, heartbeat, telemetry -- only told the marketplace this machine
exists. This one does the work.

Why the agent asks instead of being told
----------------------------------------
A provider's PC sits on a home connection, behind a router doing NAT and often
behind carrier-grade NAT on top of that. It has no address the orchestrator
could dial, and asking a provider to forward a port is asking most of them to
uninstall the app. So every byte travels over a connection this process opened.

The orchestrator holds the claim request open when there is nothing to do
(long-polling), which is why the request timeout below is generous: an empty
response after twenty seconds of waiting is the *normal* case, not a fault.

What this deliberately does not do
----------------------------------
It runs one job at a time. No concurrency, no queueing locally, no prefetch.
That is not laziness -- concurrency on a provider box is a hand-built area under
ADR 0002, because getting it wrong degrades quietly: a second request while a
model is loaded evicts it, the next request pays a cold start, throughput
collapses, and every individual request still succeeds. Nothing raises. One at a
time is the version whose behaviour is obvious.

It also does not renew a lease. If a job takes longer than the orchestrator's
lease window the work is handed to somebody else and this agent's result is
rejected with a 409, which it logs and drops. Renewal, drain and partial results
belong to agent/core/lease.py, which is hand-built and still unwritten.
"""

from __future__ import annotations

import os
import threading

import httpx

from agent import identity
from agent.runtime.ollama import OllamaSupervisor
from agent.state import ProviderState, Status

# Longer than the orchestrator's CLAIM_WAIT_SEC (20s by default) plus its
# database time. The claim endpoint holds the request open on purpose, so a
# client timeout below that would turn every idle poll into an error and, with
# retries, into a request storm against a server that is behaving correctly.
CLAIM_TIMEOUT_S = 45.0

# Sized for a model that has to be read off disk into VRAM before it can answer.
# A cold start on a consumer card is tens of seconds, and a timeout under it
# would abandon work that was about to succeed.
RUN_TIMEOUT_S = 600.0

# Submitting a result is a small request against an endpoint that only writes.
RESULT_TIMEOUT_S = 30.0

# Applied when the orchestrator is unreachable or answering with 5xx. Same shape
# as reporter.py's backoff and for the same reason: a provider whose router
# rebooted must come back on their own, without hammering a struggling server on
# the way.
MIN_BACKOFF_S = 2.0
MAX_BACKOFF_S = 120.0


def orchestrator_url() -> str:
    return (os.getenv("ORCHESTRATOR_URL") or "http://localhost:8080").rstrip("/")


class Worker:
    """One claim-run-report cycle at a time, for as long as the app is running."""

    def __init__(
        self,
        state: ProviderState,
        supervisor: OllamaSupervisor,
        base_url: str | None = None,
    ) -> None:
        self.state = state
        self.supervisor = supervisor
        self.base_url = (base_url or orchestrator_url()).rstrip("/")
        self.node_id = identity.node_id()

    # -- credential -------------------------------------------------------
    #
    # Read from disk on every use rather than cached at construction. The
    # reporter rewrites this file whenever it re-registers, and a worker holding
    # a stale token in memory would fail every claim with a 401 until the app
    # was restarted -- with the file on disk already correct, which is a
    # genuinely baffling thing to debug.

    def _token(self) -> str | None:
        return identity.node_token()

    def _auth_header(self) -> dict[str, str] | None:
        token = self._token()
        return {"Authorization": f"Bearer {token}"} if token else None

    # -- one cycle --------------------------------------------------------

    def claim(self, client: httpx.Client) -> dict | None:
        """Ask for a job. `None` means there is nothing to do, which is normal."""
        headers = self._auth_header()
        if headers is None:
            return None
        response = client.post(
            f"{self.base_url}/providers/work/claim",
            params={"node_id": self.node_id},
            headers=headers,
            timeout=CLAIM_TIMEOUT_S,
        )
        if response.status_code == 401:
            # The token this agent holds is not the one the orchestrator has.
            # Almost always because the node re-registered elsewhere, or the
            # orchestrator's database was restored. Dropping the local token
            # makes the reporter mint a fresh one on its next registration,
            # which is the self-healing path.
            print("[worker] node credential rejected; discarding it to force re-registration")
            identity.clear_node_token()
            return None
        response.raise_for_status()
        return response.json().get("job")

    def run(self, job: dict, runtime: httpx.Client | None = None) -> dict:
        """Execute one job against the local runtime and shape the result.

        Returns the body to POST back, including the failure case -- a job that
        the runtime could not run still has to be reported, or it sits claimed
        until its lease lapses and another provider is asked to repeat work that
        will fail there too.

        `runtime` is injectable so tests can supply a mock transport. The
        alternative -- monkeypatching httpx.Client globally -- makes the patched
        constructor call itself, which is an infinite recursion rather than a
        test failure and takes a while to recognise.
        """
        payload = job.get("payload") or {}
        options: dict[str, float | int] = {}
        if payload.get("temperature") is not None:
            options["temperature"] = payload["temperature"]
        if payload.get("max_tokens") is not None:
            options["num_predict"] = payload["max_tokens"]

        body: dict = {
            "model": payload.get("model") or job.get("model"),
            "messages": payload.get("messages") or [],
            "stream": False,
        }
        if options:
            body["options"] = options

        owns_client = runtime is None
        active = runtime or httpx.Client()
        try:
            response = active.post(
                f"{self.supervisor.host}/api/chat", json=body, timeout=RUN_TIMEOUT_S
            )
            response.raise_for_status()
            result = response.json()
        finally:
            # Only close what this method opened. Closing a caller's client
            # would break the next job on a shared connection.
            if owns_client:
                active.close()

        message = result.get("message") or {}
        duration_ns = result.get("total_duration")
        return {
            "status": "completed",
            "content": str(message.get("content") or ""),
            "finish_reason": "stop" if result.get("done", True) else "length",
            # Reported exactly as the runtime counted them. This agent does not
            # interpret, round, or price them -- that is metering, it is
            # hand-built under ADR 0002, and it lives in agent/core/meter.py.
            "prompt_tokens": max(0, int(result.get("prompt_eval_count") or 0)),
            "completion_tokens": max(0, int(result.get("eval_count") or 0)),
            "total_duration_ms": (
                max(0, int(duration_ns // 1_000_000))
                if isinstance(duration_ns, int)
                else None
            ),
        }

    def report(self, client: httpx.Client, job_id: str, result: dict) -> None:
        headers = self._auth_header()
        if headers is None:
            return
        response = client.post(
            f"{self.base_url}/providers/work/{job_id}/result",
            params={"node_id": self.node_id},
            headers=headers,
            json=result,
            timeout=RESULT_TIMEOUT_S,
        )
        if response.status_code == 409:
            # The lease lapsed while this machine was still working, and the job
            # has gone to somebody else. Nothing to do but say so: retrying
            # cannot reclaim it, and the customer is already being served
            # elsewhere.
            print(f"[worker] job {job_id} was reassigned before this result arrived")
            return
        response.raise_for_status()


def run(
    state: ProviderState,
    supervisor: OllamaSupervisor,
    accepting: threading.Event,
    stop: threading.Event,
    base_url: str | None = None,
) -> None:
    """Thread entry point. Returns only when `stop` is set.

    Like reporter.run, this loop never exits on error. A provider whose internet
    dropped, or whose orchestrator was restarted, must resume on their own --
    requiring them to notice and relaunch the app is the same as losing them.
    """
    worker = Worker(state, supervisor, base_url)
    backoff = MIN_BACKOFF_S

    with httpx.Client() as client:
        while not stop.is_set():
            # Respect the tray's drain switch locally as well as server-side.
            # The orchestrator already refuses to hand work to a node that is
            # not accepting, but a provider who clicked "stop" should not be
            # relying on the server to honour it.
            if not accepting.is_set():
                if stop.wait(2.0):
                    return
                continue

            try:
                job = worker.claim(client)
                backoff = MIN_BACKOFF_S
            except (httpx.HTTPError, ValueError, OSError) as exc:
                print(f"[worker] cannot claim work: {exc.__class__.__name__}: {exc}")
                if stop.wait(backoff):
                    return
                backoff = min(backoff * 2, MAX_BACKOFF_S)
                continue

            if not job:
                # The orchestrator held the request open and had nothing. Go
                # straight back rather than sleeping: the wait already happened
                # on the server.
                continue

            job_id = job.get("job_id")
            previous = (state.status, state.detail)
            state.set(Status.BUSY, f"serving {job.get('model')}")
            try:
                result = worker.run(job)
            except (httpx.HTTPError, ValueError, OSError, KeyError) as exc:
                print(f"[worker] job {job_id} failed: {exc.__class__.__name__}: {exc}")
                result = {
                    "status": "failed",
                    "error_code": exc.__class__.__name__,
                }

            try:
                worker.report(client, job_id, result)
            except (httpx.HTTPError, OSError) as exc:
                # The work was done and the answer is lost. The job's lease will
                # lapse and another provider will repeat it, which is the
                # correct outcome for the customer and a wasted GPU-minute for
                # this one. Logged loudly because it is exactly the event that
                # would otherwise look like the request simply never happened.
                print(
                    f"[worker] job {job_id} ran but the result could not be "
                    f"delivered: {exc.__class__.__name__}: {exc}"
                )

            # Return to whatever the supervisor last decided, rather than
            # asserting IDLE -- Ollama may have died while this job ran, and
            # overwriting an ERROR here would hide it until the next poll.
            state.set(*previous)
