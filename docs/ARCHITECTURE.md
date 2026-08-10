# Architecture

> **Implementation status:** This document describes the currently running TypeScript baseline. The approved Python/FastAPI migration is specified in [PYTHON-FASTAPI-BACKEND-MIGRATION.md](PYTHON-FASTAPI-BACKEND-MIGRATION.md); API behavior must remain stable until parity is verified.

## 1. System Overview

Current MVP consists of three modules:

- **`services/orchestrator`**: HTTP control plane that ingests provider heartbeats, selects providers, and tracks compute jobs.
- **`services/provider-agent`**: long-running daemon on provider machines that reports capabilities/metrics.
- **`packages/contracts`**: shared Zod schemas + TypeScript types used by both services.

## 2. Current Runtime Model

- Provider heartbeats are validated and stored in an in-memory map.
- Active providers are computed by `lastSeenEpochMs` freshness against `PROVIDER_TTL_MS`.
- Matching is synchronous and score-based:
  - Gaming: region + latency fit, then encoder/load/latency scoring.
  - Compute: region + resource constraints fit, then capacity/load scoring.
- Compute jobs are in-memory records with status `queued | running | completed | failed`.

## 3. Component Boundaries

## Orchestrator

- **Ingress APIs**
  - `POST /v1/providers/heartbeat`
  - `POST /v1/match/gaming`
  - `POST /v1/match/compute`
  - `POST /v1/jobs`
  - `GET /v1/jobs/:id`
  - `GET /health`
- **State**
  - `providers: Map<string, ProviderRecord>`
  - `jobs: Map<string, ComputeJobRecord>`
- **Core logic**
  - Contract validation (Zod)
  - Active provider filtering (TTL)
  - Provider selection (matching module)

## Provider Agent

- Produces synthetic metrics each heartbeat interval.
- Validates payload against shared schema before send.
- Posts to orchestrator and logs success/failure.

## Contracts Package

- Canonical contract schemas and inferred types:
  - `ProviderHeartbeat`
  - `GamingMatchRequest`
  - `ComputeMatchRequest`
  - `ComputeJobSubmit`

## 4. Sequence Flows

## 4.1 Heartbeat flow

1. Provider agent builds heartbeat payload.
2. Provider agent validates payload locally.
3. Provider agent sends `POST /v1/providers/heartbeat`.
4. Orchestrator validates payload.
5. Orchestrator upserts provider and records `lastSeenEpochMs`.

## 4.2 Gaming match flow

1. Client calls `POST /v1/match/gaming`.
2. Orchestrator validates request.
3. Orchestrator filters active providers.
4. Matching engine scores candidates and selects best provider.
5. Orchestrator returns selected provider metadata or `404`.

## 4.3 Compute job submit flow

1. Client calls `POST /v1/jobs`.
2. Orchestrator validates request.
3. Orchestrator runs compute matching.
4. Orchestrator creates job record:
   - `running` when provider found
   - `queued` when no provider found
5. Orchestrator returns `202` with job status and optional provider.

## 5. Data Contracts (High-Level)

## Provider heartbeat

- Identity: `providerId`
- Timing: `timestamp`
- Capability: CPU/RAM/GPU/encoder support flags
- Telemetry: region, RTT, jitter, packet loss, CPU/GPU load

## Compute job

- Requester metadata
- Image reference and command list
- Resource constraints
- Timeout
- Runtime assignment (`providerId`) and status

## 6. Known Architectural Limits (MVP)

- In-memory state is process-local and non-durable.
- No multi-instance consistency model.
- No authentication between clients/providers and orchestrator.
- No real execution sandbox or job worker lifecycle.

## 7. Planned Evolution

1. Durable datastore for providers/jobs.
2. Queue and worker coordination for execution state transitions.
3. Authn/authz and provider trust model.
4. Sandbox-based secure execution path.
