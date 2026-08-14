# Roadmap

## Mission

Agent progress should come from better systems as well as better models. AEL
exists to discover which exact skills, prompts, tools, context strategies,
models, runtimes, and workflows make an agent system more useful on a defined
class of work.

**AEL advances when it makes one real agent-stack decision more defensible.**

The research loop is:

```text
important question → exact comparison → bounded decision → real action
                   → observed outcome → next version or reversal
```

This roadmap describes research direction and evidence gates, not fixed
delivery dates. A negative or null result is progress when it prevents a weak
change from becoming the default.

## What users should get

Each mature study should produce:

1. one recognizable question about an agent-system change;
2. one clear decision: adopt, reject, narrow, or retest;
3. one exact tested artifact or reference configuration when publishable;
4. observed outcome, cost, failures, and reliability or an explicit statement
   that reliability was not established;
5. the task boundary and trigger that makes the decision stale;
6. a result card, machine-readable receipt, and audit or replication path.

The public result is the answer. The evidence machinery exists to make that
answer inspectable, not to replace it.

## Available

- Contract v0: five strict, hash-linked evidence document types for concepts,
  studies, runs, measurements, and receipts.
- Deterministic validation, receipt rendering, public result cards, frozen
  study audits, source locks, and release-artifact verification.
- Docker execution boundaries for disposable offline fixtures and a restricted
  hosted Codex adapter for exact maintainer-controlled inputs.
- Prospective pilot records for admission, effect, adoption, action, and
  follow-up without promoting those shapes into stable Contract v0.
- A pilot Study Quality Profile and `ael study preflight` for checking a study
  design before scored work.

## Next flagship question: Completion Integrity

> Can a coding agent reliably tell when the requested work is actually complete?

The user-facing outcome is a tested completion policy and routing rule, or an
honest result that the candidate did not improve false-completion behavior.
Final repository state and user-level acceptance remain primary; confident
prose is not success.

The existing Season 1 **Truthful Completion** protocol tests one pinned skill
and reached a baseline ceiling during sacrificial calibration. A future
prompt-only comparison must therefore use a distinct study identity and exact
intervention. Before any scored call, unscored calibration must demonstrate:

- non-zero baseline failure opportunity without making the hidden answer
  obvious;
- deterministic ownership of user-level completion and regression outcomes;
- an exact prompt or workflow delta rather than a theme-level intervention;
- task/evaluator audit, multiple declared strata, and a material decision the
  result can govern;
- blocked or randomized repeated execution, a paraphrase perturbation,
  retained failures, uncertainty, and an untouched confirmation subset.

If this discrimination gate fails, redesign or stop the study. Do not turn a
ceiling into an effectiveness result.

## Trust work that runs alongside the flagship study

1. Use the Study Quality Profile prospectively in the Completion Integrity
   study and one materially different study.
2. Complete the scheduled Systematic Debugging operational follow-up, recording
   an observed outcome or an explicit missing-observation state.
3. Reproduce one eligible decision with separated operator, task, or evaluator
   ownership; keep a maintainer rerun distinct from independent replication.
4. Exercise repeats, prompt perturbations, fault cases, correction,
   invalidation, and freshness before using stability language.
5. Test whether the public decision card helps a reader choose adopt, reject,
   narrow, or retest without mistaking incompatible studies for a leaderboard.

## Next intervention families

After the first prospective repeated study and one role-separated reproduction:

- evaluate one licensed third-party coding skill and publish a task-specific
  `use / skip / escalate` routing rule;
- compare model and scaffold only through a crossed design that can separate
  their individual and interaction effects;
- study repository instructions, context policies, and tool boundaries when a
  real owner decision and valid task supply exist;
- expand to durable project state and evidence-gated continual improvement only
  after the fixed protocol closes real decision and outcome loops.

A capability registry or contextual leaderboard becomes useful only after
enough compatible results exist to make discovery—not evidence quality—the
measured bottleneck.

## Default research cadence

The preferred cycle is:

```text
one serious decision question
+ one reusable answer or tested artifact
+ one improvement to trust, transfer, or outcome follow-up
```

Method-only releases are exceptions. They are justified when a known defect in
the instrument blocks the next important answer; method volume is not product
progress by itself.

## Beta evidence gates

AEL should not call its method beta until all of these are true:

- at least two prospective Study Quality Profiles completed a full
  preflight-to-receipt lifecycle;
- at least one result has role-separated or external reproduction evidence;
- task validity and evaluator calibration have been exercised on more than one
  study family;
- uncertainty and reliability outputs are generated from observed data rather
  than only declared plans;
- one real-shadow decision has a completed downstream follow-up;
- release, correction, invalidation, and freshness paths have each been tested;
- untrusted third-party execution either has short-lived brokered credentials
  or remains explicitly blocked.

## Deferred and non-goals

- No universal agent score or global model ranking.
- No claim that a system-level gain made the base model intrinsically smarter.
- No weighted study-quality grade that lets strengths compensate for a
  critical design failure.
- No retrospective quality certification of studies that predate the profile.
- No automatic execution of arbitrary third-party code with reusable hosted
  credentials.
- No stable sixth Contract object until repeated prospective use reveals a
  durable cross-study shape and an explicit migration decision is made.
- No hosted marketplace, generic eval dashboard, or automatic search platform
  before repeated external use demonstrates the need.
- No claim that structural conformance proves scientific validity, chronology
  of private model calls, transfer, independent replication, or production
  impact.

## How the roadmap changes

Roadmap changes should cite a completed study, external review, security
finding, repeated implementation need, or explicit owner decision. New ideas
can enter the research horizon without becoming active studies. Failed studies
can remove or reverse a direction; previous results remain immutable.
