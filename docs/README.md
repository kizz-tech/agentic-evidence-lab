# Documentation

Start with the question you are trying to answer. Most readers do not need the
entire evidence contract or runner design.

## I want to see what works

- [Results Index](../RESULTS.md) — current findings, practical decisions,
  evidence strength, limitations, and links to supporting artifacts.
- [Council Generation 1](../reports/2026-08-12-council-generation-1.md) — why
  the adaptive workflow was adopted locally without claiming general Council
  superiority.
- [Focused Change Verification calibration](../reports/2026-08-12-focused-change-verification-codex-calibration.md)
  — why the runner passed but the first skill task pack was rejected as an
  effect test.

## I want to evaluate a skill, model, or workflow

- [Contract v0](contract-v0.md) — the five public evidence documents and the
  invariants enforced between them.
- [Council example](../examples/council-generation-1) — a completed study with
  12 run records, measurements, and a bounded receipt.
- [Coding-skill example](../examples/coding-skill) — a controlled-factor study
  and six-cell operational calibration.
- [Architecture](architecture.md) — how the evidence core, execution adapters,
  evaluators, and capability repositories divide ownership.

The contract is runner-independent. AEL can describe a complete operational
stack comparison or a controlled change to one declared factor, but the receipt
must not promote a stack result into a model-only claim.

## I want to reproduce or inspect evidence

- [Reproducibility](reproducibility.md) — deterministic validation, receipt
  reproduction, container checks, and the boundary between rerunning and
  independently reproducing a study.
- [Schema versioning](schema-versioning.md) — compatibility and migration rules
  for the pre-stable contract.
- [Release notes](release-notes/v0.1.0-alpha.1.md) — exact first-alpha contents
  and known limits.
- [Changelog](../CHANGELOG.md) — user-visible project history.

Machine-readable manifests, runs, measurements, and receipts live under
[`examples/`](../examples). Start from a narrative report or result card before
opening those raw records.

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
one frozen task pack, estimand, budget, and comparison mode.

## Active research

These documents describe planned or gated work, not completed evidence:

- [Council Generation 2](../studies/council-generation-2/README.md)
- [Focused Change Verification](../studies/focused-change-verification/README.md)
- [Structural Search research program](structural-search.md)

Their draft manifests, simulations, and task-pack briefs must not be cited as
successful experimental results.

## Design and decision history

Decision records preserve why important boundaries changed:

- [Contract v0 kernel](decisions/2026-08-12-contract-v0-kernel.md)
- [Hosted Codex calibration boundary](decisions/2026-08-12-hosted-codex-calibration-boundary.md)
- [External review and v0 direction](decisions/2026-08-12-review-intake-and-v0-direction.md)
- [Structural Search roadmap](decisions/2026-08-12-structural-search-roadmap.md)

[The Contract v0 drafting brief](contract-v0-brief.md) is retained as design
history. It does not replace the executable [current Contract v0](contract-v0.md).
