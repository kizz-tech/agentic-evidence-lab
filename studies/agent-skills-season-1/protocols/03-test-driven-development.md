# 03 — Test-driven development

State: protocol draft; public activation calibration completed; process-level
effectiveness screening unrun.

## Decision question

Does the exact pinned Superpowers `test-driven-development` skill cause
test-first behavior that improves regression detection and final task outcomes
relative to the same agent stack without it?

## Conditions and task design

- `B0`: normal implementation workflow.
- `S1`: `B0` plus the exact skill.
- `P1`: equal-context placebo is prespecified because the skill adds substantial
  procedural context and observed behavior order is the construct under test.

Tasks include new behavior, bug repair, refactoring with an existing contract,
and a case where a brittle test would encode an implementation detail. Final
workspace inspection cannot prove red-green-refactor order; the runner must
capture timestamped tool events without exposing hidden evaluators.

## Measurements and decision

Primary: proportion of valid runs in which a discriminating test is observed
failing before the corresponding implementation change and later passes.
Secondary: hidden regression detection, acceptance, test brittleness, critical
omissions, cost, and time. A final green suite without process evidence cannot
support a TDD-mechanism claim.
