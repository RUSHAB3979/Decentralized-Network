"""Checks on the presigning in orchestrator/storage.py.

The first test is the one that matters. A signing implementation that is only
exercised through the application's own code proves nothing: it will happily
agree with itself while producing a signature the bucket rejects, and the
symptom at that point is an opaque 403 on a customer's upload with nothing in
any log saying which byte was wrong.

So the expected value below did not come from this codebase. It was produced by
botocore's own S3 presigner -- `botocore.auth.S3SigV4QueryAuth`, the code path
boto3 uses for `generate_presigned_url` -- run against the inputs recorded here.
storage.py was checked against it for GET, PUT and HEAD, path-style addressing,
a key containing `~`, and a secret containing `/` and `+`, and matched
byte-for-byte in every case. This test freezes one of those comparisons so that
a later "tidy-up" of the encoding or the header ordering goes red immediately
rather than in production.

Reproducing it needs botocore, which is deliberately NOT a dependency of this
project -- fifty megabytes to produce a string, on a 512 MB instance. The
reproduction script is therefore not committed; the inputs below are complete
enough to rebuild it in a throwaway environment.

Note the `use S3SigV4QueryAuth, not SigV4QueryAuth` detail, because it cost
time: the generic SigV4 signer hashes the (empty) body, while the S3 signer
uses the literal UNSIGNED-PAYLOAD. Comparing against the wrong one produces a
mismatch on every case with an identical query string, which looks like a bug
in the encoding and is not.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from orchestrator import storage


# AWS's published example credentials. They appear verbatim in public
# documentation and grant access to nothing.
EXAMPLE_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"
EXAMPLE_SECRET_KEY = "wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY"

# Produced by botocore 1.43.73, S3SigV4QueryAuth, for the exact call below.
BOTOCORE_SIGNATURE = "2c2b07ce87f9e48109e1e6e9c84d4448da2b0116be39d08c2ac8afb950ac1675"


def test_matches_botocores_s3_presigner():
    url = storage.presign(
        method="GET",
        host="examplebucket.s3.amazonaws.com",
        canonical_uri="/test.txt",
        region="us-east-1",
        access_key=EXAMPLE_ACCESS_KEY,
        secret_key=EXAMPLE_SECRET_KEY,
        expires_in=86400,
        now=datetime(2026, 8, 18, 12, 7, 59, tzinfo=timezone.utc),
    )
    assert f"X-Amz-Signature={BOTOCORE_SIGNATURE}" in url


def test_signature_changes_with_the_object_key():
    """A URL for one object must not authorise another.

    This is the property the whole design rests on: a provider is handed a URL
    for one .blend and one output, and that is the entire extent of its access
    to the bucket. If the signature did not cover the path, it could walk to
    any other customer's project.
    """
    common = dict(
        method="GET",
        host="bucket.example.com",
        region="auto",
        access_key="key",
        secret_key="secret",
        expires_in=600,
        now=datetime(2026, 8, 18, 12, 0, 0, tzinfo=timezone.utc),
    )
    a = storage.presign(canonical_uri="/b/renders/job-a/source.blend", **common)
    b = storage.presign(canonical_uri="/b/renders/job-b/source.blend", **common)
    assert a.split("X-Amz-Signature=")[1] != b.split("X-Amz-Signature=")[1]


def test_get_and_put_do_not_share_a_signature():
    """Read access must not be write access.

    The customer download path hands out GETs. If a GET signature also
    authorised a PUT, anybody who had ever downloaded a finished frame could
    overwrite it.
    """
    bucket = storage.Bucket(
        endpoint="https://account.r2.cloudflarestorage.com",
        bucket="renders",
        access_key="key",
        secret_key="secret",
        region="auto",
    )
    now = datetime(2026, 8, 18, 12, 0, 0, tzinfo=timezone.utc)
    get = bucket.presign_get("renders/j/source.blend", 600, now=now)
    put = bucket.presign_put("renders/j/source.blend", 600, now=now)
    assert get.split("X-Amz-Signature=")[1] != put.split("X-Amz-Signature=")[1]


def test_expiry_is_carried_in_the_url():
    bucket = storage.Bucket(
        endpoint="https://account.r2.cloudflarestorage.com",
        bucket="renders",
        access_key="key",
        secret_key="secret",
        region="auto",
    )
    assert "X-Amz-Expires=900" in bucket.presign_get("renders/j/x.png", 900)


def test_keys_are_derived_from_the_job_id_and_are_not_enumerable():
    """Neighbouring jobs must not be reachable by editing a number.

    The frame number inside one job is sequential and that is fine -- holding a
    URL for your own frame 3 is not a way to reach frame 4 of somebody else's
    job, because the job id is a uuid4 and sits above it in the path.
    """
    a = storage.source_key("2b1f0c9e4d7a4f1c8e6b5a3d2c1f0e9d")
    b = storage.source_key("9d0e1f2c3d4a5b6c7d8e9f0a1b2c3d4e")
    assert a != b
    assert a.startswith("renders/")
    assert storage.frame_key("job", 7, "png").endswith("000007.png")
    assert storage.frame_key("job", 7, "exr").endswith("000007.exr")


def test_unconfigured_storage_says_what_is_missing(monkeypatch):
    """A fresh clone must get an instruction, not an outage.

    db.NotConfigured exists for the same reason: 'nobody set this up' and 'the
    service is down' need different responses from whoever is reading, and
    collapsing them into one message costs somebody an afternoon.
    """
    for variable in (
        "RENDER_STORAGE_ENDPOINT",
        "RENDER_STORAGE_BUCKET",
        "RENDER_STORAGE_ACCESS_KEY_ID",
        "RENDER_STORAGE_SECRET_ACCESS_KEY",
    ):
        monkeypatch.delenv(variable, raising=False)

    assert storage.is_configured() is False
    with pytest.raises(storage.StorageNotConfigured) as excinfo:
        storage.bucket()
    assert "RENDER_STORAGE_ENDPOINT" in str(excinfo.value)


def test_endpoint_without_a_scheme_is_rejected_at_configuration_time(monkeypatch):
    """Fail where the mistake is, not three layers later.

    Without this, a missing `https://` produces a URL with no host, an httpx
    error at upload time, and a stack trace pointing at the render endpoint
    rather than at the environment variable that is actually wrong.
    """
    monkeypatch.setenv("RENDER_STORAGE_ENDPOINT", "account.r2.cloudflarestorage.com")
    monkeypatch.setenv("RENDER_STORAGE_BUCKET", "renders")
    monkeypatch.setenv("RENDER_STORAGE_ACCESS_KEY_ID", "key")
    monkeypatch.setenv("RENDER_STORAGE_SECRET_ACCESS_KEY", "secret")
    with pytest.raises(storage.StorageNotConfigured):
        storage.bucket()


@pytest.mark.parametrize("expires_in", [0, -1, storage.MAX_EXPIRES_IN_S + 1, 999_999])
def test_an_out_of_range_lifetime_is_refused_at_signing_time(expires_in):
    """Seven days is SigV4's ceiling, and exceeding it fails in the worst place.

    A URL signed with X-Amz-Expires above 604800 is minted without complaint,
    returned in a 200, and rejected only when the browser or the provider
    finally uses it -- by object storage, with a 400 that names neither this
    service nor the environment variable at fault. Verified against a live S3
    implementation: 604800 answers 404 NoSuchKey, 604801 answers 400
    AuthorizationQueryParametersError.

    Raising here means a misconfigured RENDER_*_TTL_SEC surfaces as a 503 from
    the orchestrator with the number in the message.
    """
    with pytest.raises(storage.StorageError) as excinfo:
        storage.presign(
            method="GET",
            host="bucket.example.com",
            canonical_uri="/b/renders/job/source.blend",
            region="auto",
            access_key="key",
            secret_key="secret",
            expires_in=expires_in,
            now=datetime(2026, 8, 18, 12, 0, 0, tzinfo=timezone.utc),
        )
    assert str(expires_in) in str(excinfo.value)


def test_the_ceiling_itself_still_signs():
    """604800 is legal; the boundary must not be off by one."""
    url = storage.presign(
        method="GET",
        host="bucket.example.com",
        canonical_uri="/b/renders/job/source.blend",
        region="auto",
        access_key="key",
        secret_key="secret",
        expires_in=storage.MAX_EXPIRES_IN_S,
        now=datetime(2026, 8, 18, 12, 0, 0, tzinfo=timezone.utc),
    )
    assert "X-Amz-Expires=604800" in url


def _bucket() -> storage.Bucket:
    return storage.Bucket(
        endpoint="https://account.r2.cloudflarestorage.com",
        bucket="renders",
        access_key="key",
        secret_key="secret",
        region="auto",
    )


NOW = datetime(2026, 8, 18, 12, 0, 0, tzinfo=timezone.utc)


def test_an_unbounded_upload_url_is_still_the_default():
    """Outputs cannot declare a size, so they must still be signable without one.

    Nobody can say how many bytes a rendered frame will be before it is
    rendered. Making content_length mandatory would leave the provider upload
    path unable to sign at all, which is why the bound is opt-in and the
    output path is bounded after the fact by the HEAD at result time instead.
    """
    url = _bucket().presign_put("renders/j/frame_0001.png", 600, now=NOW)
    assert "X-Amz-SignedHeaders=host" in url


def test_a_declared_size_is_signed_into_the_upload_url():
    """A presigned PUT is a bearer capability, and this is what bounds it.

    Whoever holds the URL can use it, so without the binding a customer who
    declared a 40 MB scene could push 40 GB through the same URL and the only
    thing that would ever notice is the storage bill. Signing the header means
    the bucket recomputes the signature from the Content-Length it actually
    received and refuses anything else -- enforcement before the bytes are
    accepted, which is the only place that can refuse them without first
    receiving them.
    """
    url = _bucket().presign_put(
        "renders/j/source.blend", 600, now=NOW, content_length=42_000_000
    )
    assert "X-Amz-SignedHeaders=content-length%3Bhost" in url


def test_two_declared_sizes_do_not_share_a_signature():
    # The property the binding rests on. If the signature did not cover the
    # value, declaring one size and sending another would still be authorised
    # and the header would be decoration.
    bucket = _bucket()
    small = bucket.presign_put("renders/j/source.blend", 600, now=NOW, content_length=1000)
    large = bucket.presign_put(
        "renders/j/source.blend", 600, now=NOW, content_length=1_000_000_000
    )
    assert small.split("X-Amz-Signature=")[1] != large.split("X-Amz-Signature=")[1]


def test_a_bound_url_is_not_the_same_as_an_unbound_one():
    # Guards against the bound silently doing nothing: if omitting
    # content_length produced the same signature as supplying it, every upload
    # would be unbounded and every test above would still pass.
    bucket = _bucket()
    unbound = bucket.presign_put("renders/j/source.blend", 600, now=NOW)
    bound = bucket.presign_put(
        "renders/j/source.blend", 600, now=NOW, content_length=1000
    )
    assert unbound.split("X-Amz-Signature=")[1] != bound.split("X-Amz-Signature=")[1]


def test_a_negative_declared_size_is_refused_rather_than_signed():
    # A negative Content-Length cannot be satisfied by any upload, so signing
    # one would mint a URL that is guaranteed to fail -- reported to the
    # customer as a broken upload rather than as the bad input it is.
    with pytest.raises(storage.StorageError):
        _bucket().presign_put("renders/j/source.blend", 600, now=NOW, content_length=-1)
