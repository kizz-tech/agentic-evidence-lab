# Property-based Testing v2 — preregistered pathfinder result

## Decision

Reject the exact pinned `property-based-testing` skill injection for the exact
Codex stack and private pilot surface measured here. The intervention produced
no favorable matched pair, and two treatment cells violated the prespecified
zero-critical-failure gate. Do not generalize this result into a claim about
property-based testing, Trail of Bits, Codex, or agent skills in general.

## What was tested

The controlled factor was one installed skill tree:

- `B0`: Codex CLI 0.146.0, `gpt-5.6-sol`, `xhigh`, no study skill;
- `S1`: the same stack plus the exact Trail of Bits `property-based-testing`
  skill from commit `304c81a8cefb6e3c029ebd0d12940ccf0713eccb`, tree hash
  `1697527a56b9e7b5cc47bb4dadd3fd26c3cb0f4af69ffc65205a19cbcc9d95d1`.

Four private screening tasks covered two declared families:
serialization-roundtrip and normalization-idempotence. The task prompt did not
name property-based testing or disclose hidden counterexamples. The evaluator
was staged only after each agent run and never mounted into its workspace.

The public [freeze](../studies/agent-skills-season-1/screening/property-based-testing-v2.freeze.json)
bound task-pack composites, randomized schedules, runtime image identities,
prompt, runner, execution dependencies, decision code, materializer, budgets,
and sequential thresholds before any scored call. Preregistration commit
`610f0d9e1e19d9c89dd6beba8fab7900222df5dd` passed GitHub CI run
`31604199862` and was tagged `property-based-testing-v2-freeze` before scored
execution began.

## Result

All eight repeat-1 cells were operationally valid. The treatment skill was
read in all four treatment cells. Binary hidden acceptance was identical:

| Outcome | Baseline | Treatment |
| --- | ---: | ---: |
| Hidden acceptance | 2/4 | 2/4 |
| Hidden failure | 2/4 | 2/4 |
| Added-test incompatibility | 2/4 | 2/4 |
| Flaky replay | 0/4 | 0/4 |
| Skill activation | not applicable | 4/4 |

Across matched task-repeat pairs: favorable `0`, unfavorable `0`, tied `4`.
Both conditions independently added edge tests in all four cells. Two cells in
each condition added tests incompatible with the private reference repair. The
baseline failures matter: this pilot does not show that the skill caused the
incompatibilities. It shows that injecting the skill created no hidden-
acceptance advantage and still failed the treatment safety gate.

The exact frozen continuation outcome was
`reject_all_critical_failure`. Repeat 2 was not run. The untouched confirmation
pack was not mounted or executed and remained locked.

## Cost and latency

| Descriptive total | Baseline | Treatment | Treatment difference |
| --- | ---: | ---: | ---: |
| Generated-work tokens | 37,341 | 47,330 | +26.8% |
| Wall time | 752,432 ms | 857,633 ms | +14.0% |

These totals cover four cells per condition. The sample is too small for a
stable cost claim, and provider behavior is not pinned to an immutable model
revision. With no outcome advantage, the pilot provides no evidence that the
additional observed cost bought value on this surface.

## What the evidence supports

- The exact skill activated reliably in this controlled Codex adapter.
- The exact intervention did not improve binary hidden acceptance in any of
  four matched pairs.
- The frozen stop rule correctly prevented extra repeat and holdout spending.
- A negative skill-effect result can be preregistered, executed in Docker,
  materialized, and published without exposing hidden task bytes.

## What it does not support

- that property-based testing or this upstream skill is generally ineffective;
- that the skill caused the two incompatible properties, because baseline had
  the same failures;
- equivalence between baseline and treatment beyond these four pairs;
- transfer to other tasks, models, CLIs, repositories, or production systems;
- a stable token or latency effect;
- independent verification. Kizz authored, operated, and evaluated the pilot.

## Audit trail

- [Analysis plan](../studies/agent-skills-season-1/screening/property-based-testing-v2-analysis-plan.md)
- [Freeze and schedule](../studies/agent-skills-season-1/screening/property-based-testing-v2.freeze.json)
- [Immutable study manifest](../studies/agent-skills-season-1/manifests/property-based-testing-v2.study-manifest.json)
- [Frozen terminal decision](../studies/agent-skills-season-1/results/property-based-testing-v2/decision.json)
- [Machine-readable measurements](../studies/agent-skills-season-1/results/property-based-testing-v2/measurement-set.json)
- [Evidence receipt](../studies/agent-skills-season-1/results/property-based-testing-v2/evidence-receipt.md)

Raw tasks, events, candidate workspaces, evaluator outputs, and credentials are
not public. Their permitted evidence references are content-addressed in the
public records. The reusable ChatGPT credential was readable by the Codex
process; inputs were maintainer-controlled, outputs were exact-value scanned,
and encrypted provider traffic was not inspected.
