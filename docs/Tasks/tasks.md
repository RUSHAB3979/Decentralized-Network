# Task Tracker — P2P Cloud Gaming Marketplace

**Owner:** You (solo, collaborators later)  
**Stack (now):** Python only · Windows · Postgres via Docker  
**Cadence:** ~2–3 hours/day  
**Sparring mode:** You write all code · plan/review with co-founder agent  

**Related:** [plan.md](./plan.md)

---

## Current focus

| Field | Value |
|--------|--------|
| **Milestone** | M0 — Control-plane hello world |
| **Phase** | Phase 0 (Foundations) → edge of Phase 1 |
| **Started** | 2026-07-15 |
| **Hard deadline** | **2026-07-17 (Friday) end of day** |
| **Stretch polish deadline** | 2026-07-21 (Monday) end of day |

---

## Milestone M0 — Control-plane hello world

### Goal (one sentence)

Postgres up → orchestrator `GET /health` OK → agent pings orchestrator and logs success.

### Why this first

Without a node that can reach the orchestrator, catalog/streaming/matching are fiction.

### Definition of done (DoD)

- [ ] Docker Postgres is running on Windows (Docker Desktop)
- [ ] Orchestrator starts and `GET /health` returns success (browser, curl, or Invoke-WebRequest)
- [ ] Orchestrator can talk to Postgres (`SELECT 1` or health reports `db: ok`)
- [ ] Agent starts, reads orchestrator URL from env, hits `/health`, logs reachable
- [ ] `.gitignore` excludes venv, `.env`, `__pycache__`, IDE junk
- [ ] `.env.example` documents required vars (no real secrets committed)
- [ ] `README.md` explains how to run DB, orchestrator, and agent on Windows

**Out of scope for M0:** auth, register/heartbeat tables, catalog, WebRTC, C++, payments.

---

## Task breakdown + deadlines

### Block A — Repo hygiene  
**Deadline: 2026-07-15 (today)** · Estimate: ~45–60 min

| ID | Task | Status | Done |
|----|------|--------|------|
| A1 | `git init` (if not already) | pending | [ ] |
| A2 | Add `.gitignore` (Python, venv, `.env`, Windows/IDE) | pending | [ ] |
| A3 | Add `.env.example` (`DATABASE_URL`, `ORCHESTRATOR_URL` placeholders) | pending | [ ] |
| A4 | Add root `README.md` (what / how to run — can be stub first) | pending | [ ] |
| A5 | Create folders: `orchestrator/`, `agent/` (and optional `docs/`) | pending | [ ] |

---

### Block B — Postgres  
**Deadline: 2026-07-15 (today) or 2026-07-16 morning** · Estimate: ~30–45 min

| ID | Task | Status | Done |
|----|------|--------|------|
| B1 | Install/verify Docker Desktop on Windows | pending | [ ] |
| B2 | Add `docker-compose.yml` with Postgres only | pending | [ ] |
| B3 | `docker compose up -d` and confirm container healthy | pending | [ ] |
| B4 | Confirm you can connect (any client or one-shot command) | pending | [ ] |

---

### Block C — Orchestrator health  
**Deadline: 2026-07-16 (Thursday)** · Estimate: ~60–90 min

| ID | Task | Status | Done |
|----|------|--------|------|
| C1 | Create orchestrator package + venv + dependencies (FastAPI) | pending | [ ] |
| C2 | App entrypoint that starts an HTTP server | pending | [ ] |
| C3 | Implement `GET /health` → JSON ok | pending | [ ] |
| C4 | Load `DATABASE_URL` from env; run `SELECT 1` | pending | [ ] |
| C5 | Extend health (or separate check) so DB failure is visible | pending | [ ] |

---

### Block D — Agent ping  
**Deadline: 2026-07-17 (Friday) — HARD DEADLINE for full M0** · Estimate: ~45–75 min

| ID | Task | Status | Done |
|----|------|--------|------|
| D1 | Create agent package + venv (or shared workspace venv — document choice) | pending | [ ] |
| D2 | Read `ORCHESTRATOR_URL` from env | pending | [ ] |
| D3 | HTTP GET `{ORCHESTRATOR_URL}/health` | pending | [ ] |
| D4 | Log clear success / failure (exit non-zero on failure is a plus) | pending | [ ] |
| D5 | Update README with exact Windows run steps for all three pieces | pending | [ ] |

---

### Block E — Stretch polish (collaborator-ready)  
**Deadline: 2026-07-21 (Monday)** · Estimate: 1–2 sessions after M0

| ID | Task | Status | Done |
|----|------|--------|------|
| E1 | Pin dependencies (`requirements.txt` or `pyproject.toml`) | pending | [ ] |
| E2 | Short ADR: hybrid architecture, Python now / C++ later | pending | [ ] |
| E3 | Short ADR: BYOL + allowlist legal model | pending | [ ] |
| E4 | Domain notes: list entities User / ProviderNode / Session (comments or doc only) | pending | [ ] |

---

## Deadline summary

| Milestone | Deadline | Severity |
|-----------|----------|----------|
| Blocks A–B (repo + Postgres) | **2026-07-15** | Soft (same day start) |
| Block C (orchestrator health + DB) | **2026-07-16** | Firm |
| **M0 complete (A–D)** | **2026-07-17 EOD** | **HARD** |
| Block E (polish) | **2026-07-21 EOD** | Soft stretch |

**If you miss the hard deadline:** do not expand scope. Finish only D1–D4 before anything else. No catalog, no streaming “to catch up.”

---

## Daily plan (suggested, 2–3 hrs/day)

| Day | Date | Focus |
|-----|------|--------|
| Day 1 | Wed 2026-07-15 | A + B (+ start C if time) |
| Day 2 | Thu 2026-07-16 | Finish C |
| Day 3 | Fri 2026-07-17 | D → **M0 done** |
| Weekend buffer | 2026-07-18–19 | Only if M0 slipped; otherwise rest or light README |
| Day 4–5 | 2026-07-20–21 | E polish optional |

---

## After M0 (do not start early)

**Next milestone M1 — Register + heartbeat** (deadline to set when M0 is checked off)

Preview only:

1. `ProviderNode` table + migration  
2. `POST /providers/register`  
3. `POST /providers/heartbeat`  
4. Agent loop every N seconds  
5. Stale → offline (TTL)

---

## Status legend

- `pending` → not started  
- `in_progress` → actively coding  
- `blocked` → note why in Progress log  
- `done` → DoD met  

---

## Progress log

| Date | Note |
|------|------|
| 2026-07-15 | Task file created. M0 hard deadline set to 2026-07-17 EOD. |

<!-- Add a line each session, e.g.:
| 2026-07-15 | Finished A1–A5, Postgres up. |
-->

---

## Sparring check-in prompts (paste when stuck)

```text
MILESTONE: M0
BLOCK: A|B|C|D
WHAT I DID:
WHAT FAILED:
WHAT I THINK NEXT:
```

---

## Sign-off

| Role | Name | M0 accepted when |
|------|------|------------------|
| Builder | You | All DoD checkboxes checked |
| Sparring partner | Co-founder agent | You demo: agent log shows orchestrator reachable |
