# ADR-005 — Redis Responsibilities and Resilience Boundary

## Status

Accepted locally — P4-A audit, P4-B distributed login rate limiting and P4-C
Redis operational hardening implemented.

## Scope and evidence boundary

This audit covers the repository at commit `4fe03fa` and the local Compose/test
definitions. The VPS, production Redis configuration, production ACLs/TLS and
runtime metrics were deliberately not accessed; those items remain **not
verified**.

## Current Redis inventory

| Area | Current behavior | Data semantics | Classification |
| --- | --- | --- | --- |
| Auth login rate limit | Atomic Redis Lua increment with first-increment TTL; versioned HMAC-derived key; configurable 5 attempts/900 seconds; successful login deletes the key | Ephemeral security-control state; loss weakens throttling but does not alter money | **Critical supporting control; reconstructible** |
| Auth Redis outage fallback | Per-process dictionary, same configurable budget, protected by an async lock; bounded entry cleanup; Redis connection timeouts | Ephemeral local protection; not globally consistent across replicas | **Critical fallback; bounded but degraded** |
| Transactions Redis client | `redis.asyncio` client is created at startup and closed at shutdown; `get_redis` exists, but no production route currently uses it and no Redis key/TTL was found | No current business state | **Dispensable/latent dependency** |
| Transactions internal-token cache | In-process dictionary keyed by `("bankcore-internal", scope)`; expiry is the token lifetime minus five seconds | Reconstructible credential cache; not Redis-backed | **Reconstructible; outside Redis scope** |
| Financial state | Balances, ledger, idempotency, outbox and event delivery state are PostgreSQL/Kafka-owned | Durable authoritative state | **Must never move to Redis** |
| Client-side caches/sessions | Mobile/desktop/browser local caches and session state; not Redis | Presentation/session convenience state | **Not a server Redis responsibility** |

No Redis use was found for balances, ledger entries, financial idempotency,
outbox ownership, Kafka offsets, Pix directory ownership or durable sessions.

## Keys, TTLs and namespaces

The P4-B Redis key is:

```text
auth:login:v1:{hmac_sha256(rate_limit_key_secret, normalized_tax_id)}
```

Its default TTL is 900 seconds and the default budget is five attempts. The
dedicated HMAC secret is separate from JWT keys, so the Redis key does not
contain the raw tax identifier or a reversible encoding of it. The namespace
is explicitly versioned; the default Compose URL still uses Redis database `0`.

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
- versioned `infra/redis/redis.conf` mounted read-only;
- configurable `maxmemory` defaulting to `64mb`;
- `maxmemory-policy noeviction`;
- AOF with `appendfsync everysec`;
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
absence of Redis use in those paths. P4-B now proves the multi-replica
distributed rate-limit contract in a disposable Compose environment.

The development override enables Uvicorn `--reload`; that is an explicit
development-only override and is not part of the production-like base Compose.

## Failure-mode assessment

| Failure | Current result | P4 interpretation |
| --- | --- | --- |
| Redis unavailable during login | Auth applies a local limit of 5/900s per process; global enforcement degrades across replicas | **Mitigated, not distributed** |
| Redis restart/flush | Login counters disappear or are reconstructed locally; users and money remain intact | **Acceptable for ephemeral control; document behavior** |
| Transactions Redis unavailable | Current observed financial path remains PostgreSQL/Kafka-backed; no route uses `get_redis` | **No current financial impact; remove or make optional later** |
| Redis memory pressure | `noeviction` rejects new writes; Auth catches the Redis error and applies the bounded local fallback | **Explicitly degraded but protected** |
| Redis network exposure | No host port in repository Compose; production exposure is not verified | **Locally constrained; production not verified** |
| Redis data corruption/loss | No financial loss by design; rate-limit state is lost | **Acceptable only for current data class** |

The fallback is not fail-open in the narrow sense of unlimited login attempts,
but it is fail-open with respect to a globally coordinated limit: each Auth
replica can apply its own local counter. P4-B preserves availability while
making this degradation explicit and bounded. Redis connection and command
timeouts prevent an outage from blocking login indefinitely.

## P4-B implementation and evidence

The local implementation adds:

- atomic Redis `INCR` plus first-increment `EXPIRE` through one Lua script;
- `auth:login:v1` HMAC-SHA256 keys using a dedicated required secret;
- configurable attempt budget, window and Redis timeout;
- the existing bounded local fallback, with automatic Redis recovery through
  the normal client reconnect path;
- a disposable Compose environment with two Auth instances and a real Redis
  outage/restart sequence.

The real local validation passed with disposable PostgreSQL, Redis and two Auth
containers: shared limits across instances, 20 concurrent requests with the
expected five allowed and fifteen rejected, TTL expiry, opaque key inspection,
local fallback during Redis downtime, recovery without restarting Auth, and
complete container/volume/network teardown. The official test runner passed
64 tests; the security subset passed 23 tests. No financial or Transactions
behavior was changed by the limiter.

## P4-C implementation and evidence

Redis operational behavior is now versioned in `infra/redis/redis.conf` and
parameterized only where the environment must choose a memory ceiling. The
Compose service publishes no Redis port; its `bind 0.0.0.0` and disabled
protected mode are therefore scoped to the private Docker network. Production
ACL/TLS configuration remains environment-specific and was not verified here.

The disposable P4-C runner validated the configured AOF and `noeviction` policy,
bounded memory pressure with a rejected write, Auth readiness while Redis was
stopped, local protection in both Auth instances during the outage, `FLUSHDB`
state loss without financial state, Redis restart and distributed limiter
recovery. It also checked that Transactions routes do not consume the Redis
dependency. PostgreSQL, ledger, balances, idempotency, outbox and Kafka state
were not placed in Redis and were not modified by this phase.

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

- **P4-B — Distributed rate limiting:** **implemented locally** with a
  versioned HMAC key contract, atomic operation, bounded local fallback,
  timeout/recovery behavior and multi-instance validation.
- **P4-C — Redis operational hardening:** **implemented locally** with a
  versioned config, bounded memory, `noeviction`, AOF continuity semantics and
  failure/recovery validation.
- **P4-D — Dead dependency cleanup:** re-audit Transactions and remove its
  unused Redis client only if the functional boundary remains unchanged.
- **P4-E — Failure modes:** extend tests for offline, restart, flush, timeout
  and recovery with PostgreSQL financial assertions unchanged.
  with PostgreSQL financial assertions unchanged.
- **P4-F — Redis observability:** add bounded metrics/logging for latency, hit
  rate, limiter fallback and connection failures without logging identifiers or
  credentials.
- **P4-G — E2E and CI:** exercise the Redis contract in disposable Compose and
  GitHub Actions environments; do not add production secrets or VPS access.

## Open decisions before implementation

- Whether the unused Transactions Redis client should be removed or retained as
  an explicitly optional integration seam.
- Whether a safe cache-aside candidate exists in a future phase; if not, keep
  cache-aside intentionally out of scope rather than adding cache complexity.
