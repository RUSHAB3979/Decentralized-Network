"""Claims inference or render work and runs it on this machine.

This is the thread that makes a provider actually earn. Everything before it --
registration, heartbeat, telemetry -- only told the marketplace this machine
exists. This one does the work.

Why the agent asks instead of being told
----------------------------------------
A provider's PC sits on a home connection, behind a router doing NAT and often
behind carrier-grade NAT on top of that. It has no address the orchestrator
could dial, and asking a provider to forward a port is asking most of them to
uninstall the app. So every byte travels over a connection this process opened.

The claim endpoint answers immediately -- it does not hold the request open --
so this loop is a poll, not a long-poll, and it must wait between attempts.
Without that wait it spins as fast as the network allows: constant database load
from a fleet doing nothing, and on a metered host, a bill. The server sets the
interval so it can be changed for every provider at once.

Real long-polling would cut the latency between a job being queued and being
picked up, and LISTEN/NOTIFY would cut it further. Both need the orchestrator to
hold a connection per waiting agent, which is a different hosting shape --
worth doing when idle latency matters more than portability.

What this deliberately does not do
----------------------------------
It runs one job at a time. No concurrency, no queueing locally, no prefetch.
That is not laziness -- concurrency on a provider box is a hand-built area under
ADR 0002, because getting it wrong degrades quietly: a render and an inference
request sharing the GPU evict each other's memory, both can still return the
right answer, and total throughput collapses. Nothing raises. One at a time is
the version whose behaviour is obvious.

It also does not renew a lease. If a job takes longer than the orchestrator's
lease window the work is handed to somebody else and this agent's result is
rejected with a 409, which it logs and drops. Renewal, drain and partial results
belong to agent/core/lease.py, which is hand-built and still unwritten.
"""

from __future__ import annotations

import os
import threading
import time

import httpx

from agent import identity
from agent.enrolment import Enrolment
from agent.runtime import blender
from agent.runtime.ollama import OllamaSupervisor
from agent.state import ProviderState, Status

# The claim endpoint returns immediately, so this only has to cover a slow
# network and the orchestrator's own database time -- its connect timeout is 5s,
# so 20 leaves room for a slow query on top without turning a healthy-but-slow
# server into an error.
CLAIM_TIMEOUT_S = 20.0

# Sized for a model that has to be read off disk into VRAM before it can answer.
# A cold start on a consumer card is tens of seconds, and a timeout under it
# would abandon work that was about to succeed.
RUN_TIMEOUT_S = 600.0

# Submitting a result is a small request against an endpoint that only writes.
RESULT_TIMEOUT_S = 30.0

# How long to wait between claims when there is no work, until the server says
# otherwise. Short enough that a customer is not waiting on the poll before
# their job is even picked up; long enough that an idle fleet is not a
# self-inflicted denial of service.
DEFAULT_POLL_INTERVAL_S = 3.0

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
        enrolment: Enrolment | None = None,
    ) -> None:
        self.state = state
        self.supervisor = supervisor
        self.base_url = (base_url or orchestrator_url()).rstrip("/")
        self.node_id = identity.node_id()
        self.enrolment = enrolment or Enrolment(state, self.base_url)
        # Overwritten by the server's answer on the first successful claim.
        self.poll_interval = DEFAULT_POLL_INTERVAL_S
        # Discovery and the version probe happen once for this worker's
        # lifetime. Repeating `blender --version` on every empty poll would
        # flash a console without CREATE_NO_WINDOW and would turn an idle fleet
        # into constant local process churn. More importantly, a binary that
        # cannot identify itself must not claim work for a guessed version.
        # Shared with the reporter through blender.installation(), so the
        # version this worker will actually run is the same one the orchestrator
        # was told about. Two independent probes could disagree.
        self.blender_binary, self.blender_version = blender.installation()

    def _claim(self, client: httpx.Client, path: str, item_key: str) -> dict | None:
        """Ask one claim endpoint, sharing credential and pacing semantics."""
        token = self.enrolment.token()
        if not token:
            return None
        response = client.post(
            f"{self.base_url}{path}",
            params={"node_id": self.node_id},
            headers={"Authorization": f"Bearer {token}"},
            follow_redirects=False,
            timeout=CLAIM_TIMEOUT_S,
        )
        if response.status_code == 401:
            self.enrolment.reject(token)
            return None
        if response.status_code == 404:
            # The reporter re-registers after its next heartbeat. The current
            # credential is still valid when only telemetry is missing.
            return None
        response.raise_for_status()
        body = response.json()
        interval = body.get("poll_interval_s")
        if isinstance(interval, (int, float)) and interval > 0:
            self.poll_interval = float(interval)
        return body.get(item_key)

    def claim(self, client: httpx.Client) -> dict | None:
        """Ask for an inference job. `None` means no work, which is normal.

        Also records the server's requested poll interval in `self.poll_interval`
        so the caller can pace itself from it.
        """
        return self._claim(client, "/providers/work/claim", "job")

    def claim_render(self, client: httpx.Client) -> dict | None:
        """Ask for one frame only when this process proved Blender is usable."""
        if self.blender_binary is None or self.blender_version is None:
            # Not calling the endpoint is stronger than claiming and then
            # failing: the latter burns a lease and makes the customer wait for
            # it to lapse before a real render node gets the frame.
            return None
        return self._claim(client, "/providers/render/claim", "frame")

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

    def run_render(self, frame: dict, storage: httpx.Client | None = None) -> dict:
        """Execute one frame and shape the render result wire body."""
        if self.blender_binary is None or self.blender_version is None:
            raise blender.BlenderError("rendering was not enabled at worker startup")
        output_bytes, render_seconds = blender.render_frame(
            self.blender_binary,
            installed_version=self.blender_version,
            requested_version=frame["blender_version"],
            engine=frame["engine"],
            output_format=frame["output_format"],
            frame_number=frame["frame_number"],
            source_url=frame["source_url"],
            output_url=frame["output_url"],
            # Lets the runtime download this job's scene once instead of once
            # per frame. Passed from the claim rather than tracked here, so a
            # frame reclaimed from another node still identifies its own job.
            job_id=frame["job_id"],
            storage=storage,
        )
        return {
            "status": "completed",
            "output_bytes": output_bytes,
            "render_seconds": render_seconds,
            "error_code": None,
        }

    def report(self, client: httpx.Client, job_id: str, result: dict) -> None:
        token = self.enrolment.token()
        if not token:
            return
        response = client.post(
            f"{self.base_url}/providers/work/{job_id}/result",
            params={"node_id": self.node_id},
            headers={"Authorization": f"Bearer {token}"},
            follow_redirects=False,
            json=result,
            timeout=RESULT_TIMEOUT_S,
        )
        if response.status_code == 401:
            self.enrolment.reject(token)
            return
        if response.status_code == 409:
            # The lease lapsed while this machine was still working, and the job
            # has gone to somebody else. Nothing to do but say so: retrying
            # cannot reclaim it, and the customer is already being served
            # elsewhere.
            print(f"[worker] job {job_id} was reassigned before this result arrived")
            return
        response.raise_for_status()

    def report_render(self, client: httpx.Client, frame_id: str, result: dict) -> None:
        token = self.enrolment.token()
        if not token:
            return
        response = client.post(
            f"{self.base_url}/providers/render/frames/{frame_id}/result",
            params={"node_id": self.node_id},
            headers={"Authorization": f"Bearer {token}"},
            follow_redirects=False,
            json=result,
            timeout=RESULT_TIMEOUT_S,
        )
        if response.status_code == 401:
            self.enrolment.reject(token)
            return
        if response.status_code == 409:
            # As with inference, lease loss transfers ownership. The uploaded
            # bytes do not make this frame ours again, and retrying this POST
            # would only repeat a conflict while another node serves it.
            print(
                f"[worker] frame {frame_id} was reassigned before this result arrived"
            )
            return
        response.raise_for_status()


def run(
    state: ProviderState,
    supervisor: OllamaSupervisor,
    accepting: threading.Event,
    stop: threading.Event,
    base_url: str | None = None,
    *,
    enrolment: Enrolment | None = None,
) -> None:
    """Thread entry point. Returns only when `stop` is set.

    A thin wrapper so that the cached scene file is deleted however the loop
    ends -- stop signal, unexpected exception, or interpreter shutdown. The
    cache exists to avoid re-downloading a job's .blend for every frame, and
    the price of holding it is that somebody else's project sits on this
    provider's disk between frames. Closing the app has to end that, and a
    cleanup that only runs on the tidy path is not the same promise.
    """
    try:
        _run_loop(state, supervisor, accepting, stop, base_url, enrolment=enrolment)
    finally:
        blender.forget_source_cache()


def _run_loop(
    state: ProviderState,
    supervisor: OllamaSupervisor,
    accepting: threading.Event,
    stop: threading.Event,
    base_url: str | None = None,
    *,
    enrolment: Enrolment | None = None,
) -> None:
    """The loop itself.

    Like reporter.run, this loop never exits on error. A provider whose internet
    dropped, or whose orchestrator was restarted, must resume on their own --
    requiring them to notice and relaunch the app is the same as losing them.
    """
    worker = Worker(state, supervisor, base_url, enrolment)
    backoff = MIN_BACKOFF_S
    poll_interval = worker.poll_interval

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

            job = None
            frame = None
            try:
                job = worker.claim(client)
                if not job:
                    # A successful claim is already ownership. Polling the
                    # second endpoint after receiving a job would prefetch a
                    # frame and violate the one-GPU-unit invariant before any
                    # execution even started, so render is asked only when the
                    # inference endpoint handed us nothing.
                    frame = worker.claim_render(client)
                backoff = MIN_BACKOFF_S
                poll_interval = worker.poll_interval
            except (httpx.HTTPError, ValueError, OSError) as exc:
                print(f"[worker] cannot claim work: {exc.__class__.__name__}: {exc}")
                if stop.wait(backoff):
                    return
                backoff = min(backoff * 2, MAX_BACKOFF_S)
                continue

            if not job and not frame:
                # Nothing to do. Wait before asking again.
                #
                # This sleep is load-bearing, and its absence was a bug: the
                # claim endpoint answers immediately rather than holding the
                # request open, so a bare `continue` here spins as fast as the
                # network allows. On a metered host that is a bill rather than a
                # crash, and on any host it is constant database load produced
                # by a fleet that is doing nothing.
                #
                # The server sets the pace via poll_interval_s, so it can be
                # changed for every provider at once without shipping a new
                # desktop build.
                if stop.wait(poll_interval):
                    return
                continue

            previous = (state.status, state.detail)
            if job:
                job_id = job.get("job_id")
                state.set(Status.BUSY, f"serving {job.get('model')}")
                try:
                    result = worker.run(job)
                except (httpx.HTTPError, ValueError, OSError, KeyError) as exc:
                    print(
                        f"[worker] job {job_id} failed: {exc.__class__.__name__}: {exc}"
                    )
                    result = {
                        "status": "failed",
                        "error_code": exc.__class__.__name__,
                    }

                try:
                    worker.report(client, job_id, result)
                except (httpx.HTTPError, OSError) as exc:
                    # The work was done and the answer is lost. The job's lease
                    # will lapse and another provider will repeat it, which is
                    # the correct outcome for the customer and a wasted
                    # GPU-minute for this one. Logged loudly because it is
                    # exactly the event that would otherwise look like the
                    # request simply never happened.
                    print(
                        f"[worker] job {job_id} ran but the result could not be "
                        f"delivered: {exc.__class__.__name__}: {exc}"
                    )
            else:
                frame_id = frame.get("frame_id")
                frame_number = frame.get("frame_number")
                state.set(Status.BUSY, f"rendering frame {frame_number}")
                render_started = time.monotonic()
                try:
                    result = worker.run_render(frame)
                except (
                    blender.BlenderError,
                    httpx.HTTPError,
                    ValueError,
                    OSError,
                    KeyError,
                ) as exc:
                    print(
                        f"[worker] frame {frame_id} failed: "
                        f"{exc.__class__.__name__}: {exc}"
                    )
                    result = {
                        "status": "failed",
                        "output_bytes": 0,
                        # Failed time is still evidence about work attempted on
                        # this node, never a bill. Metering remains hand-built.
                        "render_seconds": max(0.0, time.monotonic() - render_started),
                        "error_code": exc.__class__.__name__,
                    }

                try:
                    worker.report_render(client, frame_id, result)
                except (httpx.HTTPError, OSError) as exc:
                    # The artifact may already be in storage, but the frame is
                    # not complete until the orchestrator accepts this result.
                    # Lease expiry and reassignment are therefore still the
                    # customer-correct recovery path.
                    print(
                        f"[worker] frame {frame_id} ran but the result could not "
                        f"be delivered: {exc.__class__.__name__}: {exc}"
                    )

            # Return to whatever the supervisor last decided, rather than
            # asserting IDLE -- Ollama may have died while this job ran, and
            # overwriting an ERROR here would hide it until the next poll.
            state.set(*previous)
