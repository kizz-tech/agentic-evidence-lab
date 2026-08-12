from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from ael.sandbox import SandboxError
from ael.study_freeze import (
    DECISION_SCHEMA_VERSION,
    OBSERVATIONS_SCHEMA_VERSION,
    load_json_object,
    validate_freeze_bundle,
    validate_observation_identity,
)
from ael.validation import sha256_path

EXECUTION_CODE_FILES = (
    "src/ael/codex_runner.py",
    "src/ael/sandbox.py",
    "src/ael/study_freeze.py",
)


def execution_code_sha256() -> str:
    root = Path(__file__).resolve().parents[2]
    digest = hashlib.sha256()
    for relative in EXECUTION_CODE_FILES:
        payload = (root / relative).read_bytes()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(payload)
        digest.update(b"\n")
    return digest.hexdigest()


def _observations(data: dict[str, Any], phase: str) -> list[dict[str, Any]]:
    if data.get("schema_version") != OBSERVATIONS_SCHEMA_VERSION:
        raise SandboxError(f"observations must use {OBSERVATIONS_SCHEMA_VERSION}")
    if data.get("phase") != phase:
        raise SandboxError(f"observations phase must be {phase}")
    observations = data.get("observations")
    if not isinstance(observations, list) or not observations:
        raise SandboxError("observations must contain at least one result")
    return observations


def paired_counts(observations: list[dict[str, Any]]) -> dict[str, int]:
    pairs: dict[tuple[str, int], dict[str, dict[str, Any]]] = {}
    invalid = 0
    activation_failures = 0
    treatment_critical = 0
    for observation in observations:
        if observation.get("status") != "valid":
            invalid += 1
            continue
        task_id = observation.get("task_id")
        repeat_index = observation.get("repeat_index")
        condition_id = observation.get("condition_id")
        if not isinstance(task_id, str) or not isinstance(repeat_index, int):
            raise SandboxError("observation lacks task or repeat identity")
        if condition_id not in {"B0", "S1"}:
            raise SandboxError("PBT pilot decisions require B0 and S1")
        key = (task_id, repeat_index)
        if condition_id in pairs.setdefault(key, {}):
            raise SandboxError("observations contain a duplicate condition in a matched pair")
        pairs[key][condition_id] = observation
        if condition_id == "S1":
            if observation.get("skill_activated") is not True:
                activation_failures += 1
            if observation.get("critical_failure") is True:
                treatment_critical += 1
    favorable = 0
    unfavorable = 0
    tied = 0
    complete_pairs = 0
    baseline_failures = 0
    treatment_failures = 0
    for conditions in pairs.values():
        if set(conditions) != {"B0", "S1"}:
            continue
        complete_pairs += 1
        baseline = bool(conditions["B0"].get("hidden_acceptance"))
        treatment = bool(conditions["S1"].get("hidden_acceptance"))
        baseline_failures += int(not baseline)
        treatment_failures += int(not treatment)
        if not baseline and treatment:
            favorable += 1
        elif baseline and not treatment:
            unfavorable += 1
        else:
            tied += 1
    return {
        "valid_observations": len(observations) - invalid,
        "invalid_observations": invalid,
        "complete_pairs": complete_pairs,
        "favorable_pairs": favorable,
        "unfavorable_pairs": unfavorable,
        "tied_pairs": tied,
        "baseline_hidden_failures": baseline_failures,
        "treatment_hidden_failures": treatment_failures,
        "activation_failures": activation_failures,
        "treatment_critical_failures": treatment_critical,
    }


def decide_pbt_stage(bundle_path: Path, observations_path: Path, stage: str) -> dict[str, Any]:
    bundle_path = bundle_path.resolve()
    observations_path = observations_path.resolve()
    bundle = load_json_object(bundle_path)
    issues = validate_freeze_bundle(bundle)
    if issues:
        raise SandboxError(f"freeze bundle has {len(issues)} issue(s)")
    if stage not in {"continuation", "selection", "confirmation"}:
        raise SandboxError("decision stage must be continuation, selection, or confirmation")
    phase = "confirmation" if stage == "confirmation" else "screening"
    document = load_json_object(observations_path)
    observations = _observations(document, phase)
    validate_observation_identity(bundle_path, bundle, document, observations, phase, stage)
    counts = paired_counts(observations)
    rule = bundle[f"{stage}_rule"]
    integrity_ok = counts["invalid_observations"] == 0
    activation_ok = counts["activation_failures"] == 0
    critical_ok = counts["treatment_critical_failures"] == 0
    baseline_has_headroom = counts["baseline_hidden_failures"] > 0
    threshold_ok = (
        counts["favorable_pairs"] >= rule["minimum_favorable_pairs"]
        and counts["unfavorable_pairs"] <= rule["maximum_unfavorable_pairs"]
    )
    if not integrity_ok:
        outcome = "stopped_integrity_failure"
    elif not activation_ok:
        outcome = "stopped_activation_failure"
    elif not baseline_has_headroom:
        outcome = "stopped_baseline_ceiling"
    elif not critical_ok:
        outcome = "reject_all_critical_failure" if stage != "confirmation" else "not_confirmed"
    elif threshold_ok:
        outcome = {
            "continuation": "continue",
            "selection": "select_S1",
            "confirmation": "confirmed_S1",
        }[stage]
    else:
        outcome = "reject_all" if stage != "confirmation" else "not_confirmed"
    return {
        "schema_version": DECISION_SCHEMA_VERSION,
        "decision_id": f"{bundle['freeze_id']}:{stage}",
        "stage": stage,
        "study_id": bundle["study_id"],
        "study_revision": bundle["study_revision"],
        "freeze_ref": {
            "sha256": sha256_path(bundle_path),
            "freeze_id": bundle["freeze_id"],
        },
        "observations_sha256": sha256_path(observations_path),
        "counts": counts,
        "rule": rule,
        "outcome": outcome,
        "confirmation_unlocked": outcome == "select_S1" if stage == "selection" else False,
    }


def pbt_confirmation_unlocked(bundle_path: Path, selection_path: Path) -> bool:
    bundle_path = bundle_path.resolve()
    bundle = load_json_object(bundle_path)
    selection = load_json_object(selection_path.resolve())
    issues = validate_freeze_bundle(bundle)
    if issues:
        raise SandboxError(f"freeze bundle has {len(issues)} issue(s)")
    counts = selection.get("counts")
    rule = bundle["selection_rule"]
    expected_pairs = len(bundle["schedule"]["screening"]) // 2
    thresholds_met = (
        isinstance(counts, dict)
        and counts.get("invalid_observations") == 0
        and counts.get("activation_failures") == 0
        and counts.get("treatment_critical_failures") == 0
        and counts.get("baseline_hidden_failures", 0) > 0
        and counts.get("complete_pairs") == expected_pairs
        and counts.get("favorable_pairs", -1) >= rule["minimum_favorable_pairs"]
        and counts.get("unfavorable_pairs", expected_pairs + 1) <= rule["maximum_unfavorable_pairs"]
    )
    return (
        selection.get("schema_version") == DECISION_SCHEMA_VERSION
        and selection.get("decision_id") == f"{bundle['freeze_id']}:selection"
        and selection.get("stage") == "selection"
        and selection.get("study_id") == bundle["study_id"]
        and selection.get("study_revision") == bundle["study_revision"]
        and selection.get("outcome") == "select_S1"
        and selection.get("confirmation_unlocked") is True
        and selection.get("rule") == rule
        and selection.get("freeze_ref", {}).get("sha256") == sha256_path(bundle_path)
        and selection.get("freeze_ref", {}).get("freeze_id") == bundle["freeze_id"]
        and thresholds_met
    )
