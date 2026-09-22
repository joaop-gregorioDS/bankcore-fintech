# P6-F5C-1 — Capacity Gate Design

Status: F5C-1 design and synthetic validation ✅; F5C-2 read-only VPS baseline **CONDITIONAL**; F5C-3 disposable A+B rehearsal executed with **FAIL for the measured profile**; F5C-4a native-host design/preflight ✅; F5C-4b **NOT REPRESENTATIVE**. F5C-5 closes the portfolio demonstration. Production capacity for representative-host A+B coexistence remains **NOT PROVEN**; no production-capacity `PASS` is claimed.

## Purpose and stages

The gate decides whether the current BankCore stack (A) and the candidate P6 release (B) can coexist on the same host with operational headroom. It is intentionally not a deployment authorization.

1. **F5C-1 ✅:** define the read-only sampler, evidence contract, conservative thresholds, and synthetic tests.
2. **F5C-2 ✅ / CONDITIONAL:** collect repeated read-only measurements from the VPS. The observed 60-minute window was not confirmed to include a representative production peak, so it cannot establish a capacity `PASS`.
3. **F5C-3 ✅ / FAIL for the measured disposable profile:** combine the VPS baseline with a measured P6 staging profile. The fixed CPU hard limit was exceeded; host non-equivalence and evidence gaps mean this is not a definitive verdict on the VPS itself.
4. **F5C-4a ✅ / F5C-4b NOT REPRESENTATIVE:** native-host admission design was prepared, but the available environment was Windows and failed admission before Docker activity. No representative rehearsal was performed.
5. **F5C-5 ✅ Portfolio closure:** methodology and its stop decisions are complete for the portfolio. F5C-4c representative-host acquisition is not required; production capacity remains not proven and out of portfolio scope.

Even a `PASS` only clears the capacity gate for planning. It does not authorize any VPS mutation or cutover; other F5 blockers remain independent.

## Read-only collection contract

[`scripts/p6f5c-capacity.py`](../scripts/p6f5c-capacity.py) is an opt-in sampler. `--collect` is supported only on Linux with procfs. It reads CPU counters, memory/swap counters, load averages, process count/PID limit, and filesystem/inode availability for `/`, the legacy application path, candidate release path, and Docker root when Docker is available.

Its Docker queries are fixed, direct argument arrays (`shell=False`) limited to server/root metadata, container counts, one-shot resource statistics, image/volume counts, and aggregate Docker storage usage. It does not run `sudo`, accept arbitrary commands, read container environments, inspect application data, or invoke Docker lifecycle/build/pull operations. Container identities are replaced with ordinal labels; image names/tags, volume names, hostnames, environment values, and secrets are not emitted. Failed/unavailable telemetry is reported as unknown rather than treated as zero.

`--evaluate` consumes a separately reviewed, sanitized JSON evidence document. It does not write that document or collect remote data. No evidence file should contain hostnames, IPs, container/image names, credentials, or user/account data.

### Evidence contract

The evaluator schema is `bankcore-p6f5c-evidence-v1`. The assembled evidence must include:

- `observation_minutes` and `sample_count` from a representative host period;
- `representative_peak_period: true` only when the observation includes a normal busy period, not an idle-only window;
- `host`: logical core count, physical memory bytes, PID limit/current process count, and each distinct filesystem backing the Docker root, persistent data, and release storage;
- `projection`: measured staging A+B peak CPU/load, available memory after peak, swap I/O, projected additional process count, remaining bytes and inodes for each filesystem, plus explicit booleans proving migrations, retained A image storage, financial smoke load, digest-pinned images, and off-host image builds were included;
- `staging_profile_complete: true` only after the candidate stack's peak resource profile has actually been observed, including startup/health checks, migrations, normal PIX/Risk/Ledger/Outbox/Audit smoke and rollback overlap.

Where paths share a filesystem, they must be represented once so the remaining-space budget is not double-counted. Docker's aggregate storage summary does not establish per-volume quotas or future growth; if a relevant persistent filesystem or volume budget cannot be accounted for, evidence remains incomplete and cannot pass.

F5C-2 gathered **60 minutes and 13 successful samples** at a cadence no slower than five minutes. The sanitized aggregate is in [`artifacts/p6f5c/vps-baseline.json`](../artifacts/p6f5c/vps-baseline.json). It observed 4 logical CPUs, about 15.61 GiB RAM, minimum available RAM about 13.87 GiB, no swap configured/observed swap I/O, and about 182.67 GiB minimum free space on the Docker-root filesystem. The window was not confirmed as representative peak load; candidate release storage and per-volume quotas were not independently measured. The resulting baseline is **CONDITIONAL**, not a pass.

F5C-3 ran the healthy A→B, readiness rollback, and smoke rollback scenarios using the verified digest-pinned release images in disposable Linux. All three deployment scenarios passed, but the capacity classification for that measured profile was **FAIL**: observed cgroup CPU busy p95 was approximately 100%, exceeding the unchanged 85% hard threshold. The disposable environment used rootless Docker-in-Docker and did not share the VPS CPU model, kernel, storage implementation, or workload; therefore the result must be preserved as-is, must not be generalized into a claim that the VPS itself fails, and still withholds capacity approval. The sanitized aggregate is in [`artifacts/p6f5c/rehearsal-summary.json`](../artifacts/p6f5c/rehearsal-summary.json); methodology and limitations are in [`P6F5C_AB_CAPACITY_REHEARSAL.md`](P6F5C_AB_CAPACITY_REHEARSAL.md).

F5C-4a prepared the native host design and fail-closed preflight. F5C-4b ran only the preflight in the available Windows environment; it returned `NOT REPRESENTATIVE` before any Docker query or lifecycle. Under F5C-5, acquisition of a second paid representative host is not required for portfolio completion. Production blue/green capacity remains **NOT PROVEN**. See [`P6F5C_PORTFOLIO_CLOSURE.md`](P6F5C_PORTFOLIO_CLOSURE.md) for the portfolio decision and proposed sequential lab deployment direction.

## Decision thresholds

The classification is deliberately conservative and uses the worst observed/projection relevant to A+B. Thresholds are initial engineering guardrails, not production SLOs.

| Signal | PASS | CONDITIONAL | FAIL |
|---|---|---|---|
| Evidence duration | ≥60 min and ≥12 samples | shorter/missing | — |
| Projected CPU busy p95 / 5m load per core | ≤70% | >70% through 85% | >85% |
| Projected 1m load per core peak | ≤1.0 | >1.0 through 1.5 | >1.5 |
| Available RAM after A+B peak and migration overlap | ≥max(25% physical RAM, 2 GiB) | below pass floor but ≥max(15%, 1 GiB) | below hard floor |
| Swap I/O during representative peak | none | unavailable/unknown | any observed I/O |
| Remaining bytes on every relevant filesystem | ≥max(25% total, 20 GiB) | below pass floor but ≥max(15%, 10 GiB) | below hard floor |
| Remaining inodes on every relevant filesystem | ≥20% | 10–20% | <10% |
| Projected process use vs `pid_max` | ≤70% | >70% through 85% | >85% |

Missing fields, short observation, incomplete filesystem coverage, unavailable Docker data, unmeasured staging peak, or unproven release/migration/smoke assumptions produce `CONDITIONAL`, never `PASS`. Any hard-limit breach produces `FAIL`. `PASS` requires all rows and required proof flags to be complete.

Memory headroom uses Linux `MemAvailable`, not merely free pages. Swap capacity is not counted as RAM headroom, and swap-in/out activity during the representative peak is a failure signal. The Docker root filesystem budget must include downloaded B images while A images remain available for rollback. Image builds are off-host; host build peaks are not assumed away unless that is the actual deployment contract.

## Interpretation and limits

- Current container resource readings are a point sample. They do not substitute for the repeated host observation or the P6 staging peak profile.
- `docker system df` is aggregate; it cannot alone prove per-volume growth limits. Unaccounted storage is an open gate.
- The F5C result cannot override backup/restore, live-state migration, security, or rollback gates.
- No limits, swap, pruning, image pulls, package changes, service actions, or filesystem changes are permitted as part of measurement.
- No mutation, cutover, or deployment to the VPS has occurred as part of F5C. The thresholds and measured outcomes remain unchanged. A representative-host production-capacity certification is outside this portfolio closure.
