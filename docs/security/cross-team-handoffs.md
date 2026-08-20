# Cross-team security and reliability handoffs

These changes are required to complete the design but are outside the R4/R10
owned surfaces. This file specifies acceptance contracts; it does not authorize
R4 to edit another role's code. Owners should create/assign tracked issues and
request R4/R10 review on security/SRE acceptance evidence.

| ID | Primary owner role | Required change | Acceptance evidence | Blocks |
|---|---|---|---|---|
| SEC-H01 | R1/R5 orchestrator/auth | Replace open provider enrollment with authenticated invitation/approval and bind revocable node identity to attested agent/posture. Registration must never grant work eligibility by itself. | Fake/unapproved registrations cannot claim; stolen/replayed enrollment is rejected; revocation test passes. | Any external customer inference/render |
| SEC-H02 | R5/R9 API/database | Envelope-encrypt queued inference content; minimize job envelope; destroy DEK and clear content on every terminal state with retry/reconciliation. Correct API privacy wording until deployed. | DB/backups/logs inspection shows ciphertext/no terminal content; cancel/timeout/crash deletion tests. | Confidential external inference |
| SEC-H03 | R6 provider agent | Store node private material in DPAPI/OS credential vault or hardware key; integrate signed posture, durable sandbox state machine, startup orphan cleanup and content-free receipts. | Token absent from plaintext files/logs; reboot/crash suite; failed cleanup prevents claim. | Vetted/isolated provider tiers |
| SEC-H04 | R3/R9 storage/platform | Enforce source/artifact lifecycle, version/replica deletion, capability expiry, inventory reconciliation and per-object/job crypto-erasure. | Live staging lifecycle/deletion drill including versions/backups and expired URL denial. | External render data |
| SEC-H05 | R5/R6/R3 telemetry | Emit the bounded metric/event contract and deploy Prometheus/Grafana/alert routing without sensitive/high-cardinality labels. | Seeded-secret scan, cardinality budget, injected-alert drill and dashboard review. | Production SLO claims |
| SEC-H06 | R3/R9 CI | Resolve CI-01 through CI-08 in `ci-security-audit.md`, including actual security-test discovery, Python/Windows artifact audit and immutable pins. | Path-change matrix; deliberate failing-test evidence; signed artifact/SBOM; scanner failure blocks. | Security release gate |
| SEC-H07 | R1/R6 runtime/platform | Build Linux KVM/VFIO and/or supported Hyper-V/DDA runner to `render-sandbox-design.md`; do not substitute process/container/WSL2 isolation for hostile files. | Hardware matrix, performance baseline, isolation/cleanup/chaos suite and independent retest. | Third-party render/gaming |
| SEC-H08 | R1/R5/R9 scheduling/schema | Store authoritative posture/tier/quarantine/receipt state and make scheduler admission fail closed. Re-registration/restart cannot clear eligibility or quarantine. | Transaction/race/replay tests; next-tenant invariant; auditable privileged recovery. | Multi-tenant scheduling |
| SEC-H09 | R2 streaming | Implement privacy mode with relay-only ICE/TURN, short-lived per-session credentials and no peer IP in logs/signaling. | Packet/signaling capture shows peers only contact relay; direct candidates absent; credential expiry. | Private cloud gaming |
| SEC-H10 | R8 product | Accurately disclose tier/residual risk, retention/deletion state, capacity unavailable vs platform failure, and internal-pilot limitations. | Security/legal copy review; no “absolute confidentiality/safety” claims. | External launch messaging |
| SEC-H11 | R11/R9 legal/data | Approve purpose-specific content, artifact, security-event, access-log and backup retention/deletion schedule plus incident notification decision path. | Versioned policy mapped to technical lifecycle controls and drill. | Production retention claims |
| SEC-H12 | R1/R3 repository governance | Assign CODEOWNERS for `/security/`, `/observability/`, `/docs/security/`, `/docs/risk/`, `/docs/sre/` and `/docs/runbooks/` to R4/R10 with appropriate architecture/platform cross-review. | GitHub review request/ruleset test. | Durable ownership |

## Recommended sequencing

1. SEC-H01 and H03 prevent anonymous/credential-based provider impersonation.
2. SEC-H02/H04 establish content/key deletion on control-plane and storage paths.
3. SEC-H05/H06 make failures visible and enforce regressions.
4. SEC-H07/H08 implement actual isolated execution and scheduling.
5. Run the external penetration-test scope and remediate/retest.
6. R1 decides whether measured eligible supply justifies opening the gate;
   H09/H10/H11 complete workload-specific privacy, disclosure and retention.

Internal synthetic and owner-controlled render pilots may proceed if explicitly
labeled unsandboxed and kept off third-party customer/provider data. They do not
satisfy or waive any handoff above.
