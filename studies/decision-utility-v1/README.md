# AEL Decision Utility v1

State: **instrument qualified locally; human pilot not admitted or run**.

This study asks whether an AEL claim-first card helps a competent human owner
choose the right action more often than an ordinary decision note or the same
note plus a static checklist when all three views contain the same evidence and
recommendation.

The public calibration package is synthetic. It exercises:

- evidence-equivalent A0/A1/A2 rendering;
- supported and contradicted recommendations;
- clear-positive, null, critical-failure, stale, protocol-invalid, and
  cost-dominant cases;
- a cyclic Latin-square schedule with no repeated case per participant;
- severity-weighted, unweighted, severity-stratum, critical-miss, false-block,
  burden, time, workload, and calibration accounting.

It does not contain human responses and cannot establish comprehension,
decision utility, adoption, or outcome. Model readers may be used later only as
an instrument stress test, never as substitutes for human participants.

Run the deterministic calibration check:

```bash
uv run python tools/materialize_decision_utility_v1.py --check
```

The scored pilot remains blocked until participant recruitment/consent, a
private blinded case pack, pilot variance, a sample-size decision, and a frozen
missingness/analysis plan exist before the first response.
