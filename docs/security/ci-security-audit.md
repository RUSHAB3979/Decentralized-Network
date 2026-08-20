# CI security audit

**Owner:** R4 Security & Sandbox Engineer

**Audited:** 2026-08-20

**Scope:** `.github/workflows/ci.yml`, lock/requirements inputs and security-test
discovery. Static review was followed by local native-scanner execution. Docker
remains unavailable because system installation requires an interactive sudo
password; no container image or live database drill was executed.

## Existing controls

| Control | Assessment |
|---|---|
| Full-history secret scan | Gitleaks checks full checkout history, fails closed and redacts output. Useful, but its image uses a mutable version tag and a known historical database credential is not detected by the current rules. |
| JavaScript dependency audit | Root workspaces and web client run `npm ci --ignore-scripts` then production-only high-severity audit. Install scripts are suppressed. Dev/build dependency vulnerabilities are not blocking. |
| Filesystem vulnerability scan | Trivy action is commit-pinned, scans high/critical findings, emits SARIF and returns failure. SARIF upload is allowed to no-op, but scanner failure remains blocking. |
| SBOM | SPDX JSON artifact is generated for selected TypeScript orchestrator/agent path changes and retained 90 days. It is not signed/attested and does not comprehensively trigger on Python/security/runtime changes. |
| Least workflow permissions | Workflow defaults to read; security adds only `security-events: write`. Good baseline. |
| Reproducibility | npm locks and exact top-level Python pins exist. Transitive Python dependencies are not hash-locked; provider Windows dependencies are not installed/tested by the Python job. |
| Security contract tests | Dependency-free and now discovered: `security/tests` is in `testpaths`, so CI runs 45 of them (22 contract + 23 failure-injection). RC-01..RC-03 in `test_failure_injection.py` assert current defective behaviour, so a fix turns them red and forces a register update. |

> Runtime-contract findings (`RC-*`) and operational findings (`OPS-*`)
> are tracked in [findings-register.md](findings-register.md), which also
> carries the current status of the `CI-*` findings below.

## Findings, prioritized

### CI-01 — required build jobs can be silently skipped (critical coverage)

`orchestrator`, `provider-agent`, and `context-server` each `need` the conditional
`contracts` job. When only the dependent service changes, `contracts` is skipped;
GitHub dependency semantics can skip the downstream job before its own condition
runs. The final gate explicitly accepts `skipped` as healthy. A service-only
change may therefore merge without its build/typecheck.

**Required owner/fix:** R3/R9 CI owner changes dependency conditions to include
`always()` and explicitly accepts successful/skipped prerequisite only when path
logic is valid, or makes the contracts build unconditional for dependent jobs.
Add workflow-level test cases for each path-only change. Final gate must fail an
unexpected skip. R4 reviews the result.

### CI-02 — known historical secret evades gitleaks (critical secret hygiene)

The repository task record identifies a historical Postgres credential blob
that the current scan passes. Do not reproduce its value. Scanner green is not
evidence of rotation or revocation.

**Immediate:** founder verifies credential rotation/revocation and access logs.
**Then:** add a redacted fingerprint/custom rule regression. History purge is a
separate disruptive operation and remains blocked on explicit founder approval.

### CI-03 — security tests are absent from pytest discovery (high) — **FIXED**

**Status: FIXED.** `security/tests` was added to `testpaths` in `pytest.ini`.
`pytest -q` now collects 45 security tests where it previously collected zero.

`pytest.ini` limited discovery to product test roots. A regression in the
fail-closed cleanup/admission contract would not have executed in CI. Note the
path filter was never the problem — it triggers on `**/*.py`, so ruff and
py_compile did run over `security/`. Only the tests were skipped, which is why
this was invisible: every signal CI produced was green and accurate.

**Required owner/fix:** R1/R3 adds `security/tests` to the official Python test
command or the R4-owned security job. Acceptance is an intentional failing test
that makes the required branch check red. Do not rely only on compile.

### CI-04 — Python and Windows-agent dependency coverage is incomplete (high)

No explicit Python advisory audit runs. The test job installs orchestrator
requirements plus selected test tools, not the full provider Windows dependency
set. Trivy may recognize requirements manifests, but the intended dependency
coverage and resolved transitive tree are not demonstrated, and the packaged
Windows agent is not produced/exercised.

**Required owner/fix:** add a pinned Python advisory scanner against resolved,
hash-locked orchestrator and agent environments; build the signed Windows
artifact on a Windows runner; scan the artifact/SBOM; exercise startup and
signature verification. R4 owns severity/exception policy; R6/R3 own packaging.

### CI-05 — mutable third-party execution references (high supply chain)

The gitleaks container uses `zricethezav/gitleaks:v8.30.1`, a mutable registry
tag. Several GitHub-maintained actions use major tags. The Trivy action is
correctly commit-pinned. Any action/container with repository read access can
alter results or exfiltrate checked-out content if its reference moves.

**Required owner/fix:** pin container image by digest and actions by reviewed
commit SHA; retain human-readable version comments; use Dependabot/Renovate for
controlled updates. At minimum, pin all non-GitHub actions and every container.

### CI-06 — production-only npm audit omits build-chain risk (medium/high)

Dev dependencies execute during builds/typechecking even when absent from the
runtime bundle. Production-only audit is appropriate for runtime exposure but
does not cover compromised/vulnerable build tooling.

**Required owner/fix:** retain the production blocking gate and add a separate
all-dependency audit/report. Define exceptions with package, advisory, reachability,
owner and expiry; critical build-chain findings block release.

### CI-07 — SBOM is incomplete and unsigned (medium)

The SBOM trigger misses many Python-only, security, image and deployment changes
and describes a source tree rather than the exact signed provider artifact and
sandbox image. A mutable artifact can drift from its SBOM.

**Required owner/fix:** generate per-release SBOMs from resolved dependencies
for orchestrator, provider executable and sandbox image; bind each to artifact
digest/provenance and signature; retain with release evidence.

### CI-08 — no isolation/adversarial integration gate (expected but blocking)

Unit tests mock Blender/storage and the new security tests validate only policy.
No CI/staging gate boots the target VM, applies network denial, assigns/resets a
GPU, kills power/processes, or attempts marker recovery.

**Required owner/fix:** dedicated hardware staging pipeline owned jointly by
R4/R6/R3. It must publish signed, content-free evidence and is a release gate for
isolated workload images/runtime, not for ordinary documentation changes.

## Security gate policy

- Critical/high findings fail closed unless an R4-reviewed, time-bounded
  exception states exploitability, compensating control, owner and expiry.
- Scanner failure/timeouts are failure, not “no findings.”
- Scanner output and artifacts redact secrets and have minimum access/retention.
- Security tooling updates are reviewed like production code and run on an
  untrusted test repository before merge.
- Critical sandbox/runtime CVEs disable affected admission within the time
  needed to contain and have a 48-hour remediation target.

## Local verification completed

- Publisher checksums passed for gitleaks 8.30.1, Trivy 0.73.0, Prometheus
  `promtool` 3.13.2 and Syft 1.50.0 before execution.
- Gitleaks scanned 127 commits / approximately 7.21 MB with `--redact` and
  reported no leak. This reproduces CI's known false-negative limitation for
  the historical credential; it does not prove the history is secret-free.
- Trivy scanned vulnerabilities, secrets and misconfiguration at high/critical
  severity and exited clean. Its vulnerability database was current for the
  run; Trivy advertised 0.74.0 while the selected Arch-repository version was 0.73.0.
- `npm audit --omit=dev --audit-level=high` reported zero vulnerabilities for
  the root workspaces and web-client lockfile. `pip-audit` 2.10.1 reported no
  known vulnerabilities for both pinned Python requirement files.
- A second npm audit including development/build dependencies also reported
  zero vulnerabilities for both lockfiles. CI-06 remains a coverage finding
  because the required branch gate does not run that broader check.
- Ruff 0.16.2 passed repository-wide. Bandit 1.9.4 produced three medium
  confidence B608 warnings in `orchestrator/main.py` (lines 1923, 2304 and
  2362). Review confirmed each interpolates the same fixed internal SQL status
  expression while request values remain driver-parameterized; they are static
  analysis false positives, not accepted injection paths.
- Syft generated a repository SPDX JSON SBOM as temporary audit evidence.
- `promtool` initially rejected the new placement-latency expression. The rule
  was corrected and the final check reports success with 11 rules.
- On managed Python 3.11.15, 62/62 agent tests, 81/81 non-`TestClient`
  orchestrator tests and 22/22 security tests passed. The remaining 65
  orchestrator tests use FastAPI `TestClient`; a one-route minimal FastAPI
  control also hangs at the AnyIO blocking portal in this execution sandbox,
  so those tests cannot be evaluated here. This is recorded as an environment
  limitation rather than converted into a product pass or failure.
- No workflow file was changed: it is co-owned, and the user explicitly limited
  implementation to R4/R10-owned surfaces. Findings above are handoffs, not
  silent edits to another role's build system.
