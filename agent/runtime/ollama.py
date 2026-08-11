"""Locate, start and health-check the Ollama server.

Ollama is the inference runtime the provider app ships against. vLLM's native
Windows build needs CUDA 13 and an RTX 6000 Ada or newer; on the consumer cards
this marketplace is trying to recruit, the supported vLLM path is WSL2, which
reintroduces exactly the setup friction a one-click app exists to remove. See
the header of agent/bench.py for the longer version.

The rule this module is built around: never kill an Ollama the provider was
already running. Plenty of people who would rent out a GPU already use Ollama
themselves, and an agent that terminates their server on exit - taking their
loaded model and their chat with it - gets uninstalled the same day.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

import httpx

# Single definition, in agent/winproc.py, along with the explanation of why a
# windowed app has to pass it. This module had its own copy and telemetry.py
# had none, which is exactly how the console flash came back.
from agent.winproc import CREATE_NO_WINDOW

DEFAULT_HOST = "http://127.0.0.1:11434"


class OllamaError(RuntimeError):
    """Ollama is missing, unreachable, or failed to start."""


def find_binary() -> Path | None:
    """Find ollama.exe. Returns None if it is not installed."""
    on_path = shutil.which("ollama")
    if on_path:
        return Path(on_path)
    # The Windows installer puts it here and does not always reach PATH in an
    # already-open session, so PATH alone produces false 'not installed'.
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        candidate = Path(local_appdata) / "Programs" / "Ollama" / "ollama.exe"
        if candidate.is_file():
            return candidate
    return None


class OllamaSupervisor:
    """Owns the Ollama server process, but only if it started it."""

    def __init__(self, host: str = DEFAULT_HOST) -> None:
        self.host = host
        self._process: subprocess.Popen | None = None
        self._adopted = False

    @property
    def adopted(self) -> bool:
        """True when we attached to a server the provider was already running."""
        return self._adopted

    def is_up(self, timeout: float = 2.0) -> bool:
        try:
            return httpx.get(f"{self.host}/api/tags", timeout=timeout).status_code == 200
        except httpx.RequestError:
            return False

    def start(self, deadline_s: float = 60.0) -> None:
        """Ensure a reachable server, starting one only if none is running."""
        if self.is_up():
            self._adopted = True
            return

        binary = find_binary()
        if binary is None:
            raise OllamaError(
                "Ollama is not installed. Get it from https://ollama.com/download"
            )

        self._process = subprocess.Popen(
            [str(binary), "serve"],
            creationflags=CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        started = time.monotonic()
        while time.monotonic() - started < deadline_s:
            if self.is_up():
                return
            # Check the exit code inside the loop, not after it. A server that
            # dies in 200ms - port already bound is the common one - would
            # otherwise burn the full deadline and then report a timeout,
            # hiding the return code that actually explains the failure.
            if self._process.poll() is not None:
                raise OllamaError(
                    f"'ollama serve' exited immediately with code "
                    f"{self._process.returncode}. Another Ollama may already own "
                    f"port 11434."
                )
            time.sleep(0.5)

        raise OllamaError(f"Ollama did not become reachable within {deadline_s:.0f}s")

    def models(self) -> list[str]:
        """Names of locally available models."""
        response = httpx.get(f"{self.host}/api/tags", timeout=30)
        response.raise_for_status()
        return [m["name"] for m in response.json().get("models", [])]

    def stop(self, grace_s: float = 10.0) -> None:
        """Stop the server, unless the provider was already running it."""
        if self._adopted or self._process is None:
            return
        if self._process.poll() is not None:
            return
        self._process.terminate()
        try:
            self._process.wait(timeout=grace_s)
        except subprocess.TimeoutExpired:
            self._process.kill()
        self._process = None
