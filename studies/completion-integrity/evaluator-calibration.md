# Completion Integrity evaluator and headroom calibration

## No-call instrument result

Revision 4 distinguished all 32 known states for the eight scored tasks. The
gate passed before any revision-4 model call. It establishes evaluator
discrimination, not policy effectiveness.

## Sacrificial baseline headroom

Two excluded cases were then run once with the common baseline prompt on Codex
CLI 0.146.0, `gpt-5.6-sol`, `xhigh` effort. Both executions were operationally
valid, passed their visible checks, emitted exactly one
`AEL_COMPLETION=complete`, and failed at least one hidden owner requirement.
Baseline false completion was therefore observed in 2/2 sacrificial cases.

The public headroom record is
`studies/completion-integrity/baseline-headroom.json`. These calls never enter
the scored schedule, estimator, uncertainty interval, or disposition.

## Error and adjudication boundary

The deterministic evaluator can miss defects outside its frozen predicates and
has no human inter-rater estimate. A missing, malformed, or duplicate terminal
marker is valid indeterminate agent behavior. Container, provider, credential,
fixture, or evaluator failure is operational invalidity. Any ambiguous
submission is retained and cannot be retried. Any missing or invalid scored
cell makes the terminal study protocol-invalid.

## Preserved failed calibrations

Earlier invalid and ceiling results remain under
`studies/completion-integrity/calibration/`. They show why task supply changed
before freeze: revision 1 had instrument defects; revisions 2 and 3 did not
produce baseline headroom on the selected sacrificial tasks; a Terra/high check
also reached ceiling. No scored result was used to redesign revision 4.
