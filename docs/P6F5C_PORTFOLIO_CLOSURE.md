# P6-F5C-5 — Portfolio Capacity Gate Closure

Status: **portfolio demonstration complete**. Production capacity for blue/green coexistence on a representative host remains **NOT PROVEN** and is outside this portfolio stage's scope.

## Decision

BankCore is a portfolio and laboratory project. No additional paid host will be provisioned solely to produce a production-capacity certification. Existing measurements and outcomes are preserved without reinterpretation:

| Stage | Result |
|---|---|
| F5C-1 — Capacity gate design and fixed thresholds | ✅ Demonstrated |
| F5C-2 — Read-only VPS baseline | ✅ `CONDITIONAL`; observation was not confirmed to cover representative peak load |
| F5C-3 — A+B Docker-in-Docker rehearsal | ✅ `FAIL` for that measured profile; CPU p95 was approximately 100%, above the unchanged 85% limit |
| F5C-4a — Native host design/preflight | ✅ Prepared and validated locally |
| F5C-4b — Available environment admission | ⛔ `NOT REPRESENTATIVE`; preflight stopped before Docker activity |
| F5C-4c — Representative host acquisition/admission | ⏳ Not required for portfolio completion; no second paid host will be provisioned |

The `FAIL` is valid for the F5C-3 profile and remains in the record. It does not establish that the production VPS would fail. F5C-4b is `NOT REPRESENTATIVE`, not a capacity failure. No stage produced evidence sufficient to certify production blue/green capacity.

## Portfolio conclusions

The capacity work demonstrated a predeclared resource gate, a read-only baseline process, digest-pinned release rehearsal, fixed thresholds, fail-closed host admission, and stopping deployment qualification when evidence was insufficient. The following distinctions are part of the result:

- P6 deployment and rollback mechanics: demonstrated in disposable environments.
- Backup/restore and migration rehearsal: demonstrated under their recorded test conditions.
- Capacity gate method and evidence-based stop behavior: demonstrated.
- Production capacity certification for A+B coexistence on a representative host: **not proven; outside portfolio scope**.

The exact results, raw evidence retention policy, and F5C-4 host-admission outcome remain documented in [`P6F5C_CAPACITY_GATE_DESIGN.md`](P6F5C_CAPACITY_GATE_DESIGN.md), [`P6F5C_AB_CAPACITY_REHEARSAL.md`](P6F5C_AB_CAPACITY_REHEARSAL.md), and [`P6F5C_NATIVE_HOST_VALIDATION.md`](P6F5C_NATIVE_HOST_VALIDATION.md).

## Lab VPS deployment direction

For a future controlled update of the existing lab VPS, consider a **sequential maintenance-window deployment** instead of requiring full A+B runtime coexistence:

1. Verify a restorable backup and record the accepted release digests.
2. Enter a planned maintenance window and stop the old application stack.
3. Deploy the immutable release by digest and apply the approved forward migrations.
4. Wait for readiness, then run the financial and Audit smoke checks.
5. If acceptance fails, restore the previous release by its recorded digest and use the separately rehearsed recovery procedure for any schema change; do not run an automatic database downgrade.
6. Confirm service recovery and financial invariants before ending maintenance.

This is a proposed lab strategy, not an approved change plan or authorization to access or modify the VPS. It reduces simultaneous application runtime demand, but it does not remove the need to validate backup/restore, migration compatibility, disk for retained images, rollback behavior, maintenance impact, and available host capacity for the chosen release. Those prerequisites require a separately reviewed change plan before any remote mutation.

## Scope boundary

No production-capacity `PASS` is claimed. Thresholds have not been relaxed. No second host was provisioned. No VPS mutation, cutover, or deployment is authorized by this closure.
