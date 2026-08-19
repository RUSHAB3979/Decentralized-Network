# ADR 0006 — Blender batch rendering as the second workload class

| Field | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-08-18 |
| **Owner** | [@RUSHAB3979](https://github.com/RUSHAB3979) (R1 Architect) |
| **Implemented by** | K6–K7 (R4), Y12–Y13 (R3/R9), S9–S10 (R2/R6), A6–A7 (R8) |
| **Relates to** | [ADR 0002](0002-generated-vs-handbuilt.md) — does not move the hand-built boundary; [ADR 0003](0003-inference-beachhead.md) — does not replace the beachhead |

## Context

`docs/UNIFIED-GPU-MARKETPLACE-PLAN.md` names three execution primitives and puts **batch jobs**
first, with Blender as the wedge: it runs headless, it is open source, and animation frames can
be retried or distributed independently (§3.1). This ADR starts that vertical.

The marketplace can currently move exactly one shape of work. `POST /v1/chat/completions`
selects a node, writes a row to `inference_jobs`, and blocks the customer's HTTP request inside
`_await_job()` until an agent claims the row, runs Ollama, and posts a result back. That design
is correct for what it carries: a prompt is small text, an answer is small text, and both fit in
a JSONB column and a two-minute wait.

A render job breaks four of those assumptions at once.

**1. The payload is a file, not a field.** `inference_jobs.payload` is JSONB and
`result_content` is TEXT. A `.blend` is tens to hundreds of megabytes and the output is a
sequence of images. There is no object storage anywhere in this repository.

**2. The customer cannot wait on the socket.** `DISPATCH_WAIT_SEC` defaults to 120 and
`_await_job` blocks a FastAPI threadpool worker for its duration — the function's own docstring
notes that a few hundred concurrent waits are not survivable. A render runs for minutes to
hours. Submission has to be asynchronous.

**3. One job is many units of work.** A 120-frame animation that must restart from frame 1
because frame 87 failed is not a product. The unified plan's Phase 3 exit gate says so directly:
*"failed frames retry without restarting the full animation."*

**4. A `.blend` is untrusted code.** This is the one that governs the decision below. A Blender
file can carry embedded Python, and the unified plan already states the consequence: *"A
`.blend` file remains untrusted input because it may contain scripts; it must execute only
inside a disposable sandbox with default-deny networking"* (§3.1).

That sandbox does not exist. There is no container, no VM, and no Windows Sandbox integration
anywhere in `agent/`. `agent/requirements.txt` opens by stating that it is a security boundary
as much as a build input, because everything in it *"is something we have shipped onto hardware
we do not control."* And "provider sandbox and tenant isolation" is the first entry on ADR
0002's hand-built list.

Dispatching a customer's `.blend` to a third-party provider today would be arbitrary remote code
execution on a stranger's gaming PC, and nothing in the current codebase would prevent it or
notice it.

## Decision

### 1. Rendering is a second workload class, not a change of beachhead

ADR 0003 stands unchanged. Inference remains the beachhead; this adds a vertical alongside it
and tests whether the same aggregated supply serves batch work.

Concretely, that means rendering gets its **own tables, own endpoints, and own claim loop**
rather than a `workload_type` column bolted onto `inference_jobs`. The two have different
payload shapes, different lease windows, different retry units, and different billing units.
Collapsing them into one table would mean every future change to either one has to be reasoned
about against the other.

The cost is that the claim/lease pattern exists in a second place. That is accepted, and it is
bounded: the pattern is copied, not reinvented — `orchestrator/main.py:1039` is the reference
implementation and its `FOR UPDATE SKIP LOCKED` semantics are not to be re-derived.

### 2. Renders run only on explicitly eligible nodes — a gate, not a promise

Two columns, both defaulting to `FALSE`:

```sql
ALTER TABLE provider_nodes ADD COLUMN IF NOT EXISTS render_eligible BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE users          ADD COLUMN IF NOT EXISTS render_enabled  BOOLEAN NOT NULL DEFAULT FALSE;
```

Node selection for rendering filters on `render_eligible = TRUE`. A provider who installs the
desktop app tomorrow cannot receive a render job — not because anybody remembered to exclude
them, but because the default excludes them and a human has to run an `UPDATE` to change it.

This mirrors `provider_nodes.accepts_work`, which has defaulted `FALSE` since the first table in
the system (`orchestrator/schema.sql:39`). Defaults that fail closed are the only kind worth
having here.

**Say plainly what this is.** It is a column, not a sandbox. It buys exactly one thing: that the
blast radius of untrusted execution is a machine whose owner chose it, one `UPDATE` at a time.
Anyone who flips `render_eligible` on a machine they do not own has accepted arbitrary code
execution on it, and no code in this repository will stop them or tell them. The gate is a way
to ship the other ninety percent of the vertical while the sandbox is designed; it is not a
substitute for the sandbox and must never be described as one.

The pilot is therefore: the founder's own GPU, the founder's own files.

### 3. Files move through presigned object storage, never through the orchestrator

The orchestrator holds the storage credentials and mints short-lived, single-object presigned
URLs. Bytes travel browser→storage and storage→provider directly.

- **Upload** — `POST /v1/render/jobs` returns a presigned `PUT`. The job sits at
  `awaiting_upload` until confirmed.
- **Provider read** — the claim response carries a presigned `GET` for one source object,
  expiring inside the lease window.
- **Provider write** — a presigned `PUT` for exactly one output key. A provider cannot enumerate
  the bucket, read another customer's project, or overwrite a finished frame.
- **Customer download** — presigned `GET`s for completed frames.

The rejected alternative was proxying through FastAPI. It is less code and it is wrong twice
over: the orchestrator runs on a 512 MB Render instance that would be streaming multi-hundred-
megabyte files, and the egress is billed. More importantly it would put customer project data
through a process that has no reason to see it.

This satisfies the constraint the unified plan already states at line 419 — *"storage
credentials never reach a provider"* — and it keeps `agent/requirements.txt` unchanged, because
`httpx` already performs a presigned PUT and GET. **No storage SDK goes into the agent.** A
credential that never reaches a machine cannot leak from it.

### 4. The frame is the unit of claim, lease, and retry

`render_frames` carries one row per frame with its own `status`, `node_id`, `lease_expires_at`
and `attempts`. Job status is **derived** from its frames at read time.

Nothing sweeps. This repository has now made the same decision three times — liveness
(`schema.sql:11`), session expiry (`schema.sql:131`), and job reclaim (`main.py:1052`) — for the
same reason each time: a sweeper that dies leaves every expired thing valid forever and nothing
raises. A stored `render_jobs.status` maintained by a background task would be the fourth chance
to get that wrong.

## What this does not change

**ADR 0003 is untouched.** Inference is still the beachhead. If rendering later proves to be the
better market, that is a new decision and it gets its own record.

**ADR 0002's boundary does not move.** The sandbox, metering, and lease renewal remain
hand-built. In particular `agent/core/meter.py` still raises `NotImplementedError`, so
`render_frames.render_seconds` is recorded as **evidence of what the runtime reported, not as a
bill** — the same wording and the same reason as `submit_work_result` (`main.py:1127`).

The consequence is visible in the UI and must stay visible.
`web-client/src/components/app/RenderJobPage.jsx` already labels its quote `Illustrative only`
and its rates `preview`. **Those labels come off when metering lands and not one commit before.**
The form currently invents $0.18, $0.38 and $0.72 per hour; a screenshot of an invented price is
how a placeholder becomes a number somebody repeats as a fact.

**The agent gains no new reach.** No database driver, no storage SDK, no new capability. If a
pull request in this work touches `agent/requirements.txt`, that is the signal something went
wrong upstream of the file.

## Consequences

**Blender version drift is a silent-failure class and needs an explicit answer.** The existing
form offers 4.3, 4.2 and 3.6. The same `.blend` rendered on a different build can produce
different pixels, and nothing raises. Either the node reports its Blender version as a
capability and selection matches on it, or the product states which single version it supports.
Y12 chooses; it does not defer.

**The lease window has to be sized for the work, not copied.** `JOB_LEASE_SEC` defaults to 180
because an inference request is short. `main.py:962` explains what happens when the window is
under the slowest honest completion: the job is handed to a second agent while the first is
still working, and *"the customer pays twice for one answer."* A render frame needs its own
setting, and 180 seconds is not it.

**Lease renewal stops being optional.** For inference, a lapsed lease costs one repeated
request. For a frame that has been rendering for twenty minutes, it costs twenty minutes of a
provider's GPU and hands the same work to somebody else. `agent/core/lease.py` is unwritten, and
its absence is more expensive here than it was before.

**Migration pressure increases again.** Two tables and two columns, all reachable with
`CREATE TABLE IF NOT EXISTS` and `ADD COLUMN IF NOT EXISTS`, so this does not breach the ceiling
`orchestrator/schema.sql:151` describes. It is the third consecutive feature to say exactly that
sentence. Y4 remains unstarted and remains the right answer.

**Storage costs money and retains customer data.** Object lifecycle — how long a source `.blend`
is kept, how long artifacts are kept, who can delete them — carries legal weight given
`docs/LEGAL-SECURITY-REQUIREMENTS-INDIA.md`. It is not a bucket setting to be picked by whoever
happens to create the bucket. Y13 writes it down.

## Expiry condition

This ADR stands until the sandbox exists. When K7's design is implemented and verified — a
disposable environment with default-deny networking, resource caps, and confirmed cleanup — the
`render_eligible` gate stops being the thing that makes this safe, and opening rendering to
third-party providers becomes a new record with a threat model attached rather than an amendment
to this one.

Until then, the gate is the only control, and it is one `UPDATE` wide.
