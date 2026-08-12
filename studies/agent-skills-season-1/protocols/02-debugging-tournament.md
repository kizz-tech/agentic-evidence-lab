# 02 — Debugging tournament

State: protocol draft; public activation calibration completed; effectiveness
screening unrun.

## Decision question

On seeded repository failures, which exact workflow—strong direct debugging,
Superpowers `systematic-debugging`, or Every `ce-debug`—most often identifies
and repairs the real root cause within a matched total-system budget?

## Conditions

- `B0`: strong direct Codex debugging prompt without either candidate skill.
- `S1`: `B0` plus exact source-locked Superpowers systematic-debugging.
- `S2`: a declared Codex compatibility adaptation of exact source-locked Every
  ce-debug. The adaptation is a different intervention and must be frozen and
  hash-bound; it cannot be reported as the unmodified upstream skill.

Screening strata: misleading symptom, cross-module contract, state-dependent
failure, concurrency/order defect, and an underdetermined case where the
correct action is to narrow rather than guess.

## Measurements and decision

Primary: root-cause-correct repair rate. Gates: no symptom patch that leaves
the causal defect, no invented evidence, and no unrelated destructive change.
Secondary: hypothesis count, causal-chain completeness, regression tests,
acceptance, generated work, and wall time. Rank only inside this task contract;
the result does not establish a universally best debugging method.
