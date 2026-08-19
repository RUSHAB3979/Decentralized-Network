"""Locate Blender and render one claimed frame in a disposable directory.

The orchestrator deliberately gives this module presigned object URLs rather
than storage credentials. Keeping that boundary here matters: a provider only
needs HTTP GET and PUT for the two named objects, and never gains the ability to
list a bucket or read another customer's project.

``--disable-autoexec`` is passed because silently running an embedded script is
the wrong default for batch work. It is not a sandbox. A blend file remains
untrusted input, and the disposable directory below provides cleanup, not
isolation; the real sandbox is still a hand-built task under ADR 0002.
"""

from __future__ import annotations

import math
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import httpx

from agent import winproc
from agent.winproc import CREATE_NO_WINDOW

VERSION_TIMEOUT_S = 10.0
DOWNLOAD_TIMEOUT_S = 600.0
UPLOAD_TIMEOUT_S = 600.0
TREE_KILL_TIMEOUT_S = 15.0

# A scene can legitimately be hundreds of megabytes once textures are packed
# into it. Two GiB leaves room for those projects while still bounding what an
# untrusted Content-Length -- or a response with no Content-Length at all -- can
# consume on a provider's system drive.
MAX_SOURCE_BYTES = 2 * 1024 * 1024 * 1024

# Six hours is intentionally unrelated to worker.RUN_TIMEOUT_S. Its ten-minute
# budget is sized for loading model weights; a path-traced production frame can
# honestly take hours. Six hours admits that work but still stops a wedged
# renderer before it owns the GPU overnight. Operators piloting known heavier
# scenes can raise the bound without rebuilding the desktop app.
DEFAULT_RENDER_TIMEOUT_S = 6 * 60 * 60.0
RENDER_TIMEOUT_ENV = "BLENDER_RENDER_TIMEOUT_S"


class BlenderError(RuntimeError):
    """Blender is unavailable or could not produce the requested frame."""


def _version_sort_key(path: Path) -> tuple[int, ...]:
    match = re.search(r"Blender\s+(\d+(?:\.\d+)*)$", path.parent.name)
    if match is None:
        return ()
    return tuple(int(part) for part in match.group(1).split("."))


def find_binary() -> Path | None:
    """Find Blender without raising when it is not installed."""
    on_path = shutil.which("blender")
    if on_path:
        return Path(on_path)

    # Blender's installer creates one versioned directory per release. An
    # already-open provider app does not see PATH changes made by a later
    # installer, so relying on PATH alone would keep a capable node invisible
    # until its owner happened to restart Windows.
    roots: list[Path] = []
    program_files = os.environ.get("ProgramFiles")
    if program_files:
        roots.append(Path(program_files) / "Blender Foundation")
    roots.append(Path(r"C:\Program Files\Blender Foundation"))

    candidates: list[Path] = []
    for root in roots:
        try:
            candidates.extend(root.glob("Blender */blender.exe"))
        except OSError:
            # Discovery is a capability probe, not startup-critical work. A
            # locked or malformed installation directory means rendering is
            # not advertised; inference must still be allowed to start.
            continue
    for candidate in sorted(set(candidates), key=_version_sort_key, reverse=True):
        if candidate.is_file():
            return candidate

    # Steam's default library is easy to cover without parsing
    # libraryfolders.vdf (whose format and additional-library semantics would
    # turn a small capability probe into a Steam configuration parser).
    steam_roots: list[Path] = []
    program_files_x86 = os.environ.get("ProgramFiles(x86)")
    if program_files_x86:
        steam_roots.append(Path(program_files_x86) / "Steam")
    steam_roots.append(Path(r"C:\Program Files (x86)\Steam"))
    for root in steam_roots:
        candidate = root / "steamapps" / "common" / "Blender" / "blender.exe"
        try:
            if candidate.is_file():
                return candidate
        except OSError:
            continue
    return None


def detect_version(binary: Path) -> str | None:
    """Return Blender's full version, or None when the probe is not trustworthy."""
    try:
        completed = winproc.run(
            [str(binary), "--version"], timeout=VERSION_TIMEOUT_S, check=False
        )
        if completed.returncode != 0:
            return None
        first_line = completed.stdout.splitlines()[0]
        match = re.fullmatch(r"Blender\s+(\d+\.\d+\.\d+)", first_line.strip())
        return match.group(1) if match else None
    except (OSError, subprocess.SubprocessError, IndexError):
        # A guessed version is worse than no rendering capability: it can
        # produce different pixels successfully, leaving no exception or other
        # visible symptom. The worker therefore stays inference-only.
        return None


_PROBE_LOCK = threading.Lock()
_PROBE: tuple[Path | None, str | None] | None = None


def installation(refresh: bool = False) -> tuple[Path | None, str | None]:
    """The Blender on this machine as (binary, version), probed once per process.

    Two callers need this answer and must not disagree about it: the worker,
    which decides whether to ask for a frame at all, and the reporter, which
    tells the orchestrator which version this node can serve. If those two
    diverged -- the reporter advertising 4.3 while the worker holds a 4.2 binary
    -- the node would be handed frames it then rejects one after another, each
    one burning an attempt against a job that was never going to run here.

    Probed once because `blender --version` starts a process, and the reporter
    heartbeats every fifteen seconds for as long as the app is open. `refresh`
    exists for tests and for the case where somebody installs Blender without
    restarting the app; nothing calls it on a timer.
    """
    global _PROBE
    with _PROBE_LOCK:
        if _PROBE is None or refresh:
            binary = find_binary()
            _PROBE = (binary, detect_version(binary) if binary is not None else None)
        return _PROBE


def forget_installation() -> None:
    """Drop the cached probe.

    Exists because the cache is process-wide and therefore leaks between tests:
    whichever test constructs a Worker first would otherwise decide what every
    later test believes about this machine's Blender. Production code has no
    reason to call it -- a provider does not install Blender halfway through a
    render.
    """
    global _PROBE
    with _PROBE_LOCK:
        _PROBE = None


def installed_version() -> str | None:
    """The version string for the heartbeat, or None when Blender is absent.

    None is the honest answer and the safe one: the orchestrator matches a job's
    requested release series against this column, so a node that cannot say what
    it has is simply never matched, rather than being matched on a guess and
    producing different pixels with nothing raising.
    """
    return installation()[1]


def _major_minor(version: str) -> tuple[int, int] | None:
    match = re.fullmatch(r"(\d+)\.(\d+)(?:\.\d+)?", version.strip())
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2))


def _engine_identifier(engine: str, blender_version: str) -> str:
    normalized = engine.strip().lower()
    if normalized == "cycles":
        return "CYCLES"
    if normalized != "eevee":
        raise BlenderError(f"unsupported render engine: {engine!r}")

    version = _major_minor(blender_version)
    if version is None:
        raise BlenderError(f"invalid Blender version: {blender_version!r}")

    # Blender's own RenderEngineType registrations are the source of truth:
    # 4.2 and 4.3 register the rewritten engine as BLENDER_EEVEE_NEXT, while
    # 3.6 registers the legacy engine as BLENDER_EEVEE. Passing the friendly
    # name "eevee" makes Blender reject the flag, and using the old identifier
    # on 4.2+ can leave a scene on its saved engine instead of the claimed one.
    return "BLENDER_EEVEE_NEXT" if version >= (4, 2) else "BLENDER_EEVEE"


def _output_identifier(output_format: str) -> str:
    normalized = output_format.strip().lower()
    if normalized == "png":
        return "PNG"
    if normalized in {"exr", "open_exr"}:
        return "OPEN_EXR"
    raise BlenderError(f"unsupported output format: {output_format!r}")


def _render_timeout_s() -> float:
    configured = os.environ.get(RENDER_TIMEOUT_ENV)
    if configured is None:
        return DEFAULT_RENDER_TIMEOUT_S
    try:
        value = float(configured)
    except ValueError as exc:
        raise BlenderError(f"{RENDER_TIMEOUT_ENV} must be a number") from exc
    if not math.isfinite(value) or value <= 0:
        raise BlenderError(f"{RENDER_TIMEOUT_ENV} must be greater than zero")
    return value


def _kill_process_tree(process: subprocess.Popen[str]) -> None:
    """Stop Blender and children it launched after the render deadline."""
    if os.name == "nt":
        try:
            # Killing only blender.exe can leave renderer or crash-handler
            # children alive with the blend file open. taskkill /T is the
            # Windows primitive that makes the process-tree requirement
            # explicit, and it too gets a deadline so timeout recovery cannot
            # become the next unbounded wait.
            completed = winproc.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                timeout=TREE_KILL_TIMEOUT_S,
                check=False,
            )
            if completed.returncode == 0:
                return
        except (OSError, subprocess.SubprocessError):
            pass
    else:
        try:
            # Popen starts a new session below, so its pid is also the process
            # group id. This catches renderer helpers rather than orphaning
            # them when the parent is killed.
            os.killpg(process.pid, signal.SIGKILL)
            return
        except (OSError, ProcessLookupError):
            pass
    process.kill()


def _remove_work_dir(work_dir: Path) -> None:
    """Delete the working directory without ever masking why the render failed.

    On Windows a file cannot be deleted while any handle to it is open, and the
    handles here belong to a process that was just killed -- Blender itself, or
    a crash handler it spawned. Release is not instantaneous, so the first
    rmtree after a timeout can lose a race it wins a moment later. Hence the
    retries.

    What this must NOT do is raise out of a `finally` while a BlenderError is in
    flight. Doing so replaces "Blender exited with code 1: <the actual reason>"
    with a PermissionError about a temp path -- the diagnosis is destroyed and
    the directory is still there, so the only thing achieved is losing the
    information. When something is already propagating, the leak is reported and
    the original error is allowed through. When nothing is, the failure to clean
    up IS the error and is raised.
    """
    last: OSError | None = None
    for attempt in range(4):
        try:
            shutil.rmtree(work_dir)
            return
        except FileNotFoundError:
            return
        except OSError as exc:
            last = exc
            time.sleep(0.25 * (attempt + 1))

    print(
        f"[blender] WARNING: could not delete {work_dir}: "
        f"{last.__class__.__name__}: {last}. Another customer's scene file is "
        f"still on this disk and must be removed by hand."
    )
    # sys.exc_info() is non-None only while an exception is propagating through
    # the finally that called us. That is the case this guard exists for.
    if sys.exc_info()[0] is None and last is not None:
        raise last


def _file_chunks(path: Path, chunk_size: int = 1024 * 1024) -> Iterator[bytes]:
    with path.open("rb") as source:
        while chunk := source.read(chunk_size):
            yield chunk


def _last_log_line(path: Path, tail_bytes: int = 8192) -> str:
    """Read one diagnostic line without loading a many-hour render log."""
    with path.open("rb") as log:
        log.seek(0, os.SEEK_END)
        log.seek(max(0, log.tell() - tail_bytes))
        tail = log.read().decode("utf-8", errors="replace")
    return next(
        (line.strip() for line in reversed(tail.splitlines()) if line.strip()),
        "no diagnostic output",
    )


# -- the job's source file, downloaded once --------------------------------
#
# One slot, holding the .blend for whichever job this agent is currently
# rendering. One slot is the right size because agent/worker.py runs one job at
# a time by design, so a second entry could only ever be a job that has already
# moved on.
#
# WHY THIS EXISTS. Every frame is claimed independently, and each claim arrives
# with its own presigned GET. Downloading per claim is the obvious reading of
# that contract and it is what this module did: a 500 MB scene rendered over
# 120 frames pulled 60 GB through the provider's connection to render 500 MB of
# input. Nothing failed. The provider paid for the bandwidth, the frames were
# correct, and the only visible symptom was that renders were slow on domestic
# uplinks -- which looks like a slow GPU.
#
# The cache is keyed by job_id and is safe because a job's source is fixed once
# the orchestrator has confirmed the upload: the frames of one job are supposed
# to be renders of identical input, so serving them identical bytes is the
# contract rather than a shortcut around it.
_source_dir: Path | None = None
_source_job_id: str | None = None
_source_path: Path | None = None


def _cached_source(job_id: str) -> Path | None:
    """The .blend already on disk for this job, if there is one.

    Existence is re-checked rather than assumed. Temp directories are cleaned
    by the OS, by disk tools, and by users, and a remembered path that no longer
    resolves would send a missing file to Blender -- which fails with a message
    about the scene rather than about the cache.
    """
    if _source_job_id != job_id or _source_path is None:
        return None
    return _source_path if _source_path.exists() else None


def _source_slot(job_id: str) -> Path:
    """Reserve the cache slot for `job_id` and return where to write its source.

    Taking the slot evicts whatever was in it. That eviction is the point: a
    stranger's scene file must not stay on a provider's disk after their job
    stops being the one this machine is working on.
    """
    global _source_dir, _source_job_id, _source_path

    forget_source_cache()
    _source_dir = Path(tempfile.mkdtemp(prefix="gpu-provider-source-"))
    _source_job_id = job_id
    _source_path = _source_dir / "source.blend"
    return _source_path


def forget_source_cache() -> None:
    """Delete the cached source, if any. Safe to call when there is none.

    Called when the slot is reused, and by the worker on shutdown -- a provider
    closing the app has every right to expect another customer's project not to
    be left on their disk. A failure to delete is reported and not raised: it
    must not be able to take down the worker loop, and the warning names the
    path so it can be removed by hand.
    """
    global _source_dir, _source_job_id, _source_path

    stale = _source_dir
    _source_dir = None
    _source_job_id = None
    _source_path = None
    if stale is None:
        return
    try:
        shutil.rmtree(stale)
    except FileNotFoundError:
        pass
    except OSError as exc:
        print(
            f"[blender] WARNING: could not delete the cached scene at {stale}: "
            f"{exc.__class__.__name__}: {exc}. It must be removed by hand."
        )


def render_frame(
    binary: Path,
    *,
    installed_version: str,
    requested_version: str,
    engine: str,
    output_format: str,
    frame_number: int,
    source_url: str,
    output_url: str,
    job_id: str | None = None,
    storage: httpx.Client | None = None,
) -> tuple[int, float]:
    """Download, render and upload one frame; return bytes and wall-clock seconds.

    `job_id` enables the per-job source cache described above. It is optional so
    that a caller which does not supply one keeps the old behaviour -- a fresh
    download into the disposable directory -- rather than sharing a cache slot
    with an unrelated job under a key of None.
    """
    work_dir = Path(tempfile.mkdtemp(prefix="gpu-provider-blender-"))
    owns_client = storage is None
    active: httpx.Client | None = storage
    try:
        installed = _major_minor(installed_version)
        requested = _major_minor(requested_version)
        if installed is None or requested is None or installed != requested:
            # Patch releases are compatible with a major/minor claim, but a
            # 4.2 binary must never accept a 4.3 frame. The render can complete
            # with different pixels, which is precisely why this is a hard
            # failure rather than a warning.
            raise BlenderError(
                f"claimed Blender {requested_version}, installed {installed_version}"
            )

        engine_id = _engine_identifier(engine, installed_version)
        format_id = _output_identifier(output_format)
        if not isinstance(frame_number, int) or isinstance(frame_number, bool):
            raise BlenderError("frame_number must be an integer")

        active = active or httpx.Client()
        cached = _cached_source(job_id) if job_id else None
        if cached is not None:
            blend_path = cached
            print(
                f"[blender] frame {frame_number} reuses the cached source for "
                f"job {job_id} ({blend_path.stat().st_size} bytes)"
            )
        else:
            # Written to the cache slot when there is a job to key it by, and
            # into the disposable directory otherwise.
            #
            # The cached copy is downloaded under a .part name and renamed only
            # after the last byte lands. A truncated .blend is the one failure
            # this cache could introduce that nothing would catch: it is a real
            # file at the expected path, so the next frame would hand it to
            # Blender and get either a parse error blamed on the customer's
            # scene or, worse, a partially valid file that renders something
            # wrong. Publishing by rename means the cached path either does not
            # exist or is complete.
            blend_path = _source_slot(job_id) if job_id else work_dir / "source.blend"
            partial = (
                blend_path.with_name(blend_path.name + ".part")
                if job_id
                else blend_path
            )
            downloaded = 0
            with active.stream("GET", source_url, timeout=DOWNLOAD_TIMEOUT_S) as response:
                response.raise_for_status()
                content_length = response.headers.get("Content-Length")
                if content_length is not None:
                    try:
                        declared_size = int(content_length)
                    except ValueError as exc:
                        raise BlenderError(
                            "source returned an invalid Content-Length"
                        ) from exc
                    if declared_size < 0 or declared_size > MAX_SOURCE_BYTES:
                        raise BlenderError(
                            f"source exceeds the {MAX_SOURCE_BYTES}-byte download limit"
                        )
                with partial.open("wb") as destination:
                    for chunk in response.iter_bytes():
                        downloaded += len(chunk)
                        if downloaded > MAX_SOURCE_BYTES:
                            raise BlenderError(
                                f"source exceeds the {MAX_SOURCE_BYTES}-byte "
                                "download limit"
                            )
                        destination.write(chunk)
            if partial != blend_path:
                os.replace(partial, blend_path)
            print(
                f"[blender] downloaded frame {frame_number} source "
                f"({downloaded} bytes)"
            )

        output_dir = work_dir / "output"
        output_dir.mkdir()
        output_pattern = output_dir / "frame_####"
        command = [
            str(binary),
            "-b",
            str(blend_path),
            "--disable-autoexec",
            "-E",
            engine_id,
            "-o",
            str(output_pattern),
            "-F",
            format_id,
            "-f",
            str(frame_number),
        ]

        print(f"[blender] rendering frame {frame_number}")
        render_timeout = _render_timeout_s()
        started = time.monotonic()
        log_path = work_dir / "blender.log"
        with log_path.open("w", encoding="utf-8", errors="replace") as log:
            process = subprocess.Popen(
                command,
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=(
                    CREATE_NO_WINDOW
                    | (subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0)
                ),
                start_new_session=os.name != "nt",
            )
            try:
                process.wait(timeout=render_timeout)
            except subprocess.TimeoutExpired as exc:
                _kill_process_tree(process)
                try:
                    process.wait(timeout=TREE_KILL_TIMEOUT_S)
                except subprocess.TimeoutExpired:
                    process.kill()
                    try:
                        process.wait(timeout=TREE_KILL_TIMEOUT_S)
                    except subprocess.TimeoutExpired as stuck:
                        raise BlenderError(
                            f"Blender could not be terminated for frame {frame_number}"
                        ) from stuck
                raise BlenderError(
                    f"frame {frame_number} exceeded the render timeout"
                ) from exc
        render_seconds = max(0.0, time.monotonic() - started)

        # Blender's human-readable progress line is not a stable protocol: its
        # fields differ between Cycles and EEVEE and have changed across the
        # supported releases. There is no progress endpoint in the frame wire
        # contract either, so parsing Sample X/Y would manufacture precision
        # that cannot be reported. These download/render/upload milestones are
        # deliberately coarse and truthful.
        if process.returncode != 0:
            last_line = _last_log_line(log_path)
            raise BlenderError(
                f"Blender exited with code {process.returncode}: {last_line[:500]}"
            )

        outputs = sorted(path for path in output_dir.glob("frame_*") if path.is_file())
        if not outputs:
            # Blender can return zero after loading a file that never writes an
            # artifact. Success is the presence of the promised output, not a
            # process exit convention alone.
            raise BlenderError(f"Blender produced no output for frame {frame_number}")
        if len(outputs) != 1:
            raise BlenderError(f"Blender produced {len(outputs)} outputs for one frame")

        output = outputs[0]
        output_bytes = output.stat().st_size
        upload = active.put(
            output_url,
            content=_file_chunks(output),
            headers={"Content-Length": str(output_bytes)},
            timeout=UPLOAD_TIMEOUT_S,
        )
        upload.raise_for_status()
        print(
            f"[blender] rendered and uploaded frame {frame_number} "
            f"({output_bytes} bytes in {render_seconds:.1f}s)"
        )

        # This wall-clock measurement is evidence about what happened on this
        # machine, not a bill. Trusted metering is hand-built elsewhere and is
        # intentionally still unwritten under ADR 0002.
        return output_bytes, render_seconds
    finally:
        try:
            if owns_client and active is not None:
                active.close()
        finally:
            # Provider disks fill weeks after the job that caused it, so a
            # cleanup failure must be visible now rather than ignored. The
            # finally covers download errors, Blender failures, timeouts,
            # upload errors, and success alike.
            _remove_work_dir(work_dir)
