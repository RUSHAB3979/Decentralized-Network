# Pilot Postgres outage drill · 19 November 2026

- **Environment** — Local disposable PostgreSQL 16, FastAPI and Prometheus 3.16 with synthetic data.
- **Scenario** — Stop PostgreSQL while the orchestrator and scraper keep running. Check the API, alert state and dashboard queries, then restart the same database. [Degraded service runbook](../../runbooks/orchestrator-degraded.md)
- **Guardrails** — The database used an isolated local socket and synthetic schema. The API and scraper used loopback and a temporary scrape credential. The drill restored the database before cleaning up test resources.

## Timeline (UTC)

| Time | Observation |
|---|---|
| 17:06:20 | Baseline `/health` returned 200. The dashboard queries showed Postgres **Up**, orchestrator **Ready** and metrics **Reporting**. |
| 17:06:20 | Postgres stopped. `/service` returned 200, and `/health` returned 503 with `db: down` in 1 ms. The stopped local socket failed immediately. |
| 17:06:25 | Dashboard queries showed Postgres **Down** and readiness **Degraded**, with metrics still **Reporting**. |
| 17:06:35 | `MarketplaceDatabaseDown` entered pending, 14.8 seconds after outage injection. |
| 17:08:35 | The alert fired 135.1 seconds after outage injection. The readiness-only and missing-telemetry alerts stayed inactive. PostgreSQL restarted and the first recovery probe returned 200. |
| 17:08:50 | The alert resolved and all three dashboard queries recovered 14.6 seconds after restart. |
| 17:18:45 | The fifth recovery probe returned 200 with a healthy database and schema. The workstation clock advanced between probes two and three. |

## Results

The API and metrics distinguished database loss from an unreachable orchestrator.
Prometheus detected the outage, held the alert for two minutes, and resolved it
after recovery. Five health probes succeeded across the recovery window.
In a separate short outage, Grafana rendered all four panels in Firefox. The
dashboard showed Postgres **Down**, readiness **Degraded** and metrics
**Reporting**, along with their separate timelines.

Staging acceptance still requires a scrape path that reaches an unhealthy
instance and Alertmanager delivery and resolution to the named pilot responder.
The staging owner also needs to verify the dashboard against the hosted scraper.
[Pilot monitoring setup](../../../observability/README.md)
