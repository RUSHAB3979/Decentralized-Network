# Python/Flask Backend Migration

Status: approved direction; implementation has not started.

This document defines how to migrate the core marketplace backend from TypeScript/Express to Python/Flask without breaking the existing API contract. It is intentionally a migration specification, not generated backend implementation. Rushab owns and writes the critical backend logic; AI assistance is limited to explanation, review, test design, verification, documentation, and frontend integration.

## 1. Decision

Use Python for the core marketplace backend because it is the language the founder can understand, audit, and maintain most confidently.

Target split:

| Area | Target |
|---|---|
| Customer/provider REST control plane | Python + Flask |
| Validation and API contracts | Pydantic v2 |
| Matching and scheduling domain logic | Framework-independent Python |
| Provider agent | Plain Python + `httpx` |
| Backend tests | `pytest` |
| Formatting/linting | Ruff |
| Static typing | mypy or Pyright |
| Dependency/project management | `uv` + `pyproject.toml` |
| Frontend | React/Vite JavaScript; unchanged |
| GraphQL/MCP context server | Keep TypeScript initially; migrate separately only if useful |

Flask is an implementation detail at the HTTP boundary. Matching, scheduling, state transitions, pricing, metering, and policy code must not import Flask so those modules can be tested independently and reused by workers later.

## 2. Why Migrate Now

The current runtime is still small:

- In-memory provider registry.
- In-memory compute-job registry.
- Six HTTP endpoints.
- Pure scoring-based provider matching.
- Synthetic provider heartbeat loop.
- No production database, queue, authentication, billing, or sandbox lifecycle yet.

Migration risk will increase sharply after durable state, leases, retries, auth, balances, usage ledgers, and payouts are added. Complete contract parity before implementing those systems.

## 3. Non-Negotiable Migration Rules

1. Do not delete the TypeScript implementation first.
2. Preserve API paths, HTTP status codes, JSON names, defaults, optionality, and null/omission behavior.
3. Run the TypeScript and Flask implementations against the same fixtures before cutover.
4. Do not silently redesign job states during language migration.
5. Do not combine migration with persistence, authentication, billing, or queue work.
6. Keep domain functions independent from Flask globals and request objects.
7. Do not expose the development Flask server to production traffic.
8. Remove the TypeScript core only after parity tests pass and the provider agent works end to end.

## 4. Proposed Repository Layout

Create the Python services alongside the existing TypeScript services during migration:

```text
services/
  orchestrator-python/
    pyproject.toml
    src/
      marketplace_orchestrator/
        __init__.py
        app.py
        config.py
        contracts.py
        matching.py
        state.py
    tests/
      test_contracts.py
      test_health.py
      test_heartbeats.py
      test_matching.py
      test_jobs.py
      fixtures/

  provider-agent-python/
    pyproject.toml
    src/
      marketplace_provider/
        __init__.py
        agent.py
        config.py
        heartbeat.py
    tests/
      test_config.py
      test_heartbeat.py
```

After verified cutover, the `-python` suffixes may be removed in a separate, mechanical repository cleanup. Do not mix that rename with behavioral changes.

## 5. API Surface That Must Remain Stable

| Method | Path | Success | Main failure |
|---|---|---:|---:|
| GET | `/health` | 200 | — |
| POST | `/v1/providers/heartbeat` | 200 | 400 validation |
| POST | `/v1/match/gaming` | 200 | 400 validation, 404 no provider |
| POST | `/v1/match/compute` | 200 | 400 validation, 404 no provider |
| POST | `/v1/jobs` | 202 | 400 validation |
| GET | `/v1/jobs/:id` | 200 | 404 unknown job |

The canonical examples remain in `docs/API.md`.

## 6. Contract Parity Checklist

### Provider capability

| JSON field | Rule |
|---|---|
| `gpuModel` | Optional string; omitted is valid |
| `gpuVramGb` | Optional non-negative integer; omitted is valid |
| `cpuCores` | Required positive integer |
| `ramGb` | Required positive integer |
| `supportsNvenc` | Required boolean |
| `supportsQuickSync` | Required boolean |
| `supportsGaming` | Required boolean |
| `supportsCompute` | Required boolean |

### Provider metrics

| JSON field | Rule |
|---|---|
| `region` | Required string, minimum length 2 |
| `avgRttMs` | Required non-negative number |
| `jitterMs` | Required non-negative number |
| `packetLossPct` | Required number from 0 through 100 |
| `cpuLoadPct` | Required number from 0 through 100 |
| `gpuLoadPct` | Required number from 0 through 100 |

### Provider heartbeat

| JSON field | Rule |
|---|---|
| `providerId` | Required string, minimum length 3 |
| `timestamp` | Required ISO datetime string |
| `capability` | Required provider-capability object |
| `metrics` | Required provider-metrics object |

### Gaming match request

| JSON field | Rule |
|---|---|
| `requesterId` | Required string, minimum length 3 |
| `region` | Required string, minimum length 2 |
| `maxLatencyMs` | Positive number; defaults to 80 when omitted |

### Compute match request

| JSON field | Rule |
|---|---|
| `requesterId` | Required string, minimum length 3 |
| `region` | Required string, minimum length 2 |
| `minCpuCores` | Required positive integer |
| `minRamGb` | Required positive integer |
| `requireGpu` | Boolean; defaults to false when omitted |
| `minGpuVramGb` | Optional non-negative integer |

### Compute job submission

| JSON field | Rule |
|---|---|
| `requesterId` | Required string, minimum length 3 |
| `imageRef` | Required string, minimum length 3 |
| `command` | Required non-empty array of strings |
| `region` | Required string, minimum length 2 |
| `minCpuCores` | Required positive integer |
| `minRamGb` | Required positive integer |
| `requireGpu` | Boolean; defaults to false when omitted |
| `minGpuVramGb` | Optional non-negative integer |
| `timeoutSec` | Required positive integer, maximum 86,400 |

## 7. Pydantic Compatibility Traps

Pydantic must be configured deliberately; its defaults are not automatically identical to Zod.

### Strict input types

The current Zod schemas do not convert strings such as `"8"` into numbers or `"true"` into booleans. Pydantic commonly performs coercion unless strict validation is enabled. Contract tests must prove that incorrectly typed values still return HTTP 400.

### Missing versus explicit null

An optional Zod field may be omitted, but explicit `null` is not automatically accepted. A naive Python annotation such as `str | None = None` accepts both. Preserve the current behavior unless the API is intentionally versioned.

### Unknown fields

Zod objects currently strip unknown fields. Pydantic's extra-field policy must be chosen explicitly and tested. Do not accidentally persist attacker-controlled extra fields.

### Validation status and body

Flask/Pydantic must not return a default 422 response if the existing contract promises 400. The current error envelope is:

```json
{
  "error": {
    "formErrors": [],
    "fieldErrors": {
      "region": ["validation message"]
    }
  }
}
```

Exact human-readable wording may be normalized later, but clients should not receive an unplanned Pydantic internal error structure.

### JSON naming

Python attributes may use `snake_case`, but JSON aliases must remain `camelCase`. Serialization tests must assert both input and output names.

### Optional response fields

For a submitted job with no match, `providerId` is explicitly `null`. In stored job records, an absent provider may currently be omitted by JSON serialization. Preserve this distinction until the API contract intentionally changes.

## 8. Matching Parity

Port matching as pure Python functions before writing Flask routes.

Gaming eligibility:

- Provider must support gaming.
- Provider region must equal requested region.
- Average RTT must not exceed `maxLatencyMs`.

Gaming score:

```text
100
+ 15 when NVENC or Quick Sync is available
- cpuLoadPct × 0.4
- gpuLoadPct × 0.6
- avgRttMs × 1.2
- jitterMs × 0.8
```

Compute eligibility:

- Provider must support compute.
- Provider region must equal requested region.
- CPU cores and RAM must meet minimums.
- When GPU is required, a GPU model must exist and VRAM must meet the requested minimum.

Compute score:

```text
cpuCores × 6
+ ramGb × 1.2
+ gpuVramGb × 2
- cpuLoadPct × 0.7
- gpuLoadPct × 0.7
```

Parity tests must cover ties, no eligible provider, boundary latency, boundary VRAM, missing GPU metadata, and multiple eligible providers. Do not improve the algorithm during migration; improve it after parity in a separately reviewed change.

## 9. State and Response Parity

During migration, retain the current in-memory behavior:

- Active providers are those whose last heartbeat is within `PROVIDER_TTL_MS`.
- A heartbeat upserts by `providerId` and records server receipt time.
- New job IDs begin with `job_` followed by a UUID.
- A matching provider gives a new job status `running`.
- No matching provider gives a new job status `queued`.
- Unknown match returns 404 with `No suitable provider found`.
- Unknown job returns 404 with `Job not found`.

Persistence and richer job states belong to the next feature phase, not this migration.

## 10. Migration Phases

### Phase A — Freeze behavior

- Capture valid and invalid request fixtures.
- Capture expected status codes and JSON responses.
- Record deterministic provider fixtures for matching tests.
- Keep the TypeScript service runnable as the reference implementation.

Exit: behavior is represented by tests/fixtures rather than memory.

### Phase B — Python contracts

- Initialize the orchestrator Python project.
- Implement Pydantic models and aliases.
- Add strict validation tests for every field boundary.
- Add tests for defaults, missing values, nulls, and wrong types.

Exit: Python accepts and rejects the same fixtures as Zod.

### Phase C — Pure domain logic

- Port provider records and active-provider filtering.
- Port gaming and compute scoring.
- Add deterministic matching tests.
- Keep Flask out of these modules.

Exit: matching outputs equal the TypeScript reference for all fixtures.

### Phase D — Flask boundary

- Add application factory and configuration loading.
- Add the six routes.
- Add validation and error-envelope translation.
- Add route tests through Flask's test client.

Exit: endpoint contract tests pass without running an external server.

### Phase E — Provider agent

- Port configuration parsing.
- Port heartbeat construction and bounded synthetic telemetry.
- Port the interval loop with graceful shutdown and request timeouts.
- Test payload construction independently from the infinite loop.

Exit: Python provider heartbeats appear in Flask `/health` and can be matched.

### Phase F — Side-by-side parity

- Run Express and Flask on different local ports.
- Replay the same fixture corpus against both.
- Compare status codes and normalized JSON.
- Run the smoke-test file against Flask.

Exit: no unexplained difference remains.

### Phase G — Cutover

- Update dev scripts, Docker Compose, CI, and operations documentation.
- Point provider agent and frontend API client to Flask.
- Keep a rollback path for one migration checkpoint.
- Remove old core TypeScript services only in a later cleanup.

Exit: Python is the only active core marketplace runtime in local development and CI.

## 11. Required Test Matrix

At minimum, add tests for:

- Health with zero and multiple active providers.
- Provider expiry at the TTL boundary.
- Heartbeat insert and update.
- Every required field missing.
- Wrong scalar types and explicit nulls.
- Numeric minimum and maximum boundaries.
- Default `maxLatencyMs` and `requireGpu` behavior.
- Gaming match success and no-match.
- Compute match success and no-match.
- Provider scoring order with deterministic fixtures.
- Job creation with and without a match.
- Job lookup success and 404.
- Job ID format and 202 response.
- JSON camelCase serialization.
- No traceback or Pydantic internals leaked to clients.

## 12. Development Integration

The Vite frontend currently runs on port 3000 and the orchestrator contract uses port 8080. Prefer one of these development arrangements:

1. Vite proxy: browser calls a relative `/v1/...` path and Vite forwards it to Flask.
2. Explicit API base URL: `VITE_API_BASE_URL=http://localhost:8080` plus narrowly configured CORS.

Do not use permissive `*` CORS with credentials. Production should place the frontend and API behind a controlled gateway/origin policy.

## 13. Founder/AI Ownership Boundary

Rushab writes and understands:

- Pydantic contracts.
- Matching and scheduling functions.
- State machines and persistence.
- Authentication and authorization.
- Leases, retries, idempotency, and cancellation.
- Usage ledger, billing, balances, and payouts.
- Provider trust and workload security.

AI assistance may:

- Explain Flask/Pydantic concepts.
- Review diffs and identify correctness/security issues.
- Propose test cases and fixtures.
- Run tests, linting, type checks, and smoke tests.
- Maintain frontend code and API integration.
- Maintain migration and architecture documentation.

## 14. First Implementation Task

Start only with Python contracts:

1. Initialize `services/orchestrator-python` with `uv`.
2. Add Flask, Pydantic, pytest, Ruff, and httpx as development/runtime dependencies as appropriate.
3. Implement the six request models from Section 6.
4. Write tests for valid payloads, defaults, wrong types, explicit nulls, and boundaries.
5. Do not write Flask routes until contract tests pass.

Bring that first diff for review before moving to matching logic.
