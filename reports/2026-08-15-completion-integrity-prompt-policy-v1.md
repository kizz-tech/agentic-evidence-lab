# Completion Integrity prompt policy v1

## Answer first

The exact appended Completion Integrity prompt policy did **not** reduce false
completion on the frozen eight-task study. Baseline and treatment both produced
a `0.375` equal-task-weighted false-completion rate, so the primary reduction
was `0.000` with a deterministic 80% task-cluster bootstrap interval of
`[0.000, 0.000]`. The frozen owner rule therefore produced `null` and the
recorded disposition is `reject_exact_policy`.

This is a useful negative result. It prevents one plausible prompt-only policy
from becoming a default without evidence. It is not a general verdict on
completion prompts, structured verification, or the underlying model.

## Decision

- Public disposition: `reject`.
- Primary outcome: `0.000` false-completion risk reduction.
- False completion: `0.375` for `B0` and `0.375` for `T1`.
- Accepted final state: `0.375` for both conditions.
- False non-completion, indeterminate declaration, and critical failure: `0`
  for both conditions.
- Mechanism routing: neither `requirement_coverage` nor
  `acceptance_evidence` is eligible.
- Probe: `0.500` false completion in both conditions across four
  non-decision-governing paraphrase cells.
- Action: the exact prompt policy is recorded but not deployed.

Every frozen anti-abstention guardrail passed. The policy was rejected because
it produced no improvement, not because it traded false completion for silence,
false non-completion, or critical failures.

## What was tested

The only intended controlled factor was an exact appended prompt segment:

- `B0`: the pinned Codex stack without the candidate segment;
- `T1`: the same stack with `completion-policy-v1` appended;
- Codex CLI `0.146.0`, `gpt-5.6-sol`, reasoning effort `xhigh`;
- eight private maintainer-authored coding tasks across four strata and two
  completion mechanisms;
- three original-prompt repeats per task and condition;
- one declared paraphrase probe for two tasks under both conditions;
- 52 sequential hosted calls, all retained as valid, with no outcome retry;
- deterministic blinded final-state evaluation and marker classification.

The independent unit for the primary analysis is the task, not each stochastic
repeat. The task-cluster interval therefore resamples eight task clusters.

## Task-level result

Three tasks produced false completion in every original-prompt repeat under
both conditions: `CI-02`, `CI-05`, and `CI-07`. The other five tasks produced
none under either condition. Consequently every task-level reduction was zero.

| Mechanism | Tasks | False-completion reduction | Accepted-state delta | Route eligible |
| --- | ---: | ---: | ---: | --- |
| `requirement_coverage` | 4 | `0.000` | `0.000` | no |
| `acceptance_evidence` | 4 | `0.000` | `0.000` | no |

The result does not distinguish whether the added instructions were redundant
with the existing stack, ignored in the decisive cases, or too weak to alter
behavior. The frozen observations establish no effect for this exact delta;
they do not identify a universal mechanism for the null.

## Descriptive execution cost

These are retained totals for the 48 decision-governing original-prompt calls,
not stable economic effects:

| Condition | Calls | Generated tokens | Wall time |
| --- | ---: | ---: | ---: |
| `B0` | 24 | 145,576 | 2,684,471 ms |
| `T1` | 24 | 205,359 | 3,602,454 ms |

The four paraphrase probes added 11,911 / 17,280 generated tokens and 205,156 /
315,079 ms for `B0` / `T1`. This study was not powered or admitted to estimate
a durable token or latency effect.

## Prospective integrity

The study used the first complete prospective Study Quality Profile in AEL:

1. task provenance, evaluator calibration, exact intervention, schedule,
   budget, uncertainty rule, guardrails, and owner-action mapping were declared;
2. the revision-3 freeze recorded zero scored calls and bound the study,
   prompts, private pack, evaluator, runner, materializer, schedule, and policy;
3. commit `d0d506c67e48e1ec4e9921be74ae598bb06a9155` preserved those public bytes
   before the result bundle existed;
4. all 52 scheduled cells terminated validly and no scored call was retried;
5. the public decision was independently recomputed from the frozen normalized
   observations without changing the rule;
6. the negative decision and exact-policy rejection were retained.

Git ancestry proves repository artifact ordering. It does not independently
timestamp the private calls or turn maintainer-controlled execution and
evaluation into independent replication.

## What the result supports

- The exact prompt segment did not change false-completion or accepted-state
  rates on this frozen task population and stack.
- The frozen owner rule rejects this exact policy and routes neither declared
  mechanism.
- The public bundle can recompute the bounded decision from 52 normalized run
  records and 521 measurements.
- A prompt-only intervention should not be assumed to improve completion
  integrity merely because its instructions sound sensible.

## What the result does not support

- that completion prompts never work;
- that the policy transfers to another task population, model, CLI, repository,
  provider state, or organization;
- that tools, workflow gates, structured plans, or final-state checkers would
  also have no effect;
- a model-only capability claim, universal ranking, or production outcome;
- independent replication or stable cost conclusions.

## Public audit

```bash
uv run ael study audit \
  --freeze studies/completion-integrity/freeze.json \
  --result studies/completion-integrity/results/prompt-policy-v1 \
  --decision-adapter completion-integrity-prompt-policy-v1 \
  --require-git-proof
```

The audit validates the public Contract v0 graph, verifies exact freeze and
preregistration bindings, recomputes the terminal decision, and checks Git
artifact ordering. It does not reveal or rerun the private tasks, evaluators,
candidate workspaces, raw events, authentication, or hosted model calls.
