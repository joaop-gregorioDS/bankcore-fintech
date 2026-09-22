# P6-F5C-3 — Disposable A+B Capacity Rehearsal

Status: local disposable validation only. This runner never connects to the VPS and does not consume source dumps or backups.

## Local rehearsal result

The full three-scenario run completed all P6-E acceptance cases successfully: healthy A→B, readiness rollback, and smoke-failure rollback. All eight A/B image references remained available by digest through the run. No production data was used.

The fixed F5C-1 evaluation returned **FAIL for this measured disposable profile**, because the 4-vCPU staging cgroup reached approximately 100% CPU busy p95, above the unchanged 85% hard threshold. This is not a definitive finding that the VPS cannot host A+B: Docker-in-Docker/rootless overlay overhead, the host CPU model, and concurrent host noise differ from the VPS, and the VPS observation window was not shown to cover a representative peak. The result is sufficient to withhold a capacity `PASS` and requires further representative evidence or a more equivalent disposable host; thresholds must not be relaxed to change the outcome.

Other measured aggregate points were: staging cgroup peak memory about 7.72 GB of the 15 GiB cap; projected available VPS RAM about 7.24 GB; projected Docker-root free space about 192.0 GB (about 178.8 GiB); projected free inodes about 24.73 million of 24.96 million; projected additional process count 2,464 versus `pid_max` 4,194,304; and zero observed swap I/O. These resource projections do not override the CPU failure.

The profile is also marked incomplete: projected Linux load could not be compared across hosts; F5C-2 was not confirmed to cover production peak; the initial sampler grouped migration activity with startup/readiness; and Docker-in-Docker reported per-container stats whose sums exceeded the target cgroup totals. The runner now rejects those per-container values as unreliable and uses only cgroup aggregate CPU/memory/PIDs for its capacity evidence. No per-service CPU/RSS conclusions should be drawn from this run. A successful three-scenario P6-E run therefore does not change the `FAIL`/incomplete capacity result.

Sanitized aggregate evidence is stored in [`artifacts/p6f5c/rehearsal-summary.json`](../artifacts/p6f5c/rehearsal-summary.json); raw time-series samples and container/image identities are intentionally not retained.

## Inputs and isolation

[`scripts/p6f5c-rehearsal.py`](../scripts/p6f5c-rehearsal.py) consumes the two already-verified P6-D bundles used by P6-E (`release-a/` and `release-b/`). It validates each manifest and CycloneDX SBOM with the existing P6-E manifest contract, requires four digest-pinned images per release, and later confirms all eight immutable image references remain present after the scenarios.

The host runner uses the existing P6-F2 disposable Linux target and its rootless Docker daemon. The target and its nested Docker workload are constrained to **4 CPUs and 15 GiB RAM**, matching or slightly undercutting the observed VPS capacity (4 logical CPUs, 15.61 GiB RAM). The outer local Docker host has 12 CPUs and about 15.53 GiB RAM; its kernel, CPU model, filesystem implementation and concurrent workload are not identical to the VPS. Results therefore remain conditional where these differences matter.

The P6-E release runner performs the existing authenticated-within-the-disposable-stack financial smoke and snapshot flow for three scenarios: healthy A→B, readiness-failure rollback, and smoke-failure rollback. It retains the release images between scenarios. It does not rewrite images or manifests; database volumes and containers are disposable and P6-E teardown checks them after each run. The outer runner removes the disposable target and its temporary target image in `finally`.

No application secrets, environment values, database rows, transaction IDs, container IDs/names, image names/tags, or raw metric samples are included in the final summary. The runner reports low-cardinality Compose service labels and aggregate measurements only.

## Measurements

The sampler runs inside the disposable Linux target at approximately one-second intervals. It records host CPU/load and memory telemetry, cgroup CPU quota/usage, cgroup memory/PIDs, swap deltas, filesystem bytes/inodes, per-service Docker CPU/memory/PID maxima, and periodic aggregate Docker storage summaries.

Measurements are grouped into idle baseline, migration activity, service startup/readiness, readiness validation, healthy steady state, financial smoke, smoke-failure injection, A+B image retention, and A restoration/rollback. Migration activity is tagged only when a migration container is observed running. If a brief phase is missed or any required telemetry is unavailable, the profile is incomplete and cannot produce `PASS`.

The rehearsal intentionally holds a healthy deployment briefly at readiness and steady state so the periodic sampler has time to observe those states. Before the P6-E smoke fault (`exit 97`), it holds healthy B briefly to capture the pre-failure running footprint. The application and fault semantics are unchanged.

## Projection and decision

The runner uses the unchanged P6-F5C-1 thresholds and `evaluate_capacity()` policy. It starts disk budgeting from the F5C-2 minimum available VPS space and subtracts the measured A+B Docker storage footprint, including retained images and disposable persistent-volume growth. It subtracts the staging cgroup's peak incremental memory from the observed VPS minimum available RAM and projects process use from the VPS baseline plus staged cgroup peak growth. The candidate application images are not built in this rehearsal; they are consumed by digest.

The F5C-2 sanitized aggregate is recorded in [`artifacts/p6f5c/vps-baseline.json`](../artifacts/p6f5c/vps-baseline.json). Its peak period was not confirmed representative, so the fixed policy will keep the combined result at least `CONDITIONAL` even if measured resource budgets otherwise fit. Linux load averages from the 12-CPU local Docker host cannot be reliably rescaled to the 4-CPU VPS; missing comparable load evidence also prevents `PASS`. Thresholds are not modified to compensate.

`PASS` means only that the stated disposable profile and available evidence satisfy the capacity policy. It does not authorize a host mutation, production cutover, or override the independent backup/migration/security gates. `CONDITIONAL` means additional representative VPS evidence or closer host equivalence is required. `FAIL` means a fixed hard resource floor was crossed.
