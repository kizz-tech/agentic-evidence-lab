# Alpha.12 AEL-CEP public boundary

Date: 2026-08-30
Status: accepted for the alpha.12 method release

## Context

AEL-CEP Stage 0 already exists as a locally validated, unreleased candidate.
Its pure kernel is large and exposes many names through module-level
`__all__`, while the documented user path is the dedicated CLI over versioned
protocol and bundle files. The first release must preserve the reviewed policy
and golden bytes without turning implementation helpers into an accidental
compatibility contract.

## Decision

Alpha.12 keeps the accepted three-module dependency direction:

```text
CLI / tool -> strict bundle adapter -> deterministic simulator -> pure policy kernel
           \--------------------------------------------------> pure policy kernel
```

The supported public contract is limited to:

1. `ael coevolution simulate`;
2. `ael coevolution check`;
3. `ael coevolution rescore`;
4. the versioned protocol, record, bundle, and simulator file/schema formats;
5. deterministic file bytes and documented fail-closed CLI behavior.

`ael.coevolution`, `ael.coevolution_bundle`, and
`ael.coevolution_simulator` are package-internal experimental modules. Direct
imports remain possible for repository-owned tools and tests, but their names,
signatures, return dictionaries, and exceptions carry no compatibility promise
in alpha.12. Their `__all__` values are empty to prevent star imports from
looking like an endorsed API. A future Python facade requires an observed
separately owned consumer and a new compatibility decision.

The 7,253-line kernel is not split in this release. It contains multiple
conceptual regions, but current validation and promotion invariants cross those
regions as one fail-closed bundle transaction. File length alone does not prove
independent ownership or change cadence. Internal extraction remains available
behind the unchanged CLI/file boundary when change history or a second consumer
demonstrates one real volatility seam.

## Release and operational limits

- Contract v0 and all released alpha.11 evidence bytes remain unchanged.
- Golden Stage-0 protocol, bundle, and report bytes remain byte-identical.
- Stage 0 performs no hosted model call or external effect.
- The adapter assumes trusted local directory ownership. It rejects symlinks
  and non-regular files but does not claim protection from a hostile process
  racing pathname replacement in a shared directory.
- Hash chains establish logical content and predecessor integrity. They do not
  supply physical append-only storage, access control, secret custody,
  deletion enforcement, backup discovery, or production recovery.
- Alpha.12 does not add Stage 1, Contract v1, a database, evaluator registry,
  hosted service, or empirical coevolution claim.

## Engineering council

Route: expanded council. Four independent read-only first passes completed on
one shared factual brief:

- `clean_boundary_architect` — `AEL-A12-CB-01`;
- `domain_model_cartographer` — `ael-dmc-alpha12-20260830-01`;
- `evolutionary_deep_pragmatist` — `AEL-A12-EDP-01`;
- `production_systems_sentinel` — `AEL-A12-PSS-20260830-7F3C`.

All four recommended keeping the three-module implementation and narrowing the
public compatibility boundary rather than splitting the kernel or deferring
the method release. One targeted challenge resolved the only material
disagreement—whether to support a Python library seam—in favor of CLI/file/
schema-only compatibility (`AEL-A12-CB-CHALLENGE-01`).

The strongest rejected alternative was a pre-release split into protocol,
ledger, bridge, promotion, and projection modules. It remains credible if
future defects, change history, maintainers, or consumers demonstrate those
independent seams. Today it would broaden the verification delta around an
invariant-dense, already reviewed policy without a measured consumer benefit.

## Verification and reversal

Alpha.12 is releasable only from one clean exact commit after:

- focused and full unit/contract suites;
- architecture and empty-export fitness checks;
- byte-identical Stage-0 materialization;
- frozen historical evidence checks;
- release-tree privacy/secret scan;
- wheel/sdist verification and clean-wheel CLI exercise;
- Docker isolation smoke;
- exact-SHA remote CI and downloaded-asset verification.

If direct Python embedding becomes a real need, add one use-case-level facade
in a later release rather than stabilizing the current kernel. If Stage 0
cannot preserve golden bytes or its operational overhead exceeds the value of
retrospective use, retain alpha.12 as an experimental method artifact and do
not advance to prospective coevolution.
