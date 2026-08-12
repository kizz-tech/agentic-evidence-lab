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
