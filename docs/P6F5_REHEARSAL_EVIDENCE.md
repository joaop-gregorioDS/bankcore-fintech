# P6-F5A/F5B — Backup, Restore, and Migration Rehearsal Evidence

**Branch:** `p6/live-state-rehearsal`
**Status:** F5A and F5B technically complete on disposable local PostgreSQL copies.
**Scope boundary:** no production mutation, VPS change, commit, push, merge, or capacity test is included in this evidence.

This record contains aggregate results only. It intentionally excludes dump contents, credentials, personal identifiers, account identifiers, transaction identifiers, and connection details. The backup/restore procedure and its safety controls are documented in [`P6F5A_BACKUP_RESTORE_DESIGN.md`](P6F5A_BACKUP_RESTORE_DESIGN.md).

## P6-F5A — Backup and restore

The Auth and Transactions PostgreSQL backup artifacts were restored into the isolated local rehearsal environment. The restore completed without changing the source databases. The baseline used for F5B contained:

| Dataset | Baseline count |
| --- | ---: |
| Auth users | 4 |
| Transactions accounts | 8 |
| Transactions | 18 |
| Ledger entries | 18 |
| Aggregate account balance | 7,787,040 cents |

The backup artifacts themselves are not stored in this repository and must not be committed or attached to repository issues or reviews.

## P6-F5B — Transactions migration rehearsal

The restored Transactions copy was classified as the legacy pre-P0 schema, then migrated through the Alembic head. The final revision was `tx_005_outbox_leases`.

| Invariant after migration | Observed result |
| --- | ---: |
| Accounts | 8 |
| Transactions | 18 |
| Ledger entries | 18 |
| Aggregate account balance | 7,787,040 cents |
| Transactions with zero ledger entries | 9 |
| Transactions with two ledger entries | 9 |
| Idempotency records | 18 |
| Distinct transactions referenced by idempotency records | 18 |
| `DEPOSIT` / `COMPLETED` records | 5 |
| `TRANSFER` / `COMPLETED` records | 13 |
| Historical `risk_assessment_id` values populated | 0 |
| Historical `risk_decision` values populated | 0 |
| Historical `risk_rules_version` values populated | 0 |
| Historical outbox events | 0 |
| Outbox lease columns present at head | `locked_by`, `locked_until` |

The original ledger-entry distribution and aggregate balance were preserved. No historical ledger entries, Risk assessments, or outbox events were synthesized. The legacy PIX transaction was represented in the new idempotency scope as `TRANSFER`.

## Corrections discovered during rehearsal

1. The Transactions preflight now recognizes the legacy `idempotency_key` as protected by either an exact-column UNIQUE constraint or an exact-column UNIQUE index. Missing or non-unique protection remains fail-closed; inconsistent schemas remain `UNKNOWN`.
2. The `tx_002` backfill normalizes legacy `PIX` to `TRANSFER`, matching the current transaction and idempotency semantics. It requires resolved ownership and distinct, non-null source and destination accounts for PIX, and aborts on an idempotency-scope collision after normalization. Unsupported types and other ambiguous contexts still abort before schema changes.

Focused tests cover both corrections, including rejection of invalid PIX account context and normalized-scope collisions. In this consolidation pass, 35 focused tests passed; `py_compile` and `git diff --check` passed. The official `bash scripts/test.sh all` gate was attempted but could not complete because Docker Hub timed out while resolving the pinned Python base-image metadata, before the test containers or test suite started. The full gate must be rerun when the image registry is reachable; F5A/F5B rehearsal evidence is independent of that code-test gate.

## Gate status

| Gate | Status |
| --- | --- |
| P6-F5A — Backup/Restore | Complete |
| P6-F5B — Live-State Migration Rehearsal | Complete |
| P6-F5C — Capacity Gate | Pending |

F5A/F5B completion does not authorize a production migration or VPS operation. F5C remains the next gate; any later production change requires its own reviewed approval and execution plan.
