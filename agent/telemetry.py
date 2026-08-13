"""One snapshot of everything a provider dashboard needs to render.

Deliberately knows nothing about any GUI toolkit. It returns dataclasses and a
plain dict, so the same function feeds the tray tooltip, the desktop window,
and eventually a heartbeat payload to the orchestrator without any of them
learning about each other.

Every field that depends on hardware or a running service is Optional, and
absence is a normal outcome rather than an error. A machine with no NVIDIA GPU
is not a broken machine, it is a machine we cannot rent out - and the UI has to
be able to say that calmly instead of showing a traceback.
"""

from __future__ import annotations

import ctypes
import functools
import os
import platform
import socket
import subprocess
import shutil
from dataclasses import asdict, dataclass, field

import httpx

from agent import winproc
from agent.runtime.ollama import DEFAULT_HOST, find_binary
from agent.state import ProviderState


@dataclass
class Host:
    hostname: str
    os_version: str
    cpu: str
    logical_cores: int
    ram_total_mb: int | None


@dataclass
class Gpu:
    name: str
    vram_total_mb: int | None
    vram_used_mb: int | None
    utilisation_pct: int | None
    temperature_c: int | None
    driver: str | None


@dataclass
class Model:
    name: str
    size_mb: int | None
    # True for Ollama Cloud entries, which appear in /api/tags exactly like
    # local models but are ~400-byte pointers to ollama.com. Recorded as a
    # fact from the API rather than inferred from the size, because "small
    # file" and "not actually on this disk" are different claims and only the
    # second one is safe to make.
    remote: bool = False


@dataclass
class Ollama:
    reachable: bool
    version: str | None = None
    available: list[Model] = field(default_factory=list)
    loaded: list[Model] = field(default_factory=list)


@dataclass
class Node:
    status: str
    detail: str
    accepts_work: bool


@dataclass
class Telemetry:
    host: Host
    gpu: Gpu | None
    ollama: Ollama
    node: Node

    @property
    def rentable(self) -> bool:
        """Whether this machine could actually serve paid work right now.

        A GPU alone is not enough and a running Ollama alone is not enough.
        The dashboard needs one honest answer to 'can I earn money on this
        box', and computing it here keeps every surface agreeing on it.
        """
        return self.gpu is not None and self.ollama.reachable


def _ram_total_mb() -> int | None:
    """Total physical memory via GlobalMemoryStatusEx. Windows only, by design."""

    class MemoryStatusEx(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    try:
        status = MemoryStatusEx()
        status.dwLength = ctypes.sizeof(MemoryStatusEx)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return None
        return int(status.ullTotalPhys // (1024 * 1024))
    except (AttributeError, OSError):
        # Not Windows, or the call is unavailable. Not worth failing a whole
        # snapshot over a memory figure.
        return None


def detect_host() -> Host:
    return Host(
        hostname=socket.gethostname(),
        os_version=f"{platform.system()} {platform.release()} ({platform.version()})",
        # platform.processor() is empty on some Windows builds; the environment
        # variable is the more reliable of the two, so prefer it.
        cpu=os.environ.get("PROCESSOR_IDENTIFIER") or platform.processor() or "unknown",
        logical_cores=os.cpu_count() or 0,
        ram_total_mb=_ram_total_mb(),
    )


def _nvidia_smi() -> str | None:
    """Absolute path to nvidia-smi, or None if it is not on this machine.

    PATH alone is not enough, and assuming it was cost us a real provider.
    Current driver packages install nvidia-smi into System32, which is always
    on PATH; older ones install it only under Program Files\\NVIDIA
    Corporation\\NVSMI, which is not. A machine with a working GPU can
    therefore be running a tool we simply fail to find, and reporting that as
    "no NVIDIA GPU" tells the provider to fix hardware that was never broken.

    Verified on a GeForce RTX 3050 laptop, 2026-08-13: the GPU and driver were
    both present and the card was absent from the dashboard purely because
    nvidia-smi was not on PATH.

    Paths are built from the environment rather than hardcoded to C:, because
    a wrong absolute path fails exactly the way a missing file does - silently.
    """
    found = shutil.which("nvidia-smi")
    if found:
        return found

    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    for candidate in (
        os.path.join(program_files, "NVIDIA Corporation", "NVSMI", "nvidia-smi.exe"),
        os.path.join(system_root, "System32", "nvidia-smi.exe"),
    ):
        if os.path.isfile(candidate):
            return candidate
    return None


def detect_gpu() -> Gpu | None:
    """Live GPU state from nvidia-smi.

    None means we could not read a GPU - either because there is none, or
    because the tooling that reads it could not be found or run. Those are
    different facts and only the first is a property of the hardware, so treat
    None as "not rentable right now", never as proof the machine has no card.
    """
    binary = _nvidia_smi()
    if binary is None:
        return None
    try:
        out = winproc.run(
            [
                binary,
                "--query-gpu=name,memory.total,memory.used,utilization.gpu,"
                "temperature.gpu,driver_version",
                "--format=csv,noheader,nounits",
            ],
            timeout=15,
            check=True,
        ).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return None
    if not out:
        return None

    parts = [p.strip() for p in out.splitlines()[0].split(",")]
    if len(parts) < 6:
        return None

    def as_int(value: str) -> int | None:
        # nvidia-smi prints '[N/A]' for fields a given card does not report,
        # which is common for temperature on laptop and virtualised GPUs.
        try:
            return int(value)
        except ValueError:
            return None

    return Gpu(
        name=parts[0],
        vram_total_mb=as_int(parts[1]),
        vram_used_mb=as_int(parts[2]),
        utilisation_pct=as_int(parts[3]),
        temperature_c=as_int(parts[4]),
        driver=parts[5] or None,
    )


def _model(entry: dict) -> Model:
    size = entry.get("size")
    return Model(
        name=entry.get("name") or entry.get("model") or "unknown",
        size_mb=int(size // (1024 * 1024)) if isinstance(size, int) else None,
        # Ollama adds `remote_host` and `remote_model` to cloud entries and
        # omits them entirely for local ones. Verified against /api/tags:
        # qwen2.5:0.5b has neither key, qwen3-vl:235b-cloud has both.
        remote=bool(entry.get("remote_host")),
    )


@functools.lru_cache(maxsize=1)
def _ollama_version() -> str | None:
    """The installed Ollama version, resolved once per process.

    Cached because the dashboard polls telemetry every few seconds and this is
    the only part of a snapshot that cannot change while the app is running.
    Spawning a process on that interval to re-read a constant is waste that
    shows up as real cost on a provider's machine, and it was also how a
    console window ended up flashing on screen every three seconds.

    The trade is that upgrading Ollama underneath a running app reports the old
    version until restart. That is acceptable for a display field; it must not
    be reused for anything that gates behaviour on a version number.
    """
    binary = find_binary()
    if binary is None:
        return None
    try:
        out = winproc.run([str(binary), "--version"], timeout=10).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return None
    if not out:
        return None
    # `ollama --version` prints the sentence "ollama version is 0.32.8", not a
    # version. This field is stored in the orchestrator as `ollama_version` and
    # rendered on the provider list, so the sentence has to be reduced to the
    # thing the field claims to hold. The last whitespace-separated token is
    # taken rather than a regex over the whole line, so an unexpected future
    # wording degrades to "shows something odd" rather than to None.
    return out.split()[-1]


def detect_ollama(host: str = DEFAULT_HOST) -> Ollama:
    try:
        tags = httpx.get(f"{host}/api/tags", timeout=5)
        tags.raise_for_status()
    except (httpx.RequestError, httpx.HTTPStatusError):
        return Ollama(reachable=False)

    available = [_model(m) for m in tags.json().get("models", [])]

    # /api/ps reports what is resident in VRAM right now, which is a different
    # question from what is downloaded. A provider with ten models pulled and
    # none loaded is idle, and the dashboard must not imply otherwise.
    loaded: list[Model] = []
    try:
        running = httpx.get(f"{host}/api/ps", timeout=5)
        running.raise_for_status()
        loaded = [_model(m) for m in running.json().get("models", [])]
    except (httpx.RequestError, httpx.HTTPStatusError, ValueError):
        pass

    return Ollama(
        reachable=True, version=_ollama_version(), available=available, loaded=loaded
    )


def snapshot(state: ProviderState, host: str = DEFAULT_HOST) -> Telemetry:
    """Everything the dashboard renders, gathered once."""
    status = state.status
    return Telemetry(
        host=detect_host(),
        gpu=detect_gpu(),
        ollama=detect_ollama(host),
        node=Node(
            status=status.value,
            detail=state.detail,
            accepts_work=status.accepts_work,
        ),
    )


def to_dict(telemetry: Telemetry) -> dict:
    """JSON-serialisable form, for sending across a GUI bridge."""
    payload = asdict(telemetry)
    payload["rentable"] = telemetry.rentable
    return payload
