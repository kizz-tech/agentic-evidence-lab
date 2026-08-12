# Agentic Evidence Lab

**Open, task-specific evidence for deciding which agent systems work, where,
and under what conditions.**

[![CI](https://github.com/kizz-tech/agentic-evidence-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/kizz-tech/agentic-evidence-lab/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-alpha-orange.svg)](https://github.com/kizz-tech/agentic-evidence-lab/releases)

[**Browse results**](RESULTS.md) ·
[**Understand the method**](docs/contract-v0.md) ·
[**Evaluate a system**](#evaluate-your-own-system) ·
[**Read the documentation**](docs/README.md)

Agentic Evidence Lab (AEL) compares versioned skills, prompts, models, tools,
agent topologies, context policies, runtimes, and complete workflows. It records
the exact system that ran, what changed, what stayed fixed, what failed, what it
cost, and what decision the evidence actually supports.

The goal is not a universal agent score. It is a cumulative public map of which
agent configurations work for particular task classes, budgets, and risk
boundaries.

## Latest findings

| Study | What was tested | Result | Decision |
| --- | --- | --- | --- |
| [Property-based Testing v2](reports/2026-08-12-property-based-testing-v2.md) | Exact Codex stack with and without one pinned public skill; eight valid cells across four private tasks | All four matched pairs tied on hidden acceptance. Treatment activated 4/4 but had two critical added-test incompatibilities, as did baseline. | Reject this exact skill injection for this exact pilot surface. Repeat 2 and confirmation remained locked. |
| [Council Generation 1](reports/2026-08-12-council-generation-1.md) | Four engineering-decision workflows; 12 runs across three synthetic held-out cases | The adaptive candidate did not show a general quality advantage. It did repair a reproduced execution-conformance defect while preserving measured quality. | Adopt the exact workflow only for the measured local surface. Do not claim that councils are generally superior. |
| [Focused Change Verification calibration](reports/2026-08-12-focused-change-verification-codex-calibration.md) | The same Codex stack with and without one skill; six runs across three public coding tasks | All six runs passed, so the task pack could not distinguish the skill from baseline. The runner and skill activation worked. | Keep the pack as an operational smoke test. Do not infer that the skill improves code quality. |
| [Agent Skills Season 1 activation](reports/2026-08-12-agent-skills-season-1-activation.md) | 22 retained Codex cells across ten public-skill studies | The controlled runner and evaluators worked; ten of twelve treatment skills were explicitly read. MCP-builder and webapp-testing were injected but did not activate. Two benchmark defects were found and invalidated before publication. | Advance the ten activated snapshots to discriminating screening. Redesign MCP and webapp activation tasks first. Do not publish a skill-effect leaderboard. |

These studies answer different questions and cannot be combined into a global
ranking. See the [Results Index](RESULTS.md) for direct usage guidance,
limitations, evidence strength, and links to every public artifact.

Active research: [Agent Skills Season 1](studies/agent-skills-season-1/README.md)
now has ten bounded protocols, exact upstream source locks, a healthy public
calibration pack, 22 formal activation records, and a completed
[Property-based Testing v2 pathfinder](reports/2026-08-12-property-based-testing-v2.md).
The pathfinder is the first preregistered third-party skill-effect result and is
negative for its exact surface; arbitrary submissions remain outside the
maintainer-controlled execution boundary.

## What AEL helps answer

An agent result is produced by a whole stack:

```text
model + runtime + prompt + tools + skills + context + permissions + workflow
```

AEL supports two kinds of practical question:

- **Which complete stack should I use for this task?** Compare runnable systems
  under the same task pack, budget, and evaluation contract.
- **Did this exact change help?** Hold the surrounding stack fixed and vary a
  declared skill, prompt, tool, model, or workflow factor.

It also exposes failures that a final-answer score can hide: a skill that never
loaded, a workflow that did not execute as claimed, invalid retries, critical
omissions, excessive generated work, or a result that cannot support the
headline written about it.

## How a test works

```text
idea → frozen comparison → matched runs → measurements → bounded decision
```

1. Define the intervention and the claim being tested.
2. Freeze the baseline, changed factors, tasks, budget, roles, and stop rule.
3. Run matched conditions and retain poor answers, failures, and invalid runs.
4. Measure task outcomes, critical failures, process behavior, cost, and
   limitations separately.
5. Publish a human report and a machine-readable evidence receipt stating what
   is supported, unsupported, and invalidating.

The receipt is bound to exact artifacts by SHA-256. Structural validity does
not by itself prove task quality, causality, transfer, or real-world impact.

## Inspect the evidence

Every completed study can expose four levels of detail:

1. **Decision summary** — what to use, avoid, or test next in [RESULTS.md](RESULTS.md).
2. **Narrative report** — comparison, measurements, limitations, and reasoning.
3. **Evidence receipt** — machine-readable claims, decisions, provenance, and
   invalidation triggers.
4. **Study records** — frozen manifest, individual runs, and measurement set.

Start with the decision summary. Open raw evidence only when you need to audit,
reproduce, or reuse the result.

## Run the public checks

Requirements: Python 3.11 or later and [`uv`](https://docs.astral.sh/uv/).
Docker is optional.

```bash
git clone https://github.com/kizz-tech/agentic-evidence-lab.git
cd agentic-evidence-lab
uv sync --locked

uv run ael validate examples
uv run ael render examples/council-generation-1/evidence-receipt.json
uv run python -m unittest discover -s tests -v
```

Expected validation summary for this release:

```text
validation passed: 30 document(s); concept=4, evidence_receipt=2,
measurement_set=2, run_record=18, study_manifest=4
```

These commands validate the public evidence contract and content integrity.
They do not rerun historical model calls or independently reproduce the
research result. See [Reproducibility](docs/reproducibility.md) for those
boundaries.

## Evaluate your own system

The smallest study starts from an existing example:

1. Write a `Concept` describing the idea and proposed mechanism.
2. Freeze a `Study Manifest` with baseline, treatment, tasks, budget, and
   analysis rules.
3. Produce one `Run Record` for every condition, task, and repeat.
4. Record evaluator-owned outcomes in a `Measurement Set`.
5. Author an `Evidence Receipt`, then validate and render it with the CLI.

Use [Contract v0](docs/contract-v0.md) for the five document types and
[the public examples](examples) as executable starting points. The contract is
runner-independent: AEL can describe results from Codex, Claude Code, Cursor,
bare model APIs, or another execution system when their actual configuration
and limitations are recorded honestly.

The included Docker adapter is available for executable fixtures. Read the
[runner boundary](docs/runner-isolation.md) before model or third-party code.

## Leaderboards

AEL will publish a leaderboard only when multiple eligible candidates share the
same frozen task pack, evaluator, budget rule, and comparison mode. Until that
condition exists, the project publishes separate result cards and receipts
rather than a misleading global rank.

See the [leaderboard contract](docs/leaderboards.md) for eligibility,
uncertainty, critical-failure, cost, freshness, and correction rules.

## Security and alpha limits

The offline Docker runner is the default for untrusted executable fixtures. It
uses a disposable workspace, read-only canonical input, bounded resources, and
no network by default.

The hosted Codex adapter is **not safe for third-party submissions** because the
agent process can read its reusable credential. It is restricted to exact,
maintainer-reviewed snapshots and maintainer-controlled fixtures; arbitrary
submissions remain blocked. Read [SECURITY.md](SECURITY.md) and
[Container runner isolation](docs/runner-isolation.md) before execution.

`v0.1.0-alpha.3` is pre-stable. It does not claim universal benchmarking,
independent verification of Kizz-authored capabilities, model-only superiority
from stack comparisons, or downstream production impact.

## Documentation

Use the [documentation map](docs/README.md) to find the right level of detail:
results, evaluation, reproducibility, execution, methodology, active research,
governance, and release history.

## Contributing

Replications, methodology criticism, adapters, task packs, and narrowly scoped
fixes are welcome. Start with [CONTRIBUTING.md](CONTRIBUTING.md). Security
reports belong in GitHub Private Vulnerability Reporting, not public issues.

## Citation and license

Created by **Ryuhmanov M** under the **Kizz** organization. Cite the software
using [CITATION.cff](CITATION.cff) and cite the exact evidence receipt used in
your work.

Licensed under the [Apache License 2.0](LICENSE).
