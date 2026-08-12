# Results

Use this page to answer three questions:

1. What was actually compared?
2. What decision does the evidence support?
3. How strong and transferable is that conclusion?

Each result is bounded to its exact tasks, system revisions, runtime, budget,
and evaluation contract. A result card is not a universal ranking.

## At a glance

| Study | Tested scope | Main finding | Practical decision | Evidence strength |
| --- | --- | --- | --- | --- |
| [Council Generation 1](#council-generation-1) | Four workflows; three synthetic held-out engineering cases; 12 runs | No general answer-quality win. The candidate repaired a reproduced execution-conformance defect and preserved measured quality. | **Narrow adoption:** use the exact workflow for the measured local Council surface; test again before transferring it. | Maintainer-evaluated; one run per cell; not independently reproduced. |
| [Focused Change Verification calibration](#focused-change-verification-calibration) | Same Codex stack with and without one skill; three public coding tasks; six runs | All six runs passed. The skill activated, but the task prompts gave baseline much of the intended behavior. | **No skill-effect decision:** keep the pack as a runner smoke test and design harder tasks. | Operational calibration; not a confirmatory comparison. |

## Council Generation 1

### Should I use it?

Use the published Council alpha as an experimental successor when you want its
adaptive engineering-decision workflow and accept that the supporting evidence
is narrow. Do not choose it because you believe this study proved that councils
outperform strong direct or sequential workflows in general—it did not.

| Question | Answer |
| --- | --- |
| What was compared? | Direct answer, fixed sequential revision, historical Engineering Council, and a frozen adaptive candidate. |
| On what tasks? | Three synthetic held-out cases: routine/local, consequential domain-policy, and consequential performance. |
| What happened? | Sequential, historical Council, and the candidate each averaged 3.93/4; direct averaged 3.83/4. All had zero critical-anchor misses. Every candidate difference remained inside the frozen tie threshold. |
| What changed materially? | The historical workflow reproduced a named-profile execution failure. The candidate repaired the mechanism, routed the routine task directly, and disclosed degraded execution requirements. |
| What did it cost? | On two consequential cases, the candidate used 9,598 output-plus-reasoning tokens versus 12,560 for the historical skill, about 23.6% less generated work. Its total input surface was larger, so this is not a universal cost claim. |
| What is supported? | A local replacement of the measured historical workflow with the exact frozen adaptive semantics. |
| What is not supported? | General Council superiority, equivalence, production impact, cross-model transfer, or universal cost reduction. |

**Read and use**

- [Read the result](reports/2026-08-12-council-generation-1.md)
- [Try the Council capability](https://github.com/kizz-tech/council)
- [Open the published Council alpha](https://github.com/kizz-tech/council/releases/tag/v0.2.0-alpha.1)

**Audit the evidence**

- [Machine-readable receipt](examples/council-generation-1/evidence-receipt.json)
- [Study manifest](examples/council-generation-1/study-manifest.json)
- [Measurements](examples/council-generation-1/measurement-set.json)
- [Individual run records](examples/council-generation-1/runs)

The published Council alpha is a later product-lineage successor. Generation 1
evaluated an earlier frozen candidate, not the complete later release bundle.
The exact hashes and revision boundary are preserved in the
[full result](reports/2026-08-12-council-generation-1.md#published-capability-lineage).

## Focused Change Verification calibration

### Should I use the skill?

This study cannot answer that question. It shows that AEL can run the same
Codex stack with and without the skill, verify that the skill loaded, preserve
the input fixtures, and evaluate exported work. It does not show that the skill
improves implementation correctness.

| Question | Answer |
| --- | --- |
| What was compared? | Codex CLI 0.146.0 with `gpt-5.6-sol` at `xhigh`, first without the skill and then with the frozen Focused Change Verification skill. |
| On what tasks? | Local unit behavior, a cross-module contract, and a populated SQLite migration. |
| What happened? | Baseline passed 3/3 and treatment passed 3/3. The skill was explicitly read in every treatment run. |
| Why is that inconclusive? | The public task prompts already prescribed much of the verification behavior contributed by the skill, creating a ceiling effect. |
| What did it cost? | In this one non-randomized calibration, treatment used about 8.3% more generated-work tokens and 14.1% more wall time. These are not stable cost estimates. |
| What is supported? | Runner operation, fixture preservation, evaluation export, and treatment activation. |
| What is not supported? | A correctness, code-quality, equivalence, cost, or transfer claim for the skill. |

**Read the decision**

- [Read the calibration result](reports/2026-08-12-focused-change-verification-codex-calibration.md)
- [See the next discriminating task-pack requirements](studies/focused-change-verification/discriminating-pack-brief.md)

**Audit the evidence**

- [Machine-readable receipt](examples/coding-skill/calibration-v1/evidence-receipt.json)
- [Study manifest](examples/coding-skill/study-manifest.json)
- [Measurements](examples/coding-skill/calibration-v1/measurement-set.json)
- [Individual run records](examples/coding-skill/calibration-v1/runs)

## Upcoming studies

These are plans, not completed evidence.

| Study | Current state | Intended decision |
| --- | --- | --- |
| [Council Generation 2](studies/council-generation-2/README.md) | Draft and illustratively calibrated; not run | Test whether a frozen adaptive Council candidate beats a strong sequential baseline with the same knowledge and matched budget. |
| [Focused Change Verification discriminating pack](studies/focused-change-verification/discriminating-pack-brief.md) | Design required | Test whether the skill changes verification routing and truthful state reporting when the task does not reveal the desired checks. |
| [Property-based Testing v2 pathfinder](studies/agent-skills-season-1/screening/property-based-testing-v2-analysis-plan.md) | Preregistered: exact baseline and skill snapshot, four screening tasks, two locked confirmation tasks, schedules, budgets, hashes, and stop rules frozen with zero scored calls | Test whether this exact skill injection improves hidden-adversarial acceptance on two bounded defect families. |
| [Remaining Agent Skills Season 1 studies](studies/agent-skills-season-1/README.md) | Activation calibration completed: 22 formal run records, ten receipts, ten of twelve skills explicitly read; other effectiveness studies unrun | Continue task-specific screening without a false global score. |

## Why there is no leaderboard yet

The completed studies use different interventions, tasks, estimands, and
decision questions. Ranking them together would create comparability that does
not exist.

A public board becomes admissible only when at least two candidates share one
frozen task pack, evaluation contract, budget rule, and comparison mode, with
enough repeated observations to report uncertainty and failures. Until then,
the result cards and receipts are the honest output.

See the [leaderboard contract](docs/leaderboards.md) for the full publication
rules.
