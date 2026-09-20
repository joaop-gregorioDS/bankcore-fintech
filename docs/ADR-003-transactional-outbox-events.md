# ADR-003 — Transactional Outbox and Financial Events

- **Status:** Accepted — P3-A formalization
- **Date:** 2026-09-20
- **Scope:** Transactions financial facts and future event propagation
- **Depends on:** P2 baseline at `820406a`

## Context

BankCore's financial path is intentionally synchronous:

```text
Client → Transactions → Risk → Ledger
```

The ledger, balances, idempotency record and future outbox record must represent one PostgreSQL transaction. Kafka is an integration mechanism for facts that have already been committed; it is not part of the authorization or financial decision path.

A direct publish to Kafka around the ledger commit would create a dual-write failure window:

- ledger committed, Kafka unavailable → a committed fact could be lost;
- Kafka published, ledger rolled back → consumers could observe a fact that never happened.

## Decision

Use a PostgreSQL Transactional Outbox for events produced by Transactions.

```text
PostgreSQL transaction
├── ledger_transaction
├── ledger_entries
├── balance updates
├── idempotency_record = COMPLETED
└── outbox_event = PENDING
          │ COMMIT
          ▼
Outbox Publisher → Kafka → consumers
```

The first event is `transaction.completed.v1`, defined by [the versioned contract](events/transaction.completed.v1.json).

### Invariants

1. Ledger, balance, idempotency and outbox state are committed atomically.
2. A Kafka outage does not undo or block a committed financial transaction.
3. An outbox row remains pending until the publisher receives a successful broker acknowledgment.
4. Delivery semantics are **at-least-once**, not exactly-once.
5. Duplicate delivery is expected; every consumer must be idempotent.
6. Kafka never writes balances or ledger entries.
7. Kafka never decides `APPROVED`, `REVIEW` or `REJECTED`.
8. Consumers never modify the financial ledger directly.
9. Events contain facts and operational identifiers, not credentials or unnecessary personal data.
10. An incompatible contract change creates a new `event_version`; `v1` semantics are not silently changed.

## Event contract

Envelope fields:

- `event_id`: unique immutable event identity;
- `event_type`: stable semantic name, currently `transaction.completed`;
- `event_version`: integer schema version, currently `1`;
- `occurred_at`: UTC event creation time;
- `producer`: service that committed the fact;
- `correlation_id`: request/workflow correlation identifier;
- `data`: minimized committed transaction facts.

The Kafka message key is `transaction_id`. This preserves ordering for one transaction without claiming global ordering across the topic.

The event intentionally excludes names, email addresses, documents, Pix keys, JWTs, passwords, account balances and database details. Consumers can use the identifiers and their own authorized data sources when additional context is legitimately required.

## Outbox design

The initial logical table is:

```text
outbox_events
├── id UUID PRIMARY KEY
├── aggregate_type
├── aggregate_id
├── event_type
├── event_version
├── payload JSONB
├── occurred_at
├── published_at NULL
├── attempts
└── last_error NULL
```

Recommended constraints and indexes:

- `id` is the immutable event identity and primary key;
- `aggregate_id` is the `ledger_transaction.id`;
- `event_type` and `event_version` are required;
- `payload` must validate against the registered event contract before insertion;
- pending rows are indexed by `published_at`, `occurred_at` and `attempts`;
- `published_at` is set only after broker acknowledgment;
- `last_error` contains operational diagnostics, never secrets or full credentials.

The publisher should claim pending rows with a short database transaction and `FOR UPDATE SKIP LOCKED` (or an equivalent lease) so multiple publisher workers do not block each other. Claiming must not mark an event as published. A failed publish releases or expires the claim, increments `attempts`, records a safe error summary and makes the event eligible for retry.

## Publisher design

The future publisher will:

1. select pending or retry-eligible rows;
2. publish to the versioned topic using `transaction_id` as the message key;
3. wait for the broker acknowledgment;
4. mark `published_at` only after acknowledgment;
5. leave the financial database unchanged if Kafka is unavailable;
6. retry with bounded backoff and expose metrics/logs for pending age and failures.

The publisher is not part of the request path and does not participate in the ledger transaction.

## First consumer: Audit Consumer

The first consumer will be deliberately narrow:

```text
transaction.completed.v1
        ↓
bankcore.audit consumer group
        ↓
consumer-owned audit/processed-events store
```

It must have a unique `processed_event_id` (or equivalent unique constraint on `event_id`). Processing the same `event_id` twice must create one audit effect. The consumer must not update balances, ledger entries or idempotency records.

Notification and analytics consumers are deferred until publisher delivery and consumer idempotency are proven.

## Failure semantics

| Failure | Required behavior |
| --- | --- |
| Kafka unavailable after ledger commit | Money remains committed; outbox row remains pending |
| Publisher process crash before acknowledgment | Row is retried; duplicate delivery is acceptable |
| Publisher crash after acknowledgment before `published_at` update | Row may be published again; consumer deduplication absorbs it |
| Transient consumer failure | Retry according to the later retry policy |
| Repeated consumer failure | Route to a DLQ in a later phase; never discard silently |
| Malformed or incompatible event | Reject/quarantine safely and alert; do not touch the ledger |

## Scope and sequencing

This ADR does not implement Kafka, an outbox migration, a publisher or a consumer. The approved sequence is:

1. **P3-A:** contracts and ADR — this change;
2. **P3-B:** disposable single-node Kafka KRaft infrastructure only;
3. **P3-C:** outbox table and atomic write integration;
4. **P3-D:** idempotent publisher;
5. **P3-E:** Audit Consumer;
6. **P3-F:** retry, DLQ and consumer groups;
7. **P3-G:** E2E and failure recovery;
8. **P3-H:** CI completion.

Kafka remains outside the main Compose stack until the disposable infrastructure is proven. No VPS, production broker or deployment is part of this ADR.
