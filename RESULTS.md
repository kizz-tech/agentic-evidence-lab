# Results Index

This is the public index of completed, planned, and superseded Agentic Evidence
Lab studies. A row is an experiment state and bounded conclusion, not a claim of
universal rank.

## Completed evidence

| Study | Public runs | Comparison | Decision | What the result supports |
| --- | ---: | --- | --- | --- |
| Council Generation 1 | 12 | Four engineering-decision workflows | Narrow local adoption | The candidate repaired an observed execution-conformance failure while preserving measured synthetic-case quality; the study does not establish general Council superiority. |
| Focused Change Verification calibration | 6 | Codex baseline vs the same stack with one skill | Keep as smoke surface; redesign tasks | The hosted runner completed six stable cells and loaded the treatment correctly; 6/6 acceptance created a ceiling, so no skill-effect claim is supported. |

### Council Generation 1

- [Council capability repository](https://github.com/kizz-tech/council)
- [Council v0.2.0-alpha.1](https://github.com/kizz-tech/council/releases/tag/v0.2.0-alpha.1)
- [Study manifest](examples/council-generation-1/study-manifest.json)
- [Run records](examples/council-generation-1/runs)
- [Measurements](examples/council-generation-1/measurement-set.json)
- [Evidence receipt](examples/council-generation-1/evidence-receipt.json)
- [Narrative report](reports/2026-08-12-council-generation-1.md)

Capability release: `v0.2.0-alpha.1` at commit
`f13a06163d448a317e264a9b987a3271c5423d26`; current engineering-skill
SHA-256: `fe4b1a7c7cb272c92b94fb2239cb904dfb0a3d272027d317f918c13451a2719f`.
The study evaluated the earlier frozen candidate SHA-256
`a22a1371711509778985bdbae999929903419355332645e299bdb38ce01432fe`.
This is a lineage link, not evidence that Generation 1 executed the later full
release bundle.

### Focused Change Verification calibration

- [Study manifest](examples/coding-skill/study-manifest.json)
- [Run records](examples/coding-skill/calibration-v1/runs)
- [Measurements](examples/coding-skill/calibration-v1/measurement-set.json)
- [Evidence receipt](examples/coding-skill/calibration-v1/evidence-receipt.json)
- [Narrative report](reports/2026-08-12-focused-change-verification-codex-calibration.md)

## Planned studies

| Study | State | Decision it is intended to support |
| --- | --- | --- |
| Council Generation 2 | Draft and calibrated, not run | Select whether an adaptive council beats a strong sequential baseline at matched budget on consequential engineering decisions. |
| Focused Change Verification discriminating pack | Design required | Determine whether the skill changes verification routing and truthful state reporting when task text does not restate the treatment. |
| Third-party capability transfer | Gated | Test whether Contract v0 can evaluate a licensed external capability without owner-only assumptions. |

## Why there is no leaderboard yet

The two completed studies use different interventions, tasks, estimands, and
decision questions. Ranking their conditions together would imply
comparability that does not exist.

The first leaderboard becomes admissible when at least two eligible candidates
share one frozen task pack, evaluation contract, budget rule, and comparison
mode, with enough repeated observations to report uncertainty and failures.
Until then, the receipts are the result.

See the [leaderboard contract](docs/leaderboards.md) for the publication rules.
