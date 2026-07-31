# Operations and Security Runbook

## 1. Prerequisites

- Node.js 20+
- npm
- Docker (optional, for compose workflow)

## 2. Environment Variables

Use `.env.example` as the baseline.

### Orchestrator

- `PORT` (default `8080`)
- `PROVIDER_TTL_MS` (default `120000`)

### Provider Agent

- `PROVIDER_ID` (default `provider-local-1`)
- `ORCHESTRATOR_URL` (default `http://localhost:8080`)
- `REGION` (default `us-east-1`)
- `HEARTBEAT_SEC` (default `15`)
- Capability fields (`GPU_MODEL`, `GPU_VRAM_GB`, `CPU_CORES`, `RAM_GB`, `SUPPORTS_*`)

## 3. Local Development

1. Install:
   - `npm install`
2. Start orchestrator:
   - `npm run dev:orchestrator`
3. Start provider-agent:
   - `npm run dev:agent`
4. Verify:
   - `GET /health` returns `ok: true`
   - `providers` increases after heartbeats

## 4. Docker Compose Development

Run:

```bash
docker compose up
```

Notes:

- Compose uses `ORCHESTRATOR_URL=http://orchestrator:8080` for the provider-agent container.
- Repository is mounted into both containers; code changes are reflected live.

## 5. Basic Troubleshooting

## Provider count stays at 0

- Ensure provider-agent is running.
- Confirm `ORCHESTRATOR_URL` points to reachable orchestrator.
- Check logs for heartbeat failure response status/body.

## Match endpoints return 404

- Confirm provider region and capabilities satisfy request constraints.
- Validate heartbeat freshness (`PROVIDER_TTL_MS`) and agent heartbeat interval.

## Job stuck in queued

- No provider currently meets job constraints.
- Reduce constraints or start providers with stronger capability values.

## 6. Security Posture (Current vs Planned)

## Current MVP posture

- Input validation via Zod for all primary request payloads.
- Explicit errors for invalid payloads and failed provider/job lookup.

## Current gaps

- No authentication for API callers or providers.
- No authorization boundaries between tenants/requesters.
- No execution sandbox for submitted compute jobs.
- No signed workload artifacts or provider attestation.

## Required hardening before production

1. Add mTLS or token-based auth for providers and clients.
2. Enforce request-level authorization with tenant scoping.
3. Add workload policy controls (image allowlists, command restrictions).
4. Implement isolated runtime sandbox with strict resource limits.
5. Add immutable audit logs for auth, scheduling, and execution events.

## 7. Suggested SLO Starter Set

- Heartbeat ingest availability.
- Match decision latency.
- Provider freshness ratio (active/fresh vs stale).
- Job placement time (submit to running).

Use these as baseline operational KPIs while introducing persistence and queueing.
