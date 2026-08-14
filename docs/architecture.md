# Architecture

Agentic Evidence Lab is a file-first method with optional execution adapters.
The evidence contract owns experiment meaning; a runner only produces inputs to
that contract.

```text
capability source (separate owner/version)
                │ immutable artifact reference
                ▼
concept → study manifest → runner adapter → run records
                                      │
                                      ▼
                         domain evaluator / measurements
                                      │
                                      ▼
                              evidence receipt
```

## Evidence Core

`src/ael/schemas` defines five JSON document types. `ael.validation` performs
schema and cross-document checks, including hash resolution, condition/task
references, evidence-role consistency, and claim-level restrictions.
`ael.render` turns an already decided receipt into Markdown; it does not infer a
verdict from scores.

Alpha.5 keeps those five Contract v0 schemas and the receipt renderer unchanged.
Its public result surface is projection-first:

```text
validated Contract v0 evidence graph
              + publication profile
                         │
                         ▼
       deterministic public result projection
              ├─ RESULTS.md (human cards)
              ├─ docs/results/index.json (machine index)
              └─ docs/results/<slug>.md (card projections)
```

The profile selects public receipts and claims, declares replication
instructions and unavailable-material categories, preserves explicit historical
unknowns, and may select exact lifecycle refs. Lifecycle status is derived from
those hash-bound records rather than profile prose. The projection may enforce
a claim ceiling, but it cannot create evidence, change a receipt, or become a
second authority. Evidence level, reproducibility, independence, freshness,
action, and outcome remain separate axes; a card renders unavailable historical
action or outcome as `not_declared_historical` or `unassessed` rather than
guessing.

Alpha.6 exercises one complete prospective admission → effect → adoption →
action → follow-up lifecycle in the Systematic Debugging real-shadow pilot.
Those record shapes remain study-local and experimental; Contract v0 still has
five stable document types. Public result cards may derive lifecycle status
only from exact hash-bound refs. One completed pilot is not enough to stabilize
a generic Decision Case or Outcome Follow-up schema.

Alpha.7 adds one adjacent methodological sidecar:

```text
Contract v0 manifest ─┐
task/evaluator refs ──┼→ ael.study_quality → deterministic preflight
explicit as_of ───────┘          │
                                 └→ bounded public quality facets
```

`ael.study_quality` owns the pilot profile rules. The CLI and result surface
depend on that module and do not duplicate its policy. Contract validation does
not depend on the quality module. Historical receipts remain unchanged and
project `not_assessed_historical`; a future profiled card must match the
receipt's exact study ID, revision, and manifest hash. Preflight conformance is
design evidence, not a quality score or an empirical result.

Git ancestry or a tag can prove repository artifact ordering—for example, that
freeze bytes are present in an ancestor. It cannot prove that private model
calls occurred before a result, reconstruct private events, or establish
independent replication.

## Execution adapters

`ael.sandbox` invokes Docker with a read-only canonical fixture, a tmpfs working
copy, disposable output staging, a read-only root, no capabilities, resource
limits, and either no network or the controlled OpenAI proxy. After the
container stops, AEL rejects symlinks and special entries before copying staged
results into the operator's fresh private output. The offline runner is the
default for untrusted executable fixtures.

The hosted Codex adapter is intentionally narrower. It pins the CLI image and
egress destinations, but the agent process can read the injected credential.
It is therefore limited to maintainer-controlled inputs. See
[`SECURITY.md`](../SECURITY.md).

## Task-pack adapter

`ael.taskpack` checks that visible tests pass on a pristine fixture while hidden
acceptance tests initially fail, then evaluates an exported candidate against
both. This is one adapter, not a universal task format.

## Third-party source locks

`ael.source_lock` validates metadata-only references to external capability
trees and verifies a caller-provided Git checkout against the exact commit,
repository-relative tree hash, and observed license file. It does not fetch,
install, import, or execute the source. Registration and execution eligibility
are separate states. The current hosted runner permits only exact source-locked
snapshots that the maintainer reviewed and explicitly accepted for
maintainer-controlled execution; arbitrary submissions remain blocked because
its reusable credential is readable by the agent process.

The first multi-study use is [Agent Skills Season 1](../studies/agent-skills-season-1/README.md).
Its ten dossiers share the evidence envelope and isolation policy while keeping
their metrics, task semantics, and evaluators local. The completed bounded
negative PBT v2 result is one study-level effect decision; activation-only and
unrun studies remain distinct cards rather than entries in a global score.

## Ownership boundaries

- A capability repository owns its concept, prompts, tools, skills, versions,
  and releases.
- This repository owns generic evidence schemas, adapters, public task packs,
  cross-capability studies, and receipts.
- Evaluators own domain postconditions and cannot be replaced by model voting.
- Private holdouts, raw hosted traces, and credentials remain outside the
  public repository.

Private screening and confirmation packs also remain outside the Git worktree,
not merely under an ignored directory. Public manifests and receipts retain
only opaque identifiers, hashes, roles, and non-revealing strata. Operators
place a unique reserved private-evidence canary inside each private pack; the
release scan fails if any such bytes enter the public tree.

The system is deliberately local and file-based in alpha. There is no database,
RAG layer, hosted control plane, marketplace, or registry service.
