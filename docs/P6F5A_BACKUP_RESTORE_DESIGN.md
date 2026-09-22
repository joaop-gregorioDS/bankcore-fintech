# P6-F5A — Backup/Restore Rehearsal Design

**Execution status:** F5A backup/restore completed against a disposable local target. Sanitized evidence is recorded in [`P6F5_REHEARSAL_EVIDENCE.md`](P6F5_REHEARSAL_EVIDENCE.md).
**Base:** `759d74d6950a8fa902e0429956a507077f817cfd`
**Branch:** `p6/live-state-rehearsal`

## Scope and safety boundary

This stage defines a read-only export of the live Auth and Transactions
PostgreSQL databases and a restore into explicitly disposable, empty PostgreSQL
databases. It does not connect to the VPS, execute `pg_dump`, restore data, run
migrations, or change the current stack. Redis is reconstructible rate-limit
state and is not treated as financial source data. P6-F5B will separately own
the migration rehearsal and deeper financial invariants.

The implementation is [`scripts/p6f5a-rehearsal.py`](../scripts/p6f5a-rehearsal.py).
Its default mode validates a pre-created artifact directory and makes no
database connection. Database operations require both `--execute` and the exact
acknowledgement `I_CONFIRM_READ_ONLY_SOURCE_AND_DISPOSABLE_TARGET`. No password,
URL, DSN or token is accepted as a CLI argument.

## Connection contract

Connections use libpq service aliases from a protected `PGSERVICEFILE`; the
source and target aliases are fixed logical names:

| Logical DB | Read-only source alias | Disposable restore alias |
| --- | --- | --- |
| Auth | `bankcore_source_auth` | `bankcore_rehearsal_auth` |
| Transactions | `bankcore_source_transactions` | `bankcore_rehearsal_transactions` |

Source aliases must resolve to the reviewed database names `bankcore_auth`
and `bankcore_transactions`. Restore database names use the corresponding
rehearsal prefix plus a unique suffix and are checked against the connected
server-side disposable marker.

Credentials are supplied only by a separate `PGPASSFILE`, mode `0600` or
stricter. Both files are checked for regular-file/symlink and permission
issues. The source and restore services must use distinct endpoint tuples
(`host`, `hostaddr`, `port`). The child process receives a minimal environment; `DATABASE_URL`,
`PGPASSWORD`, arbitrary `*_PASSWORD` and other inherited variables are not
forwarded. Commands use argument arrays (`shell=False`), `pg_dump --no-password`
and `pg_restore --no-password`; tool output is captured and never copied into
errors or logs. A service file may contain endpoints and database names but is
rejected if it embeds `password` or `passfile` values.

Execution is refused outside POSIX because Windows mode bits do not prove the
required `0700`/`0600` ACL boundary. The source service must be backed by a
PostgreSQL role that has only the reads needed by `pg_dump` and snapshot queries. Network access is a separate reviewed
precondition (for example, a short-lived SSH tunnel); this utility does not
open SSH sessions, alter tunnels, or invoke a remote shell. The source is never
given a write statement. Dumps use custom format, omit owner/ACL restoration,
and are checked with `pg_restore --list` before use.

## Restore target guardrails

Before creating any dump, the utility checks both restore targets. Each must:

1. use an explicitly named database beginning `bankcore_rehearsal_auth_` or
   `bankcore_rehearsal_transactions_` (matching the service);
2. return the server-side setting `bankcore.environment=disposable`;
3. contain no user tables/schemas that could be overwritten.

The service-file target database name must match the corresponding rehearsal
prefix and unique suffix; the connected database must match it exactly. Any mismatch,
missing marker, populated target, or ambiguous response fails closed. Restore
does not use `--clean`, `--create`, `DROP`, or database lifecycle operations.
It applies only to the marked empty target with `pg_restore --exit-on-error
--single-transaction`, so a failed restore cannot leave a partially committed
database. A failed attempt still requires operator review and secure cleanup of
the isolated artifact directory/target before retry.
No Docker, systemd, VPS, or production-target lifecycle is managed here.

## Artifact handling and evidence

The operator must create a dedicated directory outside the repository before
execution. The directory must be empty, not a symlink, and mode `0700` or
exactly `0700` on POSIX. Dumps are created as `auth.dump` and
`transactions.dump`, set to `0600`, and hashed with SHA-256. A `0600`
`p6f5a-manifest.json` records only UTC creation time, PostgreSQL client version,
logical source alias, restored Alembic revision, file size and checksum. It excludes
connection endpoints, usernames, secrets and row contents. Output reports only
pass/fail and logical service names; database errors are redacted.

`pg_dump --serializable-deferrable` takes a consistent read-only source
snapshot. After restore, the runner verifies that the required core tables
exist and queries known-table row counts/revision on the disposable copy without
printing or persisting row counts. It deliberately does not compare live-source
counts sampled at a different time: concurrent production writes could make
such a comparison race-prone and falsely fail or pass. Archive integrity,
`pg_restore` success and the disposable copy's schema are the F5A evidence;
F5B must separately compare balances and validate ownership, idempotency,
referential integrity and post-migration state. Any exact
source-to-copy count reconciliation must use a shared PostgreSQL snapshot rather
than unsynchronized queries.

F5A does check the restored Transactions copy for orphan ledger/idempotency/
outbox references, unbalanced ledger entries and stuck `PROCESSING`
idempotency records (when those tables exist); all results remain in memory and
only a generic pass/fail is emitted. It also requires the core account/ledger
tables and reads the Alembic revision. This is not a before/after migration
comparison: account balances and detailed ownership/idempotency invariants must
be compared in the F5B isolated migration rehearsal.

The two databases are dumped separately; PostgreSQL does not provide one
atomic snapshot spanning both. These artifacts demonstrate per-database
backup/restore capability, not a cross-database cutover snapshot. Any use as
migration input requires an independently approved write-freeze or other
cross-service consistency/catch-up plan. F5A itself does not freeze writes.

Dumps contain live personal and financial data. They must never be committed,
uploaded to GitHub, attached to an issue/PR, or included in CI artifacts. Keep
them only for the approved rehearsal window, restrict access to the operator,
and securely destroy the dedicated temporary directory and disposable target
after comparison/evidence review. If secure deletion cannot be guaranteed on
the storage medium, use encrypted ephemeral storage and destroy its key. The
checksum is integrity evidence, not encryption or authorization.

## Acceptance and stop conditions

- The source databases remain unchanged; there is no application write freeze
  or cutover in F5A.
- Both dumps are valid PostgreSQL custom archives and have matching manifest
  checksums.
- Both restores succeed only into marked, empty disposable targets.
- The disposable PostgreSQL endpoint is distinct from the source endpoint.
- Restored Auth/Transactions copies expose expected core tables and revisions;
  row counts remain internal and are not logged or persisted.
- No values, secrets, account/customer identifiers or dump contents appear in
  logs or committed artifacts.
- Any missing PostgreSQL utility, permission problem, target ambiguity, data
  mismatch, unsupported revision or cleanup uncertainty is a hard stop.
- Source and disposable target must be configured on distinct PostgreSQL
  endpoints; the actual connected target must match the service-file database
  and server-side environment marker.
- No migration is run in F5A; schema migration and financial invariants belong
  to F5B. No capacity measurement or A+B assessment is made in F5A; that belongs
  to F5C.

## Validation performed in this stage

Local synthetic tests exercise path containment, private permissions, target
identity/server marker, service-file credential rejection and sanitized
manifest validation. No live database credentials or real data are used.
`pytest`/CI remains the official complete test gate; a passing local self-test
does not authorize the live read-only export.
