# P6-B — Production-like Bundle

`docker-compose.production.yml` is a release-shaped bundle, distinct from the
development and test Compose overlays. It represents the complete service
topology without publishing internal infrastructure ports:

```text
Nginx → Auth → Transactions → Risk → PostgreSQL
                         └→ Outbox Publisher → Kafka → Audit Consumer → Audit PostgreSQL

Auth → Redis (distributed login rate limiting only)
Services → OTel Collector → Prometheus → Grafana
```

The financial path remains synchronous through Risk and the ledger. Kafka is
only used after the PostgreSQL transaction commits, through the transactional
outbox.

## Release-shaped image contract

The bundle requires `BANKCORE_RELEASE_VERSION` and references the four custom
images with that exact version. It never uses `latest`:

```text
${BANKCORE_IMAGE_REGISTRY:-bankcore.local}/bankcore-auth:${BANKCORE_RELEASE_VERSION}
${BANKCORE_IMAGE_REGISTRY:-bankcore.local}/bankcore-transactions:${BANKCORE_RELEASE_VERSION}
${BANKCORE_IMAGE_REGISTRY:-bankcore.local}/bankcore-risk:${BANKCORE_RELEASE_VERSION}
${BANKCORE_IMAGE_REGISTRY:-bankcore.local}/bankcore-audit:${BANKCORE_RELEASE_VERSION}
```

The production bundle has no `build:` instructions. For local verification,
`docker-compose.production.local.yml` adds build instructions for those exact
image names and adds a disposable verifier profile. This is deliberately a
local builder override, not a registry or deployment workflow.

## Migrations and startup

The migration jobs are finite and ordered. Application services depend on the
corresponding successful migration, so an unsuccessful migration prevents the
release-shaped stack from becoming ready. The jobs are explicit:

1. `migrate-auth`
2. `migrate-transactions`
3. `migrate-risk`
4. `migrate-audit`
5. `kafka-init` creates the versioned event topics

The application containers do not invoke migrations during their own startup.

## Local validation

Use the cross-platform Python runner; it generates disposable JWT keys and
secrets, builds local release-tagged images, starts the bundle, waits for
health/readiness, runs a PIX → Risk → Ledger → Outbox → Kafka → Audit check,
stops observability components to prove the financial path remains available,
and always tears down the project with volumes and orphans removed.

```text
python scripts/p6b-production-bundle.py
```

The runner is intentionally destructive only inside its unique Compose project
and temporary directories. It refuses to use a configured production database
URL because it constructs all database endpoints from the disposable Compose
network.

## Explicit non-goals for P6-B

This phase does not publish images, create a registry, generate SBOMs, sign
images, change the GitHub workflow, provision a VPS, apply Terraform/OpenTofu,
configure remote TLS, or expand backup/restore coverage. Those are separate
decisions in P6-C and later.
