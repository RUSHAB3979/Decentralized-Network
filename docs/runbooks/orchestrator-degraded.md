# Runbook: orchestrator reachable, database down

**Severity:** SEV-1 when sustained/customer-impacting

**Trigger:** `GET /health` returns `503` with
`{"status":"degraded","db":"down",...}` while the service still accepts TCP/HTTP

**Expected provider symptom:** reachable but unhealthy `503`, retrying rather
than destructive deregistration

**Expected probe latency:** roughly 5–10 seconds for an unreachable database,
because the repository's database connect timeout is 5 seconds plus request and
network overhead.

## First decision: degraded or unreachable

From an approved operator host, record UTC time and status only:

```bash
curl --silent --show-error --output /dev/null --write-out '%{http_code} %{time_total}\n' https://ORCHESTRATOR/service
curl --silent --show-error --output /dev/null --write-out '%{http_code} %{time_total}\n' https://ORCHESTRATOR/health
```

- `/service` responds and `/health` is 503: this runbook; inspect database and
  its network/credentials first.
- both time out/refuse/connect-fail: the orchestrator or edge is unreachable;
  inspect deployment, routing, DNS and load balancer first.
- `/health` is 200: the original alert may have recovered; continue through
  reconciliation before closing.

Do not paste response headers, environment variables or connection URLs into
the incident record.

## Contain

1. Open one incident, assign commander, pause deployments/schema changes, and
   announce degraded control plane internally.
2. Confirm whether active provider jobs can safely continue locally. Do not
   reschedule or bill ambiguous jobs during database loss.
3. Disable new customer submission at the edge if retries are amplifying load
   or the outage exceeds the job timeout. Keep health/service endpoints alive.
4. Compare outage start with deploys, credential rotation, database maintenance,
   saturation, regional networking and provider status.

## Diagnose and recover

For the repository's local Compose environment:

```bash
docker compose ps db
docker compose logs --since 15m --tail 200 db
docker compose up -d db
docker compose exec db pg_isready
```

Use `docker compose restart db` only after logs/status show the process is wedged
and a restart will not interrupt a restore or migration. Never delete the
`pgdata` volume as an outage response.

For managed Postgres, inspect provider health, connection limits, CPU/storage,
replica/primary state, TLS/credential errors and network policy. Restore service
through the provider's documented failover/restart path. Rotate credentials
only when compromise or expiry is indicated; blind rotation adds another fault.

## Verify

1. `/health` returns 200 for five consecutive probes across at least two
   minutes, at normal latency.
2. Database connections/query latency and error rate return to baseline.
3. Heartbeats recover without a registration surge; accepting/fresh counts
   converge with pre-incident values.
4. Reconcile jobs whose leases or terminal updates overlapped the outage.
   Duplicate/ambiguous execution is not billed until the trusted-metering owner
   resolves it.
5. Reconcile terminal jobs and cleanup receipts; any missing security evidence
   invokes `cleanup-verification-failed.md`.
6. Resume submissions and deploys gradually, watching error and queue rates.

## Evidence and closure

Keep UTC timeline, status classes, aggregate counts, deploy IDs, database event
IDs and corrective actions. Do not retain query results containing customer
content. Write a postmortem for SEV-1 or any recurrence.

**Rehearsal status (2026-08-20): not rehearsed in this workspace.** No Docker
CLI is installed here, so the documented `marketplace_db` stop/recovery drill
could not safely be performed. The next staging drill must stop only the
database, confirm `/service` remains reachable, record actual `/health` latency,
then execute this runbook and add a drill log.
