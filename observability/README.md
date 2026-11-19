# R10 observability assets

## Inference pilot health

1. Set `METRICS_BEARER_TOKEN` on the orchestrator to a dedicated, randomly
   generated secret. Give Prometheus the same value in a protected credentials
   file. The route is disabled when the variable is empty. Put the scraper on
   loopback or use HTTPS on a private management path.
2. Copy `prometheus/pilot-scrape.example.yml` and `prometheus/pilot-rules.yml`
   together into the Prometheus configuration directory. Point the single
   `gpuorbit-orchestrator` scrape job at the orchestrator and set the credential
   file path. Keep the `instance: pilot` alias. On separate hosts, configure
   `scheme: https` and a TLS-enabled target. Use a route that still reaches the
   process during a failed readiness check. An edge that removes unhealthy
   instances will surface a scrape failure during that outage. [Prometheus configuration reference](https://prometheus.io/docs/prometheus/latest/configuration/configuration/#scrape_config)
3. Run `promtool check config` against the configured file. Verify the target is
   up and serves both gauges. The probe runs on every authenticated scrape and
   shares the `SELECT 1` path with `/health`. It returns HTTP 200 with zero-valued
   gauges during a database outage so Prometheus can read the failure.
4. In Grafana, import `grafana/pilot-health.json` and select the pilot Prometheus
   data source. The dashboard shows the current database, readiness and scrape
   states with their history. [Grafana import instructions](https://grafana.com/docs/grafana/latest/visualizations/dashboards/build-dashboards/import-dashboards/)
5. Connect Alertmanager and route `{owner="sre",severity="sev1"}` to the named
   pilot responder. Before enabling paging, rehearse a database outage in staging
   and confirm delivery and resolution with the responder. [Degraded service runbook](../docs/runbooks/orchestrator-degraded.md)

Run the rules regression cases from the repository root with
`promtool test rules observability/prometheus/pilot-rules.test.yml`.

## Full observability contract

`prometheus/security-sre-rules.yml` defines alerts for the remaining contract in
[Service objectives](../docs/sre/objectives-and-alerts.md). The pilot scrape
example loads only `pilot-rules.yml`. The full rule set requires application
instrumentation and staging validation before enablement.

Keep customer, provider, node and inference job identifiers, IPs, hostnames,
URLs, filenames, prompts, results and trace IDs out of metric labels. The
Prometheus `job` and `instance` labels use fixed scrape aliases.
