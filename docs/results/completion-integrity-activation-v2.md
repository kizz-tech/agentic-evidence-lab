# Completion Integrity activation v2

- Card ID: `completion-integrity-activation-v2`
- Catalog state: **listed**
- Narrative report: [open](../../reports/2026-08-15-completion-integrity-activation-v2.md)

## Decision

**inconclusive** — The frozen activation protocol was not completed without an integrity failure.

Scope:
- the versioned Completion Integrity activation adapter
- two qualified sacrificial Python and TypeScript roots
- the pinned Codex CLI 0.146.0 / gpt-5.6-sol xhigh stack

Reversal trigger: A recomputation mismatch, frozen-binding failure, hidden protocol breach, or larger preregistered pilot contradicts this bounded decision.

## Decision-governing claims

### AEL-CI11-R2-01 — bounded

The published activation bundle records: The frozen activation protocol was not completed without an integrity failure.

Claim class: `artifact`

Scope:
- exact two-root activation schedule
- versioned owner capture and reporter adapters

Evidence references:
- `ci11-r2:observable_chain_complete` — Measurement Set `aggregate`; task-pack roles: `calibration`
- `ci11-r2:artifact_or_evaluator_exposure` — Measurement Set `aggregate`; task-pack roles: `calibration`

Falsifier: A frozen recomputation produces a different disposition or any retained raw boundary check contradicts the normalized observation.

## Additional selected claims

These claims disclose supporting workflow or artifact facts; they do not govern the displayed disposition.

### AEL-CI11-R2-02 — bounded

The published normalized record states: On the exact two roots, B0 produced 0 observed agreements across 0 valid calls; T1 produced 0 observed agreements across 0 valid calls. Unrun or invalid calls are not counted as disagreements; these are descriptive counts, not an effect estimate.

Claim class: `artifact`

Scope:
- B0 and T1 reporter calls over identical sealed task-level evidence

Evidence references:
- `ci11-r2:B0_claim_agreement` — Measurement Set `aggregate`; task-pack roles: `calibration`
- `ci11-r2:T1_claim_agreement` — Measurement Set `aggregate`; task-pack roles: `calibration`

Falsifier: The public observations or terminal-claim assessments recompute to different condition counts.

## What was tested

After repairing only the provider-incompatible response-schema boundary exposed by activation v1, can the versioned Completion Integrity capture and reporter boundary activate on two qualified sacrificial Codex task roots, and is the structured reporter accurate on both roots without being descriptively worse than the minimal reporter?

Comparison mode: `controlled_factor`. Study state: `frozen`.

Primary estimand: **exact two-root reporter agreement vector** — Record B0 and T1 terminal-claim agreement separately on each frozen sacrificial task root; the vector is descriptive and is not a population-effect estimate.

Conditions:
- `E0` — Common upstream Codex executor (`control`, `workflow`)
- `B0` — Minimal evidence-only reporter (`baseline`, `prompt`)
- `T1` — Structured requirement-reconciliation reporter (`treatment`, `prompt`)

Task strata:
- `completion-integrity-v2-activation` (`calibration`): explicit-multipart-cli-contract, code-schema-cli-docs-sync

Decision owner(s): `kizz-ael-maintainer`

## Observed runs, measurements, and cost

Runs: `6`; by status: `invalid=1`, `unrun=4`, `valid=1`.

Measurements: `24`; by kind: `aggregate=6`, `cost=12`, `process=6`.

### Repeat and uncertainty evidence

- Repeat coverage: `retained_cell_without_valid_observation` across `6` retained task-condition cells.
- Valid repeats per cell: minimum `0`, maximum `1`.
- Measurement intervals: `not_reported` on `0` measurements.

These are facts about retained observations. The projection cannot infer a completely absent planned cell from Run Records alone. They are not a reliability grade, and planned repeat or perturbation coverage cannot substitute for observed data.

Selected descriptive totals (not stable effects):

- `generated_work_tokens` / `all`: total `14418 tokens` (`cost_or_latency`)
- `wall_time` / `all`: total `212947 ms` (`cost_or_latency`)

## Study design preflight

Status: `not_assessed_current`; scope: `design_preflight`.

- `design_class`: `not_assessed_current`
- `task_validity`: `not_assessed_current`
- `evaluator_validity`: `not_assessed_current`
- `sampling_strength`: `not_assessed_current`
- `planned_reliability_coverage`: `not_assessed_current`
- `independence`: `not_assessed_current`
- `freshness`: `not_assessed_current`

Activation v2 was prospectively frozen, but no preregistered Study Quality Profile governed it. No retrospective design certification is inferred from the completed run.

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

The submitted v2 schedule cannot be retried or resumed. Any repaired adapter must create a new protocol revision, preregistration, raw root, and provider observation.

## Technical evidence

- Receipt: [machine-readable evidence](../../studies/completion-integrity/activation-v2/results/evidence-receipt.json)
- Receipt SHA-256: `b29ffd2ccc9aec0156b0218244ddc015c33c607f7afad4725a23c1651a2f3f13`
- Receipt evidence state: `structurally_valid`
- Receipt Contract v0 reproducibility field: `not_rerunnable`

The receipt evidence state and reproducibility field are retained Contract v0 compatibility metadata. Neither is a score, a public task-rerun claim, or proof of independent replication.

### Verification boundary

Kind: `frozen_public_bundle`

Validates the public Contract v0 graph, exact freeze and preregistration bindings, all scheduled terminal and unrun states, normalized measurements, and the recomputed protocol-invalid decision. It does not reveal or rerun private tasks, evaluators, candidates, raw events, authentication, or hosted calls, and it is not independent replication.

Command (presentation only; not executed by this generator):

```sh
uv run ael study audit --freeze studies/completion-integrity/activation-v2/freeze.json --result studies/completion-integrity/activation-v2/results --decision-adapter completion-integrity-activation-v1 --require-git-proof
```

Audit status: `passed`.
Contract documents checked: `10`; run records: `6`.


## Materials

- **Alpha.11 activation result and post-run publication repair decision** — `public`
  - Ref: `docs/decisions/2026-08-15-alpha11-activation-result.md` (SHA-256 `19d4f8eed11112bc25c1ba289f3bff4c7a5567769f4c5351237bdda12725cd0e`)
- **Private tasks, evaluators, candidates, raw events, and attempt journals** — `withheld`
  - Reason: Exact task fixtures, evaluator code, candidate workspaces, Codex events, terminal assessments, and no-retry journals remain in the private evidence boundary.
  - Reproduction impact: A public checkout can recompute the protocol-invalid decision and verify opaque hashes but cannot reconstruct the wrapper-level causal diagnosis or rerun the historical cells.
- **Hosted model calls** — `not_retained`
  - Reason: The public graph retains normalized run records rather than a replayable provider execution service or immutable model revision.
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

- The frozen design contains only two sacrificial roots and schedules each reporter condition once per root; protocol-invalid execution can leave cells unrun.
- Task, evaluator, candidate, event, authentication, and personal-path bytes remain private.
- Maintainer authorship and evaluation overlap; provider state is not immutable or replayable.
- The reporter retained a built-in command tool inside a read-only evidence boundary; it was not tool-free.

## Invalidation triggers

- Any public graph hash, frozen decision count, preregistration ordering, or protected private hash fails verification.
- Any reporter received task artifact, evaluator, executor workspace, intervention, or mutable evidence access.
- A hidden raw event, evaluator repeat, or no-retry journal contradicts the public normalized record.

## Source hashes

- `docs/decisions/2026-08-15-alpha11-activation-result.md` — `19d4f8eed11112bc25c1ba289f3bff4c7a5567769f4c5351237bdda12725cd0e`
- `reports/2026-08-15-completion-integrity-activation-v2.md` — `e6fbdf2b10721b47333b6ed6098a6fed0cf529ef1693e7d1fdeb8c1143ada920`
- `studies/completion-integrity/activation-v2/freeze.json` — `e373f3325c6e9551889072a735f24ba51fe8621c9a822f9c9829188358a9200d`
- `studies/completion-integrity/activation-v2/results/decision.json` — `9d523357cec051c311e2409ce0e1ef6ec0588b959fc376cf1205088a0a4f04aa`
- `studies/completion-integrity/activation-v2/results/evidence-receipt.json` — `b29ffd2ccc9aec0156b0218244ddc015c33c607f7afad4725a23c1651a2f3f13`
- `studies/completion-integrity/activation-v2/results/evidence-receipt.md` — `1af354f8973978da22a55269298c833cb3d5dd372359b638d2e4905c31408a77`
- `studies/completion-integrity/activation-v2/results/freeze-ref.json` — `0865b3c9765fd0516f2961069943d49c3ada38fc2173469ca224b5af92c56da0`
- `studies/completion-integrity/activation-v2/results/measurement-set.json` — `0b03be59c4ef5a2ffac067388ff4186f05428742c446ce7b1c71e52c89d2ae04`
- `studies/completion-integrity/activation-v2/results/observations.json` — `c22b63d09dc64c48c993068273bb300692cc773ef38ddcb83b714335287bc262`
- `studies/completion-integrity/activation-v2/results/runs/CI2-PY-01-B0.json` — `8357c2cab853782e39e6d60a4e276ddc4231b33bd431c0aeb84597382635042d`
- `studies/completion-integrity/activation-v2/results/runs/CI2-PY-01-E0.json` — `386d60ecd8a4cda5c69b076935d0e3d4653ff91b5239a41b0894ecb61462bfb0`
- `studies/completion-integrity/activation-v2/results/runs/CI2-PY-01-T1.json` — `32c8fcad68a2b3eed1dcf3f8bf3052a145f2dde660683bb371450e43cd857e17`
- `studies/completion-integrity/activation-v2/results/runs/CI2-TS-01-B0.json` — `936205d3392b8a6344e2f6877c8d75a0fcb3ed2a9edc90ea923c33607e7e528e`
- `studies/completion-integrity/activation-v2/results/runs/CI2-TS-01-E0.json` — `f95b10bd7a904b22299d41a22f597368a634ee1d84ff9479343a1902ed6445dc`
- `studies/completion-integrity/activation-v2/results/runs/CI2-TS-01-T1.json` — `73779151797208b4cf83443f80318e6cbe28d5c2953c8f67f80d70b9cc1b176f`
- `studies/completion-integrity/activation-v2/study-manifest.json` — `e8eb6d3056b766e2440e121472ebd5ff89a4079dc641688959c80691832f081a`
- `studies/completion-integrity/concept.json` — `1aca3c9b3925293c240e0cdfdd1b2c3590e9c7702d66d00a05244e379e45255f`
- `studies/public-results.json` — `fb0971a699faee0b35f602bbfd93860ae181a6b55c28c90ceed57131132ae5be`

Generated by `agentic-evidence-lab` `0.1.0a13` under `ael.publication-projection/0.6`.
