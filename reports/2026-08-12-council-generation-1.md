# Council Generation 1: a process repair, not a general quality win

Status: published maintainer-evaluated evidence. Not independently reproduced.

## Answer first

On three synthetic held-out engineering cases, the frozen adaptive Council
candidate did **not** demonstrate a general answer-quality advantage over a
strong direct answer, fixed sequential revision, or the historical skill. It
did repair a reproducible profile-execution defect, preserve measured quality,
route the routine case directly, and use less generated work than the historical
skill on the two consequential cases.

That evidence justified a local workflow replacement. It did not justify a
claim that multi-agent councils are universally better.

| Decision question | Answer |
| --- | --- |
| Did the adaptive candidate produce better answers? | No demonstrated general advantage; the three structured workflows remained inside the frozen tie threshold. |
| Did it improve the execution process? | Yes, on the measured surface: it repaired a reproduced profile-execution defect and routed routine work directly. |
| Should it replace the historical local workflow? | Yes, narrowly, with the exact measured semantics and stated limitations. |
| Is this independently verified or production-proven? | No. It is maintainer-evaluated synthetic evidence with one run per case and condition. |

## Should I use Council?

Use the published Council alpha as an experimental successor when the measured
engineering-decision workflow matches your need and you can validate it in your
own environment. Do not use this study as proof that councils outperform direct
or sequential approaches across tasks, models, runtimes, or domains.

The evidence supports the mechanism used by the successor, not the complete
later release bundle. See [Published capability lineage](#published-capability-lineage)
for the exact revision boundary.

## What was compared

| Condition | Process |
| --- | --- |
| `C0` | One direct parent answer |
| `C1` | Fixed draft → critique → revision sequence |
| `C2` | Historical skill-routed Engineering Council |
| `C3` | Frozen adaptive candidate with independent first passes and accountable synthesis |

All conditions used the same held-out case facts, answer contract, model family,
and read-only target. The experiment retained three separate task strata:
routine/local, consequential domain-policy, and consequential performance.

## Held-out result

| Condition | Mean blinded score | Critical-anchor misses |
| --- | ---: | ---: |
| Direct `C0` | 3.83 / 4 | 0 |
| Sequential `C1` | 3.93 / 4 | 0 |
| Historical skill `C2` | 3.93 / 4 | 0 |
| Candidate `C3` | 3.93 / 4 | 0 |

The frozen tie threshold was 0.25. Every candidate difference remained inside
that threshold. With one sample per condition and a correlated model judge,
this is evidence of preserved measured quality—not equivalence and not
superiority.

## What materially changed

The historical skill reproduced a full-history named-profile execution failure
on a consequential held-out case. The candidate changed the orchestration
contract:

- routine work stays direct;
- one material axis may use one advisor;
- consequential competing axes receive independent, context-bounded first
  passes;
- one accountable integrator resolves evidence and preserves dissent;
- at most one targeted challenge is allowed;
- profile/result identity and degraded execution must be disclosed;
- poor answers remain data and are not retried as operational failures.

The candidate did not reproduce the historical fork error. Attribution still
was not complete: one final omitted the exact profile identities and finding
IDs, and the retained CLI event stream did not authenticate receiver IDs.

## Generated work

On the two consequential held-out cases:

| Condition | Output + reasoning tokens |
| --- | ---: |
| Historical skill `C2` | 12,560 |
| Candidate `C3` | 9,598 |

The observed reduction was about 23.6%. The candidate exposed a larger total
input surface, so this must not be restated as a universal compute, latency, or
monetary-cost reduction.

## Decision and limits

Adopt the exact frozen adaptive semantics for the measured local Engineering
Council surface, while retaining these boundaries:

- maintainer-evaluated, not independently verified;
- one run per case and condition;
- synthetic cases, not production outcomes;
- same-model-family contestant and judge;
- no downstream implementation or rework measurement;
- no cross-model, cross-runtime, or cross-domain transfer claim.

The result must be reconsidered when the artifact, model, runtime, task pack,
evaluator, or intended use moves outside this measured boundary.

## Published capability lineage

Council is published as a separately versioned capability product:

- [repository](https://github.com/kizz-tech/council);
- [v0.2.0-alpha.1](https://github.com/kizz-tech/council/releases/tag/v0.2.0-alpha.1);
- release commit: `f13a06163d448a317e264a9b987a3271c5423d26`;
- current engineering-skill SHA-256:
  `fe4b1a7c7cb272c92b94fb2239cb904dfb0a3d272027d317f918c13451a2719f`.

Generation 1 evaluated the earlier frozen candidate SHA-256
`a22a1371711509778985bdbae999929903419355332645e299bdb38ce01432fe`.
The released product preserves the adopted mechanism and contains the
historical provenance bindings, but its complete bundle was assembled later.
The release is therefore a product-lineage target, not a retrospective claim
that the study executed `v0.2.0-alpha.1`.

## Machine-readable evidence

- [Study manifest](../examples/council-generation-1/study-manifest.json)
- [Individual run records](../examples/council-generation-1/runs)
- [Measurement set](../examples/council-generation-1/measurement-set.json)
- [Evidence receipt](../examples/council-generation-1/evidence-receipt.json)
- [Rendered receipt](../examples/council-generation-1/evidence-receipt.md)

The receipt SHA-256 is
`e9cd62971120d5993bc513837ea37c4e100b273aa12cb1161532777c46b8ade6`.
The private 114-file source package is bound by composite SHA-256
`dd1716d04484c62b0348f8b329d2967da840582462c662c53650d0c4e3656656`.
Raw reasoning traces, evaluator-only anchors, and final model answers are not
copied into this repository.

## Reproduce the public checks

```bash
uv sync
uv run ael validate examples/council-generation-1
uv run ael render \
  examples/council-generation-1/evidence-receipt.json \
  --output /tmp/council-generation-1-receipt.md
uv run python -m unittest discover -s tests -v
```

These commands reproduce contract and content-integrity checks. Re-running the
original model experiment additionally requires authorized access to the frozen
private task package and a compatible model/runtime surface.

## Next falsification

Council Generation 2 will compare one frozen roster finalist with a strong
sequential baseline that receives the same factual knowledge union. Screening,
holdout size, effect thresholds, budgets, and implementation gates will remain
unfrozen until their decision error is calibrated from actual task and pilot
evidence.
