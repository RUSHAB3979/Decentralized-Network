# Python/FastAPI Backend Migration

Status: approved direction; implementation has not started.

This document defines how to migrate the core marketplace backend from TypeScript/Express to Python/FastAPI without breaking the existing API contract. It is intentionally a migration specification, not generated backend implementation. Rushab owns and writes the critical backend logic; AI assistance is limited to explanation, review, test design, verification, documentation, and frontend integration.

> **Framework decision changed 2026-08-09.** This document previously specified Flask. It now specifies FastAPI, matching the dependencies already pinned in `orchestrator/requirements.txt` and the curriculum in `docs/Plans/manual-builder-learning-plan.md` Phase B. The migration rules, contract parity tables, and matching specification below are framework-independent and are unchanged by that decision.

## 1. Decision

Use Python for the core marketplace backend because it is the language the founder can understand, audit, and maintain most confidently.

Target split:

| Area | Target |
|---|---|
| Customer/provider REST control plane | Python + FastAPI |
| ASGI server | `uvicorn[standard]` |
| Validation and API contracts | Pydantic v2 |
| Matching and scheduling domain logic | Framework-independent Python |
| Provider agent | Plain Python + `httpx` |
| Backend tests | `pytest` + `fastapi.testclient.TestClient` |
| Formatting/linting | Ruff |
| Static typing | mypy or Pyright |
| Dependency/project management | `uv` + `pyproject.toml` |
| Frontend | React/Vite JavaScript; unchanged |
| GraphQL/MCP context server | Keep TypeScript initially; migrate separately only if useful |

FastAPI is an implementation detail at the HTTP boundary. Matching, scheduling, state transitions, pricing, metering, and policy code must not import FastAPI so those modules can be tested independently and reused by workers later.

FastAPI integrates Pydantic directly into route signatures, which removes the manual parse-and-translate step Flask would have required. That convenience is also the main parity risk: the framework's default validation behavior differs from the current Zod contract in ways that must be overridden deliberately. See Section 7.

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
3. Run the TypeScript and FastAPI implementations against the same fixtures before cutover.
4. Do not silently redesign job states during language migration.
5. Do not combine migration with persistence, authentication, billing, or queue work.
6. Keep domain functions independent from FastAPI request objects and dependency injection.
7. Do not expose `uvicorn --reload` to production traffic.
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

### Validation status and body — the largest single parity risk

FastAPI returns **422 Unprocessable Entity** for request validation failures by default, with its own envelope:

```json
{
  "detail": [
    { "type": "string_too_short", "loc": ["body", "region"], "msg": "...", "input": "x" }
  ]
}
```

The existing contract promises **400** with the flattened Zod envelope:

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

These differ in both status code and body shape. Parity therefore requires an explicit `RequestValidationError` exception handler that maps Pydantic's `errors()` output into the `formErrors`/`fieldErrors` structure and returns 400. This is not optional cleanup — without it every validation test fails, and the handler must be written before any route is considered done.

Note that Pydantic's `loc` tuple begins with the request part (`"body"`, `"query"`, `"path"`); the field name is the second element for flat models and requires joining for nested ones. `capability` and `metrics` are nested objects, so nested field errors must be tested explicitly.

Exact human-readable wording may be normalized later, but clients must not receive Pydantic's internal error structure.

### JSON naming

Python attributes may use `snake_case`, but JSON aliases must remain `camelCase`. In Pydantic v2 this means `alias_generator=to_camel` with `populate_by_name=True`, and FastAPI must be told to serialize by alias — `response_model_by_alias=True` is the default but should be asserted rather than assumed. Serialization tests must assert both input and output names.

### `response_model` silently filters fields

If a route declares `response_model`, FastAPI drops any key not present on that model rather than erroring. A field missing from the response model disappears from the payload with no warning, which can silently break the contract. Either declare response models that exactly match the documented responses and test every key, or omit `response_model` during migration and return plain dictionaries.

Related: `response_model_exclude_none` and `response_model_exclude_unset` change omission behavior globally and interact directly with the null-versus-omitted rule below. Do not enable either without a test proving the resulting payloads.

### Optional response fields

For a submitted job with no match, `providerId` is explicitly `null`. In stored job records, an absent provider may currently be omitted by JSON serialization. Preserve this distinction until the API contract intentionally changes.

### Synchronous drivers in `async def` routes

`psycopg` in its synchronous mode blocks the event loop when called inside an `async def` route, degrading the whole process under concurrency while appearing correct in single-request testing. Declare routes as plain `def` unless the entire call path is awaitable — FastAPI runs `def` routes in a threadpool. Revisit only if the driver is switched to an async variant.

## 8. Matching Parity

Port matching as pure Python functions before writing FastAPI routes.

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
- Keep FastAPI out of these modules.

Exit: matching outputs equal the TypeScript reference for all fixtures.

### Phase D — FastAPI boundary

- Add the application factory and configuration loading.
- Register the `RequestValidationError` handler that produces 400 and the documented error envelope (Section 7) — before any route.
- Add the six routes.
- Add route tests through `fastapi.testclient.TestClient`.

Exit: endpoint contract tests pass without running an external server.

### Phase E — Provider agent

- Port configuration parsing.
- Port heartbeat construction and bounded synthetic telemetry.
- Port the interval loop with graceful shutdown and request timeouts.
- Test payload construction independently from the infinite loop.

Exit: Python provider heartbeats appear in FastAPI `/health` and can be matched.

### Phase F — Side-by-side parity

- Run Express and FastAPI on different local ports.
- Replay the same fixture corpus against both.
- Compare status codes and normalized JSON.
- Run the smoke-test file against FastAPI.

Exit: no unexplained difference remains.

### Phase G — Cutover

- Update dev scripts, Docker Compose, CI, and operations documentation.
- Point provider agent and frontend API client to FastAPI.
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

1. Vite proxy: browser calls a relative `/v1/...` path and Vite forwards it to FastAPI.
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

- Explain FastAPI/Pydantic concepts.
- Review diffs and identify correctness/security issues.
- Propose test cases and fixtures.
- Run tests, linting, type checks, and smoke tests.
- Maintain frontend code and API integration.
- Maintain migration and architecture documentation.

## 14. First Implementation Task

Start only with Python contracts:

1. Initialize `services/orchestrator-python` with `uv`.
2. Add FastAPI, `uvicorn[standard]`, Pydantic, pytest, Ruff, and httpx as development/runtime dependencies as appropriate.
3. Implement the six request models from Section 6.
4. Write tests for valid payloads, defaults, wrong types, explicit nulls, and boundaries.
5. Do not write FastAPI routes until contract tests pass.

Bring that first diff for review before moving to matching logic.
