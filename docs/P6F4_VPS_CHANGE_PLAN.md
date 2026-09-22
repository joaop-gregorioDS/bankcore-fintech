# P6-F4 — VPS Change Plan (Review Draft)

**Status:** planning only; no mutation authorized
**Baseline:** `6fb4e4dc56dc0c16b062e4011fdfd46d9064376e`
**Evidence:** P6-F3B/F3C read-only inventory; observations are not assumed to
cover facts that were not inspected.
**Target:** one-host blue/green transition with the existing stack retained
until the replacement is explicitly accepted.

## Purpose and boundary

This document turns the P6-F3 observations and P6-B/D/E/F1/F2 contracts into
an ordered review plan. It is not an execution runbook. It intentionally
contains no ready-to-run mutation commands, SSH target, secret value, IP
address, private-key material, or authorization to change the host. Every
change below needs its own reviewed execution procedure and explicit approval
before it is performed. This phase does not connect to the VPS.

The legacy stack under `/var/www/bankcore` remains the recovery target while
the candidate stack is prepared under `/opt/bankcore`. Do not convert Docker
rootful to rootless in place, stop the legacy services, or remove `deploy`
privileges during the initial migration.

## Inventory facts and unresolved items

| Observed from P6-F3B/F3C | P6-F1/F2/P6-B/D/E expectation | Planning consequence |
| --- | --- | --- |
| Legacy Auth, Transactions, PostgreSQL, Redis and host Nginx are present; Risk, Kafka, Publisher, Audit and observability are not part of the observed live stack. | Release topology includes those components; internal/data services remain private. | Candidate topology must be capacity-tested and must not be represented as already running on the VPS. |
| Host Nginx serves 80/443 and proxies to loopback 8080; Docker also publishes the old gateway on all IPv4/IPv6 interfaces at 8080. | Only the reviewed public gateway is exposed; host-proxy target is loopback/private. | Keep old 8080 untouched during preparation. Candidate gateway needs a separately selected, collision-checked loopback port; change the proxy only at cutover. |
| Cockpit is associated with TCP/9090 and UFW permits IPv4/IPv6 exposure. | Administrative and application surfaces should be intentionally bounded. | Investigate/decide 9090 separately, after confirming an alternate administration/recovery path. It is not part of the first cutover. |
| Current Docker is rootful; legacy app images use `latest` and writable code bind mounts; restart policy is `unless-stopped`. | Dedicated non-root `bankcore`, rootless Docker, immutable digest releases, explicit release state. | Build and validate a parallel environment. Do not change the live daemon or mounts in place. |
| PostgreSQL and Redis are not published on host ports. | Data services remain private; Redis is reconstructible rate-limit state only. | Preserve the private boundary. Kafka and observability ports must also remain private or loopback-only as explicitly contracted. |
| `.env` metadata was observed as mode `0600`, owned by `deploy`; the legacy config names `JWT_SECRET_KEY`. No values were read. | P6-B requires RS256/key-id and separate service/HMAC secrets; no secrets in repository or image. | Design and inject a separate P6 config. Do not copy or print the legacy values; rotation/compatibility must be separately planned. |
| A valid public TLS certificate was observed; certificate details are intentionally omitted here. | Preserve public HTTPS and certificate lifecycle. | Confirm renewal ownership and test proxy configuration without reading private key material. |
| A BankCore backup was not confirmed in inspected timers, cron and paths. | Cutover requires a verified backup and restore path. | Backup capability is unproven, not absent. This is a hard stop until destination, schedule/ownership and restore validation are evidenced. |
| The previous inventory reported approximately 4 CPU cores and 15.6 GiB RAM; available disk and current utilization are not established by this plan. | Coexistence must fit within measured host capacity with safe headroom. | Re-measure all capacity read-only before provisioning; no adequacy claim is made. |
| The old PostgreSQL contains live Auth/Transactions state. P6-E validated disposable releases and rollback, not migration of this VPS's live financial state into a second database. | Financial state, ledger, idempotency and outbox must survive cutover exactly once. | **Unresolved blocker:** define and test a live-data migration/catch-up and write-freeze/ownership transition. No cutover or dual-writer period until approved. |

## Change register

All steps are proposals. “Execution owner” names the intended mechanism only;
it does not imply that the mechanism is complete, approved, or safe to run on
the VPS. No step has an executable command in this document.

### VPS-01 — Establish verified backup and restore gate

- **Preconditions:** identify authoritative backup scope, destination, access
  boundary, retention, encryption, capacity and recovery owner; confirm a
  recovery console/SSH path. Evidence must distinguish Auth, Transactions,
  Risk, Audit and Kafka state.
- **Proposed action:** inventory existing backup evidence; if insufficient,
  separately design backup coverage and perform a restore rehearsal in an
  isolated target before any host mutation or cutover. Redis rate-limit keys
  are reconstructible and are not financial backup data.
- **Execution owner:** a separately reviewed backup/restore procedure; not the
  P6-F1 host role or this plan validator.
- **Risk:** incomplete, inconsistent, inaccessible or un-restorable backups
  can cause irreversible financial/audit data loss.
- **Validation:** record backup identity, timestamp, scope and integrity
  evidence without exposing dump contents; restore into isolation and compare
  approved financial/audit invariants.
- **Rollback:** no live state is changed by the rehearsal; discard only the
  isolated test target after evidence is retained. If backup verification
  fails, stop and do not proceed.
- **Stop condition:** backup/restore scope is not verified for the data being
  changed.

### VPS-02 — Freeze and preserve the legacy recovery path

- **Preconditions:** VPS-01 passed; read-only baseline refreshed immediately
  before the change window; operator has an independently tested recovery
  channel; no unknown process owns the candidate ports/storage.
- **Proposed action:** retain the old stack, its volumes, Nginx config, TLS
  lifecycle and `deploy` recovery privileges unchanged while the candidate is
  prepared. Establish an approved write-freeze/catch-up procedure for the
  eventual data transition; its exact mechanism remains undecided.
- **Execution owner:** reviewed change-window runbook and operator; no automated
  action is defined here.
- **Risk:** premature service freeze or loss of the old recovery path may
  interrupt service or prevent rollback.
- **Validation:** document the baseline and prove the legacy stack can still
  serve its existing health/smoke checks before candidate work begins.
- **Rollback:** abandon the candidate work and continue on the unchanged legacy
  stack.
- **Stop condition:** old volumes/config or independent access cannot be
  preserved, or the live-data transition remains undefined.

### VPS-03 — Prepare dedicated identity and rootless Docker in parallel

- **Preconditions:** VPS-01 passed; VPS-02 recovery path preserved; distribution,
  UID/GID/subuid/subgid, Docker/Compose versions and rootless prerequisites
  re-observed; resource and port budgets approved.
- **Proposed action:** provision the dedicated non-root `bankcore` identity and
  rootless Docker/Compose environment alongside, not in place of, the current
  rootful daemon. Keep `deploy` as a recovery operator during the stabilization
  period. The existing Ansible role is a host contract; Docker Engine
  installation and all privileged tasks require a separate implementation
  review before use.
- **Execution owner:** reviewed Ansible host-provisioning change based on
  `infra/ansible`; no playbook invocation is authorized by this plan.
- **Risk:** identity-range, socket, lingering or daemon conflicts can affect
  access and resource isolation.
- **Validation:** demonstrate non-root identity, rootless daemon ownership,
  Compose version, socket access and isolation from the old daemon; repeat the
  disposable idempotency evidence on the exact supported OS/version.
- **Rollback:** disable/remove only candidate identity/runtime artifacts using
  a separately reviewed reversibility procedure; leave the legacy daemon,
  containers and data untouched.
- **Stop condition:** candidate rootless Docker cannot coexist safely or
  requires modifying the live daemon.

### VPS-04 — Create the P6 filesystem layout

- **Preconditions:** VPS-03 validated; target paths, filesystem capacity,
  mount options and ownership are reviewed; no existing data at target paths
  would be overwritten.
- **Proposed action:** establish `/opt/bankcore` with the P6-F1 layout:
  `releases/`, `config/`, `secrets/`, `backups/`, `logs/` and `run/`; release
  directories are immutable inputs, while `current`/`previous` remain managed
  only by the P6-E deployment contract after acceptance.
- **Execution owner:** reviewed Ansible role/configuration with explicit
  ownership and modes from P6-F1; no generic recursive permission changes.
- **Risk:** path collision, wrong ownership or insufficient space can expose
  secrets or disrupt the candidate runtime.
- **Validation:** verify ownership/modes against the contract (including
  secrets directory `0700`), mount persistence and capacity; verify no
  `current`/`previous` pointer is created by host provisioning.
- **Rollback:** remove only newly created empty candidate directories after a
  separate review; retain backups and release evidence.
- **Stop condition:** an existing path or mount would be overwritten, or
  ownership/mode cannot be proven.

### VPS-05 — Define and inject the P6 configuration/secrets contract

- **Preconditions:** VPS-03/04 validated; secret source, ownership, rotation,
  recovery and file-mode policy selected; key IDs and service dependencies
  enumerated from P6-B without reusing legacy secret values.
- **Proposed action:** provide RS256 key files with matching active `kid`,
  service token, dedicated rate-limit HMAC secret, database credentials and
  operational bootstrap values through an approved out-of-band mechanism.
  Non-secret configuration is separated under `config/`; secret files are
  restricted under `secrets/`. No secret enters Git, image layers, release
  manifests, shell history or logs.
- **Execution owner:** separately approved secret-provisioning process; the
  precise manager/file delivery method is still a decision gate.
- **Risk:** key mismatch or rotation errors can prevent authentication; leaked
  or reused values can compromise services.
- **Validation:** presence/metadata-only checks, matching `kid` across
  consumers, synthetic auth/service checks and redaction checks; never echo
  secret contents.
- **Rollback:** preserve the legacy config untouched; revert candidate config
  only through an approved secure recovery path and revoke/rotate candidate
  values if exposure is suspected.
- **Stop condition:** secret delivery, ownership or recovery mechanism is
  undefined, or any credential would need to be copied from the legacy `.env`
  without a reviewed rotation plan.

### VPS-06 — Materialize a verified immutable release

- **Preconditions:** VPS-01 passed; VPS-03/04/05 validated; selected release is
  tied to an approved commit and P6-D verification; third-party image identities
  used by the deployment have an explicit digest/integrity policy.
- **Proposed action:** stage the verified release manifest and its
  `image@sha256` references in a versioned release directory. Pull only those
  references; do not rebuild on the VPS or resolve `latest`. Do not place
  secrets in the bundle. P6-D covers the four BankCore-owned images; verify
  external infrastructure image digests separately because P6-D does not
  claim they are all digest-pinned.
- **Execution owner:** reviewed release-materialization procedure using the
  P6-D verifier/manifest contract.
- **Risk:** wrong repository/ref, incomplete package access or mutable external
  dependency can produce an untrusted or incomplete runtime.
- **Validation:** independently verify provenance/signature/SBOM and compare
  every pulled image digest with the approved manifest; inspect bundle for
  secrets and mutable image references.
- **Rollback:** discard only the unactivated candidate release directory and
  retain the prior verified release; never retag/rebuild to simulate rollback.
- **Stop condition:** any image lacks approved identity/integrity evidence or
  any release input is mutable/unverified.

### VPS-07 — Resolve live financial-data migration and ownership

- **Preconditions:** VPS-01 restore evidence exists; owners for all live and
  candidate databases are mapped; a consistent snapshot and write
  freeze/catch-up strategy is designed and tested against a representative
  copy; no dual writer is active.
- **Proposed action:** select and rehearse a one-way transition of live Auth and
  Transactions state into the candidate databases, including ledger,
  balances, idempotency and outbox; define whether Risk/Audit start empty or
  require historical import and how Kafka offsets/events are reconciled. The
  current evidence does not choose between a maintenance-window snapshot/restore
  and a replication/catch-up design.
- **Execution owner:** separate data-migration design and rehearsal, reviewed
  by the financial-data owner. P6-E is not proof of live-VPS data migration.
- **Risk:** lost/duplicated transactions, mismatched balances, replayed events
  or missing audit history.
- **Validation:** compare canonical counts and financial invariants before and
  after rehearsal; prove a single write owner, idempotent catch-up and
  audit/outbox reconciliation; reconcile final snapshot at cutover.
- **Rollback:** before write ownership changes, abandon candidate and keep A;
  after writes are accepted by B, rollback requires a separately designed
  reverse/catch-up or forward-fix strategy. Blindly pointing Nginx back to A
  after B has accepted writes is not safe.
- **Stop condition:** migration/catch-up, dual-write prohibition, data
  ownership or post-write rollback strategy is unresolved. This is currently
  an **open blocker**.

### VPS-08 — Start the candidate stack privately and apply migrations

- **Preconditions:** VPS-01 through VPS-07 passed; candidate ports/network are
  collision-checked; all image digests and external dependencies are pinned or
  explicitly approved; migration compatibility and backup gates are satisfied.
- **Proposed action:** start the P6 production bundle under the rootless
  candidate runtime, reachable only on its private network and a selected
  loopback gateway port. Run the explicit migration jobs in P6-B order; do not
  publish PostgreSQL, Redis, Kafka, Risk, Audit or telemetry ports. Do not
  touch the legacy stack.
- **Execution owner:** reviewed P6-E release/deployment procedure adapted for
  the host; P6-E local runner itself does not authorize remote use.
- **Risk:** resource contention, migration failure, volume mix-up, port
  collision or accidental public binding.
- **Validation:** Compose configuration review, digest identity, migration
  completion, health/readiness for all required services, private-port scan
  from outside the host and loopback-only candidate gateway confirmation.
- **Rollback:** if no candidate financial writes occurred, stop only the
  candidate stack and retain its diagnostics; old stack remains serving.
  Migration rollback is not a downgrade—follow P6-E expand/contract policy.
- **Stop condition:** migration/readiness failure, unexpected public listener,
  resource exhaustion, ambiguous persistent volume, or any required migration
  is destructive/incompatible.

### VPS-09 — Prove capacity and coexistence

- **Preconditions:** VPS-08 candidate starts; fresh read-only CPU/RAM/disk and
  inode baseline collected; approved resource budgets and safety margins
  exist for both stacks together.
- **Proposed action:** run a bounded, representative staging workload while
  both A and B coexist; include PostgreSQL, Kafka, Risk, Audit and observability
  workload, not merely process startup.
- **Execution owner:** reviewed load/soak procedure; no automatic stress
  command is defined here.
- **Risk:** OOM, disk exhaustion, noisy-neighbor impact on A, or degraded
  financial latency.
- **Validation:** record peak/steady CPU, memory, disk, I/O and health; prove
  configured safety headroom and no restart loop or data-service degradation.
- **Rollback:** stop the candidate workload/stack only if it has not accepted
  financial writes; keep A and its storage untouched.
- **Stop condition:** capacity margin is not demonstrated. The earlier estimate
  of 4 CPU cores/~15.6 GiB RAM is not a capacity approval; free disk remains
  unverified until freshly measured.

### VPS-10 — Internal financial and event-flow acceptance

- **Preconditions:** VPS-07 data state reconciled; VPS-08/09 pass; candidate
  secrets are validated; no public cutover has occurred.
- **Proposed action:** perform controlled internal smoke/acceptance through the
  candidate gateway: PIX → Risk → double-entry ledger → idempotency → outbox →
  Kafka → Audit; validate observability is fail-open and do not use real
  customer data for synthetic probes.
- **Execution owner:** reviewed financial acceptance adapter based on P6-E;
  use only approved synthetic accounts/amounts and a bounded, reconciled test
  protocol.
- **Risk:** a test can create durable financial/audit state or exercise the
  wrong database if isolation is misunderstood.
- **Validation:** reconcile transaction, assessment, ledger entries/balances,
  idempotency, outbox publication and Audit; remove no evidence-bearing data
  without an approved retention rule.
- **Rollback:** before candidate accepts production writes, discard the
  candidate and keep A. Any persisted candidate financial write requires data
  reconciliation before abandoning B.
- **Stop condition:** any invariant mismatch, unexpected real data, duplicate
  event, missing Audit or an unapproved persistent test artifact.

### VPS-11 — Switch the host Nginx upstream to the candidate

- **Preconditions:** all prior gates passed; data ownership is singular and
  reconciled; candidate readiness and internal financial acceptance are
  green; reviewed Nginx diff and secure copy of the exact prior config exist;
  TLS renewal and operator recovery paths are known.
- **Proposed action:** change only the reviewed upstream for the BankCore
  virtual host from legacy loopback target to the selected candidate loopback
  target. Validate syntax before reload and use a controlled, separately
  authorized activation. No broad Nginx rewrite or TLS-key access is in scope.
- **Execution owner:** reviewed Nginx change procedure; not an automatic action
  from this document.
- **Risk:** public outage, wrong virtual host/upstream, TLS regression or
  routing to an unready service.
- **Validation:** syntax check, HTTPS health/readiness, controlled PIX/Audit
  smoke and external verification that only intended public ports answer.
- **Rollback:** restore the exact prior upstream/config and revalidate syntax,
  HTTPS and legacy smoke. If B has accepted financial writes, first follow the
  approved data-ownership/catch-up strategy; a proxy flip alone is not safe.
- **Stop condition:** syntax/health/smoke failure, TLS issue, ambiguous write
  ownership or inability to restore the prior config immediately.

### VPS-12 — Restrict the legacy 8080 publication after cutover

- **Preconditions:** VPS-11 is stable through the approved observation window;
  candidate is the only accepted write owner; external and internal clients
  have been checked for direct 8080 dependencies; port ownership is rechecked.
- **Proposed action:** separately remove the legacy all-interface exposure of
  8080 or constrain it to the approved loopback path; do not combine this with
  initial Nginx cutover.
- **Execution owner:** a separately reviewed Compose/network change.
- **Risk:** hidden consumers or health checks may depend on the old binding.
- **Validation:** confirm public probes cannot reach the app directly, host
  Nginx still reaches the intended gateway, and health/PIX smoke pass.
- **Rollback:** restore the reviewed prior binding only if required and only
  while the firewall/Nginx boundary is understood.
- **Stop condition:** an unknown dependency or conflicting port owner remains.

### VPS-13 — Review Cockpit/9090 separately

- **Preconditions:** identify legitimate Cockpit users, access controls,
  provider console and alternate SSH/recovery path; this plan's BankCore
  cutover is stable; collect current firewall state read-only.
- **Proposed action:** decide separately whether to keep, restrict to an
  administrative source/VPN, or disable the public 9090 exposure. Do not
  change it in the BankCore cutover window.
- **Execution owner:** separate host-administration/security change with its
  own approval.
- **Risk:** administrator lockout or reduced emergency recovery capability.
- **Validation:** prove approved administrators retain access and other
  sources cannot reach the service if restriction is chosen.
- **Rollback:** restore the prior access policy through the provider console
  or tested out-of-band recovery path.
- **Stop condition:** no tested alternate administration path or unresolved
  owner of Cockpit.

### VPS-14 — Observe, then retire the legacy stack only by later approval

- **Preconditions:** candidate has passed an agreed observation window and
  financial reconciliation; backup/restore continues to pass; operators accept
  the new recovery path; retention requirements for old volumes/images are
  defined.
- **Proposed action:** after separate review, retire only identified legacy
  containers, mutable images and writable code mounts; consider reducing
  `deploy` sudo/Docker privileges only after `bankcore` recovery has been
  independently proven. Keep legacy data/volumes until retention and rollback
  windows expire.
- **Execution owner:** separate decommissioning plan and authorization.
- **Risk:** destroying the only recoverable data or access path.
- **Validation:** candidate remains healthy; no legacy traffic/dependency is
  observed; backups and restoration are verified; least-privilege access works.
- **Rollback:** restore legacy stack only if its data has not been destroyed;
  once data/volumes are removed, recovery depends on verified backups.
- **Stop condition:** incomplete observation, missing restore evidence, traffic
  still reaches A, or new recovery path unproven.

## Mandatory stop conditions

Stop without applying the next change if any condition below holds:

- backup and restore are not verified for the affected data;
- no independent administrator recovery path exists;
- live financial data migration, write ownership or catch-up is unresolved;
- CPU/RAM/disk headroom for concurrent A+B is not demonstrated;
- image identity, third-party dependency integrity or secrets are unresolved;
- any migration fails, is destructive/incompatible, or requires an unreviewed
  downgrade;
- candidate readiness, internal financial acceptance or Audit reconciliation
  fails;
- any internal service/telemetry port is unexpectedly public;
- Nginx syntax/TLS/health/smoke fails or its prior config cannot be restored;
- an observed fact contradicts the reviewed baseline or a command would have a
  broader effect than the approved individual change.

## Approval gates and current decision

1. Review this plan and resolve the open live-data migration and backup gates.
2. Convert each approved proposal into an exact, separately reviewed change
   procedure with prerequisites, expected diff, validation and rollback.
3. Authorize the first mutation explicitly, naming its single change ID and
   target. Approval of this document alone authorizes none of them.

**Current state:** P6-F4 plan draft only. No SSH, VPS access, deploy, firewall,
Nginx, TLS, identity, package, filesystem, Docker, data or service change was
performed. No first mutation is authorized.
