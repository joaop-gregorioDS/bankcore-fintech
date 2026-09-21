# P6-B — Production Configuration Contract

This contract describes the configuration boundary for the production-like
bundle in `docker-compose.production.yml`. It is intentionally separate from
the development `.env.example`. The bundle does not create, print, rotate, or
store production secrets.

## Release identity

| Variable | Class | Contract |
| --- | --- | --- |
| `BANKCORE_RELEASE_VERSION` | required non-secret | Immutable release label. It must be supplied explicitly and must never be `latest`. |
| `BANKCORE_IMAGE_REGISTRY` | optional non-secret | Registry/repository prefix. Defaults to `bankcore.local` for local verification only. |
| `GATEWAY_PORT` | public configuration | Host port for the Nginx gateway. Defaults to `8080`. |
| `GATEWAY_BIND_ADDRESS` | public configuration | Bind address for the gateway. Defaults to `0.0.0.0`; production exposure/TLS remains an infrastructure concern. |

The custom application images use the release identity below. The local
override adds `build:` only so a disposable host can build those exact tags;
the production bundle itself contains only versioned image references.

```text
${BANKCORE_IMAGE_REGISTRY}/bankcore-auth:${BANKCORE_RELEASE_VERSION}
${BANKCORE_IMAGE_REGISTRY}/bankcore-transactions:${BANKCORE_RELEASE_VERSION}
${BANKCORE_IMAGE_REGISTRY}/bankcore-risk:${BANKCORE_RELEASE_VERSION}
${BANKCORE_IMAGE_REGISTRY}/bankcore-audit:${BANKCORE_RELEASE_VERSION}
```

## Secrets and sensitive material

The following values are required by the bundle and must come from the future
deployment secret mechanism. They must not be committed to Git, placed in
image layers, or written to logs.

| Variable/path | Class | Use |
| --- | --- | --- |
| `POSTGRES_PASSWORD` | required secret | Auth/Transactions/Risk/Audit PostgreSQL passwords. |
| `JWT_ACTIVE_KID` | required secret-adjacent release input | Selects the active signing key; it is not itself a private key. |
| `JWT_PRIVATE_KEY_FILE` | required secret path | Host path to the mounted Auth private key. |
| `JWT_PUBLIC_KEYS_HOST_DIR` | required public-key path | Host path to the public-key set mounted by Auth, Transactions, and Risk. |
| `AUTH_SERVICE_TOKEN` | required service secret | Internal Auth-to-service authentication. |
| `RATE_LIMIT_KEY_SECRET` | required service secret | Dedicated HMAC secret for opaque Redis rate-limit keys; never reuse JWT keys. |
| `GRAFANA_ADMIN_PASSWORD` | required secret | Grafana local administrative bootstrap value. Anonymous viewer mode remains explicitly configured for the disposable bundle. |

Key material is generated or provisioned outside this bundle. The local
verification runner creates temporary keys in an operating-system temporary
directory and destroys them with the runner environment.

## Required non-secret service configuration

| Variable | Default/contract |
| --- | --- |
| `POSTGRES_USER` | `bankadmin` unless the deployment contract overrides it. |
| `JWT_ALGORITHM` | `RS256`; the production bundle does not support a symmetric fallback. |
| `JWT_ISSUER` | `bankcore-auth`. |
| `JWT_AUDIENCE` | `bankcore-api` for user tokens; the Risk service keeps `bankcore-internal`. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60`. |
| `INTERNAL_TOKEN_EXPIRE_SECONDS` | `60`. |
| `RATE_LIMIT_MAX_ATTEMPTS` | `5`. |
| `RATE_LIMIT_WINDOW_SECONDS` | `900`. |
| `RATE_LIMIT_REDIS_TIMEOUT_SECONDS` | `1.0`. |
| `REDIS_MAXMEMORY` | `64mb`; `noeviction` is fixed by `infra/redis/redis.conf`. |
| `OUTBOX_BATCH_SIZE` | `100`. |
| `OUTBOX_POLL_INTERVAL_SECONDS` | `1.0`. |
| `OUTBOX_LEASE_SECONDS` | `30`. |
| `OUTBOX_PUBLISHER_ID` | `production-publisher`. |
| `MAX_RETRIES` | `3`. |
| `LOCAL_RETRY_ATTEMPTS` | `1`. |
| `PROMETHEUS_PORT` | `19095`, bound to loopback. |
| `GRAFANA_PORT` | `13005`, bound to loopback. |

`DEMO_MODE` is forced to `false` by the production bundle and cannot be
enabled through the production environment contract.

## Internal endpoints and data ownership

These endpoints are Docker-network addresses, not public configuration:

```text
Auth:         http://auth-service:8000
Transactions: http://transactions-service:8001
Risk:         http://risk-service:8080
Kafka:        kafka:9092
Redis:        redis:6379/0
OTLP:         otel-collector:4317
Audit DB:     audit-postgres:5432/bankcore_audit
```

Only Nginx publishes an application gateway port. PostgreSQL, Redis, Kafka,
Risk, Audit, OTLP, Prometheus, and Grafana are not public application
endpoints; Prometheus and Grafana are loopback-only in this local production-
like bundle for verification.

PostgreSQL remains the source of truth for balances, ledger entries,
idempotency, and outbox state. Kafka propagates committed facts. Redis is
reconstructible rate-limit state only. Observability is fail-open for the
financial path: Collector, Prometheus, or Grafana unavailability must not make
the core services unready or roll back a committed operation.

## Readiness and startup contract

The release starts finite migration jobs in this order:

```text
PostgreSQL / Audit PostgreSQL healthy
  → Auth migration
  → Transactions migration
  → Risk EF migration
  → Audit migration
  → Kafka topics
  → application services
```

No application service runs schema migration on its own. A failed migration
blocks the dependent service through `service_completed_successfully`.

Readiness has these semantics:

- Auth, Transactions, and Risk are unready when their PostgreSQL dependency is
  unavailable.
- Redis is deliberately absent from Auth readiness because the local fallback
  protects login when Redis is unavailable.
- Risk is part of the financial dependency chain; Transactions must fail
  closed when a Risk decision cannot be obtained.
- Publisher and Audit Consumer are long-running asynchronous workers. They do
  not make the synchronous ledger commit reversible when Kafka or Audit is
  unavailable; the outbox/retry contract handles recovery.
- Observability services do not gate financial readiness.

## Configuration safety rules

- No secret values, JWTs, personal identifiers, connection strings, or private
  keys may appear in configuration files tracked by Git.
- `.env.example` remains a development aid and is not a production secret
  distribution mechanism.
- The bundle contains no `latest` image reference.
- Formal image digests, release manifests, SBOMs, signatures, registry
  promotion, and secret-manager integration are intentionally deferred to
  P6-C and later.
