# Schema versioning

Contract v0 is pre-stable. The package follows Semantic Versioning, but schema
compatibility is expressed by each document's `schema_version`, not inferred
from the Python package version.

## Alpha policy

- Patch alpha releases may fix validation defects without changing a valid
  document's intended meaning.
- A change that makes a previously valid document invalid, changes a required
  interpretation, or changes a cross-document invariant increments the schema
  version.
- New optional fields may remain within a schema version only when older tools
  can safely ignore them and no claim semantics change.
- The repository keeps schemas strict: unknown fields are rejected where the
  contract declares `additionalProperties: false`.

## Alpha.5 projection boundary

Alpha.5 is projection-first. The five Contract v0 document types and their
`0.1` schemas remain unchanged, as does the existing receipt renderer. The
generated machine index and Markdown result cards are disposable publication
projections over validated, hash-linked evidence; they are not a sixth evidence
document and do not become authority for a receipt. A publication profile may
select public claims, replication instructions, unavailable-material categories,
and explicit historical unknowns without rewriting an existing receipt.

Evidence level, reproducibility, independence, freshness, action, and outcome
are orthogonal metadata axes in a projection. Missing historical action or
outcome is rendered as `not_declared_historical` or `unassessed`, never inferred
from an empty field. A Git tag or ancestor can establish repository artifact
ordering only; it cannot establish private model-call chronology or independent
replication.

Alpha.5 introduces no stable Decision Case, admission, or Outcome Follow-up
schema. Those owner-scoped lifecycles are deferred to a prospective pilot in
the next decision-governing study. The pilot must hash-bind admission before
scored work and complete one decision/action/outcome lifecycle before a schema
is stabilized.

## Alpha.6 prospective lifecycle boundary

Alpha.6 completes that first pilot without adding a sixth stable Contract v0
document. Experimental `study-admission`, `study-freeze/0.2-dev`, effect,
adoption, action, follow-up, routing-policy, and projection-deviation records
remain pilot-local. The public-results profile moves to
`ael.public-results/0.2` and the projection policy to
`ael.publication-projection/0.2` because cards may now derive admission, action,
follow-up, and freshness from exact public lifecycle refs rather than accepting
profile-authored status text.

Contract v0's five `0.1` schemas remain unchanged. The completed lifecycle is
evidence for designing a future generic owner-decision contract, not permission
to stabilize the pilot shapes without comparison across more than one study.
The disclosed materialization repair is similarly pilot-specific: it preserves
the frozen analysis and records a post-run projection defect instead of
silently changing preregistered code.

## Migration requirement

The first incompatible schema change must include:

1. the old and new schemas;
2. an explicit migration command or documented mechanical transformation;
3. fixtures before and after migration;
4. tests proving preserved identity and deliberate semantic changes;
5. a changelog entry and a decision record;
6. a deprecation window if a released CLI still accepts the old version.

Published receipts are immutable historical evidence. Migrate a copy and keep
the original revision and hash; do not silently rewrite a released receipt.
