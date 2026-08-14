from __future__ import annotations

import subprocess

from agent import telemetry


def test_nvidia_smi_is_found_in_system32_when_path_is_reduced(
    monkeypatch, tmp_path
):
    binary = tmp_path / "System32" / "nvidia-smi.exe"
    binary.parent.mkdir()
    binary.touch()
    monkeypatch.setattr(telemetry.shutil, "which", lambda _: None)
    monkeypatch.setenv("SystemRoot", str(tmp_path))

    assert telemetry._find_nvidia_smi() == binary


def test_detect_gpu_parses_nvidia_smi_output(monkeypatch, tmp_path):
    binary = tmp_path / "nvidia-smi.exe"
    binary.touch()
    monkeypatch.setattr(telemetry, "_find_nvidia_smi", lambda: binary)
    monkeypatch.setattr(
        telemetry.winproc,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="NVIDIA GeForce RTX 3050 Laptop GPU, 4096, 512, 27, 62, 592.82\n",
            stderr="",
        ),
    )

    gpu = telemetry.detect_gpu()

    assert gpu is not None
    assert gpu.name == "NVIDIA GeForce RTX 3050 Laptop GPU"
    assert gpu.vram_total_mb == 4096
    assert gpu.utilisation_pct == 27
    assert gpu.temperature_c == 62
