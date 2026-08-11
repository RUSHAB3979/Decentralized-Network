"""The one piece of state every part of the provider app agrees on.

The tray reads this, the runtime supervisor writes it, and the orchestrator
client (once it exists) will write it too. It lives in its own module so those
three can import it without importing each other.

Thread safety matters here and is not incidental. pystray owns the main thread
on Windows, so every status change is written from a worker thread and read
from the UI thread. A torn read here would show a stale tray icon, which is
exactly the class of bug ADR 0002 calls silent: nothing raises, the provider
just believes something false about their own machine.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from enum import Enum


class Status(Enum):
    """What the node is doing, as a provider would describe it."""

    STARTING = "starting"
    IDLE = "idle"          # ready and accepting work
    BUSY = "busy"          # serving at least one request
    DRAINING = "draining"  # finishing current work, refusing new work
    STOPPED = "stopped"
    ERROR = "error"

    @property
    def accepts_work(self) -> bool:
        return self in (Status.IDLE, Status.BUSY)


class ProviderState:
    """Mutable node status with change notification.

    `detail` carries the human-readable reason for the current status - the
    Ollama error, the model being pulled, the number of live requests. The tray
    shows it on hover, which is the only diagnostic surface a provider has
    before they start reading log files.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._status = Status.STARTING
        self._detail = "starting up"
        self._listeners: list[Callable[[], None]] = []

    @property
    def status(self) -> Status:
        with self._lock:
            return self._status

    @property
    def detail(self) -> str:
        with self._lock:
            return self._detail

    def set(self, status: Status, detail: str = "") -> None:
        with self._lock:
            if status == self._status and detail == self._detail:
                return  # no-op writes must not churn the tray icon
            self._status = status
            self._detail = detail
            listeners = list(self._listeners)
        # Fire outside the lock: a listener that redraws the tray must never be
        # able to deadlock against a worker thread writing the next status.
        for listener in listeners:
            listener()

    def on_change(self, listener: Callable[[], None]) -> None:
        with self._lock:
            self._listeners.append(listener)

    def __str__(self) -> str:
        return f"{self.status.value}: {self.detail}" if self.detail else self.status.value
