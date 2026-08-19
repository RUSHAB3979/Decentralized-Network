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


class Link(Enum):
    """Whether the orchestrator has actually answered this node.

    Deliberately not a member of `Status`. `Status` is about this machine --
    whether Ollama is up and whether the provider wants work -- and the two must
    not merge, because our server being unreachable does not stop their GPU
    working. See `reporter.run`.

    Three states rather than a boolean, because "we have never got through" and
    "we were connected and lost it" need different actions from the provider.
    The first is nearly always a wrong address; the second is a network or an
    outage. Collapsing them cost a full afternoon on 2026-08-15, when a node
    reported into `http://localhost:8080` for hours while every local surface
    showed perfect health.
    """

    CONNECTING = "connecting"  # no successful exchange yet, this run
    ONLINE = "online"          # the orchestrator answered the last request
    OFFLINE = "offline"        # it answered before, and does not now


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
        self._link = Link.CONNECTING
        self._link_detail = "not contacted yet"
        # Empty until the reporter tells us, which it does before its first
        # request. Nothing else in the app knows the address: it is chosen from
        # ORCHESTRATOR_URL inside reporter.py, and the whole point of surfacing
        # it here is that no other surface could show it.
        self._link_url = ""
        self._listeners: list[Callable[[], None]] = []

    @property
    def status(self) -> Status:
        with self._lock:
            return self._status

    @property
    def detail(self) -> str:
        with self._lock:
            return self._detail

    @property
    def link(self) -> Link:
        with self._lock:
            return self._link

    @property
    def link_detail(self) -> str:
        with self._lock:
            return self._link_detail

    @property
    def link_url(self) -> str:
        with self._lock:
            return self._link_url

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

    def set_link(self, link: Link, url: str, detail: str = "") -> None:
        """Record what the orchestrator client just saw.

        The URL is written on every call, including successful ones, so the
        dashboard can always answer "where is this node reporting?". A healthy
        light that does not name its destination is what made the 2026-08-15
        incident invisible.
        """
        with self._lock:
            if (
                link == self._link
                and url == self._link_url
                and detail == self._link_detail
            ):
                return  # no-op writes must not churn the tray icon
            self._link = link
            self._link_url = url
            self._link_detail = detail
            listeners = list(self._listeners)
        # Outside the lock, for the same reason as `set`.
        for listener in listeners:
            listener()

    def on_change(self, listener: Callable[[], None]) -> None:
        with self._lock:
            self._listeners.append(listener)

    def __str__(self) -> str:
        return f"{self.status.value}: {self.detail}" if self.detail else self.status.value
