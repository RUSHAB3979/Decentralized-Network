"""Presigned object storage URLs, for the render vertical.

WHY THIS FILE EXISTS AT ALL. A render job's payload is a file: a .blend going
in, images coming out. The obvious implementation -- accept the upload on a
FastAPI route, keep it, hand it to the provider -- is less code and is wrong
twice over. The orchestrator runs on a 512 MB instance that would be streaming
multi-hundred-megabyte files through itself, and its egress is billed. More
importantly it would put a customer's project data through a process that has
no reason to see it.

So the bytes never come here. This module mints short-lived URLs that authorise
exactly one operation on exactly one object, and the traffic goes
browser -> storage and storage -> provider directly.

WHY NO SDK. boto3 is roughly fifty megabytes of dependency to produce a string.
A presigned S3 URL is a SigV4 query signature: an HMAC chain over a canonical
request, all of it in hashlib and hmac. It is deterministic, it is specified in
public, and AWS publishes test vectors for it -- which means it can be verified
exactly rather than trusted. tests/test_storage.py checks this implementation
against the vector from AWS's own documentation.

The second reason is the one that matters more. `agent/requirements.txt` is a
security boundary and says so in its header: the provider agent must never hold
a storage credential. Because a presigned URL is just a URL, the agent needs no
SDK and no key -- it does an httpx PUT and GET against a string it was handed.
A credential that never reaches a machine cannot leak from it.

WHAT A PROVIDER CAN DO WITH WHAT WE GIVE IT: read one .blend, write one output
object, until the lease expires. It cannot list the bucket, cannot read another
customer's project, and cannot overwrite a frame that is already finished.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from datetime import datetime, timezone
from urllib.parse import quote

import httpx

ALGORITHM = "AWS4-HMAC-SHA256"

# S3 signs the payload hash into the canonical request. For a presigned URL the
# body is not known at signing time -- that is the entire point -- so the
# literal string UNSIGNED-PAYLOAD stands in for it. This is specified
# behaviour, not a shortcut.
UNSIGNED_PAYLOAD = "UNSIGNED-PAYLOAD"

# SigV4 query authentication caps X-Amz-Expires at seven days. Past that S3
# rejects the request with 400 AuthorizationQueryParametersError -- verified
# against a live S3 implementation, which answers 404 NoSuchKey at exactly
# 604800 and 400 at 604801. The failure is worth catching here because of where
# it would otherwise surface: the URL mints without complaint, the orchestrator
# returns 200, and the customer's browser is the first thing to see the error,
# against a host that is not ours, with a message that names neither the
# environment variable at fault nor this service.
MAX_EXPIRES_IN_S = 604_800


class StorageNotConfigured(RuntimeError):
    """No bucket credentials in the environment.

    Deliberately distinct from a storage error. 'the bucket is unreachable' and
    'nobody has configured a bucket' are different problems for whoever reads
    the log, in the same way db.NotConfigured is kept distinct from a psycopg
    error. A fresh clone with no environment hits this one, and the message has
    to tell that person what to set rather than look like an outage.
    """


class StorageError(RuntimeError):
    """The bucket answered, and the answer was not usable."""


def _uri_encode(value: str, encode_slash: bool = True) -> str:
    """Percent-encode per SigV4's rules, which are not urlencode's rules.

    The unreserved set is A-Z a-z 0-9 - _ . ~ and nothing else. Notably a
    space becomes %20 and never '+'. Getting this wrong produces a signature
    that is valid for a different string than the one in the URL, which fails
    as an opaque 403 with no indication of which character caused it.
    """
    safe = "-_.~" if encode_slash else "-_.~/"
    return quote(value, safe=safe)


def _sign(key: bytes, message: str) -> bytes:
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).digest()


def _signing_key(secret: str, datestamp: str, region: str, service: str) -> bytes:
    """The four-step derivation. Each step narrows what the key can sign for.

    That narrowing is the point: a key derived for one date, one region and one
    service cannot be replayed against another. It is also why the date in the
    credential scope must match X-Amz-Date exactly.
    """
    key = _sign(f"AWS4{secret}".encode("utf-8"), datestamp)
    key = _sign(key, region)
    key = _sign(key, service)
    return _sign(key, "aws4_request")


def presign(
    *,
    method: str,
    host: str,
    canonical_uri: str,
    region: str,
    access_key: str,
    secret_key: str,
    expires_in: int,
    now: datetime,
    scheme: str = "https",
    service: str = "s3",
    extra_signed_headers: dict[str, str] | None = None,
) -> str:
    """Build one presigned URL. Pure function -- no environment, no network.

    Kept free of configuration on purpose so it can be checked against AWS's
    published test vector, which fixes the key, the date and the host. A
    signing routine that can only be exercised through the app's configuration
    is a signing routine that is never actually verified.
    """
    if expires_in < 1 or expires_in > MAX_EXPIRES_IN_S:
        raise StorageError(
            f"expires_in must be between 1 and {MAX_EXPIRES_IN_S} seconds "
            f"(SigV4 query authentication's limit); got {expires_in}"
        )

    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    datestamp = now.strftime("%Y%m%d")
    credential_scope = f"{datestamp}/{region}/{service}/aws4_request"

    # Anything named here becomes part of the signature, which means the holder
    # of the URL can no longer choose it: send a different value and the server
    # recomputes a different signature and refuses. That is the entire mechanism
    # behind binding a size to an upload URL -- see presign_put().
    #
    # `host` is always present. Header names are lowercased and values trimmed
    # because SigV4's canonical form requires it, and a mismatch here surfaces
    # as an opaque 403 that names no cause.
    headers = {"host": host.strip()}
    for name, value in (extra_signed_headers or {}).items():
        headers[name.strip().lower()] = str(value).strip()
    signed_names = ";".join(sorted(headers))
    canonical_headers = "".join(f"{name}:{headers[name]}\n" for name in sorted(headers))

    # Every query parameter is encoded, then the whole set is sorted by key.
    # Sorted order is part of the signature; a different order signs a
    # different string.
    query = {
        "X-Amz-Algorithm": ALGORITHM,
        "X-Amz-Credential": f"{access_key}/{credential_scope}",
        "X-Amz-Date": amz_date,
        "X-Amz-Expires": str(expires_in),
        "X-Amz-SignedHeaders": signed_names,
    }
    canonical_query = "&".join(
        f"{_uri_encode(k)}={_uri_encode(v)}" for k, v in sorted(query.items())
    )

    canonical_request = "\n".join(
        [
            method.upper(),
            canonical_uri,
            canonical_query,
            canonical_headers,
            signed_names,
            UNSIGNED_PAYLOAD,
        ]
    )

    string_to_sign = "\n".join(
        [
            ALGORITHM,
            amz_date,
            credential_scope,
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        ]
    )

    signature = hmac.new(
        _signing_key(secret_key, datestamp, region, service),
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return f"{scheme}://{host}{canonical_uri}?{canonical_query}&X-Amz-Signature={signature}"


class Bucket:
    """One configured bucket, addressed path-style.

    Path-style (`https://endpoint/bucket/key`) rather than virtual-host style
    because Cloudflare R2 -- the decision in ADR 0006 -- serves that way, and it
    also works unchanged against MinIO for local development. AWS S3 proper
    accepts it too.
    """

    def __init__(
        self,
        *,
        endpoint: str,
        bucket: str,
        access_key: str,
        secret_key: str,
        region: str,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.bucket = bucket
        self.access_key = access_key
        self.secret_key = secret_key
        # R2 wants the literal string "auto"; S3 wants a real region name.
        self.region = region

        scheme, _, host = self.endpoint.partition("://")
        if not host:
            raise StorageNotConfigured(
                "RENDER_STORAGE_ENDPOINT must include a scheme, "
                "e.g. https://<account>.r2.cloudflarestorage.com"
            )
        self.scheme = scheme
        self.host = host

    def _canonical_uri(self, key: str) -> str:
        # The slash between bucket and key is a path separator and must survive
        # encoding; slashes inside the key itself are path separators too.
        return f"/{_uri_encode(self.bucket, encode_slash=False)}/{_uri_encode(key, encode_slash=False)}"

    def presign_get(self, key: str, expires_in: int, now: datetime | None = None) -> str:
        return presign(
            method="GET",
            host=self.host,
            canonical_uri=self._canonical_uri(key),
            region=self.region,
            access_key=self.access_key,
            secret_key=self.secret_key,
            expires_in=expires_in,
            now=now or datetime.now(timezone.utc),
            scheme=self.scheme,
        )

    def presign_put(
        self,
        key: str,
        expires_in: int,
        now: datetime | None = None,
        content_length: int | None = None,
    ) -> str:
        """A URL authorising one PUT to one object.

        `content_length` binds the URL to an exact number of bytes. Pass it and
        the upload must send precisely that many; the bucket recomputes the
        signature from the Content-Length header it actually received and
        rejects any other value.

        WHY THAT MATTERS. Without it a presigned PUT authorises an upload of
        unbounded size. The URL is a bearer capability -- whoever holds it can
        use it -- so a customer handed a URL for a file they said was 40 MB
        could push 40 GB through it, and the only thing that would ever notice
        is a storage bill. The declared size was already being collected at
        submission; this is what turns that declaration into a constraint
        rather than a note. Enforcement is at the bucket, before the bytes are
        accepted, which is the only place that can refuse them without first
        receiving them.

        The size check at confirmation time stays regardless. It is a
        measurement of what is actually stored, and it still catches the object
        that was uploaded through some other route, or replaced afterwards.

        Left None for outputs, where the size genuinely is not knowable in
        advance -- nobody can say how many bytes a frame will be before it is
        rendered. Those are bounded after the fact instead, by the HEAD in
        submit_render_result().
        """
        extra = None
        if content_length is not None:
            if content_length < 0:
                raise StorageError("content_length cannot be negative")
            extra = {"content-length": str(content_length)}
        return presign(
            method="PUT",
            host=self.host,
            canonical_uri=self._canonical_uri(key),
            region=self.region,
            access_key=self.access_key,
            secret_key=self.secret_key,
            expires_in=expires_in,
            now=now or datetime.now(timezone.utc),
            scheme=self.scheme,
            extra_signed_headers=extra,
        )

    def head_prefix(self, key: str, length: int, timeout: float = 10.0) -> bytes:
        """The first `length` bytes of the object, or b'' if there are none.

        A ranged GET rather than a full one, because the caller wants a file's
        magic number and the file may be two gigabytes. Range is a request
        header and not part of the signature, so this reuses the same GET
        signing path as everything else in this file -- there is still exactly
        one signing implementation to get right.

        Returns b'' rather than raising when the object is missing, so a caller
        can treat "no object" and "object with no usable prefix" the same way:
        both mean there is nothing here to accept.
        """
        url = self.presign_get(key, 60)
        try:
            response = httpx.get(
                url,
                headers={"Range": f"bytes=0-{max(0, length - 1)}"},
                timeout=timeout,
            )
        except httpx.RequestError as exc:
            raise StorageError(f"bucket unreachable: {exc.__class__.__name__}: {exc}") from exc

        if response.status_code == 404:
            return b""
        # 206 for a served range, 200 for a bucket that ignored Range and sent
        # the whole object. Both are usable; the slice below makes them equal.
        if response.status_code not in (200, 206):
            raise StorageError(f"bucket returned {response.status_code} for GET {key}")
        return response.content[:length]

    def head(self, key: str, timeout: float = 10.0) -> int | None:
        """Size of the stored object, or None if it is not there.

        This is the only place the orchestrator itself talks to the bucket, and
        it exists because a client saying "I uploaded it" is a claim and this is
        a measurement. Without it, a job whose upload silently failed fans out
        into frames that every provider in the fleet will fail to render, one
        after another, each one looking like a provider fault.

        Signed as a HEAD and issued directly rather than through a header-based
        SigV4 request, so there is exactly one signing implementation in this
        file to get right and to test.
        """
        url = presign(
            method="HEAD",
            host=self.host,
            canonical_uri=self._canonical_uri(key),
            region=self.region,
            access_key=self.access_key,
            secret_key=self.secret_key,
            expires_in=60,
            now=datetime.now(timezone.utc),
            scheme=self.scheme,
        )
        try:
            response = httpx.head(url, timeout=timeout)
        except httpx.RequestError as exc:
            raise StorageError(f"bucket unreachable: {exc.__class__.__name__}: {exc}") from exc

        if response.status_code == 404:
            return None
        if response.status_code >= 400:
            # 403 here usually means the credentials are wrong or the clock has
            # drifted past the signature's validity, and both look identical
            # from the outside. Say which status came back so the operator has
            # somewhere to start.
            raise StorageError(f"bucket returned {response.status_code} for HEAD {key}")

        length = response.headers.get("content-length")
        if length is None:
            return None
        try:
            return int(length)
        except ValueError:
            return None


def bucket() -> Bucket:
    """The configured bucket, or an explanation of what is missing.

    Read per call rather than captured at import, for the same reason ttl() and
    signups_open() are in main.py: a running deployment can be reconfigured
    without a code change, and tests can vary it.
    """
    endpoint = os.getenv("RENDER_STORAGE_ENDPOINT", "").strip()
    name = os.getenv("RENDER_STORAGE_BUCKET", "").strip()
    access_key = os.getenv("RENDER_STORAGE_ACCESS_KEY_ID", "").strip()
    secret_key = os.getenv("RENDER_STORAGE_SECRET_ACCESS_KEY", "").strip()
    region = os.getenv("RENDER_STORAGE_REGION", "auto").strip() or "auto"

    missing = [
        variable
        for variable, value in (
            ("RENDER_STORAGE_ENDPOINT", endpoint),
            ("RENDER_STORAGE_BUCKET", name),
            ("RENDER_STORAGE_ACCESS_KEY_ID", access_key),
            ("RENDER_STORAGE_SECRET_ACCESS_KEY", secret_key),
        )
        if not value
    ]
    if missing:
        raise StorageNotConfigured(
            "object storage is not configured; missing " + ", ".join(missing)
        )

    return Bucket(
        endpoint=endpoint,
        bucket=name,
        access_key=access_key,
        secret_key=secret_key,
        region=region,
    )


def is_configured() -> bool:
    try:
        bucket()
    except StorageNotConfigured:
        return False
    return True


# ---------------------------------------------------------------------------
# Key layout.
#
# Keys are derived from the job id, which is a uuid4 -- so they are not
# enumerable. Somebody holding one presigned URL learns the key it points at
# and nothing else; they cannot walk to the neighbouring job by incrementing a
# number. That property is worth more here than a tidy human-readable path,
# because these objects are other people's unreleased work.
#
# The `renders/` prefix exists so a lifecycle rule can expire this whole class
# of object without touching anything else in the bucket. What that rule should
# be -- how long a source file is kept, how long artifacts are kept, who may
# delete them -- carries legal weight under
# docs/LEGAL-SECURITY-REQUIREMENTS-INDIA.md and is not a setting to be picked by
# whoever happens to create the bucket. It is written down as task Y13.
# ---------------------------------------------------------------------------


def source_key(job_id: str) -> str:
    return f"renders/{job_id}/source.blend"


def frame_key(job_id: str, frame_number: int, output_format: str) -> str:
    extension = "exr" if output_format == "exr" else "png"
    return f"renders/{job_id}/frames/{frame_number:06d}.{extension}"
