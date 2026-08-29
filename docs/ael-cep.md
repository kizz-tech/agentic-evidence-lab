# AEL Coevolution Protocol

Status: `0.2-development`, Stage 0 no-effect method foundation (alpha.12)

AEL-CEP is AEL's protocol for studying systems whose ability to perform work
and ability to measure that work both change over time.

The protocol does not assume that mutual Builder--Evaluator improvement is real
improvement. It makes that question testable while keeping evidence history,
protected anchors, and promotion authority outside the adaptive loop they
govern.

```text
Builder population ───────┐
Evaluator population ─────┼──> cross-play and evolutionary trajectories
Challenger population ────┘                    │
                                               ▼
                                    immutable evidence ledger
                                               │
                         protected prospective anchor / referee
                                               │
                    promote · narrow · abstain · reject · revoke
```

Stage 0 is deliberately offline and synthetic. Its deterministic fixture
exercises the enumerated local policy rules under declared inputs. A passing
fixture and its arithmetic/hash closure do not prove unmaterialized external
raw events, empirical validity, real custody or holdout secrecy, model
improvement or superiority, transfer, novelty, or production safety.

## The invariant

Builder, Evaluator, and Challenger releases may evolve inside a measurement
epoch. The following may not evolve inside that same epoch:

- evidence history;
- the prospective intake and partition policy;
- anchor and confirmation custody;
- the promotion constitution and authority;
- the analysis, algorithm-matching, budget, and stopping rules.

Changing one of those authorities creates a new epoch. A new epoch does not
rewrite the old series.

The recursion ceiling is explicit:

- L0 — a Builder execution creates subject evidence;
- L1 — an Evaluator creates a score run;
- L2 — a protected anchor or meta-audit assesses the Evaluator and bridge;
- L3 — the frozen constitution plus executable, human, or delayed-outcome
  reference governs promotion.

An Evaluator cannot approve itself. Declared role names are not proof that real
organizations, credentials, providers, models, data, or incentives are
independent.

## Identity and evidence

An evaluator is a release artifact, not a free-text label:

```text
EvaluatorRelease
= implementation + prompt/rubric + model identity
+ parser/aggregation + tools/environment
+ calibration lineage + known error envelope
+ custody + allowed evidence surface
```

One evaluation binds the exact subject, evaluator, method, tasks, runner,
analysis, promotion policy, and exposure state. Subject evidence is created
before evaluator scoring and does not acquire evaluator identity by inference:

```text
SubjectExecutionEvidence (evaluator-independent)
              │ exact evidence_ref/evidence_hash
              ▼
EvaluationBinding
= BuilderRelease + EvaluatorRelease + MeasurementMethod
+ TaskPackRevision + environment/runner
+ analysis/promotion policy + exposure state + epoch
              │ exact binding_ref/binding_hash
              ▼
ScoreRun
= binding + subject evidence + evaluator identity + scoring authority
```

`SubjectExecutionEvidence`, `EvaluationBinding`, and every `ScoreRun` are
separately identified and content-addressed. A score is therefore not a
mutable property of an answer. A later evaluator appends a new release,
binding, and `ScoreRun` beside the old one. It never relabels or overwrites the
earlier verdict.

The Stage 0 ledger is a content-addressed hash chain. Records bind their exact
predecessor and dependency hashes. A successor bundle names its immediate
predecessor and preserves that predecessor's records byte-for-byte before
appending new facts. The filesystem adapter accepts an arbitrary ordered
genesis-to-immediate-predecessor chain (one `--predecessor PATH` per link) and
validates every link; it never discovers, rewrites, or truncates history.
Reports and current-state views are disposable projections over that history.
Promotion state is also scoped to the candidate key
`(candidate_ref,candidate_hash)`: separate candidates never share a reducer
chain or inherit one another's transition hash. The projection exposes the
complete `promotion_states` map; the compatibility `promotion_state` field is
present only when exactly one candidate is represented.

The strict adapter enforces a 2 MiB maximum for each JSON or Markdown file,
2,048 records per bundle, and 10,000 dependency edges per bundle. It also
rejects unsafe paths/symlinks and bounds JSON depth and predecessor-chain depth;
these are fail-closed input ceilings, not guarantees that a larger production
ledger is supported.

## Custody and scoring authority

The frozen protocol names five distinct principals: evidence, confirmation,
anchor, adjudication, and promotion. Each principal has an exact
`principal_id`, `custody`, independence declaration, and lineage. The kernel
checks the authority at the record that uses it:

- `confirmation_consumption.authority` must equal the frozen confirmation
  principal;
- `anchor_observation.authority` must equal the frozen anchor principal,
  `arm_blinded` must be true, and the referenced anchor release custody must
  equal the frozen anchor custody;
- `score_run.scoring_actor` must equal the frozen adjudication principal and
  must not equal the evaluator release custody;
- a data-only rescore must be issued by that same adjudication principal and
  cannot be self-certified by the new evaluator custody;
- a promotion `approval_actor` must equal the frozen promotion principal, while
  its transition `actor` must be a distinct actor.

Role names in JSON are not evidence of real organizational, credential,
provider, model, data, or incentive independence. Unknown or overlapping
protected dimensions fail the promotion reducer.

The five principals are distinct frozen role-level authorities. A Builder or
Evaluator release may reuse its role's custody across generations; generation
reuse does not collapse the cross-role boundary, and the kernel still checks
the exact authority and custody on every record. This is a local role-binding
invariant, not evidence of organizational or incentive independence.

## Stage 0 materialization and checks

The dedicated CLI keeps AEL-CEP outside the generic Contract v0 validator. A
generic `ael validate` invocation does not accept a CEP directory or treat its
sidecar records as Contract v0 input; use `ael coevolution check` for the
protocol/bundle boundary. The exact commands are:

```bash
# Produce the deterministic no-effect bundle and Markdown projection.
uv run ael coevolution simulate PROTOCOL.json \
  --bundle-output TRAJECTORY-BUNDLE.json \
  --report-output TRAJECTORY-REPORT.md

# Recompute and check an existing bundle/report without changing source bytes.
uv run ael coevolution check PROTOCOL.json TRAJECTORY-BUNDLE.json \
  --report TRAJECTORY-REPORT.md --check-report

# Append a data-only evaluator rescore into a new successor bundle.
uv run ael coevolution rescore PROTOCOL.json SOURCE-BUNDLE.json RESCORE-REQUEST.json \
  --output SUCCESSOR-BUNDLE.json
```

For a non-genesis source, repeat `--predecessor PATH` in oldest-to-immediate
order on `check` or `rescore`; the output path must be distinct from every
input. `simulate --check` checks exact existing bundle and report bytes. The
`rescore --check` form checks an already materialized successor rather than
rewriting it. Repository-owned tooling currently uses
`ael.coevolution_bundle.materialize_bundle(...)`, but the Python module and
signature remain experimental internals. The supported alpha.12 boundary is
the CLI plus versioned file/schema formats; there is intentionally no separate
effectful runner or provider path.

## Task governance and exposure

The frozen task population has five distinct partitions:

| Partition | Purpose | Promotion authority |
|---|---|---|
| Development | Full adaptive feedback | None |
| Adaptive screening | Bounded selection feedback | None |
| Bridge | Evaluator comparability | None |
| Sealed confirmation | One frozen release decision | Single use |
| Historical | Regression and description | None |

The prospective intake must name the target population and use, intake and
sampling custodians, sampling frame and method, eligibility and deduplication,
window and cutoff, censoring and late-arrival rules, oracle, adjudication and
appeal, utilities, harms, weights, margins, arm blinding, allocation proof, and
exposure policy. A missing or unknown critical field prevents confirmation
freeze.

Any revealed task, score, rank, pass/fail, threshold result, comment, or manual
disclosure creates an exposure event. `confirmation_eligible` is a
pre-confirmation state: it does not consume confirmation and does not create an
anchor. If the candidate remains eligible, exactly one candidate-bound sealed
confirmation pack is materialized. `confirmation_consumption` irreversibly
reserves and marks that pack used, under the frozen confirmation authority,
before exactly one final decision (`promote`, `narrow`, `abstain`, or `reject`);
the anchor observation follows that consumption. A recorded exposure blocks a
positive `promote` only when its target resolves to the sealed confirmation
task root before that decision. Screening and bridge exposures remain allowed
under their own budgets and lifecycle. Off-ledger leaks remain an operational
residual;
the fixture does not prove their absence. Historical reuse remains useful, but
it is not fresh confirmation.

## Rescore, replay, and rerun

AEL-CEP distinguishes four operations:

| Class | What is reused | What it can establish |
|---|---|---|
| `rescorable` | Retained subject evidence | How a new evaluator interprets the old observation |
| `deterministic_replayable` | Retained inputs and mocked effects | Compatibility with preserved history |
| `historical_only` | The immutable fact record | What happened then, within its old scope |
| `rerun_required` | Nothing substitutes for a new run | Current behavior after a subject or world change |

Evaluator, rubric, parser, or aggregation changes can be rescorable only when
the new evaluator's required surfaces were retained and remain unrevoked.
Builder, model, prompt, tools, retrieval, environment, or external-world
changes require a new subject run. Deterministic replay cannot establish
current provider or world behavior.

Private raw payloads may have a shorter retention boundary than the sanitized
ledger. A deletion tombstone records authority and scope, then projects every
declared descendant as revoked or unscorable. It does not silently erase the
historical fact that a record once existed.

## Evaluator bridges

Changing an evaluator changes the ruler. Direct longitudinal comparability is
therefore denied by default.

A bridge is a whole-panel measurement, not a scalar link. The frozen Stage 0
panel has five weighted strata: `good`, `bad`, `exploit`, `semantic_mutant`,
and `near_threshold`; the weights are protocol-bound and must sum to one. For
every stratum it retains evaluator-independent B0 and B1 evidence, four actual
`ScoreRun` cells (`B0×E0`, `B0×E1`, `B1×E0`, `B1×E1`) bound to that retained
evidence, and arm-blinded B0/B1 anchor observations. The validator recomputes
the weighted global shift and interaction, score decision agreement, and
anchor value/decision-threshold agreement from those cells. A synthetic scalar
or an unbacked bridge summary is not comparable evidence.

For stratum `s`, the kernel derives the global shift `G_s`, interaction `I_s`,
evaluator decision agreement, and anchor decision agreement from the four
observed cells and the two observed anchor values. Every stratum must pass its
own tolerances and agreement margins; the weighted panel summary is also
reported, but one stratum's strong result cannot cancel another stratum's
failure. Each `b0_anchor` and `b1_anchor` binds the exact retained
`SubjectExecutionEvidence` reference and hash for B0 or B1 respectively.

The bridge also binds construct and reliability evidence and exact uncertainty
intervals. Anchor agreement is based on the observed anchor values and the
frozen decision threshold, not on a free-form status label. This makes a
status-only anchor match insufficient for bridge comparability.

Stage 0's `synthetic_pass`/`synthetic_fail` construct and reliability fields are
fixture statuses used to exercise the reducer. They are not empirical
calibration, reliability, or validity evidence.

The bridge outcome is one of:

- `bridge_comparable` — the frozen equivalence and decision rules passed;
- `linked_with_uncertainty` — a bounded descriptive link is retained, but
  promotion cannot treat the scales as interchangeable;
- `new_epoch_not_comparable` — a new measurement series is required.

The diagnostic interaction remains useful:

```text
delta_E0 = score(B1, E0) - score(B0, E0)
delta_E1 = score(B1, E1) - score(B0, E1)
interaction = delta_E1 - delta_E0
```

If only the new evaluator sees improvement and the anchor does not, the result
is evidence of co-adaptation, not evidence of subject improvement.

## Causal trajectory comparison

Stage 0 models six repeated evolutionary trajectories:

1. A0 — fixed Builder and fixed Evaluator;
2. A1 — evolving Builder and fixed Evaluator;
3. A2 — fixed Builder and evolving Evaluator;
4. A3 — naive closed Builder--Evaluator loop;
5. A4 — custody-separated Builder, Evaluator, and Anchor;
6. A5 — Builder, Evaluator, Challenger, and Anchor.

For any declared pairwise estimand, eligibility, proposal admission,
selection/ranking, stopping, task exposure, analysis, and total-system budgets
must have identical hashes except for exactly one declared treatment dimension.
A mismatch makes that comparison ineligible. It is not repaired by statistical
adjustment after the fact.

Total-system cost includes Builder, Evaluator, Challenger, anchor, confirmation,
human, and governance work. A5 cannot receive a free Challenger budget that is
omitted from the other arms' comparison basis.

The shared endpoint is prospective utility on an arm-blinded anchor population
at matched declared cost. Guardrails include false promotion, critical harm,
evaluator-exploit acceptance, calibration and decision stability, forgetting,
temporal and out-of-distribution transfer, human burden, missingness, quarantine,
and rollback completeness.

On a positive A5 path, the promoted candidate is the bridge's new Builder
generation B1. The Evaluator change and bridge are therefore part of the
promotion evidence, not a hidden substitution of an unrelated candidate.

## Promotion automaton

Promotion is an append-only sequence of decisions:

```text
registered
  -> development_eligible
  -> screening_pass | screening_reject
  -> bridge_eligible | new_measurement_epoch
  -> confirmation_eligible
  -> promote | narrow | abstain | reject
  -> monitor | expire | revoke
```

Every transition binds the exact predecessor decision for its own candidate key
`(candidate_ref,candidate_hash)`. Promotion is blocked by an illegal or stale
transition, self-approval, unknown or overlapping protected independence,
reused or tainted confirmation, a missing/failed bridge, critical failure,
ambiguous or forbidden effect, or revoked ancestry. A candidate with a blocked
or quarantined effect attempt may only follow a containment transition such as
`screening_reject`, `reject`, or `revoke`; every matching effect record must be
listed in that transition's evidence references.

A failed or uncertain bridge from `bridge_eligible` transitions to
`new_measurement_epoch`; no confirmation pack is opened, and the old series is
retained as historical evidence. An early revoke from
`development_eligible`, `screening_pass`, `bridge_eligible`, or
`confirmation_eligible` requires an exact authority-bound
`deletion_tombstone`; that tombstone is terminal containment and projects its
declared descendants as revoked or unscorable.

Per-claim independence is a matrix, not a scalar score. It records authorship,
operation, custody, adjudication, organization/incentives, model/provider,
training/data, and exposure as `separate`, `overlap`, `unknown`, or `n/a`.
Protected overlap and unknown states are non-compensating.

## Stage 0 adversarial simulator

The simulator keeps latent true utility separate from evaluator score and
prospective anchor outcome. It includes frozen scenarios for:

- the true null and useful improvement;
- correlated shared blind spots;
- evaluator exploitation and Builder--Evaluator co-adaptation;
- feedback leakage and optional stopping;
- drift, preference reversal, forgetting, and missing outcomes;
- poisoning, critical failures, deletion, and revocation;
- forbidden effect attempts.

`effect_attempt` is a first-class immutable fact, tied to the candidate,
subject evidence, evaluation binding, observation authority, request hash, and
idempotency hash. Stage 0 permits only `blocked`/`not_dispatched` outcomes;
an accepted effect is rejected by the kernel. The frozen `forbidden_effect`
scenario emits a separate second candidate-keyed forbidden chain in addition
to the primary candidate chain, so effect containment is exercised for more
than one candidate without dispatching an external effect.

Optional stopping is reported at replicate level (`optional_stopping_denominator`
is one unit per replicate), while the matched-cost record keeps declared
fixed-N work separate from actual executed task count. Early stopping therefore
changes actual task cost and marks the affected causal contrast ineligible; it
cannot be hidden by copying the declared target into the actual-cost field.

The versioned deterministic random stream is derived from the protocol seed,
scenario, replicate, arm, entity, and stream identity. Reordering arms or
parallelizing execution cannot perturb an existing trajectory. A simulated
clock replaces wall time.

Bridge anchor truth is generated from an independent named `anchor_truth` stream
and materialized in a first ledger phase, together with B0/B1 subject evidence.
Bindings and score cells are emitted only in a second phase. Evaluator-cell
perturbations therefore cannot change existing evidence bytes, anchor bytes, or
their hashes, nor the anchors' thresholded decisions.

Bulk trajectories are represented by exact task/scenario/arm
`trajectory_summary` rows. One dependency-bound `contrast_summary` seal follows
all rows, depends on every row's exact reference and hash, and is recomputed
from those rows. It is the only summary seal: there is no
`simulation_summary` or scoped-trajectory fallback. The pure kernel derives
`operating_metrics`, `primary_endpoints`, and `contrast_diagnostics` only when
that seal is live; a missing, revoked, tainted, or unscorable seal makes all
three projections unavailable rather than permitting stale or nested metrics.

The exact operating-rate denominators are explicit. Let
`invalid_promotions = promotion.null + promotion.harmful + promotion.adversarial`:

```text
false_promotion_share = invalid_promotions / sum(promotion.*)
invalid_candidate_promotion_rate = invalid_promotions /
  (candidate_opportunities.null + candidate_opportunities.harmful +
   candidate_opportunities.adversarial)
```

The first is the share of all candidate promotions that were invalid; the second is
`P(promote | invalid candidate)`. Candidate-level opportunities are deliberately
separate from task-level `disposition` counts. Every rate is derived after
summing exact row counts; a zero denominator is `unknown` (`rate: null`), not
numeric zero.

Each arm's primary endpoint is represented without floating-point ambiguity as
`sum_ppm` and `observed_count`; its displayed `mean_ppm` is the integer
half-up value of `sum_ppm / observed_count`, and an empty observation count is
unknown. Frozen pairwise contrasts report endpoint deltas for diagnostics. A
contrast is `causal_eligible` only when every required compared arm/scenario row
has an observed endpoint and no optional stopping or actual-cost mismatch is
present. If any endpoint is missing, `not_estimable` with reason
`missing_endpoint` takes precedence. Otherwise optional stopping or an
actual-cost mismatch yields `diagnostic_only` with reason
`optional_stopping` or `actual_cost_mismatch`. These descriptive contrasts are
not causal claims.

The report is a deterministic descriptive projection, not an additional
authority or promotion decision. Sufficient-stat arithmetic and dependency/hash
closure verify only materialized rows and graph links; they do not prove
unmaterialized external raw events, empirical validity, real custody, or
production safety.

The model parameters are synthetic. Their numerical rates are operating
characteristics of the frozen simulated world, not forecasts for agents,
evaluators, organizations, or production.

## What Stage 0 can and cannot prove

The fixture exercises deterministic serialization, exact identities,
append-only rescoring, declared custody rules, causal-arm matching,
pre-confirmation and one-pack consumption ordering, bridge/epoch decisions,
legal promotion transitions, taint propagation, deletion closure, and no-effect
quarantine. Its synthetic construct and reliability statuses are fixture
inputs, not empirical measurements.

The adapter assumes trusted local directory ownership. Its symlink and
regular-file checks do not establish protection from a hostile process racing
path replacement in a shared directory.

The materialized sufficient statistics and hash closure cannot prove physical
append-only storage, key or credential custody, organizational independence,
absence of hidden communication or off-ledger leaks, holdout secrecy, external
descendant completeness, model replayability, safe real effects, adequate
empirical power, superiority, transfer, or production safety. Those claims
require prospective evidence and separately authorized owner-system controls.

The implementation boundary and reversal plan are recorded in
[the Stage 0 decision](decisions/2026-08-15-ael-cep-stage0-implementation.md).
