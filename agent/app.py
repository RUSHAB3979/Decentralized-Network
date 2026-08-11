"""The provider app: a tray icon and a supervised inference runtime.

Run it from the repository root:

    python -m agent.app

What v1 does: finds or starts Ollama, watches that it stays up, and shows the
node's status in the system tray with a control to stop accepting new work.

What v1 deliberately does not do: talk to the orchestrator. Enrolment, leases
and metering live in agent/core/, they are hand-built per ADR 0002, and they
are not stubbed into the boot path here. That is the point - the app runs and
can be tested today without them, so they get written carefully rather than
under pressure to make the thing start.

Threading: pystray owns the main thread on Windows, so supervision runs on a
worker and the two communicate only through agent.state.ProviderState.
"""

from __future__ import annotations

import sys
import threading

from agent.runtime.ollama import OllamaError, OllamaSupervisor
from agent.state import ProviderState, Status
from agent.ui import tray

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
    state = ProviderState()
    supervisor = OllamaSupervisor()
    accepting = threading.Event()
    accepting.set()
    stop = threading.Event()

    worker = threading.Thread(
        target=_supervise,
        args=(state, supervisor, accepting, stop),
        name="supervisor",
        daemon=True,
    )
    worker.start()

    def on_drain_change(should_accept: bool) -> None:
        accepting.set() if should_accept else accepting.clear()
        # Reflect the click immediately instead of waiting out the poll
        # interval. A drain control that looks unresponsive for fifteen seconds
        # gets clicked again, and then the provider does not trust it.
        if should_accept:
            state.set(Status.IDLE, "ready for work")
        else:
            state.set(Status.DRAINING, "not accepting new work")

    def on_quit() -> None:
        stop.set()
        worker.join(timeout=5)
        # Only stops a server this process started; an Ollama the provider was
        # already running is left alone. See runtime/ollama.py.
        supervisor.stop()
        state.set(Status.STOPPED, "")

    tray.build(state, on_drain_change, on_quit).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
