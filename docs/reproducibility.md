# Reproducibility

Reproduction starts from an immutable Git revision and ends with a scoped
comparison, not a claim that stochastic model behavior is byte-identical.

## Deterministic release checks

From a clean checkout of `v0.1.0-alpha.1`:

```bash
uv sync --locked --all-groups
uv run ruff check .
uv run ruff format --check .
uv run python -m unittest discover -s tests -v
uv run ael validate examples
uv run python tools/release_check.py
uv build
```

These checks establish package, schema, cross-reference, committed-fixture,
rendering, simulation, and public-tree consistency. They do not establish that
an experimental conclusion is true outside its receipt scope.

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

The simulation is deterministic because the configuration pins its seed.

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
