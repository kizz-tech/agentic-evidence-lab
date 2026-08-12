# 01 — Truthful completion

State: protocol draft; public activation calibration completed; effectiveness
screening unrun.

## Decision question

Does the exact pinned Superpowers `verification-before-completion` skill reduce
unsupported completion claims after repository changes relative to the same
Codex stack without it?

## Frozen candidate design

- `B0`: same model, runtime, prompt, tools, permissions, and task without the skill.
- `S1`: `B0` plus the exact source-locked skill tree.
- `P1`: equal-token inert procedural context only if calibration shows a
  context-volume or attention confound.

The public task only checks runner and evaluator mechanics. Screening must not
tell the agent which owner-layer checks demonstrate success. Tasks should mix
local behavior, cross-contract effects, stateful migrations, and an intentional
unresolved blocker.

## Measurements and decision

Primary: unsupported completion claim rate, judged against deterministic
owner-layer outcomes and the final state report. Secondary: task acceptance,
critical omissions, checks selected, unnecessary checks, generated work, and
wall time. Continue only if activation is observed and the hidden pack avoids a
baseline ceiling. Do not infer general code-quality improvement from truthful
reporting alone.
