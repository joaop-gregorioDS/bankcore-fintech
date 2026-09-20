# P3-D — Outbox Publisher

The publisher is a separate process from the Transactions API. It reads committed rows from `outbox_events`, claims them with a short PostgreSQL lease, publishes the stored payload to Kafka and marks the row only after the broker acknowledges the message.

## Delivery contract

- Topic: `bankcore.transaction.completed.v1`
- Message key: `transaction_id` stored in `message_key`
- Producer acknowledgment: `acks=all` with Kafka producer idempotence enabled
- Delivery semantics: at-least-once
- `published_at`: set only after a successful broker acknowledgment
- Failed delivery: `attempts` is incremented, the event remains pending and `last_error` stores a sanitized bounded summary

The publisher never rebuilds an event from ledger, accounts or Risk. The JSON payload already persisted in the outbox is the historical fact that is transported.

## Claim and lease

Claiming uses `SELECT ... FOR UPDATE SKIP LOCKED` in a short transaction. The transaction writes `locked_by` and `locked_until`, then commits before any Kafka I/O. A crashed publisher therefore leaves a lease that can expire and be claimed by another instance.

There is an intentional crash window after Kafka acknowledgment and before `published_at` is committed. The event may be delivered again with the same `event_id`; later consumers must deduplicate it.

## Configuration

```text
KAFKA_BOOTSTRAP_SERVERS
KAFKA_TOPIC
OUTBOX_BATCH_SIZE
OUTBOX_POLL_INTERVAL_SECONDS
OUTBOX_LEASE_SECONDS
OUTBOX_PUBLISHER_ID
```

The isolated local validation is run with `scripts/outbox-publisher-test.ps1` or `scripts/outbox-publisher-test.sh`. It starts only disposable PostgreSQL and Kafka resources, applies the Transactions migrations, runs real PostgreSQL/Kafka publisher tests and removes all containers, volumes and networks afterward.

Consumers, retry topics, DLQ, Schema Registry and production deployment are intentionally outside P3-D.
