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

-- Provider login is a separate account realm (ADR 0005).
CREATE TABLE IF NOT EXISTS provider_accounts (
    provider_account_id TEXT PRIMARY KEY,
    email               TEXT        NOT NULL UNIQUE,
    password_hash       TEXT        NOT NULL,
    display_name        TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login_at       TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS provider_sessions (
    session_id          TEXT PRIMARY KEY,
    provider_account_id TEXT        NOT NULL REFERENCES provider_accounts(provider_account_id)
                                         ON DELETE CASCADE,
    token_hash          TEXT        NOT NULL UNIQUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at          TIMESTAMPTZ NOT NULL,
    revoked_at          TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS provider_sessions_account_idx
    ON provider_sessions (provider_account_id, created_at DESC);

CREATE TABLE IF NOT EXISTS provider_enrolment_keys (
    enrolment_key_id    TEXT PRIMARY KEY,
    provider_account_id TEXT        NOT NULL REFERENCES provider_accounts(provider_account_id)
                                         ON DELETE CASCADE,
    key_prefix          TEXT        NOT NULL,
    key_hash            TEXT        NOT NULL UNIQUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at          TIMESTAMPTZ NOT NULL,
    redeemed_at         TIMESTAMPTZ,
    revoked_at          TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS provider_enrolment_keys_account_idx
    ON provider_enrolment_keys (provider_account_id, created_at DESC);

-- Keep ownership and credentials outside the telemetry registry so a node can
-- rebuild a missing telemetry row using its existing credential.
CREATE TABLE IF NOT EXISTS provider_node_credentials (
    node_id             TEXT PRIMARY KEY,
    provider_account_id TEXT        NOT NULL REFERENCES provider_accounts(provider_account_id),
    token_hash          TEXT        NOT NULL UNIQUE,
    issued_at           TIMESTAMPTZ NOT NULL,
    revoked_at          TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS provider_node_credentials_account_idx
    ON provider_node_credentials (provider_account_id);

ALTER TABLE provider_nodes
    ADD COLUMN IF NOT EXISTS inference_eligible BOOLEAN NOT NULL DEFAULT FALSE;

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

-- Whether this account may see the fleet in full detail.
--
-- FAIL-CLOSED, the same shape as render_eligible and accepts_work: default
-- FALSE, and only an operator running an UPDATE changes it. Every row in
-- provider_nodes is a hardware fingerprint of somebody's actual home computer
-- -- hostname, OS build, CPU model, driver version -- and until this column
-- existed, any signed-up customer could read all of it for every provider on
-- the marketplace. NodeView's own docstring already called itself "the model
-- that will eventually be filtered for what a customer is allowed to see";
-- this is the column that filter reads.
--
-- What a non-operator still sees is the capacity the marketplace is actually
-- selling: GPU model, VRAM, liveness, utilisation. What they no longer see is
-- everything that identifies the machine or the person who owns it.
--
-- This is a stand-in for provider accounts (ADR 0005), not a replacement. The
-- eventual answer is "the account that owns the node", and there is still no
-- owner column to filter on.
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS is_operator BOOLEAN NOT NULL DEFAULT FALSE;

-- Wall-clock the ORCHESTRATOR measured for an inference request, as distinct
-- from total_duration_ms, which is whatever the provider said.
--
-- The provider is untrusted and picks its own numbers. Before this column
-- those numbers were copied into the request row and summed by /v1/usage, so a
-- hostile provider could inflate every figure a customer sees about their own
-- spending. This is the value nobody outside this process can influence:
-- created_at and completed_at are both written here.
--
-- NOT A BILL, and specifically not the fix for metering. Metering is hand-built
-- under ADR 0002 and agent/core/meter.py still raises NotImplementedError.
-- What this closes is narrower and worth naming exactly: the provider's report
-- is no longer the only record of how long the work took, and the reported
-- figure is clamped against this one before it is stored.
ALTER TABLE inference_requests
    ADD COLUMN IF NOT EXISTS orchestrator_duration_ms INTEGER;

-- Make the owner mandatory.
--
-- The column was added nullable so that keys minted by the old loopback-only
-- demo flow would keep working. That kindness had a cost nobody priced:
-- authentication matches on the key hash alone, while listing and revoking are
-- scoped to the session's user_id -- so an ownerless key authenticated forever
-- and was invisible to the only interface that could revoke it. There was no
-- supported way to turn one off.
--
-- Guarded rather than a bare SET NOT NULL. A deployment that still has legacy
-- rows must not fail to start on a schema statement; it gets the application-
-- level refusal in _authenticate_api_key() instead, which fails closed for
-- exactly those rows and leaves this constraint to be applied once they are
-- cleaned up. This is the first constraint in this file that cannot be
-- expressed as a plain idempotent ALTER, which is the Alembic threshold
-- db.py's docstring names -- noted, not crossed.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM marketplace_api_keys WHERE user_id IS NULL) THEN
        BEGIN
            ALTER TABLE marketplace_api_keys ALTER COLUMN user_id SET NOT NULL;
        EXCEPTION WHEN others THEN
            NULL;
        END;
    END IF;
END $$;

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

-- ---------------------------------------------------------------------------
-- RENDERING: the second workload class.
--
-- See docs/adr/0006-render-batch-jobs.md. Rendering gets its own tables rather
-- than a `workload_type` column on inference_jobs, because the two differ in
-- payload shape, lease window, retry unit and billing unit. One table would
-- mean every future change to either has to be reasoned about against the
-- other.
--
-- THE GATE, AND WHAT IT IS NOT. A .blend file can carry embedded Python, so
-- running one is executing a stranger's code on a provider's machine. The
-- sandbox that would make that safe does not exist; it is hand-built under
-- ADR 0002 and is docs/ryujitasks.md K7. Until it does, render work is
-- restricted to nodes whose owner has explicitly opted in, by an UPDATE, one
-- machine at a time.
--
-- This is a column, not a sandbox. It bounds the blast radius to hardware
-- somebody chose; it does not make the execution safe. Anyone who sets
-- render_eligible on a machine they do not own has accepted arbitrary code
-- execution on it, and nothing here will stop them or tell them.
-- ---------------------------------------------------------------------------

-- Fails closed, exactly as accepts_work has since the first table in this
-- schema. A provider who installs the app tomorrow cannot receive a render
-- job -- not because somebody remembered to exclude them, but because the
-- default excludes them.
ALTER TABLE provider_nodes
    ADD COLUMN IF NOT EXISTS render_eligible BOOLEAN NOT NULL DEFAULT FALSE;

-- Which Blender the node actually has, as reported by `blender --version`.
-- Version drift is a silent-failure class: the same .blend rendered on a
-- different build can produce different pixels and nothing raises. Selection
-- matches on this, so a mismatch becomes "no node available" -- visible -- and
-- not "wrong output" -- invisible.
ALTER TABLE provider_nodes
    ADD COLUMN IF NOT EXISTS blender_version TEXT;

-- The customer half of the gate. Both sides must be on for any byte to move.
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS render_enabled BOOLEAN NOT NULL DEFAULT FALSE;

-- ---------------------------------------------------------------------------
-- One row per submission.
--
-- ON STATUS, WHICH IS THE ONE SUBTLE THING HERE. This column holds only the
-- states that are facts about the job itself and are not visible in its
-- frames: awaiting_upload (no frames exist yet), queued (they do), and
-- cancelled (a human said stop). Everything else a customer sees -- running,
-- completed, failed, and the progress count -- is DERIVED from render_frames
-- at read time and is never written here.
--
-- The alternative, a status column maintained by a background task, is the
-- mistake this schema has now declined four times: liveness (line 11), session
-- expiry (line 131), inference job reclaim, and this. The reason is the same
-- every time. A sweeper that dies leaves every job reading "running" forever,
-- the customer waits for something that finished an hour ago, and nothing
-- raises.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS render_jobs (
    job_id             TEXT PRIMARY KEY,

    user_id            TEXT        NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,

    -- awaiting_upload | queued | cancelled. See the note above: this is not
    -- the status the customer is shown.
    status             TEXT        NOT NULL DEFAULT 'awaiting_upload',

    -- Recorded at submission and matched against provider_nodes.blender_version
    -- at claim time -- on the RELEASE SERIES, not the exact string. A customer
    -- picks "4.3" because that is how Blender compatibility is described and
    -- what a scene is authored against; a node reports "4.3.2" because that is
    -- what `blender --version` prints. Compared for equality those never match
    -- and every job would sit queued forever with nothing raising. Across
    -- series it stays strict: 4.2 renders a 4.3 file into a different image,
    -- exits zero, and reports success.
    blender_version    TEXT        NOT NULL,

    -- cycles | eevee
    engine             TEXT        NOT NULL,

    frame_start        INTEGER     NOT NULL,
    frame_end          INTEGER     NOT NULL,

    -- png | exr. Video muxing needs a step after every frame lands and is not
    -- built; the submission API rejects mp4 rather than accepting it and
    -- silently delivering stills.
    output_format      TEXT        NOT NULL,

    -- Where the .blend lives in the bucket. The orchestrator never holds the
    -- bytes -- it mints a presigned URL and the browser uploads directly.
    source_object_key  TEXT        NOT NULL,

    -- Confirmed by a HEAD against the bucket after upload, not trusted from
    -- the client. A client-reported size is a claim; this is a measurement.
    source_bytes       BIGINT,

    -- Recorded as the customer's stated ceiling. NOT enforced as money:
    -- metering is hand-built under ADR 0002 and agent/core/meter.py still
    -- raises NotImplementedError, so there is no amount to compare it to. It
    -- is stored now so that the number the customer chose is not lost by the
    -- time there is.
    spending_limit_usd NUMERIC(10, 2),

    error_code         TEXT,

    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    uploaded_at        TIMESTAMPTZ,
    cancelled_at       TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS render_jobs_user_idx
    ON render_jobs (user_id, created_at DESC);

-- What the customer said the .blend would weigh, kept separately from
-- source_bytes, which is what the object actually turned out to weigh.
--
-- Two different facts that were being stored in one column. The declared figure
-- is needed after submission because it is signed into the upload URL -- the
-- presigned PUT binds Content-Length, so the bucket itself refuses an upload of
-- any other size, and re-minting that URL later requires remembering the number
-- it was minted against. Overloading source_bytes would have made "declared"
-- and "measured" indistinguishable exactly when the difference matters, which
-- is while investigating an upload that was refused.
ALTER TABLE render_jobs
    ADD COLUMN IF NOT EXISTS declared_source_bytes BIGINT;

-- ---------------------------------------------------------------------------
-- One row per frame. THIS is the unit of claim, lease and retry.
--
-- The unified plan's Phase 3 exit gate requires that "failed frames retry
-- without restarting the full animation". A 120-frame animation that starts
-- over because frame 87 died is not a product, and per-frame rows are what
-- make the alternative possible.
--
-- Unlike inference_jobs, no node is chosen at enqueue time. Frames sit
-- unassigned and any eligible node claims the oldest one. Inference pre-selects
-- because the model has to already be resident on that machine; a frame has no
-- such affinity, so pre-assigning it would idle every other node whenever one
-- node's queue was long.
--
-- HAND-BUILT SEAM, unchanged from inference_jobs: the lease semantics here are
-- the minimum needed to move a frame to a machine and back. Renewal, drain and
-- crash reconciliation belong to agent/core/lease.py, which is hand-built under
-- ADR 0002 and still raises NotImplementedError. That absence costs more here
-- than it did for inference -- a lapsed lease on a chat request wastes seconds,
-- and on a frame twenty minutes into a render it wastes twenty minutes of a
-- provider's GPU and hands the same work to somebody else.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS render_frames (
    frame_id          TEXT PRIMARY KEY,

    job_id            TEXT        NOT NULL REFERENCES render_jobs(job_id) ON DELETE CASCADE,

    frame_number      INTEGER     NOT NULL,

    -- queued | claimed | completed | failed
    status            TEXT        NOT NULL DEFAULT 'queued',

    -- Which node holds it. Not a foreign key, for the same reason
    -- inference_jobs.node_id is not one: a node that deregisters mid-flight
    -- must not delete the record of work it was given.
    node_id           TEXT,

    claimed_at        TIMESTAMPTZ,
    lease_expires_at  TIMESTAMPTZ,

    -- Incremented on every claim, including reclaims after a lapsed lease.
    -- BOUNDED at claim time: without a ceiling, a frame that crashes the
    -- runtime is handed out forever, and a job containing one poisonous frame
    -- becomes an unbounded bill against every provider in the fleet in turn.
    attempts          INTEGER     NOT NULL DEFAULT 0,

    output_object_key TEXT,
    output_bytes      BIGINT,

    -- Wall-clock the runtime reported. Evidence, NOT a bill -- same wording and
    -- same reason as inference_jobs' token counts.
    render_seconds    NUMERIC(10, 3),

    error_code        TEXT,

    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at      TIMESTAMPTZ,

    -- A job must never contain the same frame twice. This is also what makes
    -- fan-out idempotent: a retried /uploaded call cannot double the queue.
    UNIQUE (job_id, frame_number)
);

-- The claim query filters on status and lease and orders by age, across all
-- jobs. This index matches that; without it every claim scans every frame ever
-- rendered, which is fine at a hundred rows and not at a hundred thousand.
CREATE INDEX IF NOT EXISTS render_frames_claimable_idx
    ON render_frames (status, lease_expires_at, created_at);

-- "Show me this job's progress" is the single most frequent read on this table,
-- because every open browser tab polls it.
CREATE INDEX IF NOT EXISTS render_frames_job_idx
    ON render_frames (job_id, frame_number);
