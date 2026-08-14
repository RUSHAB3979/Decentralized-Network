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
