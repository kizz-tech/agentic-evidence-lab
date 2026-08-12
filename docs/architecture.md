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

## Ownership boundaries

- A capability repository owns its concept, prompts, tools, skills, versions,
  and releases.
- This repository owns generic evidence schemas, adapters, public task packs,
  cross-capability studies, and receipts.
- Evaluators own domain postconditions and cannot be replaced by model voting.
- Private holdouts, raw hosted traces, and credentials remain outside the
  public repository.

The system is deliberately local and file-based in alpha. There is no database,
RAG layer, hosted control plane, marketplace, or registry service.
