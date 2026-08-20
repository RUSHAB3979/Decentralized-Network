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
- Open findings carry **executable records** in
  `security/tests/test_failure_injection.py`. While open, the test asserts the
  *current defective* behaviour, so a fix turns it red and forces this file to
  be updated in the same change; once fixed, it converts to a regression test in
  `FixedFindings`. That is the mechanism that keeps the register honest — do not
  weaken it, and see the note under RC-03 for how to pick the property so it
  actually fires.

Status values: `OPEN` · `FIXED` · `ACCEPTED` (known risk, deliberately carried)
· `SUPERSEDED`.

---

## Open

| ID | Sev | Area | Finding |
|---|---|---|---|
| **RC-04** | Low | `security/runtime_contract.py` | Egress allowlist accepts hostnames that resolve to cloud metadata |
| **OPS-01** | Critical | git history | Historical Postgres credential — rotation not confirmed (see `CI-02`) |
| **OPS-02** | Low | `agent/identity.py` | Node credential stored in plaintext (accepted seam, see below) |

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
| **CI-03** | High | `pytest.ini` discovered only `orchestrator/tests` and `agent/tests`, so the 22 security-contract tests were linted and compiled but **never executed**. Green CI, zero security tests run | `e17e12d` |
| **RC-01** | High | `verify_cleanup` ended `if not signature_valid`, so a verifier returning a truthy non-bool accepted **every** signature | `2026-08-20` |
| **RC-02** | Medium | `SecurityController.finish()` was not idempotent — a retried delivery of an already-accepted receipt permanently quarantined a healthy node | `2026-08-20` |
| **RC-03** | Medium | `SecurityController.begin()` dropped `maximum_audit_age`, silently applying the 7-day default to deployments that had tightened it | `2026-08-20` |

### RC-01 — how it was closed

`if signature_valid is not True`. An identity check accepts one value and one
value only, so a verifier returning a result object, a string, or a non-empty
list no longer validates a signature.

A non-bool is now reported as **`verifier_contract_violation`**, separately from
`signature_invalid`, because the two need different responses: a bad signature
is a receipt to reject and possibly an attack, while a non-bool means this
deployment has wired its cryptography up wrongly and *every verdict that
verifier has ever produced is suspect*. Collapsing them would bury the second
under the noise of the first.

### RC-02 — how it was closed

`SecurityController` now records the `(payload_digest, signature)` of the
receipt it accepted, and a byte-identical redelivery returns the same success
instead of quarantining.

Recognition is deliberately narrow, because "accept it again" is a dangerous
shape. It requires both the canonical signed bytes **and** the signature to
match, so it cannot be reached by a receipt differing in any field — a changed
`sandbox_id`, a flipped cleanup flag, a recovered canary — nor by replaying a
genuine signature over altered content. It also cannot resurrect a quarantined
node. Six tests cover those edges; they are the point of the change, not the
happy path.

The behaviour it replaces was arguably fail-closed, but it made an ordinary
crash at an ordinary moment take a healthy provider off the marketplace
permanently, and it was the only write in the system that punished a retry.

### RC-03 — how it was closed

`begin()` accepts and forwards `maximum_audit_age`, and both it and `authorize`
now default to a single `DEFAULT_MAXIMUM_AUDIT_AGE` constant. A test asserts the
two signatures reference the same object, because two literals in two places is
how one gets tightened and the other keeps admitting week-old attestations.

**A note on the mechanism, because it partly failed here.** RC-01 and RC-02 had
`OpenFindings` tests that went red the moment the fix landed, exactly as
intended. RC-03's did not: it asserted that `begin()` *uses* the seven-day
default, which stayed true afterwards, since passing no argument still selects
the default. The finding was that the parameter could not be supplied at all, so
the sharp characterisation would have been `assertRaises(TypeError)`. The
forcing function is only as good as the property each test picks — worth
remembering when writing the next one.

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
pytest security/tests -q          # 54 tests; FixedFindings regression-guards RC-01..RC-03
pytest -q                         # security/tests is now discovered
ruff check .
```

A finding moving to `FIXED` should turn its open-finding test red. If a fix
lands and every test still passes, either the fix is incomplete, or the test
asserted the wrong property — check which before updating the row. RC-03 was the
second case.
