# P5-E — Grafana dashboards

The disposable P5-E stack provisions Grafana with Prometheus as its default datasource and loads four versioned dashboards: BankCore Overview, Financial Flow, Async / Kafka / Outbox, and Auth / Redis Resilience.

The dashboards use existing P5-D metrics. Histogram percentiles are calculated with `histogram_quantile` from exported buckets. No financial amounts, personal data, request identifiers, trace identifiers, or other high-cardinality identifiers are used in dashboard labels, variables, or queries.

Run the disposable validation with `python scripts/p5-grafana.py`. It validates Grafana health, Prometheus datasource health, all four dashboards, datasource bindings, and the absence of alerting configuration, then removes containers, volumes, and networks. Alerting is deferred to P5-F.
