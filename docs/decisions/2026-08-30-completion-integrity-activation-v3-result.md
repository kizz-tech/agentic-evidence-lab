# Completion Integrity activation v3 is closed protocol-invalid

Date: 2026-08-30
Status: accepted owner decision for the exact v3 evidence

## Decision

Close activation v3 as `protocol_invalid / revise_activation_adapter` and
publish the bounded negative result. Do not repair the frozen private task,
resume the raw root, retry the submitted cell, or use v3 to estimate reporter,
executor, model, or intervention quality.

The exact owner action is:

```text
do_not_scale_until_protocol_failure_is_repaired_in_a_new_revision
```

## Evidence that governs the decision

- preregistration SHA:
  `7257025eab78e8894f69e6ad0677fabec8cf5542`;
- freeze SHA-256:
  `5cbbfefdcaf48d3c57a5394e72304a080b3cf85a6312a1c69816d4c9d6762f24`;
- frozen schedule: six cells over two sacrificial roots;
- observed state: zero terminal cells, one submitted ambiguous executor
  attempt, five never-submitted cells;
- outcome retries and resumes: zero;
- public graph: six run records, 24 measurements, one structurally valid
  evidence receipt;
- deterministic public decision: `protocol_invalid`;
- public audit: passed before Git proof; exact-Git proof is a release gate.

The submitted Codex container and hidden evaluator both exited successfully,
but the owner adapter failed before terminal capture because the private
`TASK.md` requirement lines used a typographic dash where the live parser
required `: `. This occurred after provider submission, so truth is ambiguous
under the frozen protocol even though candidate and evaluator bytes exist
privately.

## Interpretation

This is a measurement-system failure, not a model result. The prior
qualification established semantic-mutant sensitivity and wrapper composition
on synthetic truth, but it did not execute the exact task-instruction parser in
the live normalization path. Therefore:

- zero valid reporter observations means **no effect estimate**, not a null;
- evaluator exit `0` cannot retrospectively create a valid executor claim;
- successful candidate code cannot compensate for missing terminal custody;
- the cost of the ambiguous attempt remains observed and public;
- v3 roots are now observed/contaminated and cannot be reused as fresh evidence.

## Prospective source repair

The repair changes only future revisions:

- task qualification now parses the exact executor-facing contract and checks
  ordered requirement identity against the dossier before expensive matrix
  execution;
- live and post-stop observation construction share one pure function that
  preserves submitted/ambiguous state;
- a no-model/no-retry finalizer closes interrupted journals without overwriting
  terminal artifacts;
- materialization uses version-derived public IDs, pack identity, task strata,
  runtime passport, and explicit ambiguous-attempt projection;
- the public auditor cross-checks observations and runs against the frozen
  schedule and verifies preregistered code bytes.

V1/v2 public identities and frozen bytes remain unchanged.
The post-freeze source boundary and zero-call terminalization are recorded in
[`normalization-deviation.json`](../../studies/completion-integrity/activation-v3/results/normalization-deviation.json);
terminal projection is disclosed as post-freeze rather than mislabeled as
preregistered analysis.

## Admission rule for any activation v4

Activation v4 is not authorized merely because source tests pass. Before a
first scored submission it requires:

1. two new uncontaminated task roots in a new private pack;
2. exact TASK-parser/dossier equality included in qualification evidence;
3. semantic-mutant and evaluator-repeat qualification on the new roots;
4. full live-path dry qualification through task parsing, normalization,
   capture, truth, sealed evidence, reporter submission, and assessment without
   a scored provider outcome;
5. a new Study Quality Profile, freeze, raw root, preregistration commit, and
   green exact-SHA CI;
6. the same one-submit, no-retry, stop-on-first-integrity-failure rule.

Only a fully valid activation may qualify the adapter for building a larger
task population. It still cannot by itself admit or prove that larger study.

## Evidence-to-Action consequence

M2 remains unresolved: no decision-governing intervention was admitted. M3
(owner action and downstream outcome) and M4 (AEL-CEP retrospective shadow)
remain ineligible. M1 human Decision Utility remains independently blocked by
participants, consent, private blinded cases, pilot variance, sample size, and
stopping.

Alpha.13 may publish this result and the prospective hardening because it adds
a real negative observation and closes a named integrity defect. It must not
claim that Completion Integrity, Codex, or AEL-CEP improved.
