# Product + Engineering Plan

## 1. Vision

Build a decentralized marketplace that routes workloads to suitable provider machines across two tracks:

- **Gaming track**: low-latency, encoder-capable providers for interactive sessions.
- **Compute track**: capacity-aware providers for batch workloads with optional GPU constraints.

## 2. MVP Goals

1. Prove end-to-end matching and job/session lifecycle feasibility.
2. Standardize contracts shared by orchestrator and provider agent.
3. Enable local and Docker-based reproducible development.

## 3. MVP Non-Goals

- Production-grade authentication/authorization.
- Durable job history and provider state.
- Real container sandbox execution pipeline.
- Billing, quotas, payouts, and anti-fraud controls.

## 4. Current Status

**Phase 0 complete (baseline):**

- Provider heartbeat ingestion with validation.
- Active provider registry (TTL-based).
- Gaming and compute matching APIs.
- Compute job submission/status APIs.
- Provider-agent heartbeat loop with capabilities and metrics payload.

## 5. Milestone Plan

## Phase 1: Reliability + Persistence

**Scope**

- Replace in-memory maps with persistent datastore.
- Add provider/job repository abstraction.
- Preserve existing API surface.

**Exit criteria**

- Orchestrator restart no longer loses providers/jobs.
- Job status endpoint remains stable across restarts.
- Data model supports provider capabilities and job lifecycle fields.

## Phase 2: Scheduling + Execution Control

**Scope**

- Queue-backed job scheduling.
- Worker pull/ack flow with lease timeouts.
- Retry and terminal failure handling.

**Exit criteria**

- Queued jobs transition deterministically to running/completed/failed.
- Lease expiry re-queues orphaned jobs.
- Basic backpressure strategy exists for queue growth.

## Phase 3: Security Hardening

**Scope**

- Request authentication for clients and providers.
- Provider identity verification and key rotation.
- Input policy validation for image references and command constraints.

**Exit criteria**

- Unauthorized calls are rejected for protected endpoints.
- Provider onboarding has verifiable trust material.
- Auditable security events are emitted for auth failures and policy violations.

## Phase 4: Sandbox Execution

**Scope**

- Isolated workload execution environment.
- Resource limits and timeout enforcement.
- Secure artifact/log collection pipeline.

**Exit criteria**

- Jobs execute in bounded isolation with enforced CPU/RAM/GPU limits.
- Timeout and cancellation paths are deterministic.
- Execution logs and outcomes are accessible via orchestrator APIs.

## 6. Success Metrics

- **Matching availability**: successful provider matches for valid requests.
- **Placement latency**: request-to-provider decision latency.
- **Heartbeat freshness**: ratio of active providers with fresh heartbeat within TTL.
- **Queue health** (post-Phase 2): time in queue and retry distribution.
- **Security signal quality** (post-Phase 3): auth failure detection and policy violation observability.

## 7. Key Risks + Mitigations

- **Risk**: stale provider metrics causing poor placement.
  - **Mitigation**: heartbeat TTL, freshness checks, and eventual weighted recency scoring.
- **Risk**: untrusted workloads on provider machines.
  - **Mitigation**: strict allowlists, signed artifacts, and sandbox isolation roadmap.
- **Risk**: scheduler hot spots under load.
  - **Mitigation**: queue partitioning and resource-aware scheduling strategy.
