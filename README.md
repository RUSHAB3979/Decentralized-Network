# P2P Compute Marketplace MVP

This repository is a dual-track decentralized marketplace baseline:

- **Cloud Gaming** (low-latency stream sessions)
- **General Compute** (secure batch jobs)

The current implementation is intentionally minimal and optimized for proving the core matching and job lifecycle loop before persistence, queueing, and security hardening.

## Documentation Index

- `docs/UNIFIED-GPU-MARKETPLACE-PLAN.md`: Master plan for render/media jobs, hosted model APIs, GPU workstations, and cloud gaming
- `docs/PYTHON-FASTAPI-BACKEND-MIGRATION.md`: Contract-first plan for moving the core runtime from TypeScript/Express to Python/FastAPI
- `docs/PLAN.md`: Product and engineering plan with phased milestones and exit criteria
- `docs/ARCHITECTURE.md`: System architecture, component boundaries, and sequence flows
- `docs/API.md`: Endpoint reference, request/response examples, and validation behavior
- `docs/OPERATIONS.md`: Local/dev runbook, Docker usage, environment variables, and security checklist
- `docs/LEGAL-STARTER-INDIA.md`: Founder-first legal document template and India compliance map
- `docs/LEGAL-SECURITY-REQUIREMENTS-INDIA.md`: Professional legal-security control framework for launch readiness
- `docs/api-smoke-test.http`: Quick HTTP requests for manual API smoke testing

## Monorepo Layout

- `services/orchestrator`: Control plane API (provider registry, matching, compute job lifecycle)
- `services/provider-agent`: Provider daemon that emits periodic heartbeats
- `packages/contracts`: Shared Zod schemas and TypeScript types for contracts

### Backend Language Direction

The current core runtime remains the TypeScript baseline until parity tests pass. New core-backend development is planned in Python using FastAPI, Pydantic, and pytest. The React/Vite frontend and the separate GraphQL/MCP context server can remain JavaScript/TypeScript. See `docs/PYTHON-FASTAPI-BACKEND-MIGRATION.md` before changing or removing the current services.

## Quick Start

### Prerequisites

- Node.js 20+

### Local Run

1. Install dependencies:
   - `npm install`
2. Run orchestrator:
   - `npm run dev:orchestrator`
3. In a second terminal, run provider agent:
   - `npm run dev:agent`
4. Smoke test:
   - Use `docs/api-smoke-test.http` (or `curl`) against `http://localhost:8080`

### Docker Compose Run

```bash
docker compose up
```

This starts both `orchestrator` and `provider-agent` with default environment values.

## Current MVP Scope (Implemented)

- In-memory provider registry with TTL-based activity filtering
- Provider heartbeat ingestion with contract validation
- Gaming and compute provider matching endpoints
- Compute job submit and status endpoints
- Simulated provider telemetry loop from provider agent

## Near-Term Priorities

1. Replace in-memory maps with persistent storage
2. Introduce queue-backed job scheduling and retries
3. Add authn/authz and provider trust controls
4. Add workload sandboxing and secure execution path
