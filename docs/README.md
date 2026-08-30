# Documentation

Start with the question you are trying to answer. Most readers do not need the
entire evidence contract or runner design.

## I want to understand why AEL exists

- [AEL Method](method.md) — the claim-to-decision workflow, non-compensation
  rule, claim-specific support predicates, and public reading order.
- [AEL Coevolution Protocol](ael-cep.md) — the family-local protocol for
  evolving Builders and Evaluators while keeping evidence history, protected
  anchors, custody, and promotion authority outside the adaptive loop.
- [AEL-CEP Stage 0 implementation decision](decisions/2026-08-15-ael-cep-stage0-implementation.md)
  — the pure-kernel, strict-sidecar, deterministic no-effect implementation
  boundary and its reversal plan.
- [Public mission and value decision](decisions/2026-08-14-public-mission-and-value.md)
  — why user-facing decisions lead the public story while scientific rigor
  remains in the evidence layer.
- [Result catalog and reproduction semantics](decisions/2026-08-14-result-catalog-and-reproduction-semantics.md)
  — why catalog membership, public graph checks, maintainer reruns, independent
  replication, and external release state remain separate predicates.
- [Roadmap](../ROADMAP.md) — the next user-visible research question, trust
  work, beta gates, and explicit non-goals.
- [Alpha.9 Completion Integrity release design](decisions/2026-08-14-alpha9-completion-integrity-release-design.md)
  — the empirical release boundary, no-call admission gate, core comparison,
  architecture constraints, and stop rules.
- [Alpha.10 observable-enactment decision](decisions/2026-08-15-alpha10-observable-enactment-candidate.md)
  — why the instrument is released as method infrastructure while empirical
  admission remains pending real exercise.
- [Alpha.10 terminal-claim foundation](decisions/2026-08-15-alpha10-terminal-claim-foundation.md)
  — terminal semantics, sample-size admission, council evidence and deferred
  runtime/remediation boundaries.

## I want to see what works

- [Results Index](../RESULTS.md) — the generated human result projection with
  bounded decisions, decision-governing claim states, observed
  repeat/uncertainty facts, limitations, and links to supporting artifacts.
- [Machine-readable study index](results/index.json) — the generated catalog
  consumed by tooling; cards are disposable projections, not a second evidence
  authority.
- [Council Generation 1](../reports/2026-08-12-council-generation-1.md) — the
  bounded adopt decision without claiming implemented adoption, downstream
  outcome, or general Council superiority.
- [Focused Change Verification calibration](../reports/2026-08-12-focused-change-verification-codex-calibration.md)
  — why the runner passed but the first skill task pack was rejected as an
  effect test.
- [Systematic Debugging real-shadow v1](../reports/2026-08-13-systematic-debugging-real-shadow-v1.md)
  — a prospective matched pilot whose frozen safety gate triggered an
  exact-version block and an explicit follow-up.
- [Completion Integrity prompt policy v1](../reports/2026-08-15-completion-integrity-prompt-policy-v1.md)
  — the first fully profiled prospective study: 52 valid cells, no measured
  false-completion improvement, and a frozen rejection of the exact policy.

## I want to evaluate a skill, model, or workflow

- [Contract v0](contract-v0.md) — the five public evidence documents and the
  invariants enforced between them.
- [Council example](../examples/council-generation-1) — a completed study with
  12 run records, measurements, and a bounded receipt.
- [Coding-skill example](../examples/coding-skill) — a controlled-factor study
  and six-cell operational calibration.
- [Architecture](architecture.md) — how the evidence core, execution adapters,
  evaluators, and capability repositories divide ownership.
- [Publication kernel decision](decisions/2026-08-14-publication-kernel-boundaries.md)
  — provenance ledger, closed audit adapters, pure rendering, dependency rules,
  and explicit scale triggers.
- [Study Quality Preflight](study-quality-preflight.md) — the pilot hash-bound
  design preflight, hard gates, warnings, public facets, and scientific boundary.
- [AEL Coevolution Protocol](ael-cep.md) — evaluator-release identity,
  immutable score lineage, rescore/replay classification, bridge and epoch
  rules, custody-separated promotion, per-stratum bridge gates, independent
  anchor truth, and the A0--A5 no-effect simulator. Stage 0's claim ceiling is
  local implementation invariants only, not empirical superiority or safety.
- [Completion Integrity observable enactment](completion-integrity-enactment.md)
- [Completion Integrity terminal claims](completion-integrity-terminal-claims.md)
- [Completion Integrity task supply](completion-integrity-task-supply.md)
  — three distinct experimental family-local policies for process diagnostics,
  claim accuracy and prospective task admission.

The contract is runner-independent. AEL can describe a complete operational
stack comparison or a controlled change to one declared factor, but the receipt
must not promote a stack result into a model-only claim.

## I want to reproduce or inspect evidence

- [Reproducibility](reproducibility.md) — deterministic validation, receipt
  reproduction, container checks, and the boundary between rerunning and
  independently reproducing a study.
- [AEL-CEP reproducibility boundary](reproducibility.md) — the dedicated
  protocol/bundle checks and deterministic Stage 0 simulation are documented
  alongside the existing evidence-graph checks; generic Contract v0 validation
  does not validate AEL-CEP sidecar artifacts.
- [Schema versioning](schema-versioning.md) — compatibility and migration rules
  for the pre-stable contract.
- [Release notes](release-notes/v0.1.0-alpha.1.md) — exact first-alpha contents
  and known limits.
- [Release notes](release-notes/v0.1.0-alpha.2.md) — Agent Skills Season 1
  activation evidence and exact study-revision validation.
- [Release notes](release-notes/v0.1.0-alpha.3.md) — first preregistered
  effectiveness pilot and negative-result evidence.
- [Release notes](release-notes/v0.1.0-alpha.4.md) — one-command frozen-study
  bundle audit and stricter Codex skill-activation evidence.
- [Release notes](release-notes/v0.1.0-alpha.5.md) — generated result cards,
  replication handoff, and release-evidence hardening.
- [Development-line notes](release-notes/v0.1.0-alpha.6.md) — prospective
  admission, public lifecycle projection, and the first decision-governing
  skill pilot.
- [Alpha.7 notes](release-notes/v0.1.0-alpha.7.md) —
  measurement-quality preflight, explicit reproduction facets, historical
  quality disclosure, and the public roadmap. This development line was not
  published and was superseded by alpha.8.
- [Release notes](release-notes/v0.1.0-alpha.8.md) — the claim-first method,
  explicit non-ordinal claim admission, observed repeat/uncertainty disclosure,
  and the regenerated projection. A note file is not proof of a tag or release.
- [Alpha.10 release notes](release-notes/v0.1.0-alpha.10.md) — the method-only
  measurement foundation and its empirical limits.
- [Alpha.11 release notes](release-notes/v0.1.0-alpha.11.md) — the real Codex
  activation failure, full-wrapper repair, and bounded alpha.12 admission path.
- [Alpha.12 release notes](release-notes/v0.1.0-alpha.12.md) — the bounded
  AEL-CEP Stage-0 method foundation and CLI/file-only compatibility boundary.
- [Alpha.13 release notes](release-notes/v0.1.0-alpha.13.md) — activation-v3's
  protocol-invalid result, exact task-contract qualification, and no-retry
  interruption finalization.
- [Alpha.9 release notes](release-notes/v0.1.0-alpha.9.md) — the terminal
  Completion Integrity null result and exact-policy rejection. A note file is
  not proof of a tag or release.
- [Changelog](../CHANGELOG.md) — user-visible project history.
- [Roadmap](../ROADMAP.md) — evidence-gated direction, beta criteria, and
  explicit non-goals; it is not a delivery promise.

Machine-readable manifests, runs, measurements, and receipts live under both
[`examples/`](../examples) and [`studies/`](../studies). Start from the generated
result projection or a narrative report before opening those raw records.

For the current Completion Integrity execution path, start with
[Completion Integrity activation](completion-integrity-activation.md), then
  open its [result card](results/completion-integrity-activation-v3.md),
  [narrative report](../reports/2026-08-30-completion-integrity-activation-v3.md),
  or [decision record](decisions/2026-08-30-completion-integrity-activation-v3-result.md).

## I want to run agent code safely

- [Container runner isolation](runner-isolation.md) — offline and hosted Codex
  execution boundaries, commands, residual risks, and model-access gate.
- [Security policy](../SECURITY.md) — supported versions, vulnerability scope,
  and the third-party submission restriction.
- [Container runner decision](decisions/2026-08-12-container-runner-boundary.md)
  — why disposable Docker workspaces became the default adapter.

The hosted Codex path is limited to maintainer-controlled content. It is not a
safe runner for untrusted third-party skills or repositories.

## I want to contribute or challenge the method

- [Contributing](../CONTRIBUTING.md) — setup, validation, and pull-request rules.
- [External review intake](reviews/README.md) — how criticism is captured,
  verified, accepted, rejected, or deferred without silently becoming project
  authority.
- [Governance](../GOVERNANCE.md) — alpha ownership and decision principles.
- [Support](../SUPPORT.md) — where to ask usage, methodology, and security
  questions.

## Publication and comparison rules

- [Leaderboard contract](leaderboards.md) — when results are comparable enough
  for a contextual ranking and which columns every board must expose.
- [First public release gate](publication-gate.md) — retained release-history
  contract for `v0.1.0-alpha.1`; not an onboarding guide.

There is no public leaderboard yet because the completed studies do not share
one frozen task pack, estimand, budget, and comparison mode. The generated
result cards remain separate and contextual; see the [leaderboard contract](leaderboards.md)
for the admission rule.

## Active research

These documents describe planned or gated work, not completed evidence unless
they link to a completed result:

- [Council Generation 2](../studies/council-generation-2/README.md)
- [Focused Change Verification](../studies/focused-change-verification/README.md)
- [Structural Search research program](structural-search.md)
- [Agent Skills Season 1](../studies/agent-skills-season-1/README.md) — ten
  bounded public-skill protocols, exact source locks, an executable public
  calibration pack, 22 activation records, and two completed bounded negative
  skill-effect results. The real-shadow study also exercises prospective
  admission, owner action, and follow-up; the remaining protocols are still
  calibration, design, or unrun work.
- [AEL Coevolution Protocol Stage 0](ael-cep.md) — a released, offline
  no-effect simulator and family-local policy boundary. One dependency-bound
  `contrast_summary` seals exact trajectory rows; the core derives operating
  metrics, primary endpoints, and diagnostic-only contrasts with explicit
  denominators. It is an implementation and adversarial-method test, not an
  empirical result or superiority claim.
- [Decision Utility v1](../studies/decision-utility-v1/README.md) — a checked
  synthetic calibration of evidence-equivalent decision views and scoring;
  human recruitment and outcomes remain blocked/not run.

Their draft manifests, simulations, and task-pack briefs must not be cited as
successful experimental results.

## Design and decision history

Decision records preserve why important boundaries changed:

- [Contract v0 kernel](decisions/2026-08-12-contract-v0-kernel.md)
- [Hosted Codex calibration boundary](decisions/2026-08-12-hosted-codex-calibration-boundary.md)
- [External review and v0 direction](decisions/2026-08-12-review-intake-and-v0-direction.md)
- [Structural Search roadmap](decisions/2026-08-12-structural-search-roadmap.md)
- [Agent Skills Season 1 architecture](decisions/2026-08-12-agent-skills-season-1.md)
- [Measurement-quality preflight](decisions/2026-08-14-measurement-quality-preflight.md)
- [Public mission and value](decisions/2026-08-14-public-mission-and-value.md)
- [Claim-first decision method](decisions/2026-08-14-claim-first-decision-method.md)
- [AEL-CEP Stage 0 implementation boundary](decisions/2026-08-15-ael-cep-stage0-implementation.md)
- [Alpha.12 AEL-CEP public boundary](decisions/2026-08-30-alpha12-public-boundary.md)
- [Evidence-to-Action execution status](decisions/2026-08-30-evidence-to-action-execution-status.md)
  — M0 publication, M1 instrument qualification, and the exact M2–M4 blockers.
- [Completion Integrity activation v3 result](decisions/2026-08-30-completion-integrity-activation-v3-result.md)
  — one submitted ambiguous attempt, no retry, root cause, and the v4 admission boundary.

[The Contract v0 drafting brief](contract-v0-brief.md) is retained as design
history. It does not replace the executable [current Contract v0](contract-v0.md).
