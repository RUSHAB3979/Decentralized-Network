"""Orchestrator HTTP surface.

M1 scope: provider nodes can enrol, report in, and be listed. There is no
scheduling, no lease, no metering and no money here yet -- those are later
milestones, and several of them are hand-built per ADR 0002.

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
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from orchestrator import db
from orchestrator.liveness import liveness
from orchestrator.models import (
    HeartbeatRequest,
    HeartbeatResponse,
    NodeList,
    NodeView,
    RegisterRequest,
    RegisterResponse,
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

# The web client is served by Vite on another origin in development, and the
# desktop build runs from file:// (origin "null"). Both need to read the node
# list. This is permissive because M1 exposes only non-sensitive provider
# telemetry; it must be narrowed to an allowlist before any endpoint returns
# customer data or accepts an authenticated write.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
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
        detail=f"provider registry unavailable: {exc.__class__.__name__}: {exc}",
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
