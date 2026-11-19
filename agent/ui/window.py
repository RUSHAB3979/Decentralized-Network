"""The provider dashboard: a real desktop window, not a page in a website.

Rendered by Edge WebView2, which ships with Windows, so the executable stays
around 20 MB instead of carrying a browser engine. The window has no address
bar, no tabs and no browser chrome, it owns its taskbar entry, and it works
with the network unplugged. What it is not is a web app: nothing here is served
over HTTP and there is no origin, only a file on disk talking to this process.

Threading note, because it is the one thing in this file that will bite. Both
pystray and pywebview want the Windows main thread. pywebview genuinely
requires it, and pystray does not, so pywebview gets it and the tray runs
detached. Closing the window therefore must not end the process: a provider who
clicks the X expects the node to keep earning from the tray, so `closing` hides
the window and cancels the close.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

import webview

from agent import telemetry
from agent.state import ProviderState


def _asset_root() -> Path:
    """Where desktop.html lives, in both a source run and a frozen build.

    PyInstaller unpacks a one-file build to a temporary directory and points
    sys._MEIPASS at it. Resolving relative to __file__ instead would land
    inside the archive path and fail only in the packaged app, which is the
    worst place to discover it.
    """
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent.parent))
    packaged = base / "agent" / "ui" / "web" / "desktop.html"
    if packaged.is_file():
        return packaged
    # Source layout, where this file sits at agent/ui/window.py.
    return Path(__file__).resolve().parent / "web" / "desktop.html"


class Api:
    """The bridge the page calls. Every method here is reachable from JS.

    Keep this surface small and boring on purpose. It is the only place where
    something rendered can reach into the process, and a method added here is a
    method the page can call.
    """

    def __init__(
        self,
        state: ProviderState,
        on_accepting_change: Callable[[bool], None],
        on_enrol: Callable[[str], str | None],
    ):
        self._state = state
        self._on_accepting_change = on_accepting_change
        self._on_enrol = on_enrol

    def snapshot(self) -> dict:
        return telemetry.to_dict(telemetry.snapshot(self._state))

    def set_accepting(self, accepting: bool) -> dict:
        self._on_accepting_change(bool(accepting))
        return self.snapshot()

    def enrol(self, key: str) -> dict:
        error = self._on_enrol(key)
        return {"ok": error is None, "error": error}


def build(
    state: ProviderState,
    on_accepting_change: Callable[[bool], None],
    on_enrol: Callable[[str], str | None],
) -> webview.Window:
    """Create the dashboard window, hidden until asked for."""
    window = webview.create_window(
        "GPU Provider",
        str(_asset_root()),
        js_api=Api(state, on_accepting_change, on_enrol),
        width=880,
        height=760,
        min_size=(720, 600),
        background_color="#08090A",
        hidden=True,
    )

    def on_closing() -> bool:
        # Returning False cancels the close. The node keeps running in the
        # tray, which is what a provider means by closing a dashboard.
        window.hide()
        return False

    window.events.closing += on_closing
    return window


def run(window: webview.Window, on_started: Callable[[], None] | None = None) -> None:
    """Enter the GUI loop. Blocks the main thread until the app really exits."""
    webview.start(func=on_started, debug=False)
