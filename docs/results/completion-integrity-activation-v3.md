# Completion Integrity activation v3

- Card ID: `completion-integrity-activation-v3`
- Catalog state: **listed**
- Narrative report: [open](../../reports/2026-08-30-completion-integrity-activation-v3.md)

## Decision

**inconclusive** — The frozen activation protocol was not completed without an integrity failure.

Scope:
- the versioned Completion Integrity activation adapter
- two qualified sacrificial Python and TypeScript roots
- the pinned codex-cli 0.146.0 / gpt-5.6-sol xhigh stack

Reversal trigger: A recomputation mismatch, frozen-binding failure, hidden protocol breach, or larger preregistered pilot contradicts this bounded decision.

## Decision-governing claims

### AEL-CI-ACTIVATION-V3-01 — bounded

The published activation bundle records: The frozen activation protocol was not completed without an integrity failure.

Claim class: `artifact`

Scope:
- exact two-root activation schedule
- versioned owner capture and reporter adapters

Evidence references:
- `ci-activation-v3:observable_chain_complete` — Measurement Set `aggregate`; task-pack roles: `calibration`
- `ci-activation-v3:artifact_or_evaluator_exposure` — Measurement Set `aggregate`; task-pack roles: `calibration`

Falsifier: A frozen recomputation produces a different disposition or any retained raw boundary check contradicts the normalized observation.

## Additional selected claims

These claims disclose supporting workflow or artifact facts; they do not govern the displayed disposition.

### AEL-CI-ACTIVATION-V3-02 — bounded

The published normalized record states: On the exact two roots, B0 produced 0 observed agreements across 0 valid calls; T1 produced 0 observed agreements across 0 valid calls. Ambiguous, invalid, or unrun calls are not counted as disagreements; these are descriptive counts, not an effect estimate.

Claim class: `artifact`

Scope:
- B0 and T1 reporter calls over identical sealed task-level evidence

Evidence references:
- `ci-activation-v3:B0_claim_agreement` — Measurement Set `aggregate`; task-pack roles: `calibration`
- `ci-activation-v3:T1_claim_agreement` — Measurement Set `aggregate`; task-pack roles: `calibration`

Falsifier: The public observations or terminal-claim assessments recompute to different condition counts.

## What was tested

After repairing owner-generated identity and full-wrapper version routing, can Completion Integrity activate once on two fresh qualified Codex roots, and are B0/T1 reporter claims valid and accurate without crossing the evidence-only boundary?

Comparison mode: `controlled_factor`. Study state: `frozen`.

Primary estimand: **exact fresh-root reporter agreement vector** — Record B0 and T1 terminal-claim validity/agreement separately on each fresh sacrificial task root; no population effect is estimated.

Conditions:
- `E0` — Common upstream Codex executor (`control`, `workflow`)
- `B0` — Minimal evidence-only reporter (`baseline`, `prompt`)
- `T1` — Structured requirement-reconciliation reporter (`treatment`, `prompt`)

Task strata:
- `completion-integrity-v3-activation` (`calibration`): batch-ingestion-accounting, subscription-lifecycle-isolation

Decision owner(s): `kizz-ael-maintainer`

## Observed runs, measurements, and cost

Runs: `6`; by status: `invalid=1`, `unrun=5`.

Measurements: `24`; by kind: `aggregate=6`, `cost=12`, `process=6`.

### Repeat and uncertainty evidence

- Repeat coverage: `retained_cell_without_valid_observation` across `6` retained task-condition cells.
- Valid repeats per cell: minimum `0`, maximum `0`.
- Measurement intervals: `not_reported` on `0` measurements.

These are facts about retained observations. The projection cannot infer a completely absent planned cell from Run Records alone. They are not a reliability grade, and planned repeat or perturbation coverage cannot substitute for observed data.

Selected descriptive totals (not stable effects):

- `generated_work_tokens` / `all`: total `6062 tokens` (`cost_or_latency`)
- `wall_time` / `all`: total `119291 ms` (`cost_or_latency`)

## Study design preflight

Status: `conformant_with_warnings`; scope: `design_preflight`.
Assessment as of: `2026-08-30`.

- `design_class`: `calibration`
- `task_validity`: `audited`
- `evaluator_validity`: `calibrated`
- `sampling_strength`: `decision_thresholded_pilot`
- `planned_reliability_coverage`: `single_run`
- `independence`: `maintainer_only`
- `freshness`: `current`

Preflight findings:
- `warning QP-W001` `execution_declaration.repeats_per_cell` — one repeat supports a bounded pilot decision, not stability evidence
- `warning QP-W002` `execution_declaration.order_policy` — non-random order can preserve nuisance effects despite the declared rationale
- `warning QP-W003` `analysis_quality.uncertainty` — effect uncertainty is explicitly not estimable
- `warning QP-W004` `study_ref.independence_claim` — maintainer-only evaluation is not independent replication

Conformance checks declared, hash-bound pre-run design evidence only; they do not prove scientific validity, chronology of execution, replication, transfer, or outcome.

## Decision lifecycle

- admission: `not_declared_historical`
- action: `not_declared_historical`
- outcome_follow_up: `not_declared_historical`
- freshness: `unassessed`

## Replication and independence

- Public graph verification: `decision_recomputable`
- Maintainer rerun: `unavailable`
- Independent replication: `none_linked`
- Evaluation ownership: `maintainer_evaluated`

No independent task selection, evaluation, provider execution, or replication exists.

Maintainer rerun boundary:

The submitted v3 attempt cannot be retried or resumed. Any repaired adapter must use new uncontaminated roots, a new protocol revision, preregistration, raw root, and provider observation.

## Technical evidence

- Receipt: [machine-readable evidence](../../studies/completion-integrity/activation-v3/results/evidence-receipt.json)
- Receipt SHA-256: `4fc7c547ce044a48cf1ab4f6ec6da5866ff927b9d637beb7e0c44beb553cf3b1`
- Receipt evidence state: `structurally_valid`
- Receipt Contract v0 reproducibility field: `not_rerunnable`

The receipt evidence state and reproducibility field are retained Contract v0 compatibility metadata. Neither is a score, a public task-rerun claim, or proof of independent replication.

### Verification boundary

Kind: `frozen_public_bundle`

Validates the public Contract v0 graph, exact freeze, preregistration and frozen-code bindings, the submitted-ambiguous versus unrun projection, all six scheduled states, 24 measurements, and the recomputed protocol-invalid decision. It does not reveal or rerun private tasks, evaluators, candidates, raw events, authentication, or hosted calls, and it is not independent replication.

Command (presentation only; not executed by this generator):

```sh
uv run ael study audit --freeze studies/completion-integrity/activation-v3/freeze.json --result studies/completion-integrity/activation-v3/results --decision-adapter completion-integrity-activation-v1 --require-git-proof
```

Audit status: `passed`.
Contract documents checked: `10`; run records: `6`.


## Materials

- **Activation-v3 result, root cause, and prospective v4 admission decision** — `public`
  - Ref: `docs/decisions/2026-08-30-completion-integrity-activation-v3-result.md` (SHA-256 `0e7b9e0c1a13da5bd829488294e8cd727db9ef6f9ffb11156621db220c96e1ba`)
- **Post-freeze normalization deviation and source binding** — `public`
  - Ref: `studies/completion-integrity/activation-v3/results/normalization-deviation.json` (SHA-256 `c146e5427bc103a40a839fd94c532a136b1b6f278b8657d624254bf1d10b216b`)
- **Private tasks, evaluators, candidate, raw events, and immutable attempt journal** — `withheld`
  - Reason: Exact task fixtures, evaluator code, candidate workspace, Codex events, authentication, and no-retry journal remain in the private evidence boundary.
  - Reproduction impact: A public checkout can recompute the protocol-invalid decision and verify opaque hashes but cannot decide the ambiguous executor outcome or rerun the historical attempt.
- **Hosted model call** — `not_retained`
  - Reason: The public graph retains normalized cost, status, and opaque source hashes rather than a replayable provider service or immutable model revision.
  - Reproduction impact: The exact historical provider behavior cannot be replayed from the repository.
- **Reusable authentication** — `not_collected`
  - Reason: Reusable credentials are excluded from public evidence and release artifacts.
  - Reproduction impact: Public audit requires no credentials; any new hosted observation requires separately authorized authentication.

## Unsupported inferences

- The structured reporter caused a change in claim accuracy.
- Either reporter is reliable on a broader task population.
- The result identifies intrinsic gpt-5.6-sol or Codex quality.
- The workflow transfers to another model, harness, repository, organization, or production environment.
- The result is independently reproduced or externally outcome-verified.

## Limitations

- The frozen design contains only two sacrificial roots and schedules each reporter condition once per root; protocol-invalid execution can leave a submitted attempt ambiguous and later cells unrun.
- Task, evaluator, candidate, event, authentication, and personal-path bytes remain private.
- Maintainer authorship and evaluation overlap; provider state is not immutable or replayable.
- The reporter retained a built-in command tool inside a read-only evidence boundary; it was not tool-free.

## Invalidation triggers

- Any public graph hash, frozen decision count, preregistration ordering, or protected private hash fails verification.
- Any reporter received task artifact, evaluator, executor workspace, intervention, or mutable evidence access.
- A hidden raw event, evaluator repeat, or no-retry journal contradicts the public normalized record.

## Source hashes

- `docs/decisions/2026-08-30-completion-integrity-activation-v3-result.md` — `0e7b9e0c1a13da5bd829488294e8cd727db9ef6f9ffb11156621db220c96e1ba`
- `reports/2026-08-30-completion-integrity-activation-v3.md` — `56f523a069f634fcd210460be0bb6e295e0913d0b5f091e46906437d9aa2e6a9`
- `studies/completion-integrity/activation-v3/freeze.json` — `5cbbfefdcaf48d3c57a5394e72304a080b3cf85a6312a1c69816d4c9d6762f24`
- `studies/completion-integrity/activation-v3/quality-profile.json` — `8ef5a14b27887219c341ff0e64ec53973954ec75c118e8abe2bedf00deda5a13`
- `studies/completion-integrity/activation-v3/results/decision.json` — `e4d9871e29af7145b0f32eb784d61e4ad81ab062c5376342ec1cd4e314fda5ee`
- `studies/completion-integrity/activation-v3/results/evidence-receipt.json` — `4fc7c547ce044a48cf1ab4f6ec6da5866ff927b9d637beb7e0c44beb553cf3b1`
- `studies/completion-integrity/activation-v3/results/freeze-ref.json` — `846a08d4ecb4885b8ecc3c37e7c2cc6977baeb2d2096a97b35dfaaadccfe0b60`
- `studies/completion-integrity/activation-v3/results/measurement-set.json` — `f2af2d2bd68e05630f460df841c142e01aee8b209980a42f77c9542def0eec01`
- `studies/completion-integrity/activation-v3/results/normalization-deviation.json` — `c146e5427bc103a40a839fd94c532a136b1b6f278b8657d624254bf1d10b216b`
- `studies/completion-integrity/activation-v3/results/observations.json` — `85379817d21b01a559435a18571759296431d5ad176bab4357e33a493dd58011`
- `studies/completion-integrity/activation-v3/results/runs/CI3-PY-01-B0.json` — `df9b0e87dc017602736a7963bd12e91a62c8d16fa4ef464316cb83ef16c78289`
- `studies/completion-integrity/activation-v3/results/runs/CI3-PY-01-E0.json` — `37f6f5fa353fd80a032ba3740e1bce81891f6630c967adbbbaea2ad7a0a2adaf`
- `studies/completion-integrity/activation-v3/results/runs/CI3-PY-01-T1.json` — `eaf5bbbf328156f2e822cefd4e5016c62737ae111c73a64dfad99ad84e567ecc`
- `studies/completion-integrity/activation-v3/results/runs/CI3-TS-01-B0.json` — `10f69dbb74de73b14f66e9b34c3b30862fc15cc6ffb053e41f879a675071ffac`
- `studies/completion-integrity/activation-v3/results/runs/CI3-TS-01-E0.json` — `db0a3c2fb3750759253fd7b25e409deb2005a5c95ad75856fe0c835d4c13acd1`
- `studies/completion-integrity/activation-v3/results/runs/CI3-TS-01-T1.json` — `6717c98f380bfef1496700e99c20a47b6864c8c470cb29eb34b5858ee6836ac2`
- `studies/completion-integrity/activation-v3/study-manifest.json` — `2d85747cee2748339f27cc7087f7b0fbc99e1f762bfdde86e6768a901d2dad48`
- `studies/completion-integrity/concept.json` — `1aca3c9b3925293c240e0cdfdd1b2c3590e9c7702d66d00a05244e379e45255f`
- `studies/public-results.json` — `0871a30f7b7057613d05a589641bc5513b8c91fe6fc86a80b6fb88f97081a9ab`

Generated by `agentic-evidence-lab` `0.1.0a13` under `ael.publication-projection/0.6`.
