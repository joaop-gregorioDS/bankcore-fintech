# P5-G — Observability End-to-End Validation

P5-G provides one disposable command that exercises the already-proven
observability layers and the financial fault-injection scenarios under one
repeatable entry point:

```text
python scripts/p5-observability-e2e.py
```

The command intentionally uses isolated disposable sub-runs. This prevents a
successful scenario from hiding state left by an earlier failure while keeping
the financial and Kafka fault-injection logic in the existing P3/P5 runners.

## Evidence chain

| Signal | Validation | Operational question |
| --- | --- | --- |
| Structured logs / correlation | P5-C tracing runner and redaction scan | Can one operation be followed without exposing credentials? |
| Distributed trace | HTTP → Risk → ledger/outbox → Kafka → Audit spans | Where did this operation spend time or fail? |
| Metrics | P5-D happy, Redis fallback, Kafka retry and recovery scenarios | Is the behavior changing in aggregate? |
| Dashboards | Grafana datasource and four provisioned dashboards | Can an operator see the relevant subsystem quickly? |
| Alerts | Prometheus pending/firing/recovery tests and runtime rule loading | Does an operational condition require attention? |
| Financial invariants | P3 Kafka/outbox/Audit recovery, poison and idempotency scenarios | Did observability failures alter money or durable state? |

The P3 scenarios cover Kafka outage/recovery, publisher crash recovery, Audit
consumer recovery, PostgreSQL restart recovery, idempotency, risk rejection
and poison/DLQ behavior. P5-D covers Redis fallback and a real transient Kafka
retry. P5-G adds a full financial happy path with the OpenTelemetry Collector,
Prometheus and Grafana stopped; the transaction must still complete and recover
with its ledger/outbox invariants intact.

The correlation contract is deliberately split by signal:

```text
request_id / correlation_id → logs and trace context
service / route / outcome   → bounded metric and alert labels
```

Identifiers are never promoted to metric or alert labels. Redaction checks
cover Authorization/Bearer material, passwords, secrets, connection strings,
CPF/CNPJ and Pix keys across the observability configuration surfaces; the
trace runner also scans Collector output after the real happy path.

No new business rule, telemetry backend, external notification, production
secret, deployment or VPS access is introduced by P5-G. P5-H will place this
single entry point under GitHub Actions.
