# Evidence receipt: kizz:ael:receipt:agent-skills-season-1:pbt-v2

- Study: `kizz:ael:study:agent-skills-season-1:property-based-testing`
- Decision: **reject**
- Evidence level: `controlled_effect_observed`
- Independence: `maintainer_evaluated`
- Reproducibility: `rerunnable`
- Publication state: `public_ready`

## Decision

S1 did not meet the frozen selection or confirmation rule on this pilot surface.

### Scope

- the exact frozen PBT v2 serialization and normalization tasks
- Codex CLI 0.146.0 with gpt-5.6-sol at xhigh effort
- preregistration commit 610f0d9e1e19d9c89dd6beba8fab7900222df5dd

## Evaluated claims

### AEL-PBT-V2-01 — contradicted

S1 changed hidden-edge acceptance enough to satisfy the frozen terminal rule on the exact pilot cells.

Claim level: `factor_causal`

Scope:
- exact matched serialization and normalization pilot cells

Falsifier: A retained cell, frozen-rule recomputation, or untouched confirmation result contradicts the published counts or outcome.

### AEL-PBT-V2-02 — supported

The public decision is bound to a preregistered freeze and private pack composites that preceded scored calls.

Claim level: `workflow`

Scope:
- freeze and result artifacts in this repository

Falsifier: Git history or retained private evidence shows a scored call preceding the freeze or a pack hash mismatch.

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

## Independence and role overlap

- Kizz authored the tasks, operated the runner, evaluated deterministic outcomes, and owns the decision.

## Invalidation triggers

- A pack hash, freeze hash, preregistration SHA, observation hash, or published count fails verification
- A scored call is shown to predate preregistration
- A task, evaluator, prompt, source, model, effort, image, budget, or decision rule changed after freeze
- Public language promotes this bounded pilot into a general skill or model claim

## State

- experiment: `PBT v2 terminal outcome: reject_all_critical_failure`
- artifact: `frozen private task composites represented by hashes; sanitized evidence materialized`
- repository: `result package prepared in the local release candidate`
- publication: `prepared, not published`
- deployment: `not deployed`
- outcome: `hidden-edge acceptance observed on exact pilot cells; downstream production outcome unmeasured`
