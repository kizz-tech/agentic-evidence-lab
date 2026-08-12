# Decision: Structural Search is a gated future AEL layer

Date: 2026-08-12  
Status: accepted as roadmap; not implemented or validated  
Decision owner: project owner  
Evidence relationship: owner-supplied research synthesis and dated primary-source research package; no independent AEL outcome evidence

## Source boundary

The direction was informed by an owner-supplied result from a parallel research
agent and the dated private LIFEOS CEDAR research package behind it. The
transport copy of that synthesis is intentionally not retained in this
repository; this decision owns only the resulting project delta.

The relevant external lead is [CEDAR v1](https://arxiv.org/abs/2608.06871), a
fresh preprint about LLM-guided structural search over executable dynamic-system
programs. AEL does not treat that work as proof that the same search pattern
improves agent configurations, that MCTS is the best policy, or that an
optimized evaluator score represents a real engineering outcome.

## Existing foundation versus new delta

AEL already owns concept lineage, declared factors, frozen interventions,
matched task packs, budget rules, adaptation/holdout separation, evaluator
identity, Pareto reporting, failed-run preservation, and bounded receipts.
Those rules do not need to be rediscovered or duplicated.

The genuinely new research object is a reconstructable process that generates
many candidate interventions before Evidence Core evaluates a frozen survivor.
That process needs search-space and mutation identity, parent lineage, protected
invariants, exploration budget, pruning and stopping rules, archive decisions,
and evaluator-sensitivity checks.

## Decision

1. Add **Structural Search** as a future research layer, not as part of the
   current Contract v0 kernel.
2. Keep Evidence Core outside the candidate-generation loop. A generator may
   mutate only declared intervention fields; it may not rewrite tasks, hidden
   tests, acceptance semantics, baseline identity, evaluator rules, or the
   comparison budget.
3. Treat the full agent configuration as the candidate: prompt, skill, model,
   tools, context policy, roster, topology, routing, permissions, and budget,
   with only the frozen grammar's subset mutable in a given study.
4. Preserve a Pareto archive and attributable failed branches. Do not collapse
   quality, critical failures, cost, latency, stability, and rework into one
   universal search score.
5. Compare search policies at equal exploration budgets. Human design, random
   search, beam or evolutionary methods, MAP-Elites, and MCTS are candidate
   policies; none is the architectural default.
6. Make a bounded **Workflow Graph Search** the first candidate study after the
   current evidence-transfer gates. Context Policy Search follows if the first
   study is decision-useful. Council Structural Search remains later and must
   include downstream implementation and rework outcomes.
7. Retain the current sequence: validate frozen interventions first, then earn
   the right to automate candidate discovery.

The executable boundary and proposed gates are specified in
[Structural Search research program](../structural-search.md).

## What this decision does not claim

- Contract v0 has not changed and no sixth schema is introduced.
- No structural-search implementation or experiment has run.
- CEDAR has not been reproduced by this project.
- MCTS superiority, automatic recursive improvement, and a product moat are
  not established.
- A generated candidate cannot become a released capability without an owner
  adoption decision and a bounded evidence receipt.

## Validation and reversal

This decision is applied when the roadmap, repository overview, and review
register consistently preserve the boundary above and local documentation tests
pass.

Revisit or reject the direction if frozen-intervention receipts fail to change
real decisions, if deterministic outcome coverage is too weak, if search mostly
finds evaluator exploits, if simple human/random baselines match the result, or
if the cost of reconstructable search exceeds its decision value.
