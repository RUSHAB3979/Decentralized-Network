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

import httpx
import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
    ModelList,
    ModelView,
    NodeList,
    NodeView,
    RegisterRequest,
    RegisterResponse,
    UsageSummary,
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
    """
    cap = req.capability
    try:
        with db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO provider_nodes (
                        node_id, hostname, os_version, cpu, logical_cores,
                        ram_total_mb, gpu_name, vram_total_mb, gpu_driver,
                        agent_version
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (node_id) DO UPDATE SET
                        hostname      = EXCLUDED.hostname,
                        os_version    = EXCLUDED.os_version,
                        cpu           = EXCLUDED.cpu,
                        logical_cores = EXCLUDED.logical_cores,
                        ram_total_mb  = EXCLUDED.ram_total_mb,
                        gpu_name      = EXCLUDED.gpu_name,
                        vram_total_mb = EXCLUDED.vram_total_mb,
                        gpu_driver    = EXCLUDED.gpu_driver,
                        agent_version = EXCLUDED.agent_version
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


def _local_demo_enabled() -> bool:
    return os.getenv("LOCAL_DEMO_MODE", "false").lower() in {"1", "true", "yes"}


def _require_local_demo(request: Request) -> None:
    """Keep unauthenticated key administration on this development machine."""
    host = request.client.host if request.client else ""
    if not _local_demo_enabled() or host not in {"127.0.0.1", "::1", "testclient"}:
        raise HTTPException(
            status_code=403,
            detail="API-key administration is available only in local demo mode",
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


def _select_demo_provider(model: str | None = None) -> dict:
    """Select the one provider allowed by the local single-node demo."""
    node_id = (os.getenv("DEMO_PROVIDER_NODE_ID") or "").strip()
    if not node_id:
        raise HTTPException(
            status_code=503,
            detail="DEMO_PROVIDER_NODE_ID is not configured",
        )
    try:
        with db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT node_id, hostname, accepts_work, ollama_reachable,
                           local_models, registered_at, last_heartbeat_at
                    FROM provider_nodes
                    WHERE node_id = %s
                    """,
                    (node_id,),
                )
                row = cur.fetchone()
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        raise _unavailable(exc) from exc

    if not row:
        raise HTTPException(status_code=503, detail="demo provider is not enrolled")
    if liveness(row["last_heartbeat_at"], _now(), ttl()) != "online":
        raise HTTPException(status_code=503, detail="demo provider heartbeat is stale")
    if not row["accepts_work"]:
        raise HTTPException(status_code=503, detail="demo provider is not accepting work")
    if not row["ollama_reachable"]:
        raise HTTPException(status_code=503, detail="demo provider runtime is unavailable")
    if model and model not in (row["local_models"] or []):
        raise HTTPException(
            status_code=404,
            detail=f"model {model!r} is not installed on the demo provider",
        )
    return row


@app.post("/v1/api-keys", response_model=ApiKeyCreated, status_code=201)
def create_api_key(req: ApiKeyCreateRequest, request: Request):
    _require_local_demo(request)
    issued = inference.issue_api_key()
    key_id = f"key_{uuid4().hex}"
    try:
        with db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO marketplace_api_keys (
                        key_id, name, key_prefix, key_hash
                    ) VALUES (%s, %s, %s, %s)
                    RETURNING created_at
                    """,
                    (key_id, req.name, issued.prefix, issued.digest),
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
def list_api_keys(request: Request):
    _require_local_demo(request)
    try:
        with db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT key_id, name, key_prefix, created_at, last_used_at
                    FROM marketplace_api_keys
                    WHERE revoked_at IS NULL
                    ORDER BY created_at DESC
                    """
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
def revoke_api_key(key_id: str, request: Request):
    _require_local_demo(request)
    try:
        with db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE marketplace_api_keys
                    SET revoked_at = %s
                    WHERE key_id = %s AND revoked_at IS NULL
                    """,
                    (_now(), key_id),
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
    provider = _select_demo_provider()
    created = int(provider["registered_at"].timestamp())
    return ModelList(
        data=[ModelView(id=model, created=created) for model in provider["local_models"]]
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
    if req.stream:
        raise HTTPException(status_code=400, detail="streaming is not supported yet")
    api_key = _authenticate_api_key(authorization)
    provider = _select_demo_provider(req.model)
    request_id = f"chatcmpl-{uuid4().hex}"
    created = int(time.time())

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
            conn.commit()
    except (db.NotConfigured, psycopg.Error, OSError) as exc:
        raise _unavailable(exc) from exc

    try:
        result = inference.run_chat(
            model=req.model,
            messages=[message.model_dump() for message in req.messages],
            temperature=req.temperature,
            max_tokens=req.max_tokens,
        )
    except (httpx.HTTPError, ValueError, OSError) as exc:
        _finish_inference_request(
            request_id,
            status_value="failed",
            error_code=exc.__class__.__name__,
        )
        raise HTTPException(
            status_code=502,
            detail=f"provider runtime failed: {exc.__class__.__name__}",
        ) from exc

    _finish_inference_request(
        request_id,
        status_value="completed",
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        total_duration_ms=result.total_duration_ms,
    )
    return ChatCompletionResponse(
        id=request_id,
        created=created,
        model=req.model,
        choices=[
            ChatCompletionChoice(
                message=ChatCompletionMessage(content=result.content),
                finish_reason=result.finish_reason,
            )
        ],
        usage=ChatUsage(
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            total_tokens=result.prompt_tokens + result.completion_tokens,
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
