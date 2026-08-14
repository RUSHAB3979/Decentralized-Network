"""How the agent decides whether this machine has a GPU worth renting.

These tests exist because of a real incident. On 2026-08-13 a provider machine
with a working GeForce RTX 3050 and a healthy driver reported itself as having
no NVIDIA GPU, and the dashboard told its owner the machine could not serve
paid work. Nothing raised. The card was fine; `nvidia-smi` simply was not on
PATH, and the agent treated "I could not find the tool" as "there is no GPU".

That is the failure shape ADR 0002 cares about most - a wrong answer that looks
like a successful one - so the resolution logic is pinned here rather than left
to be re-derived the next time someone reorganises this module.

No subprocess is spawned and no GPU is required: the filesystem and PATH
lookups are patched, so these run identically on CI's GPU-less Linux runner and
on a provider's desktop.
"""

from __future__ import annotations

import os

import pytest

from agent import telemetry


NVSMI_SUBPATH = os.path.join("NVIDIA Corporation", "NVSMI", "nvidia-smi.exe")


@pytest.fixture
def no_nvidia_smi_anywhere(monkeypatch):
    """A machine with neither the tool on PATH nor any known install."""
    monkeypatch.setattr(telemetry.shutil, "which", lambda _: None)
    monkeypatch.setattr(telemetry.os.path, "isfile", lambda _: False)


def test_path_lookup_wins_when_the_tool_is_on_path(monkeypatch):
    """The common case: current drivers install into System32, which is on PATH."""
    monkeypatch.setattr(
        telemetry.shutil, "which", lambda _: r"C:\Windows\System32\nvidia-smi.exe"
    )
    monkeypatch.setattr(
        telemetry.os.path,
        "isfile",
        lambda _: pytest.fail("fallback paths were checked despite a PATH hit"),
    )

    assert telemetry._nvidia_smi() == r"C:\Windows\System32\nvidia-smi.exe"


def test_falls_back_to_system32_when_path_is_reduced(monkeypatch):
    monkeypatch.setenv("SystemRoot", r"D:\Windows")
    monkeypatch.setattr(telemetry.shutil, "which", lambda _: None)

    expected = os.path.join(r"D:\Windows", "System32", "nvidia-smi.exe")
    monkeypatch.setattr(telemetry.os.path, "isfile", lambda path: path == expected)

    assert telemetry._nvidia_smi() == expected


def test_falls_back_to_the_nvsmi_folder_when_not_on_path(monkeypatch):
    """Older driver packages install nvidia-smi under Program Files."""
    monkeypatch.setenv("ProgramFiles", r"C:\Program Files")
    monkeypatch.setattr(telemetry.shutil, "which", lambda _: None)

    expected = os.path.join(r"C:\Program Files", NVSMI_SUBPATH)
    monkeypatch.setattr(telemetry.os.path, "isfile", lambda path: path == expected)

    assert telemetry._nvidia_smi() == expected


def test_install_paths_come_from_the_environment_not_a_hardcoded_drive(monkeypatch):
    """Windows is not always on C:, and a wrong absolute path fails silently."""
    monkeypatch.setenv("ProgramFiles", r"D:\Programs")
    monkeypatch.setattr(telemetry.shutil, "which", lambda _: None)

    expected = os.path.join(r"D:\Programs", NVSMI_SUBPATH)
    monkeypatch.setattr(telemetry.os.path, "isfile", lambda path: path == expected)

    assert telemetry._nvidia_smi() == expected


def test_returns_none_when_the_tool_is_genuinely_absent(no_nvidia_smi_anywhere):
    """A machine with no NVIDIA tooling at all is a normal outcome, not an error."""
    assert telemetry._nvidia_smi() is None


def test_detect_gpu_is_none_when_the_tool_cannot_be_found(no_nvidia_smi_anywhere):
    assert telemetry.detect_gpu() is None


def test_detect_gpu_invokes_the_resolved_path_not_the_bare_name(monkeypatch):
    """The resolved absolute path must be the command that actually runs."""
    resolved = os.path.join(r"C:\Program Files", NVSMI_SUBPATH)
    monkeypatch.setattr(telemetry, "_nvidia_smi", lambda: resolved)

    seen: list[list[str]] = []

    class Completed:
        stdout = "NVIDIA GeForce RTX 3050 Laptop GPU, 4096, 512, 3, 45, 566.36"

    def fake_run(args, *, timeout, check=False):
        seen.append(args)
        return Completed()

    monkeypatch.setattr(telemetry.winproc, "run", fake_run)

    gpu = telemetry.detect_gpu()

    assert seen, "nvidia-smi was never invoked"
    assert seen[0][0] == resolved
    assert gpu is not None
    assert gpu.name == "NVIDIA GeForce RTX 3050 Laptop GPU"
    assert gpu.vram_total_mb == 4096
    assert gpu.driver == "566.36"


def test_absent_fields_degrade_to_none_rather_than_failing(monkeypatch):
    """nvidia-smi prints '[N/A]' for values a card does not report."""
    monkeypatch.setattr(telemetry, "_nvidia_smi", lambda: "nvidia-smi")

    class Completed:
        stdout = "NVIDIA GeForce RTX 3050 Laptop GPU, 4096, 512, 3, [N/A], 566.36"

    monkeypatch.setattr(
        telemetry.winproc, "run", lambda args, *, timeout, check=False: Completed()
    )

    gpu = telemetry.detect_gpu()

    assert gpu is not None
    assert gpu.temperature_c is None
    assert gpu.vram_total_mb == 4096
