# R10 observability assets

`prometheus/security-sre-rules.yml` implements the paging expressions defined
in `docs/sre/objectives-and-alerts.md`.

These rules are intentionally not wired into deployment yet: the live services
do not emit the metric contract, and deployment configuration is owned by R3/R9.
Loading them before instrumentation would produce absent-series blind spots.
The platform owner must add metric emission and staging scrape configuration;
R10 then validates the expressions with `promtool`, injects each condition, and
records alert-routing evidence before production enablement.

No rule or future dashboard may use customer, provider, node, job, IP, hostname,
URL, filename/path, prompt, result or trace ID as a metric label.
