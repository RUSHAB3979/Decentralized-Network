# Findings register

Every security-relevant defect found in this repository, its current status, and
what closes it. **This file is meant to be edited as fixes land** — a register
that is only accurate on the day it was written is worse than none, because
people trust it.

## How to use it

- **Do not delete a row when it is fixed.** Change `Status` to `FIXED`, add the
  commit, and keep the description. The value of a register is the history.
- Findings `RC-*` and `OPS-*` originate here. `CI-*` findings live in
  [ci-security-audit.md](ci-security-audit.md) and are referenced, not copied —
  one description, one place to update.
- `RC-01`–`RC-03` have **executable records** in
  `security/tests/test_failure_injection.py::OpenFindings`. Those tests assert
  the *current* (defective) behaviour, so fixing a finding turns the test red
  and forces this file to be updated in the same change. That is the mechanism
  that keeps the register honest; do not weaken it.

Status values: `OPEN` · `FIXED` · `ACCEPTED` (known risk, deliberately carried)
· `SUPERSEDED`.

---

## Open

| ID | Sev | Area | Finding |
|---|---|---|---|
| **RC-01** | High | `security/runtime_contract.py` | A signature verifier returning a truthy **non-bool** is accepted |
| **RC-02** | Medium | `security/runtime_contract.py` | `SecurityController.finish()` is not idempotent — a retry permanently quarantines a healthy node |
| **RC-03** | Medium | `security/runtime_contract.py` | `SecurityController.begin()` silently drops `maximum_audit_age` |
| **RC-04** | Low | `security/runtime_contract.py` | Egress allowlist accepts hostnames that resolve to cloud metadata |
| **OPS-01** | Critical | git history | Historical Postgres credential — rotation not confirmed (see `CI-02`) |
| **OPS-02** | Low | `agent/identity.py` | Node credential stored in plaintext (accepted seam, see below) |

### RC-01 — a truthy non-bool verifier is accepted
**Status: OPEN** · found 2026-08-20

`verify_cleanup` ends with:

```python
if not signature_valid:
    reasons.append("signature_invalid")
```

`SignatureVerifier` is annotated `-> bool`, but nothing enforces it, and the
whole point of the injection point is that callers supply their own crypto.
Measured behaviour:

| Verifier returns | `verified` |
|---|---|
| `"yes"` | `True` |
| `1` | `True` |
| `[1]` | `True` |
| `object()` | `True` |

A caller wiring in a library whose `verify()` returns a *result object* rather
than a bool gets **every signature accepted**, silently, with the module
reporting success. The exception path was already handled carefully
(`except Exception → False`); this is the same idea one step further.

**Fix:** `if signature_valid is not True:`. This is a behaviour change to a
security check and belongs to whoever owns the module.
**Closes when:** the identity comparison lands and
`test_RC01_truthy_non_bool_verifier_is_accepted` is removed.

### RC-02 — `finish()` is not idempotent
**Status: OPEN** · found 2026-08-20

```
first  finish: verified=True   quarantined=False
second finish: verified=False  quarantined=True  ('receipt_job_mismatch')
can_claim(): False
```

A runner that completes cleanup, crashes before recording the outcome, and
retries on restart bricks a healthy node — and clearance deliberately requires
an operator audit.

Worth weighing against the rest of the codebase, which is emphatic about this:
the heartbeat is "idempotent by construction", register is an upsert precisely
so twenty restarts leave one row. This is the one place a retry is punished.

This may well be intended as fail-closed. If so it needs a comment saying so,
because as written it reads like an oversight — and a documented decision is
what stops the next person from "fixing" it.
**Closes when:** either a replay of an identical, already-accepted receipt is a
no-op, **or** a docstring states the deliberate choice and this row moves to
`ACCEPTED`.

### RC-03 — the controller drops `maximum_audit_age`
**Status: OPEN** · found 2026-08-20

`begin()` calls `authorize(posture, policy, now=now)` without forwarding the
parameter, so the 7-day default always applies through the controller:

```
authorize(..., maximum_audit_age=1 day)  → ('audit_stale',)   refused
controller.begin(same posture)           → allowed=True       admitted
```

A deployment that tightens audit freshness gets the loose default. It is a
*silent policy weakening*, which is precisely the class of defect this module
exists to prevent.
**Closes when:** `begin()` accepts and forwards the parameter.

### RC-04 — egress allowlist accepts metadata hostnames
**Status: OPEN (low)** · found 2026-08-20

`SandboxPolicy` correctly refuses IP literals — `169.254.169.254` included —
plus `localhost`, `*.localhost` and `*.local`. But `metadata.google.internal`
passes the format check and resolves to that same link-local address.

The allowlist is reviewed by a human, so this is a policy-authoring hazard
rather than a contract defect. Recorded so it is a *known* one.
**Closes when:** a denylist of known metadata names is added, or the reviewers'
checklist names it explicitly.

### OPS-01 — historical database credential
**Status: OPEN** · found 2026-08-13 · tracked as **CI-02**

A real Postgres password was committed to `.env.example` and reached the
`gh-pages` branch, which GitHub Pages serves publicly. It was removed from the
served branch on 2026-08-13, but **removal is not rotation** and it remains in
git history on `main`.

Two things made it worse than it looked: the file was one routine config change
away from being publicly fetchable (adding `.nojekyll` stops Jekyll hiding
dotfiles — both changes went in the same commit, so there was no window), and
CI's gitleaks scan does not flag it, so scanner-green proved nothing.

**Only rotation closes this.** Deleting files does not retract a credential.
**Closes when:** the founder confirms rotation, and a redacted-fingerprint
gitleaks rule regression-tests the detection gap.

### OPS-02 — node credential stored in plaintext
**Status: ACCEPTED** — hand-built seam under ADR 0002

`agent/identity.py` writes the node transport token to `%LOCALAPPDATA%` in
plaintext. Anyone with local access to a provider's machine can read it and
impersonate the node.

This is documented at the call site, not hidden. DPAPI-backed storage, rotation
and hardware binding are owed by `agent/core/creds.py`, which still raises
`NotImplementedError`.
**Closes when:** `creds.py` ships.

---

## Fixed

| ID | Sev | Finding | Fixed in |
|---|---|---|---|
| **OPS-03** | High | `POST /providers/heartbeat` took no credential; any anonymous caller who knew a `node_id` (they were listed by `/providers/nodes`) could take a provider offline or advertise models it does not have, routing work to a node guaranteed to fail | `bd4f14b` (#54) |
| **OPS-04** | Medium | Agent worker busy loop — the claim endpoint answers immediately, but the loop `continue`d with no wait, polling as fast as the network allowed. Self-inflicted DoS against the orchestrator, and on metered hosting a bill that scales with how *idle* the fleet is | `2e7737c` (#43) |
| **OPS-05** | Medium | API keys had no owner. Administration was gated on the caller being loopback with `LOCAL_DEMO_MODE` — a deployment posture, not an identity, so every caller from the right address was the same anonymous customer | `2e7737c` (#43) |
| **OPS-06** | Medium | Inference ran on the orchestrator's own host while *claiming* to run on a selected provider. Node selection was bookkeeping; execution never left the server | `2e7737c` (#43) |
| **CI-03** | High | `pytest.ini` discovered only `orchestrator/tests` and `agent/tests`, so the 22 security-contract tests were linted and compiled but **never executed**. Green CI, zero security tests run | this change |

### Notes on the fixed rows

**OPS-04** survived both the unit tests and a live end-to-end run, because the
stand-in agent used in that run had the same flaw. It was caught while preparing
metered hosting, not by a test. `test_the_loop_waits_between_empty_claims` now
guards it.

**OPS-06** was closed by deleting `inference.run_chat` rather than leaving it
unused: a working "run the model here" helper is one import away from silently
turning rented inference back into inference-on-the-server, with every test
still green.

**CI-03** is fixed by adding `security/tests` to `testpaths`. The finding is
kept here because the *shape* recurs — this repository has now had the same
class of gap twice (`pytest.ini` and `.ruff.toml` were also outside every CI
path filter until #39's fallout). Any new test root needs a discovery entry, and
nothing enforces that automatically.

---

## Deliberately carried risks

Not defects. Decisions with named expiry conditions, listed so they are not
rediscovered as surprises.

| Risk | Where stated | Ends when |
|---|---|---|
| Session token in `localStorage`, so an XSS bug leaks it | `web-client/src/services/authApi.js` header | A cookie with `SameSite` + CSRF protection is worth the complexity |
| Future-dated heartbeats are treated as online, tolerating consumer clock skew | `orchestrator/liveness.py` docstring | A timestamp affects payment — then skew becomes an attack |
| Token counts stored as evidence, never converted to money | `orchestrator/schema.sql`, `agent/worker.py` | `agent/core/meter.py` ships |
| Lease has claim and derived expiry only; no renewal, drain, or partial results | `orchestrator/schema.sql` | `agent/core/lease.py` ships |
| Provider selection ignores VRAM headroom, concurrency and cold-start cost | `_select_provider_for_model` docstring | Real scheduling is written |

---

## Verifying this file

```bash
pytest security/tests -q          # 45 tests; OpenFindings encodes RC-01..RC-03
pytest -q                         # security/tests is now discovered
ruff check .
```

A finding moving to `FIXED` should turn its `OpenFindings` test red. If a fix
lands and every test still passes, either the fix is incomplete or the test was
weakened — check which before updating the row.
