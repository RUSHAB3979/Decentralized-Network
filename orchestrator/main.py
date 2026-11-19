"""HTTP API for accounts, provider enrolment and GPU workloads."""

from __future__ import annotations

import os
import secrets
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from typing import Annotated

import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Json
from fastapi import FastAPI, Header, HTTPException, Path, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from orchestrator import auth
from orchestrator import db
from orchestrator import inference
from orchestrator import limits
from orchestrator import storage
from orchestrator.liveness import liveness
from orchestrator.models import (
    MAX_JOB_TRANSFER_BYTES,
    MAX_OUTPUT_BYTES,
    MAX_SOURCE_BYTES,
    MIN_OUTPUT_BYTES,
    OUTPUT_MAGIC,
    OUTPUT_MAGIC_BYTES,
    ApiKeyCreated,
    ApiKeyCreateRequest,
    ApiKeyList,
    ApiKeyView,
    ChatCompletionChoice,
    ChatCompletionMessage,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatUsage,
    EnrolmentKeyCreated,
    EnrolmentKeyView,
    HeartbeatRequest,
    HeartbeatResponse,
    JobClaimResponse,
    JobOffer,
    JobPayload,
    JobResultAccepted,
    JobResultRequest,
    LoginRequest,
    ModelList,
    ModelView,
    NodeList,
    NodeView,
    OwnedNodeView,
    ProviderAccountView,
    ProviderSessionCreated,
    RegisterRequest,
    RegisterResponse,
    RenderArtifact,
    RenderArtifactList,
    RenderClaimResponse,
    RenderFrameOffer,
    RenderFrameView,
    RenderJobCreateRequest,
    RenderJobCreated,
    RenderJobList,
    RenderJobView,
    RenderResultAccepted,
    RenderResultRequest,
    SessionCreated,
    SignupRequest,
    UsageSummary,
    UserView,
)

load_dotenv()

VERSION = "0.1.0"


def heartbeat_interval_s() -> int:
    """How often the agent should check in. Server-controlled; see models.py."""
    try:
        return max(1, int(os.getenv("HEARTBEAT_SEC", "15")))
    except ValueError:
        return 15


def ttl() -> timedelta:
    """How long a node stays online after its last heartbeat.

    Read per call rather than captured at import so the value can be changed
    without a code change, and so tests can vary it. It must stay comfortably
    larger than heartbeat_interval_s() -- if it ever drops below, every node
    goes offline between heartbeats and the whole fleet flaps.
    """
    try:
        ms = int(os.getenv("PROVIDER_TTL_MS", "120000"))
    except ValueError:
        ms = 120_000
    return timedelta(milliseconds=max(1000, ms))


def signups_open() -> bool:
    """Whether /v1/auth/signup will create new accounts.

    Read per call rather than captured at import, for the same reason as ttl():
    the door can then be closed on a running deployment by changing one
    environment variable, with no code change and no redeploy.

    The default is open, deliberately. A default of closed would mean a fresh
    clone with no environment cannot create its first account, and whoever hits
    that has no way to distinguish a deliberate lockdown from a broken install.
    The production deployment sets SIGNUPS_OPEN=false explicitly, so the closed
    state is always something somebody chose and can find.

    Anything other than a recognised falsy word counts as open. A typo in this
    variable must not silently lock everybody out.
    """
    value = os.getenv("SIGNUPS_OPEN", "true").strip().lower()
    return value not in {"false", "0", "no", "off"}


# Why this is remembered rather than only printed. `schema.sql` runs as a
# single statement in a single transaction, so one bad statement rolls back
# every other one in the file -- including the ADD COLUMNs. The app then boots
# against a database missing columns the code selects, and every authenticated
# request 503s while /health, which only pinged connectivity, kept answering
# "ok". That is exactly what happened after the render tables landed: a schema
# that could not apply to any database, fresh or existing, ran in production
# for days looking healthy. The startup log line said so and nobody was reading
# it. Health checks are read, so the failure belongs here.
_schema_error: str | None = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Create the M1 tables on boot, but never refuse to boot over it.

    A database that is down at startup is a normal condition in development --
    `uvicorn` gets started before `docker compose up -d db` more often than
    not. Crashing here would make that a confusing failure. Instead the app
    starts, /health reports degraded, and the provider endpoints return 503
    with the actual reason.
    """
    global _schema_error
    try:
        db.apply_schema()
        _schema_error = None
        print("[orchestrator] schema applied")
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        _schema_error = f"{exc.__class__.__name__}: {exc}"
        print(f"[orchestrator] schema not applied: {_schema_error}")
    yield


app = FastAPI(title="orchestrator", version=VERSION, lifespan=lifespan)

# The browser UI runs on a separate development origin. Keep the default list
# local-only because the API can now create credentials and submit inference.
def cors_origins() -> list[str]:
    configured = os.getenv("CORS_ORIGINS")
    if configured:
        return [origin.strip() for origin in configured.split(",") if origin.strip()]
    return ["http://localhost:3000", "http://127.0.0.1:3000"]


app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

# FastAPI serves these three from a CDN. A default-src 'none' policy would leave
# the documentation page loading forever with an empty frame, so they get the
# rest of the headers and not the content policy.
_DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")

# What this API is: JSON, to be read by a program. It loads no script, embeds no
# image, submits no form, and has no business being rendered inside a frame.
# Saying so costs nothing and closes the shapes an error body could otherwise be
# coerced into -- a reflected value in a 422 detail rendered as HTML, or an
# endpoint framed invisibly over a page the user thinks they are clicking.
_API_CSP = (
    "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Headers every response carries, whatever produced it.

    Applied as middleware rather than per-endpoint on purpose: the responses
    most worth covering are the ones no handler wrote -- 422s from validation,
    500s from an unhandled exception, 404s for paths that do not exist. Those
    are exactly the responses a per-route decorator would miss.
    """
    response = await call_next(request)

    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    # Almost every response here is either a credential, something derived from
    # one, or a customer's private job state. None of it should sit in a shared
    # cache, and 'no-store' is the only directive that also covers the browser's
    # back/forward cache.
    response.headers.setdefault("Cache-Control", "no-store")
    # Ignored by browsers when it arrives over plain HTTP, which is what makes
    # it safe to send unconditionally: local development is unaffected, and in
    # production -- where TLS is terminated by a proxy that forwards plain HTTP
    # to this process -- there is no request attribute we could condition on
    # that an attacker could not also set.
    response.headers.setdefault(
        "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
    )

    if not request.url.path.startswith(_DOCS_PATHS):
        response.headers.setdefault("Content-Security-Policy", _API_CSP)

    return response


def _now() -> datetime:
    """Server time, always timezone-aware.

    Naive datetimes compared against TIMESTAMPTZ values are the classic way a
    staleness check silently goes wrong by exactly one timezone offset -- five
    and a half hours here -- which is long enough that dead nodes read online
    and nothing raises.
    """
    return datetime.now(timezone.utc)


def _unavailable(exc: Exception) -> HTTPException:
    """Turn a storage failure into a 503 the caller can act on.

    503 rather than 500: the agent's heartbeat loop retries on 5xx, and this is
    genuinely transient. The exception class is included because 'database is
    unreachable' and 'DATABASE_URL is unset' are different problems for
    whoever is reading the agent's log.
    """
    return HTTPException(
        status_code=503,
        detail=f"orchestrator storage unavailable: {exc.__class__.__name__}: {exc}",
    )


@app.get("/service")
def ping():
    return {"service": "orchestrator"}


@app.get("/health")
def health():
    try:
        with db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
    except (db.NotConfigured, psycopg.Error, OSError):
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "db": "down", "version": VERSION},
        )
    # Reachable is not the same as usable. A database that answers SELECT 1 but
    # is missing the columns this process selects serves 503 on every
    # authenticated route, and reporting that as "ok" is how such a deploy
    # survives unnoticed. The class name is carried but not the statement text:
    # this endpoint is unauthenticated, and "UndefinedTable" is enough for an
    # operator to go and read the boot log that has the rest.
    if _schema_error is not None:
        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "db": "ok",
                "schema": "not applied",
                "error": _schema_error.split(":", 1)[0],
                "version": VERSION,
            },
        )
    return {"status": "ok", "db": "ok", "schema": "ok", "version": VERSION}


def _upsert_node(cur: psycopg.Cursor, req: RegisterRequest, *, fresh_credential: bool) -> dict:
    cap = req.capability
    cur.execute(
        """
        INSERT INTO provider_nodes (
            node_id, hostname, os_version, cpu, logical_cores,
            ram_total_mb, gpu_name, vram_total_mb, gpu_driver, agent_version
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (node_id) DO UPDATE SET
            hostname = EXCLUDED.hostname,
            os_version = EXCLUDED.os_version,
            cpu = EXCLUDED.cpu,
            logical_cores = EXCLUDED.logical_cores,
            ram_total_mb = EXCLUDED.ram_total_mb,
            gpu_name = EXCLUDED.gpu_name,
            vram_total_mb = EXCLUDED.vram_total_mb,
            gpu_driver = EXCLUDED.gpu_driver,
            agent_version = EXCLUDED.agent_version,
            node_token_hash = NULL
        RETURNING registered_at
        """,
        (
            req.node_id, cap.hostname, cap.os_version, cap.cpu, cap.logical_cores,
            cap.ram_total_mb, cap.gpu_name, cap.vram_total_mb, cap.gpu_driver, cap.agent_version,
        ),
    )
    row = cur.fetchone()
    if fresh_credential:
        _disable_node_work(cur, req.node_id)
    return row


def _disable_node_work(cur: psycopg.Cursor, node_id: str) -> None:
    cur.execute(
        """
        UPDATE provider_nodes
        SET accepts_work = FALSE, inference_eligible = FALSE, render_eligible = FALSE
        WHERE node_id = %s
        """,
        (node_id,),
    )


@app.post("/providers/register", response_model=RegisterResponse, response_model_exclude_none=True)
def register(req: RegisterRequest, authorization: str | None = Header(default=None)):
    """Refresh or recreate telemetry using the current enrolled credential."""
    digest = _bearer_digest(authorization)
    try:
        with db.connect() as conn, conn.cursor() as cur:
            _verify_node_credential(_node_credential(cur, req.node_id), digest)
            row = _upsert_node(cur, req, fresh_credential=False)
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        raise _unavailable(exc) from exc
    return RegisterResponse(
        node_id=req.node_id,
        registered_at=row["registered_at"],
        heartbeat_interval_s=heartbeat_interval_s(),
    )


@app.post("/providers/heartbeat", response_model=HeartbeatResponse)
def heartbeat(
    req: HeartbeatRequest,
    authorization: str | None = Header(default=None),
):
    """Record telemetry from an enrolled node or an existing legacy reporter."""
    digest = _bearer_digest(authorization)
    m = req.metrics
    received = _now()
    try:
        with db.connect() as conn:
            with conn.cursor() as cur:
                node = _authenticate_node(cur, req.node_id, digest, telemetry_only=True)
                cur.execute(
                    """
                    UPDATE provider_nodes SET
                        last_status         = %s,
                        last_detail         = %s,
                        accepts_work        = %s,
                        gpu_utilisation_pct = %s,
                        vram_used_mb        = %s,
                        temperature_c       = %s,
                        ollama_reachable    = %s,
                        ollama_version      = %s,
                        local_models        = %s,
                        blender_version     = %s,
                        last_heartbeat_at   = %s
                    WHERE node_id = %s
                    """,
                    (
                        req.status,
                        req.detail,
                        req.accepts_work and node["issued_at"] is not None,
                        m.gpu_utilisation_pct,
                        m.vram_used_mb,
                        m.temperature_c,
                        m.ollama_reachable,
                        m.ollama_version,
                        m.local_models,
                        m.blender_version,
                        received,
                        req.node_id,
                    ),
                )
                found = cur.rowcount
            conn.commit()
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        raise _unavailable(exc) from exc

    if not found:
        raise HTTPException(
            status_code=404,
            detail=f"unknown node {req.node_id}; register before heartbeating",
        )

    return HeartbeatResponse(
        node_id=req.node_id,
        received_at=received,
        heartbeat_interval_s=heartbeat_interval_s(),
    )


@app.get("/providers/nodes", response_model=NodeList)
def list_nodes(authorization: str | None = Header(default=None)):
    """Every enrolled node, most recently seen first. Requires a session.

    Liveness is computed here from `last_heartbeat_at` rather than read from a
    column, for the reason set out in liveness.py: a derived value cannot claim
    a heartbeat that never arrived.

    Why this needs authentication at all, when it creates nothing and changes
    nothing: every row is a hardware fingerprint of somebody's actual computer
    -- hostname, OS build, CPU model, GPU model, driver version, installed
    models, and the times that machine is awake. Served anonymously from a
    public URL, that is a map of the fleet for anyone who asks, and it is our
    providers' machines being described, not ours.

    A session is the right gate rather than an API key: keys are for
    programmatic inference, and this endpoint exists to render a console page
    for a signed-in human. When provider accounts land (ADR 0005) this should
    narrow further, from "any signed-in user" to "the account that owns the
    node" -- today there is no owner column to filter on.

    AND A SESSION WAS NOT ENOUGH. Requiring one kept the fleet off a public URL
    and then handed all of it to anyone who filled in the signup form: hostname,
    OS build, CPU model, GPU driver version and node id, for every provider on
    the marketplace, to any customer who asked. Signing up is not a relationship
    with someone else's home computer.

    So the response is now filtered by `users.is_operator`, the seam this
    model's docstring said it was waiting for. An operator sees the fleet as
    before, because diagnosing a provider's machine requires knowing which
    machine it is. Everybody else sees what the marketplace is actually selling
    -- GPU model, VRAM, liveness, utilisation, whether it is accepting work --
    and nothing that identifies the machine or its owner. See _visible_node().
    """
    session = _authenticate_session(authorization)
    full_detail = bool(session.get("is_operator"))
    try:
        with db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT n.node_id, hostname, os_version, cpu, logical_cores,
                           ram_total_mb, gpu_name, vram_total_mb, gpu_driver,
                           agent_version, last_status, last_detail,
                           (c.node_id IS NOT NULL AND c.revoked_at IS NULL
                            AND n.accepts_work AND (n.inference_eligible OR n.render_eligible))
                               AS accepts_work,
                           gpu_utilisation_pct, vram_used_mb, temperature_c,
                           ollama_reachable, ollama_version, local_models,
                           registered_at, last_heartbeat_at
                    FROM provider_nodes n
                    LEFT JOIN provider_node_credentials c ON c.node_id = n.node_id
                    ORDER BY last_heartbeat_at DESC NULLS LAST, registered_at DESC
                    """
                )
                rows = cur.fetchall()
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        raise _unavailable(exc) from exc

    now = _now()
    window = ttl()
    return NodeList(
        nodes=[_visible_node(r, now, window, full_detail) for r in rows],
        ttl_seconds=int(window.total_seconds()),
        server_time=now,
    )


def _visible_node(r: dict, now: datetime, window: timedelta, full_detail: bool) -> NodeView:
    """One node row as this caller is allowed to see it.

    WHAT IS REDACTED AND WHY THAT LINE. The fields removed for a non-operator
    are the ones that identify a machine or the person at it: hostname (people
    name their PCs after themselves), OS build and CPU model and GPU driver
    version (together, a fingerprint precise enough to correlate the same
    machine across services, and a list of exactly which patches it is missing),
    and the Ollama build number. None of that is information a customer renting
    GPU time has any use for.

    What stays is the product: GPU model, VRAM total and in use, utilisation,
    temperature, core count, RAM, liveness, whether it accepts work, and which
    models it has. That is the capacity being sold, and a marketplace that hid
    it would have nothing to show.

    `hostname` is required by NodeView and is replaced rather than emptied, with
    a stable label derived from the node id. Substituting rather than blanking
    matters for the console, which uses it as the human-readable name of a card
    -- a fleet of nodes all called "" is a worse page than a fleet called
    node-3f9a12c4, and the label is stable across polls so React keys and the
    reader's memory both survive a refresh.

    `node_id` is kept for everyone. It is the marketplace's own identifier for a
    listing, the frontend needs a key, and it is no longer a targeting primitive
    now that /providers/heartbeat requires the node's credential.
    """
    if full_detail:
        return NodeView(
            node_id=r["node_id"],
            hostname=r["hostname"],
            liveness=liveness(r["last_heartbeat_at"], now, window),
            status=r["last_status"],
            detail=r["last_detail"],
            accepts_work=r["accepts_work"],
            gpu_name=r["gpu_name"],
            vram_total_mb=r["vram_total_mb"],
            vram_used_mb=r["vram_used_mb"],
            gpu_driver=r["gpu_driver"],
            gpu_utilisation_pct=r["gpu_utilisation_pct"],
            temperature_c=r["temperature_c"],
            cpu=r["cpu"],
            logical_cores=r["logical_cores"],
            ram_total_mb=r["ram_total_mb"],
            os_version=r["os_version"],
            agent_version=r["agent_version"],
            ollama_reachable=r["ollama_reachable"],
            ollama_version=r["ollama_version"],
            local_models=r["local_models"] or [],
            registered_at=r["registered_at"],
            last_heartbeat_at=r["last_heartbeat_at"],
        )

    return NodeView(
        node_id=r["node_id"],
        hostname=f"node-{auth.hash_token(r['node_id'])[:8]}",
        liveness=liveness(r["last_heartbeat_at"], now, window),
        status=r["last_status"],
        detail=r["last_detail"],
        accepts_work=r["accepts_work"],
        gpu_name=r["gpu_name"],
        vram_total_mb=r["vram_total_mb"],
        vram_used_mb=r["vram_used_mb"],
        gpu_driver=None,
        gpu_utilisation_pct=r["gpu_utilisation_pct"],
        temperature_c=r["temperature_c"],
        cpu=None,
        logical_cores=r["logical_cores"],
        ram_total_mb=r["ram_total_mb"],
        os_version=None,
        agent_version=None,
        ollama_reachable=r["ollama_reachable"],
        ollama_version=None,
        local_models=r["local_models"] or [],
        registered_at=r["registered_at"],
        last_heartbeat_at=r["last_heartbeat_at"],
    )


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=401,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def trust_proxy_header() -> bool:
    """Whether X-Forwarded-For may be believed when identifying a caller.

    OFF BY DEFAULT, and the default is the safe one. If this process is reachable
    directly, an attacker sets that header themselves and gets a fresh rate-limit
    bucket for every request -- the limiter would be present, passing its tests,
    and enforcing nothing.

    It has to be switchable on because the opposite failure is just as real:
    behind a proxy, every request arrives from the proxy's address, so all
    callers share one bucket and the first person to fail five logins locks out
    everybody. Neither default is correct everywhere, so the deployment says
    which one it is. Render terminates TLS in front of this app, so production
    sets it; a laptop does not.
    """
    return os.getenv("TRUST_PROXY_HEADER", "").strip().lower() in {"1", "true", "yes"}


def _client_key(request: Request) -> str:
    """A stable identifier for whoever is calling, for rate-limiting purposes.

    Only ever used as a limiter key. It is not an identity and nothing is
    authorised by it.
    """
    if trust_proxy_header():
        forwarded = request.headers.get("x-forwarded-for", "")
        # Leftmost entry is the original client; the rest are proxies. Both ends
        # are attacker-influenced when the header is not trusted, which is why
        # this branch is behind the flag above.
        first = forwarded.split(",")[0].strip()
        if first:
            return first[:64]
    client = request.client
    return client.host if client else "unknown"


def _rate_limit(limiter: limits.RateLimiter, key: str) -> None:
    """Apply one limiter, converting a refusal into a 429 with Retry-After."""
    try:
        limiter.check(key)
    except limits.RateLimited as exc:
        raise HTTPException(
            status_code=429,
            detail=(
                "too many attempts; wait before trying again. This limit exists "
                "because verifying a password is deliberately expensive."
            ),
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc


def _at_capacity(detail: str) -> HTTPException:
    """503 rather than a slow success.

    Retry-After is set so a client backs off by a stated amount instead of
    retrying immediately and deepening the queue it was refused from.
    """
    return HTTPException(status_code=503, detail=detail, headers={"Retry-After": "5"})


def _authenticate_api_key(authorization: str | None) -> dict:
    try:
        secret = inference.bearer_token(authorization)
    except ValueError as exc:
        raise _unauthorized(str(exc)) from exc

    prefix = inference.api_key_prefix(secret)
    try:
        with db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT key_id, name, key_hash, user_id
                    FROM marketplace_api_keys
                    WHERE key_prefix = %s
                      AND revoked_at IS NULL
                      -- An ownerless key is refused, not accepted.
                      --
                      -- The column is nullable because keys minted by the old
                      -- loopback-only demo flow have no owner. Authentication
                      -- matched on the hash alone while listing and revoking
                      -- were scoped to the session's user_id, so such a key
                      -- authenticated indefinitely and never appeared in the
                      -- only interface that could switch it off: there was no
                      -- supported way to revoke it.
                      --
                      -- Failing closed is the right direction for a credential
                      -- nobody can turn off. The holder of one gets a 401 and
                      -- mints a replacement that belongs to their account,
                      -- which takes a moment; the alternative is a permanent
                      -- unrevocable credential, which takes a database.
                      AND user_id IS NOT NULL
                    """,
                    (prefix,),
                )
                row = cur.fetchone()
                if row and secrets.compare_digest(
                    row["key_hash"], inference.hash_api_key(secret)
                ):
                    cur.execute(
                        """
                        UPDATE marketplace_api_keys
                        SET last_used_at = %s
                        WHERE key_id = %s
                        """,
                        (_now(), row["key_id"]),
                    )
                    conn.commit()
                    return row
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        raise _unavailable(exc) from exc
    raise _unauthorized("invalid or revoked API key")


@app.post("/v1/api-keys", response_model=ApiKeyCreated, status_code=201)
def create_api_key(
    req: ApiKeyCreateRequest,
    authorization: str | None = Header(default=None),
):
    """Mint a key belonging to the logged-in account.

    Previously gated on `_require_local_demo` -- loopback address plus an
    environment flag. That is a deployment posture, not an identity: every
    caller from the right address was the same anonymous customer, and the key
    it produced belonged to nobody. Now a key has an owner, and the queries
    below are scoped to it.
    """
    session = _authenticate_session(authorization)
    issued = inference.issue_api_key()
    key_id = f"key_{uuid4().hex}"
    try:
        with db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO marketplace_api_keys (
                        key_id, name, key_prefix, key_hash, user_id
                    ) VALUES (%s, %s, %s, %s, %s)
                    RETURNING created_at
                    """,
                    (key_id, req.name, issued.prefix, issued.digest, session["user_id"]),
                )
                row = cur.fetchone()
            conn.commit()
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        raise _unavailable(exc) from exc
    return ApiKeyCreated(
        id=key_id,
        name=req.name,
        key=issued.secret,
        key_prefix=issued.prefix,
        created_at=row["created_at"],
    )


@app.get("/v1/api-keys", response_model=ApiKeyList)
def list_api_keys(authorization: str | None = Header(default=None)):
    session = _authenticate_session(authorization)
    try:
        with db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT key_id, name, key_prefix, created_at, last_used_at
                    FROM marketplace_api_keys
                    WHERE revoked_at IS NULL AND user_id = %s
                    ORDER BY created_at DESC
                    """,
                    (session["user_id"],),
                )
                rows = cur.fetchall()
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        raise _unavailable(exc) from exc
    return ApiKeyList(
        keys=[
            ApiKeyView(
                id=row["key_id"],
                name=row["name"],
                key_prefix=row["key_prefix"],
                created_at=row["created_at"],
                last_used_at=row["last_used_at"],
            )
            for row in rows
        ]
    )


@app.delete("/v1/api-keys/{key_id}", status_code=204)
def revoke_api_key(
    key_id: str,
    authorization: str | None = Header(default=None),
):
    session = _authenticate_session(authorization)
    try:
        with db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE marketplace_api_keys
                    SET revoked_at = %s
                    WHERE key_id = %s AND revoked_at IS NULL AND user_id = %s
                    """,
                    (_now(), key_id, session["user_id"]),
                )
                found = cur.rowcount
            conn.commit()
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        raise _unavailable(exc) from exc
    if not found:
        raise HTTPException(status_code=404, detail="API key not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/v1/models", response_model=ModelList)
def list_inference_models(authorization: str | None = Header(default=None)):
    _authenticate_api_key(authorization)
    provider = _select_provider_for_model()
    created = int(provider["registered_at"].timestamp())
    return ModelList(
        data=[
            ModelView(id=model, created=created)
            for model in (provider["local_models"] or [])
        ]
    )


def _finish_inference_request(
    request_id: str,
    *,
    status_value: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_duration_ms: int | None = None,
    error_code: str | None = None,
) -> None:
    """Close out the audit row for one request.

    THE PROVIDER'S NUMBERS ARE NOT THE RECORD. Everything the agent reports here
    -- token counts, duration -- is chosen by a machine we do not own and have
    said from the start we do not trust. Those figures used to be written
    straight through and then summed by /v1/usage, which meant a hostile
    provider decided what a customer read about their own consumption.

    Two things change that, and neither of them is metering:

    `orchestrator_duration_ms` is measured here, from `created_at` to now. Both
    timestamps are written by this process, so no provider can influence it. It
    is the honest figure.

    `total_duration_ms` -- the reported one -- is clamped to that measurement.
    A provider cannot claim work took longer than the request was open, because
    that is not a thing that can be true. It can still under-report, and it can
    still lie about token counts within the bounds models.py sets; those are
    not fixable by arithmetic and need attested execution, which is the
    sandbox's problem and reserved under ADR 0002.

    HAND-BUILT SEAM, unchanged: none of this is a bill. agent/core/meter.py
    still raises NotImplementedError, and this function must not be mistaken for
    it landing. What it does is stop the untrusted side of the marketplace from
    being the sole author of the record.
    """
    now = _now()
    try:
        with db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT created_at FROM inference_requests WHERE request_id = %s
                    """,
                    (request_id,),
                )
                opened = cur.fetchone()

                measured_ms = None
                if opened and opened["created_at"] is not None:
                    measured_ms = max(
                        0, int((now - opened["created_at"]).total_seconds() * 1000)
                    )

                reported_ms = total_duration_ms
                if reported_ms is not None and measured_ms is not None:
                    reported_ms = min(reported_ms, measured_ms)

                cur.execute(
                    """
                    UPDATE inference_requests SET
                        status = %s,
                        prompt_tokens = %s,
                        completion_tokens = %s,
                        total_duration_ms = %s,
                        orchestrator_duration_ms = %s,
                        error_code = %s,
                        completed_at = %s
                    WHERE request_id = %s
                    """,
                    (
                        status_value,
                        prompt_tokens,
                        completion_tokens,
                        reported_ms,
                        measured_ms,
                        error_code,
                        now,
                        request_id,
                    ),
                )
            conn.commit()
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        raise _unavailable(exc) from exc


@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
def chat_completions(
    req: ChatCompletionRequest,
    authorization: str | None = Header(default=None),
):
    """Admission control around the blocking dispatch below.

    WHY A CEILING EXISTS HERE AND NOWHERE ELSE. This is the only customer-facing
    handler that blocks. It waits up to DISPATCH_WAIT_SEC -- two minutes by
    default -- for a provider to answer, and for that entire time it occupies one
    of FastAPI's threadpool workers and reopens a database connection on every
    poll. _await_job's own docstring says a few hundred concurrent waits are not
    fine; this is the code that makes that sentence enforceable instead of
    advisory.

    Without it the arithmetic is one-sided: a customer with a valid API key sends
    a few dozen requests for a model nobody has online, each one parks a worker
    for two minutes, and every other endpoint -- /health, the console, the render
    queue -- stops being served. Nothing errors. The service simply stops
    answering, which is the most expensive kind of outage to diagnose because it
    looks like the database.

    TWO CEILINGS, because they refuse different things. The global one protects
    the process. The per-key one stops a single customer occupying every slot and
    turning their own load into everyone else's outage -- with only the global
    limit, the first caller to fill it has denied service to all the others while
    staying entirely within their rights.

    Refused with 503 and a Retry-After, not queued. See limits.py.

    The streaming refusal stays ahead of authentication and ahead of the gates:
    it is the cheapest possible rejection, it costs no database round trip, and
    a request we cannot serve at all must not consume one of the slots that
    requests we can serve are competing for.
    """
    if req.stream:
        raise HTTPException(status_code=400, detail="streaming is not supported yet")

    api_key = _authenticate_api_key(authorization)
    try:
        with limits.inference_in_flight, limits.per_key_slot(api_key["key_id"]):
            return _dispatch_chat_completion(req, api_key)
    except limits.AtCapacity as exc:
        raise _at_capacity(
            f"the inference queue is full: {exc}. The request was not enqueued; "
            "retry shortly."
        ) from exc


def _dispatch_chat_completion(
    req: ChatCompletionRequest,
    api_key: dict,
) -> ChatCompletionResponse:
    """Run a chat completion on a provider's machine and return the result.

    The shape of this changed. It used to authenticate the key, validate that a
    configured node was online, and then call Ollama on the orchestrator's own
    host -- the provider was checked and then ignored. Now the work is enqueued
    for a specific node, that node's agent claims it over a connection it opened
    itself, and this handler waits for the answer to come back.

    The three failures below are deliberately distinct, because they send
    whoever is debugging to three different places:
      503  no node is online and accepting -- a marketplace supply problem
      404  the model is not installed anywhere -- a catalogue problem
      504  a node took the job and did not answer -- a provider problem

    Callers reach this through chat_completions(), which has already refused
    streaming, authenticated the key, and taken a concurrency slot.
    """
    provider = _select_provider_for_model(req.model)
    request_id = f"chatcmpl-{uuid4().hex}"
    job_id = f"job_{uuid4().hex}"
    created = int(time.time())

    payload = {
        "model": req.model,
        "messages": [message.model_dump() for message in req.messages],
        "temperature": req.temperature,
        "max_tokens": req.max_tokens,
    }

    try:
        with db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO inference_requests (
                        request_id, api_key_id, node_id, model, status
                    ) VALUES (%s, %s, %s, %s, 'running')
                    """,
                    (request_id, api_key["key_id"], provider["node_id"], req.model),
                )
                # Same transaction as the audit row. If the job were inserted
                # separately and that second write failed, there would be a
                # request recorded as running that no agent will ever be offered
                # -- it would sit at 'running' until someone read the table and
                # wondered why.
                cur.execute(
                    """
                    INSERT INTO inference_jobs (
                        job_id, request_id, node_id, model, payload
                    ) VALUES (%s, %s, %s, %s, %s)
                    """,
                    (job_id, request_id, provider["node_id"], req.model, Json(payload)),
                )
            conn.commit()
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        raise _unavailable(exc) from exc

    result = _await_job(job_id, dispatch_wait_s())

    if result["status"] != "completed":
        raise HTTPException(
            status_code=502,
            detail=f"provider failed to run the request: {result['error_code'] or 'unknown'}",
        )

    prompt_tokens = result["prompt_tokens"] or 0
    completion_tokens = result["completion_tokens"] or 0
    return ChatCompletionResponse(
        id=request_id,
        created=created,
        model=req.model,
        choices=[
            ChatCompletionChoice(
                message=ChatCompletionMessage(content=result["result_content"] or ""),
                finish_reason=result["finish_reason"] or "stop",
            )
        ],
        usage=ChatUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        ),
    )


@app.get("/v1/usage", response_model=UsageSummary)
def inference_usage(authorization: str | None = Header(default=None)):
    api_key = _authenticate_api_key(authorization)
    try:
        with db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*) AS requests,
                           COALESCE(SUM(prompt_tokens), 0) AS prompt_tokens,
                           COALESCE(SUM(completion_tokens), 0) AS completion_tokens,
                           COALESCE(SUM(total_duration_ms), 0) AS total_duration_ms
                    FROM inference_requests
                    WHERE api_key_id = %s AND status = 'completed'
                    """,
                    (api_key["key_id"],),
                )
                row = cur.fetchone()
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        raise _unavailable(exc) from exc
    prompt_tokens = int(row["prompt_tokens"])
    completion_tokens = int(row["completion_tokens"])
    return UsageSummary(
        requests=int(row["requests"]),
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        total_duration_ms=int(row["total_duration_ms"]),
    )


# ===========================================================================
# ACCOUNTS
#
# Before this section existed, API-key administration was gated on
# `_require_local_demo` -- the caller had to be loopback and LOCAL_DEMO_MODE
# had to be on. That is a deployment posture, not an identity: everyone
# reaching the box from the right address was the same anonymous customer, and
# keys had no owner. These endpoints give a key an owner.
# ===========================================================================


def _authenticate_session(authorization: str | None) -> dict:
    """Resolve a login token to a user row, or raise 401.

    Validity is derived from the row's own columns at read time
    (`auth.session_is_valid`), never from a status column something else has to
    keep current. A sweeper that marked sessions dead on a timer would, when it
    died, leave every expired session working indefinitely with nothing raising
    -- the same failure liveness.py exists to avoid, applied to logins.
    """
    try:
        token = inference.bearer_token(authorization)
    except ValueError as exc:
        raise _unauthorized(str(exc)) from exc

    now = _now()
    try:
        with db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT s.session_id, s.expires_at, s.revoked_at,
                           u.user_id, u.email, u.display_name, u.created_at,
                           u.render_enabled, u.is_operator
                    FROM user_sessions s
                    JOIN users u ON u.user_id = s.user_id
                    WHERE s.token_hash = %s
                    """,
                    (auth.hash_token(token),),
                )
                row = cur.fetchone()
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        raise _unavailable(exc) from exc

    # One message for "no such token", "expired" and "revoked". Distinguishing
    # them tells an attacker holding a stale token that it was once real, which
    # is information we gain nothing by giving away. Contrast with
    # db.NotConfigured, where the distinction helps the operator and helps
    # nobody else.
    if not row or not auth.session_is_valid(row["expires_at"], row["revoked_at"], now):
        raise _unauthorized("invalid or expired session")
    return row


def _user_view(row: dict) -> UserView:
    return UserView(
        user_id=row["user_id"],
        email=row["email"],
        display_name=row["display_name"],
        created_at=row["created_at"],
    )


def _start_session(user_row: dict) -> SessionCreated:
    """Mint a login session for a user who has just proved who they are."""
    secret, token_hash = auth.issue_session_token()
    now = _now()
    expires_at = auth.session_expiry(now)
    try:
        with db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO user_sessions (session_id, user_id, token_hash, expires_at)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (f"sess_{uuid4().hex}", user_row["user_id"], token_hash, expires_at),
                )
                cur.execute(
                    "UPDATE users SET last_login_at = %s WHERE user_id = %s",
                    (now, user_row["user_id"]),
                )
            conn.commit()
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        raise _unavailable(exc) from exc

    return SessionCreated(
        token=secret, expires_at=expires_at, user=_user_view(user_row)
    )


def _hash_signup_password(password: str) -> str:
    try:
        with limits.password_hashing:
            return auth.hash_password(password)
    except limits.AtCapacity as exc:
        raise _at_capacity(
            "too many password operations in progress; retry shortly"
        ) from exc


def _require_login_password(password: str, account: dict | None) -> None:
    if account is None:
        # Spend the same KDF work for an unknown address.
        try:
            with limits.password_hashing:
                auth.hash_password(password)
        except limits.AtCapacity:
            pass
        raise _unauthorized("invalid email or password")

    try:
        with limits.password_hashing:
            valid = auth.verify_password(password, account["password_hash"])
    except limits.AtCapacity as exc:
        raise _at_capacity(
            "too many password operations in progress; retry shortly"
        ) from exc
    except auth.PasswordFormatError as exc:
        raise HTTPException(
            status_code=500, detail=f"stored credential is unreadable: {exc}"
        ) from exc
    if not valid:
        raise _unauthorized("invalid email or password")


@app.post("/v1/auth/signup", response_model=SessionCreated, status_code=201)
def signup(req: SignupRequest, request: Request):
    """Create an account and log it straight in.

    Returning a session here rather than making the caller log in separately is
    not just convenience: it means the password is sent once instead of twice
    for the same outcome.

    Closed deployments refuse here, before anything else happens. Two reasons
    it is first: hashing a password is scrypt and deliberately expensive, so
    doing it ahead of the check would turn a closed endpoint into a free way to
    burn our CPU; and the refusal must not depend on whether the address
    already exists, or a closed signup form becomes an oracle for which of your
    colleagues has an account.
    """
    if not signups_open():
        raise HTTPException(
            status_code=403,
            detail=(
                "new accounts are closed on this deployment. Ask an existing "
                "member to create one for you."
            ),
        )

    # Rate limited before the KDF for the reason the paragraph above gives about
    # the closed-signups check: hashing first would turn a refusal into a free
    # way to burn this machine's CPU and memory. scrypt at these parameters is
    # roughly 16 MiB and hundreds of milliseconds per call, and this endpoint
    # takes no credential, so an unauthenticated caller who can trigger it
    # without limit has a lever with enormous mechanical advantage over a 512 MB
    # instance.
    _rate_limit(limits.auth_by_address, f"signup:{_client_key(request)}")

    email = auth.normalise_email(req.email)
    user_id = f"usr_{uuid4().hex}"
    password_hash = _hash_signup_password(req.password)

    try:
        with db.connect() as conn:
            with conn.cursor() as cur:
                # ON CONFLICT DO NOTHING rather than SELECT-then-INSERT. Two
                # signups for the same address racing each other would both
                # pass a prior existence check and one would then violate the
                # UNIQUE constraint with a 500. Letting the database arbitrate
                # is the only version without a race.
                cur.execute(
                    """
                    INSERT INTO users (user_id, email, password_hash, display_name)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (email) DO NOTHING
                    RETURNING user_id, email, display_name, created_at
                    """,
                    (user_id, email, password_hash, req.display_name),
                )
                row = cur.fetchone()
            conn.commit()
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        raise _unavailable(exc) from exc

    if not row:
        raise HTTPException(status_code=409, detail="that email already has an account")
    return _start_session(row)


@app.post("/v1/auth/login", response_model=SessionCreated)
def login(req: LoginRequest, request: Request):
    """Exchange an email and password for a session token.

    Two limiters, and they answer different attacks. The per-address one bounds
    what a single caller can spend of this machine's CPU. The per-account one
    bounds how many guesses one email can receive from everywhere at once --
    without it, a run distributed across a few hundred addresses stays under
    every per-address limit while still trying thousands of passwords against
    one person's account.

    Both are applied before the database is touched and long before scrypt is,
    because the cost this is protecting is incurred by answering at all. Note
    that the deliberate hash-anyway branch below, which exists so that response
    time does not reveal whether an address is registered, is exactly what makes
    that cost reachable without an account: every request pays for a KDF whether
    or not anything matches. That timing property is worth keeping and it is
    what makes a limiter mandatory rather than nice to have.
    """
    _rate_limit(limits.auth_by_address, f"login:{_client_key(request)}")
    _rate_limit(limits.auth_by_account, f"login:{auth.normalise_email(req.email)}")

    email = auth.normalise_email(req.email)
    try:
        with db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT user_id, email, display_name, password_hash, created_at
                    FROM users WHERE email = %s
                    """,
                    (email,),
                )
                row = cur.fetchone()
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        raise _unavailable(exc) from exc

    _require_login_password(req.password, row)
    return _start_session(row)


@app.post("/v1/auth/logout", status_code=204, response_class=Response)
def logout(authorization: str | None = Header(default=None)):
    """Revoke the presented session.

    Idempotent: revoking an already-revoked session is a 204, because a client
    retrying a logout it never saw the response to must not get an error for
    succeeding twice.
    """
    session = _authenticate_session(authorization)
    try:
        with db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE user_sessions SET revoked_at = %s
                    WHERE session_id = %s AND revoked_at IS NULL
                    """,
                    (_now(), session["session_id"]),
                )
            conn.commit()
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        raise _unavailable(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/v1/auth/me", response_model=UserView)
def current_user(authorization: str | None = Header(default=None)):
    return _user_view(_authenticate_session(authorization))


# Provider accounts use their own tables and share the customer auth primitives.

def _provider_account_view(row: dict) -> ProviderAccountView:
    return ProviderAccountView(
        provider_account_id=row["provider_account_id"],
        email=row["email"],
        display_name=row["display_name"],
        created_at=row["created_at"],
    )


def _bearer_digest(authorization: str | None) -> str:
    try:
        return auth.hash_token(inference.bearer_token(authorization))
    except ValueError as exc:
        raise _unauthorized(str(exc)) from exc


def _authenticate_provider_session(authorization: str | None) -> dict:
    token_hash = _bearer_digest(authorization)
    try:
        with db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT p.provider_account_id, p.email, p.display_name,
                       p.created_at, s.expires_at, s.revoked_at
                FROM provider_sessions s
                JOIN provider_accounts p ON p.provider_account_id = s.provider_account_id
                WHERE s.token_hash = %s
                """,
                (token_hash,),
            )
            row = cur.fetchone()
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        raise _unavailable(exc) from exc
    if not row or not auth.session_is_valid(row["expires_at"], row["revoked_at"], _now()):
        raise _unauthorized("invalid or expired session")
    return row


def _start_provider_session(cur: psycopg.Cursor, account: dict) -> ProviderSessionCreated:
    token, token_hash = auth.issue_session_token()
    now = _now()
    expires_at = auth.session_expiry(now)
    account_id = account["provider_account_id"]
    cur.execute(
        """
        INSERT INTO provider_sessions (session_id, provider_account_id, token_hash, expires_at)
        VALUES (%s, %s, %s, %s)
        """,
        (f"sess_{uuid4().hex}", account_id, token_hash, expires_at),
    )
    cur.execute(
        "UPDATE provider_accounts SET last_login_at = %s WHERE provider_account_id = %s",
        (now, account_id),
    )
    return ProviderSessionCreated(
        token=token, expires_at=expires_at, provider=_provider_account_view(account)
    )


@app.post("/v1/provider/auth/signup", response_model=ProviderSessionCreated, status_code=201)
def provider_signup(req: SignupRequest, request: Request):
    if not signups_open():
        raise HTTPException(
            status_code=403,
            detail="new provider accounts are closed on this deployment",
        )
    _rate_limit(limits.auth_by_address, f"signup:{_client_key(request)}")
    password_hash = _hash_signup_password(req.password)
    try:
        with db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO provider_accounts (provider_account_id, email, password_hash, display_name)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (email) DO NOTHING
                RETURNING provider_account_id, email, display_name, created_at
                """,
                (f"prv_{uuid4().hex}", auth.normalise_email(req.email), password_hash, req.display_name),
            )
            account = cur.fetchone()
            if not account:
                raise HTTPException(status_code=409, detail="that email already has a provider account")
            return _start_provider_session(cur, account)
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        raise _unavailable(exc) from exc


@app.post("/v1/provider/auth/login", response_model=ProviderSessionCreated)
def provider_login(req: LoginRequest, request: Request):
    email = auth.normalise_email(req.email)
    _rate_limit(limits.auth_by_address, f"login:{_client_key(request)}")
    _rate_limit(limits.auth_by_account, f"provider-login:{email}")
    try:
        with db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT provider_account_id, email, password_hash, display_name, created_at
                FROM provider_accounts
                WHERE email = %s
                """,
                (email,),
            )
            account = cur.fetchone()
        _require_login_password(req.password, account)
        with db.connect() as conn, conn.cursor() as cur:
            return _start_provider_session(cur, account)
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        raise _unavailable(exc) from exc


@app.post("/v1/provider/auth/logout", status_code=204, response_class=Response)
def provider_logout(authorization: str | None = Header(default=None)):
    token_hash = _bearer_digest(authorization)
    now = _now()
    try:
        with db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE provider_sessions
                SET revoked_at = COALESCE(revoked_at, %s)
                WHERE token_hash = %s AND expires_at > %s
                RETURNING session_id
                """,
                (now, token_hash, now),
            )
            if not cur.fetchone():
                raise _unauthorized("invalid or expired session")
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        raise _unavailable(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/v1/provider/auth/me", response_model=ProviderAccountView)
def current_provider(authorization: str | None = Header(default=None)):
    return _provider_account_view(_authenticate_provider_session(authorization))


@app.post("/v1/provider/enrolment-keys", response_model=EnrolmentKeyCreated, status_code=201)
def create_enrolment_key(response: Response, authorization: str | None = Header(default=None)):
    account = _authenticate_provider_session(authorization)
    key, digest = auth.issue_enrolment_key()
    now = _now()
    try:
        with db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO provider_enrolment_keys (
                    enrolment_key_id, provider_account_id, key_prefix, key_hash,
                    created_at, expires_at
                ) VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING enrolment_key_id, key_prefix, created_at, expires_at, redeemed_at, revoked_at
                """,
                (f"enr_{uuid4().hex}", account["provider_account_id"], key[:17], digest,
                 now, now + timedelta(minutes=15)),
            )
            row = cur.fetchone()
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        raise _unavailable(exc) from exc
    response.headers["Cache-Control"] = "no-store"
    return EnrolmentKeyCreated(**row, key=key)


@app.get("/v1/provider/enrolment-keys", response_model=list[EnrolmentKeyView])
def list_enrolment_keys(authorization: str | None = Header(default=None)):
    account = _authenticate_provider_session(authorization)
    try:
        with db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT enrolment_key_id, key_prefix, created_at, expires_at, redeemed_at, revoked_at
                FROM provider_enrolment_keys WHERE provider_account_id = %s
                ORDER BY created_at DESC, enrolment_key_id
                """,
                (account["provider_account_id"],),
            )
            return cur.fetchall()
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        raise _unavailable(exc) from exc


@app.delete("/v1/provider/enrolment-keys/{key_id}", status_code=204, response_class=Response)
def revoke_enrolment_key(key_id: str, authorization: str | None = Header(default=None)):
    account = _authenticate_provider_session(authorization)
    try:
        with db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE provider_enrolment_keys SET revoked_at = COALESCE(revoked_at, now())
                WHERE enrolment_key_id = %s AND provider_account_id = %s
                RETURNING enrolment_key_id
                """,
                (key_id, account["provider_account_id"]),
            )
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="enrolment key not found")
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        raise _unavailable(exc) from exc
    return Response(status_code=204)


@app.post("/providers/enrol", response_model=RegisterResponse, status_code=201)
def enrol_node(
    req: RegisterRequest,
    response: Response,
    authorization: str | None = Header(default=None),
):
    """Spend an enrolment key and bind the supplied node ID in one transaction."""
    digest = _bearer_digest(authorization)
    token, token_hash = auth.issue_node_token()
    try:
        with db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE provider_enrolment_keys SET redeemed_at = clock_timestamp()
                WHERE key_hash = %s AND redeemed_at IS NULL AND revoked_at IS NULL
                  AND expires_at > clock_timestamp()
                RETURNING provider_account_id
                """,
                (digest,),
            )
            key = cur.fetchone()
            if not key:
                raise _unauthorized("invalid, expired or already used enrolment key")
            cur.execute(
                """
                INSERT INTO provider_node_credentials (node_id, provider_account_id, token_hash, issued_at)
                VALUES (%s, %s, %s, clock_timestamp())
                ON CONFLICT (node_id) DO UPDATE SET
                    token_hash = EXCLUDED.token_hash, issued_at = clock_timestamp(), revoked_at = NULL
                WHERE provider_node_credentials.provider_account_id = EXCLUDED.provider_account_id
                RETURNING node_id
                """,
                (req.node_id, key["provider_account_id"], token_hash),
            )
            if not cur.fetchone():
                raise HTTPException(status_code=409, detail="node belongs to another provider")
            row = _upsert_node(cur, req, fresh_credential=True)
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        raise _unavailable(exc) from exc
    response.headers["Cache-Control"] = "no-store"
    return RegisterResponse(
        node_id=req.node_id,
        registered_at=row["registered_at"],
        heartbeat_interval_s=heartbeat_interval_s(),
        node_token=token,
    )


@app.get("/v1/provider/nodes", response_model=list[OwnedNodeView])
def list_owned_nodes(authorization: str | None = Header(default=None)):
    account = _authenticate_provider_session(authorization)
    try:
        with db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.node_id, c.revoked_at, n.hostname, n.last_heartbeat_at,
                       COALESCE(n.accepts_work, FALSE) AS accepts_work,
                       COALESCE(n.inference_eligible, FALSE) AS inference_eligible,
                       COALESCE(n.render_eligible, FALSE) AS render_eligible
                FROM provider_node_credentials c
                LEFT JOIN provider_nodes n ON n.node_id = c.node_id
                WHERE c.provider_account_id = %s
                ORDER BY c.node_id
                """,
                (account["provider_account_id"],),
            )
            return cur.fetchall()
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        raise _unavailable(exc) from exc


@app.delete("/v1/provider/nodes/{node_id}", status_code=204, response_class=Response)
def revoke_owned_node(
    node_id: Annotated[str, Path(min_length=8, max_length=64)],
    authorization: str | None = Header(default=None),
):
    account = _authenticate_provider_session(authorization)
    try:
        with db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE provider_node_credentials SET revoked_at = COALESCE(revoked_at, now())
                WHERE node_id = %s AND provider_account_id = %s
                RETURNING node_id
                """,
                (node_id, account["provider_account_id"]),
            )
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="node not found")
            _disable_node_work(cur, node_id)
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        raise _unavailable(exc) from exc
    return Response(status_code=204)


# ===========================================================================
# THE PROVIDER WORK QUEUE
#
# Why a queue instead of the orchestrator calling the agent directly:
# a provider's machine is a gaming PC on a home connection, behind NAT and
# usually behind CGNAT. There is no address to dial. Every packet has to travel
# over a connection the agent opened itself, so the agent asks for work rather
# than being handed it.
#
# The previous implementation selected a provider node and then ran the model
# against LOCAL_OLLAMA_URL -- the orchestrator's own machine. Node selection was
# bookkeeping; execution never left the server. This section is what makes the
# selected node actually do the work.
# ===========================================================================

# How long a claimed job stays claimed before it becomes claimable again.
# Must exceed the slowest honest completion, or a job that is merely slow gets
# handed to a second agent while the first is still working on it -- and then
# the customer pays twice for one answer. Size it against the agent's
# RUN_TIMEOUT_S, which is the longest the provider's runtime is allowed to take.
def job_lease_s() -> int:
    try:
        return max(30, int(os.getenv("JOB_LEASE_SEC", "180")))
    except ValueError:
        return 180


# How long an agent should wait between claim attempts when there is no work.
# Sent to the agent rather than compiled into it, so the whole fleet's polling
# rate can be changed without shipping a new desktop build.
#
# This endpoint answers immediately; it does not hold the request open. The
# interval is therefore the floor on how long a queued job waits before anyone
# picks it up, and also what stops an idle fleet from becoming a self-inflicted
# denial of service. Three seconds is the compromise. Long-polling or
# LISTEN/NOTIFY would beat it on both counts and needs a held connection per
# waiting agent, which is a hosting decision rather than a code one.
def claim_poll_interval_s() -> int:
    try:
        return max(1, int(os.getenv("CLAIM_POLL_INTERVAL_SEC", "3")))
    except ValueError:
        return 3


# How long a customer's request waits for its job to come back before giving up.
def dispatch_wait_s() -> float:
    try:
        return max(5.0, float(os.getenv("DISPATCH_WAIT_SEC", "120")))
    except ValueError:
        return 120.0


def _node_credential(cur: psycopg.Cursor, node_id: str) -> dict | None:
    # Every owned-node claim holds this lock through the queue update. A
    # credential change or revocation therefore has a defined order vs claims.
    cur.execute(
        """
        SELECT token_hash, issued_at, revoked_at
        FROM provider_node_credentials WHERE node_id = %s FOR UPDATE
        """,
        (node_id,),
    )
    return cur.fetchone()


def _verify_node_credential(credential: dict | None, digest: str) -> None:
    if (
        not credential
        or credential["revoked_at"] is not None
        or not secrets.compare_digest(credential["token_hash"], digest)
    ):
        raise _unauthorized("invalid node credential")


def _authenticate_node(
    cur: psycopg.Cursor,
    node_id: str,
    digest: str,
    *,
    telemetry_only: bool = False,
) -> dict:
    credential = _node_credential(cur, node_id)
    if credential or not telemetry_only:
        _verify_node_credential(credential, digest)

    cur.execute(
        """
        SELECT node_token_hash, accepts_work, inference_eligible,
               render_eligible, blender_version, ollama_reachable, last_heartbeat_at
        FROM provider_nodes WHERE node_id = %s FOR UPDATE
        """,
        (node_id,),
    )
    row = cur.fetchone()
    if credential and row is None:
        if telemetry_only:
            raise HTTPException(status_code=404, detail="node telemetry missing; register again")
        raise _unauthorized("node must register before claiming work")
    if not credential:
        legacy_digest = row["node_token_hash"] if row else None
        if not legacy_digest or not secrets.compare_digest(legacy_digest, digest):
            raise _unauthorized("invalid node credential")
    return {**row, "issued_at": credential["issued_at"] if credential else None}


@app.post("/providers/work/claim", response_model=JobClaimResponse)
def claim_work(
    node_id: str,
    authorization: str | None = Header(default=None),
):
    """Hand this node at most one job, or nothing.

    The claim is a single UPDATE ... WHERE job_id IN (SELECT ... FOR UPDATE SKIP
    LOCKED). That combination is what makes it safe for two agents to ask at the
    same instant: SKIP LOCKED steps over rows another transaction is already
    claiming rather than blocking on them, so neither request waits and neither
    job goes out twice.

    A job is claimable when it is queued, OR when it was claimed and its lease
    has since passed. That second clause is the reclaim path, and it is derived
    at read time rather than performed by a sweeper -- a sweeper that died would
    strand every in-flight job in `claimed` forever with nothing raising, which
    is the failure mode this repository keeps designing away from.
    """
    digest = _bearer_digest(authorization)
    interval = claim_poll_interval_s()
    try:
        with db.connect() as conn:
            with conn.cursor() as cur:
                node = _authenticate_node(cur, node_id, digest)
                now = _now()
                if not (
                    node["accepts_work"] and node["inference_eligible"] and node["ollama_reachable"]
                    and liveness(node["last_heartbeat_at"], now, ttl()) == "online"
                ):
                    return JobClaimResponse(job=None, poll_interval_s=interval)
                lease_until = now + timedelta(seconds=job_lease_s())
                cur.execute(
                    """
                    UPDATE inference_jobs SET
                        status = 'claimed',
                        claimed_at = %s,
                        lease_expires_at = %s
                    WHERE job_id IN (
                        SELECT job_id FROM inference_jobs
                        WHERE node_id = %s AND created_at >= %s
                          AND (
                                status = 'queued'
                             OR (status = 'claimed' AND lease_expires_at < %s)
                          )
                        ORDER BY created_at
                        LIMIT 1
                        FOR UPDATE SKIP LOCKED
                    )
                    RETURNING job_id, model, payload, lease_expires_at
                    """,
                    (now, lease_until, node_id, node["issued_at"], now),
                )
                row = cur.fetchone()
            conn.commit()
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        raise _unavailable(exc) from exc

    if not row:
        return JobClaimResponse(job=None, poll_interval_s=interval)

    return JobClaimResponse(
        job=JobOffer(
            job_id=row["job_id"],
            model=row["model"],
            payload=JobPayload(**row["payload"]),
            lease_expires_at=row["lease_expires_at"],
        ),
        poll_interval_s=interval,
    )


@app.post("/providers/work/{job_id}/result", response_model=JobResultAccepted)
def submit_work_result(
    job_id: str,
    req: JobResultRequest,
    node_id: str,
    authorization: str | None = Header(default=None),
):
    """Record what the provider produced. Terminal, and accepted only once.

    The WHERE clause pins both the node and the current status. That means:
    a result from a node that does not hold this job is rejected, and a result
    for a job already finished is rejected. Both matter -- without the first,
    any authenticated node could answer any customer's request; without the
    second, a retried submission could overwrite a completed answer with a
    failure.

    HAND-BUILT SEAM: token counts are stored as evidence of what the runtime
    reported. They are not a bill. Converting them into an amount owed is
    metering, which is hand-built under ADR 0002 and lives in
    agent/core/meter.py -- still NotImplementedError. Nothing here should be
    read as a settled figure.
    """
    digest = _bearer_digest(authorization)
    now = _now()
    terminal = "completed" if req.status == "completed" else "failed"

    try:
        with db.connect() as conn:
            with conn.cursor() as cur:
                node = _authenticate_node(cur, node_id, digest)
                cur.execute(
                    """
                    UPDATE inference_jobs SET
                        status = %s,
                        result_content = %s,
                        finish_reason = %s,
                        prompt_tokens = %s,
                        completion_tokens = %s,
                        total_duration_ms = %s,
                        error_code = %s,
                        completed_at = %s
                    WHERE job_id = %s
                      AND node_id = %s
                      AND status = 'claimed' AND claimed_at >= %s
                    RETURNING request_id
                    """,
                    (
                        terminal,
                        req.content,
                        req.finish_reason,
                        req.prompt_tokens,
                        req.completion_tokens,
                        req.total_duration_ms,
                        req.error_code,
                        now,
                        job_id,
                        node_id,
                        node["issued_at"],
                    ),
                )
                row = cur.fetchone()
            conn.commit()
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        raise _unavailable(exc) from exc

    if not row:
        # Most often a lease that lapsed while the agent was still working, and
        # the job was handed to somebody else. 409 rather than 404 because the
        # job exists -- this agent simply no longer owns it, and it should drop
        # the result rather than retry.
        raise HTTPException(
            status_code=409,
            detail="job is not claimed by this node, or is already finished",
        )

    _finish_inference_request(
        row["request_id"],
        status_value=terminal,
        prompt_tokens=req.prompt_tokens,
        completion_tokens=req.completion_tokens,
        total_duration_ms=req.total_duration_ms,
        error_code=req.error_code,
    )
    return JobResultAccepted(job_id=job_id, status=terminal)


def _select_provider_for_model(model: str | None = None) -> dict:
    """Pick an online node that can serve this model.

    Replaces the DEMO_PROVIDER_NODE_ID lookup, which named one machine in an
    environment variable. That was honest for a single-machine demo and does not
    survive a second provider.

    HAND-BUILT SEAM, and worth being blunt about the size of it. This is
    *selection*, not *scheduling*. It orders by most-recently-seen and takes the
    first match. It does not consider VRAM headroom, how many requests a node is
    already serving, whether the model is loaded or would need a cold start, or
    what the node's measured throughput is. Those are capacity, concurrency and
    model residency -- all hand-built under ADR 0002, none of them written.

    `local_models` is the agent's report of what is on disk. Its own docstring
    is explicit that this answers "what is downloaded", not "what can be served
    right now", and that it must not become a scheduling input. Using it here as
    a filter is the weakest defensible reading: it excludes nodes that certainly
    cannot serve the model, and claims nothing about the ones that remain.
    """
    now = _now()
    window = ttl()
    try:
        with db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT n.node_id, hostname, accepts_work, ollama_reachable,
                           local_models, registered_at, last_heartbeat_at
                    FROM provider_nodes n
                    JOIN provider_node_credentials c ON c.node_id = n.node_id
                    WHERE c.revoked_at IS NULL AND n.inference_eligible
                      AND accepts_work = TRUE
                      AND ollama_reachable = TRUE
                      AND last_heartbeat_at IS NOT NULL
                    ORDER BY last_heartbeat_at DESC
                    """
                )
                rows = cur.fetchall()
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        raise _unavailable(exc) from exc

    # Liveness is recomputed here rather than trusted from the query, because
    # "has a recent heartbeat" is a derived fact and this is the one place that
    # derives it. A SQL predicate on last_heartbeat_at would be a second
    # implementation of liveness.py that could drift from it silently.
    live = [r for r in rows if liveness(r["last_heartbeat_at"], now, window) == "online"]

    if not live:
        raise HTTPException(
            status_code=503,
            detail="no provider is currently online and accepting work",
        )

    if model is None:
        return live[0]

    for row in live:
        if model in (row["local_models"] or []):
            return row

    raise HTTPException(
        status_code=404,
        detail=f"model {model!r} is not installed on any online provider",
    )


def _await_job(job_id: str, deadline_s: float) -> dict:
    """Block until the agent reports back, or the wait runs out.

    Polling the row rather than holding a notification channel open. LISTEN /
    NOTIFY would be lower latency and is the obvious next step; it also needs a
    dedicated connection per waiter, which this file has nowhere to keep because
    there is no pool yet. Polling is the version that is correct at this size.

    Note this blocks a threadpool worker for the duration. FastAPI runs `def`
    handlers in a threadpool, so a few concurrent waits are fine and a few
    hundred are not. That ceiling arrives at the same time a connection pool
    does, and both are visible as slowness rather than as wrong answers.
    """
    started = time.monotonic()
    delay = 0.25
    while True:
        try:
            with db.connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT status, result_content, finish_reason,
                               prompt_tokens, completion_tokens,
                               total_duration_ms, error_code
                        FROM inference_jobs WHERE job_id = %s
                        """,
                        (job_id,),
                    )
                    row = cur.fetchone()
        except (db.NotConfigured, psycopg.Error, OSError) as exc:
            raise _unavailable(exc) from exc

        if row and row["status"] in ("completed", "failed"):
            return row

        if time.monotonic() - started >= deadline_s:
            raise HTTPException(
                status_code=504,
                detail=(
                    "provider did not return a result in time; "
                    "the job stays queued and may still complete"
                ),
            )

        time.sleep(delay)
        # Back off gently. A fast model answers in the first second or two, so
        # start tight; a slow one should not be polled fifty times a second for
        # two minutes.
        delay = min(delay * 1.5, 2.0)


# ===========================================================================
# RENDERING
#
# The second workload class. See docs/adr/0006-render-batch-jobs.md.
#
# Three things here differ from the inference path above, and each one is a
# consequence of the payload being a file rather than a field:
#
# 1. NOTHING BLOCKS. There is no render equivalent of _await_job(). A render
#    runs for minutes to hours, and holding a FastAPI threadpool worker open
#    for that is not something a 512 MB instance survives twice. Submission
#    returns immediately and the client polls.
#
# 2. NO BYTES PASS THROUGH THIS PROCESS. Every file movement is a presigned
#    URL handed to somebody else -- see orchestrator/storage.py for why, and
#    for what a provider can and cannot do with one.
#
# 3. THE FRAME IS THE UNIT. Claim, lease, retry and progress are all per frame,
#    because a 120-frame animation that restarts because frame 87 failed is not
#    a product.
#
# THE GATE. Both `users.render_enabled` and `provider_nodes.render_eligible`
# default FALSE and both must be TRUE for any byte to move. This is what stands
# in for the sandbox that does not exist yet: a .blend can carry embedded
# Python, so running one is executing a stranger's code on somebody's gaming
# PC. The gate bounds that to machines whose owner opted in by hand. It is a
# column, not a sandbox, and it must never be described as one.
# ===========================================================================


# Sized for the work, not copied from inference. JOB_LEASE_SEC is 180 because a
# chat request is short; a Cycles frame at production sample counts can run for
# half an hour on a consumer card. The comment above job_lease_s() explains the
# cost of getting this too low -- the frame is handed to a second provider while
# the first is still rendering it, and the customer pays twice for one image.
#
# Too high has a cost as well, and it is the one this default leans towards: a
# provider that crashes mid-frame leaves that frame unclaimable for the full
# window. Half an hour of a stalled frame is the price of not double-rendering,
# and it is the right side to err on until agent/core/lease.py exists and a
# healthy agent can renew a lease it still holds.
def render_lease_s() -> int:
    try:
        return max(60, int(os.getenv("RENDER_LEASE_SEC", "1800")))
    except ValueError:
        return 1800


# How long the customer has to complete an upload. Generous, because this is a
# multi-hundred-megabyte PUT over a domestic connection and the failure mode of
# a short window is a 403 at ninety percent with no useful message.
def render_upload_ttl_s() -> int:
    try:
        return max(60, int(os.getenv("RENDER_UPLOAD_TTL_SEC", "3600")))
    except ValueError:
        return 3600


# How long a download link lives. Short, because these are handed out on every
# poll of the artifacts endpoint and are trivially re-issued.
def render_download_ttl_s() -> int:
    try:
        return max(60, int(os.getenv("RENDER_DOWNLOAD_TTL_SEC", "900")))
    except ValueError:
        return 900


# How many times one frame may be handed out before it is considered failed.
#
# A ceiling has to exist. Without one, a frame that reliably crashes Blender is
# offered to every provider in the fleet, forever: each one takes it, dies,
# lets the lease lapse, and the next one picks it up. The job never finishes,
# nothing raises, and every provider burns GPU time on the same poisoned frame.
# Three attempts distinguishes "this machine had a bad moment" from "this frame
# cannot be rendered".
def max_frame_attempts() -> int:
    try:
        return max(1, int(os.getenv("RENDER_MAX_ATTEMPTS", "3")))
    except ValueError:
        return 3



def _version_series(version: str) -> str:
    """"4.3.2" -> "4.3". The unit a Blender job is actually specified in.

    THE SEAM THIS FIXES. A customer picks a version from a dropdown offering
    4.3, 4.2 and 3.6 -- release series, because that is how Blender's
    compatibility is described and what a scene file is authored against. A node
    reports what `blender --version` printed, which is a full build number like
    4.3.2. Comparing those two strings for equality is always false, so the
    claim query would return nothing, forever, on a fleet that was working
    perfectly. Nothing would raise; every job would simply sit `queued` and look
    like a capacity problem.

    Matching on the series is also the correct behaviour rather than merely a
    workaround: 4.3.2 is the right renderer for a job that asked for 4.3, and
    demanding an exact patch match would idle capable machines over a point
    release.

    Across series it stays strict. 4.2 does not render a 4.3 job: the EEVEE
    engine identifier changed between them and geometry-node behaviour differs,
    so the wrong series produces different pixels from the same file with
    nothing raising -- the failure this whole column exists to prevent.
    """
    parts = version.split(".")
    if len(parts) < 2:
        return version
    return f"{parts[0]}.{parts[1]}"


def _render_storage():
    """The bucket, or a 503 that names the missing variable.

    StorageNotConfigured is turned into 503 rather than 500 for the same reason
    db.NotConfigured is: the request is not malformed and the caller did nothing
    wrong. Somebody has not finished setting the deployment up, and the message
    has to say which variable so that person can act on it.
    """
    try:
        return storage.bucket()
    except storage.StorageNotConfigured as exc:
        raise HTTPException(
            status_code=503,
            detail=f"render storage is not configured: {exc}",
        ) from exc


def _require_render_enabled(user_row: dict) -> None:
    """The customer half of the gate.

    403 with an explicit reason rather than pretending the feature does not
    exist. During the pilot this is expected to be the common answer, and a
    customer who hits it needs to know it is a deliberate restriction and not a
    fault.
    """
    if not user_row.get("render_enabled"):
        raise HTTPException(
            status_code=403,
            detail=(
                "rendering is limited to accounts enabled for the pilot. "
                "A .blend file can execute embedded code on the provider's "
                "machine, and the sandbox that would contain it is not built "
                "yet, so render jobs run only on hardware whose owner has "
                "explicitly opted in."
            ),
        )


# The derived status of one frame, as a SQL expression.
#
# DERIVED, NEVER SWEPT -- the rule this schema has now applied four times. A
# frame whose lease has lapsed is claimable again the instant the lease passes,
# with no background task involved, because a background task that dies leaves
# every in-flight frame stuck in `claimed` forever and nothing raises.
#
# The `attempts >= max` arm is what stops that same derivation from stranding a
# poisoned frame in a permanent "about to be retried" state: once it has used
# its attempts it reads as failed, which is both true and terminal, and the job
# containing it can finish.
_FRAME_STATUS_SQL = """
    CASE
        WHEN f.status = 'completed' THEN 'completed'
        WHEN f.status = 'failed' THEN 'failed'
        WHEN f.status = 'claimed' AND f.lease_expires_at > %(now)s THEN 'running'
        WHEN f.attempts >= %(max_attempts)s THEN 'failed'
        ELSE 'queued'
    END
"""


def _derive_job_status(job_row: dict, counts: dict) -> str:
    """What the customer is shown. Never read from render_jobs.status.

    That column carries only the three states that are facts about the job
    itself and are invisible in its frames -- awaiting_upload, queued,
    cancelled. Everything else is arithmetic over the frames, done here, on
    every read.
    """
    if job_row["status"] == "cancelled":
        return "cancelled"
    if job_row["status"] == "awaiting_upload":
        return "awaiting_upload"

    total = counts["total"]
    if total == 0:
        # Confirmed as uploaded but fan-out has not run, or ran against an
        # empty range. Either way there is nothing to be running.
        return "queued"
    if counts["completed"] == total:
        return "completed"
    if counts["completed"] + counts["failed"] == total:
        # Every frame reached a terminal state and at least one did not make it.
        return "failed"
    if counts["running"] > 0:
        return "running"
    return "queued"


def _frame_counts(cur, job_id: str, now: datetime) -> dict:
    cur.execute(
        f"""
        SELECT COUNT(*) AS total,
               COUNT(*) FILTER (WHERE {_FRAME_STATUS_SQL} = 'completed') AS completed,
               COUNT(*) FILTER (WHERE {_FRAME_STATUS_SQL} = 'failed') AS failed,
               COUNT(*) FILTER (WHERE {_FRAME_STATUS_SQL} = 'running') AS running
        FROM render_frames f
        WHERE f.job_id = %(job_id)s
        """,
        {"job_id": job_id, "now": now, "max_attempts": max_frame_attempts()},
    )
    row = cur.fetchone()
    return {
        "total": int(row["total"]),
        "completed": int(row["completed"]),
        "failed": int(row["failed"]),
        "running": int(row["running"]),
    }


def _render_job_view(job_row: dict, counts: dict, frames: list | None = None) -> RenderJobView:
    return RenderJobView(
        job_id=job_row["job_id"],
        status=_derive_job_status(job_row, counts),
        blender_version=job_row["blender_version"],
        engine=job_row["engine"],
        frame_start=job_row["frame_start"],
        frame_end=job_row["frame_end"],
        output_format=job_row["output_format"],
        frame_count=counts["total"] or (job_row["frame_end"] - job_row["frame_start"] + 1),
        frames_completed=counts["completed"],
        frames_failed=counts["failed"],
        frames_running=counts["running"],
        spending_limit_usd=(
            float(job_row["spending_limit_usd"])
            if job_row["spending_limit_usd"] is not None
            else None
        ),
        source_bytes=job_row["source_bytes"],
        error_code=job_row["error_code"],
        created_at=job_row["created_at"],
        uploaded_at=job_row["uploaded_at"],
        frames=frames,
    )


def _load_render_job(cur, job_id: str, user_id: str) -> dict:
    """Fetch a job, scoped to its owner.

    The user_id is in the WHERE clause rather than checked afterwards, so a job
    belonging to somebody else is indistinguishable from one that does not
    exist. Checking after the fetch would leak the existence of other people's
    jobs through the difference between 403 and 404.
    """
    cur.execute(
        """
        SELECT job_id, user_id, status, blender_version, engine,
               frame_start, frame_end, output_format, source_object_key,
               source_bytes, declared_source_bytes, spending_limit_usd, error_code,
               created_at, uploaded_at, cancelled_at
        FROM render_jobs
        WHERE job_id = %s AND user_id = %s
        """,
        (job_id, user_id),
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="no such render job")
    return row


@app.post("/v1/render/jobs", response_model=RenderJobCreated, status_code=202)
def create_render_job(
    req: RenderJobCreateRequest,
    authorization: str | None = Header(default=None),
):
    """Accept a render job and return somewhere to put the file.

    202, not 201: the job is not usable yet. It has no frames and cannot be
    claimed by anybody until the upload is confirmed, and saying 201 would
    describe a resource that does not do what its name suggests.

    The file does not come through here and never will.

    THE DECLARED SIZE IS NOW A CONSTRAINT, not a note. `source_bytes` is signed
    into the upload URL, so the bucket refuses any PUT that does not carry
    exactly that Content-Length. Previously the URL authorised an upload of
    unbounded size -- a customer could declare forty megabytes and push forty
    gigabytes through a URL we minted for them, and nothing would notice until
    the storage bill. A presigned URL is a bearer capability; the only safe
    version of one is narrow.

    A client whose file changed size between here and the upload gets a 403 from
    the bucket and should re-declare via POST /v1/render/jobs/{id}/upload-url,
    which re-signs against the same stored figure.
    """
    user = _authenticate_session(authorization)
    _require_render_enabled(user)
    bucket = _render_storage()

    job_id = uuid4().hex
    key = storage.source_key(job_id)
    now = _now()
    ttl = render_upload_ttl_s()

    try:
        upload_url = bucket.presign_put(
            key, ttl, now=now, content_length=req.source_bytes
        )
    except storage.StorageError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    try:
        with db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO render_jobs (
                        job_id, user_id, status, blender_version, engine,
                        frame_start, frame_end, output_format,
                        source_object_key, declared_source_bytes,
                        spending_limit_usd, created_at
                    ) VALUES (
                        %s, %s, 'awaiting_upload', %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        job_id,
                        user["user_id"],
                        req.blender_version,
                        req.engine,
                        req.frame_start,
                        req.frame_end,
                        req.output_format,
                        key,
                        req.source_bytes,
                        req.spending_limit_usd,
                        now,
                    ),
                )
            conn.commit()
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        raise _unavailable(exc) from exc

    return RenderJobCreated(
        job_id=job_id,
        status="awaiting_upload",
        frame_count=req.frame_end - req.frame_start + 1,
        upload_url=upload_url,
        upload_expires_at=now + timedelta(seconds=ttl),
    )



@app.post("/v1/render/jobs/{job_id}/upload-url", response_model=RenderJobCreated)
def reissue_render_upload_url(
    job_id: str,
    authorization: str | None = Header(default=None),
):
    """Mint a fresh presigned PUT for a job that has not been uploaded yet.

    WHY THIS EXISTS. The URL from POST /v1/render/jobs is short-lived and the
    thing it is used for -- a multi-hundred-megabyte upload over a domestic
    connection -- is not. Without this endpoint a signature that lapses at
    ninety percent leaves the job stranded at `awaiting_upload` with no way
    forward but creating a second job, which abandons the first as a permanent
    orphan row. That is a dead end reachable by nothing worse than a slow
    connection.

    Deliberately restricted to `awaiting_upload`. Once a job has been confirmed
    and fanned out into frames, re-issuing a PUT for its source would let the
    customer swap the .blend underneath frames that are already rendering, and
    the animation would come back with two different scenes in it. There would
    be no error anywhere -- just a result that is wrong in a way only a human
    watching the output would catch.
    """
    user = _authenticate_session(authorization)
    _require_render_enabled(user)
    bucket = _render_storage()
    now = _now()
    ttl = render_upload_ttl_s()

    try:
        with db.connect() as conn:
            with conn.cursor() as cur:
                job = _load_render_job(cur, job_id, user["user_id"])
                counts = _frame_counts(cur, job_id, now)
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        raise _unavailable(exc) from exc

    if job["status"] != "awaiting_upload":
        raise HTTPException(
            status_code=409,
            detail=(
                "this job's source file is already committed; "
                "submit a new job to render a different file"
            ),
        )

    try:
        # Re-signed against the size the job was created with, so a reissued URL
        # is exactly as narrow as the original. Minting this one unbounded would
        # make the retry path a way to opt out of the limit -- ask for a fresh
        # URL, upload anything.
        #
        # Falls back to unbounded only for jobs created before that column
        # existed, which cannot have a declared figure to sign. Those are
        # bounded by the size check at confirmation instead.
        upload_url = bucket.presign_put(
            job["source_object_key"],
            ttl,
            now=now,
            content_length=job.get("declared_source_bytes"),
        )
    except storage.StorageError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return RenderJobCreated(
        job_id=job_id,
        status="awaiting_upload",
        frame_count=counts["total"] or (job["frame_end"] - job["frame_start"] + 1),
        upload_url=upload_url,
        upload_expires_at=now + timedelta(seconds=ttl),
    )


@app.post("/v1/render/jobs/{job_id}/uploaded", response_model=RenderJobView)
def confirm_render_upload(
    job_id: str,
    authorization: str | None = Header(default=None),
):
    """Verify the upload actually happened, then fan the job out into frames.

    THE HEAD IS NOT CEREMONY. A client saying "I uploaded it" is a claim; the
    HEAD is a measurement. Without it, an upload that failed halfway produces a
    job whose frames every provider in the fleet will fail to render one after
    another, each failure looking like a fault on that provider's machine. The
    cost of checking is one request; the cost of not checking is a support
    investigation pointed at entirely the wrong place.

    IDEMPOTENT. A client that retries this -- because the response was lost,
    not because anything went wrong -- must not double the queue. The INSERT is
    ON CONFLICT DO NOTHING against the (job_id, frame_number) unique
    constraint, so a second call inserts nothing and returns the same view.
    """
    user = _authenticate_session(authorization)
    _require_render_enabled(user)
    bucket = _render_storage()
    now = _now()

    try:
        with db.connect() as conn:
            with conn.cursor() as cur:
                job = _load_render_job(cur, job_id, user["user_id"])

                if job["status"] == "cancelled":
                    raise HTTPException(
                        status_code=409, detail="this job was cancelled"
                    )

                if job["status"] == "awaiting_upload":
                    try:
                        size = bucket.head(job["source_object_key"])
                    except storage.StorageError as exc:
                        raise HTTPException(status_code=503, detail=str(exc)) from exc

                    if size is None:
                        raise HTTPException(
                            status_code=409,
                            detail=(
                                "no file has been uploaded for this job yet. "
                                "PUT the .blend to the upload_url first."
                            ),
                        )

                    # The measurement is only evidence if something acts on it.
                    # MAX_SOURCE_BYTES' own comment calls this HEAD the real
                    # enforcement and the submission-time check a courtesy, but
                    # the number was being read and stored without ever being
                    # compared: a job could declare one byte, upload two
                    # hundred thousand, and be confirmed. The presigned PUT
                    # carries no size condition, so this is the only place the
                    # true size is ever known.
                    if size > MAX_SOURCE_BYTES:
                        raise HTTPException(
                            status_code=413,
                            detail=(
                                f"the uploaded file is {size} bytes; the limit "
                                f"is {MAX_SOURCE_BYTES}. The job was not queued."
                            ),
                        )

                    # An empty object is a failed upload that returned 200. Left
                    # alone it fans out into frames that every provider in the
                    # fleet will fail on in turn, each failure looking like a
                    # fault on that provider's machine rather than on the file.
                    if size == 0:
                        raise HTTPException(
                            status_code=409,
                            detail=(
                                "the uploaded file is empty. The upload did not "
                                "complete; PUT the .blend again."
                            ),
                        )

                    # THE PRODUCT OF TWO LIMITS IS A THIRD LIMIT, and it was
                    # the one nobody wrote down. A provider re-downloads the
                    # whole .blend for every frame it renders, so this job's
                    # real cost in bandwidth is the source size multiplied by
                    # the frame count. MAX_SOURCE_BYTES (2 GiB) and
                    # MAX_FRAMES_PER_JOB (2,000) are each defensible alone and
                    # multiply out to roughly four terabytes of provider
                    # bandwidth from one submission -- before a single retry.
                    #
                    # Checked here because this is the first moment both
                    # numbers are known and true: the frame range came in at
                    # submission, and the real size only exists after the HEAD.
                    frame_count = job["frame_end"] - job["frame_start"] + 1
                    transfer = size * frame_count
                    if transfer > MAX_JOB_TRANSFER_BYTES:
                        raise HTTPException(
                            status_code=413,
                            detail=(
                                f"this job would move {transfer} bytes of source "
                                f"data ({size} bytes x {frame_count} frames), over "
                                f"the {MAX_JOB_TRANSFER_BYTES}-byte limit for one "
                                "job. Render fewer frames per job, or reduce the "
                                "scene file. The job was not queued."
                            ),
                        )

                    # Fan out. One row per frame, inclusive of both ends --
                    # Blender's -f is inclusive and a customer asking for 1 to
                    # 24 means 24 frames, not 23.
                    frames = [
                        (uuid4().hex, job_id, number, now)
                        for number in range(job["frame_start"], job["frame_end"] + 1)
                    ]
                    cur.executemany(
                        """
                        INSERT INTO render_frames (frame_id, job_id, frame_number, created_at)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (job_id, frame_number) DO NOTHING
                        """,
                        frames,
                    )
                    cur.execute(
                        """
                        UPDATE render_jobs
                        SET status = 'queued', source_bytes = %s, uploaded_at = %s
                        WHERE job_id = %s AND status = 'awaiting_upload'
                        """,
                        (size, now, job_id),
                    )
                    job["status"] = "queued"
                    job["source_bytes"] = size
                    job["uploaded_at"] = now

                counts = _frame_counts(cur, job_id, now)
            conn.commit()
    except HTTPException:
        raise
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        raise _unavailable(exc) from exc

    return _render_job_view(job, counts)


@app.get("/v1/render/jobs", response_model=RenderJobList)
def list_render_jobs(authorization: str | None = Header(default=None)):
    """This customer's jobs, newest first. No frame detail.

    Returning every frame of every job here would be a megabyte of JSON to draw
    a progress bar; the counts are computed in the database instead.
    """
    user = _authenticate_session(authorization)
    now = _now()

    try:
        with db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT j.job_id, j.status, j.blender_version, j.engine,
                           j.frame_start, j.frame_end, j.output_format,
                           j.source_bytes, j.spending_limit_usd, j.error_code,
                           j.created_at, j.uploaded_at,
                           COUNT(f.frame_id) AS total,
                           COUNT(f.frame_id) FILTER (WHERE {_FRAME_STATUS_SQL} = 'completed') AS completed,
                           COUNT(f.frame_id) FILTER (WHERE {_FRAME_STATUS_SQL} = 'failed') AS failed,
                           COUNT(f.frame_id) FILTER (WHERE {_FRAME_STATUS_SQL} = 'running') AS running
                    FROM render_jobs j
                    LEFT JOIN render_frames f ON f.job_id = j.job_id
                    WHERE j.user_id = %(user_id)s
                    GROUP BY j.job_id
                    ORDER BY j.created_at DESC
                    LIMIT 200
                    """,
                    {
                        "user_id": user["user_id"],
                        "now": now,
                        "max_attempts": max_frame_attempts(),
                    },
                )
                rows = cur.fetchall()
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        raise _unavailable(exc) from exc

    return RenderJobList(
        jobs=[
            _render_job_view(
                row,
                {
                    "total": int(row["total"]),
                    "completed": int(row["completed"]),
                    "failed": int(row["failed"]),
                    "running": int(row["running"]),
                },
            )
            for row in rows
        ]
    )


@app.get("/v1/render/jobs/{job_id}", response_model=RenderJobView)
def get_render_job(job_id: str, authorization: str | None = Header(default=None)):
    """One job, with per-frame detail.

    Per frame, because the frame is the unit of work. "9 of 24 done, 1 failed
    and retrying" is a true description of the state; a single percentage is a
    summary that hides the one number the customer actually needs.
    """
    user = _authenticate_session(authorization)
    now = _now()

    try:
        with db.connect() as conn:
            with conn.cursor() as cur:
                job = _load_render_job(cur, job_id, user["user_id"])
                cur.execute(
                    f"""
                    SELECT f.frame_number,
                           {_FRAME_STATUS_SQL} AS derived_status,
                           f.attempts, f.render_seconds, f.error_code, f.completed_at
                    FROM render_frames f
                    WHERE f.job_id = %(job_id)s
                    ORDER BY f.frame_number
                    """,
                    {
                        "job_id": job_id,
                        "now": now,
                        "max_attempts": max_frame_attempts(),
                    },
                )
                frame_rows = cur.fetchall()
                counts = _frame_counts(cur, job_id, now)
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        raise _unavailable(exc) from exc

    frames = [
        RenderFrameView(
            frame_number=row["frame_number"],
            status=row["derived_status"],
            attempts=row["attempts"],
            render_seconds=(
                float(row["render_seconds"]) if row["render_seconds"] is not None else None
            ),
            error_code=row["error_code"],
            completed_at=row["completed_at"],
        )
        for row in frame_rows
    ]
    return _render_job_view(job, counts, frames=frames)


@app.get("/v1/render/jobs/{job_id}/artifacts", response_model=RenderArtifactList)
def render_job_artifacts(job_id: str, authorization: str | None = Header(default=None)):
    """Short-lived download links for the frames that finished.

    Partial by design: a customer whose job is nineteen frames into twenty-four
    can have those nineteen now. Waiting for the whole animation to finish
    before releasing anything would be a worse product and no safer.

    DELIBERATELY NOT GATED on `render_enabled`, unlike every other endpoint in
    this group. The gate exists to stop untrusted code from executing on a
    provider's machine; handing back a PNG that already rendered executes
    nothing and puts no provider at risk. Gating it would mean that revoking
    an account's pilot access also destroys its access to work already
    finished, which is a data-loss behaviour dressed up as a security control.
    Ownership is still enforced -- `_load_render_job` scopes by user_id, so
    another tenant's job is a 404 here, not a 403.
    """
    user = _authenticate_session(authorization)
    bucket = _render_storage()
    now = _now()
    ttl = render_download_ttl_s()

    try:
        with db.connect() as conn:
            with conn.cursor() as cur:
                _load_render_job(cur, job_id, user["user_id"])
                cur.execute(
                    """
                    SELECT frame_number, output_object_key, output_bytes
                    FROM render_frames
                    WHERE job_id = %s AND status = 'completed'
                      AND output_object_key IS NOT NULL
                    ORDER BY frame_number
                    """,
                    (job_id,),
                )
                rows = cur.fetchall()
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        raise _unavailable(exc) from exc

    return RenderArtifactList(
        job_id=job_id,
        artifacts=[
            RenderArtifact(
                frame_number=row["frame_number"],
                url=bucket.presign_get(row["output_object_key"], ttl, now=now),
                bytes=row["output_bytes"],
            )
            for row in rows
        ],
        expires_at=now + timedelta(seconds=ttl),
    )


@app.delete("/v1/render/jobs/{job_id}", response_model=RenderJobView)
def cancel_render_job(job_id: str, authorization: str | None = Header(default=None)):
    """Stop handing out new frames for this job.

    WHAT THIS DOES NOT DO is reach into a provider's machine and stop a render
    that is already running. There is no channel to do that -- the agent is
    behind NAT and only ever calls us -- and inventing one is not what a cancel
    button is for. A frame already claimed finishes, and its provider is owed
    for it.

    The claim query requires the parent job to be `queued`, so setting
    `cancelled` here is sufficient to stop every future claim. The frames are
    deliberately left as they are: rewriting them would destroy the record of
    what was actually dispatched, which is the thing an argument about a bill
    would need.
    """
    user = _authenticate_session(authorization)
    now = _now()

    try:
        with db.connect() as conn:
            with conn.cursor() as cur:
                job = _load_render_job(cur, job_id, user["user_id"])
                if job["status"] != "cancelled":
                    cur.execute(
                        """
                        UPDATE render_jobs
                        SET status = 'cancelled', cancelled_at = %s
                        WHERE job_id = %s
                        """,
                        (now, job_id),
                    )
                    job["status"] = "cancelled"
                counts = _frame_counts(cur, job_id, now)
            conn.commit()
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        raise _unavailable(exc) from exc

    return _render_job_view(job, counts)


# ---------------------------------------------------------------------------
# The provider half.
# ---------------------------------------------------------------------------


@app.post("/providers/render/claim", response_model=RenderClaimResponse)
def claim_render_frame(
    node_id: str,
    authorization: str | None = Header(default=None),
):
    """Hand this node at most one frame, or nothing.

    The claim is the same UPDATE ... WHERE frame_id IN (SELECT ... FOR UPDATE
    SKIP LOCKED) shape as claim_work() above, and that is deliberate: the
    semantics were reasoned about once and are copied, not re-derived. SKIP
    LOCKED is what makes it safe for two agents to ask in the same instant.

    Unlike inference, no node was chosen when the work was queued. Frames sit
    unassigned and whichever eligible node asks first gets the oldest one. A
    frame has no affinity to a machine the way a resident model does, so
    pre-assigning would idle the rest of the fleet behind one node's backlog.

    THE GATE IS HERE, both halves of it. `render_eligible` is checked before
    any row is touched, and it defaults FALSE. This is the line that stops a
    stranger's .blend from executing on a provider who never agreed to run one.

    The customer half is re-checked here too, as a join on `users`, because the
    check at submission time only covers the frames that had not been handed
    out yet. Revoking `render_enabled` on an account whose job was already
    queued used to leave every remaining frame flowing to providers, which
    makes the column a filter on new submissions rather than a switch that
    turns the account off. Re-reading it on every claim is what makes
    revocation take effect on the next frame instead of the next job.
    """
    digest = _bearer_digest(authorization)
    interval = claim_poll_interval_s()
    try:
        with db.connect() as conn:
            with conn.cursor() as cur:
                node = _authenticate_node(cur, node_id, digest)
                now = _now()
                node_blender = node["blender_version"]
                if not (
                    node["accepts_work"] and node["render_eligible"] and node_blender
                    and liveness(node["last_heartbeat_at"], now, ttl()) == "online"
                ):
                    return RenderClaimResponse(frame=None, poll_interval_s=interval)
                bucket = _render_storage()
                lease_until = now + timedelta(seconds=render_lease_s())
                cur.execute(
                    """
                    UPDATE render_frames SET
                        status = 'claimed',
                        node_id = %(node_id)s,
                        claimed_at = %(now)s,
                        lease_expires_at = %(lease_until)s,
                        attempts = attempts + 1
                    WHERE frame_id IN (
                        SELECT f.frame_id
                        FROM render_frames f
                        JOIN render_jobs j ON j.job_id = f.job_id
                        JOIN users u ON u.user_id = j.user_id
                        WHERE j.status = 'queued'
                          AND u.render_enabled
                          AND split_part(j.blender_version, '.', 1)
                              || '.' || split_part(j.blender_version, '.', 2)
                              = %(blender_series)s
                          AND f.attempts < %(max_attempts)s
                          AND (
                                f.status = 'queued'
                             OR (f.status = 'claimed' AND f.lease_expires_at < %(now)s)
                          )
                        ORDER BY f.created_at, f.frame_number
                        LIMIT 1
                        FOR UPDATE OF f SKIP LOCKED
                    )
                    RETURNING frame_id, job_id, frame_number, lease_expires_at
                    """,
                    {
                        "node_id": node_id,
                        "now": now,
                        "lease_until": lease_until,
                        "blender_series": _version_series(node_blender),
                        "max_attempts": max_frame_attempts(),
                    },
                )
                row = cur.fetchone()

                if not row:
                    conn.rollback()
                    return RenderClaimResponse(frame=None, poll_interval_s=interval)

                cur.execute(
                    """
                    SELECT blender_version, engine, output_format, source_object_key
                    FROM render_jobs WHERE job_id = %s
                    """,
                    (row["job_id"],),
                )
                job = cur.fetchone()
            conn.commit()
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        raise _unavailable(exc) from exc

    output_key = storage.frame_key(row["job_id"], row["frame_number"], job["output_format"])

    # Both URLs expire with the lease, not after it. A provider that has lost
    # the frame must not still be able to write to the bucket for it -- the
    # frame may already have been reclaimed and finished by somebody else, and
    # a late PUT would overwrite a good result with a stale one.
    url_ttl = max(60, int((row["lease_expires_at"] - now).total_seconds()))

    return RenderClaimResponse(
        frame=RenderFrameOffer(
            frame_id=row["frame_id"],
            job_id=row["job_id"],
            frame_number=row["frame_number"],
            blender_version=job["blender_version"],
            engine=job["engine"],
            output_format=job["output_format"],
            source_url=bucket.presign_get(job["source_object_key"], url_ttl, now=now),
            output_url=bucket.presign_put(output_key, url_ttl, now=now),
            lease_expires_at=row["lease_expires_at"],
        ),
        poll_interval_s=interval,
    )


def _reject_output(bucket, output_key: str, stored: int | None, output_format: str) -> str | None:
    """Why this frame's upload is not acceptable, or None if it is.

    A SUCCESS REPORT IS A CLAIM; THIS IS THE MEASUREMENT. The provider is
    untrusted by design -- it is a stranger's gaming PC -- so "completed" means
    only that a machine we do not own sent us that word. Before this function
    existed the sole check was that *something* was at the key, which accepted
    two shapes of nothing:

    A zero-byte object. That is what an empty PUT produces, and it is also what
    a crash between rendering and uploading produces. It counted as a finished
    frame, completed the job, and was offered to the customer as their render.
    `stored == 0` is falsy in Python but the code tested `stored is None`, so
    the empty case fell through to success -- a defect that reads as correct.

    Arbitrary content. A provider could PUT the string "this is not a png",
    report completed, and the customer would download exactly those bytes with
    a .png key. The magic-number check closes that: it costs one ranged GET of
    sixteen bytes against an object we already had to HEAD.

    WHAT THIS DOES NOT DO, stated so nobody reads it as more than it is. It
    proves the file is the KIND of thing that was asked for. It does not prove
    the pixels came from the customer's scene -- a provider can render a
    different file, or send a valid PNG of anything at all, and this will pass
    it. Binding output to input needs attested execution inside a sandbox, and
    that is hand-built under ADR 0002. What is closed here is the cheapest
    version of the attack, where a provider uploads garbage and collects the
    frame, and it is closed completely.
    """
    if stored is None:
        return "output_missing"
    if stored < MIN_OUTPUT_BYTES:
        return "output_empty"
    if stored > MAX_OUTPUT_BYTES:
        return "output_too_large"

    expected = OUTPUT_MAGIC.get(output_format)
    if not expected:
        # A format with no signature recorded. Accepted rather than refused: the
        # job could only have been created with a format models.py allows, so
        # this means the table above is behind the enum, and failing every frame
        # of a legitimate job over our own omission is the worse error.
        return None

    try:
        prefix = bucket.head_prefix(output_key, OUTPUT_MAGIC_BYTES)
    except storage.StorageError:
        # The bucket answered the HEAD a moment ago and will not answer this.
        # Not the provider's fault and not evidence about the file, so the frame
        # is left to its lease rather than recorded as a bad render.
        raise

    if not any(prefix.startswith(magic) for magic in expected):
        return "output_not_" + output_format
    return None


@app.post(
    "/providers/render/frames/{frame_id}/result",
    response_model=RenderResultAccepted,
)
def submit_render_result(
    frame_id: str,
    req: RenderResultRequest,
    node_id: str,
    authorization: str | None = Header(default=None),
):
    """Record what the provider produced for one frame. Terminal, accepted once.

    The WHERE clause pins the node and the current status, exactly as
    submit_work_result() does: a result from a node that does not hold this
    frame is rejected, and a result for a frame already finished is rejected.

    THE UPLOAD IS VERIFIED, NOT TRUSTED. An agent reporting `completed` has not
    proved anything -- a crash between rendering and uploading produces exactly
    that report with nothing in the bucket. So a success claim is checked
    against the object itself: it must exist, be non-empty, be within a sane
    size, and begin with the magic number of the format the job asked for. A
    frame that fails any of those is recorded as failed with a code naming
    which. This is the difference between a job that finishes with a missing or
    unopenable image and a job that tells you which frame to re-run.

    Zero bytes is the case worth naming, because it read as correct: an empty
    object satisfied "something is there" and was delivered to the customer as
    their render. See _reject_output().

    HAND-BUILT SEAM: render_seconds is stored as evidence of what the runtime
    reported. It is not a bill. Turning it into an amount owed is metering,
    hand-built under ADR 0002, and agent/core/meter.py still raises
    NotImplementedError.
    """
    digest = _bearer_digest(authorization)
    now = _now()
    terminal = "completed" if req.status == "completed" else "failed"
    output_key = None
    output_bytes = req.output_bytes
    error_code = req.error_code

    if terminal == "completed":
        try:
            with db.connect() as conn:
                with conn.cursor() as cur:
                    _authenticate_node(cur, node_id, digest)
                    cur.execute(
                        """
                        SELECT f.job_id, f.frame_number, j.output_format
                        FROM render_frames f
                        JOIN render_jobs j ON j.job_id = f.job_id
                        WHERE f.frame_id = %s
                        """,
                        (frame_id,),
                    )
                    located = cur.fetchone()
        except (db.NotConfigured, psycopg.Error, OSError) as exc:
            raise _unavailable(exc) from exc

        if not located:
            raise HTTPException(status_code=404, detail="no such frame")

        output_key = storage.frame_key(
            located["job_id"], located["frame_number"], located["output_format"]
        )
        bucket = _render_storage()
        try:
            stored = bucket.head(output_key)
            rejection = _reject_output(
                bucket, output_key, stored, located["output_format"]
            )
        except storage.StorageError as exc:
            # A bucket that will not answer is our outage, not this provider's
            # bad render. 503 leaves the frame claimed so its lease decides what
            # happens next; recording a failure here would blame a machine that
            # may well have done the work correctly.
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        if rejection is not None:
            # Reported success, produced nothing usable. Recorded as a failure
            # with a distinct code so each cause is separable in the data --
            # they have different causes and different fixes, and a frame that
            # failed because the provider uploaded a text file is a different
            # conversation from one that ran out of VRAM.
            terminal = "failed"
            output_key = None
            output_bytes = None
            error_code = rejection
        else:
            output_bytes = stored

    try:
        with db.connect() as conn:
            with conn.cursor() as cur:
                node = _authenticate_node(cur, node_id, digest)
                cur.execute(
                    """
                    UPDATE render_frames SET
                        status = %s,
                        output_object_key = %s,
                        output_bytes = %s,
                        render_seconds = %s,
                        error_code = %s,
                        completed_at = %s
                    WHERE frame_id = %s
                      AND node_id = %s
                      AND status = 'claimed' AND claimed_at >= %s
                    RETURNING frame_id
                    """,
                    (
                        terminal,
                        output_key,
                        output_bytes,
                        req.render_seconds,
                        error_code,
                        now,
                        frame_id,
                        node_id,
                        node["issued_at"],
                    ),
                )
                row = cur.fetchone()
            conn.commit()
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        raise _unavailable(exc) from exc

    if not row:
        # Most often a lease that lapsed while the agent was still rendering,
        # after which the frame was handed to somebody else. 409 rather than
        # 404 because the frame exists -- this agent simply no longer holds it,
        # and it should drop the result rather than retry.
        raise HTTPException(
            status_code=409,
            detail="frame is not claimed by this node, or is already finished",
        )

    return RenderResultAccepted(frame_id=frame_id, status=terminal)
