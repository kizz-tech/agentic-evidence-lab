# Reproducibility

Reproducibility has separate operations. **Graph verification** checks the
hash-linked public records and deterministic projections. A **rerun** executes
the declared protocol again when its inputs are available. **Independent
replication** adds a new executor and role-separated evidence production. None
of these operations implies either of the others, and stochastic model
behavior is not expected to be byte-identical.

## Graph verification: deterministic public checks

From a clean checkout of the exact alpha.7 source revision under review:

```bash
uv sync --locked --all-groups
uv run ruff check .
uv run ruff format --check .
uv run python -m unittest discover -s tests -v
uv run ael validate examples
uv run ael study preflight \
  studies/quality-preflight/examples/pass/quality-profile.json \
  --json-output studies/quality-preflight/examples/pass/preflight.json \
  --markdown-output studies/quality-preflight/examples/pass/preflight.md \
  --check
uv run ael source-lock check studies/agent-skills-season-1/sources.lock.toml
uv run ael study audit \
  --freeze studies/agent-skills-season-1/screening/property-based-testing-v2.freeze.json \
  --result studies/agent-skills-season-1/results/property-based-testing-v2 \
  --decision-adapter pbt-v2 \
  --require-git-proof
uv run ael study audit \
  --freeze studies/agent-skills-season-1/screening/systematic-debugging-real-shadow.freeze.json \
  --result studies/agent-skills-season-1/results/systematic-debugging-real-shadow-v1 \
  --decision-adapter systematic-debugging-real-shadow-v1 \
  --require-git-proof
uv run ael validate \
  studies/agent-skills-season-1/concept.json \
  studies/agent-skills-season-1/manifests \
  studies/agent-skills-season-1/calibration/runtime-v1
uv run python tools/materialize_agent_skills_season.py --check
uv run ael results check studies/public-results.json --require-git-proof
uv run python tools/check_frozen_artifacts.py
uv run python tools/release_check.py
uv build
uv run python tools/verify_release_artifacts.py \
  --expected-version 0.1.0a7 dist/*.whl dist/*.tar.gz
```

These checks establish package, schema, cross-reference, committed-fixture,
rendering, simulation, generated-publication, and public-tree consistency. They
verify the published evidence graph; they do not establish that an experimental
conclusion is true outside its receipt scope.

The public Season 1 activation evidence is reproducible from retained private
run inputs only by the maintainer. Public consumers can validate every exposed
document, source lock, and content hash, but cannot reconstruct private Codex
events from their hashes. This is verification of the published evidence graph,
not a historical model-call rerun or independent reproduction of the
hosted-agent executions.

## Frozen study-bundle audit

`ael study audit` is the fail-closed verifier for a completed frozen study. It
checks the freeze contract; exact terminal-decision alias; freeze, private-pack,
and decision hashes; Contract v0 references; terminal schedule coverage; and
receipt coverage. A study-specific decision adapter can additionally reconstruct
decision counts and the terminal outcome from public run and measurement
records instead of trusting the published aggregate. The current adapter is
explicitly named `pbt-v2`; omitting it leaves those semantic checks unclaimed.

With `--require-git-proof`, the audit requires the preregistration commit to be
an ancestor of the checkout, requires that commit to contain the exact current
freeze bytes, and requires the terminal decision to be absent from that commit.
Optional `--screening-root` and `--confirmation-root` arguments verify retained
private task-pack bytes against their frozen tree digests without publishing
them. `--json-output` writes a machine-readable audit summary.

This Git proof is limited to repository artifact ordering. A tag or ancestor
does not prove that private model calls occurred before results, and it does not
reconstruct private events or establish independent replication.

The private observation payload remains opaque. The audit checks its published
hash and, with the explicit adapter, recomputes the exposed counts and outcome;
it cannot reconstruct hidden task or event bytes that were not published.

The `systematic-debugging-real-shadow-v1` adapter additionally verifies the
prospective admission-to-action chain and reconstructs the terminal effect from
80 public measurements rather than trusting the aggregate decision. It also
verifies the disclosed one-field projection repair by reconstructing the
original invalid receipt bytes. That repair occurred after scored work and did
not change observations or the effect decision; it is not represented as
preregistered analysis.

For future Codex runs, `ael study activation-check` accepts Codex JSONL events
and counts activation only when a completed, exit-zero command retrieved
non-empty content from the exact installed `SKILL.md`. A path mentioned in an
agent message, an in-progress command, a failed command, or empty output is not
activation evidence. This stricter parser does not rewrite historical records.

## Receipt and projection reproduction

```bash
uv run ael render \
  examples/council-generation-1/evidence-receipt.json \
  --output /tmp/receipt.md
diff -u examples/council-generation-1/evidence-receipt.md /tmp/receipt.md
```

Every receipt binds its concept, study, runs, and measurements by SHA-256.
`ael validate` resolves relative public references and checks those hashes.
The generated [Results Index](../RESULTS.md) and machine index are deterministic
projections over those validated references; regeneration does not change the
underlying receipt or its authority.

To regenerate intentionally, use:

```bash
uv run ael results build studies/public-results.json --require-git-proof
```

Review the generated diff, then run the corresponding `results check` command.

## Calibration reproduction

```bash
uv run ael calibrate \
  studies/council-generation-2/calibration/calibration-config.json \
  --output /tmp/calibration-result.json \
  --report /tmp/calibration-report.md
diff -u studies/council-generation-2/calibration/calibration-result.json \
  /tmp/calibration-result.json
diff -u studies/council-generation-2/calibration/calibration-report.md \
  /tmp/calibration-report.md
```

The simulation is deterministic because the configuration pins its seed and
the result records a versioned SplitMix64 PRNG seeded from SHA-256. Discrete
paired outcomes are aggregated as integers, so the result does not depend on
Python's cross-version behavior for `random.choice`, `random.gauss`, or
floating-point `sum`.

## Container reproduction

Docker builds pin base-image digests. Invocation records capture the locally
resolved image ID, fixture tree hash, limits, network policy, and exit state.
Tag names alone are not sufficient evidence.

Hosted-model repetitions can differ even when the exposed model name, CLI,
prompt, and budget are fixed. Preserve each run as a separate observation,
record exposed provider/runtime identity, and do not retry poor answers as if
they were operational failures.

## Rerun versus independent replication

The exact PBT v2 graph-verification command is the audit command shown above:

```bash
uv run ael study audit \
  --freeze studies/agent-skills-season-1/screening/property-based-testing-v2.freeze.json \
  --result studies/agent-skills-season-1/results/property-based-testing-v2 \
  --decision-adapter pbt-v2 \
  --require-git-proof
```

It recomputes the exposed counts and checks the hash-linked bundle; it does not
rerun the private model calls. A historical PBT v2 rerun has no public command
in alpha.5 because its task packs, raw Codex events, candidate workspaces, and
evaluator outputs are withheld. Do not label the audit, receipt rendering, or
projection regeneration as a rerun.

An independent replication requires a new executor to obtain the frozen
protocol and permitted inputs, run the study through the declared adapter, and
publish a new receipt with disclosed intervention ownership, task authorship,
evaluation, analysis, and decision roles. Forking the repository, rerunning a
receipt, or checking a Git tag is not automatically independent verification.
Use `reproducible_third_party` or `independently_verified` only when the
receipt's role and evidence requirements are actually satisfied. Evidence
level, reproducibility, independence, freshness, action, and outcome remain
orthogonal; missing historical action or outcome is `not_declared_historical`,
not a negative observation.
