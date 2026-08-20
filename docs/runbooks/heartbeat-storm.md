# Runbook: heartbeat storm or fleet freshness collapse

**Severity:** SEV-1 for widespread customer impact; SEV-2 when contained

**Trigger:** freshness ratio below 99% for 10 minutes, registration/heartbeat
rate spike, database saturation, or fleet flapping online/offline.

## Decide direction

- Low received heartbeats plus healthy API: provider network/agent issue.
- High heartbeat/registration rate plus rising DB/API latency: retry storm or
  abusive enrollment.
- Normal receive rate but low freshness: timestamp/TTL/configuration/deploy bug.
- API and health unavailable: use the control-plane/database runbook first.

## Contain

1. Pause deployments and new enrollment. Preserve authenticated heartbeats for
   already enrolled nodes where capacity allows.
2. Apply bounded edge rate limits and jittered `Retry-After`; never create a
   synchronized fixed retry loop. Rate-limit by authenticated enrollment and
   coarse network controls, not a public node ID alone.
3. Shed nonessential dashboards/list endpoints before health, result submission,
   lease safety or quarantine traffic.
4. If forged/open registration is involved, invoke `rogue-provider.md`.

## Recover and verify

Fix the triggering config/deploy/dependency, expand capacity only when it does
not hide the feedback loop, and ramp admission gradually. Verify DB connection
and request saturation, heartbeat freshness, registration-to-heartbeat ratio,
placement and provider flapping return to baseline. Confirm no expired/duplicate
lease was billed and cleanup evidence reconciles for jobs interrupted by the
storm.
