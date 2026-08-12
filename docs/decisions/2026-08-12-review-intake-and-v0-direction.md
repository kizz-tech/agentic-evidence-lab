# Decision: external review intake and Contract v0 direction

Date: 2026-08-12  
Status: accepted for the pre-schema design phase; not a frozen public contract  
Decision owner: project owner  
Evidence relationship: model critique with bounded primary-source verification

## Context

Three external critiques tested competitive substitution, a possible commercial
offer, and the Council Generation 2 experimental design. Their exact private
captures are content-addressed by these SHA-256 values:

- competitive: `3339278855103c351a9413035c7a8f6abc91a449fafaea4d902890abacc6edb3`;
- commercial: `59049afddb9efaec610f5c6e03360e02cd536b68beac8b06399794fb441b2544`;
- methodology: `07f4e7bf37362112e1c540f7ada6dbcb8f66d2268c60ed541a31a52ee33a126e`.

The raw responses remain private because verbatim publication permission and
their exact context boundary are not established. A model critique is an
argument source, not independent validation.

## Decision

### Accepted

1. Agentic Evidence Lab will own the evidence protocol: intervention and
   baseline identity, adaptation and confirmation boundaries, causal and
   stack-level claim scope, roles and independence, receipt invalidation, and
   decision/reversal semantics.
2. Execution, sandboxing, tracing, and experiment-ledger products are candidate
   substrates behind adapters. Contract v0 remains file/Git-first and must emit
   a useful receipt without a hosted platform, database, or custom generic
   runner.
3. Council Generation 2 should use a strong sequential non-Council baseline
   with the same factual knowledge union, separate adaptation from untouched
   holdout, freeze one candidate before confirmation, preserve failed runs, and
   disclose every author/evaluator/runner role overlap.
4. External product and benchmark claims must bind the canonical page or exact
   paper revision used. Current documentation supports substantial execution
   overlap, and SkillsBench v4 makes intervention breadth alone an insufficient
   uniqueness claim.

### Deferred pending evidence

1. Selection of Inspect AI or another execution substrate and Braintrust,
   LangSmith, or another ledger. Each candidate must pass a bounded adapter
   spike against the AEL contract before adoption.
2. Exact Council Generation 2 run counts, effect thresholds, cost/rework gates,
   confidence bounds, evaluator agreement cutoffs, and wall-clock caps. These
   require Gen1 telemetry, actual task inventory, evaluator capacity, and a
   simulation or equivalent operating-characteristic analysis.
3. Private agent release assurance as a commercial product. It is retained as
   a falsifiable future option but does not shape the current open-research v0.

### Not accepted as facts

- that exactly 80–90% of AEL is already implemented elsewhere;
- that the proposed buyer, price, run count, labor hours, model cost, purchase
  frequency, or 90-day conversion thresholds describe current demand;
- that a 12-task holdout or three-task screening set is statistically adequate;
- that AEL is unique merely because it evaluates interventions broader than
  skills;
- that any external review validates product demand or Council effectiveness.

## Smallest authorized changes

- refine the Contract v0 brief with an adapter boundary, revision pins, and a
  calibration gate;
- mark the first external-review intake complete;
- preserve the current owner intent: open research and better internal
  engineering decisions before monetization;
- leave Council source and its Generation 2 manifest unchanged until Council's
  owner explicitly applies a calibrated design.

## Validation and reversal

This decision is locally validated when the three private captures reproduce
the recorded hashes, the review process points to this decision, and Contract
v0 contains the accepted boundaries.

Revisit it if an adapter spike cannot preserve the contract, if a current
platform provides equivalent decision and receipt semantics, if statistical
calibration supports a different Council design, or if the owner separately
changes the commercialization priority.

No experiment result, public release, external review, or market outcome is
claimed by this decision.
