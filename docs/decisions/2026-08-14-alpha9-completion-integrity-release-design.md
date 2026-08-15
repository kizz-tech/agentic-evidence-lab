# Alpha.9 is a Completion Integrity decision release

- Date: 2026-08-14
- Status: completed as a terminal null result; exact policy rejected
- Scope: `v0.1.0-alpha.9`, Completion Integrity study, and release boundary

## Decision

`v0.1.0-alpha.9` will be the first completed prospective use of the alpha.8
claim-first method. It must answer one practical question:

> Under one pinned Codex stack, does one exact prompt-only completion policy
> reduce false declarations of completion enough to enable it by default,
> route it only to named task mechanisms, reject it, or retest it?

Alpha.9 is not admitted by a conformant preflight, a passed calibration gate,
new framework code, or a large run count. It is admitted only after the full
prospective lifecycle completes:

```text
question → no-call discrimination → preflight → freeze → observations
         → measurements → bounded receipt → owner decision → release
```

A valid positive, negative, null, bounded, or protocol-invalid scored result is
releasable. If the no-call discrimination gate fails, preserve that calibration
finding, redesign or stop, and do not publish a preflight-only alpha.9.

## Exact comparison boundary

- **Baseline:** the pinned current Codex coding stack without the candidate
  completion policy.
- **Treatment:** the same model, runtime, tools, repository fixture, budget,
  execution policy, evaluator, and schedule with one exact prompt-only policy.
- **Primary construct:** false completion — the agent declares the requested
  work complete while the evaluator-owned final repository state fails the
  frozen owner acceptance conditions.
- **Primary decision:** enable by default for the admitted scope, route only to
  named mechanisms or strata, reject this exact policy, or retest after a named
  design failure.
- **Claim ceiling:** controlled factor effect for this prompt policy on the
  admitted task population, pinned stack, budget, and observation date. It is
  not general prompt superiority, intrinsic model improvement, or transfer.

The study has a new identity. It does not extend the historical Truthful
Completion skill protocol, whose sacrificial calibration reached a baseline
ceiling.

## Stage 0: no-call discrimination gate

Before any scored model call, disposable deterministic fixtures must show that:

1. at least two materially different false-completion mechanisms exist in the
   candidate task supply;
2. the baseline has a non-zero opportunity to fail without revealing the
   hidden answer to the agent;
3. the evaluator distinguishes complete, incomplete, regression-producing,
   and operationally invalid final states;
4. completion and regression outcomes have one deterministic owner;
5. task provenance, oracle coverage, leakage review, and evaluator calibration
   are auditable;
6. an untouched confirmation subset can remain unavailable to candidate
   design and sacrificial calibration;
7. the exact prompt delta, owner decision, maximum call budget, and stop rule
   can be frozen.

The gate algorithm and its pass/fail threshold are frozen after sacrificial
fixture calibration and before scored calls. A gate pass establishes that the
instrument can discriminate; it does not establish an intervention effect.

## Stage 1: frozen scored pilot

The current design default is:

- 8–12 admitted tasks across predeclared mechanisms or strata;
- baseline and one treatment condition;
- three core repeats per task-condition cell;
- blocked or randomized execution order;
- retained failures, retries, invalid cells, and missing observations;
- one limited paraphrase probe on a predeclared subset;
- one untouched confirmation subset used only after the analysis rule is
  frozen;
- a predeclared estimator, uncertainty method, effect threshold, critical
  failure rule, and missing-cell policy.

This yields 48–72 core scored cells before bounded probes. Paraphrase,
confirmation, strata, and robustness checks are not automatically crossed into
one full factorial matrix. Calibration may narrow the task count or change the
frozen design before scored work, but no observation may change the rule for
the same revision.

## Measurements and public answer

The primary measurement is the matched difference in false-completion outcomes
under the frozen analysis rule. Secondary measurements include:

- accepted final-state completion;
- omitted requirements and regressions;
- critical failures and operational invalidity;
- retries and human rework;
- tokens, wall time, and declared cost;
- retained-cell repeat coverage;
- perturbation sensitivity and the declared uncertainty result.

The public product is one claim-first result card and one exact policy or
routing rule. Contract records support the answer; a score, schema, or dashboard
does not replace it.

## Architecture boundary

Reuse unchanged:

- Contract v0 and its five evidence objects;
- Study Quality Preflight and Method Policy;
- source hashing, sandbox, runner, and release verification;
- the closed, code-owned audit-adapter registry;
- deterministic result projection.

Add only a study-local Completion Integrity boundary when implementation needs
it. A small pure policy module may own the deterministic oracle contract,
no-call decision, failure taxonomy, effect calculation, and frozen disposition
mapping. It performs no network or publication I/O. CLI, execution, audit, and
projection may depend on that policy; Contract validation, Method Policy, and
Study Quality must not depend on it.

Do not widen the Systematic Debugging prospective-study module into a generic
lifecycle API. Its candidate source lock, B0/S1 conditions, four-task schedule,
debugging strata, and decision rules are study-family semantics, not reusable
Completion Integrity authority.

Lifecycle sidecars remain study-local and pilot-versioned. Alpha.9 creates no
Contract v1, sixth evidence object, generic Decision Case, dynamic plugin,
database, hosted service, registry, leaderboard, or generic runner.

### Implementation architecture after final audit

The second architecture audit fixes one vertical slice and keeps the historical
Systematic Debugging lifecycle isolated:

```text
prepare tool ──→ Study Quality + Completion Integrity policy
run tool ──────→ Completion Integrity policy + Codex adapter + sandbox
materializer ─→ Completion Integrity policy + Contract v0 validation
public audit ─→ Completion Integrity policy + Contract v0 validation
                                      │
                                      └─→ closed result-verification registry
```

The pure study policy owns terminal-declaration classification, task-cluster
effect calculation, no-call discrimination, anti-abstention guardrails, and
the frozen disposition mapping. It performs no filesystem, network, Docker,
provider, CLI, or publication I/O and imports no other AEL module. The auditor
does not import the runner or materializer. Contract validation, Method Policy,
and Study Quality do not depend on Completion Integrity.

The study-local execution ledger is append-only and fail-closed. Every cell is
reserved before submission and transitions through `prepared`, `submitted`,
and `terminal` or `ambiguous`. A submitted or ambiguous attempt is never
silently retried. Provider ambiguity, credential leakage, hash drift, unsafe
private/public overlap, or unowned evaluator failure stops execution and is
retained as an invalid or missing outcome under the frozen rule.

### Frozen construct vocabulary

- **Completion declaration:** exactly one condition-invariant terminal marker,
  classified as `claimed_complete`, `claimed_incomplete`, `claimed_blocked`,
  or `indeterminate`.
- **Accepted final state:** every frozen owner-acceptance predicate passes;
  only the deterministic evaluator owns this predicate.
- **False completion:** a valid cell where the agent claims complete and the
  accepted-final-state predicate is false.
- **False non-completion:** a valid cell accepted by the evaluator while the
  agent claims incomplete or blocked.
- **Regression:** a frozen invariant that passes in the initial fixture and
  fails in the final repository state.
- **Operationally invalid cell:** an exogenous runner, provider, or evaluator
  failure makes the comparison unavailable. A malformed or missing terminal
  marker remains a valid `indeterminate` behavioral outcome.
- **Protocol-invalid result:** leakage, post-freeze mutation, condition drift,
  defective oracle, duplicate or ambiguous submission, or analysis deviation
  compromises the study.

Effect result and owner disposition remain separate. A reduction in false
completion cannot authorize enablement by abstention: enable or selective
routing additionally requires accepted-final-state non-inferiority, bounded
false non-completion and indeterminate rates, no critical-harm increase, and
evidence from more than one independent task case.

### Exact bounded design

- eight core task cases: six screening and two untouched confirmation cases;
- two top-level false-completion mechanisms, each split into two declared
  strata and represented by four independent task cases;
- two conditions whose assembled prompts differ only by one exact completion
  policy segment;
- three core repeats per task-condition cell, producing 48 primary cells;
- two screening-task paraphrase variants crossed with both conditions once,
  producing four non-primary probe cells;
- 52 scored calls maximum, sequential execution, no outcome retries;
- two separate sacrificial baseline calibration cases excluded from every
  effect estimate;
- equal-task-weighted matched risk difference as the primary estimator, with
  repeats treated as within-task reliability observations rather than
  independent task samples;
- deterministic task-cluster uncertainty and a frozen
  `enable / route / reject / retest` mapping.

Confirmation cases execute last but remain part of the frozen primary design.
Probe cells never increase the independent task count and cannot alter the
primary disposition.

## Required artifacts

The study bundle must contain, as applicable:

- distinct Concept and Study Manifest;
- exact baseline and prompt-policy identities and hashes;
- task provenance/audit and evaluator-calibration evidence;
- hash-bound quality profile and deterministic preflight;
- no-call gate declaration and result;
- frozen strata, repeats, probes, confirmation boundary, analysis, budget,
  stop rule, owner decision, and follow-up policy;
- one Run Record for every admitted cell;
- Measurement Set, Evidence Receipt, and claim-first public projection;
- study-local action/follow-up sidecars only when their owner acts.

Every public causal claim must resolve to its own Measurement Set rows. A gate
result, profile, or lifecycle sidecar cannot substitute for observation
evidence.

## Release gates

Alpha.9 requires all of the following:

1. the no-call discrimination gate and Study Quality Preflight pass before any
   scored call;
2. exact candidates, schedules, task/evaluator packages, budgets, analysis,
   missing-cell policy, and stop rules are frozen;
3. every admitted cell is retained or explicitly classified invalid/missing;
4. the terminal claim and owner decision are computed without changing the
   frozen rule;
5. negative, null, harmful, and invalid outcomes remain publishable;
6. historical Contract v0 schemas and released evidence remain unchanged;
7. source graph, study audit, frozen bytes, package, clean-install, archive,
   Docker isolation, and exact-SHA CI gates pass;
8. the tag-built assets and manifest are downloaded and verified before the
   GitHub prerelease is published.

## Deliberately deferred

- Systematic Debugging outcome closure, role-separated replication, and the
  third-party skill study remain separate evidence steps;
- reader-comprehension and method-fitness work do not change the Completion
  effect estimate;
- model × scaffold studies, EGCAI, StateSuff, Council Generation 2, and
  Structural Search remain behind their existing readiness gates;
- lifecycle generalization waits for two materially different prospective
  families to require the same fields, transitions, invariants, and consumers.

## Council consultation ledger

Route: two-profile engineering council because the next release boundary can
stabilize public evidence and study-family architecture.

- `clean_boundary_architect` — completed,
  `AEL-CA-ALPHA9-20260814-01`;
- `evolutionary_deep_pragmatist` — completed,
  `AEL-EDP-ALPHA9-20260814-01`.

Both recommend a terminal empirical Completion Integrity release, reuse of the
existing evidence kernel, study-local semantics, and no premature Contract or
platform generalization. The material dissent was initial scale: the boundary
lens retained the roadmap's 8–12-task repeated design, while the pragmatist
preferred the smallest capped two-mechanism pilot with two repeats and limited
probes. The integrated design keeps three repeats for core cells but prevents
paraphrase and confirmation from becoming a full factorial expansion. The
exact final schedule remains owned by the frozen post-calibration design.

The implementation audit added four independent first passes over one shared
factual brief:

- `clean_boundary_architect` — completed,
  `AEL-CA-ALPHA9-20260814-02`;
- `domain_model_cartographer` — completed,
  `AEL-DM-ALPHA9-20260814-02-01` through `-05`;
- `evolutionary_deep_pragmatist` — completed,
  `AEL-EDP-ALPHA9-20260814-02-01` through `-05`;
- `production_systems_sentinel` — completed,
  `AEL-PSS-ALPHA9-20260814-02-01` through `-05`.

All four preserve a study-local vertical slice and reject premature lifecycle
generalization. The principal reconciled dissent was terminal-marker failure:
malformed output is retained as a valid indeterminate agent behavior, while
exogenous transport or evaluator failure alone is operational invalidity. The
production review also requires an append-only attempt ledger and local
private-corpus leakage gate before any scored submission.

## Strongest rejected alternatives

The strongest architecture alternative is to generalize the existing
Systematic Debugging lifecycle now. It could reduce repeated hashing and
scheduling code, but would expose one study's incidental fields as a shallow
universal API before a second lifecycle exists.

The strongest sequencing alternative is to make the scheduled Systematic
Debugging follow-up the next release. Prefer it only if owner outcome evidence
becomes available while Completion Integrity still lacks a valid candidate or
discriminating task instrument. It remains essential for beta, but it does not
replace the next new intervention decision by default.

## Reversal and generalization triggers

Narrow or stop if deterministic acceptance cannot be owned without leaking the
answer, baseline discrimination remains at a floor or ceiling, variance makes
the decision threshold unreachable inside the capped budget, or the prompt
policy increases critical failures.

Generalize lifecycle structure only after two materially different prospective
families complete admission through follow-up, independently need the same
shape, and duplicated local code causes an observed defect or an external
consumer needs a stable serialized interface. A custom runner, database, or
dynamic extension point additionally requires an observed isolation,
telemetry, concurrency, query, or extension bottleneck.

## Pre-execution closure

The architecture, construct vocabulary, exact prompt bytes, private-pack
identity, 52-cell schedule, call ceiling, estimator, decision thresholds,
runtime image identities, no-call gate, sacrificial headroom, quality profile,
preflight, and owner admission are materialized. Freeze revision 3 is the only
execution-authoritative revision: it was produced after admission, binds the
final freeze-bound code closure, and declares zero scored calls. Revisions 1
and 2 are retained as invalid pre-execution history and cannot authorize a
submission.

## Terminal result

All 52 frozen cells terminated validly with no ambiguous submission or outcome
retry. Baseline and treatment each produced a `0.375` equal-task-weighted
false-completion rate, for a primary reduction of `0.000` and a deterministic
80% task-cluster interval of `[0.000, 0.000]`. All anti-abstention guardrails
passed, but neither mechanism met the routing rule. The frozen decision is
`null`; the owner disposition is `reject_exact_policy`, recorded but not
deployed.

The public bundle, report, and result card retain this negative result. The
completed study validates the architecture boundary and prospective chain; it
does not show that the prompt helped. Release publication remains externally
owned by the exact tag, CI run, release manifest, and GitHub prerelease.
