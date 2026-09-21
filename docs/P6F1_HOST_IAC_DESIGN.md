# P6-F1 — Host and IaC Design

**Status:** local design and static validation only
**Baseline:** `e54eaee7cd9f2ba3418a09357a872cea26bcc066`
**Tag:** `bankcore-p6e-deployment-rollback`
**Branch:** `p6/iac-staging`

This document defines how a disposable or staging Linux host would be prepared
for BankCore. It does not authorize, perform, or validate changes on the real
VPS. No remote inventory, SSH target, DNS, TLS, firewall rule, registry secret,
or production credential is included.

## Decision

Use Ansible for configuration of an existing Linux host. Do not introduce
OpenTofu/Terraform yet: the current phase does not provision a VPS, network,
disk, DNS record, or provider resource. If provider-level resources become
part of scope later, they should be modeled separately from this host role.

The role is intentionally constrained to `disposable` and `staging` modes and
defaults to a local-only inventory. Host package installation, Docker
preflight, and rootless-user lingering are explicit opt-ins.

## Host contract

| Area | Contract |
| --- | --- |
| Host OS | Linux staging/disposable target; distribution-specific package names remain configurable |
| Deploy identity | non-root `bankcore` user and group |
| Docker | rootless Docker mode; Compose v2 plugin required |
| Privilege | Ansible may use `become` during host preparation; application/deployment commands run as `bankcore` |
| Release root | `/opt/bankcore` |
| Release directories | `/opt/bankcore/releases/<release-id>` |
| Configuration | `/opt/bankcore/config`, no secrets committed |
| Secrets | `/opt/bankcore/secrets`, mode `0700`, injected out-of-band |
| Backups | `/opt/bankcore/backups`, owned by the deploy identity |
| Logs/runtime | `/opt/bankcore/logs` and `/opt/bankcore/run` |
| Pointers | `current`/`previous` are deployment-runner state, never created by host provisioning |
| External surface | Nginx only; TLS/firewall are separate infrastructure controls |
| Internal services | PostgreSQL, Redis, Kafka, Risk, Audit, OTel, Prometheus and Grafana stay private |

The role creates directories with explicit modes. It does not create `.env`
files, JWT keys, passwords, service tokens, HMAC secrets, registry tokens or
release pointers.

## Release and rollback boundary

The P6-D manifest is the release identity and the P6-E runner is the rollout
contract. The host role must not rebuild images, resolve mutable tags, or
change `current`/`previous`.

The later deployment step will:

1. obtain a verified manifest and its digest-pinned images;
2. place only non-secret configuration in the release directory;
3. inject secrets from the approved staging mechanism;
4. run ordered migrations under the P6-E expand/contract policy;
5. start the release and run readiness/financial smoke;
6. atomically update `current` and `previous` only after acceptance;
7. restore the previous verified digest on rollback without database downgrade.

## Network and persistence contract

The production Compose bundle already keeps application dependencies on the
Docker network and publishes only the gateway plus loopback observability
ports for local verification. P6-F1 does not change that Compose file.

The future staging firewall plan must allow only the gateway's approved public
ports (normally 80/443) and deny direct access to database, broker, cache,
Risk, Audit and telemetry ports. No firewall rule is applied by this phase.

Persistence classes:

- PostgreSQL/Auth, Transactions, Risk and Audit: financial or audit state;
- Kafka: durable event transport with an explicit retention/backup decision;
- Redis: reconstructible login-rate-limit state only;
- Prometheus/Grafana: operational state, not financial truth;
- `/opt/bankcore/backups`: controlled backup destination for database workflows.

## Secrets boundary

Repository, release manifest, SBOM, image labels/history and provisioning
variables contain no secret values. The future staging deployment must provide:

- `POSTGRES_PASSWORD` and service credentials;
- JWT private/public key material and active `kid`;
- `AUTH_SERVICE_TOKEN`;
- `RATE_LIMIT_KEY_SECRET`;
- registry read credentials if the registry is private;
- Grafana administrative bootstrap value where required.

The exact secret manager/file-injection mechanism is intentionally undecided
until the VPS provider and access model are reviewed. A file-based staging
mechanism must use owner-only permissions and must never be copied into an
image or committed to Git.

## Idempotency and safety rules

- The default inventory is local-only and targets `localhost`.
- Host preparation is safe to repeat: users, groups and directories converge
  to the declared state.
- Docker/package setup is opt-in; P6-F1 validation itself makes no host changes.
- Production mode and pre-set release pointers are rejected by the role.
- No DNS, TLS, firewall, registry, systemd deployment unit or remote volume is
  changed by the P6-F1 role.
- `scripts/p6f-iac-validate.py` performs static checks and Ansible syntax check
  when Ansible is installed. `--require-ansible` makes its absence a failure.

## Planned disposable validation

The next phase, P6-F2, should run this role against a disposable Linux target
or a dedicated local VM/container with the required system capabilities. That
validation must prove:

1. repeated playbook execution produces no unexpected changes;
2. the `bankcore` user owns the declared layout;
3. rootless Docker and Compose are usable by that user;
4. a verified P6-D bundle can be placed without secrets;
5. P6-E migration, readiness, PIX/Audit, upgrade and rollback behavior still
   works;
6. teardown removes only the disposable target and its data.

Because this Windows host has no Ansible executable, the current P6-F1 gate
proves the YAML/contract statically and records the Ansible syntax validation
as pending. No remote host was contacted.

## Review gate before VPS access

Before any real VPS access, review and approve an explicit change plan listing:

- user/group creation and SSH policy;
- packages and Docker installation mode;
- directories, ownership and modes;
- systemd/user services and restart policy;
- public/internal ports and firewall rules;
- TLS/DNS/certificate changes;
- volumes and backup destinations;
- registry access and secret injection;
- release/current/previous paths;
- rollback and recovery commands.

No item in that plan is authorized by this P6-F1 commit.
