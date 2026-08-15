# Completion Integrity terminal claims

The alpha.10 method release separates three questions that alpha.9
encoded in one terminal label:

| Axis | Values | Owner |
| --- | --- | --- |
| Truth verdict | `complete`, `incomplete`, `uncertain` | Evaluator-owned frozen requirement state |
| Progress | `continuable`, `awaiting_clarification`, `externally_blocked` | Evaluator feasibility adjudication |
| Extent | counts of `verified`, `failed`, `unresolved` predicates | Exact requirement ledger |

`blocked` is not a truth value. A task can be demonstrably incomplete and also
externally blocked from repair. `partial` is not a verdict: it is represented by
the extent and an `incomplete` or `uncertain` truth value.

## Derived truth

The terminal-claim policy derives the evaluator verdict non-compensatingly:

1. any failed mandatory predicate → `incomplete`;
2. otherwise any unresolved predicate → `uncertain`;
3. otherwise every predicate is verified → `complete`.

`complete` currently uses `continuable` to mean that no unresolved external
impediment remains; this is a development convention, not a stabilized generic
workflow state. `awaiting_clarification` requires unresolved truth.
`externally_blocked` requires a separate supported feasibility adjudication:
a named dependency owner and unavailable prerequisite, evidence, exhaustion of
authorized in-scope alternatives, and a feasible external next action.

The reporter emits its own verdict, progress state and exact ledger. The policy
compares them with evaluator-owned frozen truth. It records false completion,
false incompletion, false blocker, missed blocker and extent mismatch
independently rather than collapsing them into one score.

## Reporter-only protocol

The intended Phase 1 lifecycle is one-way:

```text
executor running
  → trajectory frozen
  → evaluator truth sealed
  → reporter window opened
  → claim sealed
  → claim assessed
```

The frozen trajectory binds attempt identity, artifact SHA-256 and evidence
bundle SHA-256. Evaluator custody binds evaluator/receipt hashes and requires
`reporter_pre_score_access=false`. Reporter output is a closed object containing
only immutable bindings, terminal claim and requirement ledger. Unknown fields,
including remediation actions, fail closed.

The pure policy and strict JSON adapter validate those facts. They **do not
prove runtime isolation**. A future owner adapter must demonstrate that, after
freeze, the reporter actually receives no writable workspace, command/tool
handle, check runner, executor retry, evaluator access, or mutation authority.
No current fixture establishes that negative-capability claim.

## Remediation is a different experiment

Reviewer-assisted remediation is Phase 2, not a flag on the reporter-only
session. It must begin from the same matched frozen base under a separately
frozen intervention, explicit edit/tool authority, budget and attempt identity.
Its estimand concerns repair benefit and cost, not reporter accuracy. Alpha.10
does not implement a remediation runner or generic reporter framework before a
real owner adapter and sacrificial task pack exist.

## Deterministic development fixtures

Run the current semantic and binding checks with:

```bash
uv run python tools/check_completion_integrity_claim.py \
  --policy studies/completion-integrity/terminal-claim-v1/policy.pilot.json \
  --cases studies/completion-integrity/terminal-claim-v1/fixtures/cases.json \
  --assessments-json studies/completion-integrity/terminal-claim-v1/fixtures/expected-assessments.json \
  --check
```

The fixtures cover accurate completion, false completion, uncertainty awaiting
clarification and a supported external blocker. They are synthetic known-state
tests, not scored agent observations or evidence that the policy improves
outcomes.

## Evidence boundary and next proof

`ael.completion_integrity_claim` is pure family policy. The file adapter owns
strict JSON and byte hashes. The existing enactment policy remains a different
predicate: it asks whether normalized process evidence represents the declared
chain, not whether the terminal claim is true.

Promotion requires a real owner-captured vertical slice, privacy and capability
audit, sacrificial task qualification, a pack-specific justified sample-size
plan, and a separately authorized freeze. Alpha.9 policy, runner, result and
frozen evidence remain unchanged.
