"""Subprocess helpers for a Windows app that has no console of its own.

This module exists because of a bug, and the bug is worth stating so it does
not come back. GPUProvider.exe is built windowed (`console=False`), so the app
itself has no console. A child process started without CREATE_NO_WINDOW does
not inherit one - Windows allocates a *new* console for it and shows it. The
window is destroyed as soon as the child exits, so a short-lived probe like
`ollama --version` appears as a black rectangle that flashes on screen and
vanishes.

That is a bad failure in two ways. It is invisible when running from a
terminal, because there the child inherits the parent's console and nothing is
created, so it only reproduces in the packaged app a provider actually
installs. And it does not raise: the probe succeeds, the data is correct, and
the only symptom is that the app looks broken and untrustworthy on someone
else's desktop. Per ADR 0002 that is the shape of defect worth spending code to
make structurally impossible rather than remembering to avoid.

So: nothing that runs inside the app calls subprocess directly. It calls this.

One deliberate exception, marked at the call site: agent/bench.py. That file is
run as a standalone script and is meant to stay copyable onto a rented GPU box
by itself, so it cannot import from this package, and it is console-only anyway.
"""

from __future__ import annotations

import subprocess
import sys

# Documented in the Win32 process creation flags. Absent on non-Windows, where
# the whole problem does not exist, so it degrades to a no-op rather than a
# platform check at every call site.
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


def run(args: list[str], *, timeout: float, check: bool = False) -> subprocess.CompletedProcess:
    """Run a command to completion, capturing output, with no console window.

    Deliberately narrower than subprocess.run: text mode and captured output
    are not optional, because every caller in this codebase wants a string back
    and none of them want a child writing to a console that should not exist.
    """
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=check,
        creationflags=CREATE_NO_WINDOW,
    )
