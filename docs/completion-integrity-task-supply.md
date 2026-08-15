# Completion Integrity task supply

Completion Integrity Task Pack v2 is a prospective instrument-development
program. It is not a larger alpha.9 pack, a public benchmark release, or a
promise that a chosen number of tasks already exists.

## Decision question

The program asks whether a coding agent truthfully reconciles the owner-level
final state before declaring work complete, incomplete, or blocked. A useful
task therefore contains a plausible stopping trap: visible local progress can
look complete while at least one observable owner requirement remains unmet.
The task must reward final-state reconciliation, not guessing a secret test.

Historical alpha.9 tasks remain frozen evidence and regression anchors. They do
not become fresh screening or confirmation roots in v2.

## Population plan

The private authoring inventory may seek a broad candidate pool and use an
initial `16–24` range for capacity planning. Those values are not method
constants, a power result, or evidence that such a population exists.

Every pack revision owns a `sample_size_plan`. During development it may be
`pending_pilot`, but it must name the missing inputs and cannot reach
`admission_ready` or `frozen`. An admitted plan must bind one of:

- a power rationale: test, alpha, power, minimum useful effect, pilot
  discordance and clustering/design effect; or
- a precision rationale: confidence level, target interval width, pilot
  discordance and clustering/design effect.

Both routes bind the estimand, endpoint/test, allocation, independent and
clustering unit, exclusion policy, calculation revision/hash, stopping rule,
and pack-specific minimum/target. The policy validates those declarations; it
does not invent missing assumptions or implement a universal power calculator.
Repeats, paraphrases, language ports, calibration cases and parameter variants
never increase independent `n`.

The desired coverage is four families:

| Family | Candidate strata | Construct contribution |
| --- | --- | --- |
| Requirement closure | explicit multipart; repository-inferable contract | Detect premature closure over requirements the agent could actually observe. |
| Cross-boundary coherence | code/schema/docs/generated sync; compatibility/migration | Detect a focal code success that leaves another owner surface inconsistent. |
| Verification integrity | focal fix with regression; misleading green checks | Detect acceptance claims based on insufficient or non-owner evidence. |
| Delivery and authority integrity | legitimate external blocker; implemented vs packaged/published/delivered | Detect invented authority and conflation of implementation with external state. |

At least Python and TypeScript must be represented in an admitted pack.
Ecosystem is blocked or reported in analysis; it is not silently pooled away.
Iterative-extension and multi-package tasks are secondary diagnostic strata
until they show that long horizon does not overwhelm the narrower construct.

## Non-compensating admission gates

Every candidate must pass all of these gates. There is no weighted quality
score.

1. **Observable contract.** Every requirement is instruction-explicit,
   repository-inferable, or explicit on a named owner surface available to the
   agent. Hidden evaluators may verify that contract but may not invent it.
2. **Exact coverage.** Requirement IDs and executable oracle coverage match
   exactly.
3. **Alternative validity.** The oracle accepts at least two structurally
   different valid solutions where the task permits implementation choice.
4. **Semantic challenge.** It rejects operationally valid partial omission,
   narrow overfit, collateral regression, fabricated authority and reward-hack
   mutants. At least one rejected omission/overfit mutant still passes visible
   checks, demonstrating the intended stopping trap.
5. **Environment validity.** Pristine, known-good and invalid states are
   distinguished, and deterministic evaluation repeats agree.
6. **Root independence.** A scored root has unique repository graph,
   acceptance-owner identity, failure-mechanism identity and lineage group.
7. **Qualification.** Sacrificial attempts and semantic review occur before a
   scored role is assigned. Repair after the last attempt creates a new task
   revision.
8. **Confirmation hygiene.** Confirmation roots are untouched by adaptation
   and are estimated separately from screening.
9. **Terminal truth.** A hash-bound evaluator oracle discriminates
   `complete`, `incomplete`, and `uncertain`; truth is separate from progress
   (`continuable`, `awaiting_clarification`, `externally_blocked`) and from the
   verified/failed/unresolved extent.
10. **Blocker feasibility.** External blockage requires a named unavailable
    prerequisite/owner, evidence, exhaustion of authorized in-scope
    alternatives, and a feasible next action. False-blocker cases retain a
    demonstrably feasible in-scope alternative.
11. **Evaluator custody.** The dossier binds evaluator and custody-receipt
    hashes, discloses author overlap, and denies reporter pre-score access.
12. **Sample-size readiness.** Pack-specific counts are justified and
    hash-bound before admission; `pending_pilot` cannot be relabelled as ready.
13. **Privacy and safety.** Exact active instruction, fixture, evaluator,
   solution, mutant and canary bytes stay outside Git. Every artifact is bound
   by SHA-256; symlinks, traversal and special files fail closed.

Differential tests may reveal a behavioral discrepancy between solutions, but
the discrepancy is diagnostic evidence, not automatic proof that one solution
is wrong.

## Lifecycle

```text
author candidate roots (`lifecycle_state=authoring`, `study_role=none`)
  → deterministic oracle/environment challenge
  → alternative-solution and semantic-mutant challenge
  → semantic task audit
  → sacrificial agent qualification
  → `qualified`
  → assign fresh screening or untouched confirmation `study_role`
  → `role_assigned`
  → freeze exact bytes, roles, schedule, estimand, pooling and stopping
  → `frozen`
  → separately execute and estimate screening then confirmation
  → `retired` or disclose without rewriting the frozen revision
```

Development is adaptive. Qualification is sacrificial. Scored screening is
frozen. Confirmation is untouched. A failure in one stage cannot be relabelled
as evidence from another stage.

## Difficulty profile

`compact`, `medium`, and `deep` are author forecasts only. The program records
orthogonal observations when available:

- relevant human completion time;
- repository/file/package breadth;
- action and tool-use count;
- qualified agent success distribution;
- empirical task discrimination;
- failure severity and mechanism.

No line-count threshold decides admission. A difficult task with broken
dependencies, missing context, arbitrary hidden expectations or insufficient
budget is invalid rather than valuable.

## Executable contract

`ael.completion_integrity_task_supply` owns the pure non-compensating
`0.2-development` policy. Lifecycle state and study role are separate; a
qualification receipt is not an experimental role.
`tools/check_completion_integrity_task_supply.py` is the strict private-pack
adapter. The adapter verifies safe paths, exact artifact hashes, private/public
separation and strict JSON, then passes normalized facts to the policy. Artifact
kinds and paths are unique within a dossier, so custody cannot silently bind a
different duplicate. Generated assessments must be written outside the
immutable pack root; otherwise their own bytes would change the pack digest.

The contract is family-local and explicitly marked `development`. It is not a
sixth Contract v0 object, a generic task registry, or a stable cross-benchmark
schema. Promotion requires repeated use outside Completion Integrity.

Example operator command, before any scored run:

```bash
uv run python tools/check_completion_integrity_task_supply.py \
  /absolute/private/completion-integrity-v2-development \
  --public-root /absolute/public/agentic-evidence-lab \
  --json-output /absolute/private/task-supply-assessment.json
```

The generated assessment may report development progress. It cannot prove
task quality without the bound private artifacts, cannot authorize model calls,
and cannot promote a pack to `admission_ready` merely by changing a label.

## Evidence boundary

The design is informed by repository-repair oracle audits, program-variant
test augmentation, design-constraint evaluation, human-calibrated task QA,
iterative coding benchmarks, long-horizon task research and existing Harbor
task structure. Those sources justify the gates; they do not validate AEL's
future task bytes.

The next admissible public evidence is a bounded task-supply receipt containing
only identities, roles, strata, ecosystem counts, artifact hashes, audit state
and the exact checker version. It must not contain active task, evaluator,
reference, mutant, authentication, raw-attempt or personal-path bytes.
