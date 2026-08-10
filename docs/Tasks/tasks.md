# Task Tracker — P2P Cloud Gaming Marketplace

**M0 owner:** [@RUSHAB3979](https://github.com/RUSHAB3979) (solo — see note below)
**Team:** four collaborators onboard since 2026-08-10 — [TEAM-EXECUTION-PLAN.md](../TEAM-EXECUTION-PLAN.md)
**Stack (now):** Python (FastAPI) · Windows · Postgres via Docker
**Cadence:** ~2–3 hours/day, placement prep permitting

**Related:** [TEAM-EXECUTION-PLAN.md](../TEAM-EXECUTION-PLAN.md) · [ROLES.md](../ROLES.md) · [PYTHON-FASTAPI-BACKEND-MIGRATION.md](../PYTHON-FASTAPI-BACKEND-MIGRATION.md)

> **M0 stays a solo build.** It is a deliberate learning exercise: the founder
> writes every line of `orchestrator/` and `agent/`. The other four are not
> idle — their parallel, non-blocking work is in TEAM-EXECUTION-PLAN.md §7, and
> none of it touches these two directories.

---

## Current focus

| Field | Value |
|--------|--------|
| **Milestone** | M0 — Control-plane hello world |
| **Phase** | Phase 0 (Foundations) → edge of Phase 1 |
| **Started** | 2026-07-15 |
| **Timebox** | **2026-08-24** — decision point, not a hard deadline |
| **Progress** | 6 of 23 tasks verified done |

**What the timebox means.** On 2026-08-24, if M0 is not done, `orchestrator/`
transfers to [@YogitaKanwar](https://github.com/YogitaKanwar) and the founder
keeps R1 only. Decide it *on the date*. The original deadlines (2026-07-15/16/17
/21) were left to drift for 24 days while the tracker still read `pending` for
work that was finished — that failure mode is what the timebox exists to stop.

---

## Milestone M0 — Control-plane hello world

### Goal (one sentence)

Postgres up → orchestrator `GET /health` OK → agent pings orchestrator and logs success.

### Why this first

Without a node that can reach the orchestrator, catalog/streaming/matching are fiction.
Three of the four collaborators are blocked behind this endpoint.

### Definition of done (DoD)

- [ ] Docker Postgres is running on Windows (Docker Desktop)
- [ ] Orchestrator starts and `GET /health` returns success (browser, curl, or Invoke-WebRequest)
- [ ] Orchestrator can talk to Postgres (`SELECT 1` or health reports `db: ok`)
- [ ] Agent starts, reads orchestrator URL from env, hits `/health`, logs reachable
- [x] `.gitignore` excludes venv, `.env`, `__pycache__`, IDE junk
- [x] `.env.example` documents required vars (no real secrets committed)
- [ ] `README.md` explains how to run DB, orchestrator, and agent on Windows

**Out of scope for M0:** auth, register/heartbeat tables, catalog, WebRTC, C++, payments.

**Contract note:** `/health` must return `{status, db, version}`. The frozen
TypeScript service returns `{ok, providers, jobs}` — do not copy it. The frontend
already codes against the Python shape.

---

## Task breakdown

Status: `pending` · `in_progress` · `blocked` · `done` · `confirm` (believed done,
not verifiable from the repo — tick it after checking on the machine).

### Block A — Repo hygiene · **done**

| ID | Task | Status | Done |
|----|------|--------|------|
| A1 | `git init` (if not already) | done | [x] |
| A2 | Add `.gitignore` (Python, venv, `.env`, Windows/IDE) | done | [x] |
| A3 | Add `.env.example` (`DATABASE_URL`, `ORCHESTRATOR_URL` placeholders) | done | [x] |
| A4 | Add root `README.md` (what / how to run — can be stub first) | done | [x] |
| A5 | Create folders: `orchestrator/`, `agent/` (and optional `docs/`) | in_progress | [ ] |

> **A5:** `orchestrator/` is tracked (`requirements.txt`). `agent/` exists on disk
> but is empty, and git does not track empty directories — so it does not exist
> for anyone who clones. It closes when D1 puts a file in it.

---

### Block B — Postgres

| ID | Task | Status | Done |
|----|------|--------|------|
| B1 | Install/verify Docker Desktop on Windows | done | [x] |
| B2 | Add `docker-compose.yml` with Postgres only | done | [x] |
| B3 | `docker compose up -d db` and confirm container healthy | done | [x] |
| B4 | Confirm you can connect (any client or one-shot command) | done | [x] |

> Verified 2026-08-10: Docker engine 28.4.0, `marketplace_db` healthy,
> `SELECT 1` succeeded against PostgreSQL 16.14 over psycopg 3.3.4.
>
> **Use `docker compose up -d db`, not bare `docker compose up -d`.** The compose
> file still describes the frozen TypeScript stack: its `orchestrator` service is
> `image: node:20` running `npm run dev:orchestrator` on port 8080. Bring the whole
> file up and a Node process occupies the port your Python app wants, and the bind
> error will not mention Docker. Rewriting compose for the Python stack is
> [@YogitaKanwar](https://github.com/YogitaKanwar)'s (R3) task.
>
> **`DATABASE_URL` needs a percent-encoded password.** An unencoded `@` in the
> password made libpq read the host as `123@localhost` and report
> `failed to resolve host` — an error that points at DNS and is really string
> escaping. `.env.example` now documents this. B3 is also @YogitaKanwar's Track 0
> task; her clean-machine run is a stronger test than this one.

---

### Block C — Orchestrator health

| ID | Task | Status | Done |
|----|------|--------|------|
| C1 | Create orchestrator package + venv + dependencies (FastAPI) | done | [x] |
| C2 | App entrypoint that starts an HTTP server | pending | [ ] |
| C3 | Implement `GET /health` → JSON ok | pending | [ ] |
| C4 | Load `DATABASE_URL` from env; run `SELECT 1` | pending | [ ] |
| C5 | Extend health (or separate check) so DB failure is visible (503) | pending | [ ] |

> **C1:** `orchestrator/requirements.txt` lists fastapi, uvicorn[standard],
> psycopg[binary], python-dotenv — **unpinned**. That is the whole of the Python
> backend today: four dependency names, no code. Pinning is E1.

**Read before C3:** PYTHON-FASTAPI-BACKEND-MIGRATION.md §7. The 422-vs-400
validation trap costs an hour if you meet it as a bug instead of a note.

---

### Block D — Agent ping

| ID | Task | Status | Done |
|----|------|--------|------|
| D1 | Create agent package + venv (or shared workspace venv — document choice) | pending | [ ] |
| D2 | Read `ORCHESTRATOR_URL` from env | pending | [ ] |
| D3 | HTTP GET `{ORCHESTRATOR_URL}/health` | pending | [ ] |
| D4 | Log clear success / failure (exit non-zero on failure is a plus) | pending | [ ] |
| D5 | Update README with exact Windows run steps for all three pieces | pending | [ ] |

> Block D is the hand-off point. Once `agent/` has a file in it, the directory
> belongs to [@Shubh-tech-grow](https://github.com/Shubh-tech-grow) (R6) and the
> M1 heartbeat loop is his. Until then he stays out of it — his spike work lives
> in `docs/spikes/`.

---

### Block E — Polish

Originally titled "collaborator-ready" and scheduled after M0. The collaborators
arrived first, so the title is retired; the tasks are still worth doing.

| ID | Task | Status | Done | Owner |
|----|------|--------|------|-------|
| E1 | Pin dependencies (`requirements.txt` or `pyproject.toml`) | pending | [ ] | R1 |
| E2 | Short ADR: hybrid architecture, Python now / C++ later | pending | [ ] | R1 |
| E3 | Short ADR: BYOL + allowlist legal model | pending | [ ] | R4 |
| E4 | Domain notes: list entities User / ProviderNode / Session | pending | [ ] | R9 |

> **E1 is no longer optional polish.** Four people are about to install these
> dependencies on four machines. Unpinned means four different resolved trees and
> a "works on mine" bug nobody can reproduce. Do it before they clone.
> **E4** folds into @YogitaKanwar's M1 schema design (TEAM-EXECUTION-PLAN.md §7).

---

## After M0 (do not start early)

**M1 — Register + heartbeat.** First genuinely parallel milestone; per-person
split in TEAM-EXECUTION-PLAN.md §7.

1. `ProviderNode` table + migration — R9
2. Pydantic models for heartbeat/capability/metrics — R1, **ships first**
3. `POST /providers/register` · `POST /providers/heartbeat` — R5
4. Agent loop every N seconds — R6
5. Stale → offline (TTL) — R5
6. Frontend wires the provider list to real data, deletes the mock — R8
7. Security review: the heartbeat endpoint is unauthenticated — R4 decides
   whether that is acceptable for M1 and writes down why

---

## Progress log

| Date | Note |
|------|------|
| 2026-07-15 | Task file created. M0 hard deadline set to 2026-07-17 EOD. |
| 2026-08-10 | **Tracker was stale by 24 days** — all 23 tasks read `pending` while A1–A4 and B2 were done. Audited against the repo, statuses corrected, expired deadlines replaced with a 2026-08-24 timebox. Four collaborators onboarded; roles assigned in ROLES.md, paths in CODEOWNERS, execution in TEAM-EXECUTION-PLAN.md. |

<!-- Add a line each session. -->

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
| Builder | @RUSHAB3979 | All DoD checkboxes checked |
| Verifier | @YogitaKanwar | She runs it from a clean clone and it works — not the author's machine |
| Sparring partner | Co-founder agent | Agent log shows orchestrator reachable |
