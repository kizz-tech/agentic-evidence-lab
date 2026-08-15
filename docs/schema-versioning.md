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

## Alpha.7 measurement-quality boundary

Alpha.7 adds `ael.study-quality-profile/0.1-pilot` and a deterministic
preflight without registering a sixth Contract v0 type. The profile references
one exact Contract manifest and adds pre-run construct, task-audit,
evaluator-calibration, analysis, execution, and declared reliability evidence.
Manifest-owned estimand, aggregation, tasks, roles, and independence are reused
rather than copied into a second authority.

Admission `ael.study-admission/0.2-pilot` adds a hash-bound
`quality_profile_ref`; the legacy `0.1-pilot` validator remains available and
rejects the new field. A future freeze binds the admission hash transitively.
These pilot versions can evolve without changing the five stable Contract v0
`0.1` schemas.

The public-results profile and projection policy move to
`ael.public-results/0.3` and `ael.publication-projection/0.3`. Every result now
declares either `not_assessed_historical` or an exact profiled assessment.
Quality metadata cannot raise receipt evidence or claim ceilings, and the four
pre-alpha.7 studies are not retrospectively assessed.

Before release, the same alpha.7 candidate advances those projection-only
versions to `ael.public-results/0.4` and
`ael.publication-projection/0.4`. The profile replaces mutable-looking
`publication` metadata with repository-owned `catalog_state` and an explicit
maintainer-rerun handoff. Generated cards separate public graph verification,
maintainer rerun capability, and linked independent replication; the raw
Contract v0 value is retained as `receipt_reproducibility` but no longer used as
a headline.

The `0.3` projection existed only on the unreleased alpha.7 development branch.
Migration is therefore a documented mechanical profile transformation plus
regeneration, not a compatibility promise to released consumers. Mixed
versions fail closed. The five Contract v0 `0.1` schemas and frozen evidence
remain unchanged.

## Alpha.8 claim-first projection boundary

Alpha.8 advances only the generated public-results profile and projection
policy to `ael.public-results/0.5` and
`ael.publication-projection/0.5`. It replaces the unreleased ordinal claim
ceiling with explicit evidence-state and comparison-design predicates, leads
human cards with decisions and a non-empty `decision_claim_ids` subset of the
selected receipt claims, and derives observed repeat coverage and uncertainty
presence from existing Run Records and Measurement Sets. The profile grouping
controls presentation only; it cannot create or change a receipt claim.

The original Contract v0 `evidence_level` remains present and byte-compatible
as a receipt evidence state. It is not interpreted as a score or total order,
and use, payment, transfer, outcome, reliability, and independence cannot
authorize one another. The five Contract v0 `0.1` schemas, historical evidence,
and study decisions remain unchanged. The live receipt renderer changes only
its human labels from `Evidence level` / `Claim level` to `Receipt evidence
state` / `Claim class`; frozen Markdown created by prior releases remains
byte-identical and is not rematerialized.

The `0.4` projection was part of the unpublished alpha.7 development line, so
the supported migration is a mechanical profile-version update followed by
deterministic regeneration. Alpha.8 does not add a Claim-Support Envelope,
Decision Case, or sixth evidence object.

## Alpha.11 current-unassessed projection boundary

Alpha.11 advances the repository-owned result profile and projection to
`ael.public-results/0.6` and `ael.publication-projection/0.6`.
`quality.assessment = not_assessed_current` requires a reason and projects every
quality axis as unassessed. It is for a prospective run that lacked a
preregistered Study Quality Profile; it cannot be relabeled historical or
certified retrospectively.

The migration is mechanical: update both projection identifiers, use the new
state only for genuinely current unprofiled studies, and regenerate the derived
cards. Historical and hash-bound profiled entries retain their meaning. The
five Contract v0 `0.1` schemas remain unchanged.

Activation v2 also discloses a post-run publication repair: its
`structurally_valid` invalid-protocol receipt uses record-centric `artifact`
claims rather than unsupported `workflow` claims. Observations, measurements,
decision, freeze, and the historical materializer hash do not change.

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
