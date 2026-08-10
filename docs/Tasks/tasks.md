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
| **Progress** | **20 of 23 tasks done — DoD 7 of 7. M0 is complete.** |

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

- [x] Docker Postgres is running on Windows (Docker Desktop)
- [x] Orchestrator starts and `GET /health` returns success (browser, curl, or Invoke-WebRequest)
- [x] Orchestrator can talk to Postgres (`SELECT 1` or health reports `db: ok`)
- [x] Agent starts, reads orchestrator URL from env, hits `/health`, logs reachable
- [x] `.gitignore` excludes venv, `.env`, `__pycache__`, IDE junk
- [x] `.env.example` documents required vars (no real secrets committed)
- [x] `README.md` explains how to run DB, orchestrator, and agent on Windows

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
| A5 | Create folders: `orchestrator/`, `agent/` (and optional `docs/`) | done | [x] |

> **A5 closed 2026-08-10** when `agent/main.py` and `agent/requirements.txt`
> were committed. Until then `agent/` existed on disk but not in git — git does
> not track empty directories, so for anyone cloning the repo it did not exist
> at all. A directory only becomes real when it has a tracked file in it.

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
| C2 | App entrypoint that starts an HTTP server | done | [x] |
| C3 | Implement `GET /health` → JSON ok | done | [x] |
| C4 | Load `DATABASE_URL` from env; run `SELECT 1` | done | [x] |
| C5 | Extend health (or separate check) so DB failure is visible (503) | done | [x] |

**Block C complete 2026-08-10.** `orchestrator/main.py` — FastAPI app, `GET /health`
runs `SELECT 1` per request and reports real DB state. Acceptance test passed:

| Case | Result |
|---|---|
| DB up | `200 {"status":"ok","db":"ok","version":"0.1.0"}` in 0.37s |
| DB stopped | `503 {"status":"degraded","db":"down","version":"0.1.0"}` in 10.2s |
| Other route during outage | `/service` still `200` — threadpool not exhausted |
| DB restarted | `200` again **without restarting uvicorn** |

Two findings worth carrying into M1:

1. **`connect_timeout` is per resolved address, not a total budget.** Set to 5s,
   measured 10.2s: `localhost` resolves to both `::1` and `127.0.0.1` and libpq
   applies the timeout to each in turn. Worst case is
   `connect_timeout × address count`. Size timeouts against that, or connect to
   a literal IP.
2. **Without any timeout the endpoint hangs instead of failing.** Docker's port
   proxy accepts the TCP connection after the container stops but never answers,
   so libpq waited indefinitely and the `except` was unreachable. Since the route
   is sync `def`, FastAPI runs it in a threadpool — enough hung requests would
   exhaust it and take down healthy routes too. Every network call gets a timeout.

> **C1:** `orchestrator/requirements.txt` lists fastapi, uvicorn[standard],
> psycopg[binary], python-dotenv — **unpinned**. That is the whole of the Python
> backend today: four dependency names, no code. Pinning is E1.

**Read before C3:** PYTHON-FASTAPI-BACKEND-MIGRATION.md §7. The 422-vs-400
validation trap costs an hour if you meet it as a bug instead of a note.

---

### Block D — Agent ping

| ID | Task | Status | Done |
|----|------|--------|------|
| D1 | Create agent package + venv (or shared workspace venv — document choice) | done | [x] |
| D2 | Read `ORCHESTRATOR_URL` from env | done | [x] |
| D3 | HTTP GET `{ORCHESTRATOR_URL}/health` | done | [x] |
| D4 | Log clear success / failure (exit non-zero on failure is a plus) | done | [x] |
| D5 | Update README with exact Windows run steps for all three pieces | done | [x] |

**Block D complete 2026-08-10.** `agent/main.py` reads `ORCHESTRATOR_URL`, calls
`GET /health`, and distinguishes the three states a caller has to tell apart:

| What happened | What it means | Exit |
|---|---|---|
| `200` | Everything works | `0` |
| Response, status `503` | Orchestrator up, **its database is down** | `1` |
| `httpx.RequestError` | Orchestrator unreachable | `1` |

All three verified by inducing each failure — DB stopped, then uvicorn stopped.

**Choice recorded for D1: the agent gets its own venv** (`agent/env`), not a
shared one. `agent/requirements.txt` is `httpx` + `python-dotenv` and nothing
else. The dependency list is a security boundary, not just a build input: the
agent installs on a provider's own machine, and shipping `psycopg` there would
imply the agent can reach our database. It cannot, and it never should.

Three findings from Block D:

1. **A client timeout shorter than the server's worst case hides the error you
   built.** The agent's 5s timeout fired before the orchestrator's ~10s `503`
   arrived, so the `else` branch looked correct and had never once executed.
   Raised to 15s. Test the failure branch, or assume it doesn't work.
2. **`sys.exit(1)` gets forgotten on the path written last.** The `except`
   branch printed a failure and exited `0` — a monitor reporting green while
   the orchestrator was down. Exit codes are the only part a scheduler reads.
3. **Refused (`WinError 10061`) and silent (`ReadTimeout`) are different
   diagnoses.** Refused means the process is dead; silence means it is alive
   and stuck. Collapsing both into "error" throws away the useful half.

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
| E1 | Pin dependencies (`requirements.txt` or `pyproject.toml`) | done | [x] | R1 |
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
| 2026-08-10 | **M0 code complete — 14 days inside the 2026-08-24 timebox.** Blocks C and D finished: orchestrator `/health` reports real Postgres state, agent distinguishes three failure modes with exit codes, README rewritten for the Python stack. Awaiting @YogitaKanwar's clean-clone verification for sign-off. |
| 2026-08-10 | **`main` went red for ~2.5h.** PR #9, labelled a dev-dependency group bump, carried three majors including `tailwindcss` 3→4, whose PostCSS plugin moved packages. It was merged by hand while its own CI was already failing, which broke every open PR — `pull_request` checks build each branch merged with `main`. Fixed in #13 by reverting Tailwind only; v4 migration tracked in #14. Lesson: a red Dependabot PR is the cheapest bug report you will ever get. |
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
