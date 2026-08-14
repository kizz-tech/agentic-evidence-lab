# Evidence receipt: kizz:ael:receipt:focused-change-verification-calibration-v1

- Study: `kizz:ael:study:focused-change-verification-skill`
- Decision: **narrow**
- Receipt evidence state: `runtime_conformant`
- Independence: `maintainer_evaluated`
- Reproducibility: `rerunnable`
- Publication state: `public_ready`

## Decision

Keep the Codex runner and current pack as an operational smoke surface, but do not spend the planned 18-cell budget on this ceiling-limited pack; design tasks that do not restate the skill before estimating an effect.

### Scope

- Codex CLI 0.146.0 with gpt-5.6-sol at xhigh effort
- the exact pinned runtime and proxy image IDs in the six run records
- three public maintainer-authored calibration tasks
- one non-randomized repeat per condition and task

## Evaluated claims

### AEL-FCV-CAL-01 — supported

The controlled-egress Docker adapter executed six stable Codex cells without changing any canonical fixture and captured enough telemetry for deterministic post-run evaluation.

Claim class: `workflow`

Scope:
- six runtime-v2 calibration cells
- maintainer-controlled fixtures

Falsifier: A byte-equivalent rerun mutates a fixture, cannot export a candidate, or cannot bind telemetry to the evaluated workspace.

### AEL-FCV-CAL-02 — supported

The frozen skill was installed and explicitly read in all three treatment cells and in no baseline cell.

Claim class: `artifact`

Scope:
- S1 treatment cells
- retained private Codex event streams

Falsifier: A retained treatment trace lacks the exact skill read or a baseline trace loads it.

### AEL-FCV-CAL-03 — bounded

No deterministic implementation-acceptance difference was observed: baseline and treatment each passed three of three tasks.

Claim class: `workflow`

Scope:
- one calibration repeat
- three public tasks
- deterministic acceptance only

Falsifier: Repeated matched runs on a discriminating pack produce a stable acceptance or critical-omission difference.

### AEL-FCV-CAL-04 — bounded

The current public prompts are too explicit to isolate the skill's verification-routing contribution and should remain smoke tests rather than become the first confirmatory pack.

Claim class: `workflow`

Scope:
- current task wording
- observed 6-of-6 acceptance ceiling

Falsifier: A preregistered repeated study on the unchanged pack exhibits reliable non-ceiling discrimination on the primary behavioral estimand.

### AEL-FCV-CAL-05 — unresolved

Treatment finals more consistently separated local validation from commit, push, deployment, and outcome state, but this observation was not scored by a preregistered rubric.

Claim class: `workflow`

Scope:
- six final responses
- post-hoc qualitative observation

Falsifier: A blinded preregistered state-reporting rubric finds no stable paired difference or favors baseline.

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

## Independence and role overlap

- Kizz owns the intervention, task pack, runner, evaluator, analysis, and continuation decision.

## Invalidation triggers

- A change to the frozen skill, task pack, prompt, Codex version, model/effort, runner image, proxy policy, or evaluator
- New evidence that credential content entered persisted artifacts or unauthorized traffic
- A repeated or real-shadow study contradicting the calibration observations
- A public claim that omits the maintainer-evaluated and calibration-only scope

## State

- experiment: `six-cell runner calibration completed; planned 18-cell adaptation study not run`
- artifact: `frozen skill and public task pack locally validated`
- repository: `included in the v0.1.0-alpha.1 release candidate`
- publication: `prepared for public alpha release`
- deployment: `not deployed`
- outcome: `not observed`
