# Third-party image inventory

This inventory records the current production-like bundle inputs. It is an audit, not a claim that all upstream images are immutable.

| Component | Current reference | Status | Notes |
| --- | --- | --- | --- |
| Python services | `python:3.12.8-slim-bookworm` | tag-only | Auth, Transactions and Audit Dockerfiles; package indexes and apt inputs are also external. |
| Risk build/runtime | .NET SDK and ASP.NET runtime digests | digest-pinned | Risk is the current exception with immutable base references. |
| PostgreSQL | `postgres:16.4-alpine3.20` | tag-only | Auth/Transactions and Audit PostgreSQL. |
| Redis | `redis:7.4.1-alpine3.20` | tag-only | Auth rate-limit state only. |
| Kafka | `apache/kafka:3.9.0` | tag-only | KRaft broker and topic initializer. |
| Nginx | `nginxinc/nginx-unprivileged:1.27.1-alpine` | tag-only | Public gateway. |
| OTel Collector | `otel/opentelemetry-collector-contrib:0.123.0` | tag-only | Telemetry pipeline. |
| Prometheus | `prom/prometheus:v2.55.1` | tag-only | Metrics store. |
| Grafana | `grafana/grafana:11.3.1` | tag-only | Dashboards. |

P6-D publishes and signs only the four BankCore-owned images. It does not silently broaden scope to republish or mutate third-party infrastructure. Converting this inventory to a fully digest-pinned lockfile is a separate supply-chain hardening task.
