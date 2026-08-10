# Team Execution Plan — Engineering Squad

**Date:** 2026-08-10
**Owner:** R1 (Architect) — [@RUSHAB3979](https://github.com/RUSHAB3979)
**Scope:** How five people ship this repo without colliding, starting from a codebase only one of them has ever committed to.

**Companions:** [ROLES.md](./ROLES.md) (role definitions) · [Tasks/tasks.md](./Tasks/tasks.md) (M0 checklist) · [PYTHON-FASTAPI-BACKEND-MIGRATION.md](./PYTHON-FASTAPI-BACKEND-MIGRATION.md) (contract parity) · [RISK-REGISTER.md](./RISK-REGISTER.md)

This document supersedes the solo-founder assumptions in `Tasks/tasks.md`
("Owner: You (solo, collaborators later)"). It does not replace the M0
checklist itself, which is still correct.

---

## 1. Baseline — measured, not estimated

| Surface | Size | State |
|---|---:|---|
| `web-client/src` | 41 files, 4,299 lines | Works. **100% mock data.** |
| `services/` (TypeScript) | 16 files, 1,001 lines | Works. **Frozen** — read-only contract reference. |
| `.github/` + compose | 4 files, 613 lines | CI: 11 jobs, all green. |
| `orchestrator/` (Python) | 1 file, **4 dependency names** | `requirements.txt`, unpinned. No code. |
| `agent/` (Python) | **0 files** | Does not exist. |

**Commits: 39. Authors: 1.** No collaborator has pushed to this repo.

Two facts follow, and the whole plan is built on them:

1. **The product that the roles describe does not exist yet.** The Python
   control plane is four unpinned dependency names. Everything else is either
   a frozen reference implementation or a frontend talking to fixtures.
2. **The team is at zero, not at speed.** Four people need to clone, install,
   and land a first commit before any estimate here means anything.

---

## 2. The central tension, stated honestly

`Tasks/tasks.md` Block E is titled **"Stretch polish (collaborator-ready)"** and
sits *after* M0. The original plan expected collaborators to arrive once the
control plane said hello. They arrived first.

So the real problem is not "how do we split M0." M0 is roughly six hours of work
and it is the founder's deliberate learning exercise. The real problem is:

> **How do four people stay productive for two weeks while one person finishes a
> solo exercise that everything else depends on?**

Section 6 is the answer. Every task there is independent of `orchestrator/` and
`agent/` by construction — not by agreement, by file path.

---

## 3. Assignments

| Owner | Roles | Primary surface |
|---|---|---|
| [@RUSHAB3979](https://github.com/RUSHAB3979) | **R1** Architect + **R5** Orchestrator *(M0 only)* | `orchestrator/`, `packages/contracts/`, all interface decisions |
| [@YogitaKanwar](https://github.com/YogitaKanwar) | **R3** DevOps + **R9** Database → **R5** after M0 | `.github/`, `docker-compose.yml`, schema + migrations |
| [@Shubh-tech-grow](https://github.com/Shubh-tech-grow) | **R2** Networking + **R6** Provider Agent | `agent/`, streaming/TURN, telemetry |
| [@ryujikentaro](https://github.com/ryujikentaro) | **R4** Security + **R10** SRE | Threat model, sandbox, CI security gates, runbooks |
| [@AdarshNarwankar](https://github.com/AdarshNarwankar) | **R8** Frontend + **R7** Payments *(when it starts)* | `web-client/` |

Roles are paired so nobody context-switches between unrelated domains: the agent
and the network live on the same machine; the database and the infrastructure
that runs it are one surface; security and reliability share their runbooks.

`.github/CODEOWNERS` mirrors this by path and is the machine-readable source of
truth. If this table and CODEOWNERS ever disagree, **CODEOWNERS wins** and this
table is the bug.

---

## 4. Clash rules

These exist so that "who is editing what" never needs a conversation.

1. **One primary owner per path.** Not two, not a squad. CODEOWNERS enforces
   the review request; this rule is what makes it meaningful.
2. **Read anything. Change only your surface** without review. Touching someone
   else's path is fine — via a PR they review, never a direct push.
3. **Interface changes need an issue first.** HTTP shapes, Pydantic models,
   `packages/contracts/` — these are decisions, not implementations. R1 decides.
   This is the one surface where two people genuinely will collide.
4. **`services/` is frozen.** It is the reference implementation the Python port
   is checked against. Do not fix, refactor, or improve it. Read it.
5. **Branch names carry the surface:** `be/…`, `fe/…`, `agent/…`, `infra/…`,
   `sec/…`. A glance at the branch list should show who is where.
6. **Small PRs, merged fast.** A branch open longer than a week is a merge
   conflict with a delay timer on it.
7. **Never force-push `main`.** Enforced at GitHub level since 2026-08-10. If a
   push is rejected as non-fast-forward, the answer is always pull/rebase.
8. **Throwaway code goes in `docs/spikes/` or a scratch branch** — never into a
   directory someone else owns. Specifically: no spike code in `agent/` while
   M0 is open.

---

## 5. Do this before anyone clones

Two things get more expensive with every clone. Both are cheap today.

### 5a. Pin the Python dependencies · owner: R1 · ~10 minutes

`orchestrator/requirements.txt` lists `fastapi`, `uvicorn[standard]`,
`psycopg[binary]`, `python-dotenv` with **no versions**. Four people are about to
install these on four machines and resolve four different trees, and the first
"works on mine" bug will cost more than pinning does. Task **E1** in
`Tasks/tasks.md` — it is no longer optional polish.

### 5b. Purge the credential from git history · owner: R4

**A real credential is present in this repository's git history.** It is a
`POSTGRES_PASSWORD` in an early commit, not the placeholder. The repo is
private, so it is not publicly exposed, and gitleaks does **not** flag it — the
default ruleset does not match a low-entropy human-chosen password. Failing the
scanner closed did not make the history clean.

Purging it requires rewriting history and force-pushing `main`.

> **The cost of this task multiplies by the number of people who have cloned.**
> Today that number is one. Every collaborator who clones before the purge will
> have to delete their clone and start again, and any branch they push in the
> meantime carries the old history back in.

**This is the single highest-leverage task in the plan, and it gets cheaper the
sooner it happens.**

Sequence:

1. Rotate the password at the source. The purge is pointless if the credential
   still works.
2. Temporarily lift force-push protection on `main`.
3. `git filter-repo` to strip the blob. Verify it is unreachable.
4. Force-push. Re-enable protection immediately.
5. Founder re-clones. *Then* the other four clone for the first time.

If this cannot happen this week, **collaborators should still clone** — do not
block onboarding on it. Just accept that the purge gets more expensive and
schedule it deliberately.

---

## 6. Track 0 — everyone's first PR

Before feature work. The goal is to prove the machine works end to end, not to
produce anything valuable.

| Owner | First PR | Proves |
|---|---|---|
| All | Add yourself to a `CONTRIBUTORS.md` line | Clone → branch → PR → CI → merge works |
| @YogitaKanwar | `docker compose up -d` on a clean machine; fix or document whatever breaks | The DB story is reproducible off the founder's laptop |
| @AdarshNarwankar | `npm ci && npm run build` in `web-client/` | The frontend builds for someone else |
| @Shubh-tech-grow | Run the provider agent against the frozen TS orchestrator | The heartbeat path is understood before rewriting it |
| @ryujikentaro | Read the CI security job; open an issue per gap found | The gates are understood by their owner |

**Nobody writes a feature until their first PR is merged.** A team where four
people have never run CI is not a team yet.

---

## 7. Milestones

### M0 — Control-plane hello world · owner: @RUSHAB3979

Definition of done is unchanged — see `Tasks/tasks.md`. Postgres up →
`GET /health` reporting real DB state → agent pings it → README explains how.

**Timebox: 2026-08-24.** M0 is a learning exercise and the founder is also
preparing for placements. Both are true, and they compete.

> **Decision point 2026-08-24:** if M0 is not done, `orchestrator/` transfers to
> @YogitaKanwar and the founder keeps R1 only. This is not a punishment; it is
> the price of keeping four people unblocked. Decide it on the date, not by
> drifting past it — drifting is what produced a deadline 24 days expired.

**In parallel, nobody touching `orchestrator/` or `agent/`:**

| Owner | Work | Independent because |
|---|---|---|
| @ryujikentaro | Credential purge (§5); threat model for **T-01** and **T-04**, the two risks the register calls platform-killing | Touches git history and `docs/`, not code |
| @YogitaKanwar | Reproducible `docker compose up`; design the `ProviderNode` schema for M1 — **DDL in a doc, no migration yet** | Schema design is not schema application |
| @AdarshNarwankar | Fix `checkOrchestratorHealth` (§8); build the health indicator behind a feature flag | Entirely inside `web-client/` |
| @Shubh-tech-grow | NVML telemetry spike — a standalone script that reads GPU stats; written transport decision (WebRTC vs alternatives) with TURN cost estimate | Runs on a GPU box with no orchestrator; **lives in `docs/spikes/`, not `agent/`** |

### M1 — Register + heartbeat · first genuinely parallel milestone

| Owner | Work |
|---|---|
| @RUSHAB3979 (R1) | Pydantic models for heartbeat + capability + metrics. **Ships first — everything else depends on it.** |
| @YogitaKanwar | `ProviderNode` table + migration; takes over `orchestrator/` if the §7 decision point fired |
| @RUSHAB3979 / @YogitaKanwar | `POST /v1/providers/heartbeat`, TTL → stale → offline |
| @Shubh-tech-grow | Agent heartbeat loop against the real endpoint |
| @AdarshNarwankar | Wire the provider list to real data; delete the corresponding mock |
| @ryujikentaro | Review: the heartbeat endpoint is unauthenticated. Decide whether that is acceptable for M1 and write down why |

### M2 — Matching + job submission

Port `POST /v1/match/gaming`, `/v1/match/compute`, `POST /v1/jobs` (**202**),
`GET /v1/jobs/:id` to Python at full contract parity, then decommission the
TypeScript core. Parity rules and the Pydantic traps are in
`PYTHON-FASTAPI-BACKEND-MIGRATION.md` §6–7 — read §7 before writing a route, not
after debugging one.

---

## 8. Dependency map

```
                    ┌─────────────────────────────┐
   BLOCKS EVERYTHING│ M0: /health + DB (@RUSHAB)  │
                    └──────────────┬──────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                    ▼
     Agent heartbeat      Frontend real wiring    M1 persistence
     (@Shubh)             (@Adarsh)               (@Yogita)
              │                    │                    │
              └────────────────────┴────────────────────┘
                                   ▼
                          M1 → M2 → cutover

   INDEPENDENT OF M0 (start today):
     credential purge · threat model · schema design (doc)
     NVML spike · transport decision · frontend health-shape fix
```

**The known blocker.** `web-client/src/services/api.js` falls back to
`{status, db, version}`, which is the *planned Python* contract. The frozen
TypeScript `/health` returns `{ok, providers, jobs}`. These do not match, and
`checkOrchestratorHealth` is currently **never called anywhere** — it is dead
code. So the frontend cannot wire to the existing backend at all; it is waiting
on M0 by design. Adarsh should target the Python shape and leave it behind a
flag until M0 lands.

---

## 9. Founder availability

The founder is preparing for college placements. That has a fixed external
deadline and one attempt per cycle; this repository does not. **DSA wins, and
the plan must survive the founder going dark for two to three weeks.**

- **Deputy: @YogitaKanwar.** During an absence she holds backend decisions.
- **R1 decisions queue as issues** labelled `needs-r1`. They do not block —
  the owner records the decision they would make, proceeds, and it is reviewed
  on return. A wrong call caught in review costs less than a three-week stall.
- **No task may have the founder as a hard dependency for more than one step.**
  M0 currently violates this. §7's decision point is the release valve.

---

## 10. Decision rights

| Decision | Who |
|---|---|
| HTTP contracts, schemas, state transitions | R1 (deputy: @YogitaKanwar) |
| Anything inside one surface | That surface's owner, alone |
| Security-relevant change to any surface | Owner proposes, **R4 reviews** |
| Dependency additions | Surface owner; R4 reviews new runtime deps |
| Scope — what is in a milestone | R1, and only at a milestone boundary |

Merges are **not** blocked on review. CODEOWNERS requests it; nothing enforces
it. That is deliberate — the team is small and the cost of a blocked merge is
higher than the cost of a missed review. Revisit if that stops being true.

---

## 11. Risks to this plan

| # | Risk | Why it is real here | Mitigation |
|---|---|---|---|
| P-1 | Everyone is a student; exams hit all five at once | Not a staggered team — correlated absence | Milestones gated on completion, never on dates. One deputy named. |
| P-2 | M0 stalls, two people stay blocked | Founder split between placements and code | Hard decision point 2026-08-24 (§7) |
| P-3 | Planning substitutes for building | **Seven plan documents, zero backend lines.** This is the eighth. | This doc is operational only: names, paths, first PRs. If it grows a roadmap, delete that section. |
| P-4 | Credential purge after cloning | Cost scales with clones | §5 — do it before onboarding |
| P-5 | New contributor edits `services/` thinking it is live | Two backends in one repo, one frozen | §4 rule 4; frozen state stated in README |
| P-6 | R4 alone owns both platform-killing risks | Single point of failure on T-01/T-04 | Second security reviewer before launch |
| P-7 | Four owners, one has ever run the build | Onboarding untested | §6 Track 0 gates all feature work |
| P-8 | Frontend drifts further onto fixtures | 4,299 lines of mock-shaped assumptions | Wire one real endpoint at M1; delete its mock in the same PR |

---

## 12. Cadence

- **Weekly written check-in.** Three lines per person: shipped / blocked /
  next. Written, not a meeting — five students cannot reliably share a slot.
- **Issues carry the work.** If it is not an issue, it is not assigned.
- **Milestone review at each boundary**, not on a calendar.
- **This document is reviewed at every milestone boundary.** Stale plans are how
  `tasks.md` ended up with a deadline 24 days past and 0/23 tasks that were
  actually 6/23 done.

---

## 13. Definition of done

**A milestone is done when:**

- Every DoD checkbox in `Tasks/tasks.md` is ticked *and verified by someone
  other than the author*.
- CI is green on `main`, including the Python job.
- The README explains how a new person runs it on a clean Windows machine.
- Every mock replaced by real data has had its fixture **deleted**, not
  commented out.
- The next milestone's owners are named before the current one closes.

**A PR is done when:** CI green, one review from the surface owner (or R1 if it
crosses surfaces), no new `TODO` without an issue number, and the branch is
deleted on merge.
