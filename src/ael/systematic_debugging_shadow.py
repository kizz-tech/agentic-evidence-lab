"""Decision policy for the systematic-debugging real-shadow pilot."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ael.prospective_study import (
    EFFECT_DECISION_SCHEMA_VERSION,
    load_json_object,
    sha256_path,
    validate_freeze,
    validate_observations,
)
from ael.sandbox import SandboxError

EXECUTION_CODE_FILES = (
    "src/ael/codex_runner.py",
    "src/ael/sandbox.py",
    "src/ael/prospective_study.py",
)


def execution_code_sha256() -> str:
    root = Path(__file__).resolve().parents[2]
    digest = hashlib.sha256()
    for relative in EXECUTION_CODE_FILES:
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update((root / relative).read_bytes())
        digest.update(b"\n")
    return digest.hexdigest()


def paired_counts(
    observations: list[Mapping[str, Any]], strata: Mapping[str, str]
) -> tuple[dict[str, int], list[dict[str, Any]], dict[str, int]]:
    pairs: dict[str, dict[str, Mapping[str, Any]]] = {}
    invalid = 0
    activation_failures = 0
    treatment_critical = 0
    for observation in observations:
        if observation.get("status") != "valid":
            invalid += 1
            continue
        task_id = observation.get("task_id")
        condition_id = observation.get("condition_id")
        if not isinstance(task_id, str) or condition_id not in {"B0", "S1"}:
            raise SandboxError("observation has unsupported task or condition identity")
        if condition_id in pairs.setdefault(task_id, {}):
            raise SandboxError("duplicate condition within a matched task")
        pairs[task_id][condition_id] = observation
        if condition_id == "S1":
            activation_failures += int(observation.get("skill_activated") is not True)
            treatment_critical += int(observation.get("critical_failure") is True)
    favorable = 0
    unfavorable = 0
    tied = 0
    classifications: list[dict[str, Any]] = []
    favorable_by_stratum = {name: 0 for name in set(strata.values())}
    for task_id in sorted(pairs):
        conditions = pairs[task_id]
        if set(conditions) != {"B0", "S1"}:
            continue
        baseline = bool(conditions["B0"].get("accepted"))
        treatment = bool(conditions["S1"].get("accepted"))
        if not baseline and treatment:
            outcome = "favorable"
            favorable += 1
            favorable_by_stratum[strata[task_id]] += 1
        elif baseline and not treatment:
            outcome = "unfavorable"
            unfavorable += 1
        else:
            outcome = "tie"
            tied += 1
        classifications.append(
            {
                "task_id": task_id,
                "stratum": strata[task_id],
                "baseline_accepted": baseline,
                "treatment_accepted": treatment,
                "pair_outcome": outcome,
            }
        )
    counts = {
        "valid_observations": len(observations) - invalid,
        "invalid_observations": invalid,
        "complete_pairs": len(classifications),
        "favorable_pairs": favorable,
        "unfavorable_pairs": unfavorable,
        "tied_pairs": tied,
        "activation_failures": activation_failures,
        "treatment_critical_failures": treatment_critical,
    }
    return counts, classifications, favorable_by_stratum


def decide_effect(freeze_path: Path, observations_path: Path) -> dict[str, Any]:
    freeze_path = freeze_path.resolve()
    observations_path = observations_path.resolve()
    freeze = load_json_object(freeze_path)
    issues = validate_freeze(freeze)
    if issues:
        raise SandboxError(f"freeze has {len(issues)} issue(s): {issues[0]}")
    document = load_json_object(observations_path)
    observations = validate_observations(freeze_path, freeze, document)
    counts, classifications, favorable_by_stratum = paired_counts(
        observations, freeze["private_pack"]["strata"]
    )
    rule = freeze["decision_rule"]
    eligible_strata = sorted(
        stratum
        for stratum, count in favorable_by_stratum.items()
        if count >= rule["route_requires_favorable_tasks_per_stratum"]
    )
    if counts["invalid_observations"]:
        outcome = "invalid_manual_review"
        eligible_strata = []
    elif counts["activation_failures"]:
        outcome = "treatment_activation_failure"
        eligible_strata = []
    elif counts["treatment_critical_failures"]:
        outcome = "treatment_critical_failure"
        eligible_strata = []
    elif counts["unfavorable_pairs"] >= rule["reject_at_unfavorable_pairs"]:
        outcome = "treatment_harm_signal"
        eligible_strata = []
    elif eligible_strata and counts["unfavorable_pairs"] <= rule["maximum_unfavorable_for_route"]:
        outcome = "bounded_favorable_signal"
    else:
        outcome = "mixed_or_no_headroom"
        eligible_strata = []
    return {
        "schema_version": EFFECT_DECISION_SCHEMA_VERSION,
        "effect_decision_id": f"{freeze['freeze_id']}:effect",
        "study_id": freeze["study_id"],
        "study_revision": freeze["study_revision"],
        "freeze_ref": {"freeze_id": freeze["freeze_id"], "sha256": sha256_path(freeze_path)},
        "observations_sha256": sha256_path(observations_path),
        "counts": counts,
        "pair_classifications": classifications,
        "favorable_by_stratum": favorable_by_stratum,
        "eligible_strata": eligible_strata,
        "rule": rule,
        "effect_outcome": outcome,
        "claim_ceiling": "screening-derived bounded internal routing signal",
    }


def match_owner_policy(
    admission: Mapping[str, Any], effect_decision: Mapping[str, Any]
) -> tuple[Mapping[str, Any] | None, str]:
    outcome = effect_decision.get("effect_outcome")
    for rule in admission["owner_action_policy"]["rules"]:
        if outcome in rule["effect_outcomes"]:
            return rule, "applied_policy"
    return None, "blocked_integrity"
