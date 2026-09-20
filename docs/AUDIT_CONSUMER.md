# P3-E/P3-F — Idempotent Audit Consumer and Failure Handling

The Audit Consumer is a separate service with its own PostgreSQL database, `bankcore_audit`. It consumes only `bankcore.transaction.completed.v1` and records the committed fact; it never reads or writes the Transactions database and never changes balances, ledger entries or Risk decisions.

## Processing order

```text
Kafka record
  ↓ contract validation
PostgreSQL audit_events INSERT ... ON CONFLICT(event_id) DO NOTHING
  ↓ COMMIT
Kafka offset commit
```

Kafka auto-commit is disabled. If PostgreSQL fails, the offset is not committed. If the process crashes after the database commit and before the offset commit, Kafka may redeliver the event; the unique `event_id` constraint makes the replay a no-op.

The consumer validates the versioned envelope, required fields, positive `amount_cents`, fixed producer/type/version and the Kafka message key (`transaction_id`). Invalid JSON, invalid schema and key mismatches never become valid audit rows.

## Retry and DLQ

P3-F adds these topics without changing the domain payload:

```text
bankcore.transaction.completed.v1
bankcore.transaction.completed.v1.retry
bankcore.transaction.completed.v1.dlq
```

Permanent contract failures go directly to the DLQ. Database and broker-facing processing failures receive one short local retry, then go to the retry topic with a bounded `retry-count`. After `MAX_RETRIES` the event is sent to the DLQ. The retry consumer uses `bankcore-audit-retry-v1` and the source consumer uses `bankcore-audit-v1`.

Retry and DLQ records preserve the original Kafka value byte-for-byte. Sanitized operational headers carry `retry-count`, original topic/partition/offset, failure class, failure reason and failure time. Credentials, authorization headers, passwords and connection strings are never copied to those headers.

The ordering guarantee is:

```text
publish retry/DLQ
  ↓ broker ACK
commit source offset
```

If publishing the retry or DLQ record fails, the source offset remains uncommitted and the source message can be redelivered. Poison messages therefore advance after successful DLQ publication instead of blocking the partition indefinitely.

## Idempotency and ownership

```text
audit_events
├── event_id UNIQUE
├── transaction_id
├── payload JSONB
├── occurred_at
├── received_at
└── consumer_version
```

The audit database is consumer-owned. The consumer group is explicitly `bankcore-audit-v1`; multiple instances may share partition work, while `event_id` remains the final deduplication boundary.

Run the P3-E validation with `scripts/audit-consumer-test.ps1` or `scripts/audit-consumer-test.sh`. Run the P3-F retry/DLQ validation with `scripts/audit-retry-test.ps1` or `scripts/audit-retry-test.sh`. Each creates separate Transactions and Audit databases, a local Kafka KRaft broker, applies both migrations, runs real Kafka/PostgreSQL tests and destroys all temporary resources. The P3-F suite creates three partitions so two consumers can demonstrate actual group distribution.
