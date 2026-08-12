# Agent Skills Season 1 foundation calibration

Date: 2026-08-12

State: local mechanics calibration completed; third-party agent-effect runs not
started; repository changes uncommitted and unpublished.

> Historical foundation checkpoint. The maintainer subsequently accepted exact,
> reviewed, source-locked snapshots for controlled Codex execution and completed
> activation calibration. See the [activation report](2026-08-12-agent-skills-season-1-activation.md).

## Result

The Season 1 public foundation is executable:

- 12 exact upstream skill trees from four repositories resolved at the locked
  commits, matched their recorded tree hashes, and exposed the recorded license
  files and hashes;
- 10 Contract v0 study drafts and their local protocol/source/task-pack hashes
  validate;
- all 10 public fixtures passed visible smoke checks in the offline Docker
  runner;
- all 10 pristine fixtures failed their separate acceptance evaluators;
- the task-pack health decision is `healthy = true`.

The observed runner image was
`kizz/ael-runner:0.1.0-alpha.1` with local image ID
`sha256:4f136124c94206f2becf356de995094096cb04fe8a68bfaaa070f7b8f7a29f02`.
The machine-readable result is
[`task-pack-health.json`](../studies/agent-skills-season-1/calibration/task-pack-health.json).

## What this proves

The public source-lock verifier, task fixtures, Docker copy/export path, visible
checks, and separate evaluator mechanics operate for all ten planned study
shapes. Pristine inputs are discriminable at this small calibration layer.

## What this does not prove

No third-party skill was installed into a hosted agent run. No baseline versus
treatment comparison, activation measurement, screening estimate, hidden
confirmation, transfer result, independent replication, safety certification,
or leaderboard eligibility exists. The public tasks are small and known; their
health cannot be cited as evidence that any skill works.

## Blocking gate and next execution order

The hosted Codex process can read its reusable credential. Exact-host egress
allowlisting does not prevent encrypted exfiltration to an allowed host, so
third-party interventions remain blocked. Resume effect execution only after a
one-run revocable credential or out-of-process broker is proven.

When that gate passes, run activation calibration in this order:

1. truthful completion;
2. debugging tournament;
3. property-based testing.

Freeze harder, non-prescriptive screening tasks only after activation and
condition-equality evidence. Do not reuse these public mechanics tasks as
confirmation evidence.
