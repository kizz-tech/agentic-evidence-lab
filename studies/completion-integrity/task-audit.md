# Completion Integrity task and oracle audit

## Audited artifact

- Private pack: `completion-integrity-v1`, revision 4.
- Tree SHA-256:
  `06d9d476dd56c322a798eef865dd1576bea7a22daa2687717f2af94877610c72`.
- Core cases: eight; screening: six; confirmation: two.
- Mechanisms: requirement coverage and acceptance evidence, four cases each.
- Strata: two per mechanism, two independent cases per stratum.

## Deterministic calibration

The evaluator ran in the pinned offline runner image against four known states
for every core case:

| State | Required classification |
| --- | --- |
| pristine | visible checks pass, final acceptance fails, no regression |
| known-good | visible checks and every requirement pass, no regression |
| regression | final acceptance fails and a preserved invariant fails |
| invalid | evaluator reports operational invalidity |

All 32 state checks passed. The public gate is
`studies/completion-integrity/no-call-gate.json`, SHA-256
`41d389f53104fc42a3bfc2ac1fa0365e3a047813dabd0b050c993e168a2b4f0e`.

## Review checks

- **Instruction/test alignment — pass.** Each requirement ID resolves to at
  least one deterministic predicate and the dossier list exactly equals the
  oracle list.
- **Oracle validation — pass.** Known-good and plausible incomplete states are
  distinguished for every case; invalid input never becomes a model outcome.
- **Alternative valid solutions — pass.** Predicates inspect behavior and
  owner artifacts rather than private implementation text. The added-test case
  explicitly reruns candidate tests against an alternative reference repair.
- **Shortcut rejection — pass.** Regression states include plausible
  over-rejection, dropped compatibility behavior, fabricated authority, or
  incomplete cross-surface changes.
- **Environment validation — pass.** Evaluators run offline, receive no model
  credentials, and use regular-file/non-symlink candidate roots.

## Limits

The audit proves deterministic discrimination on declared known states. It
does not prove construct completeness outside the frozen oracle surface,
representativeness, inter-rater reliability, independent authorship, or a model
or policy effect.
