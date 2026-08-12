# Structural Search research program

State: future gated program; no search implementation or result exists.

## Research question

Can a bounded search process discover agent-system configurations that improve
real engineering outcomes beyond strong human-designed and simple-search
baselines, at a matched total exploration budget, without changing the task or
evaluator to make itself look better?

## Layer boundary

```text
Concept and owner constraints
        ↓
Structural Search proposes candidate interventions
        ↓
Evidence Core evaluates frozen candidates against protected reality
        ↓
Capability Studio adopts, rejects, narrows, or releases
```

Structural Search is a candidate generator. It is not the judge, the task-pack
owner, or the release authority. Evidence Core remains useful when the search
layer is absent, replaced, or rejected.

## Candidate configuration

A study may expose a declared subset of this configuration to search:

```text
prompt + skill + model + tools + context policy + permissions
       + roster + topology + routing + stop policy + run budget
```

Everything outside the declared subset is frozen surrounding configuration.
Changing the mechanism hypothesis itself creates a new Concept revision rather
than a silent mutation.

## Future Search Contract

The first design should record at least:

- `search_id`, purpose, owner, revision, and state;
- content-addressed Concept and base Study Manifest;
- mutable factors, permitted primitives, constraints, and mutation grammar;
- protected invariants and forbidden edits;
- candidate identity, parent identity, generation, and exact mutation;
- proposal policy and version: human, random, beam, evolutionary, MAP-Elites,
  MCTS, or another declared method;
- shared exploration budget and accounting unit;
- adaptation task access, leakage controls, and candidate freeze rule;
- pruning, stopping, retry, and invalid-candidate rules;
- measurements used for search versus untouched confirmation;
- archive membership, Pareto dominance, exclusion reason, and failed-branch
  retention;
- evaluator identity, independence, disagreement, goal-paraphrase sensitivity,
  and known proxy risks;
- handoff to a frozen ordinary AEL study and final owner adoption decision.

This is a design backlog, not a compatibility promise. It must not be added to
the five-object Contract v0 until completed studies show that the lifecycle is
real and cannot be represented cleanly as ordinary provenance.

## Protected reality

Before candidate generation starts, the study owner freezes three different
surfaces:

| Surface | Examples | Search authority |
| --- | --- | --- |
| Task reality | repository revision, fixtures, hidden tests, acceptance criteria, task strata | none |
| Intervention grammar | allowed workflow nodes, routing choices, model pool, context operations | mutate only within declared bounds |
| Evaluation | deterministic checks, critical failures, cost/rework accounting, independent review | none |

The generator cannot delete failing tasks, weaken critical thresholds, expand
its budget, choose a weaker baseline after seeing results, or train directly on
untouched confirmation evidence.

## Program sequence

### S0 — search-contract threat model

Model benchmark leakage, evaluator gaming, budget laundering, lineage loss,
invalid-candidate retries, and multiple-comparison risk. Exit only when every
mutable field and protected owner is explicit.

### S1 — Workflow Graph Search

Use a small coding-task pack with deterministic tests. Permit a bounded graph
over operations such as inspect, plan, implement, test, critique, and revise.
Compare under equal exploration budgets:

- frozen human-designed workflow;
- random search;
- one simple evolutionary or quality-diversity method;
- one LLM mutation policy;
- MCTS or beam only if they add a distinct falsifiable hypothesis.

Measure task correctness, critical failures, generated work, cost, latency,
stability, correction count, and implementation rework. Freeze selected
candidates before untouched confirmation.

### S2 — Context Policy Search

Compare direct repository search, repository maps, semantic retrieval, hybrid
routing, and progressive disclosure. The primary chain is downstream:

```text
correct files discovered -> placed in context -> used in the change
                         -> correct effect -> bounded rework
```

Retrieval relevance alone is not an adoption outcome.

### S3 — Council Structural Search

Search roster, topology, routing, context visibility, and stopping only after
Council Generation 2 and at least one deterministic workflow study. Require
real implementation follow-through, defects, regressions, correction count,
rework, and owner outcome so prose appeal cannot dominate selection.

## Entry gates

Do not start S1 until:

1. Contract v0 survives completed prompt-only and ordinary-skill studies;
2. Council Generation 2 produces a calibrated bounded receipt or an explicit
   stopped/inconclusive decision;
3. one licensed third-party artifact completes the review and receipt loop;
4. at least one task pack has strong deterministic postconditions and protected
   confirmation tasks;
5. the owner accepts an exploration budget and false-selection tolerance;
6. all search policies emit reconstructable candidate lineage.

## Success and stop conditions

Continue only if search changes an adoption decision and the selected candidate
retains its effect on untouched tasks without hidden budget or evaluator drift.

Narrow or stop when the result disappears under goal paraphrase or evaluator
replacement, simple random/human search matches it, invalid candidates consume
the apparent gain, archive cost exceeds decision value, or downstream outcomes
do not improve.

The first valid result may be negative: a bounded finding that automated search
does not beat simple baselines is useful evidence and must remain publishable.

