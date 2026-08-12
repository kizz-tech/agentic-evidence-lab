# Agentic Evidence Contract v0 — drafting and review brief

Status: retained design history. For the executable public contract, read
[`contract-v0.md`](contract-v0.md). The current schemas and CLI are executable
and locally validated, but nothing in this drafting brief is a stable public
contract.

## Objective

Define the smallest evidence envelope that can represent:

1. the existing Council generation-one result without expanding its claims;
2. the proposed Council Generation 2 roster comparison;
3. one prompt-only coding intervention;
4. one installable coding skill;
5. one operational comparison of two differently configured agent stacks.

If one envelope cannot represent these cases without erasing domain semantics,
v0 must narrow its scope rather than add arbitrary abstraction.

## Minimum objects

The first draft should prefer five serializable objects or fewer:

1. **Concept** — owner-controlled idea, mechanism hypothesis, intended scope,
   non-goals, revision, and lineage.
2. **Study manifest** — decision question, estimand, comparison mode, candidates,
   baselines, frozen configuration, task-pack refs, budgets, selection/stop
   rules, independence roles, and analysis-plan hash.
3. **Run record** — exact treatment/configuration/task/repeat identity,
   operational validity, observable events, usage, timing, outputs/effects refs,
   and exposed runtime/provider identity.
4. **Measurement set** — deterministic outcomes, critical failures, subjective
   assessments with evaluator identity, rework, cost, and uncertainty.
5. **Evidence receipt** — evaluated claims, limits, unsupported inferences,
   provenance, independence level, decision, and reversal trigger.

Artifacts and task packs may begin as content-addressed references inside the
study manifest. Promote them to standalone schemas only when independent reuse
or lifecycle evidence requires it.

## Execution substrate boundary

Contract v0 is file/Git-first. It must support a useful machine-readable and
human-readable receipt without requiring a hosted experiment ledger, database,
UI, or newly built generic runner.

Execution, sandbox, tracing, and experiment platforms are adapters, not owners
of AEL semantics. Inspect AI is a plausible first execution-spike candidate;
Braintrust and LangSmith are alternative ledger/integration candidates rather
than mandatory dependencies. Select none until a bounded spike shows that it
can preserve exact intervention identity, baseline delta, budgets, effects,
role overlap, evidence privacy, and receipt invalidation without distorting the
contract.

## Boundaries reviewers must challenge

### Intervention versus configuration

The same model, skill, tool, or topology may be the treatment in one study and a
frozen surrounding condition in another. The contract needs an explicit
treatment assignment and baseline delta; a taxonomy of component types is not
enough.

### Stack comparison versus causal comparison

Operational stack comparisons permit different components and support a
practical system choice. Controlled factor comparisons support narrower causal
claims. The receipt must prevent promotion of a stack-level result into a
model-only claim.

### Adaptation versus confirmation

The study must record candidate budget, task roles, task access, selection and
pruning rules, and the confirmatory candidate freeze. Repeated samples do not
repair benchmark leakage or unrestricted candidate search.

### Reproducibility versus provider drift

A hosted model name may not identify immutable behavior. v0 must distinguish
rerunnable, replayable, statistically reproduced, transferred, and
independently verified evidence.

### Own capability versus independent verification

Kizz may build and evaluate the same capability, but the resulting evidence is
maintainer-evaluated. The contract must represent role overlap rather than hide
it behind the lab brand.

### Domain semantics versus generic metadata

The generic envelope must preserve domain-owned acceptance criteria and critical
failures. It must not force every result into a universal score or generic prose
rubric.

### Statistical design versus invented precision

The contract must serialize predeclared thresholds, sample design, uncertainty,
and selection rules, but must not make uncalibrated numbers appear valid merely
because they are machine-readable. Before freezing a confirmatory Council
Generation 2 manifest, use actual generation-one telemetry, available task
families, evaluator capacity, and design simulation or equivalent operating-
characteristic evidence to justify screening size, holdout size, effect and
harm thresholds, cost/rework gates, agreement rules, and time caps.

A small screen may establish admissibility and expose critical failures. It
must not be assumed to rank multiple candidates reliably unless selection error
has been evaluated. Downstream implementation sentinels are diagnostic until
their decision stability is known.

### Current evidence versus revision drift

External product and benchmark capabilities are time-bound claims. Bind each
material assertion to the canonical source and exact revision or access date.
Do not merge counts or claims from different revisions; SkillsBench v4, for
example, is the relevant source for its current task and configuration scope.

## Required falsifiers

Reject or narrow the draft if:

- it cannot losslessly represent the supported and unsupported Council claims;
- adding a prompt-only or skill case requires changing concept semantics;
- stack and factor comparisons produce indistinguishable receipts;
- a reviewer cannot determine what changed relative to baseline;
- task leakage, candidate selection, or evaluator role overlap is hidden;
- hosted-model drift is reported as exact reproducibility;
- implementation/rework outcomes cannot remain domain-specific;
- the schema requires a custom runner, database, or UI before a receipt can be
  produced.
- confirmatory sample sizes or decision thresholds are accepted only because
  they look reasonable, without calibration evidence.

## First review inputs

1. Current Agentic Evidence Lab owner contract.
2. Council generation-one manifests, result, and limitations.
3. Council Generation 2 three-roster proposal.
4. The content-addressed ChatGPT Pro falsification review set received on
   2026-08-12 and its adoption decision.
5. One deliberately simple hypothetical prompt-only case.

External reviews are processed through `docs/reviews/README.md`. A review can
change this brief only through an explicit triage and adoption decision.

## Completion evidence

Contract v0 is ready to freeze when:

- all five representative cases serialize without invented claims;
- a deterministic validator rejects missing identities, ambiguous treatment,
  invalid state transitions, and claim-scope promotion;
- one human-readable receipt can be generated without a platform service;
- Council remains a separate canonical product owner;
- an independent methodology review has no unresolved critical finding;
- confirmatory numeric rules have an explicit calibration basis rather than
  inherited draft values;
- the repository records the exact draft hash and decision that froze it.

Current evidence: the Council Generation 1 case now serializes as one concept,
one completed study, twelve sanitized run records, one measurement set, and one
bounded receipt. Cross-document validation and deterministic rendering pass.
Prompt-only and ordinary-skill transfer, methodology review, calibration, and
the freeze decision remain open.

## Review decision incorporated on 2026-08-12

The first review intake narrowed the build boundary without validating the
product thesis. The accepted direction is recorded in
[`docs/decisions/2026-08-12-review-intake-and-v0-direction.md`](decisions/2026-08-12-review-intake-and-v0-direction.md).

In short: own the protocol and receipt semantics; test existing execution
substrates through adapters; keep commercial release assurance deferred; and
do not freeze the proposed Council Generation 2 numbers before statistical and
operational calibration.
