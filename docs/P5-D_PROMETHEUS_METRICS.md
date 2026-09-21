# P5-D — Prometheus Metrics

P5-D adds bounded OpenTelemetry metrics to the existing BankCore services and
validates them through a disposable Prometheus instance. The OTLP path is:

```text
Auth / Transactions / Risk / Publisher / Audit
                 ↓ OTLP metrics
          OpenTelemetry Collector
                 ↓ Prometheus exporter
              Prometheus
```

Metrics export is fail-open. Without an OTLP metrics endpoint, services use the
OpenTelemetry no-op provider. If the collector or Prometheus is unavailable,
the request, ledger, outbox and consumer paths continue operating.

The metric model deliberately uses only bounded labels: operation, outcome,
decision, route template, HTTP method, status class and failure class. Request,
correlation, trace, transaction, event, user, account and Pix identifiers are
never metric labels.

The disposable validation runner is:

```text
scripts/p5-metrics.py
```

It builds the project images, starts PostgreSQL, Redis, Kafka, the Collector and
Prometheus, runs the happy, risk-rejection, poison/DLQ, Kafka recovery and Redis
fallback scenarios, verifies the Prometheus metric names and checks that no
forbidden high-cardinality labels are present. It always tears down its project
and volumes, including after failure.

Grafana and alerting are intentionally deferred to P5-E/P5-F.
