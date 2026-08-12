from __future__ import annotations

import hashlib
import json
import math
import random
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _logit(probability: float) -> float:
    return math.log(probability / (1.0 - probability))


def _logistic(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def _quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.floor(probability * (len(ordered) - 1))))
    return ordered[index]


def _bernoulli(rng: random.Random, probability: float) -> int:
    return int(rng.random() < probability)


def _screening(config: dict[str, Any], rng: random.Random, iterations: int) -> list[dict[str, Any]]:
    candidate_rates = [float(item) for item in config["candidate_usable_rates"]]
    best_index = max(range(len(candidate_rates)), key=candidate_rates.__getitem__)
    critical_rates = [float(item) for item in config["candidate_critical_failure_rates"]]
    results: list[dict[str, Any]] = []
    for task_count in config["task_counts"]:
        selected_best = 0
        selected_wrong = 0
        rejected_all = 0
        tied_top = 0
        for _ in range(iterations):
            scores = [0.0] * len(candidate_rates)
            disqualified = [False] * len(candidate_rates)
            for _task in range(int(task_count)):
                difficulty = rng.gauss(0.0, float(config["task_difficulty_logit_sd"]))
                for _repeat in range(int(config["repeats"])):
                    for index, rate in enumerate(candidate_rates):
                        probability = _logistic(_logit(rate) - difficulty)
                        scores[index] += _bernoulli(rng, probability)
                        if _bernoulli(rng, critical_rates[index]):
                            disqualified[index] = True
            denominator = int(task_count) * int(config["repeats"])
            eligible = [
                index
                for index, score in enumerate(scores)
                if not disqualified[index]
                and score / denominator >= float(config["admissibility_rate"])
            ]
            if not eligible:
                rejected_all += 1
                continue
            best_score = max(scores[index] for index in eligible)
            top = [index for index in eligible if scores[index] == best_score]
            if len(top) > 1:
                tied_top += 1
            selected = rng.choice(top)
            if selected == best_index:
                selected_best += 1
            else:
                selected_wrong += 1
        results.append(
            {
                "task_clusters": int(task_count),
                "repeats": int(config["repeats"]),
                "probability_select_true_best": round(selected_best / iterations, 4),
                "probability_select_other": round(selected_wrong / iterations, 4),
                "probability_reject_all": round(rejected_all / iterations, 4),
                "probability_top_score_tie": round(tied_top / iterations, 4),
            }
        )
    return results


def _paired_task_differences(
    config: dict[str, Any],
    rng: random.Random,
    task_count: int,
    effect: float,
) -> list[float]:
    baseline_rate = float(config["baseline_usable_rate"])
    treatment_rate = min(0.999, max(0.001, baseline_rate + effect))
    correlation = float(config["within_task_pair_correlation"])
    differences: list[float] = []
    for _task in range(task_count):
        difficulty = rng.gauss(0.0, float(config["task_difficulty_logit_sd"]))
        baseline_probability = _logistic(_logit(baseline_rate) - difficulty)
        treatment_probability = _logistic(_logit(treatment_rate) - difficulty)
        paired: list[float] = []
        for _repeat in range(int(config["repeats"])):
            if rng.random() < correlation:
                shared = rng.random()
                baseline = int(shared < baseline_probability)
                treatment = int(shared < treatment_probability)
            else:
                baseline = _bernoulli(rng, baseline_probability)
                treatment = _bernoulli(rng, treatment_probability)
            paired.append(float(treatment - baseline))
        differences.append(sum(paired) / len(paired))
    return differences


def _bootstrap_lower_bound(
    differences: list[float],
    rng: random.Random,
    samples: int,
    confidence: float,
) -> float:
    size = len(differences)
    means = [
        sum(differences[rng.randrange(size)] for _ in range(size)) / size
        for _sample in range(samples)
    ]
    return _quantile(means, (1.0 - confidence) / 2.0)


def _confirmation(
    config: dict[str, Any], rng: random.Random, iterations: int
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for task_count in config["task_counts"]:
        for effect in config["absolute_effects"]:
            lower_above_zero = 0
            observed_positive = 0
            for _ in range(iterations):
                differences = _paired_task_differences(config, rng, int(task_count), float(effect))
                observed = sum(differences) / len(differences)
                if observed > 0:
                    observed_positive += 1
                lower = _bootstrap_lower_bound(
                    differences,
                    rng,
                    int(config["bootstrap_samples"]),
                    float(config["confidence"]),
                )
                if lower > 0:
                    lower_above_zero += 1
            results.append(
                {
                    "task_clusters": int(task_count),
                    "repeats": int(config["repeats"]),
                    "absolute_effect": float(effect),
                    "probability_observed_difference_positive": round(
                        observed_positive / iterations, 4
                    ),
                    "probability_bootstrap_lower_bound_above_zero": round(
                        lower_above_zero / iterations, 4
                    ),
                }
            )
    return results


def _sentinels(config: dict[str, Any]) -> list[dict[str, Any]]:
    task_count = int(config["task_count"])
    required = int(config["required_successes"])
    results: list[dict[str, Any]] = []
    for rate in config["true_success_rates"]:
        probability = sum(
            math.comb(task_count, successes)
            * float(rate) ** successes
            * (1.0 - float(rate)) ** (task_count - successes)
            for successes in range(required, task_count + 1)
        )
        results.append(
            {
                "true_task_success_rate": float(rate),
                "probability_gate_passes": round(probability, 4),
            }
        )
    return results


def simulate(config: dict[str, Any]) -> dict[str, Any]:
    iterations = int(config["iterations"])
    rng = random.Random(int(config["seed"]))
    canonical = json.dumps(config, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "schema_version": "ael.calibration-simulation-result/0.1",
        "simulation_id": config["simulation_id"],
        "generated_at": config.get(
            "generated_at",
            datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        ),
        "config_canonical_sha256": hashlib.sha256(canonical).hexdigest(),
        "assumption_state": config["assumption_state"],
        "iterations": iterations,
        "seed": int(config["seed"]),
        "screening": _screening(config["screening"], rng, iterations),
        "confirmation": _confirmation(config["confirmation"], rng, iterations),
        "implementation_sentinels": _sentinels(config["implementation_sentinels"]),
        "limitations": [
            "Illustrative assumptions are not estimates from Council Generation 1.",
            "Usable-decision outcomes are simulated as binary and do not reproduce the full Council rubric.",
            "The task-difficulty and within-task dependence model is deliberately simple.",
            "Stratum heterogeneity, evaluator disagreement, critical-failure severity, cost, and rework are not jointly modeled.",
            "The output diagnoses design sensitivity and cannot freeze a confirmatory manifest.",
        ],
    }


def render_report(result: dict[str, Any]) -> str:
    lines = [
        f"# Calibration simulation: {result['simulation_id']}",
        "",
        f"Assumption state: **{result['assumption_state']}**  ",
        f"Iterations: `{result['iterations']}`  ",
        f"Seed: `{result['seed']}`  ",
        f"Config canonical SHA-256: `{result['config_canonical_sha256']}`",
        "",
        "## Screening selection risk",
        "",
        "| Task clusters | Repeats | Select true best | Select other | Reject all | Top-score tie |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in result["screening"]:
        lines.append(
            f"| {row['task_clusters']} | {row['repeats']} | {row['probability_select_true_best']:.1%} | "
            f"{row['probability_select_other']:.1%} | {row['probability_reject_all']:.1%} | "
            f"{row['probability_top_score_tie']:.1%} |"
        )
    lines.extend(
        [
            "",
            "## Confirmatory lower-bound sensitivity",
            "",
            "| Task clusters | Repeats | Assumed effect | Observed positive | 90% bootstrap lower bound > 0 |",
            "| ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in result["confirmation"]:
        lines.append(
            f"| {row['task_clusters']} | {row['repeats']} | {row['absolute_effect']:.0%} | "
            f"{row['probability_observed_difference_positive']:.1%} | "
            f"{row['probability_bootstrap_lower_bound_above_zero']:.1%} |"
        )
    lines.extend(
        [
            "",
            "## Implementation-sentinel gate sensitivity",
            "",
            "| True per-task success rate | Gate pass probability |",
            "| ---: | ---: |",
        ]
    )
    for row in result["implementation_sentinels"]:
        lines.append(
            f"| {row['true_task_success_rate']:.0%} | {row['probability_gate_passes']:.1%} |"
        )
    lines.extend(["", "## Limits", ""])
    lines.extend(f"- {item}" for item in result["limitations"])
    lines.extend(
        [
            "",
            "## Decision",
            "",
            "Do not freeze Council Generation 2 from these numbers. Replace illustrative assumptions with actual task inventory, repeated Gen1 or pilot telemetry, evaluator capacity, and explicit error tolerances, then rerun the simulation.",
            "",
        ]
    )
    return "\n".join(lines)


def run_calibration(
    config_path: Path, output_path: Path, report_path: Path | None
) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    result = simulate(config)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(render_report(result), encoding="utf-8")
    return result
