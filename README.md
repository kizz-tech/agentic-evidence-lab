# Agentic Evidence Lab

**Evidence for better agent systems.**

[![CI](https://github.com/kizz-tech/agentic-evidence-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/kizz-tech/agentic-evidence-lab/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-alpha-orange.svg)](https://github.com/kizz-tech/agentic-evidence-lab/releases)

[**Browse decisions**](RESULTS.md) ·
[**Understand the method**](docs/contract-v0.md) ·
[**Evaluate a system**](#evaluate-your-own-system) ·
[**See the roadmap**](ROADMAP.md) ·
[**Read the documentation**](docs/README.md)

Better agent systems need more than bigger models. Agentic Evidence Lab (AEL)
tests exact changes to the system around a model: skills, prompts, tools,
context, models, runtimes, agent topologies, and complete workflows.

Each study is built to answer a practical question: should this exact change be
adopted, rejected, narrowed to a task class, or tested again? The result links
the decision to the tested configuration, task scope, observed cost and
failures, reliability evidence when measured, and the conditions that require
revalidation.

The long-term goal is a cumulative public map of how to get more useful work
from available models through better agent-system design. Today, AEL is an
open-source research alpha for producing bounded, auditable decisions about
versioned agent-stack changes. It is not a universal agent score or a claim
that one configuration works everywhere.

## What AEL publishes

```text
decision → exact change → task scope → observed outcomes and cost
         → revalidation trigger → evidence receipt
```

- **A practical verdict** — adopt, reject, narrow, or gather more evidence.
- **The exact tested system** — artifact versions, surrounding stack, budget,
  permissions, and evaluator identity.
- **The evidence boundary** — what improved or failed, what was not measured,
  and where the conclusion stops.
- **An audit path** — a human result card, machine-readable receipt, and the
  study records that support it.

## Start with the decisions

The generated [Results Index](RESULTS.md) is the fastest way to see what was
tested, the decision each study supports, and the scope where that decision
applies. Open the linked report or receipt when you want to inspect the full
comparison.

The index is generated from the validated evidence graph. It is navigation,
not a second source of research truth. Catalog membership is not GitHub release
state, and every card separates what a public checkout can verify, what only the
maintainer can rerun as a new observation, and what has independent replication
evidence.

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

1. **Decision summary** — what to use, avoid, or test next in the generated
   [Results Index](RESULTS.md).
2. **Narrative report** — comparison, measurements, limitations, and reasoning.
3. **Evidence receipt** — machine-readable claims, decisions, provenance, and
   invalidation triggers.
4. **Study records** — frozen manifest, individual runs, and measurement set.

Start with the generated cards. They are projections over the full validated
graph, not authority; open raw evidence only when you need to audit, reproduce,
or reuse the result.

The active [Agent Skills Season 1](studies/agent-skills-season-1/README.md)
program contains ten bounded protocols, exact source locks, activation records,
and the completed Property-based Testing and Systematic Debugging studies.
Arbitrary submissions remain outside the maintainer-controlled execution
boundary.

## Run the public checks

Requirements: Python 3.11 or later and [`uv`](https://docs.astral.sh/uv/).
Docker is optional.

```bash
git clone https://github.com/kizz-tech/agentic-evidence-lab.git
cd agentic-evidence-lab
uv sync --locked

uv run ael validate examples
uv run ael render examples/council-generation-1/evidence-receipt.json
uv run ael study preflight \
  studies/quality-preflight/examples/pass/quality-profile.json \
  --json-output studies/quality-preflight/examples/pass/preflight.json \
  --markdown-output studies/quality-preflight/examples/pass/preflight.md \
  --check
uv run ael results check studies/public-results.json --require-git-proof
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
uv run python -m unittest discover -s tests -v
```

Expected validation summary for alpha.7:

```text
validation passed: 30 document(s); concept=4, evidence_receipt=2,
measurement_set=2, run_record=18, study_manifest=4
```

The study audit additionally checks the freeze, terminal decision, public runs,
measurements, receipt, and repository artifact ordering as one bundle. The
explicit PBT v2 decision adapter also recomputes its exact counts and terminal
outcome. Git ancestry proves repository artifact ordering only; it does not
prove that private model calls occurred before results or reconstruct private
events. These commands do not rerun historical model calls or independently
reproduce the research result. See [Reproducibility](docs/reproducibility.md)
for the exact boundaries and commands.

## Evaluate your own system

The current alpha supports maintainer-controlled study authoring and evidence
audit. It is not a hosted submission service, and arbitrary third-party
execution remains blocked. The smallest local study starts from an existing
example:

1. Write a `Concept` describing the idea and proposed mechanism.
2. Freeze a `Study Manifest` with baseline, treatment, tasks, budget, and
   analysis rules.
3. Run the pilot [Study Quality Preflight](docs/study-quality-preflight.md) to
   bind task/evaluator evidence, claim limits, decision rules, uncertainty, and
   execution declarations before scored work.
4. Produce one `Run Record` for every condition, task, and repeat.
5. Record evaluator-owned outcomes in a `Measurement Set`.
6. Author an `Evidence Receipt`, then validate and render it with the CLI.

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

The `0.1.0a7` development line is pre-stable. It does not claim universal
benchmarking, independent verification of Kizz-authored capabilities,
model-only superiority from stack comparisons, or downstream production
impact.

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
