# 05 — Differential security review

State: protocol draft; public activation calibration completed; discriminating
security-review screening unrun.

## Decision question

Does the exact pinned Trail of Bits `differential-review` skill improve recall
of critical security regressions in code changes without producing an
unusable false-positive burden?

## Conditions and task design

- `B0`: strong single Codex security diff review under the same budget.
- `S1`: `B0` plus exact differential-review.
- A separate operational-stack comparison may be needed if the skill's allowed
  tools or report workflow cannot be matched; it must not be called a
  controlled skill effect.

Hidden diffs contain independently seeded auth, injection, cryptographic,
state-integrity, and safe-change controls. Evaluators are vulnerability labels
and exploitability anchors authored before candidate outputs; model voting is
not ground truth.

## Measurements and decision

Primary: critical/high regression recall with false positives shown separately.
Also report precision, severity calibration, blast-radius accuracy, evidence
quality, review coverage, cost, and time. A missed critical finding is never
hidden by an aggregate score. This study does not certify a repository as safe.
