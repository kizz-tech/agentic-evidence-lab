# AEL Method: from a claim to a reversible decision

AEL is a method for deciding whether one exact versioned change to an agent
system should be adopted, rejected, narrowed, or tested again. The method is
runner-independent and claim-first: it starts from the decision and the exact
statement that evidence must support, not from a benchmark score.

```text
question → claim → admitted design → frozen comparison → observations
         → evaluated claim → bounded decision → action → outcome/revalidation
```

## The non-compensation rule

Evidence predicates stay independent.

- Hash-valid artifacts do not prove valid tasks.
- A controlled design does not calibrate its evaluator.
- Planned repeats do not establish observed reliability.
- A maintainer rerun is not independent replication.
- External use does not prove transfer.
- Payment does not prove a measured downstream outcome.
- An observed outcome does not identify its causal mechanism by itself.

AEL therefore has no global evidence score or study-quality grade. Negative,
null, bounded, and unresolved claims are useful when they prevent a weak change
from becoming the default.

## Seven gates

### 1. Frame the decision

Name one owner decision, one exact intervention, one counterfactual, one task
population, and the strongest claim the design is allowed to support. Record a
falsifier and the event that will make the result stale.

The question should be expressible as:

> For this exact change, on this task population and complete system boundary,
> does the declared outcome change enough to govern this exact decision?

### 2. Admit the measurement

Before scored work, use the [Study Quality Preflight](study-quality-preflight.md)
to bind:

- construct and claim ceiling;
- task provenance and task/oracle audit;
- evaluator calibration and adjudication;
- decision threshold and missing/invalid-cell policy;
- uncertainty method or explicit `not_estimable` limitation;
- planned repeats, ordering, perturbations, role overlap, and freshness.

A preflight pass means the declaration is conformant. It is not scientific
certification and does not prove that the profile preceded private model calls.

### 3. Freeze the exact comparison

Freeze the Concept and Study Manifest, candidate and baseline identities, full
model/runtime/harness configuration, task and evaluator packages, budget,
schedule, analysis rule, stop rule, and owner roles. A changed mechanism or
post-result threshold creates a new revision; it never edits the old study.

### 4. Observe without cleaning away failure

Retain one Run Record for every admitted task-condition-repeat cell. Preserve
poor answers, critical failures, invalid runs, retries, effects, cost, and event
capture limits. Operational invalidity and task failure are different states.

### 5. Evaluate exact claims

Measurements belong to the domain evaluator. Executable end state is primary
when available; model or human judgment is used only for qualities the
deterministic oracle does not own and must retain its calibration boundary.

Each selected claim carries its own class, status, scope, evidence references,
and falsifier. The publication profile names which selected claims govern the
displayed disposition and which are additional workflow/artifact disclosures;
that grouping cannot change a receipt claim or its status. Claim admission is
explicit:

| Claim class | Minimum design/evidence predicate |
| --- | --- |
| `artifact` | structurally valid artifact identity |
| `workflow` | runtime-conformant workflow evidence |
| `factor_causal` | controlled-factor comparison with claim-local Measurement Set evidence |
| `model_only` | controlled-factor comparison whose changed intervention class is model-only, with claim-local Measurement Set evidence |
| `operational_stack` | operational-stack comparison with claim-local Measurement Set evidence |
| `transfer` | matching transfer evidence plus a claim-local measurement linked to a run on a transfer task pack; use or adoption is not a substitute |
| `outcome` | matching downstream-outcome evidence plus a claim-local outcome measurement; payment is not a substitute, and independently verified outcome evidence also requires independent ownership |

Contract v0 keeps a coarse `evidence_level` field for compatibility. Public
cards call it the **receipt evidence state** and keep it in technical detail; it
is not an ordinal claim-authority ladder.

Every selected public claim `evidence_ref` is classified as a Measurement Set
row, a safe public sidecar whose SHA-256 enters the generated card inventory,
or an explicitly opaque receipt reference. Every selected claim needs at least
one public binding. For causal, stack, transfer, and outcome claims, at least
one binding must specifically be a Measurement Set row; a sidecar cannot
substitute. A study-wide measurement of the right kind cannot authorize an
unrelated claim. Artifact and workflow claims may retain additional disclosed
opaque refs because their historical evidence is not always represented as a
Measurement Set row or hash-bearing receipt reference.

This proves graph binding, not semantic entailment. Task and evaluator audit
must still establish that a referenced metric measures the stated construct;
a `transfer` task-pack label does not prove representative transfer, and an
`outcome`-typed row does not by itself prove a valuable downstream outcome.

### 6. Decide and act

The Evidence Receipt records a bounded evidence disposition. The operational
owner separately decides whether to install, route, keep optional, reject, or
retest the candidate. An action record states what was actually verified or
blocked. Neither a receipt nor a policy file proves that every client enforced
the action.

### 7. Observe outcome, replicate, or revalidate

Complete the scheduled follow-up or record that the observation is missing,
cancelled, or invalidated. Keep these questions separate:

- can a public checkout validate or recompute the evidence graph?
- can the maintainer run a new observation with retained inputs?
- has a separately owned replication been linked?
- did the actual owner action produce an observed downstream outcome?
- is the claim still fresh for the current stack and task boundary?

New evidence appends a revision, replication, correction, or follow-up. It does
not rewrite the historical receipt.

## Public result order

An alpha.8 card is read in this order:

1. bounded decision and reversal trigger;
2. decision-governing claim statements and statuses, followed by any additional
   selected workflow/artifact disclosures;
3. exact comparison and task scope;
4. observed outcomes, cost, repeat coverage, and uncertainty presence;
5. prospective study-design preflight;
6. action, outcome, freshness, replication, and independence;
7. technical receipt metadata, raw graph, and limitations.

The generated card is a deterministic projection, not a new evidence owner.

## Minimal local path

```bash
uv run ael validate examples
uv run ael study preflight \
  studies/quality-preflight/examples/pass/quality-profile.json \
  --json-output studies/quality-preflight/examples/pass/preflight.json \
  --markdown-output studies/quality-preflight/examples/pass/preflight.md \
  --check
uv run ael results check studies/public-results.json --require-git-proof
```

Use [Contract v0](contract-v0.md) for the five evidence documents,
[Reproducibility](reproducibility.md) for audit boundaries, and the
[Roadmap](../ROADMAP.md) for the next empirical falsifiers.

## What is deliberately not stable

Admission, adoption, action, outcome-follow-up, and study-quality profiles are
pilot sidecars. A generic Decision Case, reliability schema, replication event,
or sixth Contract object waits for repeated prospective use in at least two
materially different study families and an explicit migration decision.
