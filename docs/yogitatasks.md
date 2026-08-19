# Task List — @YogitaKanwar

**Roles:** R3 DevOps + R9 Database → picks up R5 (orchestrator endpoints) after M0
**Owns:** `.github/`, `docker-compose.yml`, `.ruff.toml`, schema + migrations
**Also:** deputy for backend decisions during the founder's absences
**Related:** [TEAM-EXECUTION-PLAN.md](TEAM-EXECUTION-PLAN.md) · [ROLES.md](ROLES.md) · [Tasks/tasks.md](Tasks/tasks.md)

Status values: `pending` · `in_progress` · `blocked` · `done`

---

## Current priority

**Y0 and Y1 are done.** Y0 merged in [#47](https://github.com/RUSHAB3979/Decentralized-Network/pull/47);
Y1 signed M0/M1 off from a genuine clean clone in
[#50](https://github.com/RUSHAB3979/Decentralized-Network/pull/50), including both
failure paths, the self-heal, and two README defects filed as
[#48](https://github.com/RUSHAB3979/Decentralized-Network/issues/48) and
[#49](https://github.com/RUSHAB3979/Decentralized-Network/issues/49) rather than
fixed silently. That is the standard for the rest of this file. Nothing gates you
now.

**Y6 — the provider account, console, and agent enrolment.** Assigned 2026-08-16;
see [ADR 0005](adr/0005-provider-accounts-and-agent-enrolment.md). This is still
the main body of your work and it is where to go next.

**Y12 and Y13 were added 2026-08-18** for the rendering vertical
([ADR 0006](adr/0006-render-batch-jobs.md)). They are schema and infrastructure,
which is your surface, but they sit *behind* Y6–Y11 in priority — do not start
them while the provider console is unbuilt. The one exception is Y13's first
checkbox: verifying whether Cloudflare R2's free tier needs a card on file is ten
minutes of work and the answer changes what other people build, so it is worth
doing out of order.

Y2–Y5 remain open and unchanged.

---

## Y0 — Track 0: first PR · `done` — merged 2026-08-17 ([#47](https://github.com/RUSHAB3979/Decentralized-Network/pull/47))

Add yourself a line in `CONTRIBUTORS.md` and open a PR. The file does not
exist yet — creating it with your line in it is the task.

The change is trivial on purpose. It proves clone → branch → PR → CI → merge
works for you before anything important depends on it. **Nobody writes a
feature until their first PR is merged** — a team where people have never run
CI is not a team yet.

- [x] PR opened, CI green, merged

---

## Y1 — Verify M0 from a clean clone · `done` — signed off 2026-08-16 ([#50](https://github.com/RUSHAB3979/Decentralized-Network/pull/50))

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

- [x] Clean clone completed
- [x] Happy path verified (all three checks)
- [x] Both failure paths verified with correct exit codes
- [x] Every deviation from the README filed as an issue — [#48](https://github.com/RUSHAB3979/Decentralized-Network/issues/48), [#49](https://github.com/RUSHAB3979/Decentralized-Network/issues/49)
- [x] Re-run after fixes, no questions needed → **M0 signed off**

**Two items remain open and are not defects in this work.** The verifying machine
has no NVIDIA GPU, so a real GPU-served completion and the true `404`-unknown-model
path are still unverified; and the Nodes tab was confirmed at the API level rather
than visually. Both need hardware, not another pass. Recorded in
`docs/Tasks/tasks.md` rather than left implied.

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

# Provider accounts, console, and agent enrolment (Y6–Y11)

Assigned 2026-08-16. The decisions these tasks implement are recorded in
[ADR 0005](adr/0005-provider-accounts-and-agent-enrolment.md) — read it first,
because it explains *why* each of the choices below was made and what the cost of
each one is. This section is the work; the ADR is the reasoning.

## What you are building, in one paragraph

A provider signs up and logs in at a login page of their own, separate from the
customer one. They land in a provider console. There they generate an **enrolment
key**, paste it into the GPUProvider desktop app, and from that moment the machine
belongs to their account — their nodes, their telemetry, their job history, and
eventually their earnings all appear in the console under their name.

## Why this is worth doing properly

Right now `POST /providers/register` accepts any caller and hands back a working
credential (`orchestrator/main.py:180`, token returned at `:247`). Anyone who can
reach the orchestrator and guess a `node_id` is issued a token for it. That is
"trust on first registration", and `agent/core/creds.py` looked at that exact
design and rejected it: *"a node_id is derivable from a machine the attacker does
not have to own, and the first caller wins. Only acceptable if registration is
itself gated."*

We shipped it anyway, and then put the orchestrator on the public internet, which
[ADR 0004](adr/0004-m1-unauthenticated-heartbeat.md) explicitly said must not
happen while it stood. **Y8 is what closes that.** The console is the visible half
of this work; the gate is the point of it.

## Seven rules for all of Y6–Y11

These are not style preferences. Each one is a failure that produces no error
message, which is the only kind this repository is really afraid of.

1. **Reuse `orchestrator/auth.py`. Do not write a second password hasher.**
   It already has `hash_password`, `verify_password`, `normalise_email`,
   `issue_session_token`, `hash_token`, `session_expiry` and `session_is_valid`,
   and its docstring explains why passwords use scrypt while machine tokens use
   SHA-256. A separate account *table* is what was decided. A separate hasher was
   not, and it is the single most likely way this work goes wrong.
2. **Derive expiry; never sweep it.** Key TTL, session validity and node liveness
   are all computed at read time from the row's own columns. The reason is in
   `orchestrator/liveness.py` and repeated in `auth.py`: a background sweeper that
   dies leaves every expired thing valid forever, and nothing raises.
3. **Store digests, never secrets.** Enrolment keys and node tokens are returned
   in plaintext exactly once and stored hashed. A leaked database backup must not
   be a set of working credentials.
4. **Bind the credential to the node it claims to be.** If a token is verified but
   never checked against the `node_id` in the request body, any enrolled node can
   act as any other and the check has bought nothing. (`creds.py`, question 2.)
5. **A database restore must not brick the fleet.** A machine holding a valid
   credential but with no row in the registry has to be able to re-register. That
   self-heals today through the 404 path in `agent/reporter.py`. If gating
   registration closes it, one restore-from-backup silently disables every
   provider at once, and they will not all reinstall. (`creds.py`, question 3.)
6. **Never fall back to unauthenticated.** If the credential cannot be read, the
   node goes to ERROR and says so. Retrying without it is a downgrade attack
   wearing the costume of a convenience. (`creds.py`, question 4.)
7. **Every network call gets an explicit timeout.** No exceptions; see
   `CLAUDE.md`.

---

## Y6 — Design the provider account and enrolment schema · `pending`

**DDL in a document. No migration, no table, nothing applied.**

That instruction is deliberately identical to Y3's, because Y3 is what happened
when it was ignored. The provider node schema was never designed in a document —
it went straight into `orchestrator/schema.sql` in PR #38, was edited twice more
in #42 and #43, and now runs on the production database with no design record and
no migration path. Schema design and schema application are different activities
and the second one is much harder to undo.

Deliver `docs/schema/provider-accounts.md`:

- [ ] `provider_accounts` — columns, types, nullability, indexes
- [ ] `provider_sessions` — same, and say which column expiry is derived from
- [ ] `provider_enrolment_keys` — same, plus the lifecycle: TTL, single-use or
      reusable, how revocation works, and what is stored (digest only)
- [ ] `provider_nodes.provider_account_id` — **nullable**, mirroring how
      `marketplace_api_keys.user_id` was added when accounts arrived
- [ ] **What happens to the nodes already in the table.** They have no owner and
      they are live. Say how one gets claimed, or say explicitly that it cannot
      and they must re-enrol.
- [ ] **What happens when the same machine enrols twice.** Reinstalling Windows
      regenerates MachineGuid and therefore the `node_id`; restoring a disk image
      does not. Both happen. (`creds.py`, question 1.)
- [ ] Open questions listed explicitly rather than quietly decided

Read `orchestrator/schema.sql` first, particularly the comment block at line 151
about the migration ceiling. Your three new tables are reachable with
`CREATE TABLE IF NOT EXISTS`; note in the doc whether you think that is still true
after this change.

---

## Y7 — Provider auth backend · `pending`

The tables from Y6, plus `/v1/provider/auth/signup`, `/login`, `/logout`, `/me`,
and a `_authenticate_provider_session` helper.

`orchestrator/main.py:741` is the customer version of that helper. Read it
completely before writing yours — including the comment explaining why "no such
token", "expired" and "revoked" all return the same message. That is not
laziness; distinguishing them tells an attacker holding a stale token that it was
once real.

- [ ] Tables applied idempotently, matching the Y6 document
- [ ] Signup, login, logout, me — all four, with session tokens stored hashed
- [ ] **Zero new cryptography.** Every hash and token in this task comes from
      `orchestrator/auth.py` unchanged. If you find yourself importing `hashlib`,
      stop and re-read rule 1.
- [ ] A provider session token is rejected by the customer endpoints, and vice
      versa. Test this — two separate systems that happen to accept each other's
      tokens are one system with extra steps.
- [ ] Tests for both the success and the failure path of each endpoint

---

## Y8 — Enrolment keys, and gating registration · `pending`

**This is the task that retires ADR 0004.** Everything else in this section is
surface; this is the part that changes what an attacker can do.

- [ ] `POST /v1/provider/enrolment-keys` — mint. Plaintext returned **exactly
      once**; only the digest is stored. `create_api_key` (`main.py:425`) is the
      pattern to follow.
- [ ] `GET /v1/provider/enrolment-keys` — list by prefix and creation time. Never
      returns a usable key.
- [ ] `DELETE /v1/provider/enrolment-keys/{id}` — revoke
- [ ] `POST /providers/enrol` — the agent presents an enrolment key and receives a
      node credential; the node row is bound to the account that minted the key
- [ ] `/providers/register` no longer mints a credential for an unenrolled node
- [ ] **Rule 5 verified, not assumed.** Write the test where a node holds a valid
      credential and its row has been deleted, and prove it recovers.
- [ ] **Rule 4 verified.** Write the test where a credential issued for node A is
      presented alongside a body claiming node B, and prove it is rejected.
- [ ] ADR 0004 marked superseded, with the PR number that did it

Rate limiting on the provider endpoints is **not** part of this task, and is still
missing. ADR 0004 called it "the obvious next mitigation". Raise it as its own
issue rather than folding it in here.

---

## Y9 — Provider login and console · `pending`

`web-client/src/components/app/ProviderConsolePage.jsx` already exists and is
worth reading before you replace anything — it renders live node telemetry today
via `hooks/useProviderNodes.js` and `components/NodeTelemetry.jsx`, and both of
those should be reused rather than rewritten.

What it does not have is an account. It sits behind the *customer* login, so
today every customer sees every provider's hardware.

`GET /providers/nodes` now requires a session (PR #45, 2026-08-16) — it used to
be served to anyone at all. `fetchProviderNodes` takes the token as a parameter
rather than reading it itself, because `authApi.js` imports `ORCHESTRATOR_URL`
from `api.js` at module scope and importing back would be a cycle that throws at
page load. Keep that shape when you build the provider version: **if you rebuild
this page and drop the `Authorization` header, every panel goes blank with a 401
and it will look like your new code is broken rather than unauthenticated.**

- [ ] Routes `/provider/login`, `/provider/signup`, `/provider` in
      `web-client/src/App.jsx`
- [ ] `services/providerAuthApi.js` and `hooks/useProviderSession.js`, mirroring
      `services/authApi.js` and `hooks/useSession.js`
- [ ] **A different `localStorage` key** from `nodeforge.session`. Reusing it
      means signing into one console silently signs you into the other, which is
      the entire separation gone with no error to notice.
- [ ] The three-state session machine — `loading` / `anonymous` / `error` — copied
      in behaviour, not just in shape. `useSession.js` explains at length why a
      failed request must not be treated as signed-out.
- [ ] Console scoped to the signed-in account: its nodes only
- [ ] Tabs: Overview, Nodes, **Enrolment** (new), **Jobs** (new), Earnings
- [ ] Enrolment tab generates a key, shows it once, and says plainly that it will
      not be shown again
- [ ] `npm run build` clean, and the flow exercised in a real browser

---

## Y10 — The desktop app: paste the key · `pending` · **partly blocked**

A screen in the GPUProvider app that accepts an enrolment key, calls
`POST /providers/enrol`, and stores what comes back.

**You own everything except the storing.** `agent/core/creds.py` — DPAPI storage,
rotation, cache invalidation, refusing to downgrade — is hand-built under
[ADR 0002](adr/0002-generated-vs-handbuilt.md) and is Rushab's to write. The seam
is a function call: you call `creds.store()`, you do not implement it.

- [ ] An "not enrolled yet" state in `agent/state.py`, surfaced in the window the
      same way `Link` is
- [ ] A screen that accepts a key, with distinct messages for rejected, expired,
      already-used, and orchestrator-unreachable
- [ ] The key is never written to a log line, a traceback, or the dashboard
- [ ] Enrolment survives a restart
- [ ] Calls `creds.store()`; does not implement it

While `creds.py` is unwritten you may develop against
`identity.store_node_token()`. Be clear-eyed about what that is: it writes the
secret in plaintext to `%LOCALAPPDATA%`, its own comment says so, and it is a
known gap being tolerated — not a pattern to copy or extend.

---

## Y11 — Earnings, labelled honestly · `pending`

The console gets an earnings and payout surface. **There is no metering.**
`agent/core/meter.py` raises `NotImplementedError` on all three of its functions.
Every number on this tab is invented, and will stay invented until metering is
written — which is hand-built and not yours.

So the requirement of this task is not the numbers. It is that a person reading
the screen can tell, without being told, which figures are measured and which are
placeholders.

The page already does this well and you should keep the mechanism: per-card `Live`
and `Preview` badges, and a header that says outright that *"provider identity,
offers, usage, earnings, and payouts are not yet implemented and nothing shown for
them is real."*

- [ ] Earnings, payout account, and line-item evidence surfaces exist
- [ ] Every unbacked figure carries a visible marker
- [ ] No screenshot of this page could be mistaken for real revenue
- [ ] The tab links to what would have to exist for it to become real

This is the one that matters when someone puts a screenshot in a pitch deck. A
dashboard that mixes measured and invented numbers without marking which is which
is how a placeholder becomes a figure somebody repeats as a fact.

---

## Y12 — Design the render job schema · `pending`

**DDL in a document first. Again.** This is the third time this file has carried
that instruction, and Y3 is still the worked example of what happens when it is
skipped. Design, then apply — they are different activities and the second is much
harder to undo.

Read [ADR 0006](adr/0006-render-batch-jobs.md) before anything else. It decides the
shape; you decide the columns.

Deliver `docs/schema/render-jobs.md`:

- [ ] `render_jobs` — one row per submission. Status values, and **which of them
      are stored versus derived**. ADR 0006 decision 4 says job status is derived
      from its frames at read time; if you disagree, argue it in the document
      rather than quietly storing it.
- [ ] `render_frames` — one row per frame, carrying its own `status`, `node_id`,
      `lease_expires_at` and `attempts`. This is the unit of claim, lease and
      retry, so its index has to match the claim query the way
      `inference_jobs_claimable_idx` matches its own (`schema.sql:242`).
- [ ] `provider_nodes.render_eligible` and `users.render_enabled` — both
      `NOT NULL DEFAULT FALSE`. **The default is the entire safety property.**
      A column that defaults `TRUE` here means every provider who installs the
      app tomorrow starts running strangers' code.
- [ ] **Blender version.** ADR 0006 lists this as a silent-failure class: the same
      file on a different build produces different pixels and nothing raises.
      Either the node reports its version as a capability and selection matches on
      it, or the product supports exactly one version. Choose in this document.
- [ ] **What `attempts` is for, and what bounds it.** A frame that fails
      deterministically — a corrupt file, a missing texture — will be retried by
      every eligible node in turn unless something stops it. Say what stops it.
- [ ] The retention question, so it is answered somewhere before Y13 acts on it:
      how long a source `.blend` and its artifacts are kept.
- [ ] Open questions listed explicitly rather than quietly decided.

Then apply the tables. Two `CREATE TABLE IF NOT EXISTS` and two
`ADD COLUMN IF NOT EXISTS`, which is still inside the ceiling `schema.sql:151`
describes — note in the document whether you still believe that after writing it.
This is the third consecutive feature to claim it.

- [ ] Tables applied idempotently, matching the document
- [ ] Re-running the schema against a populated database changes nothing

---

## Y13 — Object storage: the bucket, and what it is allowed to keep · `pending`

Renders move files. ADR 0006 decision 3 puts them in object storage with the
orchestrator minting short-lived presigned URLs, so bytes travel browser→storage
and storage→provider and never through the 512 MB Render instance.

**Before anything else, verify the free tier.** Cloudflare R2 was chosen for zero
egress fees, but neither the current limits nor whether it requires a card on file
have been checked against Cloudflare's own pricing page.
`docs/solution/FREE-COMPUTE-NO-CARD.md` exists because that constraint has bitten
this project before. If R2 needs a card and there isn't one, say so on day one
rather than after the endpoints are written — the S3 API is the same either way,
so the fallback is a provider swap and not a redesign.

- [ ] Free tier verified against vendor documentation, with the limits written
      down and dated
- [ ] Bucket created, private, with **no public read** on any path
- [ ] Credentials in Render's environment. **Never in `agent/`, never in the
      repository.** ADR 0006 is explicit that no storage SDK and no storage
      credential reaches a provider machine; `httpx` performs a presigned PUT and
      GET, so `agent/requirements.txt` needs nothing new. A PR touching that file
      in this work is a signal something went wrong upstream of it.
- [ ] Key layout that makes a customer's objects unguessable and
      non-enumerable from a single presigned URL
- [ ] **Lifecycle rules**, matching what Y12's document decided about retention.
      Storage costs money monthly and holds customer project files, which
      `docs/LEGAL-SECURITY-REQUIREMENTS-INDIA.md` gives weight to. This is not a
      setting for whoever happens to create the bucket to pick.
- [ ] A local development story. Somebody without the production credentials has
      to be able to run the stack — say whether that is a second bucket, MinIO in
      `docker-compose.yml`, or a documented "you cannot".

---

## Notes

Add a dated line when something changes.

| Date | Note |
|------|------|
| 2026-08-10 | File created. M0 code complete; Y1 is the blocking item. |
| 2026-08-16 | Y6–Y11 assigned: provider accounts, the console, and gated agent enrolment, per [ADR 0005](adr/0005-provider-accounts-and-agent-enrolment.md). Y1–Y5 are unchanged and still open; Y0 still gates everything. Y8 is what retires [ADR 0004](adr/0004-m1-unauthenticated-heartbeat.md), which has already expired by its own terms. |
| 2026-08-18 | **Y0 and Y1 closed as done** (#47, #50). Y1's verification is the quality bar for this file: run from a real clean clone, both failure paths exercised, deviations filed as issues rather than absorbed, and the two things it could *not* verify — GPU-served completion and the Nodes tab — stated plainly instead of implied. The stale `main.py:707` reference in Y7 was corrected to `:741`; PR #45 inserted `signups_open()` above it and shifted the file. **Y12 and Y13 assigned** for the rendering vertical, per [ADR 0006](adr/0006-render-batch-jobs.md) — schema and object storage. They rank below Y6–Y11 deliberately; the exception is verifying R2's free tier, which is small and unblocks other people. |
