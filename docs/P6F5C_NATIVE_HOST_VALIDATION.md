# P6-F5C-4 — Representative Host Capacity Validation

Status: **design prepared; rehearsal not executed**. This stage has no access to the production VPS and does not authorize a VPS mutation or cutover.

## Objective

Replace the F5C-3 Docker-in-Docker measurement with a disposable Linux host whose execution model is closer to the VPS: native Docker/Compose, x86_64, four vCPUs, approximately 16 GiB RAM, and ordinary local storage. The existing F5C-1 thresholds remain unchanged, including the 85% CPU p95 hard limit.

The host must be disposable and isolated. It must not receive production dumps, backups, secrets, or live financial data. The rehearsal consumes only the already verified P6-D A/B bundles and their digest-pinned image references.

## Host admission contract

The preflight in [`scripts/p6f5c-native-preflight.py`](../scripts/p6f5c-native-preflight.py) must run before any image pull or Compose lifecycle. It records only sanitized host facts and rejects an execution profile that cannot be established.

Required facts:

- Linux, x86_64, and a native host kernel;
- exactly four logical CPUs, or an explicitly reviewed profile within the agreed host envelope;
- approximately 16 GiB physical memory, without counting swap as RAM;
- Docker Engine and Compose v2 available through the native local engine;
- no nested Docker-in-Docker indicator and no remote `DOCKER_HOST` endpoint;
- local Docker root and persistent-data filesystems observable with `statvfs`;
- swap I/O counters readable and zero during the representative peak;
- enough free disk/inodes for both digest-pinned A/B images, disposable volumes, migrations, and teardown;
- no production mounts, source-dump paths, or live database connection configuration.

The preflight is fail-closed for unknown host identity, unavailable required telemetry, remote Docker contexts, or an unverified native-engine claim. It never installs packages, changes limits, creates users, changes firewall rules, pulls images, starts containers, or writes system configuration.

## Immutable inputs

Before the rehearsal, the operator must provide two already verified P6-D bundles. The input gate checks both manifests, CycloneDX SBOMs, four images per release, distinct release identities, and `@sha256` references. It does not build, retag, rewrite, sign, or promote an image. No synthetic manifest may replace either real verified bundle.

The disposable host may pull those exact digest references from the registry. Builds are off-host and are not part of the capacity result. The run must fail if any effective Compose image is tag-based or uses `latest`.

## Measurement phases

The native telemetry collector samples approximately once per second and writes only an explicitly requested aggregate evidence file. It uses `/proc`, `statvfs`, cgroup-independent host counters, and read-only Docker queries; it never reads container environments or application data. The runner labels every sample with one of these phases:

1. `baseline_idle`;
2. `image_preparation` (digest pull, if needed);
3. `migrations`;
4. `service_startup`;
5. `readiness_validation`;
6. `financial_smoke`;
7. `steady_state`;
8. `retained_A_B_images`;
9. `rollback_readiness`;
10. `rollback_smoke`;
11. `teardown`.

Migration timing must be captured as its own interval, not inferred from a combined startup phase. The report must retain enough aggregate samples to calculate CPU p95, load per core, available RAM, swap I/O, disk/inodes, PIDs, and Docker storage while both A and B remain available.

## Acceptance and stop rules

The evaluator consumes the same `bankcore-p6f5c-evidence-v1` policy used by F5C-1 through F5C-3. It must not change thresholds after observing results. A missing or non-comparable host metric is `CONDITIONAL`; a fixed hard-limit breach is `FAIL`. Only complete evidence satisfying every existing row can produce `PASS`.

The rehearsal must prove, with synthetic data only:

- A starts and passes migrations/readiness/PIX and Audit smoke;
- B starts from immutable digests and passes the same checks;
- A+B image retention is measured without rebuilding;
- A→B healthy rollout, readiness rollback, and smoke rollback complete;
- no automatic database downgrade occurs;
- financial invariants remain intact in the disposable databases;
- teardown removes temporary containers, networks, volumes, and target-only images.

Any host mismatch, remote engine, missing phase, unavailable telemetry, tag-based image, secret exposure, or residual resource stops the run and prevents a `PASS`.

## Pre-rehearsal checklist

The F5C-4 execution is not ready until all of these are true:

- a disposable Linux host has been created with the admission profile above;
- the preflight report is sanitized and accepted;
- both P6-D bundles are independently verified and available outside the repository;
- no production dump, backup, secret, or live connection string is present on the host;
- the host has sufficient empty disk/inodes for A+B and teardown;
- telemetry output path is outside the repository or explicitly approved as sanitized;
- the existing F5C-1 evaluator and thresholds are unchanged;
- the operator has a teardown plan and a failed-preflight stop condition.

This document and the preflight/collector contracts do not constitute permission to access or alter the VPS.
