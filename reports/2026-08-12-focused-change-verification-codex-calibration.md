# Codex calibration: the runner works; the first skill pack is too easy

Date: 2026-08-12

State: six-cell maintainer calibration completed; 18-cell adaptation study not run

Decision: keep the current pack as a smoke test and design more discriminating tasks

Evidence level: runtime conformant, maintainer evaluated

## Answer first

The AEL runner successfully executed the same Codex stack with and without the
Focused Change Verification skill, loaded the treatment correctly, preserved
the canonical fixtures, and evaluated all six exported workspaces.

It did **not** demonstrate that the skill improves code quality. Baseline and
treatment both passed all three tasks because the task prompts already asked
for much of the verification behavior the skill was meant to contribute.

| Decision question | Answer |
| --- | --- |
| Does the hosted runner work for this controlled calibration? | Yes, within the documented maintainer-controlled credential boundary. |
| Did the skill load in treatment runs? | Yes, in all three treatment cells and none of the baseline cells. |
| Did the skill improve deterministic task acceptance? | No demonstrated difference; baseline and treatment both passed 3/3. |
| Can the current pack estimate the skill's effect? | No. Its prompts contaminate the contrast and create a ceiling. |

## Should I use the skill?

This calibration cannot decide that. It is evidence about runner operation and
treatment activation, not evidence of a correctness or code-quality advantage.
Keep the current tasks as a fast operational smoke surface. Evaluate the skill
again only after freezing tasks that request product behavior without revealing
the verification route being tested.

## What was tested

The measured stack was Codex CLI 0.146.0, `gpt-5.6-sol`, `xhigh`, the same fixed
task prompt, the same Docker/proxy images, and one repeat for each task-condition
cell. The only intended condition difference was installation of the frozen
`focused-change-verification` skill.

The three public tasks covered local unit behavior, a shared cross-module
contract, and a populated SQLite migration. This was a runner calibration, not
a confirmatory effect study.

## Result

| Task stratum | Baseline acceptance | Skill acceptance | Skill activated |
| --- | ---: | ---: | ---: |
| Local unit change | pass | pass | yes |
| Cross-module contract | pass | pass | yes |
| Populated SQLite migration | pass | pass | yes |

All six stable cells passed visible tests and their separately mounted hidden
acceptance evaluator. The skill was explicitly read in all three treatment
traces and never installed in baseline. Every before/after canonical fixture
hash matched.

The observed aggregate cost was descriptive only:

| Condition | Accepted tasks | Generated-work tokens | Wall time |
| --- | ---: | ---: | ---: |
| S0 baseline | 3/3 | 20,256 | 331,689 ms |
| S1 skill | 3/3 | 21,944 | 378,385 ms |

Treatment used 1,688 more output-plus-reasoning tokens, about 8.3%, and 46,696
more milliseconds, about 14.1%, in this single non-randomized calibration.
Those differences are not stable cost estimates.

## What the calibration found

The infrastructure is usable. It caught and repaired two real defects before
the stable cells:

1. Codex's inner `bwrap` sandbox could not create a namespace inside the already
   restricted container. The final runner disables the inner sandbox and keeps
   the outer Docker boundary as the enforcement layer.
2. The first Alpine image could not execute Codex's bundled `rg`. The final
   image uses a pinned Debian slim base; the stable cells have no corresponding
   tool failure.

The experiment design is not yet discriminating. The public tasks explicitly
tell the agent to validate the owner-local change, the direct consumer, or the
disposable migration state. Those are the very routing decisions the skill is
supposed to contribute. A strong baseline therefore receives much of the
treatment in the task prompt and reaches a three-of-three ceiling.

Treatment final answers more consistently separated `implemented`, `locally
validated`, `committed`, `pushed`, `deployed`, and `outcome-proven` state.
Baseline answers more often collapsed that into “complete.” This is a useful
hypothesis, not a scored effect: no blinded state-reporting rubric was frozen
before these outputs were read.

## Decision and next test

Keep the current three tasks as a fast operational smoke. Do not run the
remaining twelve repeats under the frozen 18-cell plan: more samples of a
ceiling-limited, treatment-contaminated pack would create volume rather than
evidence.

Before estimating a skill effect:

- freeze a new pack whose prompts describe the desired product change without
  naming the verification route;
- preregister critical-omission and state-truth reporting rubrics;
- randomize run order;
- retain a negative-control task where extra verification is unnecessary;
- preserve a failed or null pilot instead of replacing tasks after viewing
  treatment outputs.

The detailed requirements are in the
[discriminating task-pack brief](../studies/focused-change-verification/discriminating-pack-brief.md).

## Credential and network boundary

The agent container had no direct public route. A CONNECT-only sidecar allowed
exactly `api.openai.com`, `auth.openai.com`, and `chatgpt.com`; an egress smoke
reached the allowed API endpoint, blocked `example.com`, and blocked direct
public-IP access. Optional storage and analytics hosts requested by Codex stayed
blocked without preventing task completion.

Only one explicitly selected auth file was mounted read-only and copied into an
ephemeral home that was not exported. Four later cells recorded an automatic
exact-value output scan; an operator scan across all 186 retained runtime-v2
files found no exact value from the credential file. This does not prove that a
credential could not be sent inside encrypted traffic. The agent process could
read the credential, so this path is not safe for untrusted third-party skills
or tasks.

A safer credential mechanism is required before evaluating third-party
content.

## Evidence

- [Machine-readable calibration receipt](../examples/coding-skill/calibration-v1/evidence-receipt.json)
- [Study manifest](../examples/coding-skill/study-manifest.json)
- [Individual run records](../examples/coding-skill/calibration-v1/runs)
- [Measurement set](../examples/coding-skill/calibration-v1/measurement-set.json)

Raw Codex events, candidate workspaces, evaluator output, and proxy logs remain
private and ignored by Git.

## Unsupported conclusions

- The skill does not yet have a demonstrated correctness or code-quality win.
- Three passes per condition do not establish equivalence.
- No result here compares Codex with Claude Code, Cursor, another CLI, or a bare
  model.
- No transfer to real repositories, production outcomes, or third-party skills
  was measured.
- The current reusable-credential design is not a security boundary for hostile
  content.
