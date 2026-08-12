# Do Agent Skills Actually Work? — Season 1

State: ten protocols drafted, twelve exact upstream source trees verified, and
22 public activation cells represented by ten evidence receipts. Ten treatment
skills were explicitly read; MCP-builder and webapp-testing were injected but
did not activate. No effectiveness result or leaderboard is claimed. See the
[activation report](../../reports/2026-08-12-agent-skills-season-1-activation.md)
and [machine-readable matrix](calibration/runtime-v1/README.md).

Season 1 turns the broad question “do agent skills work?” into ten bounded
decisions. Each study has its own endpoint, failure taxonomy, task strata, and
claim boundary. They share provenance, condition controls, sandbox policy, run
records, and evidence receipts—not a universal score.

## The ten studies

| # | Study | Candidate intervention | Primary question | First wave |
| --- | --- | --- | --- | --- |
| 1 | [Truthful completion](protocols/01-truthful-completion.md) | Superpowers verification-before-completion | Does the skill reduce unsupported success claims after coding work? | Yes |
| 2 | [Debugging tournament](protocols/02-debugging-tournament.md) | Superpowers systematic-debugging; Every ce-debug | Which exact workflow most often repairs the real root cause without symptom patches? | Yes |
| 3 | [Test-driven development](protocols/03-test-driven-development.md) | Superpowers test-driven-development | Does the skill change test-first behavior and reduce regressions? | Later |
| 4 | [Property-based testing](protocols/04-property-based-testing.md) | Trail of Bits property-based-testing | Does the skill expose edge-case defects missed by example tests? | Yes |
| 5 | [Differential security review](protocols/05-differential-security-review.md) | Trail of Bits differential-review | Does the skill improve critical regression recall without unusable noise? | Later |
| 6 | [Review-team topology](protocols/06-review-team-topology.md) | Every ce-code-review | Does a bounded review team find more actionable defects than one strong reviewer at matched total budget? | Later |
| 7 | [MCP server construction](protocols/07-mcp-server-construction.md) | Anthropic mcp-builder | Does the skill improve protocol conformance and tool usability? | Later |
| 8 | [Webapp testing](protocols/08-webapp-testing.md) | Anthropic webapp-testing | Does the skill find and reproduce user-visible failures more reliably? | Later |
| 9 | [Frontend design](protocols/09-frontend-design.md) | Anthropic frontend-design | Does it improve blinded preference while preserving accessibility and task success? | Later |
| 10 | [Recursive skill improvement](protocols/10-recursive-skill-improvement.md) | Anthropic skill-creator; Trail of Bits skill-improver | Does an improvement loop raise held-out task performance without overfitting or new failures? | Later |

## Common experiment sequence

```text
source lock → activation calibration → matched screening → finalist freeze
            → hidden confirmation → receipt → bounded result card
```

Every comparison holds the task revision, base context, runtime, model, effort,
permissions, tool surface, budget policy, and evaluator fixed unless the study
explicitly names a whole-stack comparison. Baseline is mandatory. An
equal-context placebo is included only when a real context-volume or attention
confound needs to be controlled.

The public calibration tasks prove that fixtures are runnable and evaluators
can reject pristine inputs. They are not effectiveness evidence. Screening and
confirmation require new tasks whose target behavior is not prescribed by the
prompt; the earlier Focused Change Verification calibration demonstrated why
that separation matters.

## Source and execution boundary

[`sources.lock.toml`](sources.lock.toml) records exact repository commits,
repository-relative skill paths, AEL tree hashes, observed upstream license
locations, and execution gates. AEL does not vendor those source trees or call
the license observation a legal compliance opinion. Operators provide a Git
checkout and verify it without executing source-controlled code:

```bash
uv run ael source-lock check studies/agent-skills-season-1/sources.lock.toml
uv run ael source-lock verify studies/agent-skills-season-1/sources.lock.toml \
  --source-id superpowers-verification \
  --checkout /path/to/superpowers
```

The hosted Codex adapter exposes a reusable credential to the agent process.
For this maintainer-run study, the owner explicitly accepted that boundary for
exact source-locked snapshots after local review; those entries are
`hosted_model_execution = "maintainer_controlled_only"`. This is not a public
submission lane. Arbitrary or newly changed third-party content remains blocked
until it is separately pinned, reviewed, and accepted—or a stronger one-run
credential or broker boundary exists.

## Public calibration

The single calibration pack contains one mechanics task for each study. Check
all ten in the pinned offline runner:

```bash
uv run ael sandbox build --context docker/runner
output=$(mktemp -d)
uv run ael taskpack check-adaptation \
  studies/agent-skills-season-1/task-pack/calibration-v1 \
  --output "$output"
```

The expected health rule is: every pristine fixture passes its visible smoke
tests and fails its separate acceptance evaluator. Evaluators are never mounted
during an agent run.

## Publication and leaderboard state

- Activation calibration is executed evidence about runner compatibility,
  deterministic acceptance, explicit skill reads, usage, and latency only.
- Ten of twelve treatment snapshots activated. MCP-builder and webapp-testing
  remain activation-inconclusive because Codex never read their `SKILL.md`.
- Two invalidated benchmark revisions are retained: one underdetermined task
  contract and one evaluator false positive.
- Negative and inconclusive outcomes will be retained.
- Results remain separate study cards until one frozen contract has multiple
  eligible candidates, repeated observations, uncertainty, and no unresolved
  integrity or publication-rights issue.
- There will be no “best skill overall” board.

Vercel's public `agent-skills` repository was inspected as a possible source but
is not included in Season 1 because an applicable license grant was not located
at the pinned repository revision. That is an inclusion gate, not a quality
judgment.
