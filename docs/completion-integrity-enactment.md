# Observable enactment for Completion Integrity

The Completion Integrity alpha.10 method release separates a terminal task effect
from a narrower question: whether a declared process chain is represented by
the normalized evidence supplied to a classifier. It is experimental,
family-owned instrumentation—not Contract v1, generic telemetry, or a claim
about an agent's internal reasoning.

## Why this exists

Alpha.9 found the same `0.375` false-completion rate in baseline and treatment.
That supports rejection of the exact appended prompt policy. The retained
evidence cannot distinguish a redundant instruction from absent enactment or
an enacted but ineffective process. Tokens, elapsed time, command count, and
longer prose cannot resolve that ambiguity.

Alpha.10 does not rewrite that result. It defines the smallest candidate
instrument needed for a future study to ask a different question.

## Four non-compensating facets

| Facet | Candidate rule |
| --- | --- |
| `policy_bytes_bound` | The pure policy hashes immutable bytes read by the adapter; that digest and the reported digest both match the method plan. |
| `ledger_materialized` | Every opaque requirement ID appears exactly once and the canonical ledger digest matches. |
| `checks_evidenced` | Each satisfied requirement references a successful `verify` after the final change; each blocker references a failed pre-terminal `verify`. |
| `terminal_reconciled` | A `reconcile` event follows the final change and every cited event, and the terminal state agrees with satisfied, unmet, and blocked entries. |

No scalar score combines the facets. All four `satisfied` values produce
`observable_chain_complete`; otherwise a valid cell is
`observable_chain_incomplete`. Missing historical instrumentation is
`not_assessable`. Structurally unsafe or hash-inconsistent input is `invalid`.

The classifier permits repair loops such as:

```text
inspect → change → verify → change → verify → reconcile → declare
```

It does not impose a fictional monotonic workflow. A stage vector records only
whether a normalized event label was present.

## Evidence ceiling

The policy file, method plan, observations, and golden bundle are byte-bound.
The ledger digest is recomputed. Normalized event labels and event digests are
still caller-provided synthetic declarations; no current owner adapter proves
that a real harness captured them. Therefore fixture success establishes
deterministic classifier behavior only—not real enactment, cognition, causal
mediation, outcome correctness, or intervention benefit.

Alpha.9 is explicitly `not_assessable` for this new predicate because it did
not retain the structured ledger and requirement-to-event bindings. It is
incorrect to reinterpret the null as evidence that the agent ignored the
policy.

## Run the deterministic candidate

```bash
uv run python tools/check_completion_integrity_engagement.py \
  --method-plan studies/completion-integrity/diagnostics/process-v1/method-plan.pilot.json \
  --observations studies/completion-integrity/diagnostics/process-v1/fixtures/normalized-cells.json \
  --diagnostics-json studies/completion-integrity/diagnostics/process-v1/fixtures/expected-diagnostics.json \
  --check
```

The fixtures cover a repair loop, a supported blocker, a false blocked
declaration, zero process events, and unavailable historical evidence. The
adapter accepts strict JSON, rejects duplicate members and non-finite numbers,
rejects unsafe policy paths and symlinks, reads the policy bytes, and passes
those immutable bytes to the pure policy for hashing. Two matching caller-
provided digest strings cannot masquerade as byte verification.

## Task expansion remains prospective

Increasing task count is useful when it adds independent failure coverage and
the role of every task is frozen before outcomes are inspected. Exact counts
must come from a pack-specific power or precision rationale; `16–24` is only an
authoring-capacity range while pilot inputs are absent. A future study should
separate:

1. instrument development;
2. sacrificial qualification;
3. fresh screening;
4. untouched confirmation.

Development and qualification must not enter the effect estimate. Variants
must not inflate the independent count, and post-effect additions must not be
silently pooled into the original confirmatory estimand. Alpha.10 intentionally
does not fabricate task rows or encode a universal sample size before real task
packs exist.

## Architecture and release boundary

`ael.completion_integrity_engagement` is pure family policy. The file adapter
owns strict I/O and byte acquisition; the policy hashes those bytes. Contract
v0, Study Quality, the alpha.9
runner, freeze, audit, observations, and published result bytes are unchanged.

Terminal-claim correctness is owned by the separate
[terminal-claim policy](completion-integrity-terminal-claims.md); observable
enactment cannot establish truth, and truth cannot establish enactment.

Alpha.10 publishes this instrument as a pre-stable method component. Empirical
admission still requires real capture by an owner adapter plus either a
downstream outcome closure, a genuinely role-separated reproduction, or a
separately authorized prospective study. No scored model call was part of this
instrument release.
