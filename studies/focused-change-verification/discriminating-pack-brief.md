# Discriminating task-pack brief

State: design requirement after runtime-v2 calibration; no candidate tasks
frozen or run.

## Why a second pack is required

Adaptation v1 proved runner operation and skill activation, but its prompts
explicitly prescribed owner-local, direct-consumer, and migration validation.
That gives baseline much of the intervention and produced a six-of-six
acceptance ceiling. Repetition would not repair the estimand.

## Target contrast

The next pack should test whether the installed skill changes what the agent
chooses to inspect, validate, and claim when the product request itself does not
name those checks.

Hold model, Codex version, task prompt template, tools, permissions, timeout,
fixture revision, and evaluator fixed. Change only skill installation. Keep
implementation correctness, verification routing, evidence-state accuracy,
generated work, and wall time as separate outcomes.

## Required task strata

1. **Negative-control local change** — one obvious owner and no material direct
   consumer, so unnecessary broad validation is measurable overhead.
2. **Implicit shared-contract propagation** — the requested change appears
   local, but a discoverable direct consumer can break unless the contract is
   traced.
3. **Persistence evolution** — a populated disposable store requires row
   preservation, repeated application safety, and a recovery decision, none of
   which is named in the user prompt.
4. **Configuration or generated boundary** — the source edit is insufficient
   unless the consuming startup/build/generated path is checked.
5. **Failure-preservation case** — one required check fails for a real reason;
   the correct behavior is accurate limitation reporting, not rerunning or
   substituting a weaker check until green.

At least one task must make extra validation harmful through time or work caps,
and at least one must require a broader direct-consumer check to avoid a
critical omission.

## Prompt rule

Task prompts describe desired product behavior, constraints, and prohibited
external effects. They must not say which files own the behavior, which
consumer to inspect, which exact tests to run, or which completion-state labels
to report. Those choices are the intervention target.

## Preregistered measurements

- separate hidden implementation acceptance;
- task-specific critical verification omissions derived from captured commands
  and artifacts;
- false or collapsed completion-state claims;
- unnecessary check count and generated-work cost;
- skill activation and operational validity;
- downstream correction required by a blinded maintainer or deterministic
  repair evaluator where feasible.

No global score should hide a critical omission. Acceptance and state-reporting
accuracy must be reported per task before aggregation.

## Pilot and stop rule

Freeze the tasks, evaluators, rubric, randomized order, and runtime identity
before execution. Run one matched pair per task as calibration. Do not expand
to three repeats when all cells pass and the behavioral rubric cannot
distinguish the conditions, when the skill fails to activate, or when evaluator
leakage makes the target route obvious. Preserve a failed or null pilot instead
of silently replacing tasks after inspecting treatment outputs.

Only after a discriminating public adaptation pack works should untouched
private holdout tasks be authored and frozen.
