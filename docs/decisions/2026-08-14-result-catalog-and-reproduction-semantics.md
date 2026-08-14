# Result catalog and reproduction semantics

- Date: 2026-08-14
- Status: accepted for `v0.1.0-alpha.7`
- Scope: generated public result profile, index, and cards

## Problem

The alpha.7 candidate used one profile field to describe whether a study was
`published`, `unpublished`, or `withdrawn`. That value was embedded in a
deterministic projection committed before a GitHub release. It therefore could
not truthfully represent mutable external release state. It also made the
Systematic Debugging result simultaneously present in public files and absent
from the generated catalog.

The cards also promoted the Contract v0 receipt value `rerunnable` into a
headline. That source enum does not say who can rerun the study, whether the
historical provider execution can be replayed, whether the public result can be
recomputed, or whether a separate party replicated the finding.

## Decision

The result profile and projection policy move to `0.4`.

1. `catalog_state` describes only membership in this repository's result
   catalog: `listed` or `withdrawn`.
2. Git tag, GitHub release, package publication, and release date remain owned
   by their external systems and release records. They are never inferred from
   catalog membership or committed projection bytes.
3. Public cards expose three independent reproduction facets:

   | Facet | Question answered | Current source |
   | --- | --- | --- |
   | Public graph verification | What can a public checkout validate or recompute? | verification kind and boundary |
   | Maintainer rerun | What new execution can the maintainer perform with retained inputs? | explicit profile handoff |
   | Independent replication | What separately owned replication is linked? | receipt independence disclosure |

4. The raw Contract v0 `reproducibility` value is retained as
   `receipt_reproducibility` in the machine card and explained inside the
   technical verification section. It is not a public headline or an alias for
   any of the three facets.
5. All four existing result families, including Systematic Debugging, are
   `listed`. This means they are deliberately included in the catalog, not that
   alpha.7 has been tagged or published.

## Evidence and claim boundary

This is a projection-only correction. It does not change the five Contract v0
schemas, receipt renderer, frozen manifests, run records, measurements,
receipts, study decisions, or historical reports. A profile can narrow a public
handoff but cannot raise receipt evidence, create a replication event, or turn
retained private inputs into public material.

`decision_recomputable` means the checked-in adapter can reconstruct the
published decision from the public frozen bundle. `graph_validatable` means the
public Contract graph and hashes can be checked. Neither means the hosted model
calls can be replayed. `maintainer_only_new_observation` describes a possible
new execution with retained inputs, not a reproduction of historical provider
behavior. `none_linked` is an explicit absence of linked independent
replication evidence, not a claim that no outside attempt exists.

## Migration from the unreleased `0.3` candidate

The transformation is deliberately mechanical:

- replace the ambiguous `publication` field with `catalog_state`;
- add a required `maintainer_rerun` status and boundary;
- move receipt `reproducibility` to `receipt_reproducibility` in generated
  machine cards;
- derive the three reproduction facets without rewriting source receipts;
- regenerate `RESULTS.md`, `docs/results/index.json`, and every result card.

Version `0.3` existed only on the unreleased alpha.7 development branch, so the
repository does not advertise a compatibility window or a migration command
for external consumers. The validator fails closed on mixed `0.3`/`0.4`
profiles, and tests cover the new required fields, allowed enums, deterministic
projection, and current catalog values.

## Consultation and alternatives

The adaptive engineering council used a material-decision route with two
independent profiles:

- `clean_boundary_architect` — finding `clean-boundary-alpha7-01`;
- `evolutionary_deep_pragmatist` — finding `AEL-EDP-20260814-01`.

Both recommended a small projection-only change and preserving frozen evidence.
The strongest rejected alternative was to remove Systematic Debugging from the
catalog. That would avoid the immediate inconsistency, but it would leave both
the mutable-publication-state bug and the overloaded `rerunnable` headline in
place.

Also rejected:

- synchronizing GitHub release state into deterministic generated files;
- changing Contract v0 or historical receipts to repair presentation language;
- designing a generic replication-event schema before one hash-bound external
  replication exists.

## Reversal and extension triggers

Revisit this decision when AEL has a real independently executed replication
to link, when a consumer needs a versioned replication-event contract, or when
catalog withdrawal requires more lifecycle states than `listed` and
`withdrawn`. Any future external release-status view must read the owning
release system or a separately captured release record; it must not overload
the deterministic study catalog.
