# 10 — Recursive skill improvement

State: protocol draft; both raw skill snapshots activated; optional dependency
freeze, contamination controls, and effectiveness screening remain unrun.

## Decision question

Can a frozen skill-improvement workflow raise held-out task performance for a
target skill without overfitting calibration prompts or introducing new
critical failures?

## Conditions and task design

- `B0`: one accountable manual/model-assisted revision pass with the same
  examples, evaluator feedback, and total budget.
- `S1`: exact Anthropic skill-creator workflow.
- `S2`: Trail of Bits skill-improver plus its separately frozen reviewer
  dependency; the skill alone is not an executable complete intervention.

The target skill source is copied into disposable workspace. Conditions export
a patch or new content-addressed tree and can never mutate upstream, AEL, the
calibration set, or confirmation set. Calibration and confirmation task
families are disjoint; improvement stops before confirmation access.

## Measurements and decision

Primary: held-out task-performance difference from the frozen predecessor.
Secondary: trigger precision/recall, critical failures, regression count,
instruction size, generated work, human review load, and iteration count.
Every new candidate is a new version; unfavorable and null generations remain
visible. Better rubric conformance without better held-out task outcomes is not
skill effectiveness.
