# P6-E — Deployment and Rollback Contract

P6-E defines a local/staging deployment contract without contacting the VPS.
The runner consumes only a P6-D manifest that has already passed the GHCR,
SBOM, provenance and Cosign verification workflow:

```text
verified P6-D manifest A/B
        ↓
preflight and Compose config
        ↓
ordered migrations
        ↓
digest-pinned rollout
        ↓
readiness
        ↓
financial smoke/E2E
        ↓
current release pointer
```

The runner is `scripts/p6e-deploy-rollback.py`. It uses the production Compose
file directly and writes a temporary override containing the four verified
`image@sha256:...` references. It never uses the local production builder
overlay, never rebuilds an application image, and never changes a manifest.

## Release identity and rollback

The disposable deployment keeps `current` and `previous` release identities
(release plus Git commit) in an atomically replaced JSON pointer file. Pass
`--state-dir` to retain that pointer in a local staging directory; otherwise it
is temporary and is removed with the disposable run. A candidate becomes current only
after migrations, readiness, image-identity checks and the financial smoke
command pass. If readiness or smoke fails, the runner reapplies the previous
verified manifest, checks readiness again and compares the financial snapshot
before and after rollback.

The snapshot command must print a canonical representation of financial state
(for example ordered transaction, ledger-entry, balance, outbox and
idempotency rows). It must not print credentials, tokens, personal data or
connection strings. A health-only run is available for structural diagnostics,
but it is explicitly not a financial acceptance run.

Example, with two verified P6-D bundles already downloaded locally:

```text
python scripts/p6e-deploy-rollback.py \
  --release-a release-a/manifest.json \
  --release-b release-b/manifest.json \
  --smoke-a "python scripts/p6e-smoke-adapter.py" \
  --smoke-b "python scripts/p6e-smoke-adapter.py" \
  --snapshot-command "python scripts/p6e-financial-snapshot.py" \
  --failure-mode readiness
```

The actual adapter is intentionally external to the deployment engine so that
the deployment code cannot manufacture a passing financial result. In the
BankCore disposable environment it should invoke the existing PIX → Risk →
Ledger → Outbox → Kafka → Audit E2E and query the three PostgreSQL stores.

## Migration safety

Automatic rollout accepts additive/expand changes only. The runner examines
the `upgrade`/`Up` sections of the Alembic and EF migration sources and blocks
destructive table, column or index operations. `downgrade`/`Down` methods are
not treated as automatic production actions. Destructive changes require a
separate expand/contract phase with an explicit review and backup plan.

The existing Compose dependency graph is the migration order:

1. Auth
2. Transactions
3. Risk
4. Audit

The finite jobs must exit successfully before the long-running services are
accepted as ready.

## Failure scenarios

The disposable runner supports controlled validation of:

- candidate readiness failure (`--failure-mode readiness`);
- candidate smoke failure (`--failure-mode smoke`);
- restoration of the previous release;
- preservation of the financial snapshot;
- teardown of containers, volumes and Compose orphans.

`--failure-command` is only a local test fault injection. There is no remote
deployment, SSH, TLS/firewall change, production secret, registry push or VPS
access in P6-E.
