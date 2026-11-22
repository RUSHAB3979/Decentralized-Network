# Detailed Implementation & Execution Plan
**P2P Cloud Gaming & Compute Marketplace**

**Status:** Living Engineering Blueprint · Created 2026-07-26  
**Parent Plan:** [`docs/Plans/plan.md`](./plan.md)  
**Learning Roadmap:** [`docs/Plans/manual-builder-learning-plan.md`](./manual-builder-learning-plan.md)  
**Task Tracker:** [`docs/Tasks/tasks.md`](../Tasks/tasks.md)  

---

## 1. Deep-Research Gap Analysis: Plan vs Current Codebase

### 1.1 Summary of Found Gaps
| Layer | Declared Intent in `plan.md` / `tasks.md` | Actual Codebase State Today | Gap & Required Work |
|---|---|---|---|
| **Database** | Postgres 16 running via Docker Compose | `docker-compose.yml` present; container unverified | Run container, run `SELECT 1` health query from Python |
| **Orchestrator** | FastAPI control-plane API with `/health` and DB ping | `orchestrator/requirements.txt` only (`fastapi`, `uvicorn`, `psycopg`); no `main.py` or routes | Build `orchestrator/main.py`, FastAPI app, `/health` route with Postgres connectivity check |
| **Agent** | Python daemon pinging orchestrator `/health` | Directory `agent/` missing or empty | Build `agent/main.py` daemon, read `ORCHESTRATOR_URL` from `.env`, execute HTTP GET, exit codes |
| **Web Client** | React 18 + TS + Tailwind frontend (`web-client/`) | Full SPA built with mock client (`src/services/api.ts`) | Wire live API fallback in `api.ts` to hit real `http://localhost:8000/health`, add real backend endpoints as M1/M2/M3 progress |
| **ADRs** | Architectural decision records for trust boundaries & legal rules | `docs/` has `plan.md` and `manual-builder-learning-plan.md`; no `ADR-001` or `ADR-002` | Draft `ADR-001` (Control-plane / media trust boundaries) & `ADR-002` (Title approval & BYOL stance) before M2 |

---

## 2. Architecture & Subsystem Blueprint

```
┌──────────────────────────────────────────────────────────────────────────┐
│                            Consumer Browser                              │
│  React 18 + TS Web-Client (Catalog / Preflight / Session / Debugger)    │
└───────────────────┬──────────────────────────────────▲───────────────────┘
                    │ WSS / HTTP                       │ WebRTC Direct / TURN
                    ▼                                  │ Relay
┌─────────────────────────────────────────┐            │
│          Orchestrator Control           │            │
│   FastAPI (Auth, Catalog, State Machine)│            │
└─────────┬───────────────────────┬───────┘            │
          │ SQL                   │ HTTP Polling /     │
          ▼                       │ Outbound WSS       │
┌───────────────────┐    ┌────────┴────────────────────┴───────────────────┐
│ PostgreSQL 16 DB  │    │            Provider Agent Daemon                │
│ (Users, Nodes,    │    │   (Hardware Discovery, Heartbeat, Supervision)   │
│  Sessions, Audit) │    └─────────────────────────┬───────────────────────┘
└───────────────────┘                              │ Local process IPC
                                                   ▼
                                         ┌───────────────────┐
                                         │  Media Host App   │
                                         │  (Dedicated Host) │
                                         └───────────────────┘
```

---

## 3. Milestone-by-Milestone Implementation Plan

---

### Milestone M0: Local Control-Plane Hello World
**Goal:** Run Postgres container → start FastAPI orchestrator (`GET /health`) → execute agent ping → confirm end-to-end local connectivity.

#### Task Breakdown & File Specifications

1. **`docker-compose.yml` (Postgres Container)**
   - Confirm Postgres 16 container (`marketplace_db`) starts cleanly on `5432:5432`.
   - Use the `marketplace` user and database. Set `POSTGRES_PASSWORD` in your local `.env` file.

2. **`orchestrator/main.py` (FastAPI Server)**
   ```python
   # Required Endpoints:
   GET /health
   # Response Contract:
   {
     "status": "ok" | "degraded",
     "db": "ok" | "unhealthy",
     "version": "0.1.0"
   }
   ```
   - Connects to Postgres via `psycopg` pool using `DATABASE_URL` from `.env`.
   - Runs `SELECT 1;` on health request; returns HTTP 200 when DB is connected, HTTP 503 (`status: degraded`, `db: unhealthy`) when DB fails.

3. **`agent/main.py` (Provider Daemon Baseline)**
   - Reads `ORCHESTRATOR_URL` (default `http://localhost:8000`) from `.env`.
   - Sends HTTP GET to `/health` with 5s timeout.
   - Logs timestamped status; exits with code `0` on success, `1` on failure.

4. **Frontend Integration (`web-client/src/services/api.ts`)**
   - `checkOrchestratorHealth()` queries `http://localhost:8000/health`.
   - Falls back gracefully to `{ status: 'unreachable', db: 'mock', version: '0.1.0-mock' }` if orchestrator is offline.

#### Definition of Done (DoD) for M0
- [ ] `docker compose up -d` starts Postgres without errors.
- [ ] `python orchestrator/main.py` exposes `/health` returning `{"status":"ok","db":"ok","version":"0.1.0"}`.
- [ ] `python agent/main.py` outputs `[INFO] Orchestrator reachable: ok (DB: ok)`.
- [ ] `npm run build` in `web-client/` passes cleanly.

---

### Milestone M1: Provider Identity & Observed Availability
**Goal:** Allow an approved dedicated node to enroll, heartbeat periodically, report hardware state, and transition to `online_idle` / `offline`.

#### Data Schema (`migrations/001_provider_nodes.sql`)
```sql
CREATE TYPE node_state AS ENUM (
  'pending_approval', 'enrolled', 'online_idle',
  'reserved', 'launching', 'streaming', 'draining',
  'quarantined', 'revoked', 'error_cooldown'
);

CREATE TABLE provider_nodes (
  node_id VARCHAR(64) PRIMARY KEY,
  name VARCHAR(128) NOT NULL,
  state node_state NOT NULL DEFAULT 'pending_approval',
  region VARCHAR(32) NOT NULL,
  host_class VARCHAR(64) NOT NULL DEFAULT 'dedicated_test_machine',
  public_key TEXT,
  last_heartbeat_at TIMESTAMPTZ,
  telemetry JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_provider_nodes_state ON provider_nodes(state);
CREATE INDEX idx_provider_nodes_heartbeat ON provider_nodes(last_heartbeat_at);
```

#### API Endpoints (`orchestrator/routes/providers.py`)
- `POST /api/v1/providers/register`: One-time enrollment with device public key.
- `POST /api/v1/providers/heartbeat`: Signed payload containing `node_id`, `state`, `telemetry` (GPU, VRAM, temp, power), and timestamp.
- **TTL Sweeper Background Task:** Runs every 10s; sets nodes with `last_heartbeat_at < NOW() - 15s` from `online_idle` → `offline` (reconciliation).

#### Definition of Done (DoD) for M1
- [ ] Migration applies cleanly to Postgres.
- [ ] Node agent registers, generates local keypair, and sends signed heartbeats every 5 seconds.
- [ ] Stopping the agent causes orchestrator to mark node offline after 15 seconds.
- [ ] `NodeTelemetry.tsx` component in web-client visualizes live provider node states from API.

---

### Milestone M2: Media Feasibility Spike
**Goal:** Prove browser WebRTC streaming pipeline on representative networks; measure time-to-first-frame, bitrate, FPS, RTT, jitter, and direct vs relay connection.

#### Key Tasks
1. **Signaling Service (`orchestrator/routes/signaling.py`)**
   - WebSocket endpoint `/ws/signaling/{session_id}` exchanging WebRTC SDP offers/answers and ICE candidates.
2. **TURN / STUN Infrastructure Configuration**
   - Configure coturn or managed Twilio/Xirsys TURN credentials.
   - Enforce authenticated, short-lived TURN tokens.
3. **Media Host Adapter Spike**
   - Test candidate stream host (Sunshine / WebRTC bridge) on a dedicated Windows test node.
   - Collect WebRTC stats via `RTCPeerConnection.getStats()` in `SessionPlayer.tsx`.
4. **Deliverable: `ADR-003-media-stack.md`**
   - Written evaluation of 10 test sessions; choice/rejection of media host technology based on objective evidence.

#### Definition of Done (DoD) for M2
- [ ] 10 instrumented sessions completed on 2 distinct network paths.
- [ ] Preflight diagnostic (`PreflightModal.tsx`) accurately measures RTT, jitter, and packet loss.
- [ ] `ADR-003` committed to repository.

---

### Milestone M3: Safe Internal Session Vertical Slice
**Goal:** End-to-end session lifecycle: Request → Match → Bounded Launch → WebRTC Stream → End → Clean Up → Reconcile.

#### State Machine Verification
```
Session: requested → eligibility_checked → offered → accepted → reserved → launching → signaling → connecting → live → ending → cleaned → completed
```

#### Safety & Isolation Rules
- Host execution runs under non-administrator Windows account (`game_user`).
- Launch path strictly restricted to allowlisted executables.
- Input capture bounded to remote video container (`requestPointerLock` + clamped mouse coordinates).

#### Definition of Done (DoD) for M3
- [ ] 20 internal sessions executed across 3 dedicated test hosts.
- [ ] Emergency Stop button in `SessionPlayer.tsx` immediately terminates remote process and triggers cleanup.
- [ ] Zero unhandled process leaks or orphaned host processes.

---

## 4. Engineering Standards & Quality Checklist

1. **Accessibility (UIA / Screen Readers):**
   - All interactive elements must specify `aria-label` or visible text.
   - Modal overlays must provide `role="dialog"`, `aria-modal="true"`, `aria-labelledby`, and trap keyboard focus.

2. **Numerical & Layout Robustness:**
   - Numerical metrics displayed in UI must be explicitly rounded (`Math.round`, `.toFixed()`).
   - Flex/grid metric containers must enforce `overflow-hidden` and `truncate` to prevent layout breaking.

3. **Performance & Energy Efficiency:**
   - Background telemetry polling loops must check `document.hidden` and pause when tabs are inactive.

4. **Security & Data Isolation:**
   - No store credentials, personal account data, or arbitrary shell commands passed via API.

---

## 5. Next Concrete Action Items

1. Create `orchestrator/main.py` with FastAPI `/health` endpoint and Postgres `SELECT 1` check.
2. Create `agent/main.py` Python daemon script.
3. Commit `docs/Plans/detailed-plan.md` to git repository.
4. Run full smoke test of Milestone M0 and update `docs/Tasks/tasks.md`.
