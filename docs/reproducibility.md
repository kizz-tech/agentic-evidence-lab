# Reproducibility

Reproducibility has separate operations. **Graph verification** checks the
hash-linked public records and deterministic projections. A **rerun** executes
the declared protocol again when its inputs are available. **Independent
replication** adds a new executor and role-separated evidence production. None
of these operations implies either of the others, and stochastic model
behavior is not expected to be byte-identical.

Public result cards use three explicit facets:

| Facet | Meaning | What it does not prove |
| --- | --- | --- |
| Public graph verification | A public checkout can validate hashes or recompute the published decision, depending on the named adapter. | A new model execution or independent replication. |
| Maintainer rerun | The maintainer can perform a new observation with the declared retained inputs, when assessed. | Replay of historical provider behavior or outside ownership. |
| Independent replication | A separately owned replication is linked by the evidence graph. | Transfer beyond the replicated scope. |

Contract v0 receipts retain their original `reproducibility` enum for source
compatibility. Generated machine cards expose it as
`receipt_reproducibility`, and technical cards explain its boundary; it is not
used as a shortcut for any row above. Catalog membership is likewise distinct
from Git tag, GitHub release, or package-publication state.

## Graph verification: deterministic public checks

From a clean checkout of the exact alpha.12 source revision under review:

```bash
uv sync --locked --all-groups
uv run ruff check .
uv run ruff format --check .
uv run python -m unittest discover -s tests -v
uv run ael validate examples
uv run ael study preflight \
  studies/quality-preflight/examples/pass/quality-profile.json \
  --json-output studies/quality-preflight/examples/pass/preflight.json \
  --markdown-output studies/quality-preflight/examples/pass/preflight.md \
  --check
uv run python tools/check_completion_integrity_engagement.py \
  --method-plan studies/completion-integrity/diagnostics/process-v1/method-plan.pilot.json \
  --observations studies/completion-integrity/diagnostics/process-v1/fixtures/normalized-cells.json \
  --diagnostics-json studies/completion-integrity/diagnostics/process-v1/fixtures/expected-diagnostics.json \
  --check
uv run ael source-lock check studies/agent-skills-season-1/sources.lock.toml
uv run ael study audit \
  --freeze studies/completion-integrity/freeze.json \
  --result studies/completion-integrity/results/prompt-policy-v1 \
  --decision-adapter completion-integrity-prompt-policy-v1 \
  --require-git-proof
uv run ael study audit \
  --freeze studies/completion-integrity/activation-v2/freeze.json \
  --result studies/completion-integrity/activation-v2/results \
  --decision-adapter completion-integrity-activation-v1 \
  --require-git-proof
uv run ael study audit \
  --freeze studies/agent-skills-season-1/screening/property-based-testing-v2.freeze.json \
  --result studies/agent-skills-season-1/results/property-based-testing-v2 \
  --decision-adapter pbt-v2 \
  --require-git-proof
uv run ael study audit \
  --freeze studies/agent-skills-season-1/screening/systematic-debugging-real-shadow.freeze.json \
  --result studies/agent-skills-season-1/results/systematic-debugging-real-shadow-v1 \
  --decision-adapter systematic-debugging-real-shadow-v1 \
  --require-git-proof
uv run ael validate \
  studies/agent-skills-season-1/concept.json \
  studies/agent-skills-season-1/manifests \
  studies/agent-skills-season-1/calibration/runtime-v1
uv run python tools/materialize_agent_skills_season.py --check
uv run ael results check studies/public-results.json --require-git-proof
uv run python tools/check_frozen_artifacts.py
uv run python tools/check_completion_integrity_claim.py \
  --policy studies/completion-integrity/terminal-claim-v1/policy.pilot.json \
  --cases studies/completion-integrity/terminal-claim-v1/fixtures/cases.json \
  --assessments-json studies/completion-integrity/terminal-claim-v1/fixtures/expected-assessments.json \
  --check
uv run python tools/release_check.py
uv build
uv run python tools/verify_release_artifacts.py \
  --expected-version 0.1.0a12 dist/*.whl dist/*.tar.gz
```

These checks establish package, schema, cross-reference, committed-fixture,
rendering, simulation, generated-publication, and public-tree consistency. They
verify the published evidence graph; they do not establish that an experimental
conclusion is true outside its receipt scope.

## AEL-CEP Stage 0 checks

AEL-CEP is a family-local sidecar beside Contract v0. Its JSON is intentionally
not part of the recursive `ael validate` walk: generic `ael validate` does not
accept a CEP directory as Contract v0 input. Use the dedicated CLI, which
validates the protocol, the content-addressed ledger, the custody/authority
bindings, and the deterministic projection:

```bash
# Materialize a deterministic no-effect Stage 0 bundle and report.
uv run ael coevolution simulate PROTOCOL.json \
  --bundle-output TRAJECTORY-BUNDLE.json \
  --report-output TRAJECTORY-REPORT.md

# Validate existing bytes and check the report projection exactly.
uv run ael coevolution check PROTOCOL.json TRAJECTORY-BUNDLE.json \
  --report TRAJECTORY-REPORT.md --check-report

# Append a data-only evaluator rescore into a distinct successor bundle.
uv run ael coevolution rescore PROTOCOL.json SOURCE-BUNDLE.json RESCORE-REQUEST.json \
  --output SUCCESSOR-BUNDLE.json
```

For a successor whose ancestry is not available from one immediate source,
repeat `--predecessor PATH` in oldest-genesis-to-immediate-predecessor order on
`check` or `rescore`. This is a full predecessor chain, not a hint: the
adapter loads and validates every supplied prefix, checks each successor's
exact predecessor and dependency hashes, and preserves the chain before
appending new facts:

```bash
uv run ael coevolution check PROTOCOL.json SUCCESSOR-BUNDLE.json \
  --predecessor GENESIS-BUNDLE.json \
  --predecessor PRIOR-BUNDLE.json \
  --report SUCCESSOR-REPORT.md --check-report
```

The output path must be distinct from every protocol, request, bundle, report,
and predecessor input. `simulate --check` checks the existing bundle and report
against byte-identical deterministic output. `rescore --check` checks an
already-materialized successor and never rewrites its source bundle. The
Repository-owned tools currently call
`ael.coevolution_bundle.materialize_bundle`, `check_bundle`, and
`append_rescore_files` directly. These Python modules and signatures are
experimental internals, not alpha.12 compatibility contracts. External use
should invoke the CLI and versioned file/schema boundary; a supported Python
facade requires a future explicit compatibility decision.

The strict adapter rejects any JSON or Markdown file above 2 MiB, bundles above
2,048 records, and dependency graphs above 10,000 edges. It additionally bounds
JSON depth and predecessor-chain depth and fails closed on duplicate members,
non-finite values, unsafe absolute/file references, symlinks, output aliases,
and non-regular files. These are local input ceilings, not claims about
production storage or real append-only custody.

Run these operations only in directories whose ownership is trusted. The
adapter rejects observed symlinks and non-regular files, but alpha.12 does not
claim protection against another process racing pathname replacement in a
shared directory.

The evidence graph is evaluator-independent until the final scoring edge:

```text
SubjectExecutionEvidence (retained execution facts)
        │ evidence_ref/evidence_hash
        ▼
EvaluationBinding (exact Builder/Evaluator/method/task/environment binding)
        │ binding_ref/binding_hash
        ▼
ScoreRun (Evaluator release + frozen adjudication/scoring actor)
```

The bridge validator requires the complete weighted five-stratum panel
(`good`, `bad`, `exploit`, `semantic_mutant`, `near_threshold`). Each stratum
must point to retained B0/B1 subject evidence, four actual `ScoreRun` cells
(`B0×E0`, `B0×E1`, `B1×E0`, `B1×E1`), and arm-blinded B0/B1
`anchor_observation` records. It recomputes global shift, interaction, score
decision agreement, and anchor agreement from anchor values against the frozen
decision threshold; status-only anchor equality is not sufficient. Bridge
weights, cells, hashes, and degenerate derived intervals are all checked
against the frozen protocol.

For each stratum, the validator derives global shift `G_s`, interaction `I_s`,
evaluator decision agreement, and anchor decision agreement from the four score
cells and two anchor values. Every stratum must pass all four gates; the weighted
summary cannot cancel a failing stratum. Each B0/B1 `anchor_observation` binds
the exact corresponding retained `SubjectExecutionEvidence` reference and
hash. Stage 0 `synthetic_pass`/`synthetic_fail` construct and reliability
statuses are fixture declarations, not empirical calibration or validity
evidence.

Promotion projection is keyed by `(candidate_ref,candidate_hash)`. Each
candidate has an independent transition chain with an exact predecessor
transition hash; the `promotion_states` map is the authoritative projection,
while the legacy `promotion_state` view is emitted only for a single-candidate
bundle. A blocked/quarantined `effect_attempt` is candidate-bound and must be
included in a containment transition's evidence references; accepted effects
are forbidden by Stage 0. The frozen forbidden-effect scenario also exercises
a second independently keyed forbidden candidate chain.

The protocol freezes five distinct principals. `confirmation_eligible` is a
pre-confirmation state and must not consume or anchor. If it passes, exactly one
candidate-bound sealed confirmation pack is materialized. The confirmation
principal irreversibly reserves/marks that pack used before exactly one final
decision (`promote`, `narrow`, `abstain`, or `reject`); `anchor_observation` follows the consumption,
must be arm-blinded, use the frozen anchor authority and custody, and bind the
same candidate. A recorded exposure blocks a positive `promote` only when its
target resolves to the sealed confirmation task root before that decision.
Screening and bridge exposures remain allowed under their own budgets and
lifecycle; off-ledger leaks remain an operational residual. `ScoreRun.scoring_actor`
and a data-only rescore must be the frozen adjudication principal and not
evaluator custody; promotion approval must be the frozen promotion principal
with a distinct transition actor. JSON role labels do not establish real
organizational independence.

These are distinct role-level authorities. A release may reuse its role's
custody across generations; same-role generation reuse is allowed, while every
cross-role authority and custody check remains exact. This local separation is
not evidence of organizational or incentive independence.

Stage 0 simulation is deterministic and no-effect. It exercises A0--A5,
append-only lineage, bridge/epoch and promotion rules, taint/revocation,
missingness and adversarial scenarios. The simulator records blocked,
`postcondition_status=not_dispatched` `effect_attempt` facts; it does not
dispatch external effects. Optional-stopping diagnostics use a replicate-level
denominator, and matched cost records declared fixed-N work separately from
actual executed task count; early stopping therefore changes actual cost and
marks that causal contrast ineligible. Its output is a descriptive projection
of a synthetic world: it does not establish real custody, holdout secrecy,
model improvement, empirical validity or superiority, transfer, novelty, or
production safety.

The simulator derives bridge anchors from an independent named `anchor_truth`
stream. It emits B0/B1 subject evidence and anchor observations before the
second-phase binding/score records, so evaluator-cell perturbations cannot alter
already committed evidence or anchor bytes/hashes or their thresholded
decisions. A positive A5 promotion targets the bridge's new Builder generation
B1.

The deterministic simulator emits exact task/scenario/arm
`trajectory_summary` rows and one dependency-bound `contrast_summary` seal
after all rows. The seal depends on every row's exact reference and hash; the
core recomputes and derives `operating_metrics`, `primary_endpoints`, and
`contrast_diagnostics` from that seal. There is no `simulation_summary` or
scoped-trajectory fallback, and arbitrary nested ledger payloads cannot become
report metrics. If the seal is missing, revoked, tainted, or unscorable, all
three projections are unavailable and history is not rewritten. The report is
not promotion authority.

The exact operating metrics are summed across validated rows before rates are
calculated. With
`invalid_promotions = promotion.null + promotion.harmful + promotion.adversarial`:

```text
false_promotion_share = invalid_promotions / sum(promotion.*)
invalid_candidate_promotion_rate = invalid_promotions /
  (candidate_opportunities.null + candidate_opportunities.harmful +
   candidate_opportunities.adversarial)
```

The first denominator is all candidate promotions; the second is invalid candidate-level
opportunities (`P(promote | invalid candidate)`). They are distinct from
task-level `disposition` counts. A zero denominator is `rate: null` (unknown).
Fixture missingness can leave a row without a complete endpoint, which is
`not_estimable`, not numeric zero. Per-arm primary endpoints retain exact
`sum_ppm` and `observed_count`, with integer half-up `mean_ppm`. A contrast is
`causal_eligible` only when every required compared arm/scenario row has an
observed endpoint and no optional stopping or actual-cost mismatch. A missing
endpoint takes precedence as `not_estimable` with reason `missing_endpoint`;
otherwise optional stopping or an actual-cost mismatch is `diagnostic_only` with
reason `optional_stopping` or `actual_cost_mismatch`. Its delta is descriptive,
not causal. Optional stopping counts eligible replicates, while actual executed
cost remains separate from declared fixed-N cost.

A failed or uncertain bridge transitions to `new_measurement_epoch` without
opening confirmation. Early revoke from an eligible state requires an exact
authority-bound `deletion_tombstone` and is terminal containment. The fixture's
sufficient-stat arithmetic and dependency/hash closure verify only materialized
rows and graph links; they do not prove unmaterialized external raw events,
empirical validity, real custody, or production safety.

The public Season 1 activation evidence is reproducible from retained private
run inputs only by the maintainer. Public consumers can validate every exposed
document, source lock, and content hash, but cannot reconstruct private Codex
events from their hashes. This is verification of the published evidence graph,
not a historical model-call rerun or independent reproduction of the
hosted-agent executions.

## Frozen study-bundle audit

`ael study audit` is the fail-closed verifier for a completed frozen study. It
checks the freeze contract; exact terminal-decision alias; freeze, private-pack,
and decision hashes; Contract v0 references; terminal schedule coverage; and
receipt coverage. A study-specific decision adapter can additionally reconstruct
decision counts and the terminal outcome from public run and measurement
records instead of trusting the published aggregate. Adapters are explicit and
closed by study family; omitting one leaves its semantic checks unclaimed.

With `--require-git-proof`, the audit requires the preregistration commit to be
an ancestor of the checkout, requires that commit to contain the exact current
freeze bytes, and requires the terminal decision to be absent from that commit.
Optional `--screening-root` and `--confirmation-root` arguments verify retained
private task-pack bytes against their frozen tree digests without publishing
them. `--json-output` writes a machine-readable audit summary.

This Git proof is limited to repository artifact ordering. A tag or ancestor
does not prove that private model calls occurred before results, and it does not
reconstruct private events or establish independent replication.

The private observation payload remains opaque. The audit checks its published
hash and, with the explicit adapter, recomputes the exposed counts and outcome;
it cannot reconstruct hidden task or event bytes that were not published.

The `completion-integrity-prompt-policy-v1` adapter verifies the zero-call
freeze and preregistration binding, reconstructs all 52 scheduled cells from
521 public measurements, and recomputes the null effect and exact-policy
rejection. Private tasks, evaluator code, candidates, events, attempt journals,
and authentication remain outside the public graph.

The `completion-integrity-activation-v1` audit adapter also verifies activation
v2 because the adapter name identifies the study-family decision algorithm, not
one hard-coded study revision. For v2 it checks the exact preregistration and
freeze, six scheduled records including invalid and unrun cells, 24 normalized
measurements, and the recomputed
`protocol_invalid / revise_activation_adapter` decision. It does not use the
current repaired runner source in place of the source hashes retained by the v2
freeze.

Activation audit is not a rerun. The exact v2 schedule cannot be retried or
resumed; a repaired adapter requires a new revision and new provider
observation. The public bundle cannot reconstruct the withheld reporter payload
or independently verify the maintainer diagnosis that its semantic claim
matched truth while the owner wrapper identifier was invalid.

The observable-enactment fixture check is separate. It validates an
experimental classifier against sanitized known states and verifies that its policy,
ledger, and golden projection hashes remain bound.
It does not rerun alpha.9 or classify its process retrospectively: alpha.9 is
explicitly `not_assessable` because it retained no structured ledger and no
requirement-to-check event bindings.

The `systematic-debugging-real-shadow-v1` adapter additionally verifies the
prospective admission-to-action chain and reconstructs the terminal effect from
80 public measurements rather than trusting the aggregate decision. It also
verifies the disclosed one-field projection repair by reconstructing the
original invalid receipt bytes. That repair occurred after scored work and did
not change observations or the effect decision; it is not represented as
preregistered analysis.

For future Codex runs, `ael study activation-check` accepts Codex JSONL events
and counts activation only when a completed, exit-zero command retrieved
non-empty content from the exact installed `SKILL.md`. A path mentioned in an
agent message, an in-progress command, a failed command, or empty output is not
activation evidence. This stricter parser does not rewrite historical records.

## Receipt and projection reproduction

```bash
uv run ael render \
  examples/council-generation-1/evidence-receipt.json \
  --output /tmp/receipt.md
diff -u examples/council-generation-1/evidence-receipt.md /tmp/receipt.md
```

Every receipt binds its concept, study, runs, and measurements by SHA-256.
`ael validate` resolves relative public references and checks those hashes.
The generated [Results Index](../RESULTS.md) and machine index are deterministic
projections over those validated references; regeneration does not change the
underlying receipt or its authority. The exact public handoff for each result
is visible in those projections without implying that hidden inputs became
public.

To regenerate intentionally, use:

```bash
uv run ael results build studies/public-results.json --require-git-proof
```

Review the generated diff, then run the corresponding `results check` command.

## Calibration reproduction

```bash
uv run ael calibrate \
  studies/council-generation-2/calibration/calibration-config.json \
  --output /tmp/calibration-result.json \
  --report /tmp/calibration-report.md
diff -u studies/council-generation-2/calibration/calibration-result.json \
  /tmp/calibration-result.json
diff -u studies/council-generation-2/calibration/calibration-report.md \
  /tmp/calibration-report.md
```

The simulation is deterministic because the configuration pins its seed and
the result records a versioned SplitMix64 PRNG seeded from SHA-256. Discrete
paired outcomes are aggregated as integers, so the result does not depend on
Python's cross-version behavior for `random.choice`, `random.gauss`, or
floating-point `sum`.

## Container reproduction

Docker builds pin base-image digests. Invocation records capture the locally
resolved image ID, fixture tree hash, limits, network policy, and exit state.
Tag names alone are not sufficient evidence.

Hosted-model repetitions can differ even when the exposed model name, CLI,
prompt, and budget are fixed. Preserve each run as a separate observation,
record exposed provider/runtime identity, and do not retry poor answers as if
they were operational failures.

## Rerun versus independent replication

The exact PBT v2 graph-verification command is the audit command shown above:

```bash
uv run ael study audit \
  --freeze studies/agent-skills-season-1/screening/property-based-testing-v2.freeze.json \
  --result studies/agent-skills-season-1/results/property-based-testing-v2 \
  --decision-adapter pbt-v2 \
  --require-git-proof
```

It recomputes the exposed counts and checks the hash-linked bundle; it does not
rerun the private model calls. A historical PBT v2 rerun has no public command
in the current alpha because its task packs, raw Codex events, candidate
workspaces, and evaluator outputs are withheld. Do not label the audit, receipt
rendering, or projection regeneration as a rerun.

An independent replication requires a new executor to obtain the frozen
protocol and permitted inputs, run the study through the declared adapter, and
publish a new receipt with disclosed intervention ownership, task authorship,
evaluation, analysis, and decision roles. Forking the repository, rerunning a
receipt, or checking a Git tag is not automatically independent verification.
Use `reproduced_third_party` or `independently_verified` only when the
receipt's role and evidence requirements are actually satisfied. Evidence
level, public graph verification, maintainer rerun capability, linked
independent replication, freshness, action, and outcome remain orthogonal;
missing historical action or outcome is `not_declared_historical`, not a
negative observation.
