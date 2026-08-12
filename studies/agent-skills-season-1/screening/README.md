# Agent Skills Season 1 — first-wave screening boundary

State: public design contract; private task packs do not yet exist and no
effectiveness screening has run.

Activation calibration is the completed `v0.1.0-alpha.2` milestone. Screening
is a separate experiment and begins only after its private inputs, evaluator,
budget, order, repeat rule, and stop rule are frozen.

## Scope

The first wave contains only the three studies already marked `first_wave` in
`season.toml`, in this order:

1. truthful completion;
2. debugging tournament;
3. property-based testing.

MCP construction and webapp testing retain their activation-inconclusive
receipts. They do not block the first wave and will be redesigned in their own
later milestones. The other five studies remain protocol drafts.

## Physical boundary

Screening and confirmation are two operator-owned roots outside this Git
worktree. They are not subdirectories of `artifacts/private`, and they are
never mounted together.

```text
external screening root
  → read-only fixture mount
  → private run and evaluator output
  → allowlisted public evidence materializer
  → opaque hashes, run records, measurements, receipt

external confirmation root
  → unavailable during screening
  → unlocked only by a hash-bound finalist-selection record
  → same allowlisted public evidence flow
```

Every private pack contains a unique marker beginning with the private canary
prefix documented in the architecture. The public release check rejects that
prefix. This is an accidental-publication sentinel, not an access-control
mechanism.

## Freeze gate

Before the first scored call for a study, freeze and content-address:

- a new immutable study-manifest revision; revision 1 remains the activation
  contract and is never overwritten;
- baseline and treatment identities, with an exact condition delta;
- task-pack composite, evaluator composite, non-revealing public task IDs, and
  contamination review;
- primary endpoint, critical-failure gates, exclusions, invalid-run and retry
  policy;
- model, Codex version, image digests, prompt, tool and permission surface;
- per-cell limits, total study budget, randomized order, repeat count, and
  uncertainty method;
- finalist selection or reject-all rule;
- confirmation pack digest, held inaccessible until finalist freeze.

The evidence validator resolves versioned studies by `(study_id, revision)`.
Multiple revisions may coexist; duplicate identical revisions fail validation.

## Pilot and stop rules

Run one matched screening pass per frozen task before expanding repeats. Stop
the study and publish an inconclusive or rejected result when any of these
occurs:

- the treatment does not activate;
- all conditions hit a ceiling and the behavioral endpoint cannot distinguish
  them;
- task/evaluator integrity fails or a second behavior-changing repair would be
  required;
- the fixed total budget is exhausted;
- condition equality or hidden/public separation cannot be demonstrated.

Invalid cells are retained. A failed holdout cannot promote a runner-up, and
no task, evaluator, candidate, or decision threshold changes after confirmation
is opened.

## Release boundary

No universal or cross-study leaderboard follows from this wave. A contextual
board becomes eligible only inside one frozen study contract after repeated
observations, prespecified uncertainty, critical-failure disclosure, and a
completed confirmation and factual-correction pass.
