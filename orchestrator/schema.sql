-- M1 schema: the provider node registry.
--
-- One row per enrolled machine. This is the first table in the system, so two
-- decisions in it set precedent for everything after.
--
-- 1. There is no credential column, and that is deliberate. `node_id` is a
--    public identifier, like a username. The provider's secret belongs in
--    agent/core/creds.py, which is hand-built and not written yet, so M1
--    identifies nodes without authenticating them. See docs/adr/0004.
--
-- 2. Liveness is NOT stored. There is no `is_online` column and no background
--    sweeper that flips one. Online-ness is derived from `last_heartbeat_at`
--    at read time, by orchestrator/liveness.py. A stored flag needs something
--    to keep it true, and when that something dies the flag stays where it was
--    -- every node reads "online" forever and nothing raises. A derived value
--    cannot lie about a heartbeat it never received.

CREATE TABLE IF NOT EXISTS provider_nodes (
    -- Chosen by the agent from stable machine facts, so a reinstall re-registers
    -- as the same node rather than orphaning the old row. See agent/identity.py.
    node_id             TEXT PRIMARY KEY,

    -- Capability: hardware facts, refreshed on register. These change rarely
    -- (a driver update, a new GPU) but are not immutable, so register is an
    -- upsert rather than an insert.
    hostname            TEXT        NOT NULL,
    os_version          TEXT,
    cpu                 TEXT,
    logical_cores       INTEGER,
    ram_total_mb        INTEGER,
    gpu_name            TEXT,
    vram_total_mb       INTEGER,
    gpu_driver          TEXT,
    agent_version       TEXT,

    -- Metrics: the live half, overwritten by every heartbeat.
    last_status         TEXT,
    last_detail         TEXT,
    accepts_work        BOOLEAN     NOT NULL DEFAULT FALSE,
    gpu_utilisation_pct INTEGER,
    vram_used_mb        INTEGER,
    temperature_c       INTEGER,
    ollama_reachable    BOOLEAN     NOT NULL DEFAULT FALSE,
    ollama_version      TEXT,

    -- Models that are actually resident on this machine's disk. Ollama Cloud
    -- entries are excluded by the agent before they are sent -- they are
    -- ~400-byte pointers to ollama.com, and counting them here would let a node
    -- advertise a 671B model it cannot serve. See agent/runtime/ollama.py.
    local_models        TEXT[]      NOT NULL DEFAULT '{}',

    registered_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_heartbeat_at   TIMESTAMPTZ
);

-- The provider list is read far more often than it is written, and always
-- ordered by recency of contact.
CREATE INDEX IF NOT EXISTS provider_nodes_heartbeat_idx
    ON provider_nodes (last_heartbeat_at DESC NULLS LAST);

-- Customer credentials for the local managed-inference vertical slice. The
-- plaintext key is returned once by POST /v1/api-keys and is never stored.
CREATE TABLE IF NOT EXISTS marketplace_api_keys (
    key_id          TEXT PRIMARY KEY,
    name            TEXT        NOT NULL,
    key_prefix      TEXT        NOT NULL UNIQUE,
    key_hash        TEXT        NOT NULL UNIQUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at    TIMESTAMPTZ,
    revoked_at      TIMESTAMPTZ
);

-- An audit and usage record, deliberately without prompt or response content.
-- The local demo has no billing, but it still records enough evidence to show
-- which key and provider handled a request and what Ollama counted.
CREATE TABLE IF NOT EXISTS inference_requests (
    request_id         TEXT PRIMARY KEY,
    api_key_id         TEXT        NOT NULL REFERENCES marketplace_api_keys(key_id),
    node_id            TEXT        NOT NULL REFERENCES provider_nodes(node_id),
    model              TEXT        NOT NULL,
    status             TEXT        NOT NULL,
    prompt_tokens      INTEGER     NOT NULL DEFAULT 0,
    completion_tokens  INTEGER     NOT NULL DEFAULT 0,
    total_duration_ms  INTEGER,
    error_code         TEXT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at       TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS inference_requests_key_created_idx
    ON inference_requests (api_key_id, created_at DESC);

-- ---------------------------------------------------------------------------
-- Accounts.
--
-- A customer owns API keys; an API key owns inference requests. Before this
-- table existed, `marketplace_api_keys` had no owner and key administration was
-- gated on the caller being loopback (`LOCAL_DEMO_MODE`), which is a deployment
-- posture rather than an identity. Anyone reaching the orchestrator from the
-- right address was every customer at once.
--
-- Passwords are stored as scrypt digests, never plaintext and never a bare
-- hash. See orchestrator/auth.py for the parameters and why a plain SHA-256
-- would be wrong here.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    user_id         TEXT PRIMARY KEY,

    -- Stored lowercased and trimmed by the application so that
    -- `Rushab@x.com` and `rushab@x.com` cannot become two accounts. The UNIQUE
    -- constraint is what actually enforces it under a race; the normalisation
    -- is what makes the constraint mean what we think it means.
    email           TEXT        NOT NULL UNIQUE,

    -- Opaque `scrypt$n$r$p$salt$digest`. Self-describing so the cost
    -- parameters can be raised later without invalidating existing rows.
    password_hash   TEXT        NOT NULL,

    display_name    TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login_at   TIMESTAMPTZ
);

-- ---------------------------------------------------------------------------
-- Login sessions.
--
-- Opaque random tokens, stored hashed, rather than JWTs. A JWT cannot be
-- revoked before it expires without keeping a deny-list, which is a database
-- lookup -- the same lookup this table already is, minus the cryptography.
--
-- Expiry is DERIVED at read time from `expires_at`, never swept by a
-- background job. Same reasoning as provider liveness: a sweeper that dies
-- leaves every expired session valid forever, and nothing raises.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_sessions (
    session_id      TEXT PRIMARY KEY,
    user_id         TEXT        NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,

    -- Only the digest is stored. A leaked database backup must not be a set of
    -- working login tokens.
    token_hash      TEXT        NOT NULL UNIQUE,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at      TIMESTAMPTZ NOT NULL,
    revoked_at      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS user_sessions_user_idx
    ON user_sessions (user_id, created_at DESC);

-- ---------------------------------------------------------------------------
-- Columns added to tables that already existed.
--
-- `CREATE TABLE IF NOT EXISTS` cannot alter a table that is already there, so
-- new columns need their own idempotent statements. This is the migration
-- ceiling orchestrator/db.py names in its docstring: it is still reachable
-- with ADD COLUMN IF NOT EXISTS, and it stops being reachable the first time a
-- column needs a type change or a backfill. That is the point to adopt Alembic.
-- ---------------------------------------------------------------------------

-- Which customer owns this key. Nullable because keys issued by the old
-- loopback-only demo flow have no owner and must keep working until they are
-- revoked; every key minted from now on has one.
ALTER TABLE marketplace_api_keys
    ADD COLUMN IF NOT EXISTS user_id TEXT REFERENCES users(user_id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS marketplace_api_keys_user_idx
    ON marketplace_api_keys (user_id, created_at DESC);

-- Proof that a machine claiming to be this node actually is. `node_id` is a
-- public identifier (agent/identity.py); this is the secret half, issued once
-- at registration and stored only as a digest.
--
-- SCOPE, STATED PLAINLY: this authenticates the transport, nothing more. It is
-- not agent/core/creds.py, which is hand-built under ADR 0002 and still
-- unwritten. In particular the agent currently keeps this token in a plaintext
-- file under %LOCALAPPDATA%; DPAPI storage, rotation and per-machine binding
-- are exactly what creds.py owes. Do not read this column as that work being
-- done.
ALTER TABLE provider_nodes
    ADD COLUMN IF NOT EXISTS node_token_hash TEXT;

-- ---------------------------------------------------------------------------
-- The work queue.
--
-- Why a queue at all: a provider's agent runs on a home PC behind NAT. The
-- orchestrator cannot open a connection to it, so work cannot be pushed. The
-- agent asks for work over a connection it opened itself, which is the only
-- direction that survives a consumer router.
--
-- Claim expiry is DERIVED, never swept. A job is claimable when it is queued,
-- or when it was claimed and its lease has passed. There is no background task
-- marking jobs abandoned -- if there were, its death would strand every job in
-- `claimed` forever with nothing raising, which is the exact failure this
-- repository keeps designing around.
--
-- HAND-BUILT SEAM: the lease semantics here are the minimum needed to move a
-- request to a machine and back. Renewal, drain, partial results and crash
-- reconciliation belong to agent/core/lease.py, which is hand-built under
-- ADR 0002 and still raises NotImplementedError.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS inference_jobs (
    job_id            TEXT PRIMARY KEY,

    -- One job per request today. Kept as separate identifiers because a
    -- retried or re-dispatched request must be able to produce a second job
    -- without losing the first one's evidence.
    request_id        TEXT        NOT NULL REFERENCES inference_requests(request_id),

    -- Chosen at enqueue time. Not a foreign key to provider_nodes on purpose:
    -- a node that deregisters mid-flight must not delete the record of work it
    -- was given.
    node_id           TEXT        NOT NULL,

    model             TEXT        NOT NULL,

    -- The chat payload exactly as it will be handed to the runtime. JSONB so
    -- it can be inspected during an incident without a second table.
    payload           JSONB       NOT NULL,

    -- queued | claimed | completed | failed
    status            TEXT        NOT NULL DEFAULT 'queued',

    claimed_at        TIMESTAMPTZ,
    lease_expires_at  TIMESTAMPTZ,

    -- Result, written once by the agent that holds the lease.
    result_content    TEXT,
    finish_reason     TEXT,
    prompt_tokens     INTEGER,
    completion_tokens INTEGER,
    total_duration_ms INTEGER,
    error_code        TEXT,

    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at      TIMESTAMPTZ
);

-- The claim query filters on node and status and orders by age. This index
-- matches that access pattern; without it every claim scans the table, which
-- is fine at ten jobs and not at ten thousand.
CREATE INDEX IF NOT EXISTS inference_jobs_claimable_idx
    ON inference_jobs (node_id, status, created_at);

-- The waiting request polls its own job by id; that is served by the primary
-- key. This one serves "what happened to request X" during debugging.
CREATE INDEX IF NOT EXISTS inference_jobs_request_idx
    ON inference_jobs (request_id);
