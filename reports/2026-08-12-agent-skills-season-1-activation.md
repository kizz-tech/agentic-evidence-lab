# Agent Skills Season 1 activation calibration

Date: 2026-08-12

State: controlled activation calibration completed and included in the
`v0.1.0-alpha.2` evidence package; effectiveness screening, holdout
confirmation, and leaderboard publication are not completed. GitHub is the
authority for commit, CI, tag, and release state.

## Decision

The Season 1 runner and evidence pipeline are ready for discriminating study
design. Ten of twelve exact public-skill snapshots were installed and
explicitly read by Codex; those ten may advance as execution-compatible
candidates. Anthropic `mcp-builder` and `webapp-testing` were installed but not
read, so their activation is inconclusive and their tasks must be redesigned
before screening.

This calibration does **not** show that any skill improves code, debugging,
security, design, testing, cost, or latency. It produces no skill leaderboard.

## Executed surface

- Codex CLI `0.146.0`;
- `gpt-5.6-sol`, `xhigh` reasoning effort;
- controlled-egress Docker runner
  `sha256:f5ebad21373b16799a4bb0189d917856280cca8394c25967c95d612b6b61ac08`;
- proxy image
  `sha256:69a5e44397a2e752507076cf12b30b7609c47711bd6d3f342c612dba7d968e35`;
- ten public maintainer-authored mechanics tasks;
- ten baseline cells and twelve treatment cells;
- one non-randomized repeat per condition;
- deterministic post-run evaluator kept outside the agent workspace.

The final public evidence package contains 22 run records, ten measurement
sets, and ten evidence receipts. The [activation matrix](../studies/agent-skills-season-1/calibration/runtime-v1/README.md)
reports acceptance, explicit skill reads, generated-work tokens, and wall time
per condition.

## Activation outcome

| Study | Treatment snapshots | Explicitly read | Calibration decision |
| --- | ---: | ---: | --- |
| Truthful completion | 1 | 1 | Advance to screening design |
| Debugging tournament | 2 | 2 | Advance both snapshots |
| Test-driven development | 1 | 1 | Advance; add process telemetry |
| Property-based testing | 1 | 1 | Advance to screening design |
| Differential security review | 1 | 1 | Advance to security-specific screening |
| Review-team topology | 1 | 1 | Advance raw snapshot; topology conformance still unproved |
| MCP server construction | 1 | 0 | Inconclusive; redesign activation task |
| Web application testing | 1 | 0 | Inconclusive; require browser-backed task |
| Frontend design | 1 | 1 | Advance to blinded evaluation design |
| Recursive skill improvement | 2 | 2 | Advance raw snapshots; freeze optional dependency policy |

All 22 final-revision candidates reached a normal runner terminal state. The
deterministic calibration evaluator accepted every final-revision candidate.
That shared acceptance is a mechanics result and likely includes substantial
ceiling contamination; it is not equivalence or no-effect evidence.

## Benchmark defects found and retained

Activation exposed two defects that static health checks did not catch:

1. Truthful-completion revision 1 asked for a failure reason but did not define
   the evaluator-required `blocked:` prefix. Baseline and treatment both used
   the reasonable `failed:` prefix. Those two cells are invalid, retained, and
   excluded from the 22 final records.
2. Frontend-design revision 2 treated the XML namespace inside an inline
   `data:` SVG as an external network resource. The apparent baseline failure
   was an evaluator false positive. Both cells are retained as invalid; the
   evaluator now checks remote resource-bearing attributes and CSS URLs, and
   both conditions were rerun under revision 3.

The [revision 1](../studies/agent-skills-season-1/calibration/revision-1/INVALIDATION.md)
and [revision 2](../studies/agent-skills-season-1/calibration/revision-2/INVALIDATION.md)
records publish the defect explanation and hashes of all four retained private
run/evaluation trees. Nothing was silently deleted or relabelled as a retry.

## Descriptive cost signal

Single-run token and latency values are retained to calibrate later budgets,
not to rank skills. Several treatments were materially heavier: the TDD cell
and the review-team cell used much more generated work than their baselines.
Property-based testing was close to its baseline. These observations justify a
matched total-system budget and repeated cells; they do not estimate stable
cost overhead.

## Credential and source boundary

The Codex process could read the maintainer's reusable ChatGPT credential. The
owner explicitly accepted this normal local-runtime property for the exact
source-locked snapshots in this study. Inputs were maintainer-controlled,
source trees were pinned and reviewed, canonical fixtures were mounted
read-only, execution used disposable Docker workspaces, outbound destinations
were constrained to the OpenAI path, and persisted outputs were exact-value
scanned.

This does not make the runner safe for arbitrary public submissions. A newly
submitted or changed skill remains blocked until it is separately pinned,
reviewed, and explicitly accepted; a one-run credential or out-of-process
broker would still provide a stronger public-service boundary.

## What is supported

- exact source provenance and snapshot identity for twelve public skills;
- controlled Codex execution and deterministic evaluation for 22 final cells;
- fixture preservation and absence of exact credential values in persisted
  output scans;
- explicit `SKILL.md` reads for ten of twelve treatments;
- activation-inconclusive status for MCP-builder and webapp-testing;
- reproducible public mechanics-pack health under revision 4;
- a machine-readable evidence receipt for every study.

## What remains unsupported

- any skill-effect, model-effect, or whole-stack superiority claim;
- a universal, cross-study, or Season 1 leaderboard;
- equivalence from shared acceptance;
- stable token, latency, or cost overhead;
- transfer to real repositories, other models, Claude Code, Cursor, or a raw
  model API;
- full execution of Every's intended review-team topology merely because the
  root skill was read;
- real-browser benefit from the webapp-testing skill;
- safety for arbitrary third-party submissions or encrypted-traffic inspection;
- downstream product, production, or user outcomes.

## Next experiment gate

Do not increase repeats on the public calibration tasks. The next work is:

1. build non-prescriptive hidden screening packs for truthful completion,
   debugging, and property-based testing;
2. freeze primary endpoints, critical-failure rules, randomized order, matched
   total-system budget, repeat count, and uncertainty method before execution;
3. select one finalist per frozen rule or reject all candidates;
4. evaluate finalists once on untouched confirmation tasks;
5. publish contextual result cards and a leaderboard only inside a single
   frozen study contract with enough repeated evidence.

MCP-builder and webapp-testing activation redesign belongs to those later-wave
study milestones and does not block the three-study first wave.
