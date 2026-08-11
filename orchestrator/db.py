"""Database access for the orchestrator.

Deliberately small. There is no ORM and no connection pool yet, because M1 has
one table and two writes, and every abstraction added here has to be understood
by whoever debugs the first production incident.

Two things it does insist on.

Every connection carries an explicit `connect_timeout`. Without one, psycopg
inherits the operating system's TCP timeout, which on Windows can hang a
request for over a minute against an unreachable host. A heartbeat that hangs
is worse than a heartbeat that fails: the agent's request is still open, the
worker thread is blocked, and the node stops reporting without ever reporting
an error.

Schema application is idempotent and happens at startup. `schema.sql` is
written entirely with IF NOT EXISTS, so running it against an existing database
is a no-op. This is a migration story that works for exactly one table; the
moment a column needs to change type or be backfilled, it stops being enough
and a real migration tool has to replace it. That threshold is worth naming now
so nobody discovers it during a deploy.
"""

from __future__ import annotations

import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

CONNECT_TIMEOUT_S = 5

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


class NotConfigured(RuntimeError):
    """DATABASE_URL is missing.

    Distinct from a connection failure. 'You forgot to set an environment
    variable' and 'Postgres is down' need different responses from whoever is
    on the other end, and an unset variable that surfaces as a generic
    connection error sends people to look at the wrong system.
    """


def database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise NotConfigured(
            "DATABASE_URL is not set. Copy .env.example to .env, then run "
            "`docker compose up -d db`."
        )
    return url


def connect() -> psycopg.Connection:
    """Open a connection with dict rows and a bounded connect timeout."""
    return psycopg.connect(
        database_url(), connect_timeout=CONNECT_TIMEOUT_S, row_factory=dict_row
    )


def apply_schema() -> None:
    """Create the M1 tables if they are absent. Safe to run on every boot."""
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
