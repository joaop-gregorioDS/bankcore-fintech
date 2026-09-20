# BankCore 2.0 — Baseline P2 Risk Service

**Baseline commit:** `820406a`
**Local tag:** `bankcore-p2-risk-service`
**PR:** [#3 — P2 — ASP.NET Core Risk Service + Financial Risk Gate](https://github.com/joaop-gregorioDS/bankcore-fintech/pull/3)
**CI final:** [BankCore CI run #10](https://github.com/joaop-gregorioDS/bankcore-fintech/actions/runs/35513405394)

This document freezes the P2 state before event-driven work. It is a baseline, not a production-readiness claim.

## Architecture

```text
Client
  │
  ▼
Nginx → Auth ───────────────┐
  │                         │ internal RS256 token
  ▼                         ▼
Transactions ────────────→ Risk Service
  │  synchronous assessment     │
  │                            PostgreSQL bankcore_risk
  ▼
PostgreSQL bankcore_transactions
  ├── accounts
  ├── ledger_transactions
  ├── ledger_entries
  └── idempotency_records
```

- Auth owns users, credentials, JWT issuance and the internal Pix directory.
- Transactions owns accounts, balances, idempotency, ledger transactions and ledger entries.
- Risk owns deterministic assessments in its own PostgreSQL database and never writes the Transactions ledger.
- PostgreSQL is the financial source of truth. Redis is used for supporting concerns and is not authoritative for balances or ledger state.
- There is no Kafka, outbox table, publisher or consumer in this baseline.

## P2 decisions frozen

- The financial path remains synchronous: `Transactions → Risk → Ledger`.
- Risk must approve before a Pix transfer can enter the ledger; timeout, invalid response and infrastructure failure fail closed.
- Money crosses the domain boundary as integer cents and is persisted as `BIGINT`.
- Idempotency is owned by the server and scoped by user, account, operation and client key, with a normalized request fingerprint.
- The idempotency record and ledger effect are committed in the same PostgreSQL transaction.
- Concurrent claims are handled through the PostgreSQL uniqueness constraint and deliberate replay/conflict handling.
- Auth and Risk use separate service-to-service RS256 capabilities with issuer, audience, scope and key rotation validation.
- Risk assessments are persisted with their decision, reasons, rules version and request fingerprint.
- Database evolution is migration-based: Alembic for Python services and EF Core migrations for Risk.

## Transaction commit boundary

`services/transactions-service/app/services/ledger.py` creates or replays the idempotency record, locks the relevant accounts in deterministic order, inserts the ledger transaction and entries, updates balances, completes idempotency and calls `db.commit()` as one unit.

The Pix route calls Risk before entering this final ledger transaction. A successful Risk response is therefore a prerequisite, but it is not itself the financial commit. A failure after the Risk call and before the ledger commit can be retried with the same deterministic transaction identity.

The current commit boundary has no durable post-commit notification mechanism. Adding a direct Kafka publish before or inside this transaction would create a dual-write risk and is explicitly out of scope for P3-A.

## CI and evidence

P2 was merged with nine preserved commits, including the CI completion and the E2E portability fix.

- PR #3 checks: quality, .NET build/tests/EF validation, Risk PostgreSQL integration and disposable Auth → Risk E2E all passed.
- The corrected E2E builds Auth, Transactions and Risk in its own job, applies all migrations, validates the full Auth → Nginx → Transactions → Risk → PostgreSQL → Ledger flow, and tears down temporary containers, volumes and networks.
- The post-merge `main` run #10 passed on commit `820406a`.
- No production secrets, VPS access or deployment were used for this baseline.

## Residual risks before P3

- A committed ledger fact has no durable event record to publish after commit.
- There is no retryable publisher, delivery status, consumer group, deduplication store or DLQ.
- There is no event contract or compatibility policy.
- Redis outage/recovery does not affect financial truth, but event delivery cannot currently be recovered because no outbox exists.
- The current system proves synchronous financial integrity, not eventual-consistency behavior or replayable integrations.

## P3-A proposal — Event Architecture & Contracts

P3-A is design and contract work only. It must not add Kafka or change the synchronous financial path.

### First fact

The first event should represent a completed fact, not a request or authorization:

```json
{
  "event_id": "uuid",
  "event_type": "transaction.completed",
  "event_version": 1,
  "occurred_at": "2026-01-01T00:00:00Z",
  "producer": "transactions-service",
  "transaction_id": "uuid",
  "source_account_id": "uuid",
  "destination_account_id": "uuid",
  "amount_cents": 250000,
  "operation_type": "PIX",
  "risk_assessment_id": "uuid",
  "risk_decision": "APPROVED",
  "risk_rules_version": "risk-rules-v1"
}
```

Contract rules:

- `event_id` is globally unique and immutable.
- `event_type` and `event_version` are explicit; incompatible changes require a new version.
- Monetary values use integer cents, never floating point.
- The event contains facts required by consumers, not passwords, JWTs, raw Pix keys, private data or internal database credentials.
- Consumers must not infer authorization from an event; the producer's committed fact is the source context.
- Events are append-only facts. Corrections are new events, not mutation of an old event.
- Correlation and causation identifiers may be added as operational metadata without changing the business payload.

### Transactional Outbox

The intended P3-C design is:

```text
One PostgreSQL transaction
├── ledger_transaction
├── ledger_entries
├── balance updates
├── idempotency_record = COMPLETED
└── outbox_event = PENDING
          │ COMMIT
          ▼
Outbox publisher → Kafka → consumers
```

The outbox row must be created in the same transaction as the financial effect. The publisher may retry delivery, so delivery is at-least-once and consumers must be idempotent. Kafka must never decide whether the ledger transaction is committed.

### Planned phases

| Phase | Scope |
| --- | --- |
| P3-A | ADR, ownership, event envelope and versioned contracts |
| P3-B | Local single-node Kafka in KRaft mode |
| P3-C | PostgreSQL transactional outbox and migration |
| P3-D | Idempotent publisher and delivery status |
| P3-E | Audit consumer |
| P3-F | Notification consumer |
| P3-G | Retry policy, DLQ and consumer groups |
| P3-H | Disposable E2E and CI gates |

Kafka Streams, Schema Registry, Avro, Kubernetes, managed Kafka and multi-broker HA remain outside this initial laboratory scope.
