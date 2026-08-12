# Alpha.5 external-review integration (sanitized)

Date: 2026-08-12
Status: accepted for the alpha.5 implementation boundary
Decision owner: project owner
Evidence relationship: two owner-supplied private external reviews; model and
product critiques, not independent experimental verification

## Source and privacy boundary

Two private external reviews were supplied to the owner and considered for the
alpha.5 direction. The raw captures, prompts, private context, and reviewer
identifiers remain outside this repository. The following SHA-256 values are
included only as provenance because they are already recorded in the
owner-canonical project record and are safe, non-revealing identifiers:

- current-state review: `ff93ba7a79da1135b1b640b69e80cf56e8fabe53de65dbfc0142c174288dc956`;
- release-gate and outcome-loop review: `13b4d65ca5213080c78feb69bd252066049d0646e90ab243a3251b82786aa5da`.

The first review inspected public artifacts, evidence links, and CI, but did
not rerun the original model calls or inspect private task packs, raw Codex
events, or evaluator outputs. The second review is a product and business
argument; it is not customer discovery, market validation, or experimental
evidence. Neither review changes repository authority or makes private source
content public.

## Accepted recommendations

1. Use a projection-first alpha.5 surface: keep Contract v0's five closed
   evidence objects, the existing receipt renderer, and frozen historical
   artifacts unchanged. Generate `RESULTS.md`, `docs/results/index.json`, and
   per-card Markdown from the validated evidence graph.
2. Make each public card a deterministic, disposable projection rather than a
   second evidence authority. Enforce a claim ceiling and show evidence level,
   reproducibility, independence, freshness, action, and outcome as separate
   facets.
3. Publish an exact replication handoff: say whether a command verifies the
   graph, reruns a study, or supports independent replication; list withheld
   material and preserve `not_declared_historical` or `unassessed` when history
   was not recorded.
4. Retain the completed bounded negative Property-based Testing v2 result and
   correct navigation that previously described Season 1 as having no
   skill-effect result.

## Deferred or rejected claims

- No stable Decision Case, admission, or Outcome Follow-up schema is introduced
  in alpha.5. Exercise those owner-scoped lifecycles prospectively in the next
  decision-governing study, with admission hash-bound before scored work, then
  stabilize fields only after one complete decision/action/outcome lifecycle.
- The reviews do not establish product demand, commercial willingness to pay,
  production impact, transfer, or independent replication. Buyer, pricing,
  paid-partner, cadence, and commercial-pivot proposals remain unvalidated
  hypotheses.
- A Git tag or ancestor proves repository artifact ordering only. It does not
  prove that private model calls occurred before results, reconstruct private
  events, or establish independent verification.
- A global leaderboard, database, hosted service, marketplace, and general
  runner remain outside this release boundary.

## Owner decision

Adopt the four recommendations above as the alpha.5 static-publication and
replication-handoff boundary. Keep the existing Contract v0 receipts as the
canonical evidence; generated cards and the machine index may narrow or expose
claims but may not upgrade them. Historical action, outcome, and freshness
remain unknown unless explicitly recorded.

## Verification and reversal

Before release, verify that generated cards agree with the hash-linked evidence
graph, no card claims beyond its receipt, no stale Season 1 status remains, and
the existing validation, audit, clean-wheel, and isolation checks still pass.
The reproducibility commands and their graph/rerun/replication boundaries are
documented in [Reproducibility](../reproducibility.md).

Stop and reverse the alpha.5 projection change if a generated view exceeds its
receipt's evidence, a frozen historical artifact changes, private material is
exposed, or the prospective admission/outcome pilot cannot support its declared
fields. Revert or regenerate only the disposable projection and supersede this
record with a new owner decision; do not rewrite an immutable receipt.

This sanitized record is a provenance and decision summary. It intentionally
does not reproduce either private review.
