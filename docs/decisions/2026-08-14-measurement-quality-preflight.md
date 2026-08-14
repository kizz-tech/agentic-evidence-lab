# Measurement-quality preflight remains a pilot sidecar

- Date: 2026-08-14
- Status: accepted for `v0.1.0-alpha.7`
- Scope: prospective design-quality evidence and public projection

## Decision

Add one self-contained pilot module for a hash-bound Study Quality Profile and
deterministic preflight. Keep all five Contract v0 schemas unchanged. The CLI
and public result projection consume the same module; neither reimplements its
rules.

Historical studies receive an explicit `not_assessed_historical` quality
variant. Future assessed studies reference one exact profile whose study ID,
revision, and manifest hash must match the receipt. Quality facets never raise
receipt evidence, claim level, publication state, independence, or outcome.

## Council consultation ledger

Two independent read-only advisor profiles reviewed the same evidence brief:

- `clean_boundary_architect` argued for a deep sidecar module, explicit
  historical/profiled variants, seven non-compensating facets, and a future
  pre-run admission binding.
- `evolutionary_deep_pragmatist` argued for the smallest vertical slice,
  reuse of Contract-owned fields, hard gates only for interpretability, and
  warnings for repeats, order, uncertainty, and role overlap.

The consultation records used stable finding IDs
`AEL-A7-BOUNDARY-01` through `AEL-A7-BOUNDARY-05` and `A7-SIMPLE-01`
through `A7-SIMPLE-05`. The parent integrator checked those recommendations
against the live repository before accepting this decision.

Both rejected a sixth Contract v0 schema, retrospective certification, a
quality score, duplicated manifest fields, and universal repeat/randomization
requirements.

## Integrated resolution and dissent

The implementation keeps seven public axes because they are useful disclosure,
but it does not turn them into seven independent authorities. Construct, task,
evaluator, analysis, and execution evidence live in the prospective profile.
Independence is derived from the Contract manifest. Freshness is relative to an
explicit CLI or publication `as_of`, not the system clock. Reliability coverage describes
the declared plan and is not presented as observed stability.

The pragmatist's narrower five-facet projection remains a credible future
simplification if real consumers find the seven-axis view noisy. The boundary
advisor's stronger recommendation to require hash-bound provenance for every
facet is adopted where local evidence exists; descriptive axes derived from
the manifest retain that manifest as their owner instead of duplicating refs.

## Consequences

- `ael.study-quality-profile/0.1-pilot` and its output are pre-stable.
- A preflight pass means design-conformant declaration, not scientific
  validity.
- Admission `0.2-pilot` can bind the profile before scored work while legacy
  admission `0.1-pilot` remains valid unchanged.
- Public-results/projection move to `0.3`; underlying receipts, manifests,
  runs, measurements, freezes, and reports are not rewritten.
- Stabilization waits for repeated prospective use and an explicit migration
  decision.
