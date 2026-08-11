"""System tray icon: the provider's entire interface to the node.

There is no window. A provider installs this, sees a dot near the clock, and
should never need to look at it again - except for the one moment that matters,
which is when they sit down to play a game and want their GPU back. That is the
'Accept new work' toggle, and it is the reason this app has a UI at all.

The icon is drawn in code rather than loaded from a .ico file. That is a
packaging decision: a bundled asset means --add-data in the PyInstaller spec
and a path that resolves differently under _MEIPASS than it does from source,
which is a recurring way for a frozen build to break in a way the source build
never does.
"""

from __future__ import annotations

from collections.abc import Callable

import pystray
from PIL import Image, ImageDraw

from agent.state import ProviderState, Status

# Read at a glance from a 16px tray slot, so: green good, amber transitional,
# red broken, grey off.
_COLOURS: dict[Status, tuple[int, int, int]] = {
    Status.STARTING: (150, 150, 150),
    Status.IDLE: (46, 160, 67),
    Status.BUSY: (31, 111, 235),
    Status.DRAINING: (191, 135, 0),
    Status.STOPPED: (110, 110, 110),
    Status.ERROR: (207, 34, 46),
}


def _icon_image(status: Status) -> Image.Image:
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    ImageDraw.Draw(image).ellipse((8, 8, 56, 56), fill=_COLOURS[status])
    return image


def build(
    state: ProviderState,
    on_drain_change: Callable[[bool], None],
    on_quit: Callable[[], None],
    on_open: Callable[[], None] | None = None,
) -> pystray.Icon:
    """Build the tray icon.

    Call .run_detached() rather than .run(): pywebview needs the Windows main
    thread and pystray does not, so the dashboard gets it and the tray runs
    alongside. See agent/ui/window.py.
    """

    def accepting() -> bool:
        return state.status.accepts_work

    def toggle_accepting(icon: pystray.Icon, item: pystray.MenuItem) -> None:
        on_drain_change(not accepting())

    def quit_app(icon: pystray.Icon, item: pystray.MenuItem) -> None:
        on_quit()
        icon.stop()

    def open_dashboard(icon: pystray.Icon, item: pystray.MenuItem) -> None:
        if on_open is not None:
            on_open()

    menu = pystray.Menu(
        # Disabled, so it reads as a status line rather than something to click.
        pystray.MenuItem(lambda item: str(state), None, enabled=False),
        pystray.Menu.SEPARATOR,
        # default=True makes this the double-click action, which is what people
        # try first on a tray icon before they ever find the menu.
        pystray.MenuItem("Open dashboard", open_dashboard, default=True),
        pystray.MenuItem(
            "Accept new work",
            toggle_accepting,
            checked=lambda item: accepting(),
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", quit_app),
    )

    icon = pystray.Icon(
        name="gpu-provider",
        icon=_icon_image(state.status),
        title="GPU Provider",
        menu=menu,
    )

    def refresh() -> None:
        icon.icon = _icon_image(state.status)
        icon.title = f"GPU Provider - {state}"
        icon.update_menu()

    state.on_change(refresh)
    return icon
