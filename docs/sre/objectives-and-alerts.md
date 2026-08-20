# Service objectives, incident severity and observability contract

**Owner:** R10 Site Reliability Engineer

**Initial measurement window:** 28 rolling days

**Status:** objectives and alert rules defined; application metric emission and
dashboard deployment require the cross-team instrumentation handoff.

## Safety invariants

Safety invariants override availability objectives and error budgets:

- 100% of terminal customer jobs have a verified cleanup receipt.
- No next tenant starts after missing or failed cleanup evidence.
- Zero recovered cross-job canary markers.
- Zero unisolated third-party render/cloud-gaming admissions.
- Zero customer content, secrets, URLs, paths or peer IPs in telemetry.

An invariant breach pages immediately and disables affected scheduling. Do not
keep accepting work to preserve availability.

## Service-level objectives

| User journey / control | SLI | Objective | Exclusions |
|---|---|---|---|
| Control-plane availability | valid non-5xx API responses / valid requests, measured at edge | 99.5% over 28 days | approved maintenance; rejected/invalid/auth-failed requests |
| Database-backed health | successful `/health` DB probes / probes | 99.5% over 28 days | approved maintenance |
| Provider heartbeat freshness | enrolled accepting nodes fresh within configured TTL / enrolled accepting nodes | 99.0% each 10-minute window; 99.5% over 28 days | nodes explicitly drained or sleeping before accepting work |
| Job placement | time from schedulable submission to valid claim | p95 no more than two configured claim-poll intervals | no eligible supply, customer hold, invalid job |
| Session/job success | accepted jobs completing without platform failure / accepted jobs | at least 95% over 28 days | customer cancel, invalid input, declared capacity limit |
| Cleanup coverage | verified cleanup receipts / terminal customer jobs | 100% in every 5-minute reconciliation window | none |
| Quarantine latency | cleanup failure observed to node unable to claim | 100% within 60 seconds | none |
| Orphan discovery | elapsed time from supervisor startup/orphan creation to discovery | startup gate plus periodic reconciliation within 5 minutes | none |

“No eligible supply” is shown separately from control-plane failure. A product
with no matching node is unavailable to the customer even if the API is green,
so capacity-denial rate has a dashboard panel and product objective, but it does
not corrupt the control-plane error budget.

## Metrics contract

Names below are the required interface for the provided Prometheus rules.

| Metric | Type | Allowed labels |
|---|---|---|
| `marketplace_dependency_up` | gauge | `dependency` from bounded enum |
| `marketplace_http_requests_total` | counter | route template, method, status class |
| `marketplace_http_request_duration_seconds` | histogram | route template, method |
| `marketplace_provider_heartbeat_fresh_ratio` | gauge | coarse provider pool only |
| `marketplace_job_placement_seconds` | histogram | workload, outcome |
| `marketplace_claim_poll_interval_seconds` | gauge | workload |
| `marketplace_jobs_terminal_total` | counter | workload, terminal class |
| `marketplace_job_success_total` | counter | workload, outcome class |
| `marketplace_security_cleanup_receipts_total` | counter | workload, outcome, bounded reason |
| `marketplace_security_cleanup_pending_oldest_seconds` | gauge | workload only |
| `marketplace_security_orphan_oldest_seconds` | gauge | sandbox kind only |
| `marketplace_security_quarantined_nodes` | gauge | bounded reason, sandbox kind |
| `marketplace_security_quarantine_latency_seconds` | histogram | bounded reason |
| `marketplace_security_canary_recovered_total` | counter | bounded surface |
| `marketplace_security_unsandboxed_admissions_total` | counter | workload, tier |
| `marketplace_security_egress_denied_total` | counter | destination class, workload |
| `marketplace_security_sensitive_telemetry_findings_total` | counter | finding class, source class |

Never label a metric with node, job, customer, provider, IP, hostname, URL,
model input/output, path, exception text, or trace ID. Those cause cardinality
failures and data leaks. Opaque node/job/trace aliases may appear only in
access-controlled structured events with bounded retention.

## Alert policy

The deployable rule definitions are in
`observability/prometheus/security-sre-rules.yml`. Alert routing must use:

- **Page immediately:** sandbox escape/canary recovery, unsandboxed admission,
  cleanup pending over 60 seconds, cleanup failure, leaked telemetry secret,
  or inability to quarantine.
- **Page after sustained impact:** database down for 2 minutes, control-plane
  fast burn, heartbeat-freshness below 99% for 10 minutes.
- **Ticket/business hours:** slow burn, capacity exhaustion trends, denied
  egress with no successful flow, audit staleness before eligibility expires.

Every page names a runbook and a single symptom. Do not alert on every provider
node separately; aggregate first, then use logs/inventory for investigation.

## Severity

| Severity | Examples | Initial response target | Authority |
|---|---|---|---|
| SEV-0 | confirmed/suspected sandbox escape, cross-tenant marker, customer data exposure, cleanup bypass with subsequent tenant | acknowledge 5 min; contain immediately | incident commander may disable workload tier/fleet and revoke credentials |
| SEV-1 | cleanup unverified before reuse, rogue provider admitted, database/control plane unavailable, mass heartbeat loss, deletion failure before exposure | acknowledge 15 min | incident commander may drain pool/disable affected endpoint |
| SEV-2 | contained single-node failure, elevated placement latency, isolated capacity loss, repeated denied egress | business-hour owner or 60 min if customer impact | owner drains affected component |

SEV-0/SEV-1 opens one incident record, UTC timeline and commander. Preserve
content-free evidence; do not copy customer content into chat/tickets. Founder,
security, SRE, relevant system owner and retained counsel are paged for suspected
personal-data exposure. Counsel/legal owner decides statutory notification and
communications; engineers do not promise a breach determination or deadline.

## Dashboard layout

1. Customer: control-plane availability/latency, placement p50/p95/p99, success
   rate, capacity denial by workload.
2. Fleet: enrolled/accepting/fresh/drained/quarantined counts, heartbeat ratio,
   claim rate and orphan age.
3. Safety: terminal jobs vs verified receipts, oldest pending cleanup, cleanup
   failure reasons, quarantine latency, canary recovery, unsandboxed admissions.
4. Dependencies: Postgres/object storage/KMS/relay availability and saturation.
5. Incidents: error-budget burn, active alerts, deploy/image/runtime versions.

Dashboard variables are time range, workload, tier, sandbox kind and image
release only. No customer or node identifier variable is permitted.

## Error-budget policy

- At 50% of the 28-day availability budget consumed: stop discretionary risk
  changes and assign the top reliability cause.
- At 100%: freeze workload expansion; ship only recovery/security fixes until
  the rolling window is back within objective or the objective is deliberately
  changed in an architecture decision.
- Safety invariant incidents always freeze affected workload expansion,
  independent of error-budget status.

## Drills

Quarterly drills cover database-down degraded mode, cleanup failure/quarantine,
orphan cleanup after abrupt host restart, heartbeat storm, credential revocation,
object-deletion failure, and sandbox-escape containment. Use
`docs/sre/drill-log-template.md`; a runbook is not “rehearsed” until it has a
dated drill record with observed timings and corrective actions.
