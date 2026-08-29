# Architecture

Agentic Evidence Lab is a file-first method with optional execution adapters.
The evidence contract owns experiment meaning; a runner only produces inputs to
that contract.

```text
capability source (separate owner/version)
                │ immutable artifact reference
                ▼
concept → study manifest → runner adapter → run records
                                      │
                                      ▼
                         domain evaluator / measurements
                                      │
                                      ▼
                              evidence receipt
```

## Evidence Core

`src/ael/schemas` defines five JSON document types. `ael.validation` performs
schema and cross-document checks, including hash resolution, condition/task
references, evidence-role consistency, and claim-level restrictions.
`ael.render` turns an already decided receipt into Markdown; it does not infer a
verdict from scores.

Alpha.5 keeps those five Contract v0 schemas and the receipt renderer unchanged.
Its public result surface is projection-first:

```text
validated Contract v0 evidence graph
              + result-catalog profile
                         │
                         ▼
       deterministic public result projection
              ├─ RESULTS.md (human cards)
              ├─ docs/results/index.json (machine index)
              └─ docs/results/<slug>.md (card projections)
```

The profile selects public receipts and claims, declares unavailable-material
categories and a bounded maintainer-rerun handoff, preserves explicit
historical unknowns, and may select exact lifecycle refs. Lifecycle status is
derived from those hash-bound records rather than profile prose. The projection
may enforce claim-specific support predicates, but it cannot create evidence,
change a receipt, claim an external release, or become a second authority.
Receipt evidence state, catalog membership, public graph verification,
maintainer rerun capability, linked independent replication, freshness, action,
and outcome remain separate axes; a card renders unavailable historical action
or outcome as `not_declared_historical` or `unassessed` rather than guessing.

Alpha.6 exercises one complete prospective admission → effect → adoption →
action → follow-up lifecycle in the Systematic Debugging real-shadow pilot.
Those record shapes remain study-local and experimental; Contract v0 still has
five stable document types. Public result cards may derive lifecycle status
only from exact hash-bound refs. One completed pilot is not enough to stabilize
a generic Decision Case or Outcome Follow-up schema.

Alpha.7 adds one adjacent methodological sidecar:

```text
Contract v0 manifest ─┐
task/evaluator refs ──┼→ ael.study_quality → deterministic preflight
explicit as_of ───────┘          │
                                 └→ bounded public quality facets
```

`ael.study_quality` owns the pilot profile rules. The CLI and result surface
depend on that module and do not duplicate its policy. Contract validation does
not depend on the quality module. Historical receipts remain unchanged and
project `not_assessed_historical`; a future profiled card must match the
receipt's exact study ID, revision, and manifest hash. Preflight conformance is
design evidence, not a quality score or an empirical result.

Alpha.7 projection `0.4` also treats GitHub release state as an external-system
predicate. Committed catalog bytes can say that a result is `listed` or
`withdrawn`; they cannot truthfully say that a future tag or release action has
succeeded. The original receipt `reproducibility` enum remains source metadata,
while public cards separately expose graph verification, maintainer rerun, and
independent replication.

Alpha.8 adds `ael.method_policy`, a pure policy module called by the existing
result projection. It replaces numeric rank-based claim authorization with
explicit evidence-state, comparison-design, and claim-local evidence-binding
predicates, then orders cards around the bounded decision and selected claims.
The result surface owns graph loading and projection; the policy receives only
resolved facts and performs no I/O. Contract v0 `evidence_level` remains machine
compatibility metadata but is no longer a public grade or index column.
Completed run and measurement records expose observed repeat coverage and
uncertainty presence; Study Quality continues to own prospective design
declarations only.

The result surface classifies every evidence reference of every selected claim.
Measurement IDs bind to their typed row and contributing run/task-pack roles;
safe public sidecar paths enter the generated source-hash inventory; historical
logical refs that Contract v0 cannot resolve remain explicitly opaque.
Every selected claim still needs at least one public binding, and causal,
stack, transfer, and outcome classes need a Measurement Set binding rather than
only a sidecar. Unselected receipt claims are not dereferenced. Resolution
proves identity and graph linkage, not semantic entailment.

```text
Contract v0 claims + study design ─┐
Study Quality preflight ───────────┼→ claim-first Method Policy
run/measurement observations ─────┤          │
replication/lifecycle refs ────────┘          ▼
                                      public projection 0.5
```

The policy is not a persisted Claim-Support Envelope, a Decision Case, or a
sixth Contract object. Study-local lifecycle adapters remain local until at
least two materially different prospective studies expose a repeated
consistency boundary.

The raw receipt renderer now uses the same non-ordinal vocabulary—**receipt
evidence state** and **claim class**—without changing any JSON field or
historical rendered evidence byte. Frozen Markdown produced by older releases
remains historical output and is not regenerated.

### AEL Coevolution Protocol (Stage 0)

AEL-CEP is a family-local protocol beside Contract v0. It is the current
central research direction for evaluating systems whose Builder and Evaluator
capabilities evolve together. Contract v0 remains exactly its five released
document types; AEL-CEP has its own schema namespace and dedicated validator
until a second materially different task family demonstrates a stable shared
boundary.

The Stage 0 dependency direction is deliberately small and one-way:

```text
CLI / tool ──→ strict bundle adapter ──→ deterministic simulator ──→ pure policy kernel
      └──────────────────────────────────────────────────────────────→ pure policy kernel
```

`ael.coevolution` is the pure kernel. It owns evaluator and builder release
identity, exact evaluation bindings, content-addressed record lineage,
append-only rescoring, replay classification, exposure and revocation
projections, bridge comparability, measurement epochs, per-claim independence
ceilings, causal contrast eligibility, and the promotion reducer. It does not
import filesystem, CLI, process, network, provider, sandbox, runner, Contract
validation, result projection, ambient clock, or ambient randomness facilities.

The strict sidecar adapter owns JSON parsing, schema loading, path and size
limits, raw-byte hashing, atomic materialization, and check mode. It may reject
an artifact or report a deterministic error, but it does not decide whether a
candidate should be promoted. AEL-CEP JSON is intentionally excluded from the
generic `ael validate` Contract v0 walk; use the dedicated protocol and bundle
boundary described in [AEL-CEP](ael-cep.md) and
[Reproducibility](reproducibility.md).

Alpha.12 supports that CLI/file/schema boundary only. The three
`ael.coevolution*` Python modules are inward implementation details and export
no compatibility-bearing star-import surface. This preserves freedom to split
or recombine policy internals after observed change evidence rather than
freezing speculative seams now.

The adapter's Stage 0 ceilings are 2 MiB per JSON or Markdown file, 2,048
records per bundle, and 10,000 dependency edges per bundle, with additional
bounded JSON and predecessor-chain depth. A successor may supply an arbitrary
ordered genesis-to-immediate-predecessor chain through repeated predecessor
inputs; each link is validated and retained before new records are appended.
These are fail-closed local limits, not production storage or physical
append-only guarantees.

The deterministic no-effect simulator owns only a declared synthetic world. It
compares A0--A5 trajectories (fixed/evolving Builder and Evaluator, naive
closed loop, custody-separated anchor, and Challenger-assisted custody) with
the same task exposure, selection/stopping/analysis algorithms, and matched
total-system budget for each declared contrast. It keeps latent utility,
Evaluator score, and arm-blinded prospective anchor outcome separate. Its
parameters are operating characteristics of that frozen simulation, not agent
forecasts.

An Evaluator is a release artifact, not a label. The evidence graph keeps the
subject observation evaluator-independent until scoring:

```text
SubjectExecutionEvidence → EvaluationBinding → ScoreRun
```

`SubjectExecutionEvidence` is retained execution evidence. `EvaluationBinding`
then freezes the exact Builder, Evaluator, measurement method, task revision,
runner/environment, analysis, promotion policy, exposure state, and epoch. A
`ScoreRun` binds that evidence and binding to the evaluator release and frozen
adjudication/scoring actor. A new evaluator appends a new binding and score
beside the old fact; it never rewrites or upgrades historical evidence. Direct
cross-epoch comparison is denied by default. A bridge can establish bounded
comparability, retain a linked-with-uncertainty description, or require a new
measurement epoch.

The Stage 0 bridge is a complete weighted panel over `good`, `bad`, `exploit`,
`semantic_mutant`, and `near_threshold`. Every stratum retains B0/B1 evidence,
four actual score runs (`B0×E0`, `B0×E1`, `B1×E0`, `B1×E1`), and arm-blinded B0/B1
anchor observations. The kernel recomputes weighted global shift, interaction,
score decision agreement, and anchor value/decision-threshold agreement; a
status-only anchor match or scalar summary is insufficient. For each stratum,
the kernel derives `G_s`, `I_s`, evaluator decision agreement, and anchor
decision agreement from the four score cells and two anchor values. Every
stratum must pass all four gates; weighted summaries cannot cancel a failing
stratum. Each B0/B1 anchor binds the exact corresponding
`SubjectExecutionEvidence` reference and hash. Promotion state is keyed by
`(candidate_ref,candidate_hash)`, with an independent predecessor chain per
candidate and `promotion_states` as the authoritative projection.

The simulator obtains anchor values from an independent named `anchor_truth`
stream and emits B0/B1 subject evidence plus anchor observations before the
second-phase binding/score records. Evaluator-cell perturbations therefore
cannot change committed evidence or anchor bytes/hashes or their thresholded
decisions. On a positive A5 path, promotion targets the bridge's new Builder
generation B1. Bridge `synthetic_pass`/`synthetic_fail` construct and
reliability fields are fixture statuses, not empirical calibration or validity
evidence.

Blocked effects are also first-class ledger facts: each `effect_attempt` binds
the candidate, subject evidence, evaluation binding, authority, request hash,
and idempotency key, and Stage 0 requires `blocked` plus
`postcondition_status=not_dispatched`. The frozen forbidden-effect scenario
emits a second candidate-keyed containment chain; accepted effects are rejected
before promotion.

Promotion authority is outside the adaptive roles. Unknown/overlapping
protected custody, self-approval, failed or missing bridges, reused or tainted
confirmation, critical failure, ambiguous effects, and revoked ancestry are
rejected by the local reducer. Stage 0's deterministic fixture exercises these
rules and no-effect adversarial handling; its sufficient-stat arithmetic and
hash closure do not prove unmaterialized external raw events, physical custody,
holdout secrecy, organizational independence, real model improvement,
empirical superiority, transfer, or production safety.

The frozen protocol has separate evidence, confirmation, anchor, adjudication,
and promotion principals. `confirmation_eligible` is pre-confirmation and does
not consume or anchor. If it passes, exactly one candidate-bound sealed
confirmation pack is materialized; `confirmation_consumption` irreversibly
reserves/marks it used under the frozen confirmation authority before exactly
one final decision (`promote`, `narrow`, `abstain`, or `reject`), and the anchor
observation follows that consumption. A recorded exposure blocks a positive
`promote` only when its target resolves to the sealed confirmation task root
before that decision. Screening and bridge exposures remain allowed under
their own budgets and lifecycle; off-ledger leaks remain an operational
residual. ScoreRuns/rescores
and promotion approvals use their exact frozen authorities; score adjudication
cannot be performed by evaluator custody, and promotion approval cannot be the
same actor as the transition actor. A failed or uncertain bridge transitions to
`new_measurement_epoch` without opening confirmation. Early revocation from an
eligible state requires an authority-bound `deletion_tombstone` and is terminal
containment. The exact CLI forms (`coevolution simulate`, `check`, and `rescore`)
plus materializer semantics are maintained in [Reproducibility](reproducibility.md).

Each `trajectory_summary` is an exact task/scenario/arm sufficient statistic.
One dependency-bound `contrast_summary` seal follows every trajectory row and
depends on all row references and hashes. The core derives
`operating_metrics`, `primary_endpoints`, and `contrast_diagnostics` only from
that live seal; it never falls back to `simulation_summary`, scoped summaries,
or arbitrary nested payloads. `false_promotion_share` is invalid promotions
over all candidate promotions, while `invalid_candidate_promotion_rate` is the same
invalid-promotion numerator over invalid candidate opportunities; candidate
opportunities and task-level dispositions are different denominators. Primary
endpoints retain exact `sum_ppm`/`observed_count` (integer half-up `mean_ppm`).
A `causal_eligible` contrast requires complete compared arm/scenario endpoints;
any missing compared row takes precedence as `not_estimable`, while optional
stopping or actual-cost mismatch otherwise yields `diagnostic_only`. A zero
denominator is unknown. A revoked, tainted, or unscorable seal makes all three
projections unavailable. Generic `ael validate` does not accept a CEP directory; use the
dedicated `ael coevolution check` boundary.

These principals are distinct role-level authorities; a release may reuse its
role's custody across generations while cross-role authority checks remain
exact. This local role separation is not evidence of organizational or
incentive independence. Sufficient-stat arithmetic and hash closure cover only
materialized rows and dependency links, not unmaterialized external events,
real custody, empirical validity, or production safety.

### Publication kernel

Alpha.8 also separates the public projection's observed volatility seams while
retaining `ael.result_surface` as the compatibility facade:

```text
method_policy                  result_constants
     ▲                              ▲
     │                              │
result_surface ──→ result_core      └── result_rendering
     │
     └──────────→ result_verification ──→ study-family audits
```

`result_core.SourceLedger` is the single owner of source hashes for one card.
Every dereferenced receipt, Contract record, report, quality profile, lifecycle
record, verification freeze or public claim sidecar enters that ledger; helpers
cannot maintain an untracked parallel hash dictionary. `result_verification`
owns one immutable allowlist of study-family adapters shared by the CLI and
projection. `result_rendering` receives already-admitted values and performs no
evidence I/O or claim authorization. Architecture tests keep these dependency
arrows one-way.

This is an information-hiding refactor, not a plugin system. Adapter names stay
closed and code-owned; arbitrary profile input cannot load Python. See
[`Publication kernel boundaries`](decisions/2026-08-14-publication-kernel-boundaries.md).

### Completion Integrity observable-enactment instruments

The alpha.10 method release adds three family-local pure policies without
changing the alpha.9 policy or the generic evidence kernel:

```text
strict enactment adapter ──→ completion_integrity_engagement
strict claim adapter     ──→ completion_integrity_claim
strict private-pack      ──→ completion_integrity_task_supply
```

Each pure module accepts parsed, normalized facts and imports no AEL I/O,
runner, Contract, CLI, sandbox, or provider module. The adapter owns strict
JSON, path safety, byte reading, input hashes, atomic output, and check mode.
The enactment policy receives immutable policy bytes and hashes them itself; a
pair of matching caller-provided digest strings cannot establish byte binding.
It also recomputes the canonical ledger digest, permits repair loops, and
returns four non-compensating facets. Event labels remain normalized caller-
provided facts; the instrumentation does not infer real harness capture, cognition,
or causal mediation.

The terminal-claim policy compares a closed reporter submission with evaluator-
owned frozen truth. It keeps truth, progress and verified/failed/unresolved
extent orthogonal and binds attempt, artifact and evidence hashes. Closed-shape
validation cannot prove that a real runtime denied the reporter tools, writes,
retries, executor access, evaluator access or remediation authority. That proof
belongs to the activation owner adapter and its retained runtime evidence.

Task supply is now a separate family-local development boundary:

```text
strict private-pack adapter ──→ completion_integrity_task_supply
       │                                  └─ non-compensating assessment
       ├─ safe paths + artifact hashes
       └─ private/public boundary
```

The task policy consumes normalized task-quality facts. Its `0.2-development`
contract separates lifecycle state from study role, requires terminal truth,
blocker-feasibility and evaluator-custody evidence, and blocks admission while
sample sizing remains `pending_pilot`. The adapter alone reads private paths
and bytes. It remains prospective: no task registry, generic mediator schema,
public synthetic dataset, stable cross-family API or alpha.9 policy change is
introduced. See
[Completion Integrity task supply](completion-integrity-task-supply.md).

Alpha.11 adds the real owner adapter and a public study-family audit. The path
is executor → event capture → offline evaluator → sealed reporter evidence →
closed submission → terminal assessment. Activation v2 proved that response-
schema acceptance alone is insufficient: an owner-generated identifier failed
the complete wrapper contract. Current source makes attempt IDs valid by
construction and tests the complete wrapper, while the v2 freeze continues to
bind the historical source. See [Completion Integrity activation](completion-integrity-activation.md).

Git ancestry or a tag can prove repository artifact ordering—for example, that
freeze bytes are present in an ancestor. It cannot prove that private model
calls occurred before a result, reconstruct private events, or establish
independent replication.

## Execution adapters

`ael.sandbox` invokes Docker with a read-only canonical fixture, a tmpfs working
copy, disposable output staging, a read-only root, no capabilities, resource
limits, and either no network or the controlled OpenAI proxy. After the
container stops, AEL rejects symlinks and special entries before copying staged
results into the operator's fresh private output. The offline runner is the
default for untrusted executable fixtures.

The hosted Codex adapter is intentionally narrower. It pins the CLI image and
egress destinations, but the agent process can read the injected credential.
It is therefore limited to maintainer-controlled inputs. See
[`SECURITY.md`](../SECURITY.md).

## Task-pack adapter

`ael.taskpack` checks that visible tests pass on a pristine fixture while hidden
acceptance tests initially fail, then evaluates an exported candidate against
both. This is one adapter, not a universal task format.

## Third-party source locks

`ael.source_lock` validates metadata-only references to external capability
trees and verifies a caller-provided Git checkout against the exact commit,
repository-relative tree hash, and observed license file. It does not fetch,
install, import, or execute the source. Registration and execution eligibility
are separate states. The current hosted runner permits only exact source-locked
snapshots that the maintainer reviewed and explicitly accepted for
maintainer-controlled execution; arbitrary submissions remain blocked because
its reusable credential is readable by the agent process.

The first multi-study use is [Agent Skills Season 1](../studies/agent-skills-season-1/README.md).
Its ten dossiers share the evidence envelope and isolation policy while keeping
their metrics, task semantics, and evaluators local. The completed bounded
negative PBT v2 result is one study-level effect decision; activation-only and
unrun studies remain distinct cards rather than entries in a global score.

## Ownership boundaries

- A capability repository owns its concept, prompts, tools, skills, versions,
  and releases.
- This repository owns generic evidence schemas, adapters, public task packs,
  cross-capability studies, and receipts.
- Evaluators own domain postconditions and cannot be replaced by model voting.
- Private holdouts, raw hosted traces, and credentials remain outside the
  public repository.

Private screening and confirmation packs also remain outside the Git worktree,
not merely under an ignored directory. Public manifests and receipts retain
only opaque identifiers, hashes, roles, and non-revealing strata. Operators
place a unique reserved private-evidence canary inside each private pack; the
release scan fails if any such bytes enter the public tree.

The system is deliberately local and file-based in alpha. There is no database,
RAG layer, hosted control plane, marketplace, or registry service.
