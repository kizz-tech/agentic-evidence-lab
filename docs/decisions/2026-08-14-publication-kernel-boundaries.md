# Publication kernel boundaries

- Status: accepted for `v0.1.0-alpha.8`
- Scope: public-result projection architecture and extension seams
- Contract impact: none; Contract v0 and frozen evidence remain unchanged

## Context

The claim-first release made the public projection methodologically safer, but
the implementation still concentrated unrelated change reasons in
`ael.result_surface`: untrusted JSON and path handling, source-hash accounting,
study-family audit dispatch, claim admission, empirical projection, rendering,
and output materialization.

That concentration had already produced two concrete defects: a selected claim
could inherit study-wide measurement support, and a selected public sidecar
could be omitted from the source-hash inventory. Future studies will add audit
families and presentation facets, so relying on every caller to remember every
provenance step is not a scalable safety boundary.

## Decision

Keep the file-first architecture and the existing public `ael.result_surface`
API, but separate four inward dependencies:

```text
method_policy                  result_constants
     ▲                              ▲
     │                              │
result_surface ──→ result_core      └── result_rendering
     │
     └──────────→ result_verification ──→ study-family audits
```

The responsibilities are:

- `ael.method_policy`: pure claim-admission rules; no repository or adapter I/O;
- `ael.result_core`: strict JSON, path/symlink checks and one `SourceLedger`
  that owns the complete source-hash inventory for one card;
- `ael.result_verification`: the closed, immutable registry of named
  study-family audit adapters used by both the CLI and public projection;
- `ael.result_rendering`: deterministic JSON and Markdown rendering of values
  that have already passed admission and projection;
- `ael.result_surface`: profile validation, graph-to-card orchestration and
  atomic materialization; it remains the compatibility facade for callers.

Every dereferenced source byte must enter `SourceLedger`. A projection helper
must not mutate an unowned `dict[str, str]` or manually maintain a parallel hash
inventory. Opaque logical receipt references remain explicit and are not
silently dereferenced.

New audit families enter through one registry entry and an adapter test. The
registry is closed by default: profile input cannot import or name arbitrary
Python callables. New rendering formats consume projected values and may not
load evidence or authorize claims.

Architecture tests enforce that Method Policy remains I/O-free and that core,
constants, rendering and verification do not depend back on the orchestrator.

## Why this boundary

These are observed volatility seams, not speculative services. Provenance
accounting changed repeatedly across alpha.5–alpha.8; two frozen study families
already require different audit implementations; and human and machine public
views already share one admitted projection.

The split therefore reduces the blast radius of the next real study while
preserving a single process, one package, one CLI and one file-backed evidence
model.

## Rejected alternatives

1. **Plugin discovery or dynamic entry points.** Rejected because arbitrary
   adapter loading expands the execution and supply-chain boundary before
   external use demonstrates the need.
2. **A service graph, database or event bus.** Rejected because current scale is
   local and deterministic; these add operational state without improving
   evidence validity.
3. **Contract v1 or a sixth persisted object.** Rejected because the refactor is
   implementation structure, not a newly proven domain consistency boundary.
4. **Only renaming or moving the 1,800-line module.** Rejected because it would
   preserve the same coupled responsibilities and the same provenance failure
   mode.

## Consequences and limits

- Existing public imports and generated formats remain compatible.
- Frozen evidence and Contract v0 schemas are unchanged.
- Source inventories may gain a previously dereferenced but previously omitted
  file; this is a correctness repair in the unreleased alpha.8 projection.
- Adding a study card that uses only the generic evidence graph remains
  profile-only. Adding a genuinely new frozen decision semantics requires a
  named adapter and tests.
- The registry does not make study-family semantics generic. Task meaning,
  evaluator fitness and decision logic remain owned by the study family.
- `result_surface` remains a deliberately deep orchestration module. Split it
  again only when a second implementation needs profile parsing or card
  projection independently, not to satisfy a line-count target.

## Revisit triggers

Reconsider these boundaries when at least one of the following is observed:

- an external adapter must be installed without changing AEL source;
- two consumers need a stable typed in-memory projection API;
- concurrent writers or remote execution make file-atomic materialization
  insufficient;
- repeated lifecycle shapes justify a stable Contract object;
- profiling shows rendering or hashing is a material bottleneck;
- an architecture test blocks a legitimate dependency rather than a shortcut.
