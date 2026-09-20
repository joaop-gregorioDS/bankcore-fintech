# P3-G — End-to-End and Failure Recovery

The disposable P3-G environment validates the complete local path:

```text
Nginx → Transactions → Risk → Ledger + Outbox
                                  ↓
                         Outbox Publisher
                                  ↓
                                Kafka
                                  ↓
                           Audit Consumer
                                  ↓
                            bankcore_audit
```

The financial commit remains synchronous. Kafka is only a propagation mechanism for the committed `transaction.completed.v1` fact.

## Invariants

For an approved PIX transfer the runner verifies:

- one Risk assessment;
- one `ledger_transaction`;
- two balanced ledger entries;
- one outbox event, committed in the same PostgreSQL transaction;
- `published_at` only after Kafka acknowledgement;
- one logical `audit_event`, even when Kafka redelivers the event.

For rejected Risk decisions the runner verifies zero ledger and outbox effects.

## Failure scenarios

The runner deliberately validates:

- Kafka offline after the ledger commit: the outbox remains pending and recovers when Kafka returns;
- publisher crash after Kafka ACK and before `published_at`: the lease expires and a new publisher recovers the event;
- Audit Consumer crash after the audit database commit and before offset commit: redelivery remains one audit effect;
- PostgreSQL outage during the Audit recovery window: the committed Kafka event remains recoverable;
- repeated HTTP idempotency: one ledger, one outbox and one audit effect;
- invalid poison event followed by a valid event: the poison event reaches DLQ and the valid event is audited.

These tests demonstrate **at-least-once delivery plus idempotent processing**, not Kafka exactly-once semantics.

## Running locally

Use `scripts/p3-e2e.ps1` on Windows or `scripts/p3-e2e.sh` on Linux/macOS. The runner generates temporary JWT material, builds its own images, applies Auth, Transactions, Risk and Audit migrations, starts only disposable resources and always removes containers, volumes and networks during teardown.

No VPS, production secret, external database or registry image is used.
