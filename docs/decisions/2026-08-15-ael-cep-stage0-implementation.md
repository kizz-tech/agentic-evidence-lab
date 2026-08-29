# AEL-CEP Stage 0 implementation boundary

Date: 2026-08-15
Status: accepted implementation boundary; empirical method remains provisional

## Context

Agentic Evidence Lab can already freeze a study, retain run and measurement
records, issue a bounded receipt, and audit several family-local prospective
contracts. It cannot yet identify an evaluator as an independently versioned
release, add a later score without rewriting history, govern evaluator bridges,
account for task exposure, or keep promotion authority outside an adaptive
Builder--Evaluator loop.

Those omissions make a closed recursive-improvement loop scientifically
ambiguous. A higher score can mean better subject behavior, a changed ruler,
shared blind spots, evaluator exploitation, or adaptive holdout exhaustion.

The owner selected evaluator coevolution as AEL's next central research
direction and authorized a complete local implementation. Publication, hosted
model calls, hidden task disclosure, effectful execution, and an empirical
superiority claim remain separate actions.

## Decision

Implement **AEL Coevolution Protocol 0.2-development (AEL-CEP)** as a
family-local protocol beside Contract v0.

Contract v0 remains exactly its five released document types. AEL-CEP uses a
separate validator and schema namespace until at least two materially different
prospective task families demonstrate a stable shared boundary.

The dependency direction is:

```text
CLI / tool -> coevolution_bundle -> coevolution_simulator -> coevolution
                               \---------------------------> coevolution
```

- `ael.coevolution` is pure policy. It owns identities, binding rules,
  append-only ledger semantics, replay classification, exposure and revocation
  projections, evaluator bridges, causal contrast eligibility, independence
  ceilings, and the promotion reducer.
- `ael.coevolution_simulator` is a deterministic no-effect producer. It owns
  only the declared synthetic world and A0--A5 trajectory generation.
- `ael.coevolution_bundle` owns strict JSON, files, raw bytes, schemas, size and
  path limits, atomic materialization, and check mode. It does not decide
  promotion or comparability.
- The CLI is a thin adapter. It does not import a runner or provider SDK on the
  AEL-CEP path.

`ael.coevolution` must not import filesystem, CLI, process, network, provider,
sandbox, runner, Contract validation, result projection, ambient clock, or
ambient randomness facilities.

## Bounded contexts

The implementation retains five ownership boundaries without turning them
into services:

1. **Adaptive Development** owns Builder, Evaluator, and Challenger candidate
   releases and trajectory proposals.
2. **Task Governance** owns prospective intake, task partitions, exposure,
   sealed confirmation, and custody declarations.
3. **Evidence Kernel** owns immutable execution evidence, score runs, lineage,
   and deletion tombstones.
4. **Measurement Science** owns measurement methods, evaluator bridges, and
   comparability decisions.
5. **Release Governance** owns measurement epochs and promotion transitions.

No adaptive role owns evidence history, anchor custody, or promotion authority
inside the epoch it is optimizing against.

## Artifact model

Stage 0 has two logical artifact families:

1. `ProtocolFreeze` freezes the epoch, authorities, prospective intake,
   partitions, release requirements, six arms, pairwise estimands, algorithms,
   budgets, missingness and stopping policy, replay policy, bridge tolerances,
   independence requirements, promotion automaton, scenarios, and deterministic
   seed.
2. `TrajectoryBundle` is an immutable successor bundle containing individually
   identified and content-addressed ledger records plus a derived assessment.

The ledger is a hash chain. Every record binds its epoch, sequence,
predecessor, dependency hashes, type, payload, and domain-separated canonical
hash. A successor bundle names an immediate predecessor, preserves every
predecessor record byte-for-byte, and appends new records. The strict adapter
accepts an arbitrary ordered genesis-to-immediate-predecessor chain and checks
each link; it does not discover, rewrite, or truncate history. Derived indexes
and reports are projections, not authority.

The evaluator-independent evidence graph is explicit:

```text
SubjectExecutionEvidence
        │ evidence_ref/evidence_hash
        ▼
EvaluationBinding
        │ binding_ref/binding_hash
        ▼
ScoreRun
```

`SubjectExecutionEvidence` is retained before scoring and contains no evaluator
identity. `EvaluationBinding` freezes the Builder, Evaluator, method, task,
runner/environment, analysis, promotion policy, exposure state, and epoch.
`ScoreRun` binds that exact binding and evidence to the evaluator identity and
the frozen adjudication/scoring authority. Rescoring appends a new release,
binding, and score; it cannot overwrite an earlier fact.

An evaluator bridge is a retained whole-panel artifact. The frozen Stage 0
panel contains the five weighted strata `good`, `bad`, `exploit`,
`semantic_mutant`, and `near_threshold`. Each stratum carries evaluator-
independent B0/B1 evidence, four actual score runs (`B0×E0`, `B0×E1`,
`B1×E0`, `B1×E1`), and arm-blinded B0/B1 anchor observations. The validator
recomputes weighted global shift, interaction, score decision agreement, and
anchor agreement from values relative to the frozen decision threshold; a
status-only anchor match or an unbacked scalar cannot establish comparability.
For each stratum it derives `G_s`, `I_s`, evaluator decision agreement, and
anchor decision agreement from the four score cells and two anchor values.
Every stratum must pass all four gates; weighted aggregates are reported but
cannot cancel a failing stratum. Each B0/B1 anchor binds the exact
corresponding `SubjectExecutionEvidence` reference and hash. The bridge is
`bridge_comparable` only when the complete panel satisfies its frozen
tolerances and agreements.

Stage 0's `synthetic_pass`/`synthetic_fail` construct and reliability fields are
fixture statuses for policy execution, not empirical calibration, reliability,
or validity evidence.

Promotion state is keyed independently by `(candidate_ref,candidate_hash)`.
Each candidate has its own append-only transition chain and exact predecessor
transition hash; the projection exposes `promotion_states`, with the legacy
single `promotion_state` view retained only for a singleton candidate set.

The adapter's input ceilings are 2 MiB per JSON or Markdown file, 2,048 ledger
records, and 10,000 dependency edges per bundle (with bounded JSON and
predecessor-chain depth). These are fail-closed Stage 0 limits, not a claim of
production-scale storage capacity.

Record variants cover:

- Builder, Evaluator, Challenger, and Anchor releases;
- measurement methods and exact evaluation bindings;
- subject execution evidence and score runs;
- exposure and confirmation-consumption events;
- bridge observations and comparability decisions;
- per-claim independence assessments;
- promotion transitions;
- first-class `effect_attempt` facts and their containment transitions;
- trajectory and operating-characteristic summaries;
- deletion tombstones.

Historical scores are never overwritten. A later evaluator produces a new
binding and `ScoreRun` beside the old score. Current score, comparability,
taint, promotion, and revocation are computed projections over immutable facts.

## Non-compensating invariants

The implementation fails closed when any of these conditions is not proven:

- every critical prospective-intake field is present and hash-bound;
- anchor, confirmation, adjudication, and promotion custody are known and meet
  the epoch's per-claim independence ceiling;
- `confirmation_eligible` is pre-confirmation and must not consume or anchor;
  if it passes, exactly one candidate-bound sealed confirmation pack is
  materialized, then irreversibly reserved/marked used by the frozen authority
  before exactly one final decision (`promote`, `narrow`, `abstain`, or `reject`),
  with the anchor observation following consumption. A recorded exposure blocks
  a positive `promote` only when its target resolves to the sealed confirmation
  task root before that decision. Screening and bridge exposures remain allowed
  under their own budgets and lifecycle; off-ledger leaks remain an operational
  residual;
- Builder, Evaluator, task, method, runner/environment, analysis, promotion,
  and exposure identities match the exact `EvaluationBinding`;
- every pairwise causal contrast has hash-equal eligibility, proposal
  admission, selection/ranking, and stopping algorithms and matched total-system
  budgets except for its one declared treatment;
- every ledger predecessor and dependency exists, precedes the child, and has
  the declared hash;
- confirmation consumption is opened by the exact frozen confirmation
  principal, and `anchor_observation` is arm-blinded, binds the same candidate
  and single-use consumption, is adjudicated by the frozen anchor principal,
  and uses the frozen anchor release custody;
- every `ScoreRun` is scored by the frozen adjudication principal, which cannot
  equal evaluator custody; a data-only rescore uses that same authority;
- promotion approval is issued by the frozen promotion principal and the
  transition actor is distinct from the approval actor;
- rescoring has the retained evidence surface required by the new evaluator;
- a bridge passes its frozen transition, uncertainty, construct, reliability,
  and anchor rules before two evaluator generations are called comparable;
- a promotion transition is legal from the exact prior transition hash and no
  protected independence dimension is `overlap` or `unknown`;
- no ancestor is tombstoned or tainted in a way that invalidates the claim;
- every Stage 0 `effect_attempt` is explicitly `blocked` with
  `postcondition_status=not_dispatched`; an accepted or applied effect is
  rejected by the frozen policy. A blocked attempt must be contained by a
  candidate-keyed rejection/revocation transition and cannot silently enable
  promotion.

The five principals are distinct frozen role-level authorities. A release may
reuse its role's custody across generations; that same-role reuse is allowed,
while cross-role authority and custody checks remain exact. Role separation is
an implementation invariant, not evidence of organizational or incentive
independence.

Unknown critical custody, missing evidence, ambiguous effects, reused
confirmation, evaluator self-certification, and a failed bridge block
promotion. They are not averaged away by a better score. A failed or uncertain
bridge from `bridge_eligible` moves to `new_measurement_epoch` without opening
confirmation. Early revoke from an eligible state requires an exact
authority-bound `deletion_tombstone` and is terminal containment.

## Bounded recursion

- L0: Builder execution creates subject evidence.
- L1: Evaluator creates a score run.
- L2: protected anchor or meta-audit assesses the Evaluator and bridge.
- L3: the frozen constitution plus executable, human, or delayed-outcome
  reference governs promotion.

An Evaluator release cannot approve itself. Changing the anchor or constitution
creates a new measurement epoch. A failed bridge starts a new measurement
series and leaves earlier observations intact.

## Stage 0 experiment

The deterministic simulator compares replicated trajectories for:

- A0: fixed Builder and fixed Evaluator;
- A1: evolving Builder and fixed Evaluator;
- A2: fixed Builder and evolving Evaluator;
- A3: naive closed Builder--Evaluator loop;
- A4: custody-separated Builder, Evaluator, and Anchor;
- A5: Builder, Evaluator, Challenger, and Anchor.

Its adversarial scenarios include a true null, real improvement, shared blind
spots and evaluator exploitation, feedback leakage and optional stopping,
drift/reversal/forgetting/missingness, poisoning, deletion, and forbidden
effect attempts. `effect_attempt` is a first-class immutable record bound to a
candidate, subject evidence, evaluation binding, observation authority, effect
request hash, and idempotency hash. The frozen forbidden-effect scenario emits
a second independently keyed blocked candidate chain as well as the primary
chain; it never dispatches an external effect. The simulator reports
prospective utility at matched declared cost, false promotion, useful-candidate
power, critical failures, exploit acceptance, bridge reversals, taint,
missingness, quarantine, and revocation completeness.

Optional-stopping diagnostics use one denominator unit per replicate. The
matched-cost record preserves the declared fixed-N work plan and records actual
executed task count separately, so early stopping changes actual task cost and
marks that causal contrast ineligible. Every exact task/scenario/arm
`trajectory_summary` row is followed by one dependency-bound
`contrast_summary` seal that depends on all row refs/hashes. The kernel derives
`operating_metrics`, `primary_endpoints`, and `contrast_diagnostics` only from
that live seal; duplicate or nested summary fallbacks are forbidden.

The operating metrics are summed across rows. With
`invalid_promotions = promotion.null + promotion.harmful + promotion.adversarial`,
`false_promotion_share = invalid_promotions / sum(promotion.*)`, while
`invalid_candidate_promotion_rate = invalid_promotions /
(candidate_opportunities.null + candidate_opportunities.harmful +
candidate_opportunities.adversarial)`. Candidate opportunities are distinct
from task-level disposition counts; the first rate's denominator is all
candidate promotions, and a zero denominator is unknown. Primary
endpoints retain exact `sum_ppm`/`observed_count` and integer half-up `mean_ppm`.
Contrasts with complete compared arm/scenario endpoints but optional stopping
or actual-cost mismatch are `diagnostic_only`; any missing endpoint takes
precedence as `not_estimable`, and otherwise a complete contrast can be
`causal_eligible`. The deltas are descriptive unless eligible.

The simulator uses an explicit versioned PRNG, simulated clock, fixed seeds,
and canonical JSON. Identical inputs must produce byte-identical outputs on all
supported Python versions.

Bridge anchors use an independent named `anchor_truth` stream. The simulator
first emits B0/B1 subject evidence and protected anchor observations, then in a
second ledger phase emits evaluation bindings and score cells. Consequently,
evaluator-cell perturbations cannot change already committed evidence or anchor
bytes/hashes or their thresholded decisions. On a positive A5 trajectory,
promotion targets the bridge's new Builder generation B1.

If the `contrast_summary` seal is revoked, tainted, or unscorable, all current
derived metrics, endpoints, and diagnostics are unavailable. The adapter does
not fall back to nested or stale summaries and never rewrites the historical
fact. Sufficient-stat arithmetic and hash closure verify only materialized rows
and graph links; they do not prove unmaterialized external raw events, empirical
validity, real custody, or production safety.

## Replay and retention

The policy distinguishes:

- `rescorable`: retained observation surfaces satisfy a new evaluator;
- `deterministic_replayable`: retained inputs and mocked effects can reproduce
  a code path, but do not prove current external behavior;
- `historical_only`: the fact happened then but required evidence is unavailable
  or revoked;
- `rerun_required`: Builder, model, prompt, tools, retrieval, environment, or
  external world behavior changed.

A deletion tombstone never deletes history silently. It records authority and
scope, and the revocation projection marks every declared descendant
`revoked` or `unscorable`. Real private payload retention, encryption, access
control, and deletion remain owner-system responsibilities outside Stage 0.

## CLI and materialization

The family-local CLI has three explicit operations, documented with exact
arguments in [Reproducibility](../reproducibility.md):

- `coevolution simulate PROTOCOL.json --bundle-output BUNDLE.json
  --report-output REPORT.md [--check]` produces or byte-checks the deterministic
  no-effect bundle and descriptive report;
- `coevolution check PROTOCOL.json BUNDLE.json [--predecessor PATH ...]
  [--report REPORT.md --check-report]` validates a bundle and optionally
  byte-checks its projection;
- `coevolution rescore PROTOCOL.json SOURCE.json REQUEST.json --output
  SUCCESSOR.json [--predecessor PATH ...] [--check]` appends a data-only
  evaluator release/binding/score without mutating the source.

Repeated predecessor paths are supplied oldest genesis first and terminate at
the immediate predecessor. The library materializer is
`ael.coevolution_bundle.materialize_bundle`; it performs the same strict
validation and atomic write/check semantics. No operation invokes a runner,
provider, network, or model.

## Compatibility and release state

- No Contract v0 schema or released alpha.11 evidence byte may change.
- AEL-CEP JSON is excluded from generic `ael validate`; it is checked by its
  dedicated command.
- Historical receipts cannot be backfilled with evaluator identity or upgraded
  claims. A future adapter may render missing historical identity explicitly as
  unknown.
- A code-bearing publication requires a new package version and release. Local
  implementation and validation do not prove a commit, push, tag, publication,
  organizational custody, empirical validity, superiority, transfer, or
  production safety.

## Reversal and evolution path

The change is additive. It can be disabled by removing the family-local command
and modules while retaining generated bundles as experimental history.

Stage 1 may add a read-only adapter from eligible historical AEL artifacts.
Stage 2 may replace simulated producers with one prospective runner adapter.
Stage 3 may admit a quarantined Challenger. Contract v1 requires a separate
migration decision after a second task family confirms the stable identities
and invariants.

## Engineering council record

Route: expanded council. Four independent first passes completed.

- `clean_boundary_architect` — `CEP-CB-01`
- `domain_model_cartographer` — `CEP-DM-01`
- `evolutionary_deep_pragmatist` — `CEP-EDP-01`
- `production_systems_sentinel` — `CEP-PSS-01`

The advisors agreed on the family-local boundary, immutable addressed ledger,
pure-policy dependency direction, fail-closed custody and promotion, and
deferral of Contract v1 and effect-capable infrastructure. No targeted challenge
was required. The strongest rejected alternative was immediate Contract v1;
it would stabilize untested boundaries and expand the compatibility blast
radius before cross-family evidence exists.
