"""Standalone NVML telemetry spike.

This is an experiment, not product code. It answers one question:

    What GPU facts can we read on a real provider machine, how expensive is
    one read, and what fails cleanly on machines that do not have NVIDIA
    hardware?

It deliberately uses only the standard library. If `pynvml` is already
installed, the script will try it first because it gives the richest read; if
not, it falls back to `nvidia-smi`, which is the cheapest supported path on a
provider machine. Nothing here is meant to land in `agent/`.

Usage:
    python docs/spikes/nvml-telemetry.py

Output:
    - Human-readable summary on stdout
    - Optional JSON report when --json is supplied
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Sample:
    method: str
    duration_ms: float
    ok: bool
    details: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass
class Report:
    platform: str
    python: str
    gpu_present: bool
    nvidia_smi: bool
    pynvml: bool
    samples: list[Sample]


def has_pynvml() -> bool:
    return importlib.util.find_spec("pynvml") is not None


def has_nvidia_smi() -> bool:
    return shutil.which("nvidia-smi") is not None


def _try_int(value: str | None) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text == "[N/A]":
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def _try_float(value: str | None) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text == "[N/A]":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def sample_with_nvidia_smi() -> Sample:
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.used,utilization.gpu,"
                "temperature.gpu,power.draw,fan.speed,driver_version",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        line = proc.stdout.strip().splitlines()[0]
        parts = [p.strip() for p in line.split(",")]
        details = {
            "name": parts[0] if len(parts) > 0 else None,
            "memory_total_mb": _try_int(parts[1]) if len(parts) > 1 else None,
            "memory_used_mb": _try_int(parts[2]) if len(parts) > 2 else None,
            "utilisation_pct": _try_int(parts[3]) if len(parts) > 3 else None,
            "temperature_c": _try_int(parts[4]) if len(parts) > 4 else None,
            "power_draw_w": _try_float(parts[5]) if len(parts) > 5 else None,
            "fan_speed_pct": _try_int(parts[6]) if len(parts) > 6 else None,
            "driver_version": parts[7] if len(parts) > 7 else None,
            "encoder_sessions": None,
            "source": "nvidia-smi",
        }
        return Sample(
            method="nvidia-smi",
            duration_ms=(time.perf_counter() - started) * 1000,
            ok=True,
            details=details,
        )
    except Exception as exc:  # pragma: no cover - spike needs broad capture
        return Sample(
            method="nvidia-smi",
            duration_ms=(time.perf_counter() - started) * 1000,
            ok=False,
            error=f"{exc.__class__.__name__}: {exc}",
        )


def sample_with_pynvml() -> Sample:
    started = time.perf_counter()
    try:
        import pynvml  # type: ignore

        pynvml.nvmlInit()
        try:
            count = pynvml.nvmlDeviceGetCount()
            handles = [pynvml.nvmlDeviceGetHandleByIndex(i) for i in range(count)]
            if not handles:
                raise RuntimeError("pynvml loaded but no GPU handles were returned")

            h = handles[0]
            name = pynvml.nvmlDeviceGetName(h)
            mem = pynvml.nvmlDeviceGetMemoryInfo(h)
            util = pynvml.nvmlDeviceGetUtilizationRates(h)
            temp = pynvml.nvmlDeviceGetTemperature(
                h, pynvml.NVML_TEMPERATURE_GPU
            )
            driver = pynvml.nvmlSystemGetDriverVersion()

            encoder_sessions = None
            try:
                info = pynvml.nvmlDeviceGetEncoderUtilization(h)
                encoder_sessions = {
                    "utilisation_pct": info[0],
                    "sampling_period_ms": info[1],
                }
            except Exception:
                encoder_sessions = None

            details = {
                "name": name.decode() if isinstance(name, bytes) else str(name),
                "memory_total_mb": int(mem.total // (1024 * 1024)),
                "memory_used_mb": int(mem.used // (1024 * 1024)),
                "utilisation_pct": int(util.gpu),
                "temperature_c": int(temp),
                "power_draw_w": None,
                "fan_speed_pct": None,
                "driver_version": driver.decode()
                if isinstance(driver, bytes)
                else str(driver),
                "encoder_sessions": encoder_sessions,
                "source": "pynvml",
            }
            return Sample(
                method="pynvml",
                duration_ms=(time.perf_counter() - started) * 1000,
                ok=True,
                details=details,
            )
        finally:
            pynvml.nvmlShutdown()
    except Exception as exc:  # pragma: no cover - spike needs broad capture
        return Sample(
            method="pynvml",
            duration_ms=(time.perf_counter() - started) * 1000,
            ok=False,
            error=f"{exc.__class__.__name__}: {exc}",
        )


def detect_gpu_presence() -> bool:
    if not has_nvidia_smi():
        return False
    try:
        proc = subprocess.run(
            ["nvidia-smi", "-L"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        return bool(proc.stdout.strip())
    except Exception:
        return False


def summarize(report: Report) -> None:
    print("# NVML telemetry spike")
    print(f"platform          : {report.platform}")
    print(f"python            : {report.python}")
    print(f"nvidia-smi present: {report.nvidia_smi}")
    print(f"pynvml present    : {report.pynvml}")
    print(f"gpu present       : {report.gpu_present}")
    print()

    for sample in report.samples:
        status = "ok" if sample.ok else "failed"
        print(f"method            : {sample.method} ({status})")
        print(f"read time         : {sample.duration_ms:.2f} ms")
        if sample.ok:
            for key, value in sample.details.items():
                print(f"  {key:18}: {value}")
        else:
            print(f"error             : {sample.error}")
        print()

    if not report.gpu_present:
        print("conclusion        : no NVIDIA GPU was detected on this machine.")
        print(
            "                   This is a valid provider-lab result, but it does "
            "not"
        )
        print(
            "                   answer the real hardware questions from the spike."
        )
        print(
            "                   Re-run this script on a box with an NVIDIA GPU "
            "to fill"
        )
        print(
            "                   in the metric support matrix and the no-admin "
            "answers."
        )


def build_report() -> Report:
    gpu_present = detect_gpu_presence()
    samples: list[Sample] = []

    if has_pynvml():
        samples.append(sample_with_pynvml())

    if has_nvidia_smi():
        samples.append(sample_with_nvidia_smi())

    if not samples:
        samples.append(
            Sample(
                method="none",
                duration_ms=0.0,
                ok=False,
                error="No pynvml module and no nvidia-smi on PATH",
            )
        )

    return Report(
        platform=platform.platform(),
        python=sys.version.replace("\n", " "),
        gpu_present=gpu_present,
        nvidia_smi=has_nvidia_smi(),
        pynvml=has_pynvml(),
        samples=samples,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, help="write the report as JSON")
    args = parser.parse_args()

    report = build_report()
    summarize(report)

    if args.json:
        args.json.write_text(
            json.dumps(
                {
                    **asdict(report),
                    "samples": [asdict(sample) for sample in report.samples],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"wrote JSON report to {args.json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
