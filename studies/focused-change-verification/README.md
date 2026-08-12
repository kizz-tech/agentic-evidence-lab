# Focused Change Verification study

State: intervention and public adaptation pack frozen; six-cell hosted Codex
runner calibration completed; planned 18-cell adaptation comparison unrun.

The study compares one exact installable Codex skill with the same coding-agent
configuration without that skill. It is the first non-Council transfer of the
AEL evidence contract toward completed deterministic repository outcomes.

Current evidence:

- the skill package passes the official Codex skill validator;
- its two-file tree is content-addressed by `artifact.toml`;
- three adaptation fixtures cover local unit behavior, a shared contract, and a
  populated SQLite migration;
- every pristine fixture passes its visible tests and fails its separate
  acceptance evaluator inside the offline Docker runner;
- evaluators are not mounted during an agent run;
- the exact 18-cell adaptation analysis is frozen.

One non-randomized calibration repeat per task and condition ran on Codex CLI
0.146.0 with `gpt-5.6-sol` at `xhigh`. All six candidates passed their separate
acceptance evaluator, and the skill was explicitly read in all three treatment
cells. That is runner and activation evidence, not evidence that the skill
improves implementation correctness.

The calibration also exposed a design problem: every public task prompt already
asks for much of the verification behavior contributed by the skill. Baseline
therefore reached a three-of-three acceptance ceiling. The planned 18 cells are
paused; repeating this pack would spend budget without a credible primary
contrast. The next pack must request the product change without prescribing the
owner-layer checks being evaluated.

The hosted path uses an explicitly selected reusable ChatGPT credential. It is
not copied into the repository or public evidence, and persisted outputs are
exact-value scanned. Because the Codex process and generated shell commands can
still read it inside the container, the path is approved only for
maintainer-controlled fixtures and skills—not third-party submissions.

Files:

- [`artifact.toml`](artifact.toml) — frozen skill identity;
- [`analysis-plan.md`](analysis-plan.md) — comparison and decision rules;
- [`task-pack/adaptation-v1/task-pack.toml`](task-pack/adaptation-v1/task-pack.toml)
  — frozen public adaptation pack;
- [`../../examples/coding-skill/study-manifest.json`](../../examples/coding-skill/study-manifest.json)
  — Contract v0 study manifest.
- [`../../examples/coding-skill/calibration-v1/evidence-receipt.json`](../../examples/coding-skill/calibration-v1/evidence-receipt.json)
  — bounded machine-readable calibration decision.
- [`discriminating-pack-brief.md`](discriminating-pack-brief.md) — requirements
  for the next task pack before repeated comparison.
