# Calibration simulation: kizz:ael:calibration:council-generation-2:illustrative-v1

Assumption state: **illustrative_not_calibrated**  
Iterations: `1000`  
Seed: `20260812`  
RNG algorithm: `ael-splitmix64-irwin-hall12/v1`  
Config canonical SHA-256: `4ea4792a53a235acad6507eccdf7852fc9cde0c1ab8630df800334a6863452ff`

## Screening selection risk

| Task clusters | Repeats | Select true best | Select other | Reject all | Top-score tie |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 3 | 2 | 40.7% | 58.8% | 0.5% | 33.3% |
| 6 | 2 | 44.0% | 55.3% | 0.7% | 20.5% |
| 9 | 2 | 44.6% | 54.3% | 1.1% | 16.7% |
| 12 | 2 | 47.1% | 52.0% | 0.9% | 11.5% |

## Confirmatory lower-bound sensitivity

| Task clusters | Repeats | Assumed effect | Observed positive | 90% bootstrap lower bound > 0 |
| ---: | ---: | ---: | ---: | ---: |
| 12 | 3 | 0% | 40.8% | 6.2% |
| 12 | 3 | 5% | 66.8% | 16.3% |
| 12 | 3 | 10% | 82.5% | 28.1% |
| 12 | 3 | 15% | 95.5% | 53.6% |
| 18 | 3 | 0% | 42.8% | 4.2% |
| 18 | 3 | 5% | 72.6% | 18.3% |
| 18 | 3 | 10% | 89.4% | 39.0% |
| 18 | 3 | 15% | 97.1% | 67.4% |
| 24 | 3 | 0% | 47.0% | 5.1% |
| 24 | 3 | 5% | 76.3% | 21.8% |
| 24 | 3 | 10% | 94.3% | 47.2% |
| 24 | 3 | 15% | 99.9% | 77.5% |
| 36 | 3 | 0% | 44.0% | 4.9% |
| 36 | 3 | 5% | 82.6% | 26.2% |
| 36 | 3 | 10% | 96.6% | 59.6% |
| 36 | 3 | 15% | 99.9% | 88.8% |

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
