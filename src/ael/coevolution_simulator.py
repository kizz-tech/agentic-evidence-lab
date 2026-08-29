"""Deterministic no-effect producer for AEL-CEP Stage 0.

The simulator deliberately has no ambient inputs.  It consumes a frozen
``ael.coevolution`` protocol, derives independent SplitMix64 streams from the
declared seed, and emits a hash-linked ``TrajectoryBundle`` using the policy
kernel's constructors and validator.  The synthetic world is intentionally
small: it is an operating-characteristic diagnostic, not a model of a real
agent, evaluator, or organisation.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from typing import Any

from ael import coevolution as core

SIMULATOR_SCHEMA_VERSION = "ael-cep-simulator-0.2-development"
WORLD_MODEL_VERSION = "ael-cep-world-model-stage0/v1"
RNG_ALGORITHM = "ael-cep-splitmix64-sha256-stream/v1"
SIMULATION_CLOCK_VERSION = "ael-cep-simulated-clock/v1"
ARM_ORDER = ("A0", "A1", "A2", "A3", "A4", "A5")
SCENARIO_CATALOG = (
    "null",
    "useful",
    "shared_blind_spot",
    "evaluator_exploit",
    "feedback_leakage",
    "optional_stopping",
    "drift_reversal",
    "forgetting",
    "missingness",
    "poisoning",
    "deletion_tombstone",
    "forbidden_effect",
)

DEFAULT_REPLICATES = 3
DEFAULT_TASKS = 16
DEFAULT_DECISION_THRESHOLD = 0.64
DEFAULT_CLOCK_START = 1_000_000
MAX_SCENARIO_TASKS = 1_024
MAX_SCENARIO_REPLICATES = 256
MAX_SIMULATION_CELLS = 500_000
OPTIONAL_DIAGNOSTIC_LOOK = 0.5
# The diagnostic fixture intentionally stops at the frozen look for every
# baseline replicate; this makes the replicate-level denominator observable
# (e.g. 3 stopped / 3 replicates) rather than silently mixing task counts.
OPTIONAL_DIAGNOSTIC_STOP_THRESHOLD = 0.60
_FIXED_POINT_SCALE = 1_000_000
_TRUTH_FAMILY = {
    "null": "baseline",
    "shared_blind_spot": "baseline",
    "evaluator_exploit": "baseline",
    "feedback_leakage": "baseline",
    "optional_stopping": "baseline",
    "missingness": "baseline",
    "deletion_tombstone": "baseline",
    "forbidden_effect": "baseline",
    "useful": "useful",
    "drift_reversal": "drift_reversal",
    "forgetting": "forgetting",
    "poisoning": "poisoning",
}
# The core treats these five frozen strata as part of the bridge contract.
# Keep the names and weights versioned here rather than deriving them from
# mapping iteration or an arm's trajectory.
BRIDGE_STRATA = (
    ("good", 0.2),
    ("bad", 0.2),
    ("exploit", 0.2),
    ("semantic_mutant", 0.2),
    ("near_threshold", 0.2),
)
_MASK64 = (1 << 64) - 1
_ZERO_HASH = "0" * 64


class SimulatorError(ValueError):
    """Raised when a simulator-only input cannot be interpreted."""


def _hash(value: Any, domain: str = "ael-cep-simulator") -> str:
    return core.canonical_hash(value, domain=domain)


def _artifact(label: str) -> str:
    return _hash({"label": label, "version": SIMULATOR_SCHEMA_VERSION}, "ael-cep-artifact")


def derive_stream_seed(
    master_seed: int,
    scenario: str,
    replicate: int,
    arm: str,
    entity: str,
    stream: str,
) -> int:
    """Derive an independent 64-bit stream seed from stable named coordinates."""

    fields = (
        RNG_ALGORITHM,
        str(int(master_seed)),
        str(scenario),
        str(int(replicate)),
        str(arm),
        str(entity),
        str(stream),
    )
    material = "\x00".join(fields).encode("utf-8")
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")


class SplitMix64:
    """Version-stable SplitMix64 stream with a small deterministic API."""

    algorithm = RNG_ALGORITHM

    def __init__(self, seed: int) -> None:
        self._state = int(seed) & _MASK64

    def word(self) -> int:
        self._state = (self._state + 0x9E3779B97F4A7C15) & _MASK64
        value = self._state
        value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & _MASK64
        value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & _MASK64
        return (value ^ (value >> 31)) & _MASK64

    def random(self) -> float:
        return self.word() / float(1 << 64)

    def normal(self, mean: float = 0.0, standard_deviation: float = 1.0) -> float:
        # Irwin-Hall(12) is deterministic and avoids implementation-specific
        # transcendental/random helpers.
        return float(mean) + float(standard_deviation) * (
            sum(self.random() for _ in range(12)) - 6.0
        )

    def bernoulli(self, probability: float) -> bool:
        return self.random() < max(0.0, min(1.0, float(probability)))


def _clip(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, float(value)))


def _round(value: float) -> float:
    # Quantize emitted measurements before converting back to JSON numbers.
    # This keeps accumulator/canonical bytes stable across supported Python
    # versions while retaining more precision than the protocol thresholds.
    scaled = int(float(value) * _FIXED_POINT_SCALE + (0.5 if value >= 0 else -0.5))
    return scaled / _FIXED_POINT_SCALE


def _fixed(value: float) -> int:
    return int(float(value) * _FIXED_POINT_SCALE + (0.5 if value >= 0 else -0.5))


def _unfixed(value: int) -> float:
    return float(int(value)) / _FIXED_POINT_SCALE


def _rate(count: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    # Integer division followed by fixed-point emission avoids float sums.
    scaled = (int(count) * _FIXED_POINT_SCALE + int(denominator) // 2) // int(denominator)
    return scaled / _FIXED_POINT_SCALE


def _ratio(count: int, denominator: int) -> dict[str, Any]:
    return {"count": int(count), "denominator": int(denominator), "rate": _rate(count, denominator)}


_BRIDGE_TRUTH_CENTERS = {
    "good": 0.80,
    "bad": 0.35,
    "exploit": 0.56,
    "semantic_mutant": 0.44,
}


def _bridge_anchor_truth(
    master_seed: int,
    truth_scenario: str,
    stratum: str,
    decision_threshold: float,
) -> tuple[float, float]:
    """Return frozen B0/B1 anchor truth from an independent named stream.

    This stream is deliberately separate from evaluator-cell generation.  In
    particular, changing evaluator perturbations cannot change these values,
    their record hashes, or the thresholded anchor decisions.
    """

    rng = SplitMix64(
        derive_stream_seed(
            master_seed,
            truth_scenario,
            0,
            "A5",
            f"bridge-truth:{stratum}",
            "anchor_truth",
        )
    )
    if stratum == "near_threshold":
        # Deliberately place the two Builder generations on opposite sides of
        # the decision boundary while retaining a frozen, arm-blinded truth.
        b0 = decision_threshold - 0.012 + 0.004 * rng.random()
        b1 = decision_threshold + 0.012 + 0.004 * rng.random()
    else:
        center = _BRIDGE_TRUTH_CENTERS[stratum]
        b0 = center + (rng.random() - 0.5) * 0.012
        b1 = b0 + (rng.random() - 0.5) * 0.008
    b0_value = _round(_clip(b0))
    b1_value = _round(_clip(b1))
    if b1_value == b0_value:
        # Preserve a visible generation distinction even after fixed-point
        # quantization; this does not depend on evaluator-cell output.
        b1_value = _round(_clip(b0_value + (0.003 if b0_value <= 0.997 else -0.003)))
    return b0_value, b1_value


def _bridge_cell_scores(
    truth_values: tuple[float, float],
    *,
    decision_threshold: float,
    rng: SplitMix64,
) -> dict[str, float]:
    """Generate evaluator cells from latent truth plus bounded perturbations."""

    b0_truth, b1_truth = truth_values
    b0_decision = b0_truth >= decision_threshold
    b1_decision = b1_truth >= decision_threshold

    def preserve_decision(value: float, decision: bool) -> float:
        margin = decision_threshold + 0.002 if decision else decision_threshold - 0.002
        if decision:
            return _round(_clip(max(margin, value)))
        return _round(_clip(min(margin, value)))

    baseline_noise = (rng.random() - 0.5) * 0.004
    evaluator_shift = 0.002 + 0.001 * rng.random()
    builder_shift = (rng.random() - 0.5) * 0.004
    interaction = (rng.random() - 0.5) * 0.002
    b0e0 = preserve_decision(b0_truth + baseline_noise, b0_decision)
    b0e1 = preserve_decision(b0e0 + evaluator_shift, b0_decision)
    b1e0 = preserve_decision(b1_truth + builder_shift, b1_decision)
    b1e1 = preserve_decision(b1e0 + evaluator_shift + interaction, b1_decision)
    return {"b0e0": b0e0, "b0e1": b0e1, "b1e0": b1e0, "b1e1": b1e1}


def _scenario_names(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise SimulatorError("protocol.simulation.scenarios must be an array")
    names: list[str] = []
    for item in value:
        if isinstance(item, Mapping):
            raw = item.get("name", item.get("scenario", item.get("id")))
            if not isinstance(raw, str) or not raw.strip():
                raise SimulatorError("scenario mapping requires a non-empty name")
            name = raw.strip()
        elif isinstance(item, str) and item.strip():
            name = item.strip()
        else:
            raise SimulatorError("scenario names must be non-empty strings or mappings")
        if name not in names:
            names.append(name)
    unknown = sorted(set(names) - set(SCENARIO_CATALOG))
    if unknown:
        raise SimulatorError(f"unknown scenario(s): {', '.join(unknown)}")
    catalog_rank = {name: index for index, name in enumerate(SCENARIO_CATALOG)}
    names.sort(key=lambda name: (catalog_rank.get(name, len(catalog_rank)), name))
    return names


def _scenario_options(protocol: Mapping[str, Any], name: str) -> dict[str, Any]:
    scenarios = protocol["simulation"]["scenarios"]
    for item in scenarios:
        if isinstance(item, Mapping):
            item_name = item.get("name", item.get("scenario", item.get("id")))
            if item_name == name:
                return {str(key): value for key, value in item.items()}
    return {"name": name}


def _scenario_runtime(protocol: Mapping[str, Any], name: str) -> tuple[int, int]:
    """Read optional synthetic fixture sizing without adding protocol policy."""

    options = _scenario_options(protocol, name)
    tasks = options.get("tasks", DEFAULT_TASKS)
    replicates = options.get("replicates", DEFAULT_REPLICATES)
    if isinstance(tasks, bool) or not isinstance(tasks, int) or tasks <= 0:
        raise SimulatorError(f"scenario {name} tasks must be a positive integer")
    if isinstance(replicates, bool) or not isinstance(replicates, int) or replicates <= 0:
        raise SimulatorError(f"scenario {name} replicates must be a positive integer")
    if tasks > MAX_SCENARIO_TASKS:
        raise SimulatorError(f"scenario {name} tasks exceeds product cap {MAX_SCENARIO_TASKS}")
    if replicates > MAX_SCENARIO_REPLICATES:
        raise SimulatorError(
            f"scenario {name} replicates exceeds product cap {MAX_SCENARIO_REPLICATES}"
        )
    return tasks, replicates


def _empty_counts() -> dict[str, int]:
    return {
        "eligible": 0,
        "quarantined": 0,
        "revoked": 0,
        "unscorable": 0,
        "invalid": 0,
        "missing": 0,
    }


def _new_metrics() -> dict[str, Any]:
    return {
        "disposition": _empty_counts(),
        # Exactly one latent truth opportunity is assigned per replicate. It
        # is separate from promoted outcomes so opportunity denominators stay
        # honest when screening or bridge gates block a promotion.
        "candidate_opportunities": {
            "useful": 0,
            "null": 0,
            "harmful": 0,
            "adversarial": 0,
        },
        "attempted": 0,
        "promoted": 0,
        "promoted_useful": 0,
        "promoted_null": 0,
        "promoted_harmful": 0,
        "promoted_adversarial": 0,
        "false_promotion_count": 0,
        "useful_candidates": 0,
        "useful_candidates_eligible": 0,
        "exploit_candidates": 0,
        "exploit_accepted": 0,
        "critical_failures": 0,
        "bridge_attempted": 0,
        "bridge_pass": 0,
        "bridge_fail": 0,
        "bridge_unknown": 0,
        "bridge_later_reversal": 0,
        "tainted": 0,
        "missing": 0,
        "quarantine": 0,
        "optional_stopping": 0,
        # Optional stopping is a replicate-level diagnostic. Keep its
        # denominator separate from task-level ``attempted``.
        "optional_stopping_denominator": 0,
        "forbidden_effect_attempted": 0,
        "forbidden_effect_accepted": 0,
        "forbidden_effect_blocked": 0,
        "forbidden_effect_quarantined": 0,
        "declared_revocable_descendants": 0,
        "revoked": 0,
        "revocation_complete": 0,
        "matched_cost_target": 0,
        "matched_cost_actual": 0,
        "matched_cost_delta": 0,
        "matched_cost_equal": True,
        "ineligible_contrasts": 0,
        "unknown_custody": 0,
        "anchor_utility_sum": 0,
        "evaluator_score_sum": 0,
        "anchor_observations": 0,
        "score_observations": 0,
        "diagnostic": {},
    }


def _merge_metrics(left: dict[str, Any], right: Mapping[str, Any]) -> None:
    for key, value in right.items():
        if key == "disposition":
            for disposition, count in value.items():
                left["disposition"][disposition] += int(count)
        elif key == "candidate_opportunities":
            for category, count in value.items():
                left["candidate_opportunities"][category] += int(count)
        elif key == "diagnostic":
            left.setdefault("diagnostic", {}).update(value)
        elif isinstance(value, bool):
            if key not in left:
                left[key] = value
            else:
                left[key] = (
                    bool(left[key]) and value
                    if key == "matched_cost_equal"
                    else bool(left[key]) or value
                )
        elif isinstance(value, (int, float)):
            if key not in left:
                left[key] = 0
            left[key] += value


def _finalize_metrics(metrics: dict[str, Any], *, scenario: str, arm: str) -> dict[str, Any]:
    counts = metrics["disposition"]
    attempted = sum(counts.values())
    metrics["attempted"] = attempted
    promoted = int(metrics["promoted"])
    metrics["disposition_total"] = attempted
    metrics["disposition_identity"] = attempted == sum(counts.values())
    metrics["false_promotion"] = _ratio(int(metrics["false_promotion_count"]), promoted)
    metrics["false_promotion_rate"] = metrics["false_promotion"]["rate"]
    metrics["useful_power_attempted"] = _ratio(
        int(metrics["promoted_useful"]), int(metrics["useful_candidates"])
    )
    metrics["useful_power_eligible"] = _ratio(
        int(metrics["promoted_useful"]), int(metrics["useful_candidates_eligible"])
    )
    metrics["useful_candidate_power"] = metrics["useful_power_attempted"]
    metrics["exploit_acceptance"] = _ratio(
        int(metrics["exploit_accepted"]), int(metrics["exploit_candidates"])
    )
    metrics["promoted_critical_harm"] = _ratio(int(metrics["promoted_harmful"]), promoted)
    metrics["critical_failure"] = _ratio(int(metrics["critical_failures"]), attempted)
    metrics["bridge_pass_rate"] = _ratio(
        int(metrics["bridge_pass"]), int(metrics["bridge_attempted"])
    )
    metrics["bridge_reversal_rate"] = _ratio(
        int(metrics["bridge_later_reversal"]), int(metrics["bridge_pass"])
    )
    metrics["bridge_reversal"] = metrics["bridge_reversal_rate"]
    metrics["taint_rate"] = _ratio(int(metrics["tainted"]), attempted)
    metrics["missing_rate"] = _ratio(int(metrics["missing"]), attempted)
    metrics["missingness"] = metrics["missing_rate"]
    metrics["quarantine_rate"] = _ratio(int(metrics["quarantine"]), attempted)
    metrics["optional_stopping_rate"] = _ratio(
        int(metrics["optional_stopping"]), int(metrics["optional_stopping_denominator"])
    )
    metrics["forbidden_effects"] = {
        "attempted": int(metrics["forbidden_effect_attempted"]),
        "accepted": int(metrics["forbidden_effect_accepted"]),
        "blocked": int(metrics["forbidden_effect_blocked"]),
        "quarantined": int(metrics["forbidden_effect_quarantined"]),
    }
    metrics["revocation_completeness"] = _ratio(
        int(metrics["revocation_complete"]), int(metrics["declared_revocable_descendants"])
    )
    metrics["anchor_utility_mean"] = (
        _round(_unfixed(int(metrics["anchor_utility_sum"])) / metrics["anchor_observations"])
        if metrics["anchor_observations"]
        else None
    )
    metrics["evaluator_score_mean"] = (
        _round(_unfixed(int(metrics["evaluator_score_sum"])) / metrics["score_observations"])
        if metrics["score_observations"]
        else None
    )
    metrics["arm"] = arm
    metrics["scenario"] = scenario
    # Do not leave implementation-only accumulators in projections.
    return metrics


def _candidate_truth_class(
    scenario: str, anchor_mean: float, threshold: float = DEFAULT_DECISION_THRESHOLD
) -> str:
    """Classify one replicate's latent promotion opportunity."""

    if scenario == "useful" and anchor_mean >= threshold:
        return "useful"
    if scenario in {"drift_reversal", "forgetting", "poisoning"} and anchor_mean < 0.52:
        return "harmful"
    if scenario in {"evaluator_exploit", "shared_blind_spot"} and anchor_mean < threshold:
        return "adversarial"
    return "null"


def _trajectory_counts(metrics: Mapping[str, Any]) -> dict[str, Any]:
    """Project rich simulator metrics into the core's closed count contract.

    Trajectory summaries intentionally carry only integer aggregation inputs;
    rates and descriptive diagnostics remain derived data on the simulator
    projection.  Keeping this conversion at the emission boundary prevents a
    free-form nested metrics object from becoming an unvalidated decision
    input.
    """

    disposition = {
        key: int(metrics["disposition"].get(key, 0))
        for key in ("eligible", "quarantined", "revoked", "unscorable", "invalid", "missing")
    }
    return {
        "disposition": disposition,
        "promotion": {
            "useful": int(metrics.get("promoted_useful", 0)),
            "null": int(metrics.get("promoted_null", 0)),
            "harmful": int(metrics.get("promoted_harmful", 0)),
            "adversarial": int(metrics.get("promoted_adversarial", 0)),
        },
        "candidate_opportunities": {
            key: int(metrics["candidate_opportunities"].get(key, 0))
            for key in ("useful", "null", "harmful", "adversarial")
        },
        "exploit": {
            "candidates": int(metrics.get("exploit_candidates", 0)),
            "accepted": int(metrics.get("exploit_accepted", 0)),
        },
        "critical_failures": int(metrics.get("critical_failures", 0)),
        "bridge": {
            # The closed summary contract counts every attempted bridge
            # disposition, including an explicit unknown custody/bridge
            # result.  The rich diagnostic metric keeps ``bridge_attempted``
            # as the physical attempt flag; derive the contract denominator
            # from the mutually exclusive outcomes here.
            "attempted": int(
                metrics.get("bridge_pass", 0)
                + metrics.get("bridge_fail", 0)
                + metrics.get("bridge_unknown", 0)
            ),
            "passed": int(metrics.get("bridge_pass", 0)),
            "failed": int(metrics.get("bridge_fail", 0)),
            "unknown": int(metrics.get("bridge_unknown", 0)),
            "later_reversal": int(metrics.get("bridge_later_reversal", 0)),
        },
        "tainted": int(metrics.get("tainted", 0)),
        "optional_stopping": {
            "events": int(metrics.get("optional_stopping", 0)),
            "eligible_replicates": int(metrics.get("optional_stopping_denominator", 0)),
        },
        "revocation": {
            "declared_descendants": int(metrics.get("declared_revocable_descendants", 0)),
            "complete_descendants": int(metrics.get("revocation_complete", 0)),
        },
    }


def _scenario_truth(
    seed: int,
    scenario: str,
    replicate: int,
    task: int,
    task_count: int = DEFAULT_TASKS,
    *,
    arm: str = "A0",
    evolving_builder: bool = False,
    partition: str = "screening",
) -> tuple[float, float, float]:
    truth_family = _TRUTH_FAMILY.get(scenario, scenario)
    task_entity = f"{partition}:task:{task}"
    truth_rng = SplitMix64(
        derive_stream_seed(seed, truth_family, replicate, "WORLD", task_entity, "latent_truth")
    )
    anchor_rng = SplitMix64(
        derive_stream_seed(seed, truth_family, replicate, "WORLD", task_entity, "anchor_truth")
    )
    base = 0.52 + 0.07 * truth_rng.normal()
    if truth_family == "useful":
        base += 0.18
    elif truth_family == "drift_reversal":
        base += 0.04 if task < task_count // 2 else -0.08
    elif truth_family == "forgetting":
        base += 0.06 if task < task_count // 2 else -0.04
    elif truth_family == "poisoning":
        base -= 0.03
    # Builder evolution is a predeclared arm property, not a function of the
    # candidate output or evaluator score.  The protected anchor remains an
    # arm-blinded prospective stream with shared task noise.
    builder_truth = base
    if evolving_builder:
        if truth_family == "useful":
            builder_truth += 0.06 + 0.05 * (task / max(1, task_count - 1))
        elif truth_family == "drift_reversal":
            builder_truth += 0.08 if task < task_count // 2 else -0.10
        elif truth_family == "forgetting":
            builder_truth += 0.06 if task < task_count // 2 else -0.10
    # ``arm`` is intentionally part of the named domain even though fixed
    # builders use the shared family stream; this prevents accidental stream
    # consumption/arm-order coupling when builder evolution is introduced.
    _ = arm
    anchor = _clip(builder_truth + 0.025 * anchor_rng.normal())
    return _clip(base), _clip(builder_truth), anchor


def _matched_cost(
    protocol: Mapping[str, Any],
    arm: str,
    task_count: int,
    replicate_count: int,
    replicate_index: int = 0,
    executed_tasks: int | None = None,
) -> dict[str, Any]:
    """Compute a matched budget from declared role/work/governance components."""

    if executed_tasks is None:
        executed_tasks = task_count
    if isinstance(executed_tasks, bool) or not isinstance(executed_tasks, int):
        raise SimulatorError("executed task count must be an integer")
    if executed_tasks < 0 or executed_tasks > task_count:
        raise SimulatorError("executed task count must be within the declared task count")

    total_target_fp = _fixed(float(protocol["budgets"]["total_system"]))
    target_base, target_remainder = divmod(total_target_fp, replicate_count)
    target_fp = target_base + int(replicate_index < target_remainder)
    arm_policy = protocol["arms"][arm]
    role_components_fp = {
        "builder": _fixed(30.0),
        "evaluator": _fixed(30.0),
        "anchor": _fixed(24.0 if arm_policy["anchor"] == "protected" else 8.0),
        "challenger": _fixed(18.0 if arm_policy["challenger"] == "present" else 0.0),
    }
    declared_task_execution_fp = _fixed(task_count * 1.75)
    actual_task_execution_fp = _fixed(executed_tasks * 1.75)
    # Governance is booked against the declared fixed-N work plan. If an
    # optional-stopping replicate executes fewer tasks, task execution falls
    # while the same governance allocation remains booked; copying the target
    # into ``actual`` would hide that diagnostic cost difference.
    governance_balance_fp = (
        target_fp - sum(role_components_fp.values()) - declared_task_execution_fp
    )
    if governance_balance_fp < 0:
        raise SimulatorError("declared total-system budget is below synthetic role/work cost")
    actual_components_fp = dict(role_components_fp)
    actual_components_fp["task_execution"] = actual_task_execution_fp
    actual_components_fp["governance_balance"] = governance_balance_fp
    actual_fp = sum(actual_components_fp.values())
    components_fp = dict(actual_components_fp)
    components_fp["task_execution_declared"] = declared_task_execution_fp
    return {
        "target": _unfixed(target_fp),
        "actual": _unfixed(actual_fp),
        "delta": _unfixed(actual_fp - target_fp),
        "equal": actual_fp == target_fp,
        "components": {key: _unfixed(value) for key, value in components_fp.items()},
        "declared_task_count": int(task_count),
        "executed_task_count": int(executed_tasks),
    }


def _simulate_arm_scenario(
    protocol: Mapping[str, Any],
    scenario: str,
    arm: str,
    replicate: int,
    task_count: int,
    *,
    replicate_count: int = DEFAULT_REPLICATES,
    clock_start: int,
    partition: str = "screening",
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    seed = int(protocol["simulation"]["seed"])
    decision_threshold = float(protocol["decision_rule"]["threshold"])
    metrics = _new_metrics()
    observations: list[dict[str, Any]] = []
    evolving_builder = protocol["arms"][arm]["builder"] == "evolving"
    evolving_evaluator = protocol["arms"][arm]["evaluator"] == "evolving"
    protected = protocol["arms"][arm]["anchor"] == "protected"
    challenger = protocol["arms"][arm]["challenger"] == "present"
    scenario_optional = scenario == "optional_stopping"
    if scenario_optional:
        # One denominator unit per replicate, regardless of how many task
        # observations the diagnostic look consumed.
        metrics["optional_stopping_denominator"] = 1
    optional_boundary = (
        max(2, min(task_count - 1, int(task_count * OPTIONAL_DIAGNOSTIC_LOOK)))
        if scenario_optional and task_count > 2
        else None
    )
    stopped_early = False

    for task in range(task_count):
        _latent, builder_truth, anchor = _scenario_truth(
            seed,
            scenario,
            replicate,
            task,
            task_count,
            arm=arm,
            evolving_builder=evolving_builder,
            partition=partition,
        )
        candidate_rng = SplitMix64(
            derive_stream_seed(
                seed,
                scenario,
                replicate,
                arm,
                f"{partition}:task:{task}",
                "candidate",
            )
        )
        evaluator_rng = SplitMix64(
            derive_stream_seed(
                seed,
                scenario,
                replicate,
                arm,
                f"{partition}:task:{task}",
                "evaluator",
            )
        )
        # Candidate output noise is not fed back into the protected anchor.
        true_utility = _clip(builder_truth + 0.015 * candidate_rng.normal())
        evaluator_score = _clip(true_utility + 0.03 * evaluator_rng.normal())
        exploit = scenario == "evaluator_exploit" or (
            scenario == "shared_blind_spot" and task % 3 == 0
        )
        if exploit:
            evaluator_score = _clip(evaluator_score + (0.32 if arm in {"A2", "A3", "A4"} else 0.18))
        if scenario == "shared_blind_spot":
            evaluator_score = _clip(evaluator_score + 0.20)
        if evolving_evaluator:
            evaluator_score = _clip(evaluator_score + 0.025 * (task / max(1, task_count - 1)))
        if scenario == "feedback_leakage" and task >= task_count // 2:
            evaluator_score = _clip(evaluator_score + 0.12)

        missing_probability = 0.0
        if scenario == "missingness":
            missing_probability = 0.12 if task % 4 else 0.32
            if true_utility < 0.42:
                missing_probability += 0.18
        missing = candidate_rng.bernoulli(missing_probability)
        critical = scenario == "poisoning" and candidate_rng.bernoulli(0.14)
        tainted = scenario == "feedback_leakage" and task >= task_count // 2
        effect_attempt = scenario == "forbidden_effect" and task == 0
        revoked = scenario == "deletion_tombstone" and task == task_count - 1
        detected_exploit = challenger and exploit and candidate_rng.bernoulli(0.80)

        if missing:
            disposition = "missing"
            metrics["missing"] += 1
        elif revoked:
            disposition = "revoked"
        elif effect_attempt:
            disposition = "quarantined"
            metrics["forbidden_effect_attempted"] += 1
            metrics["forbidden_effect_blocked"] += 1
            metrics["forbidden_effect_quarantined"] += 1
            metrics["quarantine"] += 1
        elif critical:
            disposition = "unscorable"
            metrics["critical_failures"] += 1
        elif tainted:
            disposition = "quarantined"
            metrics["tainted"] += 1
            metrics["quarantine"] += 1
        elif detected_exploit:
            disposition = "quarantined"
            metrics["quarantine"] += 1
        else:
            disposition = "eligible"

        metrics["disposition"][disposition] += 1
        # Missing attempts stay in the attempted/disposition denominator but
        # contribute neither score nor anchor observations.
        if not missing:
            metrics["anchor_utility_sum"] += _fixed(anchor)
            metrics["anchor_observations"] += 1
            metrics["evaluator_score_sum"] += _fixed(evaluator_score)
            metrics["score_observations"] += 1
            if exploit:
                metrics["exploit_candidates"] += 1
            if exploit and disposition == "eligible" and evaluator_score >= 0.72:
                metrics["exploit_accepted"] += 1
        observations.append(
            {
                "task": task,
                "partition": partition,
                "clock": clock_start + replicate * task_count + task,
                "latent_true_utility": _round(true_utility),
                "evaluator_score": _round(evaluator_score),
                "anchor_outcome": _round(anchor),
                "exploit": exploit,
                "detected_exploit": detected_exploit,
                "missing": missing,
                "critical_failure": critical,
                "tainted": tainted,
                "effect_attempt": effect_attempt,
                "revoked": revoked,
                "disposition": disposition,
            }
        )
        if optional_boundary is not None and task + 1 == optional_boundary:
            interim = (
                _unfixed(int(metrics["evaluator_score_sum"])) / metrics["score_observations"]
                if metrics["score_observations"]
                else 0.0
            )
            if interim < OPTIONAL_DIAGNOSTIC_STOP_THRESHOLD:
                metrics["optional_stopping"] += 1
                stopped_early = True
                break

    if scenario == "deletion_tombstone":
        metrics["declared_revocable_descendants"] = 2
        metrics["revoked"] = 2
        metrics["revocation_complete"] = 2

    # A candidate-level decision is deliberately conservative for protected
    # arms: anchor, bridge, and custody gates are required before promotion.
    anchor_mean = (
        _unfixed(int(metrics["anchor_utility_sum"])) / metrics["anchor_observations"]
        if metrics["anchor_observations"]
        else 0.0
    )
    score_mean = (
        _unfixed(int(metrics["evaluator_score_sum"])) / metrics["score_observations"]
        if metrics["score_observations"]
        else 0.0
    )
    truth_class = _candidate_truth_class(scenario, anchor_mean, decision_threshold)
    metrics["candidate_opportunities"][truth_class] += 1
    candidate_eligible = (
        metrics["disposition"]["eligible"] > 0
        and not metrics["tainted"]
        and not metrics["critical_failures"]
        and not metrics["forbidden_effect_attempted"]
        and not stopped_early
    )
    if scenario == "useful":
        # Useful power is a trajectory/candidate denominator, not a task count.
        metrics["useful_candidates"] = 1
        metrics["useful_candidates_eligible"] = int(candidate_eligible)
    promotion = False
    if candidate_eligible and score_mean >= decision_threshold and not scenario_optional:
        promotion = anchor_mean >= decision_threshold if protected else True
    if promotion:
        metrics["promoted"] += 1
        metrics[f"promoted_{truth_class}"] += 1
        if truth_class != "useful":
            metrics["false_promotion_count"] += 1

    metrics["bridge_attempted"] = int(protected or evolving_evaluator)
    if metrics["bridge_attempted"] and metrics["score_observations"]:
        bridge_gap = abs(score_mean - anchor_mean)
        shift = _round(bridge_gap * 0.02)
        interaction = _round(bridge_gap * 0.01)
        agreement = _round(_clip(1.0 - bridge_gap * 0.10))
        bridge_pass = int(
            shift <= float(protocol["bridge"]["global_shift_tolerance"])
            and interaction <= float(protocol["bridge"]["interaction_tolerance"])
            and agreement >= float(protocol["bridge"]["decision_agreement_min"])
        )
        metrics["bridge_pass"] = bridge_pass
        metrics["bridge_fail"] = int(not bridge_pass)
        if scenario == "drift_reversal":
            metrics["bridge_later_reversal"] = int(anchor_mean < 0.52)
    else:
        metrics["bridge_unknown"] = 1

    cost = _matched_cost(
        protocol,
        arm,
        task_count,
        replicate_count,
        replicate,
        executed_tasks=len(observations),
    )
    metrics["matched_cost_target"] = cost["target"]
    metrics["matched_cost_actual"] = cost["actual"]
    metrics["matched_cost_delta"] = cost["delta"]
    metrics["matched_cost_equal"] = cost["equal"]
    metrics["cost_components"] = cost["components"]
    metrics["declared_task_count"] = cost["declared_task_count"]
    metrics["executed_task_count"] = cost["executed_task_count"]
    metrics["unknown_custody"] = int(arm == "A3")
    if scenario_optional:
        metrics["diagnostic"] = {
            "causal_comparison_eligible": False,
            "reason": "optional_stopping",
            "stopped_early": stopped_early,
            "optional_stopping_unit": "replicate",
            "optional_stopping_denominator_unit": "replicate",
            "looks": 2 if optional_boundary is not None else 1,
        }
    else:
        metrics["diagnostic"] = {"causal_comparison_eligible": True}
    metrics["promotion_candidate_eligible"] = promotion
    metrics["anchor_observed_tasks"] = metrics["anchor_observations"]
    metrics["score_observed_tasks"] = metrics["score_observations"]
    return _finalize_metrics(metrics, scenario=scenario, arm=arm), observations


def _algorithm(ref: str) -> dict[str, str]:
    return {"ref": ref, "hash": _artifact(f"algorithm:{ref}")}


def _arms() -> dict[str, dict[str, str]]:
    return {
        "A0": {
            "builder": "fixed",
            "evaluator": "fixed",
            "loop": "open",
            "custody": "shared",
            "challenger": "absent",
            "anchor": "absent",
        },
        "A1": {
            "builder": "evolving",
            "evaluator": "fixed",
            "loop": "open",
            "custody": "shared",
            "challenger": "absent",
            "anchor": "absent",
        },
        "A2": {
            "builder": "fixed",
            "evaluator": "evolving",
            "loop": "open",
            "custody": "shared",
            "challenger": "absent",
            "anchor": "absent",
        },
        "A3": {
            "builder": "evolving",
            "evaluator": "evolving",
            "loop": "naive_closed",
            "custody": "shared",
            "challenger": "absent",
            "anchor": "absent",
        },
        "A4": {
            "builder": "evolving",
            "evaluator": "evolving",
            "loop": "custody_separated",
            "custody": "separated",
            "challenger": "absent",
            "anchor": "protected",
        },
        "A5": {
            "builder": "evolving",
            "evaluator": "evolving",
            "loop": "challenger_anchor",
            "custody": "separated",
            "challenger": "present",
            "anchor": "protected",
        },
    }


def default_protocol(
    *, seed: int = 20260815, scenarios: Sequence[Any] | None = None
) -> dict[str, Any]:
    """Return a complete frozen Stage-0 protocol accepted by the core."""

    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise SimulatorError("seed must be a nonnegative integer")
    supplied_scenarios = list(scenarios) if scenarios is not None else list(SCENARIO_CATALOG)
    scenario_names = _scenario_names(supplied_scenarios)
    scenario_by_name = {
        str(item.get("name", item.get("scenario", item.get("id")))): item
        for item in supplied_scenarios
        if isinstance(item, Mapping)
    }
    scenario_values: list[dict[str, int | str]] = []
    for name in scenario_names:
        item = scenario_by_name.get(name, {})
        tasks = item.get("tasks", DEFAULT_TASKS) if isinstance(item, Mapping) else DEFAULT_TASKS
        replicates = (
            item.get("replicates", DEFAULT_REPLICATES)
            if isinstance(item, Mapping)
            else DEFAULT_REPLICATES
        )
        if (
            isinstance(tasks, bool)
            or not isinstance(tasks, int)
            or tasks <= 0
            or tasks > MAX_SCENARIO_TASKS
        ):
            raise SimulatorError(
                f"scenario {name} tasks must be an integer in 1..{MAX_SCENARIO_TASKS}"
            )
        if (
            isinstance(replicates, bool)
            or not isinstance(replicates, int)
            or replicates <= 0
            or replicates > MAX_SCENARIO_REPLICATES
        ):
            raise SimulatorError(
                f"scenario {name} replicates must be an integer in 1..{MAX_SCENARIO_REPLICATES}"
            )
        # Core protocol scenarios are intentionally a closed object shape;
        # aliases supplied by callers (scenario/id) and unrelated keys are
        # normalized away while declared sizing remains stable.
        scenario_values.append({"name": name, "tasks": int(tasks), "replicates": int(replicates)})
    arms = _arms()
    algorithms = {
        "eligibility": _algorithm("ael-cep/eligibility/v1"),
        "task_allocation": _algorithm("ael-cep/task-allocation/fixed-paired/v1"),
        "proposal_admission": _algorithm("ael-cep/proposal-admission/fixed/v1"),
        "selection_ranking": _algorithm("ael-cep/selection-ranking/fixed/v1"),
        "stopping": _algorithm("ael-cep/stopping/fixed-n/v1"),
        "analysis": _algorithm("ael-cep/analysis/anchor-utility/v1"),
        "promotion": _algorithm("ael-cep/promotion/fail-closed/v1"),
    }
    budgets = {"total_system": 1000.0, "feedback": 120.0, "exposure": 40.0, "confirmation": 80.0}
    partitions = {}
    for name, purpose, feedback, sealed, single_use, eligible, budget in (
        ("development", "adaptive development", "full", False, False, False, 0),
        ("screening", "bounded adaptive screening", "aggregate", False, False, False, 120),
        ("bridge", "evaluator bridge", "none", True, True, False, 40),
        ("confirmation", "sealed confirmation", "none", True, True, True, 80),
        ("historical", "descriptive history", "none", True, False, False, 0),
    ):
        partitions[name] = {
            "partition_id": name,
            "purpose": purpose,
            "feedback": feedback,
            "sealed": sealed,
            "single_use": single_use,
            "eligible_for_promotion": eligible,
            "exposure_budget": budget,
            "task_root_hash": _artifact(f"task-root:{name}"),
        }
    principal_names = ("evidence", "confirmation", "anchor", "adjudication", "promotion")
    principals = {
        name: {
            "principal_id": f"cep:{name}:stage0",
            "custody": (f"cep:{name}:stage0" if name == "anchor" else f"synthetic-{name}-custody"),
            "independence": "separate",
            "lineage": f"stage0:{name}:lineage",
        }
        for name in principal_names
    }
    contrasts: list[dict[str, Any]] = []
    arm_fields = ("builder", "evaluator", "loop", "custody", "challenger", "anchor")
    for index, arm_a in enumerate(ARM_ORDER):
        for arm_b in ARM_ORDER[index + 1 :]:
            differing = [field for field in arm_fields if arms[arm_a][field] != arms[arm_b][field]]
            if len(differing) == 1:
                dimension = differing[0]
                estimand_kind = "component"
                arm_a_level = arms[arm_a][dimension]
                arm_b_level = arms[arm_b][dimension]
            else:
                dimension = "policy_package"
                estimand_kind = "policy_package"
                arm_a_level = arm_a
                arm_b_level = arm_b
            contrasts.append(
                {
                    "contrast_id": f"contrast:{arm_a}:{arm_b}",
                    "arm_a": arm_a,
                    "arm_b": arm_b,
                    "treatment": {
                        "dimension": dimension,
                        "arm_a_level": arm_a_level,
                        "arm_b_level": arm_b_level,
                    },
                    "estimand_kind": estimand_kind,
                    **{key: dict(value) for key, value in algorithms.items()},
                    "budgets": dict(budgets),
                }
            )
    return {
        "schema_version": core.PROTOCOL_SCHEMA_VERSION,
        "protocol_id": f"ael-cep-stage0-{seed}",
        "epoch": {
            "epoch_id": f"epoch-stage0-{seed}",
            "state": "frozen",
            "constitution_ref": "ael-cep-stage0-constitution",
            "constitution_hash": _artifact("constitution:stage0"),
        },
        "principals": principals,
        "intake": {
            "target_population": "synthetic prospective agent tasks",
            "use": "Stage-0 operating-characteristic simulation",
            "intake_owner": "cep:intake-owner",
            "sampling_custodian": "cep:sampling-custodian",
            "sampling_frame": "synthetic-fixed-task-frame-v1",
            "sampling_method": "paired-stratified-deterministic",
            "sampling_window": "simulated-epoch",
            "sampling_cutoff": "simulated-cutoff",
            "eligibility": "declared synthetic task schema",
            "deduplication": "task-root-hash",
            "censoring_late_arrival": "none-in-simulation",
            "oracle": "arm-blinded-anchor-truth-stream",
            "adjudication": "protected-anchor-adjudication",
            "appeal": "fail-closed-no-appeal",
            "utility": "bounded prospective utility [0,1]",
            "harms": "critical-failure-and-reversal",
            "weights": "equal-task-weight",
            "margins": "synthetic-diagnostic-thresholds",
            "arm_blinding": "candidate-and-arm-blinded-anchor",
            "allocation_proof": "stream-derived-paired-allocation",
            "exposure_policy": "append-only-exposure-ledger",
        },
        "partitions": partitions,
        "arms": arms,
        "contrasts": contrasts,
        "algorithms": algorithms,
        "budgets": budgets,
        "feedback_exposure": {
            "development": "full-feedback",
            "screening": "aggregate-only-bounded",
            "bridge": "sealed-dual-score",
            "confirmation": "none-before-open",
            "total": "matched-total-system-budget",
        },
        "missingness": {
            "policy": "record-assignment-execution-scoring-separately",
            "bounds": {"mcar": 0.15, "mnar": 0.30},
            "critical_failure_rule": "critical-failure-is-unscorable",
        },
        "stopping": {
            "algorithm_ref": algorithms["stopping"]["ref"],
            "algorithm_hash": algorithms["stopping"]["hash"],
            "rule": "fixed-N-except-optional-stopping-diagnostic",
            "max_looks": 1,
            "missing_data": "honest-denominators",
        },
        "bridge": {
            "global_shift_tolerance": 0.05,
            "interaction_tolerance": 0.05,
            "decision_agreement_min": 0.90,
            "construct_required": True,
            "reliability_required": True,
            "anchor_required": True,
            "strata": [
                {
                    "stratum": name,
                    "weight": weight,
                    "task_root_hash": _artifact(f"task-root:bridge:{name}"),
                }
                for name, weight in BRIDGE_STRATA
            ],
        },
        "decision_rule": {
            "threshold": DEFAULT_DECISION_THRESHOLD,
            "operator": "gte",
            "value_range": [0.0, 1.0],
            "required_status": "observed",
            "outcome": "prospective_utility",
            "critical_failure": "block",
        },
        "replay": {
            "retention_policy": "retain-sanitized-surfaces",
            "required_surfaces": ["subject-output", "task-input", "runner-trace"],
            "deterministic_code_policy": "mocked-effects-only",
        },
        "independence": {
            "protected_dimensions": [
                "authorship",
                "operation",
                "custody",
                "adjudication",
                "organization",
                "model_provider",
                "training_data",
                "exposure",
            ],
            "ceiling": "separate",
        },
        "promotion": {
            "initial_state": "registered",
            "transition_table": {
                state: sorted(targets) for state, targets in core.PROMOTION_TRANSITIONS.items()
            },
            "terminal_states": [
                state for state in core.PROMOTION_STATES if not core.PROMOTION_TRANSITIONS[state]
            ],
        },
        "effect_policy": "forbidden",
        "simulation": {
            "config_version": SIMULATOR_SCHEMA_VERSION,
            "seed": seed,
            "scenarios": scenario_values,
        },
    }


def _release_payload(
    role: str, release_id: str, *, parent: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "release_id": release_id,
        "release_kind": role,
        "revision": "stage0-v1",
        "artifact_hash": _artifact(f"release:{release_id}"),
        "lineage": f"synthetic:{role}:lineage",
        "custody": "cep:anchor:stage0" if role == "anchor" else f"synthetic:{role}:custody",
        "allowed_evidence_surface": ["subject-output", "task-input", "runner-trace"],
        "changes": ["stage0-synthetic-world"],
        "self_certification": False,
    }
    if parent is not None:
        payload["parent_release_ref"] = parent["record_id"]
        payload["parent_release_hash"] = parent["record_hash"]
    if role == "evaluator":
        payload.update(
            {
                "implementation": "synthetic-score/v1",
                "prompt_or_rubric": "latent-utility-rubric/v1",
                "model": "synthetic-evaluator/v1",
                "parser_or_aggregation": "mean-score/v1",
                "tools_or_environment": "no-tools-synthetic-env/v1",
                "calibration_lineage": "synthetic-anchor-calibration/v1",
                "known_error_envelope": {"shared_blind_spot": True, "exploit_surface": True},
            }
        )
    if role == "anchor":
        payload["adjudication_protocol"] = "arm-blinded-anchor-adjudication/v1"
    return payload


class _Ledger:
    def __init__(self, protocol: Mapping[str, Any]) -> None:
        self.protocol = protocol
        self.records: list[dict[str, Any]] = []
        # A candidate that fails screening must not materialize a bridge panel.
        # The bridge producer below still shares the deterministic panel
        # construction path with successful candidates; suppressed IDs return
        # validated ephemeral records so the path can compute its diagnostics
        # without entering the append-only ledger.
        self.suppressed_record_prefixes: tuple[str, ...] = ()

    def add(
        self,
        record_type: str,
        record_id: str,
        payload: Mapping[str, Any],
        dependencies: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        previous = self.records[-1]["record_hash"] if self.records else None
        record = core.create_record(
            record_id=record_id,
            record_type=record_type,
            epoch_id=self.protocol["epoch"]["epoch_id"],
            sequence=len(self.records),
            previous_record_hash=previous,
            payload=dict(payload),
            dependency_refs=dependencies or {},
        )
        if any(record_id.startswith(prefix) for prefix in self.suppressed_record_prefixes):
            return record
        self.records.append(record)
        return record


def _binding_payload(
    protocol: Mapping[str, Any],
    binding_id: str,
    builder: Mapping[str, Any],
    evaluator: Mapping[str, Any],
    method: Mapping[str, Any],
    evidence: Mapping[str, Any],
    partition: str,
) -> dict[str, Any]:
    evidence_payload = evidence["payload"]
    return {
        "binding_id": binding_id,
        "builder_release_ref": builder["record_id"],
        "builder_release_hash": builder["record_hash"],
        "evaluator_release_ref": evaluator["record_id"],
        "evaluator_release_hash": evaluator["record_hash"],
        "method_ref": method["record_id"],
        "method_hash": method["record_hash"],
        "evidence_ref": evidence["record_id"],
        "evidence_hash": evidence["record_hash"],
        "task_partition": partition,
        "task_ref": evidence_payload["task_ref"],
        "task_hash": evidence_payload["task_hash"],
        "exposure_policy": "screening_feedback_only"
        if partition == "screening"
        else "sealed_single_use",
        "analysis_ref": protocol["algorithms"]["analysis"]["ref"],
        "analysis_hash": protocol["algorithms"]["analysis"]["hash"],
        "environment_ref": "environment:synthetic:v1",
        "environment_hash": _artifact("environment:synthetic:v1"),
        "runner_ref": "runner:simulation:v1",
        "runner_hash": _artifact("runner:simulation:v1"),
        "promotion_policy_ref": protocol["algorithms"]["promotion"]["ref"],
        "promotion_policy_hash": protocol["algorithms"]["promotion"]["hash"],
        "exposure_state_ref": "exposure:ledger:v1",
        "exposure_state_hash": _artifact("exposure:ledger:v1"),
        "allowed_evidence_surface": ["subject-output", "task-input", "runner-trace"],
    }


def _evidence_payload(
    evidence_id: str,
    builder: Mapping[str, Any],
    partition: str,
    *,
    commitment: Mapping[str, Any] | None = None,
    tainted: bool = False,
) -> dict[str, Any]:
    # The core schema intentionally keeps the retained synthetic surface
    # compact.  Commit the exact scenario/seed/summary coordinates in the
    # artifact hash so the same record id cannot mask a different observation
    # set across protocol runs.
    commitment_value = dict(commitment or {"evidence_id": evidence_id})
    task_ref = commitment_value.get("task_ref", f"task-pack:{partition}:stage0")
    task_hash = commitment_value.get("task_root_hash", _artifact(f"task-root:{partition}"))
    return {
        "evidence_id": evidence_id,
        "subject_ref": f"subject:{evidence_id}",
        "builder_release_ref": builder["record_id"],
        "builder_release_hash": builder["record_hash"],
        "task_partition": partition,
        "task_ref": task_ref,
        "task_hash": task_hash,
        "environment_ref": "environment:synthetic:v1",
        "environment_hash": _artifact("environment:synthetic:v1"),
        "runner_ref": "runner:simulation:v1",
        "runner_hash": _artifact("runner:simulation:v1"),
        "exposure_state_ref": "exposure:ledger:v1",
        "exposure_state_hash": _artifact("exposure:ledger:v1"),
        "partition": partition,
        "surface_refs": ["subject-output", "task-input", "runner-trace"],
        "artifact_hash": _hash(
            {"evidence_id": evidence_id, "commitment": commitment_value},
            domain="ael-cep-evidence-commitment",
        ),
        # Bridge evidence is retained and dual-scored before the comparison
        # record is sealed; the core bridge validator therefore accepts only
        # an observed/retained evidence status here.  Confirmation evidence
        # remains sealed until the final promotion decision consumes it.
        "status": "observed" if partition in {"screening", "bridge"} else "sealed",
        "tainted": bool(tainted),
    }


def _aggregate_arm_scenario(
    protocol: Mapping[str, Any], scenario: str, arm: str, *, partition: str = "screening"
) -> dict[str, Any]:
    task_count, replicate_count = _scenario_runtime(protocol, scenario)
    aggregate = _new_metrics()
    for replicate in range(replicate_count):
        rep_metrics, _ = _simulate_arm_scenario(
            protocol,
            scenario,
            arm,
            replicate,
            task_count,
            replicate_count=replicate_count,
            clock_start=DEFAULT_CLOCK_START,
            partition=partition,
        )
        _merge_metrics(aggregate, rep_metrics)
    return _finalize_metrics(aggregate, scenario=scenario, arm=arm)


def simulate(protocol: Mapping[str, Any]) -> dict[str, Any]:
    """Generate and validate one deterministic AEL-CEP trajectory bundle."""

    frozen = core.freeze_protocol(protocol)
    scenario_names = _scenario_names(frozen["simulation"]["scenarios"])
    if not scenario_names:
        raise SimulatorError("at least one scenario is required")
    total_cells = 0
    for scenario in scenario_names:
        task_count, replicate_count = _scenario_runtime(frozen, scenario)
        total_cells += task_count * replicate_count * len(ARM_ORDER)
    if total_cells > MAX_SIMULATION_CELLS:
        raise SimulatorError(
            f"simulation cell count {total_cells} exceeds product cap {MAX_SIMULATION_CELLS}"
        )
    seed = int(frozen["simulation"]["seed"])
    ledger = _Ledger(frozen)
    promotion_scenario = next(
        (
            name
            for name in ("useful", "null", "shared_blind_spot", "evaluator_exploit", "poisoning")
            if name in scenario_names
        ),
        scenario_names[0],
    )
    promotion_metrics = _aggregate_arm_scenario(frozen, promotion_scenario, "A5")
    screening_metrics = {
        arm: _aggregate_arm_scenario(frozen, promotion_scenario, arm) for arm in ARM_ORDER
    }
    # Confirmation is a distinct prospective sample.  Its domain-separated
    # partition stream prevents screening exposure or score changes from
    # rewriting the sealed anchor outcome.
    confirmation_metrics = _aggregate_arm_scenario(
        frozen, promotion_scenario, "A5", partition="confirmation"
    )
    candidate_screening_metrics = _aggregate_arm_scenario(
        frozen, promotion_scenario, "A5", partition="screening_candidate"
    )

    builders: dict[str, dict[str, Any]] = {}
    evaluators: dict[str, dict[str, Any]] = {}
    for arm in ARM_ORDER:
        builder = ledger.add(
            "builder_release", f"builder:{arm}:v1", _release_payload("builder", f"builder:{arm}:v1")
        )
        evaluator = ledger.add(
            "evaluator_release",
            f"evaluator:{arm}:v1",
            _release_payload("evaluator", f"evaluator:{arm}:v1"),
        )
        builders[arm] = builder
        evaluators[arm] = evaluator
    _challenger_record = ledger.add(
        "challenger_release", "challenger:A5:v1", _release_payload("challenger", "challenger:A5:v1")
    )
    anchor = ledger.add(
        "anchor_release", "anchor:protected:v1", _release_payload("anchor", "anchor:protected:v1")
    )
    method = ledger.add(
        "measurement_method",
        "method:anchor-utility:v1",
        {
            "method_id": "method:anchor-utility:v1",
            "revision": "stage0-v1",
            "artifact_hash": _artifact("method:anchor-utility:v1"),
            "construct": "prospective utility",
            "oracle": "arm-blinded-anchor-truth",
            "parser": "bounded-float-parser",
            "aggregation": "equal-task-mean",
            "validity": "synthetic-operating-characteristic",
            "reliability": "deterministic-stream",
            "custody": "synthetic:measurement:custody",
        },
    )

    bindings: dict[str, dict[str, Any]] = {}
    evidences: dict[str, dict[str, Any]] = {}
    scores: dict[str, dict[str, Any]] = {}
    for arm in ARM_ORDER:
        binding_id = f"binding:{arm}:screening:v1"
        evidence_id = f"evidence:{arm}:screening:sample"
        evidence = ledger.add(
            "subject_execution_evidence",
            evidence_id,
            _evidence_payload(
                evidence_id,
                builders[arm],
                "screening",
                commitment={
                    "seed": seed,
                    "scenario": promotion_scenario,
                    "arm": arm,
                    "partition": "screening",
                    "summary": screening_metrics[arm],
                },
                tainted=promotion_scenario in {"feedback_leakage", "poisoning"},
            ),
            {builders[arm]["record_id"]: builders[arm]["record_hash"]},
        )
        binding_payload = _binding_payload(
            frozen,
            binding_id,
            builders[arm],
            evaluators[arm],
            method,
            evidence,
            "screening",
        )
        binding = ledger.add(
            "evaluation_binding",
            binding_id,
            binding_payload,
            {
                builders[arm]["record_id"]: builders[arm]["record_hash"],
                evaluators[arm]["record_id"]: evaluators[arm]["record_hash"],
                method["record_id"]: method["record_hash"],
                evidence["record_id"]: evidence["record_hash"],
            },
        )
        score_id = f"score:{arm}:screening:original"
        score = ledger.add(
            "score_run",
            score_id,
            {
                "score_run_id": score_id,
                "binding_ref": binding_id,
                "binding_hash": binding["record_hash"],
                "evidence_ref": evidence_id,
                "evidence_hash": evidence["record_hash"],
                "evaluator_release_ref": evaluators[arm]["record_id"],
                "evaluator_release_hash": evaluators[arm]["record_hash"],
                "builder_release_ref": builders[arm]["record_id"],
                "builder_release_hash": builders[arm]["record_hash"],
                "method_ref": method["record_id"],
                "method_hash": method["record_hash"],
                "score": screening_metrics[arm]["evaluator_score_mean"] or 0.0,
                "score_status": "observed",
                "scoring_actor": frozen["principals"]["adjudication"]["principal_id"],
                "partition": "screening",
                "surface_refs": ["subject-output", "task-input", "runner-trace"],
                "critical_failure": False,
                "score_key": f"sample:{arm}",
                "exposure_policy": "screening_feedback_only",
            },
            {
                binding_id: binding["record_hash"],
                evidence_id: evidence["record_hash"],
                evaluators[arm]["record_id"]: evaluators[arm]["record_hash"],
                builders[arm]["record_id"]: builders[arm]["record_hash"],
                method["record_id"]: method["record_hash"],
            },
        )
        bindings[arm] = binding
        evidences[arm] = evidence
        scores[arm] = score

    # The positive promotion lineage is the bridge's new Builder generation.
    # Create it before confirmation artifacts so every promotion-bound pack
    # can name and hash the exact generation that the bridge validated.
    bridge_builder_payload = _release_payload("builder", "builder:A5:v2", parent=builders["A5"])
    bridge_builder_payload["revision"] = "stage0-v2-bridge"
    bridge_builder = ledger.add(
        "builder_release",
        "builder:A5:v2",
        bridge_builder_payload,
        {builders["A5"]["record_id"]: builders["A5"]["record_hash"]},
    )
    promotion_candidate = bridge_builder

    # Promotion lifecycle starts with the stable B1 candidate registration.
    # Screening evidence is deliberately produced only after this
    # candidate-only development eligibility transition; otherwise a later
    # screen could be mistaken for evidence that existed before registration.
    effect_attempts: list[dict[str, Any]] = []
    candidate_gate = False
    promotion_state = "registered"
    promotion_hash = _ZERO_HASH
    promotion_ref: str | None = None

    def append_promotion_transition(
        index: int,
        to_state: str,
        *,
        evidence_extra: Mapping[str, str] | None = None,
        bridge_status: str = "new_epoch_not_comparable",
        confirmation_status: str = "not_opened",
        effect_attempt: bool = False,
        critical_failure: bool = False,
        revoked_ancestry: bool = False,
    ) -> dict[str, Any]:
        nonlocal promotion_state, promotion_hash, promotion_ref
        promotion_evidence: dict[str, str] = {
            promotion_candidate["record_id"]: promotion_candidate["record_hash"],
        }
        if effect_attempts:
            promotion_evidence.update(
                {
                    item["record_id"]: item["record_hash"]
                    for item in effect_attempts
                    if item["payload"]["candidate_ref"] == promotion_candidate["record_id"]
                }
            )
        if evidence_extra:
            promotion_evidence.update(evidence_extra)
        transition_id = f"promotion:A5:{index}:{to_state}"
        transition_payload = {
            "transition_id": transition_id,
            "candidate_ref": promotion_candidate["record_id"],
            "candidate_hash": promotion_candidate["record_hash"],
            "from_state": promotion_state,
            "to_state": to_state,
            "predecessor_transition_hash": promotion_hash,
            "actor": "synthetic:release-governance",
            "approval_actor": frozen["principals"]["promotion"]["principal_id"],
            "independence": {
                dimension: "separate"
                for dimension in frozen["independence"]["protected_dimensions"]
            },
            "confirmation_status": confirmation_status,
            "bridge_status": bridge_status,
            "critical_failure": critical_failure,
            "effect_attempt": effect_attempt,
            "revoked_ancestry": revoked_ancestry,
            "reason": (
                f"scenario={promotion_scenario}; "
                f"candidate_eligible={candidate_gate}; "
                f"anchor=sealed_later; "
                f"score={candidate_screening_metrics['evaluator_score_mean']}"
            ),
            "evidence_refs": sorted(promotion_evidence),
        }
        if promotion_ref is not None:
            transition_payload["predecessor_transition_ref"] = promotion_ref
            promotion_evidence[promotion_ref] = promotion_hash
            transition_payload["evidence_refs"] = sorted(promotion_evidence)
        transition = ledger.add(
            "promotion_transition", transition_id, transition_payload, promotion_evidence
        )
        promotion_state = to_state
        promotion_hash = transition["record_hash"]
        promotion_ref = transition["record_id"]
        return transition

    append_promotion_transition(0, "development_eligible")

    # B1 is the generation that the bridge validates and the promotion state
    # machine addresses.  Retain a distinct screening execution for B1 before
    # its screening-pass/development transitions; B0's screening record is
    # historical context, not a relabelled decision about B1.
    candidate_screening_evidence_id = "evidence:A5:screening:candidate-v2"
    candidate_screening_evidence = ledger.add(
        "subject_execution_evidence",
        candidate_screening_evidence_id,
        _evidence_payload(
            candidate_screening_evidence_id,
            promotion_candidate,
            "screening",
            commitment={
                "seed": seed,
                "scenario": promotion_scenario,
                "arm": "A5",
                "partition": "screening_candidate",
                "candidate_generation": "b1",
                "summary": candidate_screening_metrics,
            },
            tainted=bool(candidate_screening_metrics["tainted"]),
        ),
        {promotion_candidate["record_id"]: promotion_candidate["record_hash"]},
    )
    candidate_screening_binding_id = "binding:A5:screening:candidate-v2"
    candidate_screening_binding = ledger.add(
        "evaluation_binding",
        candidate_screening_binding_id,
        _binding_payload(
            frozen,
            candidate_screening_binding_id,
            promotion_candidate,
            evaluators["A5"],
            method,
            candidate_screening_evidence,
            "screening",
        ),
        {
            promotion_candidate["record_id"]: promotion_candidate["record_hash"],
            evaluators["A5"]["record_id"]: evaluators["A5"]["record_hash"],
            method["record_id"]: method["record_hash"],
            candidate_screening_evidence["record_id"]: candidate_screening_evidence["record_hash"],
        },
    )
    candidate_screening_score = ledger.add(
        "score_run",
        "score:A5:screening:candidate-v2",
        {
            "score_run_id": "score:A5:screening:candidate-v2",
            "binding_ref": candidate_screening_binding_id,
            "binding_hash": candidate_screening_binding["record_hash"],
            "evidence_ref": candidate_screening_evidence_id,
            "evidence_hash": candidate_screening_evidence["record_hash"],
            "evaluator_release_ref": evaluators["A5"]["record_id"],
            "evaluator_release_hash": evaluators["A5"]["record_hash"],
            "builder_release_ref": promotion_candidate["record_id"],
            "builder_release_hash": promotion_candidate["record_hash"],
            "method_ref": method["record_id"],
            "method_hash": method["record_hash"],
            "score": candidate_screening_metrics["evaluator_score_mean"] or 0.0,
            "score_status": "observed",
            "scoring_actor": frozen["principals"]["adjudication"]["principal_id"],
            "partition": "screening",
            "surface_refs": ["subject-output", "task-input", "runner-trace"],
            "critical_failure": bool(candidate_screening_metrics["critical_failures"]),
            "score_key": "sample:A5:candidate-v2",
            "exposure_policy": "screening_feedback_only",
        },
        {
            candidate_screening_binding_id: candidate_screening_binding["record_hash"],
            candidate_screening_evidence_id: candidate_screening_evidence["record_hash"],
            evaluators["A5"]["record_id"]: evaluators["A5"]["record_hash"],
            promotion_candidate["record_id"]: promotion_candidate["record_hash"],
            method["record_id"]: method["record_hash"],
        },
    )
    candidate_screening_refs = {
        candidate_screening_evidence["record_id"]: candidate_screening_evidence["record_hash"],
        candidate_screening_binding["record_id"]: candidate_screening_binding["record_hash"],
        candidate_screening_score["record_id"]: candidate_screening_score["record_hash"],
    }

    exposure = ledger.add(
        "exposure_event",
        "exposure:A5:screening:v1",
        {
            "exposure_id": "exposure:A5:screening:v1",
            "target_ref": candidate_screening_score["record_id"],
            "target_hash": candidate_screening_score["record_hash"],
            "partition": "screening",
            "exposure_kind": (
                "feedback-leakage"
                if promotion_scenario == "feedback_leakage"
                else "poisoning"
                if promotion_scenario == "poisoning"
                else "aggregate-score-feedback"
            ),
            "amount": 1,
            "tainted": promotion_scenario in {"feedback_leakage", "poisoning"},
        },
        {candidate_screening_score["record_id"]: candidate_screening_score["record_hash"]},
    )
    # The screening closure is candidate-scoped: expose the exact exposure
    # event alongside B1's own evidence, binding, and observed score so a
    # later transition cannot silently omit feedback provenance.
    candidate_screening_refs[exposure["record_id"]] = exposure["record_hash"]
    # Advance the candidate through the screening gate only after its B1
    # evidence, binding, score, and exposure have been recorded.  Confirmation
    # remains a later phase and cannot depend on a sealed confirmation pack.
    candidate_gate = bool(
        candidate_screening_metrics["disposition"]["eligible"] > 0
        and not candidate_screening_metrics["tainted"]
        and not candidate_screening_metrics["critical_failures"]
        and not candidate_screening_metrics["forbidden_effect_attempted"]
        and not candidate_screening_metrics["optional_stopping"]
        and candidate_screening_metrics["score_observations"] > 0
        and candidate_screening_metrics["evaluator_score_mean"] is not None
        and candidate_screening_metrics["evaluator_score_mean"]
        >= float(frozen["decision_rule"]["threshold"])
    )
    screening_exposure_tainted = bool(exposure["payload"]["tainted"])
    candidate_gate = bool(
        candidate_screening_metrics["disposition"]["eligible"] > 0
        and not candidate_screening_metrics["tainted"]
        and not candidate_screening_metrics["critical_failures"]
        and not candidate_screening_metrics["forbidden_effect_attempted"]
        and not candidate_screening_metrics["optional_stopping"]
        and not screening_exposure_tainted
        and candidate_screening_metrics["score_observations"] > 0
        and candidate_screening_metrics["evaluator_score_mean"] is not None
        and candidate_screening_metrics["evaluator_score_mean"]
        >= float(frozen["decision_rule"]["threshold"])
    )
    if not candidate_gate:
        # No successful bridge_eligible transition exists for this candidate;
        # keep the shared panel code deterministic but prevent any bridge,
        # bridge-partition evidence, or bridge exposure from being ledger facts.
        ledger.suppressed_record_prefixes = (
            "evaluator:A5:v2",
            "evidence:A5:bridge:",
            "anchor-observation:A5:bridge:",
            "binding:A5:bridge:",
            "score:A5:bridge:",
            "exposure:A5:bridge:",
            "bridge:A5:",
            "comparability:A5:",
            "independence:A5:promotion:",
        )
    screening_targets = (
        ("screening_pass", "bridge_eligible")
        if candidate_gate
        else ("screening_reject",)
        if promotion_scenario != "forbidden_effect"
        else ()
    )
    for index, to_state in enumerate(screening_targets, start=1):
        append_promotion_transition(
            index,
            to_state,
            evidence_extra=candidate_screening_refs,
            critical_failure=(
                bool(candidate_screening_metrics["critical_failures"])
                if to_state == "screening_reject"
                else False
            ),
            revoked_ancestry=(
                bool(candidate_screening_metrics["tainted"] or screening_exposure_tainted)
                if to_state == "screening_reject"
                else False
            ),
        )

    bridge_evaluator_payload = _release_payload(
        "evaluator", "evaluator:A5:v2", parent=evaluators["A5"]
    )
    bridge_evaluator_payload["revision"] = "stage0-v2-bridge"
    bridge_evaluator = ledger.add(
        "evaluator_release",
        "evaluator:A5:v2",
        bridge_evaluator_payload,
        {evaluators["A5"]["record_id"]: evaluators["A5"]["record_hash"]},
    )

    # A bridge is a full 2x2 panel: old/new Builder generations crossed with
    # old/new Evaluator generations.  Each stratum retains paired execution
    # evidence for B0 and B1; all non-builder axes remain identical.  Anchor
    # truth is intentionally selected from the frozen truth family, not from
    # any evaluator score emitted by the screening trajectory.
    bridge_truth_scenario = _TRUTH_FAMILY.get(promotion_scenario, promotion_scenario)
    decision_threshold = float(frozen["decision_rule"]["threshold"])
    bridge_strata: list[dict[str, Any]] = []
    bridge_dependencies: dict[str, str] = {
        builders["A5"]["record_id"]: builders["A5"]["record_hash"],
        bridge_builder["record_id"]: bridge_builder["record_hash"],
        evaluators["A5"]["record_id"]: evaluators["A5"]["record_hash"],
        bridge_evaluator["record_id"]: bridge_evaluator["record_hash"],
        anchor["record_id"]: anchor["record_hash"],
    }
    weighted_global = 0.0
    weighted_interaction = 0.0
    weighted_decision = 0.0
    weighted_anchor = 0.0
    bridge_panels: list[dict[str, Any]] = []
    for stratum_config in frozen["bridge"]["strata"]:
        stratum = stratum_config["stratum"]
        weight = float(stratum_config["weight"])
        # Use separate domain-separated streams for protected truth and
        # evaluator perturbations.  The truth tuple therefore remains stable
        # when a cell's evaluator shift/noise is changed in a fixture.
        truth_values = _bridge_anchor_truth(
            seed,
            bridge_truth_scenario,
            stratum,
            decision_threshold,
        )
        cell_rng = SplitMix64(
            derive_stream_seed(
                seed,
                bridge_truth_scenario,
                0,
                "A5",
                f"bridge-cells:{stratum}",
                "evaluator_cells",
            )
        )
        values = _bridge_cell_scores(
            truth_values,
            decision_threshold=decision_threshold,
            rng=cell_rng,
        )
        if promotion_scenario == "shared_blind_spot":
            # Keep the protected anchor truth fixed while modelling a shared
            # evaluator blind spot: both E1 cells inherit a deterministic
            # positive shift that is large enough to fail the preregistered
            # bridge tolerance.  The perturbation is applied only to the
            # evaluator-cell stream; evidence and anchor records are emitted
            # from the independent subject-side truth stream below.
            values = {
                **values,
                "b0e1": _round(_clip(values["b0e1"] + 0.08)),
                "b1e1": _round(_clip(values["b1e1"] + 0.08)),
            }
        old_evidence_id = f"evidence:A5:bridge:{stratum}:b0"
        new_evidence_id = f"evidence:A5:bridge:{stratum}:b1"
        old_evidence = ledger.add(
            "subject_execution_evidence",
            old_evidence_id,
            _evidence_payload(
                old_evidence_id,
                builders["A5"],
                "bridge",
                commitment={
                    "seed": seed,
                    "scenario": promotion_scenario,
                    "arm": "A5",
                    "partition": "bridge",
                    "stratum": stratum,
                    "task_ref": f"task-pack:bridge:{stratum}:stage0",
                    "task_root_hash": stratum_config["task_root_hash"],
                    "builder_generation": "b0",
                    "truth_values": {"b0": truth_values[0], "b1": truth_values[1]},
                },
                tainted=promotion_scenario in {"feedback_leakage", "poisoning"},
            ),
            {builders["A5"]["record_id"]: builders["A5"]["record_hash"]},
        )
        new_evidence = ledger.add(
            "subject_execution_evidence",
            new_evidence_id,
            _evidence_payload(
                new_evidence_id,
                bridge_builder,
                "bridge",
                commitment={
                    "seed": seed,
                    "scenario": promotion_scenario,
                    "arm": "A5",
                    "partition": "bridge",
                    "stratum": stratum,
                    "task_ref": f"task-pack:bridge:{stratum}:stage0",
                    "task_root_hash": stratum_config["task_root_hash"],
                    "builder_generation": "b1",
                    "truth_values": {"b0": truth_values[0], "b1": truth_values[1]},
                },
                tainted=promotion_scenario in {"feedback_leakage", "poisoning"},
            ),
            {bridge_builder["record_id"]: bridge_builder["record_hash"]},
        )
        bridge_dependencies.update(
            {
                old_evidence["record_id"]: old_evidence["record_hash"],
                new_evidence["record_id"]: new_evidence["record_hash"],
            }
        )
        evidence_for_cell = {
            "b0e0": old_evidence,
            "b0e1": old_evidence,
            "b1e0": new_evidence,
            "b1e1": new_evidence,
        }
        builder_for_cell = {
            "b0e0": builders["A5"],
            "b0e1": builders["A5"],
            "b1e0": bridge_builder,
            "b1e1": bridge_builder,
        }
        evaluator_for_cell = {
            "b0e0": evaluators["A5"],
            "b0e1": bridge_evaluator,
            "b1e0": evaluators["A5"],
            "b1e1": bridge_evaluator,
        }
        # Emit protected anchor facts before any evaluator binding/score facts.
        # Their record hashes then commit only to candidate, anchor release and
        # retained latent evidence—not to mutable evaluator-cell outputs.
        b0_anchor_value, b1_anchor_value = truth_values
        b0_anchor_id = f"anchor-observation:A5:bridge:{stratum}:b0"
        b0_anchor = ledger.add(
            "anchor_observation",
            b0_anchor_id,
            {
                "anchor_observation_id": b0_anchor_id,
                "candidate_ref": builders["A5"]["record_id"],
                "candidate_hash": builders["A5"]["record_hash"],
                "anchor_release_ref": anchor["record_id"],
                "anchor_release_hash": anchor["record_hash"],
                "evidence_ref": old_evidence["record_id"],
                "evidence_hash": old_evidence["record_hash"],
                "partition": "bridge",
                "authority": frozen["principals"]["anchor"]["principal_id"],
                "arm_blinded": True,
                "outcome": "prospective_utility",
                "value": b0_anchor_value,
                "critical_failure": False,
                "status": "observed",
            },
            {
                builders["A5"]["record_id"]: builders["A5"]["record_hash"],
                anchor["record_id"]: anchor["record_hash"],
                old_evidence["record_id"]: old_evidence["record_hash"],
            },
        )
        b1_anchor_id = f"anchor-observation:A5:bridge:{stratum}:b1"
        b1_anchor = ledger.add(
            "anchor_observation",
            b1_anchor_id,
            {
                "anchor_observation_id": b1_anchor_id,
                "candidate_ref": bridge_builder["record_id"],
                "candidate_hash": bridge_builder["record_hash"],
                "anchor_release_ref": anchor["record_id"],
                "anchor_release_hash": anchor["record_hash"],
                "evidence_ref": new_evidence["record_id"],
                "evidence_hash": new_evidence["record_hash"],
                "partition": "bridge",
                "authority": frozen["principals"]["anchor"]["principal_id"],
                "arm_blinded": True,
                "outcome": "prospective_utility",
                "value": b1_anchor_value,
                "critical_failure": False,
                "status": "observed",
            },
            {
                bridge_builder["record_id"]: bridge_builder["record_hash"],
                anchor["record_id"]: anchor["record_hash"],
                new_evidence["record_id"]: new_evidence["record_hash"],
            },
        )
        bridge_dependencies.update(
            {
                b0_anchor["record_id"]: b0_anchor["record_hash"],
                b1_anchor["record_id"]: b1_anchor["record_hash"],
            }
        )
        bridge_panels.append(
            {
                "stratum": stratum,
                "weight": weight,
                "values": values,
                "truth_values": truth_values,
                "evidence_for_cell": evidence_for_cell,
                "builder_for_cell": builder_for_cell,
                "evaluator_for_cell": evaluator_for_cell,
                "old_evidence": old_evidence,
                "new_evidence": new_evidence,
                "b0_anchor": b0_anchor,
                "b1_anchor": b1_anchor,
            }
        )

    # Score/binding records are emitted only after every protected evidence
    # and anchor fact in the panel exists.  This isolates anchor record hashes
    # from later evaluator-cell perturbations while retaining one hash chain.
    for panel in bridge_panels:
        stratum = panel["stratum"]
        weight = panel["weight"]
        values = panel["values"]
        evidence_for_cell = panel["evidence_for_cell"]
        builder_for_cell = panel["builder_for_cell"]
        evaluator_for_cell = panel["evaluator_for_cell"]
        old_evidence = panel["old_evidence"]
        new_evidence = panel["new_evidence"]
        b0_anchor = panel["b0_anchor"]
        b1_anchor = panel["b1_anchor"]
        cells: dict[str, dict[str, Any]] = {}
        for cell in ("b0e0", "b0e1", "b1e0", "b1e1"):
            evidence = evidence_for_cell[cell]
            builder = builder_for_cell[cell]
            evaluator = evaluator_for_cell[cell]
            binding_id = f"binding:A5:bridge:{stratum}:{cell}"
            binding = ledger.add(
                "evaluation_binding",
                binding_id,
                _binding_payload(
                    frozen,
                    binding_id,
                    builder,
                    evaluator,
                    method,
                    evidence,
                    "bridge",
                ),
                {
                    builder["record_id"]: builder["record_hash"],
                    evaluator["record_id"]: evaluator["record_hash"],
                    method["record_id"]: method["record_hash"],
                    evidence["record_id"]: evidence["record_hash"],
                },
            )
            bridge_dependencies[binding["record_id"]] = binding["record_hash"]
            score_id = f"score:A5:bridge:{stratum}:{cell}"
            score = ledger.add(
                "score_run",
                score_id,
                {
                    "score_run_id": score_id,
                    "binding_ref": binding_id,
                    "binding_hash": binding["record_hash"],
                    "evidence_ref": evidence["record_id"],
                    "evidence_hash": evidence["record_hash"],
                    "evaluator_release_ref": evaluator["record_id"],
                    "evaluator_release_hash": evaluator["record_hash"],
                    "builder_release_ref": builder["record_id"],
                    "builder_release_hash": builder["record_hash"],
                    "method_ref": method["record_id"],
                    "method_hash": method["record_hash"],
                    "score": values[cell],
                    "score_status": "observed",
                    "scoring_actor": frozen["principals"]["adjudication"]["principal_id"],
                    "partition": "bridge",
                    "surface_refs": ["subject-output", "task-input", "runner-trace"],
                    "critical_failure": False,
                    "score_key": f"bridge:{stratum}:{cell}",
                    "exposure_policy": "sealed_single_use",
                },
                {
                    binding_id: binding["record_hash"],
                    evidence["record_id"]: evidence["record_hash"],
                    evaluator["record_id"]: evaluator["record_hash"],
                    builder["record_id"]: builder["record_hash"],
                    method["record_id"]: method["record_hash"],
                },
            )
            cells[cell] = score
            bridge_dependencies[score["record_id"]] = score["record_hash"]
        # Keep a distinct, non-feedback exposure fact for each sealed bridge
        # stratum.  It targets that row's B1/E1 score and is included in the
        # bridge dependency graph before the panel is sealed.
        bridge_exposure_id = f"exposure:A5:bridge:{stratum}"
        bridge_exposure = ledger.add(
            "exposure_event",
            bridge_exposure_id,
            {
                "exposure_id": bridge_exposure_id,
                "target_ref": cells["b1e1"]["record_id"],
                "target_hash": cells["b1e1"]["record_hash"],
                "partition": "bridge",
                "exposure_kind": "sealed-bridge-observation",
                "amount": 1,
                "tainted": False,
            },
            {cells["b1e1"]["record_id"]: cells["b1e1"]["record_hash"]},
        )
        bridge_dependencies[bridge_exposure["record_id"]] = bridge_exposure["record_hash"]
        panel["bridge_exposure"] = bridge_exposure
        global_value = ((values["b0e1"] - values["b0e0"]) + (values["b1e1"] - values["b1e0"])) / 2.0
        interaction_value = (values["b1e1"] - values["b0e1"]) - (values["b1e0"] - values["b0e0"])
        decision_value = 0.5 * float(
            (values["b0e0"] >= decision_threshold) == (values["b0e1"] >= decision_threshold)
        ) + 0.5 * float(
            (values["b1e0"] >= decision_threshold) == (values["b1e1"] >= decision_threshold)
        )
        b0_anchor_decision = b0_anchor["payload"]["value"] >= decision_threshold
        b1_anchor_decision = b1_anchor["payload"]["value"] >= decision_threshold
        anchor_value_agreement = 0.25 * sum(
            (
                float((values["b0e0"] >= decision_threshold) == b0_anchor_decision),
                float((values["b0e1"] >= decision_threshold) == b0_anchor_decision),
                float((values["b1e0"] >= decision_threshold) == b1_anchor_decision),
                float((values["b1e1"] >= decision_threshold) == b1_anchor_decision),
            )
        )
        weighted_global += weight * global_value
        weighted_interaction += weight * interaction_value
        weighted_decision += weight * decision_value
        weighted_anchor += weight * anchor_value_agreement
        bridge_strata.append(
            {
                "stratum": stratum,
                "weight": weight,
                "old_evidence_ref": old_evidence["record_id"],
                "old_evidence_hash": old_evidence["record_hash"],
                "new_evidence_ref": new_evidence["record_id"],
                "new_evidence_hash": new_evidence["record_hash"],
                **{
                    f"{cell}_score_ref": cells[cell]["record_id"]
                    for cell in ("b0e0", "b0e1", "b1e0", "b1e1")
                },
                **{
                    f"{cell}_score_hash": cells[cell]["record_hash"]
                    for cell in ("b0e0", "b0e1", "b1e0", "b1e1")
                },
                "b0_anchor_ref": b0_anchor["record_id"],
                "b0_anchor_hash": b0_anchor["record_hash"],
                "b1_anchor_ref": b1_anchor["record_id"],
                "b1_anchor_hash": b1_anchor["record_hash"],
            }
        )
    bridge_global = weighted_global
    bridge_interaction = weighted_interaction
    bridge_agreement = weighted_decision
    bridge_anchor_agreement = weighted_anchor
    bridge_pass = bool(
        abs(bridge_global) <= float(frozen["bridge"]["global_shift_tolerance"])
        and abs(bridge_interaction) <= float(frozen["bridge"]["interaction_tolerance"])
        and bridge_agreement >= float(frozen["bridge"]["decision_agreement_min"])
        and bridge_anchor_agreement >= float(frozen["bridge"]["decision_agreement_min"])
    )
    bridge_outcome = "bridge_comparable" if bridge_pass else "new_epoch_not_comparable"
    if not candidate_gate:
        # Screening rejection is terminal for this candidate; no bridge was
        # attempted, so expose an explicit zero-attempt outcome downstream.
        bridge_pass = False
        bridge_outcome = "new_epoch_not_comparable"
    # The top-level panel anchors are retained for compact consumers; the
    # authoritative per-stratum cells below carry the complete weighted
    # derivation.  They point to the lexicographically first frozen stratum.
    panel_anchor = bridge_strata[0]
    bridge = ledger.add(
        "bridge_observation",
        "bridge:A5:evaluator:v1",
        {
            "bridge_id": "bridge:A5:evaluator:v1",
            "old_builder_ref": builders["A5"]["record_id"],
            "old_builder_hash": builders["A5"]["record_hash"],
            "new_builder_ref": bridge_builder["record_id"],
            "new_builder_hash": bridge_builder["record_hash"],
            "old_evaluator_ref": evaluators["A5"]["record_id"],
            "old_evaluator_hash": evaluators["A5"]["record_hash"],
            "new_evaluator_ref": bridge_evaluator["record_id"],
            "new_evaluator_hash": bridge_evaluator["record_hash"],
            "old_evidence_ref": panel_anchor["old_evidence_ref"],
            "old_evidence_hash": panel_anchor["old_evidence_hash"],
            "new_evidence_ref": panel_anchor["new_evidence_ref"],
            "new_evidence_hash": panel_anchor["new_evidence_hash"],
            "old_builder_old_evaluator_score_ref": panel_anchor["b0e0_score_ref"],
            "old_builder_old_evaluator_score_hash": panel_anchor["b0e0_score_hash"],
            "old_builder_new_evaluator_score_ref": panel_anchor["b0e1_score_ref"],
            "old_builder_new_evaluator_score_hash": panel_anchor["b0e1_score_hash"],
            "new_builder_old_evaluator_score_ref": panel_anchor["b1e0_score_ref"],
            "new_builder_old_evaluator_score_hash": panel_anchor["b1e0_score_hash"],
            "new_builder_new_evaluator_score_ref": panel_anchor["b1e1_score_ref"],
            "new_builder_new_evaluator_score_hash": panel_anchor["b1e1_score_hash"],
            "anchor_release_ref": anchor["record_id"],
            "anchor_release_hash": anchor["record_hash"],
            "decision_threshold": decision_threshold,
            "global_shift_interval": [bridge_global, bridge_global],
            "interaction_interval": [bridge_interaction, bridge_interaction],
            "decision_agreement": bridge_agreement,
            "anchor_agreement": bridge_anchor_agreement,
            "construct_evidence": "synthetic_pass" if bridge_pass else "synthetic_fail",
            "reliability_evidence": "synthetic_pass" if bridge_pass else "synthetic_fail",
            "strata": bridge_strata,
            "outcome": bridge_outcome,
        },
        bridge_dependencies,
    )
    bridge_decision = ledger.add(
        "comparability_decision",
        "comparability:A5:evaluator:v1",
        {
            "decision_id": "comparability:A5:evaluator:v1",
            "bridge_ref": bridge["record_id"],
            "bridge_hash": bridge["record_hash"],
            "outcome": bridge_outcome,
            "reason": "derived from the observed frozen bridge panel and protected bridge anchors",
            "eligible": bridge_pass,
        },
        {bridge["record_id"]: bridge["record_hash"]},
    )
    independence = ledger.add(
        "independence_assessment",
        "independence:A5:promotion:v1",
        {
            "assessment_id": "independence:A5:promotion:v1",
            "claim_ref": promotion_candidate["record_id"],
            "stage": "bridge",
            "dimensions": {
                dimension: "separate"
                for dimension in frozen["independence"]["protected_dimensions"]
            },
            "overall": "separate",
            "authority": frozen["principals"]["adjudication"]["principal_id"],
            "evidence_refs": [
                bridge["record_id"],
                bridge_decision["record_id"],
            ],
        },
        {
            bridge["record_id"]: bridge["record_hash"],
            bridge_decision["record_id"]: bridge_decision["record_hash"],
        },
    )
    # One legal promotion chain is retained only when the selected scenario's
    # observed trajectory satisfies the same gates represented in the summary.
    confirmation_eligible_allowed = bool(candidate_gate and bridge_pass)
    if candidate_gate and not bridge_pass:
        # A failed bridge opens a fresh measurement epoch.  Do not emit a
        # confirmation pack or infer a final decision from a non-comparable
        # panel; the terminal transition is explicitly downstream of the
        # observed bridge and its comparability decision.
        append_promotion_transition(
            len(screening_targets) + 1,
            "new_measurement_epoch",
            evidence_extra={
                bridge["record_id"]: bridge["record_hash"],
                bridge_decision["record_id"]: bridge_decision["record_hash"],
                independence["record_id"]: independence["record_hash"],
            },
            bridge_status=bridge_outcome,
        )
    final_anchor_pass = bool(
        confirmation_metrics["anchor_utility_mean"] is not None
        and confirmation_metrics["anchor_utility_mean"]
        >= float(frozen["decision_rule"]["threshold"])
        and confirmation_metrics["critical_failures"] == 0
        and confirmation_metrics["tainted"] == 0
        and confirmation_metrics["forbidden_effect_attempted"] == 0
    )
    promotion_allowed = bool(confirmation_eligible_allowed and final_anchor_pass)

    if confirmation_eligible_allowed:
        append_promotion_transition(
            len(screening_targets) + 1,
            "confirmation_eligible",
            evidence_extra={
                bridge["record_id"]: bridge["record_hash"],
                bridge_decision["record_id"]: bridge_decision["record_hash"],
                independence["record_id"]: independence["record_hash"],
            },
            bridge_status=bridge_outcome,
        )

    # Confirmation is opened only after the pre-confirmation gate, for the
    # final promote/reject decision.  In
    # particular, scenarios with tainted, missing, harmful, or below-threshold
    # outcomes do not get an unconsumed sealed pack that could be mistaken for
    # evidence.  The bridge's B1 Builder remains the stable candidate key.
    if confirmation_eligible_allowed:
        confirmation_evidence_id = "evidence:A5:confirmation:pack"
        confirmation_evidence = ledger.add(
            "subject_execution_evidence",
            confirmation_evidence_id,
            _evidence_payload(
                confirmation_evidence_id,
                promotion_candidate,
                "confirmation",
                commitment={
                    "seed": seed,
                    "scenario": promotion_scenario,
                    "arm": "A5",
                    "partition": "confirmation",
                    "summary": confirmation_metrics,
                    "sample_root": "task-pack:confirmation:stage0",
                },
            ),
            {promotion_candidate["record_id"]: promotion_candidate["record_hash"]},
        )
        confirmation_binding_id = "binding:A5:confirmation:v1"
        confirmation_binding = ledger.add(
            "evaluation_binding",
            confirmation_binding_id,
            _binding_payload(
                frozen,
                confirmation_binding_id,
                promotion_candidate,
                evaluators["A5"],
                method,
                confirmation_evidence,
                "confirmation",
            ),
            {
                promotion_candidate["record_id"]: promotion_candidate["record_hash"],
                evaluators["A5"]["record_id"]: evaluators["A5"]["record_hash"],
                method["record_id"]: method["record_hash"],
                confirmation_evidence["record_id"]: confirmation_evidence["record_hash"],
            },
        )
        _confirmation_score = ledger.add(
            "score_run",
            "score:A5:confirmation:observed",
            {
                "score_run_id": "score:A5:confirmation:observed",
                "binding_ref": confirmation_binding_id,
                "binding_hash": confirmation_binding["record_hash"],
                "evidence_ref": confirmation_evidence_id,
                "evidence_hash": confirmation_evidence["record_hash"],
                "evaluator_release_ref": evaluators["A5"]["record_id"],
                "evaluator_release_hash": evaluators["A5"]["record_hash"],
                "builder_release_ref": promotion_candidate["record_id"],
                "builder_release_hash": promotion_candidate["record_hash"],
                "method_ref": method["record_id"],
                "method_hash": method["record_hash"],
                "score": confirmation_metrics["evaluator_score_mean"] or 0.0,
                "score_status": "observed",
                "scoring_actor": frozen["principals"]["adjudication"]["principal_id"],
                "partition": "confirmation",
                "surface_refs": ["subject-output", "task-input", "runner-trace"],
            },
            {
                confirmation_binding_id: confirmation_binding["record_hash"],
                confirmation_evidence_id: confirmation_evidence["record_hash"],
                evaluators["A5"]["record_id"]: evaluators["A5"]["record_hash"],
                promotion_candidate["record_id"]: promotion_candidate["record_hash"],
                method["record_id"]: method["record_hash"],
            },
        )
        consumption = ledger.add(
            "confirmation_consumption",
            "consumption:A5:confirmation:v1",
            {
                "consumption_id": "consumption:A5:confirmation:v1",
                "partition": "confirmation",
                "confirmation_ref": confirmation_evidence_id,
                "confirmation_hash": confirmation_evidence["record_hash"],
                "candidate_ref": promotion_candidate["record_id"],
                "candidate_hash": promotion_candidate["record_hash"],
                "authority": frozen["principals"]["confirmation"]["principal_id"],
                "consumed": True,
            },
            {
                confirmation_evidence_id: confirmation_evidence["record_hash"],
                promotion_candidate["record_id"]: promotion_candidate["record_hash"],
            },
        )
        anchor_observation = ledger.add(
            "anchor_observation",
            "anchor-observation:A5:confirmation:v1",
            {
                "anchor_observation_id": "anchor-observation:A5:confirmation:v1",
                "candidate_ref": promotion_candidate["record_id"],
                "candidate_hash": promotion_candidate["record_hash"],
                "anchor_release_ref": anchor["record_id"],
                "anchor_release_hash": anchor["record_hash"],
                "confirmation_consumption_ref": consumption["record_id"],
                "confirmation_consumption_hash": consumption["record_hash"],
                "partition": "confirmation",
                "authority": frozen["principals"]["anchor"]["principal_id"],
                "arm_blinded": True,
                "outcome": "prospective_utility",
                "value": confirmation_metrics["anchor_utility_mean"] or 0.0,
                "critical_failure": bool(confirmation_metrics["critical_failures"]),
                "status": "observed",
            },
            {
                promotion_candidate["record_id"]: promotion_candidate["record_hash"],
                anchor["record_id"]: anchor["record_hash"],
                consumption["record_id"]: consumption["record_hash"],
            },
        )
        promotion_independence = ledger.add(
            "independence_assessment",
            "independence:A5:promotion:final",
            {
                "assessment_id": "independence:A5:promotion:final",
                "claim_ref": promotion_candidate["record_id"],
                "stage": "confirmation",
                "dimensions": {
                    dimension: "separate"
                    for dimension in frozen["independence"]["protected_dimensions"]
                },
                "overall": "separate",
                "authority": frozen["principals"]["adjudication"]["principal_id"],
                "evidence_refs": [
                    anchor_observation["record_id"],
                    bridge["record_id"],
                    bridge_decision["record_id"],
                ],
            },
            {
                anchor_observation["record_id"]: anchor_observation["record_hash"],
                bridge["record_id"]: bridge["record_hash"],
                bridge_decision["record_id"]: bridge_decision["record_hash"],
            },
        )
    if confirmation_eligible_allowed:
        final_state = "promote" if promotion_allowed else "reject"
        append_promotion_transition(
            len(screening_targets) + 2,
            final_state,
            evidence_extra={
                confirmation_evidence["record_id"]: confirmation_evidence["record_hash"],
                confirmation_binding["record_id"]: confirmation_binding["record_hash"],
                _confirmation_score["record_id"]: _confirmation_score["record_hash"],
                anchor_observation["record_id"]: anchor_observation["record_hash"],
                bridge_decision["record_id"]: bridge_decision["record_hash"],
                promotion_independence["record_id"]: promotion_independence["record_hash"],
                consumption["record_id"]: consumption["record_hash"],
                exposure["record_id"]: exposure["record_hash"],
            },
            bridge_status=bridge_outcome,
            confirmation_status="single_use",
        )

    def emit_forbidden_chain(
        candidate: Mapping[str, Any],
        development: Mapping[str, Any],
        evidence: Mapping[str, Any],
        binding: Mapping[str, Any],
        score: Mapping[str, Any],
        chain_label: str,
    ) -> None:
        """Emit a candidate-keyed blocked-effect containment chain."""

        candidate_ref = candidate["record_id"]
        candidate_hash = candidate["record_hash"]
        base_evidence = {
            candidate_ref: candidate_hash,
            evidence["record_id"]: evidence["record_hash"],
            binding["record_id"]: binding["record_hash"],
            score["record_id"]: score["record_hash"],
        }
        _, replicate_count = _scenario_runtime(frozen, "forbidden_effect")
        local_effects: list[dict[str, Any]] = []
        for replicate in range(replicate_count):
            effect_request = {
                "candidate_ref": candidate_ref,
                "evidence_ref": evidence["record_id"],
                "binding_ref": binding["record_id"],
                "partition": "screening",
                "operation": "synthetic-forbidden-effect",
                "replicate": replicate,
            }
            effect_attempt_id = f"effect-attempt:{chain_label}:screening:r{replicate}"
            local_effects.append(
                ledger.add(
                    "effect_attempt",
                    effect_attempt_id,
                    {
                        "effect_attempt_id": effect_attempt_id,
                        "candidate_ref": candidate_ref,
                        "candidate_hash": candidate_hash,
                        "evidence_ref": evidence["record_id"],
                        "evidence_hash": evidence["record_hash"],
                        "binding_ref": binding["record_id"],
                        "binding_hash": binding["record_hash"],
                        "partition": "screening",
                        "observation_authority": frozen["principals"]["evidence"]["principal_id"],
                        "effect_request_hash": _hash(
                            effect_request, domain="ael-cep-effect-request"
                        ),
                        "idempotency_key_hash": _hash(
                            {"effect_attempt_id": effect_attempt_id, "request": effect_request},
                            domain="ael-cep-effect-idempotency",
                        ),
                        "disposition": "blocked",
                        "postcondition_status": "not_dispatched",
                        "reason_code": "forbidden_effect_policy",
                    },
                    {
                        candidate_ref: candidate_hash,
                        evidence["record_id"]: evidence["record_hash"],
                        binding["record_id"]: binding["record_hash"],
                    },
                )
            )
        effect_attempts.extend(local_effects)
        reject_evidence = dict(base_evidence)
        reject_evidence.update({item["record_id"]: item["record_hash"] for item in local_effects})
        reject_id = f"promotion:{chain_label}:1:screening_reject"
        ledger.add(
            "promotion_transition",
            reject_id,
            {
                "transition_id": reject_id,
                "candidate_ref": candidate_ref,
                "candidate_hash": candidate_hash,
                "from_state": "development_eligible",
                "to_state": "screening_reject",
                "predecessor_transition_ref": development["record_id"],
                "predecessor_transition_hash": development["record_hash"],
                "actor": "synthetic:release-governance",
                "approval_actor": frozen["principals"]["promotion"]["principal_id"],
                "independence": {
                    dimension: "separate"
                    for dimension in frozen["independence"]["protected_dimensions"]
                },
                "confirmation_status": "not_opened",
                "bridge_status": "new_epoch_not_comparable",
                "critical_failure": False,
                "effect_attempt": True,
                "revoked_ancestry": False,
                "reason": "forbidden_effect_blocked_before_dispatch",
                "evidence_refs": sorted(reject_evidence),
            },
            {
                **reject_evidence,
                development["record_id"]: development["record_hash"],
            },
        )

    if "forbidden_effect" in scenario_names:
        forbidden_candidate = ledger.add(
            "builder_release",
            "builder:A5:forbidden:v1",
            _release_payload("builder", "builder:A5:forbidden:v1", parent=builders["A5"]),
            {builders["A5"]["record_id"]: builders["A5"]["record_hash"]},
        )
        forbidden_development_id = "promotion:A5:forbidden:0:development_eligible"
        forbidden_development = ledger.add(
            "promotion_transition",
            forbidden_development_id,
            {
                "transition_id": forbidden_development_id,
                "candidate_ref": forbidden_candidate["record_id"],
                "candidate_hash": forbidden_candidate["record_hash"],
                "from_state": "registered",
                "to_state": "development_eligible",
                "predecessor_transition_hash": _ZERO_HASH,
                "actor": "synthetic:release-governance",
                "approval_actor": frozen["principals"]["promotion"]["principal_id"],
                "independence": {
                    dimension: "separate"
                    for dimension in frozen["independence"]["protected_dimensions"]
                },
                "confirmation_status": "not_opened",
                "bridge_status": "new_epoch_not_comparable",
                "critical_failure": False,
                "effect_attempt": False,
                "revoked_ancestry": False,
                "reason": "forbidden_effect_candidate_registered",
                "evidence_refs": [forbidden_candidate["record_id"]],
            },
            {forbidden_candidate["record_id"]: forbidden_candidate["record_hash"]},
        )
        forbidden_metrics = _aggregate_arm_scenario(frozen, "forbidden_effect", "A5")
        forbidden_evidence_id = "evidence:A5:forbidden:screening"
        forbidden_evidence = ledger.add(
            "subject_execution_evidence",
            forbidden_evidence_id,
            _evidence_payload(
                forbidden_evidence_id,
                forbidden_candidate,
                "screening",
                commitment={
                    "seed": seed,
                    "scenario": "forbidden_effect",
                    "arm": "A5",
                    "partition": "screening",
                    "summary": forbidden_metrics,
                },
            ),
            {forbidden_candidate["record_id"]: forbidden_candidate["record_hash"]},
        )
        forbidden_binding_id = "binding:A5:forbidden:screening"
        forbidden_binding = ledger.add(
            "evaluation_binding",
            forbidden_binding_id,
            _binding_payload(
                frozen,
                forbidden_binding_id,
                forbidden_candidate,
                evaluators["A5"],
                method,
                forbidden_evidence,
                "screening",
            ),
            {
                forbidden_candidate["record_id"]: forbidden_candidate["record_hash"],
                evaluators["A5"]["record_id"]: evaluators["A5"]["record_hash"],
                method["record_id"]: method["record_hash"],
                forbidden_evidence["record_id"]: forbidden_evidence["record_hash"],
            },
        )
        forbidden_score_id = "score:A5:forbidden:screening"
        forbidden_score = ledger.add(
            "score_run",
            forbidden_score_id,
            {
                "score_run_id": forbidden_score_id,
                "binding_ref": forbidden_binding_id,
                "binding_hash": forbidden_binding["record_hash"],
                "evidence_ref": forbidden_evidence["record_id"],
                "evidence_hash": forbidden_evidence["record_hash"],
                "evaluator_release_ref": evaluators["A5"]["record_id"],
                "evaluator_release_hash": evaluators["A5"]["record_hash"],
                "builder_release_ref": forbidden_candidate["record_id"],
                "builder_release_hash": forbidden_candidate["record_hash"],
                "method_ref": method["record_id"],
                "method_hash": method["record_hash"],
                "score": forbidden_metrics["evaluator_score_mean"] or 0.0,
                "score_status": "observed",
                "scoring_actor": frozen["principals"]["adjudication"]["principal_id"],
                "partition": "screening",
                "surface_refs": ["subject-output", "task-input", "runner-trace"],
                "critical_failure": False,
                "score_key": "forbidden:A5:screening",
                "exposure_policy": "screening_feedback_only",
            },
            {
                forbidden_binding_id: forbidden_binding["record_hash"],
                forbidden_evidence["record_id"]: forbidden_evidence["record_hash"],
                evaluators["A5"]["record_id"]: evaluators["A5"]["record_hash"],
                forbidden_candidate["record_id"]: forbidden_candidate["record_hash"],
                method["record_id"]: method["record_hash"],
            },
        )
        emit_forbidden_chain(
            forbidden_candidate,
            forbidden_development,
            forbidden_evidence,
            forbidden_binding,
            forbidden_score,
            "A5:forbidden",
        )

    # Aggregate trajectories.  Truth streams were generated separately for
    # each arm, while every scenario uses the same task/replicate coordinates.
    trajectory_metrics: dict[str, dict[str, Any]] = {}
    trajectory_summary_refs: dict[str, str] = {}
    overall = _new_metrics()
    for arm in ARM_ORDER:
        arm_metrics = _new_metrics()
        scenario_summaries: list[str] = []
        for scenario in scenario_names:
            aggregate = _aggregate_arm_scenario(frozen, scenario, arm)
            if arm == "A5" and scenario == promotion_scenario:
                # The representative bridge is the decision-bearing panel
                # for the selected promotion scenario.  Keep its trajectory
                # counts aligned with the observed panel outcome rather than
                # leaving the generic replicate-level bridge diagnostic to
                # report a pass after a failed shared-blind-spot bridge.
                if candidate_gate:
                    aggregate["bridge_pass"] = int(bool(bridge_pass)) * int(
                        aggregate.get("bridge_attempted", 0)
                    )
                    aggregate["bridge_fail"] = int(not bridge_pass) * int(
                        aggregate.get("bridge_attempted", 0)
                    )
                    aggregate["bridge_unknown"] = 0
                else:
                    aggregate["bridge_attempted"] = 0
                    aggregate["bridge_pass"] = 0
                    aggregate["bridge_fail"] = 0
                    aggregate["bridge_unknown"] = 0
                aggregate["promotion"] = {
                    "scenario": promotion_scenario,
                    "candidate_eligible": bool(promotion_metrics["promotion_candidate_eligible"]),
                    "promoted": bool(promotion_allowed),
                    "bridge": bridge_outcome,
                }
            summary_id = f"trajectory:{arm}:{scenario}"
            trajectory_summary = ledger.add(
                "trajectory_summary",
                summary_id,
                {
                    "summary_id": summary_id,
                    "arm": arm,
                    "scenario_ref": f"scenario:{scenario}",
                    "counts": _trajectory_counts(aggregate),
                    "primary_endpoint": {
                        "sum_ppm": int(aggregate["anchor_utility_sum"]),
                        "observed_count": int(aggregate["anchor_observations"]),
                    },
                    "budget": {
                        "target": aggregate["matched_cost_target"],
                        "actual": aggregate["matched_cost_actual"],
                        "delta": aggregate["matched_cost_delta"],
                    },
                },
            )
            trajectory_summary_refs[summary_id] = trajectory_summary["record_hash"]
            scenario_summaries.append(summary_id)
            _merge_metrics(arm_metrics, aggregate)
            _merge_metrics(overall, aggregate)
        arm_metrics = _finalize_metrics(arm_metrics, scenario="overall", arm=arm)
        if arm == "A5":
            arm_metrics["promotion"] = {
                "scenario": promotion_scenario,
                "candidate_eligible": bool(promotion_metrics["promotion_candidate_eligible"]),
                "promoted": bool(promotion_allowed),
                "bridge": bridge_outcome,
            }
        trajectory_metrics[arm] = arm_metrics

    overall = _finalize_metrics(overall, scenario="overall", arm="all")
    if "forbidden_effect" in scenario_names:
        attempted_effects = int(overall["forbidden_effect_attempted"])
        represented_effects = len(effect_attempts)
        bulk_count = max(0, attempted_effects - represented_effects)
        overall["forbidden_effect_bulk"] = {
            "count": bulk_count,
            "represented_count": represented_effects,
            "digest": _hash(
                {
                    "seed": seed,
                    "scenario": promotion_scenario,
                    "attempted": attempted_effects,
                    "represented_ids": [item["record_id"] for item in effect_attempts],
                },
                domain="ael-cep-effect-bulk",
            ),
        }
    comparison_metrics: dict[str, Any] = {}
    for contrast in frozen["contrasts"]:
        a = trajectory_metrics[contrast["arm_a"]]
        b = trajectory_metrics[contrast["arm_b"]]
        eligible = (
            contrast["estimand_kind"] == "component"
            or contrast["treatment"]["dimension"] == "policy_package"
        ) and "optional_stopping" not in scenario_names
        comparison_metrics[contrast["contrast_id"]] = {
            "arm_a": contrast["arm_a"],
            "arm_b": contrast["arm_b"],
            "estimand_kind": contrast["estimand_kind"],
            "treatment": contrast["treatment"],
            "eligible": eligible,
            "anchor_utility_delta": _round(
                (a["anchor_utility_mean"] or 0.0) - (b["anchor_utility_mean"] or 0.0)
            ),
            "ineligible_reason": (
                None
                if eligible
                else (
                    "optional_stopping_noncausal"
                    if "optional_stopping" in scenario_names
                    else "algorithm_or_budget_mismatch"
                )
            ),
        }
    overall["ineligible_contrasts"] = sum(
        1 for item in comparison_metrics.values() if not item["eligible"]
    )
    overall["contrasts"] = comparison_metrics
    overall["arms"] = trajectory_metrics
    overall["promotion"] = {
        "scenario": promotion_scenario,
        "arm": "A5",
        "candidate_eligible": bool(promotion_metrics["promotion_candidate_eligible"]),
        "promoted": bool(promotion_allowed),
        "bridge": bridge_outcome,
    }
    overall["scenarios"] = scenario_names
    overall["world_model_version"] = WORLD_MODEL_VERSION
    overall["rng_algorithm"] = RNG_ALGORITHM
    overall["simulated_clock"] = SIMULATION_CLOCK_VERSION
    overall["effect_policy"] = "forbidden"
    overall["forbidden_effect_accepted"] = 0

    # Append a later evaluator score without rewriting the original bytes.
    old_evaluator = evaluators["A0"]
    new_evaluator_payload = _release_payload("evaluator", "evaluator:A0:v2", parent=old_evaluator)
    new_evaluator_payload["revision"] = "stage0-v2-rescore"
    new_evaluator = ledger.add(
        "evaluator_release",
        "evaluator:A0:v2",
        new_evaluator_payload,
        {old_evaluator["record_id"]: old_evaluator["record_hash"]},
    )
    rescore_binding_id = "binding:A0:rescore:v2"
    rescore_binding_payload = _binding_payload(
        frozen,
        rescore_binding_id,
        builders["A0"],
        new_evaluator,
        method,
        evidences["A0"],
        "screening",
    )
    rescore_binding = ledger.add(
        "evaluation_binding",
        rescore_binding_id,
        rescore_binding_payload,
        {
            builders["A0"]["record_id"]: builders["A0"]["record_hash"],
            new_evaluator["record_id"]: new_evaluator["record_hash"],
            method["record_id"]: method["record_hash"],
            evidences["A0"]["record_id"]: evidences["A0"]["record_hash"],
        },
    )
    rescore_id = "score:A0:screening:rescore"
    ledger.add(
        "score_run",
        rescore_id,
        {
            "score_run_id": rescore_id,
            "binding_ref": rescore_binding_id,
            "binding_hash": rescore_binding["record_hash"],
            "evidence_ref": evidences["A0"]["record_id"],
            "evidence_hash": evidences["A0"]["record_hash"],
            "evaluator_release_ref": new_evaluator["record_id"],
            "evaluator_release_hash": new_evaluator["record_hash"],
            "builder_release_ref": builders["A0"]["record_id"],
            "builder_release_hash": builders["A0"]["record_hash"],
            "method_ref": method["record_id"],
            "method_hash": method["record_hash"],
            "score": _round((screening_metrics["A0"]["evaluator_score_mean"] or 0.0) + 0.01),
            "score_status": "observed",
            "scoring_actor": frozen["principals"]["adjudication"]["principal_id"],
            "partition": "screening",
            "surface_refs": ["subject-output", "task-input", "runner-trace"],
            "critical_failure": False,
            "score_key": "sample:A0",
            "exposure_policy": "screening_feedback_only",
        },
        {
            rescore_binding_id: rescore_binding["record_hash"],
            evidences["A0"]["record_id"]: evidences["A0"]["record_hash"],
            new_evaluator["record_id"]: new_evaluator["record_hash"],
            builders["A0"]["record_id"]: builders["A0"]["record_hash"],
            method["record_id"]: method["record_hash"],
        },
    )

    tombstone_targets = [evidences["A5"]["record_id"], scores["A5"]["record_id"]]
    tombstone_id = "tombstone:A5:sample:v1"
    ledger.add(
        "deletion_tombstone",
        tombstone_id,
        {
            "tombstone_id": tombstone_id,
            "targets": tombstone_targets,
            "authority": frozen["principals"]["evidence"]["principal_id"],
            "reason": "synthetic deletion drill",
            "descendant_policy": "revoke-or-unscorable-all-dependants",
            "deleted_surfaces": ["subject-output", "runner-trace"],
        },
        {
            target: next(
                record["record_hash"] for record in ledger.records if record["record_id"] == target
            )
            for target in tombstone_targets
        },
    )

    trajectory_payloads = [
        record["payload"]
        for record in ledger.records
        if record["record_type"] == "trajectory_summary"
    ]
    contrast_summary = core.derive_contrast_diagnostics(frozen, trajectory_payloads)
    summary_id = "contrast-summary:stage0"
    ledger.add(
        "contrast_summary",
        summary_id,
        {
            "summary_id": summary_id,
            "aggregation_version": core.CONTRAST_SUMMARY_AGGREGATION_VERSION,
            "contrasts": contrast_summary,
        },
        trajectory_summary_refs,
    )

    # The tombstone must be the final fact so no post-tombstone dependency is
    # created; it still revokes all prior descendants in the projection.
    bundle = core.create_bundle(
        frozen, bundle_id=f"trajectory-bundle:{frozen['protocol_id']}", records=ledger.records
    )
    validated = core.validate_bundle(bundle, protocol=frozen)
    return validated


def simulate_scenario(
    protocol: Mapping[str, Any], scenario: str, arm: str = "A0", replicate: int = 0
) -> dict[str, Any]:
    """Return one diagnostic trajectory projection without constructing a ledger."""

    frozen = core.freeze_protocol(protocol)
    if arm not in ARM_ORDER:
        raise SimulatorError(f"unknown arm {arm}")
    if scenario not in _scenario_names(frozen["simulation"]["scenarios"]):
        raise SimulatorError(f"scenario {scenario} is not frozen in the protocol")
    task_count, replicate_count = _scenario_runtime(frozen, scenario)
    if (
        isinstance(replicate, bool)
        or not isinstance(replicate, int)
        or replicate < 0
        or replicate >= replicate_count
    ):
        raise SimulatorError(
            f"replicate must be an integer in 0..{replicate_count - 1} for scenario {scenario}"
        )
    metrics, observations = _simulate_arm_scenario(
        frozen,
        scenario,
        arm,
        replicate,
        task_count,
        replicate_count=replicate_count,
        clock_start=DEFAULT_CLOCK_START,
    )
    return {
        "metrics": metrics,
        "observations": observations,
        "world_model_version": WORLD_MODEL_VERSION,
        "rng_algorithm": RNG_ALGORITHM,
    }


# Simulator helpers are implementation details behind the supported CLI/file
# contract.  Repository-owned tests may import them directly; alpha.12 does not
# promise Python-level compatibility for these names.
__all__: tuple[str, ...] = ()
