# P6-F3A — VPS Read-only Preflight Design

**Status:** local design only; no VPS access authorized  
**Baseline:** `f2fc3321cf397e4df076e486ae93d07a9c1736b6`  
**Branch:** `p6/vps-preflight`

## Purpose

This phase defines the first real-host observation step without authorizing
any host mutation. The inventory must produce enough evidence to compare the
actual VPS with the P6-F1/F2 host contract before a change plan is approved.

The report is organized as:

1. **Observed** — values and availability reported by read-only probes;
2. **Expected** — the P6-F1/F2 contract;
3. **Drift** — differences or unverified areas;
4. **Proposed change** — changes to consider, not execute;
5. **Risk** — impact if the drift is real;
6. **Rollback** — how the later mutation would be reversed, or why work must stop.

## Inventory scope

The preflight covers OS/kernel/architecture, CPU/RAM/disk, the `bankcore`
identity and relevant groups, effective SSH configuration, Docker and Compose
versions, rootless signals, containers/images/networks/volumes, listening
ports, Nginx metadata, certificate paths and metadata, firewall state,
filesystem ownership/modes, systemd services/timers, cron paths, mounts,
PostgreSQL/Redis/Kafka process signals, backup metadata and configuration
file names.

Configuration and secret values are not read into the report. The inventory
records only presence, names, ownership, permissions and safe fingerprints if
later added by review. Private-key material, environment values, JWTs,
connection strings and authorization headers are redacted or never queried.

## Read-only safety contract

`scripts/p6f3-readonly-preflight.py` is deliberately constrained:

- subprocess calls use argument arrays, `shell=False`, and a small allowlist;
- shell execution, `sudo`, privilege escalation and command substitution are
  not available;
- mutating verbs such as `rm`, `mv`, `chmod`, `chown`, `systemctl restart`,
  Docker lifecycle operations and firewall changes are rejected;
- the script has no file-writing path, no `--output` option and no Docker
  lifecycle operation;
- command failures are represented as unavailable/unverified probes rather
  than causing a fallback to a mutating command;
- sanitized output is truncated before it is placed in a report.

The script can be reviewed and tested locally now. A future SSH invocation
must run this same read-only program under an explicitly read-only session;
this document does not authorize SSH access to the VPS.

## Port review model

The expected contract is currently:

| Class | Expected values | Decision |
| --- | --- | --- |
| Public gateway | 80/tcp, 443/tcp | confirm against observed gateway |
| Internal financial/data | PostgreSQL, Redis, Kafka, Risk, Audit | must not be public |
| Telemetry | Collector, Prometheus, Grafana | private or explicitly loopback-bound |
| SSH | 22/tcp | inspect actual policy; do not change it here |

The values are a review baseline, not a firewall instruction. The real
inventory decides which listeners exist and which proposed changes require a
separate approval.

## Required change-plan format after inventory

No mutation is authorized by P6-F3A. The next reviewed plan must list each
candidate item with:

| Item | Required detail |
| --- | --- |
| Identity | user/group change, owner, precondition |
| Docker | rootless setup, package/version, validation |
| Filesystem | path, mode, owner, persistence, rollback |
| Network | public/internal ports, firewall rule, rollback |
| Nginx/TLS | config/certificate action, validation, rollback |
| Secrets | injection source, permissions, rotation/recovery |
| Release | digest bundle, `current`/`previous`, migration policy |
| Backup | location, capacity, restore validation |
| Services | systemd/user services, restart policy, rollback |

The plan must be reviewed before any `useradd`, package installation, Docker
lifecycle command, `systemctl` mutation, firewall change, file move, chmod,
chown, DNS/TLS change or deployment.

## Local validation

Run from a Linux environment when available:

```bash
python3 scripts/p6f3-readonly-preflight.py --self-test
python3 scripts/p6f3-readonly-preflight.py > p6f3-report.md
```

The second command is intentionally stdout-only; the repository should not
receive a generated host report or any host-specific artifact. For this
phase, the report command is exercised locally only and does not contact the
VPS.
