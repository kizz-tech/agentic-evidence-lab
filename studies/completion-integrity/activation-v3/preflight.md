# Study Quality Preflight: kizz:ael:quality-profile:completion-integrity-activation-v3:1

- Study: `kizz:ael:study:completion-integrity-activation-v3` revision `3`
- Assessed at: `2026-08-30`
- As of: `2026-08-30`
- Status: **conformant_with_warnings**
- Scope: `design_preflight`

## Quality axes

- `design_class`: `calibration`
- `task_validity`: `audited`
- `evaluator_validity`: `calibrated`
- `sampling_strength`: `decision_thresholded_pilot`
- `reliability_coverage`: `single_run`
- `independence`: `maintainer_only`
- `freshness`: `current`

## Findings

- **warning QP-W001** `execution_declaration.repeats_per_cell` — one repeat supports a bounded pilot decision, not stability evidence
- **warning QP-W002** `execution_declaration.order_policy` — non-random order can preserve nuisance effects despite the declared rationale
- **warning QP-W003** `analysis_quality.uncertainty` — effect uncertainty is explicitly not estimable
- **warning QP-W004** `study_ref.independence_claim` — maintainer-only evaluation is not independent replication

## Boundary

Conformance checks declared, hash-bound pre-run design evidence only; they do not prove scientific validity, chronology of execution, replication, transfer, or outcome.
