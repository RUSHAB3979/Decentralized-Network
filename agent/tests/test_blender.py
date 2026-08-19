"""The provider-side boundary around Blender and customer-owned scene files.

No test here requires Blender or object storage. The subprocess is fake and
httpx.MockTransport stands in for presigned GET and PUT, which keeps failure
cleanup testable on the same machines where the real renderer is absent.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from agent.runtime import blender


class _Process:
    """A completed Blender process whose output behavior a test can choose."""

    pid = 4321

    def __init__(self, returncode: int, output: Path | None = None) -> None:
        self.returncode = returncode
        self.output = output

    def wait(self, timeout):
        if self.output is not None:
            self.output.write_bytes(b"rendered pixels")
        return self.returncode


def _storage(request: httpx.Request) -> httpx.Response:
    if request.method == "GET":
        return httpx.Response(200, content=b"fake blend contents")
    return httpx.Response(200)


def _render(storage: httpx.Client) -> tuple[int, float]:
    return blender.render_frame(
        Path("blender.exe"),
        installed_version="4.3.2",
        requested_version="4.3",
        engine="cycles",
        output_format="png",
        frame_number=12,
        source_url="https://storage.invalid/source.blend",
        output_url="https://storage.invalid/frame.png",
        storage=storage,
    )


def test_failed_render_always_removes_its_working_directory(tmp_path, monkeypatch):
    work_dir = tmp_path / "render-work"

    def make_work_dir(prefix):
        work_dir.mkdir()
        return str(work_dir)

    monkeypatch.setattr(blender.tempfile, "mkdtemp", make_work_dir)
    monkeypatch.setattr(
        blender.subprocess,
        "Popen",
        lambda *args, **kwargs: _Process(returncode=2),
    )

    with httpx.Client(transport=httpx.MockTransport(_storage)) as storage:
        with pytest.raises(blender.BlenderError, match="exited with code 2"):
            _render(storage)

    # Scene files can contain packed assets and quietly exhaust the provider's
    # disk over many failed jobs. Cleanup after success alone would miss the
    # path most likely to accumulate them.
    assert not work_dir.exists()


def test_zero_exit_without_an_output_is_a_render_failure(monkeypatch):
    monkeypatch.setattr(
        blender.subprocess,
        "Popen",
        lambda *args, **kwargs: _Process(returncode=0),
    )

    with httpx.Client(transport=httpx.MockTransport(_storage)) as storage:
        with pytest.raises(blender.BlenderError, match="produced no output"):
            _render(storage)


def test_render_command_is_ordered_before_the_final_frame_action(monkeypatch):
    captured = {}

    def popen(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        pattern = args[args.index("-o") + 1]
        output = Path(pattern.replace("####", "0012") + ".png")
        return _Process(returncode=0, output=output)

    uploaded = {}

    def storage_handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, content=b"fake blend contents")
        uploaded["content"] = request.read()
        return httpx.Response(200)

    monkeypatch.setattr(blender.subprocess, "Popen", popen)

    with httpx.Client(transport=httpx.MockTransport(storage_handler)) as storage:
        output_bytes, render_seconds = blender.render_frame(
            Path("blender.exe"),
            installed_version="4.3.2",
            requested_version="4.3",
            engine="eevee",
            output_format="png",
            frame_number=12,
            source_url="https://storage.invalid/source.blend",
            output_url="https://storage.invalid/frame.png",
            storage=storage,
        )

    args = captured["args"]
    assert args[1] == "-b"
    assert args[args.index("-E") + 1] == "BLENDER_EEVEE_NEXT"
    assert args[args.index("-F") + 1] == "PNG"
    # Blender executes while parsing. Any option after this pair is too late to
    # affect the render even though the process still returns successfully.
    assert args[-2:] == ["-f", "12"]
    assert "creationflags" in captured["kwargs"]
    assert uploaded["content"] == b"rendered pixels"
    assert output_bytes == len(b"rendered pixels")
    assert render_seconds >= 0


@pytest.mark.parametrize(
    "version, expected",
    [
        ("3.6.23", "BLENDER_EEVEE"),
        ("4.2.0", "BLENDER_EEVEE_NEXT"),
        ("4.3.2", "BLENDER_EEVEE_NEXT"),
    ],
)
def test_eevee_identifier_tracks_the_blender_release(version, expected):
    assert blender._engine_identifier("eevee", version) == expected


def _successful_popen(args, **kwargs):
    """Popen stand-in that writes the frame Blender was asked to produce."""
    pattern = args[args.index("-o") + 1]
    return _Process(returncode=0, output=Path(pattern.replace("####", "0012") + ".png"))


def _render_for_job(storage: httpx.Client, job_id: str | None) -> tuple[int, float]:
    return blender.render_frame(
        Path("blender.exe"),
        installed_version="4.3.2",
        requested_version="4.3",
        engine="cycles",
        output_format="png",
        frame_number=12,
        source_url="https://storage.invalid/source.blend",
        output_url="https://storage.invalid/frame.png",
        job_id=job_id,
        storage=storage,
    )


def test_frames_of_one_job_download_the_scene_once(monkeypatch):
    """The whole point of the cache.

    Every frame is claimed separately and arrives with its own presigned GET,
    so downloading per claim looks correct and is what this module used to do.
    On a 120-frame animation of a 500 MB scene it pulled 60 GB through the
    provider's connection to render 500 MB of input -- with nothing failing and
    no symptom except renders being slow on a domestic uplink.
    """
    downloads = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            downloads.append(str(request.url))
            return httpx.Response(200, content=b"fake blend contents")
        return httpx.Response(200)

    monkeypatch.setattr(blender.subprocess, "Popen", _successful_popen)

    with httpx.Client(transport=httpx.MockTransport(handler)) as storage:
        _render_for_job(storage, "job-a")
        _render_for_job(storage, "job-a")
        _render_for_job(storage, "job-a")

    assert len(downloads) == 1


def test_a_different_job_is_downloaded_and_evicts_the_previous_scene(monkeypatch):
    """One slot, because the worker runs one job at a time.

    The eviction matters for more than disk space: the cached file is another
    customer's project sitting on a provider's machine, and it must not outlive
    the job this machine is working on.
    """
    downloads = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            downloads.append(str(request.url))
            return httpx.Response(200, content=b"fake blend contents")
        return httpx.Response(200)

    monkeypatch.setattr(blender.subprocess, "Popen", _successful_popen)

    with httpx.Client(transport=httpx.MockTransport(handler)) as storage:
        _render_for_job(storage, "job-a")
        first = blender._source_path
        assert first is not None and first.exists()

        _render_for_job(storage, "job-b")
        assert len(downloads) == 2
        assert not first.exists(), "the previous customer's scene was left on disk"

    blender.forget_source_cache()
    assert blender._source_path is None


def test_a_download_that_fails_leaves_nothing_to_reuse(monkeypatch):
    """A truncated .blend is the one failure this cache could introduce.

    It would be a real file at the expected path, so the next frame would hand
    it to Blender and get either a parse error blamed on the customer's scene
    or a partially valid file that renders something subtly wrong. The cached
    path is published by rename, so it either does not exist or is complete.
    """
    attempts = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            attempts.append(str(request.url))
            if len(attempts) == 1:
                return httpx.Response(500, content=b"")
            return httpx.Response(200, content=b"fake blend contents")
        return httpx.Response(200)

    monkeypatch.setattr(blender.subprocess, "Popen", _successful_popen)

    with httpx.Client(transport=httpx.MockTransport(handler)) as storage:
        with pytest.raises(httpx.HTTPStatusError):
            _render_for_job(storage, "job-a")
        assert blender._cached_source("job-a") is None
        _render_for_job(storage, "job-a")

    assert len(attempts) == 2


def test_without_a_job_id_nothing_is_cached(monkeypatch):
    """The default is unchanged behaviour.

    A caller with no job to key by must get a fresh download into the
    disposable directory rather than sharing one cache slot with an unrelated
    job under a key of None.
    """
    downloads = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            downloads.append(str(request.url))
            return httpx.Response(200, content=b"fake blend contents")
        return httpx.Response(200)

    monkeypatch.setattr(blender.subprocess, "Popen", _successful_popen)

    with httpx.Client(transport=httpx.MockTransport(handler)) as storage:
        _render_for_job(storage, None)
        _render_for_job(storage, None)

    assert len(downloads) == 2
    assert blender._source_path is None
