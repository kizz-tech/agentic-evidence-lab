# 04 — Property-based testing

State: protocol draft; public activation calibration completed; effectiveness
screening unrun.

## Decision question

Does the exact pinned Trail of Bits `property-based-testing` skill discover and
prevent edge-case defects that strong example-based testing misses?

## Conditions and task design

- `B0`: same coding agent and test budget without the skill.
- `S1`: `B0` plus the exact source-locked skill.
- A placebo is added only if prompt-size calibration shows a material confound.

Strata cover serialization round trips, parsers, normalizers, validators, and
stateful collections. Hidden generators use frozen seeds plus adversarial edge
classes; task prompts request robust behavior but do not name properties or
counterexamples.

## Measurements and decision

Primary: seeded edge-case defect detection rate on initially unknown defects.
Secondary: meaningful property count, shrinking/reproducibility, false
properties, final acceptance, test runtime, tokens, and wall time. Reject a
candidate that gains coverage by asserting an invalid property or produces
flaky non-replayable failures. Results transfer only to the measured pattern
families and dependency/runtime versions.
