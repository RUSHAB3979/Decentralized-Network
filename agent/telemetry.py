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
import os
import platform
import socket
import subprocess
import shutil
from dataclasses import asdict, dataclass, field

import httpx

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


def detect_gpu() -> Gpu | None:
    """Live GPU state from nvidia-smi. None means no NVIDIA GPU, not a failure."""
    if shutil.which("nvidia-smi") is None:
        return None
    try:
        out = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.used,utilization.gpu,"
                "temperature.gpu,driver_version",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
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
    )


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

    version: str | None = None
    binary = find_binary()
    if binary is not None:
        try:
            version = subprocess.run(
                [str(binary), "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            ).stdout.strip() or None
        except (subprocess.SubprocessError, OSError):
            version = None

    return Ollama(reachable=True, version=version, available=available, loaded=loaded)


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
