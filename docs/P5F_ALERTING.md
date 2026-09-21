# P5-F — Alerting & Failure Visibility

P5-F adds a small, versioned Prometheus alert contract. It uses only bounded
operational labels and metrics already present in the P5-D pipeline. It does
not add external notifications or business-decision alerts.

The rules are in `infra/prometheus/rules/bankcore-alerts.yml`. Initial
thresholds are operational defaults, not production SLOs; they must be
calibrated after representative load and incident data exists.

The initial alerts cover:

- Redis local fallback;
- growing or old transactional outbox backlog;
- Kafka retries and DLQ events;
- Audit retry/DLQ processing failures;
- explicitly emitted technical Risk outcomes;
- high Transactions HTTP 5xx rate;
- the OpenTelemetry Collector scrape target being down.

Risk `REJECTED` decisions are intentionally not alerts: they are valid domain
outcomes. The `RiskServiceErrors` rule is dormant until the Risk service emits
an `ERROR` or `UNAVAILABLE` technical outcome, so the current decision metric
cannot confuse business rejection with infrastructure failure.

The disposable runner is:

```text
python scripts/p5-alerts.py
```

It runs `promtool` inside the pinned Prometheus image and injects synthetic
time series for every rule. Each scenario verifies the complete lifecycle:

```text
normal → pending → firing → recovered/inactive
```

No Alertmanager, Slack, email, PagerDuty, webhook, production secret, deploy
or VPS connection is involved in P5-F. Routing to external systems is deferred
until alert semantics and thresholds have been calibrated.

Logs/traces identify one operation; metrics/dashboards show aggregate
behavior; alerts indicate that an operational condition requires attention.
