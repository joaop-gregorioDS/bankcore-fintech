# P5-B — Structured Logging and Correlation IDs

## Contract

P5-B introduces operational context without introducing tracing yet:

- `request_id`: identity of one HTTP request. A client retry is a new request and therefore receives a new value.
- `correlation_id`: identity of the logical BankCore operation. Transactions derives it from the existing deterministic `transaction_id`, so retries with the same idempotency context retain the same value.
- `trace_id`/`span_id`: intentionally reserved for P5-C; P5-B does not manufacture trace identifiers.

The existing `transaction.completed.v1` contract remains unchanged. Its `correlation_id` continues to equal the committed transaction ID. This preserves compatibility with the outbox and Audit Consumer while giving HTTP and service logs the same business identity.

## Propagation

Nginx preserves a supplied safe `X-Request-ID` or generates one using its request ID variable. It forwards that value to Auth and Transactions. Nginx never generates a business correlation ID.

The Python HTTP services validate or generate `X-Request-ID` and `X-Correlation-ID`, return both headers, and emit a JSON completion event. Transactions replaces the provisional correlation context with the deterministic transaction ID before Pix destination resolution and the Risk call. It forwards both IDs to Auth's internal Pix resolution and to Risk.

The outbox publisher adds `x-event-id` and `x-correlation-id` Kafka headers. Audit validates those headers when present against the versioned event payload and preserves them through retry/DLQ messages. Existing messages without the new headers remain compatible.

## JSON log policy

Python services use the shared `common.observability` allowlist. Risk uses the JSON console with the same conceptual fields. Operational events include `service`, `environment`, `event`, `request_id`, `correlation_id`, and only when useful: `transaction_id`, `event_id`, `risk_assessment_id`, `duration_ms`, `status`, `decision`, `rules_version`, retry metadata, topic and consumer group. Nginx exposes its native millisecond-resolution request time as `duration_seconds` because `$request_time` is supplied by Nginx in seconds.

The implementation never logs `Authorization`, JWTs, passwords, CPF/CNPJ, Pix keys, email addresses, connection strings, key material, secrets or full request payloads. High-cardinality identifiers are not metric labels; metrics remain a later P5 phase.

## Scope boundary

P5-B does not add OpenTelemetry, Prometheus, Grafana, trace propagation, dashboards, alerts or worker readiness endpoints. Those belong to P5-C through P5-H. Logging is best-effort and is not part of the financial commit: logging failures must not change ledger, outbox, Kafka or Audit semantics.

## Verification

The unit contract tests cover JSON validity, allowlisting, sensitive-value exclusion, request/correlation header preservation and response header emission. Existing Risk, idempotency, outbox, Kafka and Audit suites remain the integration evidence for the unchanged financial and delivery behavior.
