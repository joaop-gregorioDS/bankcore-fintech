# P6-F2 — Disposable Linux Staging Validation

P6-F2 validates the P6-F1 host contract without contacting a VPS or changing
remote infrastructure. The target is a short-lived Linux container running a
rootless Docker daemon as the non-root `bankcore` user. The target is a test
host, not a BankCore runtime image and is never published.

## Scope

The runner proves:

- Ansible can configure a clean Linux target;
- the second playbook run is idempotent (`changed=0`);
- `bankcore` is non-root and owns the declared `/opt/bankcore` layout;
- the rootless Docker socket is reachable as `bankcore`;
- the disposable environment guard fails closed for `production`;
- verified P6-D bundles can be consumed by the P6-E deployment runner;
- migrations, readiness, PIX, Risk, double-entry ledger, idempotency, outbox,
  Kafka and Audit are exercised by the existing financial acceptance probes;
- A→B rollout, readiness rollback and smoke rollback preserve the financial
  snapshot and remove all temporary Docker resources.

The P6-E scenarios consume the manifests mounted from `--bundles`; the runner
does not rebuild, rewrite, sign, or promote those releases.

## Local command

From the repository root, with Docker Desktop available:

```text
python scripts/p6f-staging.py --bundles C:\path\to\p6e-bundles
```

The bundles must contain `release-a/manifest.json` and
`release-b/manifest.json`, each produced and independently verified by P6-D.
The bundle directory is mounted read-only and should live outside the Git
worktree.

## Safety boundaries

- no VPS, SSH, DNS, TLS, firewall or provider API access;
- no production secrets; P6-E creates ephemeral credentials in the disposable
  target;
- no host PostgreSQL/Redis/Kafka ports are opened by this runner;
- no release is accepted from a mutable tag or rebuilt locally;
- the target container, inner Docker resources and temporary image are removed
  in `finally` even after a failure.

The host-side PowerShell runner is intentionally not used as the evidence
source for the Linux playbook test. The Ansible execution and rootless Docker
checks happen inside the disposable Linux target.

## Local evidence

The disposable run completed with:

- Ansible provisioning run #1: successful;
- Ansible provisioning run #2: `changed=0`;
- non-root user, rootless Docker and filesystem permissions: successful;
- invalid `bankcore_environment=production` guard: rejected before deployment;
- P6-E A→B healthy rollout: successful;
- P6-E readiness rollback: successful, financial snapshot preserved;
- P6-E smoke rollback: successful, financial snapshot preserved;
- financial probes: PIX/Risk/ledger/idempotency/outbox/Audit successful;
- teardown: no P6-F2 container, image, volume or network residue on the host.

The production-like migrations are executed by the verified P6-D images and
the existing P6-E contract. This stage validates host provisioning and its
integration with those artifacts; it does not publish or re-sign releases.
