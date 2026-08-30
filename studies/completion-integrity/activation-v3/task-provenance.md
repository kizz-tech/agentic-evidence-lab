# Activation v3 task provenance

The two sacrificial roots are private, maintainer-authored repository graphs
created for activation v3 after all activation-v2 task/output bytes were
observed.

| Root | Ecosystem | Distinct graph | Primary stopping trap |
| --- | --- | --- | --- |
| `CI3-PY-01` | Python | batch-ingestion parser, rejection ledger, and summary owner | valid rows pass while invalid-row accounting is silently omitted |
| `CI3-TS-01` | TypeScript/Node | event subscription registry and lifecycle owner | callback delivery passes while unsubscribe damages or leaks listener state |

Private pack identity:

- pack: `kizz:ael:private-pack:completion-integrity-v3-activation` revision `1`;
- strict-adapter SHA-256:
  `6cd7e18513e3f130a60878afaeec3ee6befc43c17ecd63e4cd4844e211ef5c9d`;
- sandbox tree SHA-256:
  `0b7585b044bceb789b227bb175e0a0931a76566a0b977816c9c891e5072ce691`;
- current assessment: structural `pass`, two candidates, zero scored roots,
  `pending_pilot` sample size;
- passing qualification receipt SHA-256:
  `8f0718dbc2d5f51fd322bc4f8b4693ee8ce36cba615b54e68f28d28f63321c1d`.

The roots share no task bytes, repository graph, acceptance owner, failure
mechanism, or ecosystem with each other. They are sacrificial calibration
instruments only and cannot contribute to a future screening or confirmation
sample.

The first full qualification produced a passing task matrix but an invalid
owner receipt identity (`activation-v1`). That receipt remains private and
invalid. After the version-derived identity repair, a fresh complete
qualification passed both roots, all eight challenge cases per root, and two
deterministic evaluator repeats per case.
