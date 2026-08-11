# Claude Code instructions — P2P Compute Marketplace

## Source of truth
Before substantial work, read `README.md`, `docs/adr/0002-generated-vs-handbuilt.md`, `docs/adr/0003-inference-beachhead.md`, and the relevant current plan/task document. ADR 0003 (inference beachhead) and ADR 0002 (generation boundary) supersede older gaming-first and "hand-write every backend line" text that still exists in historical documents.

Use the repository's `startup-context` MCP to retrieve risks, standing rules, phases, roles, and indexed docs when useful. Verify consequential claims against the underlying tracked file.

## Current architecture
- Beachhead: metered LLM inference on idle consumer GPUs; Ollama is the native-Windows provider runtime. Cloud gaming is deferred, not removed.
- Live code: `orchestrator/` (Python/FastAPI), `agent/` (Python provider app), and `web-client/` (React/Vite).
- Frozen reference only: `services/orchestrator/`, `services/provider-agent/`, and `packages/contracts/`. Do not run or extend the frozen TypeScript backend unless explicitly asked.
- `agent/requirements.txt` is a security boundary: the provider agent must not receive database reach or broad cloud credentials.

## Generate vs hand-build boundary
Generate by default, including frontend, CRUD endpoints, Pydantic models, migrations, auth integration, billing-provider integration, CI/Docker/config, and documentation.

Do not write the final implementation for components whose defects can silently degrade while appearing successful unless Rushab explicitly overrides this boundary. For those areas, teach, help define invariants, design failure-injection tests, review Rushab's code, and make him explain the result. Current hand-built areas are:
- provider sandbox and tenant isolation;
- metering and billing-unit correctness;
- inference result integrity/model identity;
- capacity and throughput benchmarks;
- model residency, concurrency fallback, and cold starts;
- lease expiry, reclaim, and lifecycle reconciliation;
- WebRTC/ICE/TURN/capture-encode-transport if gaming resumes.

When classification is unclear, ask: "If this is wrong, will something reliably raise?" If not, treat it as hand-built.

## Required workflow
1. Establish the current milestone and acceptance gate before coding. Do not build later marketplace surfaces ahead of evidence.
2. Inspect definitions/usages, manifests, contracts, and neighbouring tests before edits. Use Context7 for version-specific APIs.
3. For generated code, explain the critical flow and failure modes so Rushab can review it before merge.
4. Test both success and deliberately induced failure paths. Every network operation needs an explicit timeout; retryable operations need idempotency analysis.
5. Never use bare `docker compose up`; the documented safe database command is `docker compose up -d db`.
6. Use Python 3.11 for the live backend, matching CI and `.ruff.toml`.
7. Keep all changes local. Never commit/push/deploy without explicit permission.

## Verification
- Python: use the component's Python 3.11 environment and run focused tests/ruff as configured; do not silently substitute Python 3.13.
- TypeScript workspace: `npm run typecheck` and the relevant workspace build.
- Frontend: `npm run build` in `web-client/`, then use Playwright against the running app and inspect console errors, failed requests, responsive layouts, and the changed user flow.
- Repository context server: `npm run typecheck -w @market/context-server` and `npm run build -w @market/context-server`.
- End every implementation report with commands actually run, their outcomes, remaining risks, and files changed.
