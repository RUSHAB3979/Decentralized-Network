"""The provider app: a tray icon and a supervised inference runtime.

Run it from the repository root:

    python -m agent.app

What it does: finds or starts Ollama, watches that it stays up, shows the
node's status in the system tray with a control to stop accepting new work,
and (M1) registers with the orchestrator and heartbeats its telemetry there.

Threading: pywebview owns the main thread on Windows, so supervision and
reporting run on workers. The reporter and job worker share the enrolment
coordinator so a rejected credential is retired consistently.
"""

from __future__ import annotations

import sys
import threading

from dotenv import load_dotenv

from agent import reporter, worker
from agent.runtime.ollama import OllamaError, OllamaSupervisor
from agent.state import ProviderState, Status
from agent.ui import tray, window

# Slow enough to be free, fast enough that a provider who kills Ollama sees the
# tray go red before they wonder whether the app noticed.
HEALTH_POLL_S = 15.0


def _supervise(
    state: ProviderState,
    supervisor: OllamaSupervisor,
    accepting: threading.Event,
    stop: threading.Event,
) -> None:
    """Keep Ollama up and keep `state` honest about it. Runs on a worker thread."""
    state.set(Status.STARTING, "starting Ollama")
    try:
        supervisor.start()
    except OllamaError as exc:
        # A provider without Ollama is the single most likely first-run
        # outcome, so it gets the tray tooltip rather than a log line.
        state.set(Status.ERROR, str(exc))
        return

    source = "attached to running Ollama" if supervisor.adopted else "Ollama started"
    print(f"[app] {source} at {supervisor.host}")

    while True:
        if supervisor.is_up():
            if accepting.is_set():
                state.set(Status.IDLE, "ready for work")
            else:
                # Once leases exist this waits for them to finish. Today there
                # is nothing in flight, so draining completes immediately.
                state.set(Status.DRAINING, "not accepting new work")
        else:
            state.set(Status.ERROR, "Ollama stopped responding")

        if stop.wait(HEALTH_POLL_S):
            return


def main() -> int:
    # Reads ORCHESTRATOR_URL from a .env beside the repository when running
    # from source. The packaged app has no .env, which is why reporter.py
    # carries a working default rather than requiring the variable.
    load_dotenv()

    state = ProviderState()
    supervisor = OllamaSupervisor()
    accepting = threading.Event()
    accepting.set()
    stop = threading.Event()
    node_reporter = reporter.Reporter(state)

    # Named for what it does, not for what it is. The bare name `worker` used
    # to live here and now belongs to the agent.worker module imported above --
    # leaving it would shadow the module and make `worker.run` resolve to a
    # Thread, which fails at runtime rather than at import.
    supervisor_thread = threading.Thread(
        target=_supervise,
        args=(state, supervisor, accepting, stop),
        name="supervisor",
        daemon=True,
    )
    supervisor_thread.start()

    # Separate thread from the supervisor on purpose. Reporting is network I/O
    # against a machine we do not control, and a slow orchestrator must never
    # be able to delay noticing that Ollama died locally.
    telemetry_reporter = threading.Thread(
        target=reporter.run,
        args=(state, stop),
        kwargs={"reporter": node_reporter},
        name="reporter",
        daemon=True,
    )
    telemetry_reporter.start()

    # A third thread, separate from both of the above. It has to be separate
    # from the reporter because a job can run for minutes and heartbeats must
    # keep flowing while it does -- sharing a thread would make a busy node look
    # offline exactly when it is earning. And separate from the supervisor
    # because noticing that Ollama died must not wait behind a request being
    # served by Ollama.
    job_worker = threading.Thread(
        target=worker.run,
        args=(state, supervisor, accepting, stop),
        kwargs={"base_url": node_reporter.base_url, "enrolment": node_reporter.enrolment},
        name="worker",
        daemon=True,
    )
    job_worker.start()

    def on_drain_change(should_accept: bool) -> None:
        accepting.set() if should_accept else accepting.clear()
        # Reflect the click immediately instead of waiting out the poll
        # interval. A drain control that looks unresponsive for fifteen seconds
        # gets clicked again, and then the provider does not trust it.
        if should_accept:
            state.set(Status.IDLE, "ready for work")
        else:
            state.set(Status.DRAINING, "not accepting new work")

    dashboard = window.build(state, on_drain_change, node_reporter.enrol)

    def on_quit() -> None:
        stop.set()
        supervisor_thread.join(timeout=5)
        # Bounded like the supervisor join. Both threads are daemons, so a
        # request still in flight cannot hold the process open past this; the
        # orchestrator will age the node out via TTL rather than being told.
        # A clean deregister is a later milestone - it needs a credential,
        # or anyone could deregister anyone.
        telemetry_reporter.join(timeout=5)
        # Bounded like the others. A job still running at this point is
        # abandoned: its lease lapses server-side and another provider picks it
        # up. Waiting for it would mean a provider who clicked Quit watches a
        # spinner for the length of someone else's inference request.
        job_worker.join(timeout=5)
        # Only stops a server this process started; an Ollama the provider was
        # already running is left alone. See runtime/ollama.py.
        supervisor.stop()
        state.set(Status.STOPPED, "")
        # Ends the GUI loop below. Without this the process survives the tray
        # being quit, because webview.start() is still holding the main thread.
        dashboard.destroy()

    icon = tray.build(state, on_drain_change, on_quit, on_open=dashboard.show)
    icon.run_detached()

    # Blocks the main thread until on_quit destroys the window. The window is
    # created hidden and shown here, once the GUI loop is actually running -
    # showing it before that races the loop and can paint an empty frame.
    #
    # Launching straight to the dashboard is right while a human is starting
    # this by hand. Once the app auto-starts at login it should come up in the
    # tray instead, which is a flag this does not have yet.
    window.run(dashboard, on_started=dashboard.show)
    icon.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
