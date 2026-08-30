# Completion Integrity activation

Completion Integrity activation is the owner adapter between a real Codex task
trajectory and the pure terminal-claim policy. It is deliberately smaller than
a benchmark: its job is to prove that capture, evaluation, sealing, reporting,
and assessment compose correctly before a larger task population is spent.

## The boundary under test

```text
Codex executor → owner event capture → offline evaluator → sealed evidence
                                                       ↓
                         isolated reporter → closed claim → owner assessment
```

The executor can edit an ephemeral candidate. The deterministic evaluator runs
afterward and remains hidden from the executor. A reporter receives only a
sealed read-only evidence packet: no task artifact, evaluator, candidate
workspace, intervention bytes, or repair capability. The owner then wraps the
reporter JSON with immutable trajectory identifiers and compares it with frozen
truth.

An activation call is valid only when every boundary holds. Correct-looking
content cannot compensate for a malformed wrapper, changed evidence, forbidden
mount, ambiguous submission, or broken custody record.

## What alpha.11 learned

Two prospective revisions failed at different composition layers:

- v1 stopped before model generation because the provider rejected the frozen
  response-schema keyword `uniqueItems`;
- v2 passed exact schema and isolation qualification, then stopped after two of
  six cells because an owner-generated hexadecimal `attempt_id` violated the
  terminal-claim identifier grammar.

In v2 the first reporter's private content matched all frozen requirement
states, verdict, progress, and evidence references. It still remains invalid
under the frozen protocol. This distinction is the point of activation: a
schema-valid model answer is not yet an end-to-end-valid experimental record.

Read the [v2 report](../reports/2026-08-15-completion-integrity-activation-v2.md)
and [alpha.11 decision](decisions/2026-08-15-alpha11-activation-result.md) for
the exact outcome and repair boundary.

## What activation v3 learned

V3 was a new prospective revision, not an alpha.11 retry. It froze:

- two fresh sacrificial Python/TypeScript repository graphs;
- a corrected version-bound deterministic qualification receipt;
- a six-cell no-call full-wrapper qualification;
- a prospective `conformant_with_warnings` Study Quality Profile;
- a passing offline reporter-boundary probe;
- a green exact-SHA preregistration gate.

The first fresh qualification output was retained as invalid because its owner
tool still emitted an `activation-v1` receipt identity. Version-derived
qualification, schedule, truth, and submission identity is now covered by
regression tests, and the complete deterministic matrix was rerun successfully.

The first scored executor was submitted once. Codex and the evaluator exited
successfully, but the owner adapter then failed to parse the private `TASK.md`:
the task used a typographic dash where the live requirement parser required
`: `. The attempt therefore remains ambiguous, zero cells are terminal, and
the five later cells remain unrun. V3 is closed
`protocol_invalid / revise_activation_adapter`; it did not measure reporter or
model quality.

Read the [v3 report](../reports/2026-08-30-completion-integrity-activation-v3.md)
and [owner decision](decisions/2026-08-30-completion-integrity-activation-v3-result.md).
The larger 16-root effect study remains blocked by adapter activation, task
supply, and `pending_pilot` sample size.

## Current source versus frozen evidence

Current source constructs namespaced attempt identifiers, checks the exact
executor-facing task grammar during semantic qualification, preserves an
ambiguous submitted attempt in normalized observations, and can finalize an
interrupted journal without a model call or retry. These repairs do not alter
the v1/v2/v3 freezes or reinterpret their results.

No v2 or v3 cell may be retried. A new observation requires a new revision,
new uncontaminated roots, new raw root, new preregistration, and new prospective
quality profile.

## Public verification

```bash
uv run ael study audit \
  --freeze studies/completion-integrity/activation-v3/freeze.json \
  --result studies/completion-integrity/activation-v3/results \
  --decision-adapter completion-integrity-activation-v1 \
  --require-git-proof
```

This recomputes the bounded public decision and validates artifact ordering. It
does not replay private Codex calls or constitute independent replication.
