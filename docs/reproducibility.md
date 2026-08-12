# Reproducibility

Reproduction starts from an immutable Git revision and ends with a scoped
comparison, not a claim that stochastic model behavior is byte-identical.

## Deterministic release checks

From a clean checkout of `v0.1.0-alpha.4`:

```bash
uv sync --locked --all-groups
uv run ruff check .
uv run ruff format --check .
uv run python -m unittest discover -s tests -v
uv run ael validate examples
uv run ael source-lock check studies/agent-skills-season-1/sources.lock.toml
uv run ael study audit \
  --freeze studies/agent-skills-season-1/screening/property-based-testing-v2.freeze.json \
  --result studies/agent-skills-season-1/results/property-based-testing-v2 \
  --decision-adapter pbt-v2 \
  --require-git-proof
uv run ael validate \
  studies/agent-skills-season-1/concept.json \
  studies/agent-skills-season-1/manifests \
  studies/agent-skills-season-1/calibration/runtime-v1
uv run python tools/materialize_agent_skills_season.py --check
uv run python tools/release_check.py
uv build
```

These checks establish package, schema, cross-reference, committed-fixture,
rendering, simulation, and public-tree consistency. They do not establish that
an experimental conclusion is true outside its receipt scope.

The public Season 1 activation evidence is reproducible from retained private
run inputs only by the maintainer. Public consumers can validate every exposed
document, source lock, and content hash, but cannot reconstruct private Codex
events from their hashes. This is verification of the published evidence graph,
not independent reproduction of the hosted-agent executions.

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

The private observation payload remains opaque. The audit checks its published
hash and, with the explicit adapter, recomputes the exposed counts and outcome;
it cannot reconstruct hidden task or event bytes that were not published.

For future Codex runs, `ael study activation-check` accepts Codex JSONL events
and counts activation only when a completed, exit-zero command retrieved
non-empty content from the exact installed `SKILL.md`. A path mentioned in an
agent message, an in-progress command, a failed command, or empty output is not
activation evidence. This stricter parser does not rewrite historical records.

## Receipt reproduction

```bash
uv run ael render \
  examples/council-generation-1/evidence-receipt.json \
  --output /tmp/receipt.md
diff -u examples/council-generation-1/evidence-receipt.md /tmp/receipt.md
```

Every receipt binds its concept, study, runs, and measurements by SHA-256.
`ael validate` resolves relative public references and checks those hashes.

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

## Independent reproduction

Forking the repository or rerunning a receipt is not automatically independent
verification. Disclose intervention ownership, task authorship, evaluation,
analysis, and decision roles. Use `reproducible_third_party` or
`independently_verified` only when the receipt's role and evidence requirements
are actually satisfied.
