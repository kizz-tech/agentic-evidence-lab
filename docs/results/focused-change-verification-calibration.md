# Focused Change Verification calibration

- Card ID: `focused-change-verification-calibration`
- Catalog state: **listed**
- Narrative report: [open](../../reports/2026-08-12-focused-change-verification-codex-calibration.md)

## Decision

**narrow** — Keep the Codex runner and current pack as an operational smoke surface, but do not spend the planned 18-cell budget on this ceiling-limited pack; design tasks that do not restate the skill before estimating an effect.

Scope:
- Codex CLI 0.146.0 with gpt-5.6-sol at xhigh effort
- the exact pinned runtime and proxy image IDs in the six run records
- three public maintainer-authored calibration tasks
- one non-randomized repeat per condition and task

Reversal trigger: Reconsider after a frozen discriminating pack, preregistered behavioral rubric, randomized order, repeated cells, and a safer credential boundary are available.

## Decision-governing claims

### AEL-FCV-CAL-03 — bounded

No deterministic implementation-acceptance difference was observed: baseline and treatment each passed three of three tasks.

Claim class: `workflow`

Scope:
- one calibration repeat
- three public tasks
- deterministic acceptance only

Evidence references:
- `acceptance-total:S0` — Measurement Set `aggregate`; task-pack roles: `adaptation`
- `acceptance-total:S1` — Measurement Set `aggregate`; task-pack roles: `adaptation`

Falsifier: Repeated matched runs on a discriminating pack produce a stable acceptance or critical-omission difference.

### AEL-FCV-CAL-04 — bounded

The current public prompts are too explicit to isolate the skill's verification-routing contribution and should remain smoke tests rather than become the first confirmatory pack.

Claim class: `workflow`

Scope:
- current task wording
- observed 6-of-6 acceptance ceiling

Evidence references:
- `acceptance-total:S0` — Measurement Set `aggregate`; task-pack roles: `adaptation`
- `acceptance-total:S1` — Measurement Set `aggregate`; task-pack roles: `adaptation`

Falsifier: A preregistered repeated study on the unchanged pack exhibits reliable non-ceiling discrimination on the primary behavioral estimand.

## Additional selected claims

These claims disclose supporting workflow or artifact facts; they do not govern the displayed disposition.

### AEL-FCV-CAL-01 — supported

The controlled-egress Docker adapter executed six stable Codex cells without changing any canonical fixture and captured enough telemetry for deterministic post-run evaluation.

Claim class: `workflow`

Scope:
- six runtime-v2 calibration cells
- maintainer-controlled fixtures

Evidence references:
- `canonical-fixture-mutation` — opaque receipt reference; this projection does not independently resolve it
- `acceptance-total:S0` — Measurement Set `aggregate`; task-pack roles: `adaptation`
- `acceptance-total:S1` — Measurement Set `aggregate`; task-pack roles: `adaptation`

Falsifier: A byte-equivalent rerun mutates a fixture, cannot export a candidate, or cannot bind telemetry to the evaluated workspace.

### AEL-FCV-CAL-02 — supported

The frozen skill was installed and explicitly read in all three treatment cells and in no baseline cell.

Claim class: `artifact`

Scope:
- S1 treatment cells
- retained private Codex event streams

Evidence references:
- `skill-activation:local-unit:S1` — Measurement Set `process`; task-pack roles: `adaptation`
- `skill-activation:cross-contract:S1` — Measurement Set `process`; task-pack roles: `adaptation`
- `skill-activation:migration:S1` — Measurement Set `process`; task-pack roles: `adaptation`

Falsifier: A retained treatment trace lacks the exact skill read or a baseline trace loads it.

## What was tested

Does the exact installable verification skill improve owner-layer test selection and state-truth reporting relative to the same coding agent without the skill?

Comparison mode: `controlled_factor`. Study state: `draft`.

Primary estimand: **verified change completion difference** — Paired difference in deterministic repository acceptance and critical validation omissions with downstream correction effort reported separately.

Conditions:
- `S0` — Coding agent without verification skill (`baseline`, `skill`)
- `S1` — Coding agent with focused verification skill (`treatment`, `skill`)

Task strata:
- `focused-change-verification-adaptation-v1` (`adaptation`): local-unit-change, cross-module-contract-change, migration-backed-change

Decision owner(s): `kizz-ael-maintainer`

## Observed runs, measurements, and cost

Runs: `6`; by status: `valid=6`.

Measurements: `33`; by kind: `aggregate=6`, `cost=12`, `deterministic=12`, `process=3`.

### Repeat and uncertainty evidence

- Repeat coverage: `single_valid_observation_per_retained_cell` across `6` retained task-condition cells.
- Valid repeats per cell: minimum `1`, maximum `1`.
- Measurement intervals: `not_reported` on `0` measurements.

These are facts about retained observations. The projection cannot infer a completely absent planned cell from Run Records alone. They are not a reliability grade, and planned repeat or perturbation coverage cannot substitute for observed data.

Selected descriptive totals (not stable effects):

- `generated_work_tokens` / `S0`: total `20256 tokens` (`cost_or_latency`)
- `generated_work_tokens` / `S1`: total `21944 tokens` (`cost_or_latency`)
- `skill_activated` / `S1`: true `3/3` (`activation`)
- `wall_time` / `S0`: total `331689 milliseconds` (`cost_or_latency`)
- `wall_time` / `S1`: total `378385 milliseconds` (`cost_or_latency`)

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

- Public graph verification: `graph_validatable`
- Maintainer rerun: `not_assessed`
- Independent replication: `none_linked`
- Evaluation ownership: `maintainer_evaluated`

This is maintainer calibration evidence, not independent certification or a confirmatory skill-effect study.

Maintainer rerun boundary:

No current maintainer rerun package is asserted; the public package supports evidence-graph validation only.

## Technical evidence

- Receipt: [machine-readable evidence](../../examples/coding-skill/calibration-v1/evidence-receipt.json)
- Receipt SHA-256: `7a770b0b177a313f6b042d67d2aaab62919d333b6d1625fcd7b3eff766c3e581`
- Receipt evidence state: `runtime_conformant`
- Receipt Contract v0 reproducibility field: `rerunnable`

The receipt evidence state and reproducibility field are retained Contract v0 compatibility metadata. Neither is a score, a public task-rerun claim, or proof of independent replication.

### Verification boundary

Kind: `evidence_graph`

Validates the published Contract v0 graph and exact local reference hashes. It does not rerun hosted Codex calls or turn this calibration into skill-effect evidence.

Command (presentation only; not executed by this generator):

```sh
uv run ael validate examples/coding-skill
```


## Materials

- **Hosted Codex event streams and exported workspaces** — `withheld`
  - Reason: Raw hosted execution artifacts remain in the private evidence boundary.
  - Reproduction impact: A public checkout can validate normalized records but cannot replay the exact six hosted calls.
- **Discriminating holdout pack** — `not_collected`
  - Reason: The completed work was an operational calibration; the discriminating pack was not run.
  - Reproduction impact: The public evidence cannot estimate a skill effect.

## Unsupported inferences

- The skill improves implementation correctness or code quality.
- The skill is cost-effective or faster.
- The skill transfers to real repositories or other models and agent runtimes.
- Codex or gpt-5.6-sol is superior to Claude Code, Cursor, another CLI, or another model.
- The current credential boundary is safe for untrusted third-party tasks or skills.
- Three acceptance passes per condition establish equivalence.

## Limitations

- One non-randomized calibration repeat was run per task and condition; this is not an effect estimate.
- The public task prompts explicitly request much of the verification behavior contributed by the skill, creating a ceiling and treatment-contamination risk.
- Kizz owns the skill, tasks, runner, deterministic evaluator, and decision.
- The provider exposes a model identifier but not an immutable model revision.
- Generated-work and wall-time budgets were matched by configuration but not forced to equal realized usage.
- The reusable ChatGPT credential was process-readable; persisted outputs were scanned, but encrypted provider traffic was not inspected.
- No downstream rework, production behavior, user outcome, or third-party replication was measured.

## Invalidation triggers

- A change to the frozen skill, task pack, prompt, Codex version, model/effort, runner image, proxy policy, or evaluator
- New evidence that credential content entered persisted artifacts or unauthorized traffic
- A repeated or real-shadow study contradicting the calibration observations
- A public claim that omits the maintainer-evaluated and calibration-only scope

## Source hashes

- `examples/coding-skill/calibration-v1/evidence-receipt.json` — `7a770b0b177a313f6b042d67d2aaab62919d333b6d1625fcd7b3eff766c3e581`
- `examples/coding-skill/calibration-v1/measurement-set.json` — `5172087b3082098af68655e23b496d9f53f2f43406ff3c7bd2503ec453e30978`
- `examples/coding-skill/calibration-v1/runs/cross-contract-S0-01.json` — `d68662c9e3fc296b91d20cc826aeeaf44d22b5e1e38778e67ebf9cab6e50f929`
- `examples/coding-skill/calibration-v1/runs/cross-contract-S1-01.json` — `6abeea0eb521ba1bf8548c9329d56dd651e4369d4ccdd10279062055f3579828`
- `examples/coding-skill/calibration-v1/runs/local-unit-S0-01.json` — `2d1af1c992511cc015d2d3624b617cfc20545659748eb2d4e19218408404638a`
- `examples/coding-skill/calibration-v1/runs/local-unit-S1-01.json` — `8adc6c3a3cd041255d91e75efedcfa412cde4f781f4ddc62b369f2fd1644d1fc`
- `examples/coding-skill/calibration-v1/runs/migration-S0-01.json` — `195d089f6a892add9f6197d60fb197d88325e8b234ae83b62b99849a113094a0`
- `examples/coding-skill/calibration-v1/runs/migration-S1-01.json` — `47dd47a0a3d908cfd1e30d3fd75cd5b459e4ca7e1e6f6f8a698a52187b3a78d6`
- `examples/coding-skill/concept.json` — `056da8f4a9bd5f90140f3440e7c283b0c172f64adfa5606f783a8223372d48b8`
- `examples/coding-skill/study-manifest.json` — `330700bc8cb12d77520f251fb94f54c8b879a9915c39f530feaf5d56a1bed841`
- `reports/2026-08-12-focused-change-verification-codex-calibration.md` — `0d5159f51fbe4be863be1feb319ffd0ef1364ddbd859f12d49cfabef15d15d2c`
- `studies/public-results.json` — `df0a8c164b1b9035be0d72bcd5e05873feff91a88516ebc06b1f35062bff3518`

Generated by `agentic-evidence-lab` `0.1.0a8` under `ael.publication-projection/0.5`.
