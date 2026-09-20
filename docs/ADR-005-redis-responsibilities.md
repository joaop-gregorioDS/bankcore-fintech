# ADR-005 — Redis Responsibilities and Resilience Boundary

## Status

Proposed — P4-A audit, no runtime implementation yet.

## Scope and evidence boundary

This audit covers the repository at commit `4fe03fa` and the local Compose/test
definitions. The VPS, production Redis configuration, production ACLs/TLS and
runtime metrics were deliberately not accessed; those items remain **not
verified**.

## Current Redis inventory

| Area | Current behavior | Data semantics | Classification |
| --- | --- | --- | --- |
| Auth login rate limit | `INCR auth:login:{normalized_tax_id}`; first increment sets a 900-second TTL; values above 15 return `429`; successful login deletes the key | Ephemeral security-control state; loss weakens throttling but does not alter money | **Critical supporting control; reconstructible** |
| Auth Redis outage fallback | Per-process dictionary, 5 attempts per 900 seconds, protected by an async lock; dictionary is cleared above 10,000 entries | Ephemeral local protection; not globally consistent across replicas | **Critical fallback; bounded but degraded** |
| Transactions Redis client | `redis.asyncio` client is created at startup and closed at shutdown; `get_redis` exists, but no production route currently uses it and no Redis key/TTL was found | No current business state | **Dispensable/latent dependency** |
| Transactions internal-token cache | In-process dictionary keyed by `("bankcore-internal", scope)`; expiry is the token lifetime minus five seconds | Reconstructible credential cache; not Redis-backed | **Reconstructible; outside Redis scope** |
| Financial state | Balances, ledger, idempotency, outbox and event delivery state are PostgreSQL/Kafka-owned | Durable authoritative state | **Must never move to Redis** |
| Client-side caches/sessions | Mobile/desktop/browser local caches and session state; not Redis | Presentation/session convenience state | **Not a server Redis responsibility** |

No Redis use was found for balances, ledger entries, financial idempotency,
outbox ownership, Kafka offsets, Pix directory ownership or durable sessions.

## Keys, TTLs and namespaces

The only observed Redis key is:

```text
auth:login:{normalized_tax_id}
```

Its intended TTL is 900 seconds. The key contains the normalized tax identifier
in the Redis key name; this is not emitted by the application logs observed in
the repository, but it is still sensitive operational data and should be
reviewed before a distributed redesign. There is no explicit environment,
version or service namespace beyond the `auth:login:` prefix, and the default
Compose URL uses Redis database `0`.

P4 should define a versioned, environment-scoped namespace and preferably avoid
placing a raw tax identifier in a key. Any new key contract must specify owner,
purpose, schema version, TTL, cardinality expectations and safe invalidation.

## Compose, persistence and health behavior

The main Compose file uses `redis:7.4.1-alpine3.20` with:

- `appendonly yes`;
- named volume `redis_data` mounted at `/data`;
- `restart: unless-stopped`;
- `redis-cli ping` healthcheck;
- no published host port;
- the shared `bankcore_net` bridge network;
- no explicit `maxmemory` or eviction policy;
- no Redis password, ACL or TLS settings in the repository Compose definition.

The container has `no-new-privileges`, but the Redis service does not inherit
the application services' full `cap_drop: ALL` hardening anchor. This is an
observed local configuration fact, not a claim about the VPS.

Auth and Transactions do not declare a Redis health dependency. Auth readiness
checks PostgreSQL only, and Transactions readiness checks PostgreSQL only.
Auth intentionally falls back to a local limiter when Redis fails. Transactions
creates a lazy client without a connectivity probe, and its current Redis
dependency has no observed business effect. The Redis container healthcheck
proves only that the broker answers `PING`; it does not prove the application
contract or rate-limit behavior.

Redis AOF and the named volume allow local restart persistence, but P1-D does
not back up or restore Redis. This is correct for the current financial design:
Redis is not authoritative and its rate-limit state is reconstructible. The
durability behavior of a production Redis instance remains not verified.

## Test and environment usage

The disposable P3 E2E environment starts Redis because it composes the normal
Auth/Transactions stack, but its financial assertions use PostgreSQL, Kafka and
the service APIs. Several migration/unit/integration Compose environments set
`REDIS_URL=redis://unused` and do not start Redis, which is consistent with the
absence of Redis use in those paths. No test currently proves a multi-replica
distributed rate-limit contract.

The development override enables Uvicorn `--reload`; that is an explicit
development-only override and is not part of the production-like base Compose.

## Failure-mode assessment

| Failure | Current result | P4 interpretation |
| --- | --- | --- |
| Redis unavailable during login | Auth applies a local limit of 5/900s per process; global enforcement degrades across replicas | **Mitigated, not distributed** |
| Redis restart/flush | Login counters disappear or are reconstructed locally; users and money remain intact | **Acceptable for ephemeral control; document behavior** |
| Transactions Redis unavailable | Current observed financial path remains PostgreSQL/Kafka-backed; no route uses `get_redis` | **No current financial impact; remove or make optional later** |
| Redis memory pressure | No explicit maxmemory/eviction policy is configured | **Unspecified operational risk** |
| Redis network exposure | No host port in repository Compose; production exposure is not verified | **Locally constrained; production not verified** |
| Redis data corruption/loss | No financial loss by design; rate-limit state is lost | **Acceptable only for current data class** |

The fallback is not fail-open in the narrow sense of unlimited login attempts,
but it is fail-open with respect to a globally coordinated limit: each Auth
replica can apply its own local counter. P4-B must preserve availability while
making this degradation explicit and bounded.

## Proposed P4-A policy

1. PostgreSQL is authoritative for users, accounts, balances, ledger entries,
   idempotency records, outbox records and all durable financial facts.
2. Kafka is authoritative only as the event propagation log for committed facts;
   Redis must not replace Kafka Streams, outbox delivery or consumer state.
3. Redis may provide distributed rate limiting, safe cache-aside data and
   coordination for non-financial work only.
4. Every Redis key must have an owner, versioned namespace, TTL or explicit
   persistence rationale, cardinality bound and documented failure behavior.
5. Redis loss, flush, restart or eviction must not create, delete, duplicate or
   authorize a financial transaction.
6. Financial correctness tests must continue to run with Redis unavailable.
7. No Redis-based distributed lock will be introduced around the ledger where
   PostgreSQL row locking and transactions already provide the required
   correctness.

## P4 backlog proposal

- **P4-B — Distributed rate limiting:** move only the login limiter to a
  versioned Redis key contract, retain a bounded local fallback, define the
  availability/security trade-off, and test single-node and multi-instance
  behavior.
- **P4-C — Safe cache-aside:** identify one non-financial, reconstructible read
  model before adding cache behavior. Do not cache balances as authority or
  cache authorization decisions without an explicit invalidation contract.
- **P4-D — TTL and eviction policy:** set explicit TTLs, namespace/version rules,
  memory limits and eviction behavior; verify that eviction cannot affect money.
- **P4-E — Failure modes:** test offline, restart, flush, timeout and recovery
  with PostgreSQL financial assertions unchanged.
- **P4-F — Redis observability:** add bounded metrics/logging for latency, hit
  rate, limiter fallback and connection failures without logging identifiers or
  credentials.
- **P4-G — E2E and CI:** exercise the Redis contract in disposable Compose and
  GitHub Actions environments; do not add production secrets or VPS access.

## Open decisions before implementation

- Whether the P4-B limiter should hash the tax identifier in the key and which
  environment prefix format to standardize.
- The exact local-fallback budget and whether it should be configurable per
  process without weakening the default.
- Whether the unused Transactions Redis client should be removed or retained as
  an explicitly optional integration seam.
- The memory ceiling and eviction policy for each environment.
- Whether a safe cache-aside candidate exists; if not, P4-C should be closed as
  intentionally unnecessary rather than adding cache complexity.
