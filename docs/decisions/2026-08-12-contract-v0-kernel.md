# Decision: Contract v0 is a file-first evidence kernel

Date: 2026-08-12  
Status: implemented for the local v0 vertical slice  
Route: direct engineering decision; no named advisor consultation was claimed

## Decision

Use five language-neutral JSON document types: Concept, Study Manifest, Run
Record, Measurement Set, and Evidence Receipt. JSON Schema defines their
portable structure. A small Python CLI validates cross-document invariants,
checks local content hashes, rejects personal absolute paths, and renders an
explicitly authored receipt into Markdown.

The CLI never infers an adoption decision from a score. Measurement and claim
ownership stay explicit; rendering is deterministic presentation, not an
automated judge.

Council remains a separate source owner. The first AEL example imports only
sanitized run identity, usage, aggregate judgment, and content-addressed source
references from Council Generation 1. It does not copy private task anchors,
final answers, raw traces, or personal filesystem paths.

## Binding reasons

- The first receipt must work without a hosted service, database, UI, or new
  runner.
- Public contracts should not depend on one implementation language.
- JSON avoids the undeclared YAML dependency failure already observed in the
  Council Generation 1 toolchain.
- Cross-document validation is where AEL adds decision safety beyond ordinary
  per-file JSON Schema validation.
- Example-first development exposes missing semantics before schema stability is
  claimed.

## Strongest rejected alternative

Adopt Inspect AI plus Braintrust or LangSmith as the initial product kernel.
Those systems remain adapter candidates, but selecting them before the first
receipt would bind AEL semantics to execution and storage choices that the
contract is intended to outlive.

## Reversal path

The schema version is explicitly pre-stable. If the Council, prompt-only, and
skill examples cannot share the five-object envelope without erasing domain
meaning, revise or narrow v0 before publishing it. A future runtime may replace
the Python CLI while retaining the JSON contract.
