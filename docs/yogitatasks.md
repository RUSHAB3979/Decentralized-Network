# Task List — @YogitaKanwar

**Roles:** R3 DevOps + R9 Database → picks up R5 (orchestrator endpoints) after M0
**Owns:** `.github/`, `docker-compose.yml`, `.ruff.toml`, schema + migrations
**Also:** deputy for backend decisions during the founder's absences
**Related:** [TEAM-EXECUTION-PLAN.md](TEAM-EXECUTION-PLAN.md) · [ROLES.md](ROLES.md) · [Tasks/tasks.md](Tasks/tasks.md)

Status values: `pending` · `in_progress` · `blocked` · `done`

---

## Current priority

**Y1 — verify M0 from a clean clone.** M0 code is complete as of 2026-08-10 and
cannot be signed off until this passes. Four people are waiting behind it.

---

## Y0 — Track 0: first PR · `pending`

Add yourself a line in `CONTRIBUTORS.md` and open a PR. The file does not
exist yet — creating it with your line in it is the task.

The change is trivial on purpose. It proves clone → branch → PR → CI → merge
works for you before anything important depends on it. **Nobody writes a
feature until their first PR is merged** — a team where people have never run
CI is not a team yet.

- [ ] PR opened, CI green, merged

---

## Y1 — Verify M0 from a clean clone · `pending` · **blocking**

You are the verifier on M0's sign-off. Read this section carefully, because
the thing being tested is not what most people assume.

### What you are actually testing

**You are testing the README, not the code.** The code demonstrably works —
on the founder's laptop. That laptop has a year of accumulated configuration
in it: a uv-managed Python, a hand-written `.env`, Docker already set up,
virtualenvs built in steps he's half-forgotten. Every one of those is
invisible to him and mandatory for you.

A clean clone is the only instrument that finds them.

### Steps

1. **Clone fresh** into a new folder.

   Not `git pull` on an existing copy. A stale `node_modules`, an old `.env`,
   an existing venv — each one hides exactly the failure this exercise exists
   to catch.

2. **Open `README.md` and follow the Windows quick start literally**, top to
   bottom. Type the commands as written. Do not substitute a command you know
   works. If the README says `py -3.11 -V`, run that, even if you would
   normally reach for something else.

3. **Confirm the three DoD claims:**

   | Check | Expected |
   |---|---|
   | `docker ps --filter name=marketplace_db` | `Up ... (healthy)` |
   | `Invoke-RestMethod http://localhost:8080/health` | `{"status":"ok","db":"ok","version":"0.1.0"}` |
   | `.\agent\env\Scripts\python.exe agent\main.py` | `Orchestrator Healthy`, `$LASTEXITCODE` = `0` |

4. **Run the failure cases too.** This is the part that gets skipped, and it
   is the part that matters — a health check that cannot fail correctly is not
   a health check.

   | Do this | Expected output | `$LASTEXITCODE` |
   |---|---|---|
   | `docker stop marketplace_db`, run the agent | `Orchestrator Reachable but Unhealthy 503` | `1` |
   | Stop uvicorn (Ctrl+C), run the agent | `Down [WinError 10061] ... actively refused it` | `1` |

   Then `docker start marketplace_db` and confirm `/health` returns `200`
   again **without restarting uvicorn**.

### The two rules that make this worth doing

**1. If you have to ask a question to get past a step, that step failed.**

Not "failed after you asked" — failed. Someone cloning this in six months
does not have the founder available. Every question you need to ask is a line
missing from the README, and it is only findable right now, by you.

**2. If you work out the fix yourself, report it — do not absorb it.**

If you discover that `uv venv` works where `py -3.11` doesn't, that is a
README bug. Fixing it silently in your own setup moves the knowledge out of
the file and into your head, and the file stays broken for the next person.

### How to report

**One GitHub issue per failure.** Include the **exact command you typed** and
the **exact output**, pasted, not paraphrased. The error text is the entire
diagnosis; a summary throws away the part that identifies the cause.

Title format: `M0 verify: <step> fails on clean clone`

- [ ] Clean clone completed
- [ ] Happy path verified (all three checks)
- [ ] Both failure paths verified with correct exit codes
- [ ] Every deviation from the README filed as an issue
- [ ] Re-run after fixes, no questions needed → **M0 signed off**

---

## Y2 — Make `docker compose up` reproducible · `pending`

Starts once Y1 signs off. This is your Track 0 task in the execution plan and
your first real piece of ownership.

**The problem today:** `docker-compose.yml` still describes the frozen
TypeScript stack. Its `orchestrator` service is `image: node:20` bound to port
**8080** — the same port the Python app uses. Anyone running bare
`docker compose up` gets a Node process squatting on the port, and a bind
error that never mentions Docker. The README currently works around this by
telling people to type `docker compose up -d db` and explaining why.

**A workaround in a README is a bug with documentation attached.** Fix the
file so the obvious command is the correct one.

Scope:

- [ ] `docker compose up` starts the Python stack, or starts only what is safe
- [ ] The frozen `services/` containers are removed or clearly quarantined
      (a profile, a separate file — your call, write down which and why)
- [ ] Port 8080 belongs to exactly one thing
- [ ] The README's "do not run bare `docker compose up`" warning can be deleted
- [ ] Verified on a clean machine, not the founder's

**Do not delete `services/` itself.** It is a read-only contract reference
until the Python side reaches parity — see
[PYTHON-FASTAPI-BACKEND-MIGRATION.md](PYTHON-FASTAPI-BACKEND-MIGRATION.md).

---

## Y3 — Design the `ProviderNode` schema · `pending`

For M1. **DDL in a document. No migration, no table, nothing applied.**

Schema design and schema application are different activities, and the second
one is much harder to undo. M0 has no tables at all and that is deliberate —
this work exists so M1 starts from a considered design rather than whatever
shape the first endpoint happened to need.

Deliver a doc (`docs/schema/provider-node.md`) containing:

- [ ] Column list with types and nullability
- [ ] Primary key, and how a provider is identified across restarts
- [ ] What "stale" means: which timestamp, which TTL, and who writes it
- [ ] Indexes the heartbeat and matching queries will actually need
- [ ] The state transitions — online → stale → offline — and what causes each
- [ ] Open questions, explicitly listed rather than quietly decided

Read `packages/contracts/` first. Those Zod schemas are the contract the
Python models must match; the table should not disagree with them.

**Coordinate with R1 before finalising.** The founder ships the Pydantic
models first in M1, and everything else depends on them — the table and the
models describing different shapes is the expensive version of this mistake.

---

## Y4 — `ProviderNode` table + migration · `blocked` (needs Y3 + M1 start)

The application half of Y3. Migration tooling choice is yours; write down
why in the same doc.

- [ ] Migration tool chosen and justified
- [ ] Migration applies cleanly to an empty database
- [ ] Migration is reversible, and the reverse is tested
- [ ] Runs in CI against a throwaway Postgres

---

## Y5 — CI ownership · `ongoing`

You own `.github/`, and `ci.yml` jointly with @ryujikentaro.

Standing responsibilities:

- [ ] Keep `PYTHON_VERSION` in `ci.yml` and `target-version` in `.ruff.toml`
      in lockstep — both are `3.11`. They drifted once already; a mismatch
      passes locally and fails in CI, or worse, the reverse.
- [ ] The `main` ruleset requires the check **"🟢 All checks passed"**. The
      Dependabot auto-merge workflow and `scripts/ship.ps1` are only safe
      because of it. **If that ruleset is ever removed, delete both in the
      same commit** — `gh pr merge --auto` with no required checks merges
      instantly, which is strictly worse than merging by hand.
- [ ] Treat a red Dependabot PR as a finding, not noise. On 2026-08-10, PR #9
      was labelled a dev-dependency group bump, carried three majors including
      `tailwindcss` 3→4, was already failing its own CI, and was merged by
      hand. `main` was red for two and a half hours and every open PR failed
      with it, because `pull_request` checks build each branch merged with
      `main`.

---



## Notes

Add a dated line when something changes.

| Date | Note |
|------|------|
| 2026-08-10 | File created. M0 code complete; Y1 is the blocking item. |
