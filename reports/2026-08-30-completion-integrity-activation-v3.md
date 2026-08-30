# Completion Integrity activation v3

## Answer first

Activation v3 did **not** qualify the Completion Integrity adapter and did not
measure a `B0` versus `T1` reporter effect. The frozen six-cell Codex schedule
stopped on the first submitted executor cell. Codex and the hidden evaluator
both exited successfully, but the owner adapter then failed to parse the exact
executor-facing requirement contract. Because submission had already occurred,
the attempt is retained as `ambiguous`, not retried or reclassified as a valid
executor observation.

The public decision is `protocol_invalid` with disposition
`revise_activation_adapter`. There are zero terminal cells, one submitted
ambiguous attempt, and five never-submitted cells. This is evidence about an
owner-method integration failure, not evidence that Codex, the executor, or
either reporter condition performed well or poorly.

## Decision

- Public status: `protocol_invalid`.
- Disposition: `revise_activation_adapter`.
- Owner action: do not scale until the protocol failure is repaired in a new
  revision.
- Schedule: 0 terminal cells out of 6; 1 submitted ambiguous executor attempt;
  5 cells never submitted.
- Retries or resumes: 0.
- Valid executor observations: 0.
- Valid reporter observations: 0 for `B0`, 0 for `T1`.
- Effect estimate: none. Ambiguous, invalid, and unrun calls are not scored as
  disagreements.

The exact v3 pack, raw root, and preregistration are closed. Repairing the task
text or parser and rerunning those cells would violate the frozen no-retry
contract.

## What was frozen

- Codex CLI `0.146.0`, `gpt-5.6-sol`, reasoning effort `xhigh`;
- one new Python and one new TypeScript sacrificial repository root;
- a common executor followed by matched `B0` and `T1` reporters per root;
- deterministic hidden evaluation and a sealed read-only reporter boundary;
- an eight-case semantic-mutant qualification with two evaluator repeats per
  case;
- a six-cell synthetic full-wrapper qualification, a passing two-call schema
  capability probe, exact Docker image identities, and zero outcome retries;
- preregistration commit
  `7257025eab78e8894f69e6ad0677fabec8cf5542` and freeze SHA-256
  `5cbbfefdcaf48d3c57a5394e72304a080b3cf85a6312a1c69816d4c9d6762f24`.

The Study Quality Profile was `conformant_with_warnings`. It disclosed only two
maintainer-authored roots, one planned call per retained cell, fixed order,
unestimable uncertainty, and author/evaluator overlap. Passing that profile was
permission to attempt activation, not evidence that activation would work.

## Observed execution

The only submitted cell was `CI3-PY-01-E0`. The container exited `0`, preserved
the frozen fixture and image bindings, persisted no detected reusable
credential value, and emitted one completed Codex turn. The retained public
cost projection records 132,484 input tokens, 106,752 cached input tokens,
4,327 output tokens, 1,735 reasoning-output tokens, and 119,291 ms wall time.

The hidden evaluator also exited `0`. After that, the owner adapter attempted
to map the model ledger to the task requirements and found no requirement lines
matching its exact grammar. The parser accepted only:

```text
- `REQ:...`: requirement statement
```

The private task used a typographic dash instead of the required colon. This
was an owner-authored contract mismatch. It occurred after submission and
before a terminal cell, sealed evidence packet, capture assessment, or frozen
truth record existed. The candidate and raw events are retained privately by
hash, but they cannot be promoted into a valid executor claim after the fact.

## Why qualification missed it

The deterministic task qualification exercised visible tests, hidden evaluator
acceptance, semantic mutants, evaluator repeat agreement, artifact hashes, and
task/dossier structure. The synthetic wrapper qualification exercised
versioned attempt, truth, submission, and terminal-assessment identities using
retained qualification truth. Neither executed the exact `TASK.md` parser used
by the live executor normalization path.

That was the missing edge:

```text
qualified task semantics
    ≠ exact executor-facing requirement syntax
    ≠ live owner normalization
```

The scored call exposed the gap. The method did the correct thing afterward:
the immutable journal preserved `prepared → submitted → ambiguous`, the stop
rule prevented later calls, and the public result did not convert absence into
a zero effect.

## Prospective repair

Current source now repairs the future process without changing v3 evidence:

1. semantic qualification parses the exact executor-facing `TASK.md` and
   requires its ordered requirement IDs to equal the dossier;
2. activation observations derive task identities and preserve submitted or
   ambiguous attempts instead of collapsing them to `unrun`;
3. a post-stop finalizer can normalize immutable journals but has no Codex,
   Docker, evaluator, retry, or overwrite capability;
4. the public materializer projects a submitted ambiguous attempt as an
   `invalid` Contract run with nonzero observed cost and hidden source hashes;
5. the auditor binds public task/run status to the frozen schedule and verifies
   every frozen code hash from the preregistration commit when Git proof is
   required.

These changes qualify only the repaired measurement path. A future observation
requires a new revision, new uncontaminated roots, new private pack and raw
root, new qualification receipt, new freeze, and new exact-SHA CI proof.
The exact frozen-versus-terminal source hashes and the zero-call normalization
operation are disclosed in
[`normalization-deviation.json`](../studies/completion-integrity/activation-v3/results/normalization-deviation.json).

## What the result supports

- The exact activation-v3 protocol did not complete.
- The first scored attempt became ambiguous after submission because the owner
  task syntax and owner parser contract differed.
- The prior task and wrapper qualifications did not cover the exact live
  normalization edge.
- The no-retry stop rule preserved the failure and prevented five further
  submissions.
- A public checkout can recompute the protocol-invalid decision from six
  normalized run records and 24 measurements.

## What the result does not support

- a `B0` versus `T1` effect or accuracy comparison;
- correctness or incorrectness of the ambiguous executor's implementation;
- Codex, `gpt-5.6-sol`, executor, or reporter reliability;
- transfer to another task population, model, harness, repository, or provider
  state;
- a larger Completion Integrity pilot, production adoption, or AEL-CEP
  retrospective rescore;
- independent reproduction.

## Public audit

```bash
uv run ael study audit \
  --freeze studies/completion-integrity/activation-v3/freeze.json \
  --result studies/completion-integrity/activation-v3/results \
  --decision-adapter completion-integrity-activation-v1 \
  --require-git-proof
```

The audit validates the Contract v0 graph, exact freeze and preregistration
ordering, frozen code bindings, the ambiguous-versus-unrun projection, all six
scheduled run states, 24 measurements, and the recomputed decision. It does not
reveal or replay private tasks, evaluators, candidates, events, authentication,
or hosted calls, and it is not independent replication.
