# Reliability and security drill record

- Drill ID:
- UTC start/end:
- Scenario and runbook:
- Environment (must not be production unless explicitly approved):
- Incident commander:
- Participants/observers:
- Safety guardrails and abort conditions:
- Expected signals and objective:

## Timeline

Record UTC time, action/observation, role, and result. Never paste customer
content, credentials, presigned URLs, IPs, hostnames, or raw production dumps.

## Results

- Time to detect:
- Time to acknowledge:
- Time to contain:
- Time to recover:
- Was the affected node/workload prevented from accepting new work?
- Did any canary cross the boundary?
- Did alerts route to the expected owner?
- Did the dashboard distinguish degraded from unreachable?
- Did all evidence remain content-free?
- Objective passed/failed:

## Follow-up

| Action | Owner role | Due UTC | Verification | Status |
|---|---|---|---|---|
| | | | | |

Runbook changes, alert tuning and unresolved risk are linked from the incident
record. Close the drill only after each critical corrective action has an owner.
