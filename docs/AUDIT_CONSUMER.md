# P3-E — Idempotent Audit Consumer

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

The consumer validates the versioned envelope, required fields, positive `amount_cents`, fixed producer/type/version and the Kafka message key (`transaction_id`). Invalid JSON, invalid schema and key mismatches never become valid audit rows. DLQ and retry topics are intentionally deferred to P3-F.

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

Run the disposable validation with `scripts/audit-consumer-test.ps1` or `scripts/audit-consumer-test.sh`. It creates separate Transactions and Audit databases, a local Kafka KRaft broker, applies both migrations, runs the E2E/idempotency tests and destroys all temporary resources.
