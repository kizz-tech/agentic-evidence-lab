# Systematic Debugging real-shadow v1

## Answer first

The exact source-locked Superpowers `systematic-debugging` snapshot did not
earn automatic routing on this pilot. All four matched task pairs tied on final
acceptance: three tasks were accepted in both conditions and one was rejected
in both. The treatment also recorded one critical failure, so the frozen
safety gate produced `treatment_critical_failure` and the preregistered owner
policy blocked this exact snapshot on the tested Codex stack.

This is not evidence that systematic debugging is useless, that Superpowers is
bad, or that the treatment harmed performance relative to baseline. The same
task produced a critical failure in both conditions. It is a conservative,
screening-derived decision about one exact skill tree, four sanitized fixtures,
one model/runtime configuration, and one stochastic draw per condition.

## Decision and action

- Effect outcome: `treatment_critical_failure`.
- Pair classifications: `0` favorable, `0` unfavorable, `4` ties.
- Final acceptance: `3/4` for baseline and `3/4` for treatment.
- Treatment activation: `4/4` exact `SKILL.md` retrievals verified.
- Critical failures: `1/4` for baseline and `1/4` for treatment.
- Owner disposition: `reject_exact_version`.
- Action: a verified AEL/Kizz routing-policy record blocks only revision
  `44c9b2d6e889982ac18c27d05a19fefe335194e1`, tree
  `46da4917c596a8c90ca03cc1f91992cee66eaec9208cb9be2edb3fbd2a0c746f`,
  on the frozen stack. No global install or removal was performed.
- Follow-up: scheduled through `2026-09-12T23:59:59Z` for the next ten
  naturally eligible internal debugging cases or 30 days, whichever comes
  first. It can test policy operation and surface a reason to readmit a changed
  version; it cannot turn this pilot into independent replication.

The safety gate was absolute rather than comparative: any treatment critical
failure blocks routing even when the baseline fails the same task. That rule
was fixed before scored work. It protects the owner action from a tiny pilot
silently normalizing a severe failure, but it also makes this result unsuitable
for a claim that the skill caused harm.

## What was tested

The controlled factor was the presence of one exact, source-locked
`systematic-debugging` skill tree. Everything else was intended to remain
matched:

- `B0`: Codex baseline without the candidate skill;
- `S1`: the same Codex stack with only the candidate skill installed;
- Codex CLI `0.146.0`;
- `gpt-5.6-sol`, reasoning effort `xhigh`;
- four private, sanitized AEL defect-derived fixtures;
- two declared strata: `cross-boundary-contract` and
  `state-order-lifecycle`;
- one frozen schedule of eight scored calls in Docker;
- deterministic hidden acceptance, root-cause invariant, reference
  compatibility, safe-scope, activation, token, and wall-time measurements.

All eight calls completed as valid. Private task, event, candidate, and
evaluator bytes remain outside the repository and are represented by hashes.
The public Contract v0 graph contains eight run records and 80 measurements.

## Descriptive cost observations

These totals are descriptive, not stable cost effects:

| Condition | Generated tokens | Wall time | Accepted | Critical failures |
| --- | ---: | ---: | ---: | ---: |
| `B0` | 33,106 | 676,315 ms | 3/4 | 1/4 |
| `S1` | 32,109 | 616,685 ms | 3/4 | 1/4 |

Eight hosted calls are far too few to infer a durable latency or token advantage.

## Prospective chain

The study used an experimental prospective contract rather than retrofitting
admission after the result:

1. the study manifest, owner action policy, exact source, private-pack digest,
   code/prompt/image bindings, schedule, budget, and effect rule were frozen;
2. commit `58c73ab76630002145599ddb7b3837aa27018bc9` recorded those bytes before
   the scored result artifacts existed;
3. eight authorized scored calls ran once, without outcome-dependent retries;
4. the effect decision was recomputed from the frozen rule;
5. the admitted owner policy resolved the effect outcome to an exact-version
   block;
6. a separate action record and scheduled outcome follow-up were written.

Git proves repository artifact ordering. It does not independently timestamp
private model calls or establish independent execution.

## Disclosed projection deviation

The frozen materializer completed the evidence and lifecycle files but then
failed Contract v0 validation because it emitted the undeclared
`partially_rerunnable` reproducibility value. The scored observations and
effect decision were already complete and were not changed.

A one-field post-run projection repair mapped that invalid value to the
Contract v0 `rerunnable` enum, disclosed the deviation in the receipt, and
recomputed only dependent hash references. The audit reconstructs the original
invalid receipt bytes, checks the repair tool and frozen materializer hashes,
and requires the public effect decision to remain byte-bound. This is a
publication-layer repair, not a preregistered analysis change; it cannot raise
the claim ceiling.

## What the result supports

- On these four exact fixtures, the treatment did not improve final acceptance.
- The exact treatment activated in all four treatment calls.
- The frozen absolute safety gate was tripped by one treatment critical failure.
- The resulting owner action is a reversible block of one exact snapshot on one
  exact stack.

## What the result does not support

- a general verdict on systematic-debugging skills or Superpowers;
- a claim that the skill caused the critical failure;
- transfer to other defects, repositories, models, CLIs, prompts, or teams;
- a public leaderboard rank;
- a stable token or latency comparison;
- independent replication or downstream outcome evidence.

## Reproduce the public audit

```bash
uv run ael study audit \
  --freeze studies/agent-skills-season-1/screening/systematic-debugging-real-shadow.freeze.json \
  --result studies/agent-skills-season-1/results/systematic-debugging-real-shadow-v1 \
  --decision-adapter systematic-debugging-real-shadow-v1 \
  --require-git-proof
```

The audit validates the public Contract v0 graph, reconstructs the effect from
public measurements, checks admission-to-action hashes, verifies the disclosed
projection repair, and checks Git artifact ordering. It does not rerun the
withheld fixtures or hosted model calls.
