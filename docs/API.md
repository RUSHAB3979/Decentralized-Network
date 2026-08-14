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

Prompts and responses are not stored. `inference_requests` keeps usage metadata
as evidence of what a runtime reported; it is **not** a bill. Turning those
counts into an amount owed is metering, which is hand-built under ADR 0002 and
lives in `agent/core/meter.py`.

### `POST /v1/api-keys`

Creates a key owned by the logged-in account. Requires a session token. The
plaintext key is returned once; only its SHA-256 digest is stored.

### `GET /v1/api-keys`

Lists the calling account's keys. Never returns plaintext.

### `DELETE /v1/api-keys/{key_id}`

Revokes a key the calling account owns. `404` for a key belonging to somebody
else -- deliberately the same response as a key that does not exist, so the
endpoint cannot be used to probe for other people's key ids.

## Provider Work Queue

Agent-facing. Authenticated with the node credential returned once by
`POST /providers/register`.

Scope note: that credential authenticates the transport and nothing more. Secure
storage on the provider's machine, rotation, and binding the credential to the
hardware are `agent/core/creds.py`'s job -- hand-built under ADR 0002 and still
unwritten. The agent currently keeps the token in a plaintext file.

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
