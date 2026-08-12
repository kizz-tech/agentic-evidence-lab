# Contextual leaderboard contract

An AEL leaderboard is a view over eligible evidence receipts. It is not an
independent source of truth and never combines incomparable studies into one
score.

## Two board families

### Operational stack board

Ranks complete user-runnable configurations under the same task pack and
budget. It answers a practical selection question such as:

> Which available stack should I use for migration-backed repository changes
> with this time and token budget?

The result applies to the whole stack. It cannot be reported as model-only
superiority when prompts, tools, skills, runtimes, permissions, or workflows
differ.

### Controlled factor board

Compares conditions that hold the surrounding stack fixed and vary one declared
factor or interaction. It investigates a causal mechanism such as whether one
skill changes validation selection. Eligibility requires the claimed controls
to be evidenced, not merely named.

## Eligibility

A candidate may appear only when its receipt:

- resolves to immutable concept, study, run, measurement, and artifact hashes;
- uses the board's frozen task pack, strata, evaluator, budget rule, and stop
  rule;
- satisfies the declared minimum run count and operational-validity policy;
- discloses model/runtime freshness and all exposed configuration differences;
- reports critical failures and invalid runs without selective removal;
- has no unresolved integrity, publication-rights, or credential incident;
- uses an evidence and independence label supported by its recorded roles.

## Required columns

Every board shows at least:

- candidate and exact stack revision;
- primary outcome with uncertainty;
- task and repeat counts;
- critical failures and operational-invalid rate;
- generated work, wall time, and available cost measures;
- evidence level and independence label;
- last eligible run date and invalidation state;
- link to the source receipt.

No overall rank may hide a critical failure. When candidates trade quality,
cost, latency, or safety, AEL shows a Pareto frontier or separate columns instead
of inventing undisclosed weights.

Evidence level, reproducibility, independence, freshness, action, and outcome
are orthogonal facets. A board or result card must show them separately; one
facet never upgrades another. Missing historical action or outcome is rendered
as `not_declared_historical`, not as a claim that no action or outcome occurred.

## Update and correction policy

Boards are generated from immutable receipts. New evidence creates a new board
revision; it does not rewrite old receipts. A candidate becomes stale or
ineligible when an explicit invalidation trigger fires. Corrections retain the
superseded view and explain the change. The generated [Results
Index](../RESULTS.md) and [machine study index](results/index.json) expose
derived current cards and counts; they are projections for navigation, not
additional evidence authority.

## First-board gate

The first public board is blocked until one study has at least two eligible
candidates on the same frozen contract, repeated observations sufficient for
the preregistered uncertainty method, and a completed factual-correction pass.
Until that condition exists, the alpha publishes separate contextual result
cards in the [Results Index](../RESULTS.md) instead. Run totals are derived
from the referenced evidence graph and must not be hard-coded into this policy.
