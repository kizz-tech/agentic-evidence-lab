# Agentic Evidence Contract v0

Status: executable pre-stable contract shipped in `0.1.0-alpha.1`. It is not
frozen or promised compatible.

## Purpose

The contract records enough identity and decision context to answer:

> Did this exact agentic intervention change the measured outcome relative to
> this exact baseline, on these tasks and runtime, under these rules, and what
> conclusion is still admissible after the result is inspected?

It deliberately does not prescribe a runner, database, trace platform, model,
or evaluator.

## Five documents

```text
Concept
  └── Study Manifest
        ├── Run Record × N
        ├── Measurement Set
        └── Evidence Receipt
```

### Concept

Owner-controlled meaning: idea, proposed mechanism, intended scope, non-goals,
revision, and lineage. Evaluation may falsify its claims but must not silently
rewrite the concept.

Schema: [`concept.schema.json`](../src/ael/schemas/concept.schema.json)

### Study Manifest

The frozen decision contract: comparison mode, primary estimand, baseline and
treatment conditions, exact changed factors, task-pack roles, budgets,
adaptation boundary, selection and stop rules, role assignments, independence
claim, and analysis-plan identity.

Schema: [`study-manifest.schema.json`](../src/ael/schemas/study-manifest.schema.json)

### Run Record

One condition × task × repeat observation. It records operational validity,
runtime/model identity as exposed, usage, outputs, effects, event-capture limits,
integrity issues, and source provenance. A poor answer remains a valid run; only
an operationally invalid run may use the declared retry path.

Schema: [`run-record.schema.json`](../src/ael/schemas/run-record.schema.json)

### Measurement Set

Domain-owned deterministic, outcome, subjective, process, cost, and aggregate
measurements. It preserves evaluator identity, blinding, evidence links,
critical failures, and limitations instead of forcing one universal score.

Schema: [`measurement-set.schema.json`](../src/ael/schemas/measurement-set.schema.json)

### Evidence Receipt

The bounded decision output: receipt evidence state, reproducibility,
independence, adopt/reject/narrow/inconclusive disposition, evaluated claims,
unsupported inferences, limitations, invalidation triggers, and exact state.

Schema: [`evidence-receipt.schema.json`](../src/ael/schemas/evidence-receipt.schema.json)

## Binding invariants

The CLI currently enforces both JSON Schema and cross-document rules:

- every study contains a baseline and a treatment;
- every treatment declares its changed factors and baseline delta;
- frozen, executing, and completed studies pin concept, intervention,
  task-pack, and analysis-plan hashes;
- run conditions and task packs exist in the referenced study;
- evaluative measurements cannot consume operationally invalid runs;
- relative local references reproduce their declared SHA-256;
- an operational-stack study cannot promote its result into a model-only or
  factor-causal claim;
- a receipt with disclosed role overlap cannot call itself independently
  verified;
- public contract objects reject personal absolute filesystem paths.

Schema validity does not establish study validity. Statistical calibration,
task quality, evaluator fitness, causal identification, publication rights, and
the truth of authored claims require separate evidence and review.

## State and evidence language

The receipt keeps these dimensions separate:

```text
experiment → artifact → repository → publication → deployment → outcome
```

The receipt also retains a coarse evidence-state vocabulary:

```text
integrity: structurally valid · runtime conformant
effect: controlled effect observed · effect reproduced
generality: transferred
use: externally decision-changing · paid repeated use
outcome: downstream outcome observed · independently outcome-verified
```

These values are retained for Contract v0 compatibility; they are not a score
or total order. Alpha.8 public projection uses explicit claim-specific
predicates instead of converting them into numeric ranks. External use does not
stand in for transfer, payment does not stand in for measured outcome, and no
state upgrades task validity, evaluator calibration, reliability, independence,
or freshness. See the [AEL Method](method.md).

## Deterministic CLI

```bash
uv sync
uv run ael validate examples/council-generation-1
uv run ael render \
  examples/council-generation-1/evidence-receipt.json \
  --output examples/council-generation-1/evidence-receipt.md
uv run ael hash examples/council-generation-1/evidence-receipt.json
```

Rendering never derives a verdict from scores. The machine-readable receipt
already contains an accountable decision; the CLI only validates and presents
it. Contract v0 retains the JSON keys `evidence_level` and `claim_level` for
compatibility; the live renderer labels them **receipt evidence state** and
**claim class** so its human output does not imply an ordinal scale.

The optional Docker adapter runs deterministic fixtures without writable access
to their canonical source. It does not change the five documents or make a run
valid by itself. See [Container runner isolation](runner-isolation.md).

## First executable mapping

[`examples/council-generation-1`](../examples/council-generation-1) contains:

- one reconstructed Council concept;
- one completed study manifest;
- twelve sanitized held-out run records;
- one measurement set with case-level scores, critical-anchor observations,
  generated-work metrics, process findings, and explicit limitations;
- one machine-readable receipt and deterministic Markdown rendering.

The import checks the frozen 114-file private source package composite before
writing sanitized records. It does not copy private task anchors, final model
answers, raw reasoning traces, or personal filesystem paths.

## Compatibility and next gates

The schema version is pre-stable. Freeze is blocked until:

1. the Council mapping remains lossless under independent methodology review;
2. prompt-only and ordinary-skill examples validate without changing concept
   meaning;
3. Council Generation 2 numeric rules are calibrated rather than inherited;
4. a migration rule exists for the first intentional schema change;
5. the first intentional schema change exercises and documents the migration
   policy.
