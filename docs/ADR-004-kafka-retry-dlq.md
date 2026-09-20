# ADR-004 — Kafka Retry and Dead-Letter Handling

## Status

Accepted for P3-F.

## Context

The Audit Consumer provides at-least-once delivery: PostgreSQL commits before the source Kafka offset. A malformed event must not be retried forever, while a temporary database or broker failure must not discard a valid event. A poison message must also not block later messages in the same partition.

## Decision

Use two derived topics for the versioned transaction event:

```text
bankcore.transaction.completed.v1.retry
bankcore.transaction.completed.v1.dlq
```

Contract and key validation failures are permanent and go directly to the DLQ. Other processing failures receive one short local retry, then a bounded retry-topic delivery. `MAX_RETRIES` defaults to three; a retry failure at or beyond that count goes to the DLQ.

The original domain payload is preserved. Only sanitized operational headers are added:

- `retry-count`
- `original-topic`
- `original-partition`
- `original-offset`
- `failure-class`
- `failure-reason`
- `failed-at`

The source offset is committed only after the retry or DLQ producer receives a broker acknowledgement. If publication fails, the source offset remains uncommitted, so duplicate publication is possible but loss is not. Consumers remain idempotent through the `event_id` uniqueness constraint.

The source group is `bankcore-audit-v1`; retry deliveries use `bankcore-audit-retry-v1`. The P3-F test environment uses three partitions to prove distribution across two instances.

## Consequences

At-least-once delivery remains explicit. A producer or consumer crash after a derived-topic ACK and before source-offset commit may create a duplicate retry/DLQ record; this is acceptable because no source event is lost and downstream processing is idempotent. Delayed retry scheduling, DLQ replay tooling, notification consumers and a schema registry remain outside this phase.
