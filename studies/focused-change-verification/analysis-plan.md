# Focused Change Verification — adaptation analysis plan

State: frozen for runner calibration; model runs unstarted.

## Question

Does the frozen `focused-change-verification` skill change verification behavior
or deterministic task acceptance relative to the same coding agent without the
skill on the three public adaptation tasks?

This stage debugs the intervention and experiment pipeline. It cannot support a
held-out generalization or release-adoption claim.

## Design

- Conditions: `S0` without the skill and `S1` with the exact frozen skill.
- Tasks: local-unit, cross-contract, and migration from adaptation pack v1.
- Repeats: three independent runs per condition and task after the hosted-model
  runner is calibrated, for 18 planned cells.
- Pairing: same task revision, model, effort, runtime image, task prompt, tool
  surface, permissions, context, timeout, and generated-work cap.
- Changed factor: only skill installation and the instructions it contributes.
- Order: randomized within each task/repeat block and recorded before execution.
- Retry: only operational invalidity from the same frozen input; poor work is a
  valid observation.

## Environment

Use the AEL container adapter. The task fixture is mounted read-only, work occurs
in tmpfs, and only the private output directory is writable. Hosted-model runs
remain blocked until controlled egress, minimum-secret injection, and an
exfiltration smoke test pass. Do not substitute writable host execution.

## Measurements

Report each task and condition separately before any aggregate:

1. hidden deterministic acceptance pass/fail;
2. visible test state in the exported result;
3. critical omission count;
4. validation commands and owner layers actually exercised;
5. unnecessary check count;
6. generated-work tokens and wall time;
7. operational validity and retry reason;
8. accuracy of the final evidence-state report.

The primary adaptation signal is the paired difference in critical omissions.
Acceptance rate, verification routing, cost, and state reporting remain separate
dimensions; no universal score is authorized.

## Decisions

- Continue to hidden task-pack design only if the skill activates as intended,
  causes no new critical omission, and the runner captures enough evidence to
  distinguish verification behavior.
- Revise the skill only as a new content-addressed version. Never overwrite this
  candidate after inspecting its task outputs.
- Stop or narrow if the tasks merely restate the skill, deterministic evaluators
  cannot distinguish useful behavior, or the model-access boundary cannot be
  operated without broad credentials or egress.
- Do not adopt the skill for general use from this adaptation result alone.

