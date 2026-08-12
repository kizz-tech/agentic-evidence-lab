# Agent Skills Season 1 — first-wave screening boundary

State: one preregistered pathfinder; no effectiveness screening has run.

Activation calibration is the completed `v0.1.0-alpha.2` milestone. The
Property-based Testing v2 pilot now has private screening and confirmation
packs outside Git plus a public freeze that binds their digests, evaluator
boundary, budget, order, repeat rules, code, prompt, and stop rules. It was
frozen with zero scored calls.

## Scope

The first wave still contains the three studies marked `first_wave` in
`season.toml`, but calibration changed the execution order:

1. Property-based Testing v2 is the first frozen pathfinder.
2. Truthful completion returns to task design after two sacrificial prompt
   variants produced a baseline ceiling; no scored calls were made.
3. The debugging tournament remains the next distinct study after the
   pathfinder closes.

The PBT [analysis plan](property-based-testing-v2-analysis-plan.md),
[freeze](property-based-testing-v2.freeze.json), and immutable
[study-manifest revision 2](../manifests/property-based-testing-v2.study-manifest.json)
are the preregistration record. Private task and evaluator bytes remain outside
the repository.

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
