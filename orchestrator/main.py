"""Orchestrator HTTP surface.

Provider nodes can enrol, report in, and be listed. The local demo also exposes
an API-key-protected inference gateway that selects one configured provider,
forwards a chat request to its local Ollama runtime, and records usage totals.
It is a single-machine learning milestone, not a production marketplace.

On authentication, or its absence: `POST /providers/heartbeat` is
unauthenticated in M1. tasks.md item 7 asks for that decision to be written
down rather than left implicit, and it is, in docs/adr/0004-m1-unauthenticated-
heartbeat.md. The short version is that a node identity carries nothing of
value until a lease or a payout is attached to it, and the credential that
would secure it belongs in agent/core/creds.py, which is hand-built and
unwritten. Shipping a guessed-at authentication scheme now would be worse than
shipping none: it would look like security in code review while protecting an
asset that does not exist yet.
"""

from __future__ import annotations

import os
import secrets
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Json
from fastapi import FastAPI, Header, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from orchestrator import auth
from orchestrator import db
from orchestrator import inference
from orchestrator.liveness import liveness
from orchestrator.models import (
    ApiKeyCreated,
    ApiKeyCreateRequest,
    ApiKeyList,
    ApiKeyView,
    ChatCompletionChoice,
    ChatCompletionMessage,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatUsage,
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
    RegisterRequest,
    RegisterResponse,
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


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Create the M1 tables on boot, but never refuse to boot over it.

    A database that is down at startup is a normal condition in development --
    `uvicorn` gets started before `docker compose up -d db` more often than
    not. Crashing here would make that a confusing failure. Instead the app
    starts, /health reports degraded, and the provider endpoints return 503
    with the actual reason.
    """
    try:
        db.apply_schema()
        print("[orchestrator] schema applied")
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        print(f"[orchestrator] schema not applied: {exc.__class__.__name__}: {exc}")
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
    return {"status": "ok", "db": "ok", "version": VERSION}


@app.post("/providers/register", response_model=RegisterResponse)
def register(req: RegisterRequest):
    """Enrol a node, or refresh the hardware facts of one already enrolled.

    An upsert rather than an insert, because the agent calls this on every
    start. Registration therefore has to be idempotent: restarting the app
    twenty times must leave one row, not twenty, and must not reset
    `registered_at` -- that column is how long this provider has been with us,
    and overwriting it on every launch would quietly destroy the only tenure
    signal we have.

    Registration now also mints the node's transport credential and returns it
    exactly once. Re-registering rotates it, which is deliberate: the agent
    registers on every start, so a machine that restarts gets a fresh secret and
    an attacker holding an old one loses it. The cost is that two agents cannot
    run as the same node -- the second registration silently invalidates the
    first one's token, and the first agent will start failing to claim work with
    a 401. That is the correct outcome for a duplicated install, and it is
    visible rather than silent because the agent logs the 401 and re-registers.
    """
    cap = req.capability
    node_token, token_hash = auth.issue_node_token()
    try:
        with db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO provider_nodes (
                        node_id, hostname, os_version, cpu, logical_cores,
                        ram_total_mb, gpu_name, vram_total_mb, gpu_driver,
                        agent_version, node_token_hash
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (node_id) DO UPDATE SET
                        hostname      = EXCLUDED.hostname,
                        os_version    = EXCLUDED.os_version,
                        cpu           = EXCLUDED.cpu,
                        logical_cores = EXCLUDED.logical_cores,
                        ram_total_mb  = EXCLUDED.ram_total_mb,
                        gpu_name      = EXCLUDED.gpu_name,
                        vram_total_mb = EXCLUDED.vram_total_mb,
                        gpu_driver    = EXCLUDED.gpu_driver,
                        agent_version = EXCLUDED.agent_version,
                        node_token_hash = EXCLUDED.node_token_hash
                    RETURNING registered_at
                    """,
                    (
                        req.node_id,
                        cap.hostname,
                        cap.os_version,
                        cap.cpu,
                        cap.logical_cores,
                        cap.ram_total_mb,
                        cap.gpu_name,
                        cap.vram_total_mb,
                        cap.gpu_driver,
                        cap.agent_version,
                        token_hash,
                    ),
                )
                row = cur.fetchone()
            conn.commit()
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        raise _unavailable(exc) from exc

    return RegisterResponse(
        node_id=req.node_id,
        registered_at=row["registered_at"],
        heartbeat_interval_s=heartbeat_interval_s(),
        node_token=node_token,
    )


@app.post("/providers/heartbeat", response_model=HeartbeatResponse)
def heartbeat(req: HeartbeatRequest):
    """Record that a node is alive and what it is currently doing.

    An UPDATE, not an upsert. A heartbeat for an unknown node returns 404, and
    the agent responds by registering again. That matters because it is the
    recovery path for a wiped or restored database: without it, agents would
    keep heartbeating into a registry that has no row for them, every request
    would succeed, and the fleet would appear to have vanished.

    Idempotent by construction -- every column is overwritten with the values
    in this request -- so the agent can safely retry a heartbeat whose response
    it never saw.
    """
    m = req.metrics
    received = _now()
    try:
        with db.connect() as conn:
            with conn.cursor() as cur:
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
                        last_heartbeat_at   = %s
                    WHERE node_id = %s
                    """,
                    (
                        req.status,
                        req.detail,
                        req.accepts_work,
                        m.gpu_utilisation_pct,
                        m.vram_used_mb,
                        m.temperature_c,
                        m.ollama_reachable,
                        m.ollama_version,
                        m.local_models,
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
def list_nodes():
    """Every enrolled node, most recently seen first.

    Liveness is computed here from `last_heartbeat_at` rather than read from a
    column, for the reason set out in liveness.py: a derived value cannot claim
    a heartbeat that never arrived.
    """
    try:
        with db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT node_id, hostname, os_version, cpu, logical_cores,
                           ram_total_mb, gpu_name, vram_total_mb, gpu_driver,
                           agent_version, last_status, last_detail, accepts_work,
                           gpu_utilisation_pct, vram_used_mb, temperature_c,
                           ollama_reachable, ollama_version, local_models,
                           registered_at, last_heartbeat_at
                    FROM provider_nodes
                    ORDER BY last_heartbeat_at DESC NULLS LAST, registered_at DESC
                    """
                )
                rows = cur.fetchall()
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        raise _unavailable(exc) from exc

    now = _now()
    window = ttl()
    return NodeList(
        nodes=[
            NodeView(
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
            for r in rows
        ],
        ttl_seconds=int(window.total_seconds()),
        server_time=now,
    )


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=401,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


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
                    SELECT key_id, name, key_hash
                    FROM marketplace_api_keys
                    WHERE key_prefix = %s AND revoked_at IS NULL
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
    try:
        with db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE inference_requests SET
                        status = %s,
                        prompt_tokens = %s,
                        completion_tokens = %s,
                        total_duration_ms = %s,
                        error_code = %s,
                        completed_at = %s
                    WHERE request_id = %s
                    """,
                    (
                        status_value,
                        prompt_tokens,
                        completion_tokens,
                        total_duration_ms,
                        error_code,
                        _now(),
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
    """
    if req.stream:
        raise HTTPException(status_code=400, detail="streaming is not supported yet")

    api_key = _authenticate_api_key(authorization)
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
                           u.user_id, u.email, u.display_name, u.created_at
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


@app.post("/v1/auth/signup", response_model=SessionCreated, status_code=201)
def signup(req: SignupRequest):
    """Create an account and log it straight in.

    Returning a session here rather than making the caller log in separately is
    not just convenience: it means the password is sent once instead of twice
    for the same outcome.
    """
    email = auth.normalise_email(req.email)
    user_id = f"usr_{uuid4().hex}"
    password_hash = auth.hash_password(req.password)

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
def login(req: LoginRequest):
    """Exchange an email and password for a session token."""
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

    if row is None:
        # Hash a throwaway password anyway, so a request for an address with no
        # account costs the same time as one with an account. Returning early
        # here would make the response time an oracle for which emails are
        # registered -- a timing side channel that needs no special tooling to
        # exploit, only a stopwatch.
        auth.hash_password(req.password)
        raise _unauthorized("invalid email or password")

    try:
        ok = auth.verify_password(req.password, row["password_hash"])
    except auth.PasswordFormatError as exc:
        # Corrupt or unreadable stored hash. This is our problem, not the
        # caller's, and reporting it as a failed login would send someone to
        # reset a password that is in fact correct.
        raise HTTPException(
            status_code=500, detail=f"stored credential is unreadable: {exc}"
        ) from exc

    if not ok:
        raise _unauthorized("invalid email or password")
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


def _authenticate_node(node_id: str, authorization: str | None) -> dict:
    """Prove that this caller is the machine that registered as `node_id`.

    HAND-BUILT SEAM. This is transport authentication and nothing more: it stops
    an arbitrary internet host from claiming another provider's work or posting
    fabricated results. It is not agent/core/creds.py, which is hand-built under
    ADR 0002 and owes DPAPI-backed storage, rotation, and binding the credential
    to the machine. The agent currently keeps this token in a plaintext file, so
    anyone with local access to a provider's PC still has their identity.
    """
    try:
        token = inference.bearer_token(authorization)
    except ValueError as exc:
        raise _unauthorized(str(exc)) from exc

    try:
        with db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT node_id, node_token_hash, accepts_work, ollama_reachable,
                           local_models, last_heartbeat_at
                    FROM provider_nodes WHERE node_id = %s
                    """,
                    (node_id,),
                )
                row = cur.fetchone()
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        raise _unavailable(exc) from exc

    if not row or not row["node_token_hash"]:
        # A node registered before this column existed has no token and cannot
        # claim work. Re-registering mints one, which the agent does on its next
        # start, so this heals itself rather than needing an operator.
        raise _unauthorized("unknown node, or node has no credential; register again")
    if not secrets.compare_digest(row["node_token_hash"], auth.hash_token(token)):
        raise _unauthorized("invalid node credential")
    return row


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
    node = _authenticate_node(node_id, authorization)
    now = _now()

    # A node that is draining should not be given new work. It may still be
    # finishing something it already holds, which is why this refuses new claims
    # rather than cancelling the lease.
    if not node["accepts_work"]:
        return JobClaimResponse(job=None, poll_interval_s=claim_poll_interval_s())

    lease_until = now + timedelta(seconds=job_lease_s())
    try:
        with db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE inference_jobs SET
                        status = 'claimed',
                        claimed_at = %s,
                        lease_expires_at = %s
                    WHERE job_id IN (
                        SELECT job_id FROM inference_jobs
                        WHERE node_id = %s
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
                    (now, lease_until, node_id, now),
                )
                row = cur.fetchone()
            conn.commit()
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        raise _unavailable(exc) from exc

    if not row:
        return JobClaimResponse(job=None, poll_interval_s=claim_poll_interval_s())

    return JobClaimResponse(
        job=JobOffer(
            job_id=row["job_id"],
            model=row["model"],
            payload=JobPayload(**row["payload"]),
            lease_expires_at=row["lease_expires_at"],
        ),
        poll_interval_s=claim_poll_interval_s(),
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
    _authenticate_node(node_id, authorization)
    now = _now()
    terminal = "completed" if req.status == "completed" else "failed"

    try:
        with db.connect() as conn:
            with conn.cursor() as cur:
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
                      AND status = 'claimed'
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
                    SELECT node_id, hostname, accepts_work, ollama_reachable,
                           local_models, registered_at, last_heartbeat_at
                    FROM provider_nodes
                    WHERE accepts_work = TRUE
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
