# Agentic Evidence Lab

**An open research lab for finding out which agent systems work, where, and
why — backed by a file-first evidence toolkit.**

[![CI](https://github.com/kizz-tech/agentic-evidence-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/kizz-tech/agentic-evidence-lab/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-alpha-orange.svg)](https://github.com/kizz-tech/agentic-evidence-lab/releases)

Agentic Evidence Lab (AEL) runs and publishes reproducible studies of versioned
skills, prompts, models, tools, agent topologies, context policies, runtimes,
and complete workflows. Its long-term goal is a cumulative public map of which
agent configurations work for which task classes, budgets, and risk boundaries
— and a mechanism for recursively improving the capabilities we build.

Instead of asking only whether the final answer scored higher, AEL records the
exact system that ran, what changed, what stayed fixed, what it cost, which
failures appeared, and what conclusion the evidence actually permits.

```text
concept → frozen study → matched runs → measurements → evidence receipt
```

The goal is not one context-free score. It is reusable knowledge and honest,
task-specific comparisons.

## What the Lab publishes

- **Runs** — versioned observations bound to the exact agent stack, task,
  runtime, budget, output, and operational state.
- **Studies and conclusions** — human-readable reports plus machine-readable
  receipts that say what is supported, unsupported, and invalidating.
- **Benchmarks and task packs** — public evaluation surfaces with deterministic
  postconditions where possible.
- **Contextual leaderboards** — comparisons within the same frozen task pack,
  budget, evaluation contract, and comparison mode.
- **Capabilities** — skills, councils, environments, and workflows developed
  from the accumulated evidence, released on their own lifecycles.

See the current [Results Index](RESULTS.md). The first alpha contains 18 public
run records across two completed studies. They answer different questions and
therefore are not collapsed into a fake global ranking.

## Why AEL exists

An “agent” result is produced by a whole stack:

```text
model + runtime + prompt + tools + skills + context + permissions + workflow
```

Change several parts at once and a model-only claim is no longer justified.
Look only at the final answer and you can miss broken tool execution, unused
skills, secret exposure, excess work, invalid retries, or a workflow that merely
looks sophisticated.

AEL makes those distinctions explicit and machine-readable.

## What is included

- Five JSON document types: `Concept`, `Study Manifest`, `Run Record`,
  `Measurement Set`, and `Evidence Receipt`.
- JSON Schema plus cross-document validation, hash binding, and deterministic
  receipt rendering.
- Controlled-factor and complete operational-stack comparison modes.
- An offline Docker runner for executable fixtures and task-pack evaluation.
- A controlled-egress Codex adapter for maintainer-controlled inputs.
- Public examples that preserve negative, narrow, and inconclusive results.

## Five-minute start

Requirements: Python 3.11 or later and [`uv`](https://docs.astral.sh/uv/).
Docker is optional.

```bash
git clone https://github.com/kizz-tech/agentic-evidence-lab.git
cd agentic-evidence-lab
uv sync --locked

uv run ael --version
uv run ael validate examples
uv run ael render examples/council-generation-1/evidence-receipt.json
uv run python -m unittest discover -s tests -v
```

Expected validation summary for this release:

```text
validation passed: 30 document(s); concept=4, evidence_receipt=2,
measurement_set=2, run_record=18, study_manifest=4
```

To test the offline execution boundary:

```bash
uv run ael sandbox doctor
uv run ael sandbox build --context docker/runner

output=$(mktemp -d)
uv run ael sandbox run \
  --fixture docker/runner/smoke-fixture \
  --output "$output/result" \
  -- python mutate.py
```

## How a study works

1. Define the intervention's idea and proposed mechanism without silently
   rewriting it after seeing results.
2. Freeze the baseline, treatment, changed factors, tasks, budget, roles,
   analysis, selection rule, and stop rule.
3. Execute matched runs and preserve operational failures separately from poor
   answers.
4. Measure deterministic outcomes, process behavior, critical failures, cost,
   and limitations without forcing them into one global score.
5. Emit a receipt with supported claims, unsupported inferences, role overlap,
   invalidation triggers, and an adopt/reject/narrow/inconclusive decision.

The contract binds the artifacts by SHA-256. It does not pretend that schema
validity proves task quality, causal identification, or real-world transfer.

## Current evidence

### Council Generation 1

The first mapping compared direct, sequential, historical Council, and a frozen
adaptive Council workflow on three held-out synthetic engineering cases. It did
**not** establish a general quality win. It did expose an execution-conformance
failure in the historical skill and supported only a narrow local workflow
decision.

- [Machine-readable receipt](examples/council-generation-1/evidence-receipt.json)
- [Sanitized report](reports/2026-08-12-council-generation-1.md)

### Codex skill calibration

Six maintainer-controlled Codex cells verified the runner and treatment
activation path. Baseline and treatment both passed all three tasks, producing
a ceiling effect. The result is therefore an operational calibration, not proof
that the skill improves code quality.

- [Machine-readable receipt](examples/coding-skill/calibration-v1/evidence-receipt.json)
- [Calibration report](reports/2026-08-12-focused-change-verification-codex-calibration.md)

Publishing an inconclusive result is part of the method, not a failed launch.

## Leaderboards

AEL will publish leaderboards when multiple eligible candidates have been run
against the same frozen evaluation contract. Each board must expose:

- task pack, strata, comparison mode, and eligibility rules;
- exact model/runtime/tool/skill configuration and revision;
- matched budget, run count, uncertainty, and data freshness;
- primary outcome, critical failures, cost, and Pareto tradeoffs;
- maintainer/evaluator role overlap and replication state.

Operational-stack boards answer “what should I use for this job?” Controlled-
factor boards investigate “which changed component caused the difference?” The
two are never mixed into a model-only claim. See
[`docs/leaderboards.md`](docs/leaderboards.md).

## Security boundary

The offline runner is the default for untrusted executable fixtures. It uses a
read-only canonical fixture, tmpfs workspace, disposable output staging,
read-only container root, dropped capabilities, resource limits, and no network
by default.

The hosted Codex adapter is **not safe for third-party submissions**. Its agent
process can read the reusable credential. Exact-host egress filtering cannot
prevent exfiltration to an allowed provider host, so the CLI refuses to run
without the explicit `--trusted-input-only` acknowledgement.

Read [`SECURITY.md`](SECURITY.md) and
[`docs/runner-isolation.md`](docs/runner-isolation.md) before executing model or
third-party code.

## Alpha status

`v0.1.0-alpha.1` is the first public alpha. The Python package, schemas, and CLI
may change incompatibly before `1.0`. Pin an exact release and preserve the
receipt and artifact hashes used by your study.

This release does not claim:

- a universal agent benchmark or certification system;
- independent verification of Kizz-authored capabilities;
- safety for hosted execution of untrusted skills or repositories;
- model superiority from comparisons where the surrounding stack differs;
- downstream production or business impact.

## Documentation

- [Contract v0](docs/contract-v0.md) — document types and enforced invariants.
- [Architecture](docs/architecture.md) — components and ownership boundaries.
- [Reproducibility](docs/reproducibility.md) — clean-checkout verification.
- [Schema versioning](docs/schema-versioning.md) — alpha compatibility policy.
- [Review intake](docs/reviews/README.md) — how external criticism becomes a
  traceable decision rather than an instruction.
- [Leaderboard contract](docs/leaderboards.md) — eligibility and publication
  rules for contextual rankings.
- [Release notes](docs/release-notes/v0.1.0-alpha.1.md) — exact first-alpha
  scope and limitations.

## Contributing

Methodology criticism, replications, adapters, task packs, and narrowly scoped
fixes are welcome. Start with [`CONTRIBUTING.md`](CONTRIBUTING.md) and use the
methodology-review issue template for evidence or inference challenges.

Security reports belong in GitHub Private Vulnerability Reporting, not public
issues.

## Citation and license

Created by **Ryuhmanov M** under the **Kizz** organization. Cite the software
using [`CITATION.cff`](CITATION.cff) and cite the exact evidence receipt used in
your work.

Licensed under the [Apache License 2.0](LICENSE).
