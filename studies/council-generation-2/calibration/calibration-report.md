# Calibration simulation: kizz:ael:calibration:council-generation-2:illustrative-v1

Assumption state: **illustrative_not_calibrated**  
Iterations: `1000`  
Seed: `20260812`  
Config canonical SHA-256: `4ea4792a53a235acad6507eccdf7852fc9cde0c1ab8630df800334a6863452ff`

## Screening selection risk

| Task clusters | Repeats | Select true best | Select other | Reject all | Top-score tie |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 3 | 2 | 43.7% | 55.5% | 0.8% | 35.5% |
| 6 | 2 | 43.9% | 55.3% | 0.8% | 22.8% |
| 9 | 2 | 46.0% | 52.7% | 1.3% | 16.4% |
| 12 | 2 | 45.4% | 52.9% | 1.7% | 15.0% |

## Confirmatory lower-bound sensitivity

| Task clusters | Repeats | Assumed effect | Observed positive | 90% bootstrap lower bound > 0 |
| ---: | ---: | ---: | ---: | ---: |
| 12 | 3 | 0% | 45.3% | 4.6% |
| 12 | 3 | 5% | 64.6% | 14.5% |
| 12 | 3 | 10% | 84.2% | 30.7% |
| 12 | 3 | 15% | 94.9% | 54.5% |
| 18 | 3 | 0% | 45.0% | 4.9% |
| 18 | 3 | 5% | 72.6% | 16.8% |
| 18 | 3 | 10% | 90.8% | 39.6% |
| 18 | 3 | 15% | 98.6% | 67.8% |
| 24 | 3 | 0% | 43.8% | 3.9% |
| 24 | 3 | 5% | 78.7% | 20.1% |
| 24 | 3 | 10% | 92.7% | 47.0% |
| 24 | 3 | 15% | 99.2% | 77.1% |
| 36 | 3 | 0% | 43.1% | 3.6% |
| 36 | 3 | 5% | 84.8% | 24.9% |
| 36 | 3 | 10% | 97.7% | 62.3% |
| 36 | 3 | 15% | 100.0% | 91.1% |

## Implementation-sentinel gate sensitivity

| True per-task success rate | Gate pass probability |
| ---: | ---: |
| 50% | 50.0% |
| 60% | 64.8% |
| 70% | 78.4% |
| 80% | 89.6% |

## Limits

- Illustrative assumptions are not estimates from Council Generation 1.
- Usable-decision outcomes are simulated as binary and do not reproduce the full Council rubric.
- The task-difficulty and within-task dependence model is deliberately simple.
- Stratum heterogeneity, evaluator disagreement, critical-failure severity, cost, and rework are not jointly modeled.
- The output diagnoses design sensitivity and cannot freeze a confirmatory manifest.

## Decision

Do not freeze Council Generation 2 from these numbers. Replace illustrative assumptions with actual task inventory, repeated Gen1 or pilot telemetry, evaluator capacity, and explicit error tolerances, then rerun the simulation.
