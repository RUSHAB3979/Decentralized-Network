# API Reference (MVP)

Base URL (local): `http://localhost:8080`

## Accounts

Customer-facing base URL: `http://localhost:8080/v1`

API keys belong to an account. Key administration used to be gated on the caller
being loopback with `LOCAL_DEMO_MODE=true`, which is a deployment posture rather
than an identity -- everyone arriving from the right address was the same
anonymous customer, and the key they made belonged to nobody.

Passwords are stored as scrypt digests with per-row salts and self-describing
cost parameters. Sessions are opaque random tokens stored as digests; validity
is derived from the row at read time, so logout is immediate and expiry needs no
background job.

### `POST /v1/auth/signup`

Creates an account and returns a session in one step. Email is trimmed and
lowercased before validation, so `You@Example.COM ` and `you@example.com` are
one account. `409` if the address is taken. Minimum password length is 10.

### `POST /v1/auth/login`

Exchanges email and password for a session token. Returns `401` for both an
unknown address and a wrong password, with the same message and the same
response time -- an early return for unknown accounts would make the endpoint a
membership oracle for anyone with a stopwatch.

### `POST /v1/auth/logout`

Revokes the presented session. `204`, and idempotent.

### `GET /v1/auth/me`

The current account. `401` when the session is missing, expired or revoked.

## Rented Inference

Inference runs on a **provider's machine**, not on the orchestrator.

The orchestrator authenticates the customer key, picks an online provider that
advertises the model, and writes a job. The provider's agent claims that job
over a connection it opened itself, runs it against its own Ollama, and posts
the result back; the waiting customer request returns it. The agent asks for
work rather than being handed it because a provider's PC sits behind a home
router with no address the orchestrator could dial.

The customer's API key terminates at the orchestrator. The job envelope handed
to a provider carries a model and messages and has no field for a credential.

The internal pilot stores prompts and completed responses in PostgreSQL's
`inference_jobs` table for dispatch and result delivery. Those fields remain
after a job finishes. Use synthetic inputs for the pilot while application-level
encryption and terminal deletion are pending. `inference_requests` records usage
reported by the runtime. Billing-grade metering is a separate implementation
under ADR 0002 in `agent/core/meter.py`.

### `POST /v1/api-keys`

Creates a key owned by the logged-in account. Requires a session token. The
plaintext key is returned once; only its SHA-256 digest is stored.

### `GET /v1/api-keys`

Lists the calling account's keys. Never returns plaintext.

### `DELETE /v1/api-keys/{key_id}`

Revokes a key the calling account owns. `404` for a key belonging to somebody
else -- deliberately the same response as a key that does not exist, so the
endpoint cannot be used to probe for other people's key ids.

## Provider account sessions

Provider logins are separate from customer logins. All paths below use the
`/v1/provider/auth` prefix.

| Method | Path | Result |
|---|---|---|
| POST | `/signup` | `201` with a new provider session, or `403` when signup is closed |
| POST | `/login` | `200` with a provider session for valid credentials |
| GET | `/me` | `200` with the profile for the provider bearer token |
| POST | `/logout` | `204` after revoking the provider bearer token |

Signup takes `email`, `password` and optional `display_name`. Login takes
`email` and `password`. Both return `token`, `expires_at` and `provider`.
Use `python -m orchestrator.seed_users --provider provider@example.com` to
provision a provider account when `SIGNUPS_OPEN=false`.

The web console lives at `#/provider`, with sign-in and signup at
`#/provider/login` and `#/provider/signup`. It keeps a separate provider
session and shows the full enrolment key only when it is issued.

## Machine enrolment

| Method | Path | Credential and result |
|---|---|---|
| POST | `/v1/provider/enrolment-keys` | Provider session. Returns `201` with a one-time key valid for 15 minutes. |
| GET | `/v1/provider/enrolment-keys` | Provider session. Lists key prefixes and lifecycle timestamps for the account. |
| DELETE | `/v1/provider/enrolment-keys/{key_id}` | Provider session. Revokes an owned key. |
| POST | `/providers/enrol` | Enrolment key as a bearer header. Returns `201` with a node credential. |
| POST | `/providers/register` | Current node credential as a bearer header. Refreshes or reconstructs telemetry and returns `200`. |
| GET | `/v1/provider/nodes` | Provider session. Lists only the account's machines, with heartbeat status, GPU telemetry, work eligibility and revocation state. |
| DELETE | `/v1/provider/nodes/{node_id}` | Provider session. Revokes the machine credential and clears both work permissions. |
| GET | `/v1/provider/jobs` | Provider session. Lists up to 50 recent work records attributed to the account, newest claim first. |

Both machine endpoints take the same body with `node_id` and `capability`.
If heartbeat returns `404` for an authenticated node, send `/providers/register`
with its current credential and retry the heartbeat. A `401` requires an owner
to issue a new enrolment key. A lost enrolment response also needs a new key.
A fresh enrolment clears work approval. An operator must explicitly approve
the node for inference or the owner-controlled render pilot. See the
[schema and rollout notes](schema/provider-accounts.md).

The job list includes the work ID, workload type, node ID, claim and completion
timestamps, and status. The server records the provider account with each claim.
When a frame is reassigned, its row represents the latest claim. Rows from
before account attribution are omitted. The list contains operational metadata
only and excludes customer identity, content, object links, and billing amounts.

### Pilot inference approval

`POST /v1/operator/providers/nodes/{node_id}/inference-approval` takes
`provider_account_id` and a boolean `approved`. It requires a customer session
whose account has operator access. Approval requires a current node credential
and a fresh heartbeat from that enrolment. Pausing works with stale telemetry.
An owner mismatch returns `404`. A node that cannot be approved returns `409`.
Replaying an already-applied decision returns `changed: false` after checking
the same prerequisites.

The application records approval changes and credential revocation in
`provider_node_events` in the same transaction as the corresponding changes.
Each record contains a timestamp, event type, node ID, provider account ID and
authenticated actor ID.

## Provider work queue

Inference and frame claims require a current node credential, a fresh
heartbeat, and operator approval for the workload.

### `POST /providers/work/claim?node_id=...`

Returns at most one job, or `{"job": null}` when there is nothing to do, and
answers immediately -- it does not hold the request open. The response carries
`poll_interval_s` (`CLAIM_POLL_INTERVAL_SEC`, default 3), and the agent waits
that long before asking again. Without that wait the agent spins: constant load
from a fleet doing nothing, and on metered hosting, a bill.

A job is claimable when it is queued, or when it was claimed and its lease has
lapsed. Expiry is derived at read time -- there is no sweeper, because a sweeper
that died would strand every in-flight job in `claimed` forever with nothing
raising. Concurrent claims are serialised with `FOR UPDATE SKIP LOCKED`, so two
agents asking at the same instant cannot receive the same job.

### `POST /providers/work/{job_id}/result?node_id=...`

Terminal, accepted once, and only from the node holding the claim. `409` if the
lease already lapsed and the job went elsewhere -- the agent should drop the
result rather than retry.

### `GET /v1/models`

Requires `Authorization: Bearer <api-key>` and lists models available on the
configured online provider.

### `POST /v1/chat/completions`

Accepts an OpenAI-style non-streaming chat body and returns one assistant
choice plus token usage. The requested model must be in the provider's
reported `local_models` list.

```json
{
  "model": "tinyllama:latest",
  "messages": [
    {"role": "user", "content": "Say hello in one sentence."}
  ]
}
```

### `GET /v1/usage`

Requires the same Bearer key and returns aggregate request, token, and duration
totals for that key.

This is not production-ready. Provider credentials, TLS, workload isolation,
rate limiting, billing, multi-provider scheduling, and failover are still
required before internet deployment.

The current TypeScript baseline validates JSON payloads with shared Zod schemas from `packages/contracts`. The planned Python/FastAPI implementation must preserve this documented behavior using Pydantic before cutover; see [PYTHON-FASTAPI-BACKEND-MIGRATION.md](PYTHON-FASTAPI-BACKEND-MIGRATION.md).

## Health

### `GET /health`

Response:

```json
{
  "ok": true,
  "providers": 1,
  "jobs": 2
}
```

## Provider Heartbeat

### `POST /v1/providers/heartbeat`

Request body:

```json
{
  "providerId": "provider-local-1",
  "timestamp": "2026-08-01T00:00:00.000Z",
  "capability": {
    "gpuModel": "RTX-4070",
    "gpuVramGb": 12,
    "cpuCores": 12,
    "ramGb": 32,
    "supportsNvenc": true,
    "supportsQuickSync": false,
    "supportsGaming": true,
    "supportsCompute": true
  },
  "metrics": {
    "region": "us-east-1",
    "avgRttMs": 28,
    "jitterMs": 4,
    "packetLossPct": 0.2,
    "cpuLoadPct": 35,
    "gpuLoadPct": 40
  }
}
```

Success response:

```json
{
  "ok": true,
  "providerId": "provider-local-1"
}
```

## Match Endpoints

### `POST /v1/match/gaming`

Request body:

```json
{
  "requesterId": "req-1",
  "region": "us-east-1",
  "maxLatencyMs": 80
}
```

Success response:

```json
{
  "providerId": "provider-local-1",
  "region": "us-east-1",
  "avgRttMs": 23.5,
  "supportsEncoder": true
}
```

### `POST /v1/match/compute`

Request body:

```json
{
  "requesterId": "req-2",
  "region": "us-east-1",
  "minCpuCores": 8,
  "minRamGb": 16,
  "requireGpu": true,
  "minGpuVramGb": 8
}
```

Success response:

```json
{
  "providerId": "provider-local-1",
  "region": "us-east-1",
  "cpuCores": 12,
  "ramGb": 32,
  "gpuModel": "RTX-4070",
  "gpuVramGb": 12
}
```

## Compute Jobs

### `POST /v1/jobs`

Request body:

```json
{
  "requesterId": "req-3",
  "imageRef": "ghcr.io/acme/render:latest",
  "command": ["blender", "-b", "scene.blend", "-f", "1"],
  "region": "us-east-1",
  "minCpuCores": 8,
  "minRamGb": 16,
  "requireGpu": true,
  "minGpuVramGb": 8,
  "timeoutSec": 3600
}
```

Success response (`202 Accepted`):

```json
{
  "jobId": "job_11111111-2222-3333-4444-555555555555",
  "status": "running",
  "providerId": "provider-local-1"
}
```

When no provider matches immediately:

```json
{
  "jobId": "job_11111111-2222-3333-4444-555555555555",
  "status": "queued",
  "providerId": null
}
```

### `GET /v1/jobs/:id`

Success response:

```json
{
  "id": "job_11111111-2222-3333-4444-555555555555",
  "status": "running",
  "createdAt": "2026-08-01T00:00:00.000Z",
  "providerId": "provider-local-1",
  "request": {
    "requesterId": "req-3",
    "imageRef": "ghcr.io/acme/render:latest",
    "command": ["blender", "-b", "scene.blend", "-f", "1"],
    "region": "us-east-1",
    "minCpuCores": 8,
    "minRamGb": 16,
    "requireGpu": true,
    "minGpuVramGb": 8,
    "timeoutSec": 3600
  }
}
```

## Error Behavior

- `400 Bad Request`: schema validation failed.
- `404 Not Found`:
  - no suitable provider found (match endpoints)
  - unknown job id (`GET /v1/jobs/:id`)

Validation error shape:

```json
{
  "error": {
    "formErrors": [],
    "fieldErrors": {
      "region": ["String must contain at least 2 character(s)"]
    }
  }
}
```
