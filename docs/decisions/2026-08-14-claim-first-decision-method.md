# Claim-first decision method replaces scalar claim authorization

- Date: 2026-08-14
- Status: accepted for `v0.1.0-alpha.8`
- Scope: method policy, public result projection, and roadmap

## Problem

Contract v0 retains one `evidence_level` value whose vocabulary spans artifact
integrity, runtime conformance, controlled effects, reproduction, transfer,
external use, payment, and downstream outcomes. The alpha.7 public projection
converted claim classes and those heterogeneous states into numeric ranks, used
the rank as a claim ceiling, and presented the resulting evidence label as a
headline.

That is not only a presentation problem. Evidence that a result changed an
external decision does not by itself establish transfer, and paid repeated use
does not by itself establish a measured outcome. A higher-looking value on one
predicate must not authorize a claim in another.

The repository already keeps study-design preflight, public graph checks,
maintainer rerun, independent replication, action, outcome, and freshness
separate. It should apply the same rule to claim authorization and public
reading order.

## Decision

Alpha.8 introduces a claim-first Method Policy over the existing five Contract
v0 objects.

1. Claim classes are admitted by explicit evidence-state and study-design
   predicates, never a numeric rank.
2. Causal, stack, transfer, and outcome claims require claim-local Measurement
   Set evidence in addition to their study-level predicates. Transfer evidence
   must resolve through a run to a transfer task pack; outcome evidence must
   resolve to an outcome measurement. Transfer and outcome claims still
   require their own receipt evidence predicates.
   `externally_decision_changing` and `paid_repeated_use` do not act as aliases.
   Transfer additionally requires a transfer task-pack role; outcome requires
   an outcome measurement; independently verified outcome evidence requires a
   matching independent ownership label.
3. Factor-causal and model-only claims require a controlled-factor design;
   model-only claims additionally require the changed intervention class to be
   model-only. Operational-stack claims require an operational-stack design.
4. Contract v0 `evidence_level` remains byte-compatible machine metadata. Human
   cards call it a **receipt evidence state**, place it in technical disclosure,
   and do not present it as a grade or index column.
5. Public cards lead with the decision and selected claim statements/statuses.
   A supported, contradicted, bounded, or unresolved claim remains first-class.
6. The publication profile explicitly marks the non-empty subset of selected
   receipt claims that governs the displayed disposition. Additional selected
   workflow/artifact claims remain visible but cannot make a rejected effect
   look positive in the Results Index.
7. Study Quality is renamed **Study design preflight** on public cards.
   Its `reliability_coverage` value is rendered as planned coverage.
8. Completed run and measurement records separately expose valid repeat
   coverage and whether uncertainty intervals were actually reported. Those
   facts do not become a synthetic reliability grade.
9. The live receipt renderer uses the same non-ordinal labels as result cards.
   Contract JSON names and frozen historical Markdown do not change.

The result profile and projection policy advance to `0.5`. Contract v0 schemas,
historical receipts, reports, runs, measurements, freezes, and study decisions
remain unchanged.

## Method lifecycle and ownership

```text
question framed
→ design admitted
→ study frozen
→ observations retained
→ evaluated claims and receipt issued
→ owner decision recorded
→ action verified, blocked, or not performed
→ outcome observed, missing, cancelled, or revalidation due
```

- Contract v0 owns experimental identity, observations, evaluated claims,
  receipt disposition, limits, and invalidation triggers.
- Method Policy owns claim-admissibility and interpretation rules.
- Study-family adapters own task meaning, evaluator postconditions, effect
  calculation, and any experimental lifecycle shapes.
- The operational owner owns adoption, action, and real outcomes.
- The publication catalog selects and renders authority; it cannot create it.

`receipt.decision`, an effect decision, an owner adoption decision, an action,
and an outcome observation are related but distinct acts. Corrections create a
new revision or invalidation record; they do not rewrite historical evidence.

## Council consultation ledger

Two independent read-only profiles reviewed one factual brief:

- `domain_model_cartographer` — finding `AEL-DM-20260814-01`;
- `evolutionary_deep_pragmatist` — finding
  `AEL-EDP-METHOD-20260814-01`.

Both rejected Contract v1, a sixth stable object, a generic Decision Case CLI,
a composite support score, and retrospective quality certification. The domain
lens proposed a named derived Claim-Support Envelope; the pragmatist preferred
only a claim-first projection. The integrated decision keeps a versioned policy
and derived presentation inside the existing projection but does not persist or
advertise another envelope object.

## Strongest rejected alternatives

### New Decision Case sidecar

The Systematic Debugging lifecycle demonstrates useful fields, but its current
validator is tied to one exact B0/S1, four-task, eight-cell study. Generalizing
that shape now would stabilize incidental structure before a second study
family exists.

### Contract v1

No Contract byte change is required to correct public claim authorization.
Changing the five schemas would add migration cost and historical ambiguity
without adding evidence.

### Documentation only

Documentation would leave the numeric authorization executable. The smallest
defensible fix therefore changes the pure projection policy and its tests.

### Wait for the next scored study

A prospective study would provide valuable empirical shape, but the current
authorization defect is already known and reversible to fix. Alpha.8 remains
bounded; the next study is still the test of whether the method changes real
decisions.

## Compatibility and reversal

- Existing Contract objects and source evidence stay byte-identical.
- Machine cards retain the original `evidence_level` value.
- Generated result cards and the machine index intentionally change under
  projection `0.5`.
- The profile-only `decision_claim_ids` field must be a non-empty subset of
  `claim_ids`; it classifies presentation and creates no new receipt claim.
- Revert the public ordering or simplify the policy if a comprehension test
  shows worse decisions.
- Reconsider a serialized support object only after two materially different
  prospective studies require the same fields and an external consumer needs
  the shape.

## Missing evidence

- no prospective profiled scored study exists;
- no independently owned replication exists;
- no completed downstream follow-up exists;
- no reader study has compared scalar-led and claim-first cards.
- claim-local reference resolution proves graph binding, not that the metric
  semantically entails the claim or that a transfer population is representative.

Those gaps limit the release claim. Alpha.8 corrects method semantics; it does
not prove that AEL improves agent systems or user decisions.
