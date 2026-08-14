# Property-based Testing v2

- Card ID: `property-based-testing-v2`
- Catalog state: **listed**
- Narrative report: [open](../../reports/2026-08-12-property-based-testing-v2.md)

## Decision

**reject** — S1 did not meet the frozen selection or confirmation rule on this pilot surface.

Scope:
- the exact frozen PBT v2 serialization and normalization tasks
- Codex CLI 0.146.0 with gpt-5.6-sol at xhigh effort
- preregistration commit 610f0d9e1e19d9c89dd6beba8fab7900222df5dd

Reversal trigger: Re-evaluate after any intervention, task, evaluator, runtime, model, prompt, budget, or provider-behavior change.

## Decision-governing claims

### AEL-PBT-V2-01 — contradicted

S1 changed hidden-edge acceptance enough to satisfy the frozen terminal rule on the exact pilot cells.

Claim class: `factor_causal`

Scope:
- exact matched serialization and normalization pilot cells

Evidence references:
- `hidden_acceptance:P-S01:B0:R01` — Measurement Set `outcome`; task-pack roles: `screening`
- `hidden_acceptance:P-S01:S1:R01` — Measurement Set `outcome`; task-pack roles: `screening`
- `hidden_acceptance:P-S02:B0:R01` — Measurement Set `outcome`; task-pack roles: `screening`
- `hidden_acceptance:P-S02:S1:R01` — Measurement Set `outcome`; task-pack roles: `screening`
- `hidden_acceptance:P-S03:B0:R01` — Measurement Set `outcome`; task-pack roles: `screening`
- `hidden_acceptance:P-S03:S1:R01` — Measurement Set `outcome`; task-pack roles: `screening`
- `hidden_acceptance:P-S04:B0:R01` — Measurement Set `outcome`; task-pack roles: `screening`
- `hidden_acceptance:P-S04:S1:R01` — Measurement Set `outcome`; task-pack roles: `screening`

Falsifier: A retained cell, frozen-rule recomputation, or untouched confirmation result contradicts the published counts or outcome.

## Additional selected claims

These claims disclose supporting workflow or artifact facts; they do not govern the displayed disposition.

### AEL-PBT-V2-02 — supported

The public decision is bound to a preregistered freeze and private pack composites that preceded scored calls.

Claim class: `workflow`

Scope:
- freeze and result artifacts in this repository

Evidence references:
- `screening-decision.json` — public sidecar `studies/agent-skills-season-1/results/property-based-testing-v2/screening-decision.json` (SHA-256 `90f792419b4b2d64ecc49d10afd54e9f3e7f9f597f7981a299a027fac6a192d1`)
- `decision.json` — public sidecar `studies/agent-skills-season-1/results/property-based-testing-v2/decision.json` (SHA-256 `90f792419b4b2d64ecc49d10afd54e9f3e7f9f597f7981a299a027fac6a192d1`)

Falsifier: Git history or retained private evidence shows a scored call preceding the freeze or a pack hash mismatch.

## What was tested

On the exact hidden serialization-roundtrip and normalization-idempotence pilot tasks, does adding the pinned property-based-testing skill to an otherwise identical Codex stack increase binary hidden-adversarial acceptance?

Comparison mode: `controlled_factor`. Study state: `frozen`.

Primary estimand: **hidden-adversarial acceptance** — Matched-condition difference in binary final hidden acceptance; invalid properties, flakiness, activation, invalid runs, cost, and latency remain separate measurements or gates.

Conditions:
- `B0` — Frozen strong Codex baseline (`baseline`, `skill`)
- `S1` — trailofbits-property-based-testing (`treatment`, `skill`)

Task strata:
- `agent-skills-season-1-calibration-v1` (`calibration`): property-based-testing
- `property-based-testing-v2-screening` (`screening`): serialization-roundtrip, normalization-idempotence
- `property-based-testing-v2-confirmation` (`holdout`): serialization-roundtrip, normalization-idempotence

Decision owner(s): `kizz-ael-maintainer`

## Observed runs, measurements, and cost

Runs: `8`; by status: `valid=8`.

Measurements: `88`; by kind: `cost=16`, `deterministic=24`, `outcome=32`, `process=16`.

### Repeat and uncertainty evidence

- Repeat coverage: `single_valid_observation_per_retained_cell` across `8` retained task-condition cells.
- Valid repeats per cell: minimum `1`, maximum `1`.
- Measurement intervals: `not_reported` on `0` measurements.

These are facts about retained observations. The projection cannot infer a completely absent planned cell from Run Records alone. They are not a reliability grade, and planned repeat or perturbation coverage cannot substitute for observed data.

Selected descriptive totals (not stable effects):

- `critical_failure` / `B0`: true `2/4` (`critical_failure`)
- `critical_failure` / `S1`: true `2/4` (`critical_failure`)
- `generated_tokens` / `B0`: total `37341 tokens` (`cost_or_latency`)
- `generated_tokens` / `S1`: total `47330 tokens` (`cost_or_latency`)
- `skill_activated` / `B0`: true `0/4` (`activation`)
- `skill_activated` / `S1`: true `4/4` (`activation`)
- `wall_time_ms` / `B0`: total `752432 milliseconds` (`cost_or_latency`)
- `wall_time_ms` / `S1`: total `857633 milliseconds` (`cost_or_latency`)

## Study design preflight

Status: `not_assessed_historical`; scope: `design_preflight`.

- `design_class`: `not_assessed_historical`
- `task_validity`: `not_assessed_historical`
- `evaluator_validity`: `not_assessed_historical`
- `sampling_strength`: `not_assessed_historical`
- `planned_reliability_coverage`: `not_assessed_historical`
- `independence`: `not_assessed_historical`
- `freshness`: `not_assessed_historical`

The study predates the pilot Study Quality Profile. No retrospective measurement-quality assessment is inferred from current artifacts.

## Decision lifecycle

- admission: `not_declared_historical`
- action: `not_declared_historical`
- outcome_follow_up: `not_declared_historical`
- freshness: `unassessed`

## Replication and independence

- Public graph verification: `decision_recomputable`
- Maintainer rerun: `maintainer_only_new_observation`
- Independent replication: `none_linked`
- Evaluation ownership: `maintainer_evaluated`

This is a preregistered maintainer pilot, not independent verification.

Maintainer rerun boundary:

A new maintainer-controlled execution can use retained private screening inputs, but it cannot replay the historical provider behavior or constitute independent replication.

## Technical evidence

- Receipt: [machine-readable evidence](../../studies/agent-skills-season-1/results/property-based-testing-v2/evidence-receipt.json)
- Receipt SHA-256: `07c52812f97fe0c6333fbe919b6d1f99ca409e9d0d44cbeb375c0a43ea43f3f6`
- Receipt evidence state: `controlled_effect_observed`
- Receipt Contract v0 reproducibility field: `rerunnable`

The receipt evidence state and reproducibility field are retained Contract v0 compatibility metadata. Neither is a score, a public task-rerun claim, or proof of independent replication.

### Verification boundary

Kind: `frozen_public_bundle`

Verifies the published Contract v0 graph, frozen public bundle, recomputed PBT decision counts, and repository artifact ordering. It does not rerun model calls, reveal private tasks, or constitute independent replication.

Command (presentation only; not executed by this generator):

```sh
uv run ael study audit --freeze studies/agent-skills-season-1/screening/property-based-testing-v2.freeze.json --result studies/agent-skills-season-1/results/property-based-testing-v2 --decision-adapter pbt-v2 --require-git-proof
```

Audit status: `passed`.
Contract documents checked: `12`; run records: `8`.


## Materials

- **Private screening task bytes** — `withheld`
  - Reason: The task pack is retained outside the public repository to preserve holdout value.
  - Reproduction impact: A public checkout can verify frozen digests and recompute the published decision, but cannot independently rerun the exact tasks.
- **Private confirmation task bytes** — `withheld`
  - Reason: The unopened confirmation pack remains private and was not executed.
  - Reproduction impact: The public package cannot run confirmation; the receipt makes no confirmation claim.
- **Hosted model calls** — `not_retained`
  - Reason: The public evidence contains normalized run records rather than a replayable provider execution service.
  - Reproduction impact: The exact historical model calls cannot be replayed from the repository.

## Unsupported inferences

- Property-based-testing skills work in general.
- The skill independently caused defect discovery or prevention rather than a final hidden-acceptance difference.
- The result transfers to other defect families, tasks, models, CLIs, repositories, or production systems.
- The maintainer-evaluated result is independent verification.
- A token or latency difference from this small pilot is a stable cost effect.

## Limitations

- The terminal decision used 4 matched pairs and has wide task-sampling uncertainty.
- Tasks, raw events, candidates, and deterministic evaluator outputs remain private and are represented by opaque hashes.
- Kizz authored, operated, and evaluated this pilot; no independent replication exists.
- The provider exposed a model identifier but not an immutable model revision.
- The reusable ChatGPT credential was process-readable; persisted output was exact-value scanned, but encrypted provider traffic was not inspected.

## Invalidation triggers

- A pack hash, freeze hash, preregistration SHA, observation hash, or published count fails verification
- A scored call is shown to predate preregistration
- A task, evaluator, prompt, source, model, effort, image, budget, or decision rule changed after freeze
- Public language promotes this bounded pilot into a general skill or model claim

## Source hashes

- `reports/2026-08-12-property-based-testing-v2.md` — `018e28ce8a8e63ed05903182836336a8e3b0ca91bb8360f9b8c68fe3e5bf30bb`
- `studies/agent-skills-season-1/concept.json` — `832391e453e62d7615ec67d150534a074d043a76346a9d3b8e83e21a45aac5a6`
- `studies/agent-skills-season-1/manifests/property-based-testing-v2.study-manifest.json` — `48b4d8211412ad06123a27cee10cc7051a6a5d9e5d79d055fe98715ff36f6d62`
- `studies/agent-skills-season-1/results/property-based-testing-v2/decision.json` — `90f792419b4b2d64ecc49d10afd54e9f3e7f9f597f7981a299a027fac6a192d1`
- `studies/agent-skills-season-1/results/property-based-testing-v2/evidence-receipt.json` — `07c52812f97fe0c6333fbe919b6d1f99ca409e9d0d44cbeb375c0a43ea43f3f6`
- `studies/agent-skills-season-1/results/property-based-testing-v2/evidence-receipt.md` — `87a7304f6fe26c68c48767a0b6fc0393ba11decf435e57494697b58dc856c555`
- `studies/agent-skills-season-1/results/property-based-testing-v2/freeze-ref.json` — `4a8b383e7db948df58e5c23d6c861598f77384bfcd56357b582cffb8a588552f`
- `studies/agent-skills-season-1/results/property-based-testing-v2/measurement-set.json` — `e77974bec757ed9af6280dd95ce1899897f11aa3c9c8dd1c2891ee49445251a5`
- `studies/agent-skills-season-1/results/property-based-testing-v2/runs/P-S01-B0-R01.json` — `f92768de66234e5c0b7bc00bbc2e067054ae3c1ca4da14cede89101a7d4ccf37`
- `studies/agent-skills-season-1/results/property-based-testing-v2/runs/P-S01-S1-R01.json` — `848d294a13583f25b5d709993f76aebb6d1f2f2d2a66d34bed5a088cb460817d`
- `studies/agent-skills-season-1/results/property-based-testing-v2/runs/P-S02-B0-R01.json` — `cf070ab2c8b166276e4e0dc8102cf990cf68b1454b152f2fe3abccf1ae4d87b3`
- `studies/agent-skills-season-1/results/property-based-testing-v2/runs/P-S02-S1-R01.json` — `de96eef924e54995a1dd3b06c4559e1942db29283dc49a09b8737730c2deaffe`
- `studies/agent-skills-season-1/results/property-based-testing-v2/runs/P-S03-B0-R01.json` — `aea819bbf1e01c29b383911a6a1121a6cf4b2e44b27f9742c32236a7cd8851ab`
- `studies/agent-skills-season-1/results/property-based-testing-v2/runs/P-S03-S1-R01.json` — `3b19adc51fb12ea80ecff8530679c95b28fd15477af1e26d218a0fc6062472a4`
- `studies/agent-skills-season-1/results/property-based-testing-v2/runs/P-S04-B0-R01.json` — `ee11abaed993f8083a267346470c3f743f56b2f8b10287b8b78c62ed59684b13`
- `studies/agent-skills-season-1/results/property-based-testing-v2/runs/P-S04-S1-R01.json` — `5ca5ed0127590840c6e2bec4dd174cec01a5be6ce38610c23390b78f12ad7c72`
- `studies/agent-skills-season-1/results/property-based-testing-v2/screening-decision.json` — `90f792419b4b2d64ecc49d10afd54e9f3e7f9f597f7981a299a027fac6a192d1`
- `studies/agent-skills-season-1/screening/property-based-testing-v2.freeze.json` — `a1fac08b84e35f412de04f37a1d3eb3ac3ce2711df474febd9a64b2fb4e3fb05`
- `studies/public-results.json` — `df0a8c164b1b9035be0d72bcd5e05873feff91a88516ebc06b1f35062bff3518`

Generated by `agentic-evidence-lab` `0.1.0a8` under `ael.publication-projection/0.5`.
