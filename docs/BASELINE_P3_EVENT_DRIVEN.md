# BankCore 2.0 — Baseline P3 Event-Driven Architecture

**Baseline commit:** `4fe03fa657cc54246f866f90210eb0d717f02ca9`
**Local tag:** `bankcore-p3-event-driven`
**PR:** [#4 — P3 — Kafka Event-Driven Architecture + Transactional Outbox](https://github.com/joaop-gregorioDS/bankcore-fintech/pull/4)
**Post-merge CI:** [BankCore CI run #13](https://github.com/joaop-gregorioDS/bankcore-fintech/actions/runs/35527575582)

This document freezes the P3 state before Redis-focused work. It is an engineering
baseline, not a production-readiness claim. No VPS, production broker or
production Redis instance was accessed for this baseline.

## Architecture frozen at P3

```text
Client → Nginx → Auth
                  │
                  ▼
             Transactions → Risk → PostgreSQL ledger
                  │                    │
                  │                    └─ committed financial fact
                  ▼
          PostgreSQL transactional outbox
                  │
                  ▼
          Outbox publisher → Kafka KRaft
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
             Audit Consumer             Retry / DLQ topics
             PostgreSQL audit             consumer groups
```

The financial path remains synchronous. Risk approval, the idempotency record,
balances, ledger entries and the outbox row are committed in PostgreSQL before
Kafka is involved. Kafka propagates a committed fact; it does not decide or
reverse a financial operation.

## P3 decisions and delivered capabilities

- `transaction.completed.v1` is an explicit, versioned event contract.
- Event payloads use integer cents and exclude credentials, JWTs, raw Pix keys
  and unnecessary personal data.
- The outbox row is written in the same PostgreSQL transaction as the ledger
  effect and idempotency completion.
- The publisher claims rows with PostgreSQL leases and `FOR UPDATE SKIP LOCKED`,
  publishes with broker acknowledgement and marks `published_at` only after
  acknowledgement.
- Delivery is at-least-once. Acknowledgement/crash windows may produce duplicate
  delivery, so consumers deduplicate by immutable `event_id`.
- The Audit Consumer owns its processed-event state and never writes balances,
  ledger entries or idempotency records.
- Retry and DLQ topics preserve the original event and add only sanitized
  operational headers. Poison events do not block later valid events.
- Kafka runs in an isolated single-node KRaft environment for the local lab;
  ZooKeeper, Schema Registry, Kafka Streams, Kubernetes and multi-broker HA are
  outside this baseline.

## Evidence

The post-merge `main` workflow completed successfully with all ten jobs green:

- quality gates;
- .NET build, tests and EF validation;
- Risk PostgreSQL integration;
- disposable Auth → Risk E2E;
- workflow lint;
- Kafka KRaft smoke;
- transactional outbox and publisher;
- Audit Consumer idempotency;
- Kafka retry, DLQ and consumer groups;
- P3 E2E failure recovery.

The tests cover commit-before-publish, publisher lease recovery, consumer
deduplication, retry/DLQ routing, broker/database failure recovery and the
complete financial-to-audit flow. Warnings emitted by the runner were non-fatal
tooling notices; no production secret or VPS access was used.

## P4 boundary

Redis may accelerate, coordinate or limit. Redis is never the source of truth
for balances, ledger entries, durable financial idempotency, outbox history or
the existence of a committed transaction. PostgreSQL remains authoritative for
financial state, and Kafka remains the propagation mechanism for committed
facts.

The next phase starts with a read-only Redis responsibility audit before any
runtime change. The audit is recorded in
`docs/ADR-005-redis-responsibilities.md` on the P4 branch.
