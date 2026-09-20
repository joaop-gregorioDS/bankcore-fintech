# ADR-002 — Transactions Risk Gate

## Status

Accepted for P2-F.

## Context

Pix transfers must be evaluated by the ASP.NET Core Risk Service before they
can create financial ledger effects. The transfer path also needs to preserve
the existing idempotency guarantees under retries and concurrent requests.

## Decision

Transactions processes a Pix transfer in three explicit phases:

1. **Pre-flight:** authenticate the user, verify account ownership and input,
   resolve the exact Pix destination, and derive a stable transaction ID.
2. **Risk:** call `POST /internal/risk/assessments` with a service token whose
   audience is `bankcore-internal`, subject is `service:transactions`, and
   scope is `risk:assess`. This phase does not hold a database transaction or
   account locks.
3. **Ledger:** only an `APPROVED` assessment may enter a new SQLAlchemy
   session/transaction. That transaction locks both accounts, claims the
   scoped idempotency record, writes the ledger transaction and its two
   entries, links the risk metadata, and commits atomically.

The stable transaction ID is UUIDv5 over the server-owned tuple
`user_id + account_id + operation_type + idempotency_key`. Amount and
destination remain part of the canonical request fingerprint, so a changed
payload cannot be accepted as a replay.

The Risk Service is fail-closed: `REVIEW` returns a domain response without a
ledger effect; `REJECTED`, timeout, authentication failure, unavailable
service, malformed response, and other upstream failures do not create a
ledger effect. A retry after a successful Risk assessment reuses the same
transaction ID and idempotency scope.

The `ledger_transactions` table stores nullable `risk_assessment_id`,
`risk_decision`, and `risk_rules_version` columns through the `tx_003`
Alembic migration. There is intentionally no cross-database foreign key.

## Consequences

- Concurrent identical requests converge on one idempotency record, one
  ledger transaction, and two ledger entries.
- A valid Risk assessment may exist without a ledger row when the later ledger
  transaction fails; recovery is handled by a retry using the same stable ID.
- The Risk HTTP call is synchronous for now. Kafka, circuit breakers,
  OpenTelemetry, ML, review queues, and deployment changes remain out of
  scope for P2-F.
- Internal token capabilities are allowlisted by Auth and cached separately by
  audience and scope in Transactions.
