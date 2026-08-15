# Study Quality Preflight

`ael study preflight` checks whether a prospective study has declared and
hash-bound the minimum design evidence needed for an interpretable bounded
decision. It runs offline and deterministically before scored work.

It does **not** certify that a study is scientifically valid. A conformant
profile does not prove private-call chronology, task validity beyond the cited
audit, evaluator correctness beyond the cited calibration, independent
replication, transfer, or downstream outcome.

## Boundary

The Study Quality Profile is `ael.study-quality-profile/0.1-pilot`. It is not a
sixth Contract v0 object and is not registered in the generic Contract
validator. Contract v0 remains the five `0.1` schemas for Concept, Study
Manifest, Run Record, Measurement Set, and Evidence Receipt.

The profile references one exact Contract v0 Study Manifest by study ID,
revision, path, and SHA-256. It adds pre-run methodological evidence that the
manifest does not own:

- an operational construct, bounded target claim, claim ceiling, and
  falsifier;
- hash-bound task provenance and task-audit evidence;
- hash-bound evaluator calibration with known-pass and known-fail cases;
- a decision threshold, missing/invalid-cell rule, and uncertainty method or
  explicit `not_estimable` reason;
- task count, repeats, order policy, nuisance factors, and planned reliability
  coverage;
- an explicit zero-scored-call declaration, assessment date, and freshness
  window.

The profile reuses the manifest's estimand, aggregation, task-pack identity,
strata, selection/stop rules, roles, and independence claim. It does not create
a second authority for those fields.

Study Quality also does not own intervention-family process semantics. A
conformant design may declare an intended mechanism while still retaining no
evidence that the mechanism was enacted. The experimental
[Completion Integrity observable-enactment](completion-integrity-enactment.md)
slice therefore remains a separate family-local policy rather than a profile
v0.2 field or sixth Contract object.

The same boundary applies to prospective terminal-claim and task-supply
policies. Study Quality may bind their exact revisions, but it does not own
terminal truth semantics, blocker feasibility, evaluator custody, reporter
isolation, or a family-specific sample-size calculation.

## Run the checked example

```bash
uv run ael study preflight \
  studies/quality-preflight/examples/pass/quality-profile.json \
  --json-output studies/quality-preflight/examples/pass/preflight.json \
  --markdown-output studies/quality-preflight/examples/pass/preflight.md \
  --check
```

The example is synthetic and performs no model call. Its expected status is
`conformant_with_warnings` because the evaluator and decision roles remain
maintainer-owned. The warning is evidence disclosure, not a failing test and
not independent replication.

Without `--check`, the command atomically materializes the selected JSON and
Markdown outputs. With no output paths it performs the same preflight and
prints a concise status. Exit status is `0` for `conformant` or
`conformant_with_warnings`, and `1` for `blocked` or an unsafe input/output.
`--as-of YYYY-MM-DD` recomputes freshness from an explicit date; the command
never reads the system clock. Public result projection supplies its own
profile `as_of`, so revalidation remains deterministic and reviewable.

## Hard gates

The pilot fails closed when any of the following is true:

- JSON has duplicate members, non-finite values, unknown fields, missing
  fields, unsafe paths, symlinks, or mismatched hashes;
- the referenced Contract manifest is invalid or its study ID/revision/hash
  does not match;
- the manifest is already executing or completed, or the profile declares any
  scored call;
- construct operationalization, bounded target claim, claim ceiling, or
  falsifier is absent;
- an operational-stack comparison asks for factor-causal or model-only proof,
  or any pilot profile asks for transfer/outcome proof;
- task audit is absent or any instruction/test, oracle, alternative-solution,
  shortcut, or environment check is not `pass`;
- active confirmation tasks are disclosed or adaptively reused;
- evaluator calibration lacks a scoring rule, known-pass evidence,
  known-fail evidence, error boundary, or adjudication rule;
- the decision threshold, missing/invalid-cell policy, or uncertainty
  declaration is absent.

## Warnings, not universal bans

The following are retained as stable warnings because their acceptability
depends on the bounded decision:

- one repeat per cell;
- fixed or hash-keyed execution order with a declared rationale;
- uncertainty explicitly marked `not_estimable`;
- maintainer-only evaluation and decision ownership.

A narrow safety screen can rationally use one repeat and a critical-failure
gate. That design must not be presented as stability evidence or a universal
effect estimate. A future regulatory or confirmatory profile may promote some
warnings to hard gates under a separately named policy.

## Public quality facets

An assessed result card projects seven descriptive axes from the same preflight
implementation:

| Axis | Meaning |
| --- | --- |
| `design_class` | calibration, screening, controlled pilot, or real-shadow design derived from the manifest |
| `task_validity` | audited or independently audited task evidence declared before execution |
| `evaluator_validity` | calibrated or independently checked evaluator evidence |
| `sampling_strength` | current pilot's decision-thresholded sampling class, not a population guarantee |
| `reliability_coverage` | planned repeat/perturbation/fault coverage, not observed reliability |
| `independence` | maintainer-only, role-separated, or external-replication status derived from the manifest |
| `freshness` | current, revalidation due, or invalidated relative to an explicit CLI/publication `as_of` |

There is no composite score. A public-results entry uses exactly one mode:

```json
{"assessment": "not_assessed_historical"}
```

or:

```json
{
  "assessment": "profiled",
  "profile_ref": {"uri": "...", "sha256": "..."}
}
```

The four studies that predate alpha.7 use
`not_assessed_historical` on every quality axis. Current files are not used to
retroactively manufacture a pre-run assessment. A profiled result fails public
projection when the quality profile is blocked or its study ID, revision, or
manifest hash differs from the receipt.

## Prospective binding

Admission version `ael.study-admission/0.2-pilot` requires an exact
`quality_profile_ref`. A future freeze binds the complete admission bytes via
its existing `admission_ref`, producing this chain:

```text
quality profile hash → admission hash → freeze → scored work → receipt
```

The synthetic example demonstrates profile conformance only; it does not claim
Git or wall-clock proof that a model call occurred after preflight. Future
scored studies must retain the admission/freeze chain and audit repository
artifact ordering separately.

## Promotion rule

Do not stabilize the pilot shape after one example. Promotion requires at
least two prospective study families, a recurring field need, evidence that
the fields change real decisions, a compatibility plan, and an explicit schema
decision. See the [roadmap](../ROADMAP.md).
