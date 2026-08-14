# Public mission leads; evidence rigor remains underneath

- Date: 2026-08-14
- Status: accepted for the alpha development line
- Scope: public positioning, result outputs, and research roadmap

## Decision

AEL's public thesis is:

> Better agent systems need more than bigger models.

Its mission is to test versioned changes to complete agent systems and publish
bounded evidence about what improves task outcomes, what makes them worse, and
what remains inconclusive under declared conditions.

The present-tense alpha product remains narrower: a Git-first protocol and CLI
for freezing an exact comparison, validating its evidence, and producing an
auditable adopt, reject, narrow, or retest decision. The mission describes the
direction; it does not promote the current evidence corpus into general proof
that AEL improves agent capability or reliability.

## Public output contract

The primary public product of a study is the answer, not the schema:

```text
decision → exact change → task scope → observed outcomes and cost
         → revalidation trigger → result card and receipt
```

Every mature study should try to produce one recognizable question, one clear
decision, one exact tested artifact or reference configuration when
publishable, and one audit or replication path. Reliability is described only
when observed; otherwise the result states that it was not established.

Detailed caveats remain mandatory in the result card, receipt,
reproducibility documentation, and raw study records. They do not lead the
landing-page narrative. This is progressive disclosure, not relaxed evidence
standards.

## Causal language

- Skills and prompts change behavior.
- Tools expand the available action space.
- Context and retrieval policies change available information.
- Orchestration may spend additional computation and coordination.
- Evidence gates decide whether a versioned change should survive.

These mechanisms can improve the complete system without making the base model
intrinsically smarter. A model-only claim requires a design that holds the
surrounding stack fixed. A system-level result must report the full stack and
budget.

Use `tested artifact` by default. Use `evidence-backed improvement` only when a
receipt supports an improvement claim in the named scope. AEL records reversal
or revalidation conditions; it does not claim to execute rollback.

## Roadmap consequence

The default research cycle combines:

1. one important agent-system decision;
2. one reusable answer or tested artifact;
3. one improvement to trust, transfer, or downstream follow-up.

Method-only releases are exceptions for instrument defects that block the next
important answer.

The next flagship public question is **Completion Integrity**: can a coding agent
reliably tell when requested work is actually complete? It is not yet an
admitted scored study. The existing Season 1 Truthful Completion protocol tests
a pinned skill and reached a baseline ceiling during sacrificial calibration.
Any prompt-only successor therefore needs a distinct study identity, a frozen
exact intervention, and an unscored task-discrimination gate before model
calls.

## Release-state corrections

The alpha.7 candidate resolves the two repository-owned blockers exposed by
this review:

- Systematic Debugging is deliberately listed in the public result catalog;
- [result-catalog and reproduction semantics](2026-08-14-result-catalog-and-reproduction-semantics.md)
  separate public graph verification, maintainer rerun capability, and linked
  independent replication instead of promoting the ambiguous Contract v0
  label `rerunnable`.

Release state remains externally owned. Alpha.6 stays an unreleased development
line unless it is separately tagged and published; alpha.7 may supersede it
without inventing a historical release. A release date and published status
may be recorded only after the tag and release actions succeed. These are state
and vocabulary corrections; they do not change frozen study decisions.

## Rejected alternatives

- Leading with schemas, hashes, and reproducibility terminology while the user
  value remains implicit.
- Marketing AEL as a universal agent optimizer, certification authority, or
  model leaderboard before transfer and independent replication exist.
- Exposing the full internal portfolio, domain model, or future platform
  architecture as the public onboarding model.
- Treating the new Completion Integrity question as continuation evidence for
  the existing Truthful Completion skill protocol.

## Reversal and review triggers

Revisit this decision if readers cannot identify AEL's decision job in a
thirty-second comprehension check, receipts do not govern real actions, public
result cards do not improve decisions over a simple score, or the method cost
exceeds the value of the decisions it informs.
