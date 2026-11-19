"""The render vertical, tested where it can be tested without a database.

Two things are checked here. The first is the derived job status, which is pure
arithmetic over frame counts and is the piece most likely to be quietly wrong:
it is the only place that decides whether a customer sees "running" or "failed",
and every wrong answer it can give looks plausible. The second is the gate --
that an unauthenticated or un-enabled caller is refused *before* anything is
read or written, so the refusal does not depend on the database being up.

What is deliberately NOT here: the claim query. Its correctness is
`FOR UPDATE SKIP LOCKED` behaviour under concurrency, which a test without
Postgres cannot demonstrate and a mock would only pretend to. It is on the
acceptance gate in the plan instead, as the step where the agent is killed
mid-frame and the frame must come back.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from orchestrator import storage
from orchestrator.models import (
    MAX_FRAMES_PER_JOB,
    MAX_JOB_TRANSFER_BYTES,
    MAX_OUTPUT_BYTES,
    MAX_SOURCE_BYTES,
    OUTPUT_MAGIC,
    OUTPUT_MAGIC_BYTES,
)
from orchestrator.main import (
    _derive_job_status,
    _reject_output,
    _require_render_enabled,
    _version_series,
    app,
    job_lease_s,
    max_frame_attempts,
    render_download_ttl_s,
    render_lease_s,
    render_upload_ttl_s,
)

NODE_ID = "a1b2c3d4e5f6a7b8"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with TestClient(app) as c:
        yield c


def counts(total: int, completed: int = 0, failed: int = 0, running: int = 0) -> dict:
    return {
        "total": total,
        "completed": completed,
        "failed": failed,
        "running": running,
    }


# ---------------------------------------------------------------------------
# Derived status.
# ---------------------------------------------------------------------------


def test_a_job_with_every_frame_done_is_completed():
    job = {"status": "queued"}
    assert _derive_job_status(job, counts(24, completed=24)) == "completed"


def test_a_job_is_not_completed_while_one_frame_is_outstanding():
    """The off-by-one that would matter most.

    Reporting `completed` at 23 of 24 hands the customer an animation with a
    hole in it and no indication that anything went wrong. Every other wrong
    answer this function can give is recoverable by waiting; this one is not.
    """
    job = {"status": "queued"}
    assert _derive_job_status(job, counts(24, completed=23, running=1)) != "completed"


def test_a_job_fails_only_when_every_frame_has_stopped():
    """One failed frame among many running is not a failed job.

    A frame fails, is retried, and succeeds. If a single failure marked the
    whole job failed, the frontend would stop polling and the customer would
    abandon a job that was about to finish.
    """
    job = {"status": "queued"}
    assert _derive_job_status(job, counts(24, completed=10, failed=1, running=1)) == "running"
    assert _derive_job_status(job, counts(24, completed=23, failed=1)) == "failed"


def test_a_job_with_no_running_frames_reads_as_queued_not_stalled():
    """Nothing claimed yet is a normal state, not an error.

    During the pilot exactly one machine is eligible to render, so a job can sit
    with zero running frames for a long time with nothing at all wrong.
    """
    job = {"status": "queued"}
    assert _derive_job_status(job, counts(24)) == "queued"


def test_awaiting_upload_and_cancelled_are_facts_about_the_job_not_its_frames():
    """These three are the only states the status column is allowed to hold.

    They are the states that are true of the job itself and invisible in its
    frames: a cancelled job whose frames are all still 'queued' looks identical
    to a waiting one from the frames alone.
    """
    assert _derive_job_status({"status": "awaiting_upload"}, counts(0)) == "awaiting_upload"
    assert _derive_job_status({"status": "cancelled"}, counts(24, completed=5)) == "cancelled"


def test_cancellation_outranks_completion():
    # A job cancelled after its last frame landed still reads as cancelled --
    # what the customer asked for is the more useful thing to show them.
    assert _derive_job_status({"status": "cancelled"}, counts(24, completed=24)) == "cancelled"


# ---------------------------------------------------------------------------
# The gate.
# ---------------------------------------------------------------------------


def test_a_user_without_the_flag_is_refused():
    """The customer half of the pilot gate.

    `render_enabled` defaults FALSE in the schema, so this is the answer every
    account gets until somebody runs an UPDATE. The message has to say it is
    deliberate, because a 403 with no explanation reads as a fault.
    """
    with pytest.raises(HTTPException) as excinfo:
        _require_render_enabled({"user_id": "u", "render_enabled": False})
    assert excinfo.value.status_code == 403
    assert "sandbox" in excinfo.value.detail

    # A row that predates the column, or a SELECT that forgot it, must fail
    # closed rather than reading as permission.
    with pytest.raises(HTTPException):
        _require_render_enabled({"user_id": "u"})

    _require_render_enabled({"user_id": "u", "render_enabled": True})


VALID_JOB = {
    "blender_version": "4.3",
    "engine": "cycles",
    "frame_start": 1,
    "frame_end": 24,
    "output_format": "png",
    "source_bytes": 1024,
}


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("post", "/v1/render/jobs", VALID_JOB),
        ("post", "/v1/render/jobs/abc/upload-url", None),
        ("post", "/v1/render/jobs/abc/uploaded", None),
        ("get", "/v1/render/jobs", None),
        ("get", "/v1/render/jobs/abc", None),
        ("get", "/v1/render/jobs/abc/artifacts", None),
        ("delete", "/v1/render/jobs/abc", None),
    ],
)
def test_customer_endpoints_refuse_an_anonymous_caller_before_storage(client, method, path, body):
    """401, never 503.

    With no database and no bucket configured, an endpoint that checked
    authentication late would answer 503 and tell an anonymous caller that the
    service merely happens to be down right now. The refusal must not depend on
    any backing service being reachable.

    The create request carries a VALID body on purpose: a 422 would also not be
    a 503, and would let a genuine ordering bug through unnoticed.
    """
    kwargs = {"json": body} if body is not None else {}
    response = getattr(client, method)(path, **kwargs)
    assert response.status_code == 401


@pytest.mark.parametrize(
    "path",
    [
        "/providers/render/claim?node_id=" + NODE_ID,
        "/providers/render/frames/f1/result?node_id=" + NODE_ID,
    ],
)
def test_provider_endpoints_refuse_a_missing_credential_before_storage(client, path):
    response = client.post(path, json={"status": "completed"})
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Configuration that has to hold together.
# ---------------------------------------------------------------------------


def test_the_render_lease_is_sized_for_a_render_not_a_prompt():
    """The number that costs money when it is wrong.

    Too short and a frame still being rendered is handed to a second provider,
    which produces the same image twice and owes two people for one result.
    JOB_LEASE_SEC is 180 because a chat reply is quick; a Cycles frame at
    production sample counts is not, and copying that constant across would have
    been the easy mistake.
    """
    assert render_lease_s() >= 10 * job_lease_s()
    assert render_lease_s() >= 600


def test_the_upload_window_outlives_a_large_file_on_a_domestic_connection():
    # A few hundred megabytes at a few megabits up is tens of minutes. A short
    # window fails at ninety percent with an opaque 403.
    assert render_upload_ttl_s() >= 1800


def test_download_links_are_short_lived():
    # Re-issued on every poll of the artifacts endpoint, so there is no reason
    # for one to outlive the page that asked for it.
    assert render_download_ttl_s() <= render_upload_ttl_s()


def test_a_frame_cannot_be_retried_forever():
    """A ceiling has to exist, and has to be small.

    Without one, a frame that reliably crashes Blender is offered to every
    provider in the fleet in turn, forever: each takes it, dies, lets the lease
    lapse, and the next one picks it up. Nothing raises, the job never finishes,
    and everybody burns GPU time on the same poisoned frame.
    """
    assert 1 <= max_frame_attempts() <= 5


def test_the_output_key_matches_what_the_provider_was_told_to_write():
    """The claim hands out a PUT for one key; the result HEADs the same key.

    Both sides derive it from storage.frame_key rather than passing it around,
    so they cannot drift apart. If they did, every completed frame would be
    recorded as `output_missing` -- a failure that looks like a provider fault
    and is not.
    """
    assert storage.frame_key("job", 12, "png") == storage.frame_key("job", 12, "png")
    assert storage.frame_key("job", 12, "png") != storage.frame_key("job", 13, "png")
    assert storage.frame_key("job", 12, "exr").endswith(".exr")


def test_a_point_release_still_renders_the_series_it_belongs_to():
    """The seam that would have failed silently on a fleet that worked.

    The customer picks "4.3" from a dropdown of release series. The provider
    reports what `blender --version` printed, which is "4.3.2". Compared for
    equality those never match, so the claim query would return nothing forever
    and every job would sit `queued` looking like a capacity shortage. Nothing
    would raise; there would be no failed frame to investigate.
    """
    assert _version_series("4.3.2") == _version_series("4.3")
    assert _version_series("3.6.15") == "3.6"


def test_a_different_series_is_still_refused():
    """Strict across series, because that is where the output actually changes.

    The EEVEE engine identifier was renamed between 4.1 and 4.2, and geometry
    node behaviour differs across majors. A 4.2 binary rendering a 4.3 job
    returns an image, exits zero, and is wrong -- which is the whole reason the
    version is matched at all rather than ignored.
    """
    assert _version_series("4.2.1") != _version_series("4.3.0")
    assert _version_series("3.6.15") != _version_series("4.3")


# ---------------------------------------------------------------------------
# Tripwires for the four guards added after the live security review.
#
# These assert on source text, which is a weak form of test and is not
# pretending otherwise: they cannot show that the guard WORKS, only that it is
# still there. That is deliberate. Each guard was verified against real
# Postgres and real S3 end to end -- the live run is the evidence -- and every
# one of them is a clause whose deletion produces no error, no failing request,
# and no symptom until someone is already exploiting it. The main.py comments
# make the same argument for keeping the eligibility check as a branch rather
# than a WHERE clause: silence on removal is the risk being defended against.
# ---------------------------------------------------------------------------

import inspect  # noqa: E402

from orchestrator import main as _main  # noqa: E402


def test_the_claim_re_reads_the_customers_half_of_the_gate():
    """Revocation has to stop the next frame, not just the next submission.

    `_require_render_enabled` runs at submit time, which covers frames that do
    not exist yet. Live-verified before the fix: set render_enabled = FALSE on
    an account whose job was already fanned out and the very next claim still
    handed a provider frame 2. Without this join the column is a filter on new
    jobs wearing the name of a switch that turns the account off.
    """
    sql = inspect.getsource(_main.claim_render_frame)
    assert "JOIN users u ON u.user_id = j.user_id" in sql
    assert "u.render_enabled" in sql


def test_the_head_after_upload_is_compared_and_not_merely_recorded():
    """MAX_SOURCE_BYTES' own comment calls this HEAD the real enforcement.

    It was reading the size and storing it without ever comparing it. Live-
    verified before the fix: a job declaring one byte was confirmed after a
    200 KB upload, and a zero-byte object fanned out into frames that every
    provider in the fleet would have failed on in turn -- each failure looking
    like a fault on that provider's machine rather than on the file. The
    presigned PUT carries no size condition, so this is the only point at which
    the true size is ever known.
    """
    src = inspect.getsource(_main.confirm_render_upload)
    assert "size > MAX_SOURCE_BYTES" in src
    assert "size == 0" in src


def test_artifact_downloads_are_gated_by_ownership_and_not_by_the_pilot_flag():
    """A finished PNG executes nothing, so the gate does not belong here.

    Recorded as a test because the absence of `_require_render_enabled` on this
    one endpoint reads as an oversight next to the three that have it, and the
    next person to notice will otherwise 'fix' it. Adding it would mean
    revoking an account's pilot access also destroys its access to work already
    rendered, which is data loss dressed up as a security control.
    """
    src = inspect.getsource(_main.render_job_artifacts)
    assert "_require_render_enabled" not in src
    assert "DELIBERATELY NOT GATED" in src
    # Ownership is what actually protects this endpoint.
    assert "_load_render_job(cur, job_id, user[\"user_id\"])" in src


# -- what a provider uploaded, as opposed to what it said ------------------


class _FakeBucket:
    """Answers head_prefix from bytes a test chooses. No network, no storage."""

    def __init__(self, prefix: bytes = b"", fail: bool = False) -> None:
        self.prefix = prefix
        self.fail = fail
        self.reads: list[tuple[str, int]] = []

    def head_prefix(self, key: str, length: int, timeout: float = 10.0) -> bytes:
        if self.fail:
            raise storage.StorageError("the bucket did not answer")
        self.reads.append((key, length))
        return self.prefix[:length]


PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16


def test_a_missing_object_is_not_a_finished_frame():
    # The agent reporting 'completed' has proved nothing: a crash between
    # rendering and uploading produces exactly that report with nothing in the
    # bucket.
    assert _reject_output(_FakeBucket(), "renders/j/f.png", None, "png") == (
        "output_missing"
    )


def test_a_zero_byte_upload_is_not_a_finished_frame():
    """The defect that read as correct.

    An empty PUT and a crash between render and upload both leave a zero-byte
    object. The check was `stored is None`, and 0 is falsy but not None, so the
    empty case fell through to success -- completing the job and offering the
    customer nothing at all as their render.
    """
    assert _reject_output(_FakeBucket(), "renders/j/f.png", 0, "png") == "output_empty"


def test_an_absurdly_large_upload_is_refused():
    # The other end of the same claim. The provider chooses how many bytes to
    # PUT, and without a ceiling one frame can fill the bucket.
    assert (
        _reject_output(_FakeBucket(), "renders/j/f.png", MAX_OUTPUT_BYTES + 1, "png")
        == "output_too_large"
    )


def test_a_png_that_is_actually_a_png_is_accepted():
    bucket = _FakeBucket(prefix=PNG)
    assert _reject_output(bucket, "renders/j/f.png", 4096, "png") is None
    # One ranged read of a fixed prefix, not a download of the frame.
    assert bucket.reads == [("renders/j/f.png", OUTPUT_MAGIC_BYTES)]


def test_arbitrary_content_is_not_a_png_however_it_is_named():
    """A provider could PUT "this is not a png" and collect the frame.

    The customer would then download exactly those bytes under a .png key. The
    magic number costs one sixteen-byte ranged GET against an object we already
    had to HEAD, and it closes the cheapest version of the attack completely.
    """
    bucket = _FakeBucket(prefix=b"this is not a png")
    assert (
        _reject_output(bucket, "renders/j/f.png", 4096, "png") == "output_not_png"
    )


def test_an_exr_is_accepted_in_either_byte_order():
    # OpenEXR's magic is written little-endian on almost everything and
    # big-endian on the rest. Refusing one of them would fail every frame of a
    # legitimate job on hardware nobody tested on.
    for magic in OUTPUT_MAGIC["exr"]:
        bucket = _FakeBucket(prefix=magic + b"\x00" * 16)
        assert _reject_output(bucket, "renders/j/f.exr", 4096, "exr") is None


def test_a_format_with_no_recorded_signature_is_accepted():
    """Our own omission must not fail a legitimate customer's job.

    A job can only be created with a format models.py allows, so reaching here
    means the magic table is behind the enum. Failing every frame over that
    would be the worse error, and it would look like a provider fault.
    """
    assert _reject_output(_FakeBucket(), "renders/j/f.tiff", 4096, "tiff") is None


def test_a_bucket_that_cannot_answer_is_not_evidence_against_the_provider():
    """A storage outage must not be recorded as a bad render.

    Marking the frame failed would burn an attempt and, at the retry ceiling,
    fail the customer's job because of our own dependency. Raising leaves the
    frame to its lease, which is the path that already handles "we do not know".
    """
    with pytest.raises(storage.StorageError):
        _reject_output(_FakeBucket(fail=True), "renders/j/f.png", 4096, "png")


# -- the product of two limits ---------------------------------------------


def test_the_transfer_budget_is_smaller_than_the_two_limits_multiplied_out():
    """The limit nobody wrote down.

    A provider re-downloads the .blend for every frame it renders, so a job's
    real cost in bandwidth is source size times frame count. The 2 GiB source
    ceiling and the 2,000 frame ceiling are each defensible alone and multiply
    out to roughly four terabytes of somebody else's bandwidth from a single
    submission -- before a single retry.
    """
    assert MAX_JOB_TRANSFER_BYTES < MAX_SOURCE_BYTES * MAX_FRAMES_PER_JOB


def test_the_budget_still_admits_an_ordinary_animation():
    # A limit that refuses real work gets raised in a hurry by whoever hits it,
    # so it has to leave room for the jobs this marketplace exists to run: a
    # 250 MB scene over a 240-frame shot.
    assert 250 * 1024 * 1024 * 240 < MAX_JOB_TRANSFER_BYTES
