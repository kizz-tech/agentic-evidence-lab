# Alpha.11 activation result and repair boundary

Status: accepted for the alpha.11 empirical release.

## Decision

Publish Completion Integrity activation v2 exactly as
`protocol_invalid / revise_activation_adapter`. Do not retry, resume, repair in
place, or score the semantically matching private reporter payload. Keep the
v2 freeze and result bytes immutable.

Repair future source by making adapter-generated attempt identifiers valid by
construction and by testing the complete truth/submission/assessment wrapper.
Do not claim that this source repair changes the v2 result. A repaired
activation must be a new protocol revision with a new raw root and
preregistration.

## Why

The frozen schedule terminated correctly after its second cell. The reporter
output matched frozen truth at the content layer, but an owner-generated bare
hexadecimal attempt identifier violated the terminal-claim identifier grammar.
The passing schema capability probe had exercised only model-authored output,
not the composed owner wrapper. Retrospective acceptance would weaken the exact
no-retry and preregistration properties the study was built to test.

The invalid result is therefore evidence about the adapter and qualification
process, not evidence about a reporter effect. Publishing it is decision-useful:
it blocks a larger pilot until the real integration boundary is qualified.

The frozen materializer originally labeled both selected receipt claims as
`workflow` while assigning the invalid result the lower `structurally_valid`
evidence state. Public claim admission correctly rejected that combination.
Alpha.11 repairs only the publication representation: invalid-protocol claims
are record-centric `artifact` claims, while a completed activation may retain
`workflow` claims under `runtime_conformant`. The decision, observations,
measurements, scheduled states, and historical frozen materializer hash do not
change.

## Quality representation

Activation v2 was prospective, but no frozen Study Quality Profile governed
it. Labeling it `not_assessed_historical` would be false; constructing a profile
after the run would be retrospective certification. Public projection policy
`0.6` therefore adds `not_assessed_current` with a mandatory reason and projects
every quality axis as unassessed.

This status does not invalidate the frozen protocol decision. It prevents the
result catalog from silently upgrading design-quality evidence that was never
preregistered.

## Alpha.12 admission gates

A new activation revision may run only when all of the following pass before
freeze:

1. generated attempt identities pass the terminal-claim grammar for every
   scheduled cell;
2. a full-wrapper preflight constructs frozen truth and reporter submission and
   receives a passing terminal assessment;
3. schema capability, local evidence readability, optional-tool denial,
   image identity, and credential-persistence checks still pass;
4. the public Study Quality Profile is frozen with task, evaluator, sampling,
   reliability, independence, and freshness evidence;
5. tasks use new sacrificial roots so observed v2 content cannot tune a scored
   replacement;
6. the new schedule preserves terminal invalid, ambiguous, harmful, negative,
   and unrun states without outcome retry.

Only after activation passes may alpha.12 admit a larger Codex-only pilot. Model
and harness comparisons remain deferred until the Codex method is stable enough
that adapter defects are not mistaken for model differences.

## Rejected alternatives

- **Count the B0 output as correct.** Rejected because it changes a frozen
  validity rule after observation.
- **Retry only the failed cell.** Rejected because the protocol forbids resume
  after submission and provider state is not replayable.
- **Hide the result and publish only the repair.** Rejected because it destroys
  the most useful evidence about qualification coverage.
- **Immediately run v3 in alpha.11.** Rejected because the observed root and
  payload would contaminate a supposedly prospective repair validation.

## Reversal

Revisit this decision if public recomputation contradicts the retained result,
if the raw no-retry journal is found inconsistent, or if an independently
specified protocol shows that wrapper identity is intentionally outside claim
validity. None of those conditions currently holds.
