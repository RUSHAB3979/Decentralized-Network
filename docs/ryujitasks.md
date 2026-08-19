# Task List — @ryujikentaro

**Roles:** R4 Security & Sandbox + R10 SRE
**Owns:** Threat model, sandbox design, CI security gates, runbooks
**Shares:** `.github/workflows/ci.yml` with @YogitaKanwar (she owns `.github/`; you own the `security` job)
**Related:** [TEAM-EXECUTION-PLAN.md](TEAM-EXECUTION-PLAN.md) · [ROLES.md](ROLES.md) · [Tasks/tasks.md](Tasks/tasks.md)

Status values: `pending` · `in_progress` · `blocked` · `done`

Task IDs use `K` so they do not collide with the role IDs (R1–R10).

---

## Current priority

**K0, then K2.** K1 is the highest-value item on this list and it is
**blocked on the founder's explicit go-ahead** — do not begin any part of it
until he says so in writing.

**K6 and K7 were added on 2026-08-18** and are the newest security work on the
critical path: the marketplace is starting a Blender rendering vertical, which
puts untrusted files on provider hardware. Do K2 before K6 — K6 is the concrete
instance of the T-04 category K2 models, and it reads better second.

---

## Read this first

There is a real, unrotated credential in this repository's git history.

- Blob `05996365c42ff1e394e7cf6adb4ab23dae28c824`
- It is a `POSTGRES_PASSWORD`
- The repository is **private**, which is the only reason this is a task and
  not an incident

**The CI secret scanner does not detect it.** Gitleaks is pinned, runs against
full history with `fetch-depth: 0`, and fails closed — and it returns clean on
a repository that demonstrably contains a live password.

That sentence is the most useful thing on this page, so it is worth stating
plainly: **failing the scanner closed did not make the history clean.** A
green security job is evidence that a specific set of patterns did not match.
It is not evidence that there are no secrets. Every gate you inherit or build
should be read the same way — ask what a pass actually proves, not what it
feels like it proves.

**Never paste the credential itself** into an issue, a commit message, a PR
description, or a chat. Reference the blob SHA. The password contains an `@`,
which means a URL-parsing error message can leak a fragment of it — treat
error text from connection failures as sensitive too.

---

## K0 — Track 0: read the CI security job · `pending` · **start here**

Read the `security` job in `.github/workflows/ci.yml` (starts around line 317)
and **open one issue per gap you find**.

That is your first PR task's replacement — the reading is the deliverable, and
issues are the artifact. Also add yourself a line to `CONTRIBUTORS.md` in a
first PR, same as everyone else; nobody writes a feature until their first PR
is merged.

### What is currently there

| Gate | Tool | Notes |
|---|---|---|
| Secrets in history | `gitleaks v8.30.1` (pinned) | `--redact`, full history, fails closed |
| JS dependency vulns | `npm audit` ×2 | root workspaces + `web-client` |
| Filesystem vulns | `trivy-action` (SHA-pinned) | `CRITICAL,HIGH`, SARIF → GitHub Security |
| Supply chain | separate `sbom` job | |

### The questions to ask of each one

Do not just check that a gate exists. For each, work out:

- **What does a pass prove?** And more importantly, what does it *not* prove?
  You already have one worked example above.
- **What is excluded?** Read the flags. `--omit=dev` and `--audit-level=high`
  are both decisions, and both were made without being written down. Are they
  the right decisions? Say why either way.
- **What is not covered at all?** Enumerate what the repo contains and what
  each scanner actually reads. Something in this repo has dependencies that no
  gate on that list audits — find it.
- **Does it fail closed or fail quiet?** A step with `continue-on-error` or
  `if: always()` is deliberately allowed to not block. Each such case in this
  file has a reason; check that the reason still holds.
- **What happens on a fork PR?** Permissions and secrets behave differently.

Title format: `security: <gate> does not cover <thing>`

One issue per gap. A single issue listing eight problems gets closed when
three are fixed.

- [ ] `CONTRIBUTORS.md` line, PR merged
- [ ] `security` job read end to end
- [ ] One issue filed per gap, each with what a pass currently proves

---

## K1 — Credential purge · `blocked` — **needs the founder's explicit go-ahead**

**Do not start any step of this without written approval from @RUSHAB3979.**
He has not given it. This section documents the plan so it is ready when he
does, not so it can be executed.

The reason for the gate is that step 3 rewrites every commit hash in the
repository. Everyone's existing clone becomes invalid at that moment and the
cost multiplies by the number of people who have cloned — which is why the
timing is a founder decision, not a security-owner decision.

### Sequence (from execution plan §5b — order matters)

1. **Rotate the password first.** Not last. Between rotation and purge, the
   exposed value is worthless; in the other order, there is a window where the
   history is rewritten and the live credential is still valid.
2. Lift the force-push protection on `main`.
3. `git filter-repo` to remove the blob from history.
4. Force-push.
5. **Re-enable force-push protection immediately.** This is the step that gets
   forgotten because the interesting part is already over.
6. Founder re-clones, verifies, and only then tells everyone else to re-clone.

### Before you propose a date

- [ ] Confirm how many live clones exist (each one is a copy of the history
      you are about to rewrite, and re-cloning is manual work for that person)
- [ ] Confirm the password is not in use anywhere outside `.env` — a rotation
      that breaks something unlisted turns a planned change into an outage
- [ ] Write down what "verified" means in step 6, as a command someone can run
- [ ] Check whether GitHub retains the old objects after force-push, and what
      to do about it if so
- [ ] Decide whether to purge *before* or *after* the repository ever goes
      public. Public changes this from a hygiene task to an emergency

### After it lands

- [ ] Add a rule that catches this class of mistake next time. Gitleaks
      already missed it once — a gate that would not have caught the thing you
      just spent a day removing is not a fix

---

## K2 — Threat model: T-01 and T-04 · `done` (2026-08-20)

The risk register calls these two platform-killing. Model those two properly
rather than all ten superficially.

**T-01 — data theft from provider nodes.** A customer's data sits on hardware
owned by a stranger. Register controls: per-session encrypted ephemeral
volumes, keys never on the host OS, wipe-on-exit verified, auto-suspend on
wipe-verification failure.

**T-04 — malicious workload escapes the sandbox.** A customer's code runs on a
stranger's PC. Register controls: gVisor or Firecracker, no privileged
containers, no host mounts, syscall filtering, GPU passthrough only to the
sandbox, curated-image allowlist in v1, external pen-test before Phase 1 exit,
48h CVE patch SLA.

Note that these are opposite directions of the same trust problem — the
customer does not trust the provider, and the provider does not trust the
customer. Any control that only protects one side is half a control.

For each, deliver:

- [ ] Attack tree: what a motivated attacker actually does, step by step, not
      a category name
- [ ] **Which listed control is load-bearing** — if exactly one control has to
      hold, which is it, and what happens the day it fails
- [ ] Detection: how we find out it happened. Several of the listed controls
      are preventive with no detection story attached
- [ ] "GPU passthrough only to the sandbox" — what that actually means at the
      driver level, and whether it is achievable on consumer Windows hardware,
      which is the hardware this platform is built on
- [ ] What is **not** mitigated, stated explicitly. An honest residual risk is
      worth more than a full column of green

Deliver as `docs/risk/threat-model-t01-t04.md`.

---

## K3 — Review: the unauthenticated heartbeat endpoint · `blocked` (needs M1)

M1 ships `POST /providers/register` and `POST /providers/heartbeat`. As
designed, both are **unauthenticated**.

Your job is not automatically to demand auth. It is to decide, and to write
down the reasoning either way:

- [ ] What can an unauthenticated caller do — register fake providers, forge
      heartbeats for someone else's node, flood the table?
- [ ] What does that cost us at M1 scale, where the users are the five people
      in this repo?
- [ ] What is the trigger that makes it unacceptable — first external
      provider, first paying customer, public repo? Name it concretely so the
      decision expires on its own instead of quietly becoming permanent
- [ ] If the answer is "acceptable for now", the reasoning goes in an ADR, not
      a PR comment. A decision nobody can find later gets re-argued later

Coordinate with @Shubh-tech-grow — he writes the agent side, and whatever you
decide he has to implement.

---

## K4 — CI security gates · `ongoing`

You own the `security` job; @YogitaKanwar owns the rest of `.github/`. Changes
that touch both need both of you.

Standing responsibilities:

- [ ] Keep the pins pinned. `gitleaks` is on a version tag and `trivy-action`
      on a commit SHA, on purpose — an unpinned scanner is a third party with
      write access to whether your build passes
- [ ] Close the gaps K0 turns up, in priority order, one PR each
- [ ] Treat a red Dependabot PR as a finding, not noise. On 2026-08-10, PR #9
      was labelled a dev-dependency group bump, actually carried three majors,
      was already failing its own CI, and was merged by hand. `main` was red
      for two and a half hours. The group label hid the semver intent — the
      reliable source is `dependabot/fetch-metadata`'s `update-type`
- [ ] The `main` ruleset requiring **"🟢 All checks passed"** is what makes
      `gh pr merge --auto` and `scripts/ship.ps1` safe. If it is ever removed,
      both must be deleted in the same commit

---

## K5 — Runbooks (R10) · `pending`

SRE half of your role. Start with one and make it real rather than writing six
templates.

The first one to write is **"the orchestrator is up and its database is
down"**, because that state already exists, is already reachable, and already
has an observable signature:

| Signal | Value |
|---|---|
| `GET /health` | `503`, `{"status":"degraded","db":"down","version":"0.1.0"}` |
| Provider agent | `Orchestrator Reachable but Unhealthy 503`, exit `1` |
| Response time | ~10s, not immediate |

Reproduce it with `docker stop marketplace_db` and write down what someone
does next. The distinction this runbook exists to preserve is *degraded* vs
*unreachable* — alive but broken, versus not running. They look similar on a
dashboard and have completely different first moves.

- [ ] `docs/runbooks/orchestrator-degraded.md`
- [ ] Reproduced by hand before it was written, not from the code

---

## K6 — Threat model: the untrusted `.blend` · `done` (2026-08-20)

This is T-04 stopped being hypothetical. [ADR 0006](adr/0006-render-batch-jobs.md)
starts a Blender rendering vertical, and a `.blend` file can carry embedded
Python. K2 models T-04 as a category; this models the one instance of it that is
about to have code written against it.

Read ADR 0006 first, particularly decision 2. **The gate it describes is a column,
not a control.** `render_eligible` defaults to `FALSE` so that only the founder's
own machine runs renders during the pilot. Your job is to establish what has to be
true before that column can ever be set on a machine we do not own.

- [ ] **Embedded scripts.** `--disable-autoexec` is what the agent will pass.
      Establish what it actually covers and what it does not — drivers, node
      groups, app handlers, and anything else that executes without being an
      auto-run script. Say whether the flag is a control or a speed bump.
- [ ] **Path traversal on output.** The render writes files. A scene that
      controls its own output path controls where those bytes land on the
      provider's disk.
- [ ] **Resource exhaustion.** A scene can request more memory than the machine
      has, or run effectively forever. Both look like a slow render, and the
      provider's PC becomes unusable while it happens.
- [ ] **Egress.** The unified plan requires default-deny networking (§3.1). The
      pilot has none. State what a render process can reach today on a normal
      Windows machine, including the local network behind the provider's router.
- [ ] **Oversized artifacts.** Output size is attacker-controlled. Say what
      bounds it, and what happens to the provider's disk if nothing does.
- [ ] **What is not mitigated**, stated explicitly, as in K2.

Deliver as `docs/risk/threat-model-untrusted-blend.md`.

---

## K7 — Sandbox design — the document that retires the gate · `done` (2026-08-20)

ADR 0006's expiry condition is this task. Until a sandbox exists, rendering is
restricted to one machine by a boolean, and the marketplace has one supplier.

The unified plan states the requirement (§3.1): *"it must execute only inside a
disposable sandbox with default-deny networking."* K2 lists gVisor and Firecracker
as register controls. **Both assume Linux.** The providers this marketplace is
built to aggregate run consumer Windows — that is ADR 0003's whole premise — so
the register's answer and the actual hardware do not currently meet.

Compare, on the hardware we actually have:

- [ ] **Windows Sandbox** — present on Windows Pro and above, absent on Home.
      Establish whether GPU access works, because a sandbox with no GPU renders
      nothing. Rushab's own machine runs Windows 11 Home Single Language; if that
      excludes it, the pilot machine cannot run the sandbox it is meant to prove.
- [ ] **Containers with GPU passthrough** — requires WSL2 or Hyper-V. Say what
      that asks of a provider who just wanted to install an app, and whether
      NVIDIA passthrough into WSL2 is dependable on consumer drivers.
- [ ] **A full VM** — heaviest, most isolated. Say what it costs in setup and in
      render throughput.
- [ ] **Cleanup verification.** Not "we delete the folder" — how do we *know* it
      is gone, and what happens when the machine is put to sleep mid-render and
      resumed three days later. Provider PCs are gaming PCs; this is the normal
      case, not the edge case.
- [ ] A recommendation, with the honest answer about what fraction of consumer
      Windows machines can actually run it. **If the answer is "most providers
      cannot", that is the finding** — it is better delivered now than after the
      agent has been built against an assumption.

Deliver as `docs/security/render-sandbox-design.md`.

This does not block the pilot. It blocks the pilot ending.

---

## Notes

Add a dated line when something changes.

| Date | Note |
|------|------|
| 2026-08-20 | **K2, K6 and K7 design artifacts delivered.** Added the fail-closed runtime/cleanup contract and tests, data-lifecycle/identity policy, external penetration-test scope, CI audit, SRE objectives/alerts and incident runbooks. The design concludes that consumer Windows Sandbox/WSL2 is not the sole boundary for hostile GPU workloads; third-party render requires a certified full-VM/dedicated-GPU profile. Native gitleaks, Trivy, pip-audit, npm audit, Bandit, Syft, Ruff and promtool validation has now run and is recorded in the CI audit. K5 remains pending because Docker installation requires interactive sudo and the database-down runbook has not yet been rehearsed. K0 remains pending until its one-issue-per-gap and contributor-PR acceptance artifacts are filed. |
| 2026-08-10 | File created. K1 blocked pending founder go-ahead — not yet given. Recorded that gitleaks passes clean on a history containing blob `05996365`. |
| 2026-08-18 | **K6 and K7 assigned**, per [ADR 0006](adr/0006-render-batch-jobs.md). The marketplace is adding Blender rendering, which means untrusted files executing on provider hardware — T-04 with a date on it. K6 models the specific case; K7 designs the sandbox, and ADR 0006's expiry condition *is* K7. Neither blocks the pilot: rendering is gated to one machine by a column defaulting to `FALSE`. Both block that gate ever opening. Worth flagging early if K7 concludes that consumer Windows cannot host a real sandbox — that finding changes the product, and it is cheaper now than after the agent is built. |
