# Completion Integrity process-v1 fixtures

This subtree is the deterministic, zero-model-call fixture for the unreleased
alpha.10 observable-enactment candidate.

- `method-plan.pilot.json` binds the real policy fixture, non-compensating
  rules, and causal boundary.
- `policy-fixture.txt` provides the exact bytes verified by the adapter.
- `fixtures/normalized-cells.json` contains five sanitized known states.
- `fixtures/expected-diagnostics.json` is a golden bundle bound to the exact
  method plan, policy fixture, and normalized observations.

Event labels and event digests in the normalized cells are synthetic reported
facts. They are not runnable private attempts or empirical evidence. A future
owner adapter must capture and normalize actual harness events under a new
freeze.

Run the exact check from the repository root:

```bash
uv run python tools/check_completion_integrity_engagement.py \
  --method-plan studies/completion-integrity/diagnostics/process-v1/method-plan.pilot.json \
  --observations studies/completion-integrity/diagnostics/process-v1/fixtures/normalized-cells.json \
  --diagnostics-json studies/completion-integrity/diagnostics/process-v1/fixtures/expected-diagnostics.json \
  --check
```

This proves deterministic fixture behavior only. It does not rerun alpha.9,
show that the future runner captures these facts, or support an intervention
effect or mechanism claim.
