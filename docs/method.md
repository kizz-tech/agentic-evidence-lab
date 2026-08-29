# AEL Method: from a claim to a reversible decision

AEL is a method for deciding whether one exact versioned change to an agent
system should be adopted, rejected, narrowed, or tested again. The method is
runner-independent and claim-first: it starts from the decision and the exact
statement that evidence must support, not from a benchmark score.

```text
question → claim → admitted design → frozen comparison → observations
         → evaluated claim → bounded decision → action → outcome/revalidation
```

## The non-compensation rule

Evidence predicates stay independent.

- Hash-valid artifacts do not prove valid tasks.
- A controlled design does not calibrate its evaluator.
- Planned repeats do not establish observed reliability.
- A maintainer rerun is not independent replication.
- External use does not prove transfer.
- Payment does not prove a measured downstream outcome.
- An observed outcome does not identify its causal mechanism by itself.

AEL therefore has no global evidence score or study-quality grade. Negative,
null, bounded, and unresolved claims are useful when they prevent a weak change
from becoming the default.

## Applying the method to evaluator coevolution

The [AEL Coevolution Protocol](ael-cep.md) applies the same claim-first and
non-compensation rules when both the subject system and its ruler change. The
unit of evidence is not an answer with a mutable score:

```text
SubjectExecutionEvidence → EvaluationBinding → ScoreRun
```

`SubjectExecutionEvidence` is retained execution evidence and carries no
evaluator identity. An `EvaluatorRelease` includes its implementation,
rubric/prompt, model and tool identity, parser/aggregation, calibration
lineage, known error envelope, custody, and allowed evidence surface. An
`EvaluationBinding` additionally freezes the Builder, Evaluator, measurement
method, task revision, runner/environment, analysis and promotion policy,
exposure state, and measurement epoch. A `ScoreRun` binds that exact evidence
and binding to the evaluator release and scoring authority. A later Evaluator
produces a new binding and `ScoreRun` alongside the old observation; it never
overwrites, relabels, or retroactively upgrades the earlier verdict.

Direct longitudinal comparison is denied when the ruler changes. A bridge is a
whole-panel artifact over five weighted strata: `good`, `bad`, `exploit`,
`semantic_mutant`, and `near_threshold`. Each stratum retains B0/B1 subject
evidence, four actual score cells (`B0×E0`, `B0×E1`, `B1×E0`, `B1×E1`), and
arm-blinded B0/B1 anchor observations. The validator recomputes weighted
global shift, interaction, score decision agreement, and anchor agreement from
anchor values against the frozen decision threshold; a status-only anchor match
or scalar summary is insufficient. For each stratum, derive `G_s`, `I_s`,
evaluator decision agreement, and anchor decision agreement from the four cells
and two anchor values; every stratum must pass all four gates, so weighted
aggregation cannot cancel a failing stratum. Each B0/B1 anchor binds the exact
corresponding `SubjectExecutionEvidence` reference and hash. The result is
`bridge_comparable`,
`linked_with_uncertainty`, or `new_epoch_not_comparable`. A failed bridge starts
a new measurement series; historical facts remain intact.

The adaptive loop may evolve Builder, Evaluator, and eventually Challenger
releases, but not evidence history, prospective intake/partition policy,
anchor or confirmation custody, promotion constitution, or the matching and
budget rules within the same epoch. Confirmation is arm-blinded and single-use;
exposure consumes its freshness. Promotion is a custody-separated append-only
state transition, not a score threshold owned by the evaluator it governs.

The protocol freezes five distinct principals: evidence, confirmation, anchor,
adjudication, and promotion. Confirmation consumption must use the confirmation
principal; `anchor_observation` must be arm-blinded, use the anchor principal
and its exact release custody, and bind the same single-use candidate;
`ScoreRun.scoring_actor` and data-only rescore must use the adjudication
principal and cannot equal evaluator custody; promotion approval must use the
promotion principal and a distinct transition actor. These are exact local
bindings, not proof of real organizational or incentive independence.

The five principals are distinct role-level authorities. Same-role custody may
be reused across release generations; cross-role authority and custody checks
remain exact. This role separation is an implementation invariant, not evidence
of organizational or incentive independence.

The strict adapter rejects files above 2 MiB, bundles above 2,048 records, and
dependency graphs above 10,000 edges, in addition to bounded depth and unsafe
path checks. A successor may include an arbitrary ordered predecessor chain;
every predecessor remains historical evidence and is validated before new
facts are appended. Promotion projection is keyed independently by
`(candidate_ref,candidate_hash)`, with one exact predecessor transition chain
per candidate. A blocked/quarantined `effect_attempt` is candidate-bound and
must be included in a containment transition; Stage 0 rejects accepted effects
and the default forbidden-effect scenario exercises a second candidate chain.

Stage 0 uses a deterministic no-effect simulator to exercise these invariants
across A0--A5 trajectories, including nulls, useful changes, shared blind spots,
evaluator exploitation, leakage, optional stopping, drift/reversal, forgetting,
missingness, poisoning, deletion/revocation, and forbidden effects. It records
blocked/not-dispatched `effect_attempt` facts but dispatches no external effect.
Optional-stopping diagnostics use a replicate-level denominator; actual
executed-task cost remains distinct from declared fixed-N cost, and the
affected causal contrast is ineligible. Each task/scenario/arm
`trajectory_summary` is a sufficient statistic. One dependency-bound
`contrast_summary` seal follows all rows and depends on their exact references
and hashes; the core derives `operating_metrics`, `primary_endpoints`, and
`contrast_diagnostics` only from that live seal, never from a
`simulation_summary`, scoped fallback, or arbitrary nested payload.

The operating metrics use exact, separate denominators:
`false_promotion_share = invalid promotions / all candidate promotions`, while
`invalid_candidate_promotion_rate = invalid promotions / invalid candidate
opportunities`; candidate opportunities are not task-level dispositions. A
primary endpoint is exact `sum_ppm / observed_count` (integer half-up
`mean_ppm`), and a zero denominator is unknown. Contrasts with complete compared
arm/scenario endpoints but optional stopping or actual-cost mismatch are
`diagnostic_only`; any missing endpoint takes precedence as `not_estimable`, and
only complete matched contrasts are `causal_eligible`.
These are synthetic operating characteristics. The fixture exercises local
serialization, lineage, custody, bridge, and promotion rules, but its
sufficient-stat arithmetic/hash closure cannot prove unmaterialized external
events, real custody, empirical validity, model improvement or superiority,
transfer, novelty, or production safety.

The simulator derives bridge anchors from an independent named `anchor_truth`
stream and emits B0/B1 subject evidence plus anchor observations before the
second-phase binding/score records. Evaluator-cell perturbations cannot change
those committed evidence or anchor bytes/hashes or their thresholded decisions.
On a positive A5 path, promotion targets the bridge's new Builder generation B1.
The bridge's `synthetic_pass`/`synthetic_fail` construct and reliability values
are fixture statuses, not empirical calibration or validity evidence. The
`confirmation_eligible` state is pre-confirmation and does not consume or
anchor. A passing candidate receives exactly one candidate-bound sealed
confirmation pack; consumption irreversibly reserves/marks it used before one
final decision (`promote`, `narrow`, `abstain`, or `reject`), and the anchor
follows consumption. A recorded exposure blocks a positive `promote` only when
its target resolves to the sealed confirmation task root before that decision.
Screening and bridge exposures remain allowed under their own budgets and
lifecycle; off-ledger leaks remain an operational residual. A failed bridge
starts `new_measurement_epoch`
without a pack. Early eligible-state revocation requires an authority-bound
`deletion_tombstone`. If the contrast seal is revoked, tainted, or unscorable,
all derived metrics/endpoints/diagnostics are unavailable; no stale or nested
fallback is accepted.

## Seven gates

### 1. Frame the decision

Name one owner decision, one exact intervention, one counterfactual, one task
population, and the strongest claim the design is allowed to support. Record a
falsifier and the event that will make the result stale.

The question should be expressible as:

> For this exact change, on this task population and complete system boundary,
> does the declared outcome change enough to govern this exact decision?

### 2. Admit the measurement

Before scored work, use the [Study Quality Preflight](study-quality-preflight.md)
to bind:

- construct and claim ceiling;
- task provenance and task/oracle audit;
- evaluator calibration and adjudication;
- decision threshold and missing/invalid-cell policy;
- uncertainty method or explicit `not_estimable` limitation;
- planned repeats, ordering, perturbations, role overlap, and freshness.

For a new Completion Integrity population, the family-local
[task-supply contract](completion-integrity-task-supply.md) additionally
requires observable requirements, exact oracle coverage, structurally distinct
valid solutions, semantic mutants, environment checks, independent root
lineage, known-state terminal truth, blocker-feasibility adjudication, evaluator
custody, sacrificial qualification, untouched confirmation, private artifact
binding, and a pack-specific power or precision rationale. A task-count target
cannot compensate for a failed gate; unresolved sizing blocks admission.

A preflight pass means the declaration is conformant. It is not scientific
certification and does not prove that the profile preceded private model calls.

### 3. Freeze the exact comparison

Freeze the Concept and Study Manifest, candidate and baseline identities, full
model/runtime/harness configuration, task and evaluator packages, budget,
schedule, analysis rule, stop rule, and owner roles. A changed mechanism or
post-result threshold creates a new revision; it never edits the old study.

### 4. Observe without cleaning away failure

Retain one Run Record for every admitted task-condition-repeat cell. Preserve
poor answers, critical failures, invalid runs, retries, effects, cost, and event
capture limits. Operational invalidity and task failure are different states.

When a study claims that a workflow mechanism was enacted, retain observable
engagement evidence separately from the terminal task outcome. Policy delivery,
structured artifacts, checks captured by the owning harness, and terminal
reconciliation may be measured; token volume, elapsed time, or longer prose do
not establish engagement. Missing historical instrumentation is
`not_assessable`, not proof
that an agent ignored the intervention. The current family-local example is
[Completion Integrity observable enactment](completion-integrity-enactment.md).

Terminal reporting uses a different predicate. Truth (`complete`, `incomplete`,
`uncertain`), progress feasibility and verified/failed/unresolved extent remain
orthogonal, and the reporter is compared with evaluator-owned frozen truth. A
closed schema does not prove runtime capability isolation. See
[Completion Integrity terminal claims](completion-integrity-terminal-claims.md).

### 5. Evaluate exact claims

Measurements belong to the domain evaluator. Executable end state is primary
when available; model or human judgment is used only for qualities the
deterministic oracle does not own and must retain its calibration boundary.

Each selected claim carries its own class, status, scope, evidence references,
and falsifier. The publication profile names which selected claims govern the
displayed disposition and which are additional workflow/artifact disclosures;
that grouping cannot change a receipt claim or its status. Claim admission is
explicit:

| Claim class | Minimum design/evidence predicate |
| --- | --- |
| `artifact` | structurally valid artifact identity |
| `workflow` | runtime-conformant workflow evidence |
| `factor_causal` | controlled-factor comparison with claim-local Measurement Set evidence |
| `model_only` | controlled-factor comparison whose changed intervention class is model-only, with claim-local Measurement Set evidence |
| `operational_stack` | operational-stack comparison with claim-local Measurement Set evidence |
| `transfer` | matching transfer evidence plus a claim-local measurement linked to a run on a transfer task pack; use or adoption is not a substitute |
| `outcome` | matching downstream-outcome evidence plus a claim-local outcome measurement; payment is not a substitute, and independently verified outcome evidence also requires independent ownership |

Contract v0 keeps a coarse `evidence_level` field for compatibility. Public
cards call it the **receipt evidence state** and keep it in technical detail; it
is not an ordinal claim-authority ladder.

Every selected public claim `evidence_ref` is classified as a Measurement Set
row, a safe public sidecar whose SHA-256 enters the generated card inventory,
or an explicitly opaque receipt reference. Every selected claim needs at least
one public binding. For causal, stack, transfer, and outcome claims, at least
one binding must specifically be a Measurement Set row; a sidecar cannot
substitute. A study-wide measurement of the right kind cannot authorize an
unrelated claim. Artifact and workflow claims may retain additional disclosed
opaque refs because their historical evidence is not always represented as a
Measurement Set row or hash-bearing receipt reference.

This proves graph binding, not semantic entailment. Task and evaluator audit
must still establish that a referenced metric measures the stated construct;
a `transfer` task-pack label does not prove representative transfer, and an
`outcome`-typed row does not by itself prove a valuable downstream outcome.

### 6. Decide and act

The Evidence Receipt records a bounded evidence disposition. The operational
owner separately decides whether to install, route, keep optional, reject, or
retest the candidate. An action record states what was actually verified or
blocked. Neither a receipt nor a policy file proves that every client enforced
the action.

### 7. Observe outcome, replicate, or revalidate

Complete the scheduled follow-up or record that the observation is missing,
cancelled, or invalidated. Keep these questions separate:

- can a public checkout validate or recompute the evidence graph?
- can the maintainer run a new observation with retained inputs?
- has a separately owned replication been linked?
- did the actual owner action produce an observed downstream outcome?
- is the claim still fresh for the current stack and task boundary?

New evidence appends a revision, replication, correction, or follow-up. It does
not rewrite the historical receipt.

## Public result order

An alpha.8 card is read in this order:

1. bounded decision and reversal trigger;
2. decision-governing claim statements and statuses, followed by any additional
   selected workflow/artifact disclosures;
3. exact comparison and task scope;
4. observed outcomes, cost, repeat coverage, and uncertainty presence;
5. prospective study-design preflight;
6. action, outcome, freshness, replication, and independence;
7. technical receipt metadata, raw graph, and limitations.

The generated card is a deterministic projection, not a new evidence owner.

Process diagnostics remain additional evidence. They cannot compensate for a
failed final state or promote a null effect into a mechanism claim.

## Minimal local path

```bash
uv run ael validate examples
uv run ael study preflight \
  studies/quality-preflight/examples/pass/quality-profile.json \
  --json-output studies/quality-preflight/examples/pass/preflight.json \
  --markdown-output studies/quality-preflight/examples/pass/preflight.md \
  --check
uv run ael results check studies/public-results.json --require-git-proof
```

Use [Contract v0](contract-v0.md) for the five evidence documents,
[Reproducibility](reproducibility.md) for audit boundaries, and the
[Roadmap](../ROADMAP.md) for the next empirical falsifiers.

## What is deliberately not stable

Admission, adoption, action, outcome-follow-up, and study-quality profiles are
pilot sidecars. A generic Decision Case, reliability schema, replication event,
or sixth Contract object waits for repeated prospective use in at least two
materially different study families and an explicit migration decision.
