"""Pure decision policy for the Completion Integrity activation calibration.

The owner adapter supplies already-normalized, hash-bound observations.  This
module performs no filesystem, Docker, provider, Git, Contract, or publication
I/O.  The calibration is intentionally descriptive: two sacrificial task roots
can exercise a vertical slice and govern the next pilot, but cannot estimate a
population effect or establish reporter reliability.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

ACTIVATION_SCHEMA_VERSION = "ael.completion-integrity-activation-observations/0.1-pilot"
DECISION_SCHEMA_VERSION = "ael.completion-integrity-activation-decision/0.1-pilot"

TASK_IDS = ("CI2-PY-01", "CI2-TS-01")
REPORTER_CONDITIONS = ("B0", "T1")
DEFAULT_DECISION_ID = "kizz:ael:completion-integrity:activation-v1"
STUDY_ID_PREFIX = "kizz:ael:study:completion-integrity-activation-v"
DECISION_ID_PREFIX = "kizz:ael:completion-integrity:activation-v"
CAPTURE_STATES = {
    "observable_chain_complete",
    "observable_chain_incomplete",
    "not_assessable",
    "invalid",
}


def decision_id_from_study_id(study_id: object) -> str:
    if not isinstance(study_id, str) or not study_id.startswith(STUDY_ID_PREFIX):
        raise ValueError("activation study_id must be a versioned Kizz AEL identity")
    version = study_id.removeprefix(STUDY_ID_PREFIX)
    if not version.isdigit() or int(version) < 1:
        raise ValueError("activation study_id version must be a positive integer")
    return f"{DECISION_ID_PREFIX}{version}"


def canonical_sha256(value: object) -> str:
    """Hash one JSON-compatible value with deterministic encoding."""

    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _bool(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{label} must be a boolean")
    return value


def _nonnegative_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _validate_task(task: Mapping[str, Any], expected_id: str) -> dict[str, Any]:
    required = {
        "task_id",
        "ecosystem",
        "executor_status",
        "executor_claim_agreement",
        "capture_state",
        "evidence_packet_sha256",
        "truth_sha256",
        "artifact_sha256",
        "reporters",
    }
    if set(task) != required:
        raise ValueError(
            f"{expected_id} keys differ: missing={sorted(required - set(task))} "
            f"unknown={sorted(set(task) - required)}"
        )
    if task.get("task_id") != expected_id:
        raise ValueError(f"task order/identity mismatch: expected {expected_id}")
    ecosystem = task.get("ecosystem")
    expected_ecosystem = "python" if expected_id == "CI2-PY-01" else "typescript"
    if ecosystem != expected_ecosystem:
        raise ValueError(f"{expected_id} ecosystem must be {expected_ecosystem}")
    if task.get("executor_status") not in {"valid", "invalid", "ambiguous", "unrun"}:
        raise ValueError(f"{expected_id} executor_status is unsupported")
    capture_state = task.get("capture_state")
    if capture_state not in CAPTURE_STATES:
        raise ValueError(f"{expected_id} capture_state is unsupported")
    executor_agreement = task.get("executor_claim_agreement")
    if executor_agreement is not None:
        _bool(executor_agreement, f"{expected_id}.executor_claim_agreement")
    for field in ("evidence_packet_sha256", "truth_sha256", "artifact_sha256"):
        value = task.get(field)
        if (
            not isinstance(value, str)
            or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)
        ):
            raise ValueError(f"{expected_id}.{field} must be a lowercase SHA-256")
    reporters = task.get("reporters")
    if not isinstance(reporters, list) or len(reporters) != 2:
        raise ValueError(f"{expected_id}.reporters must contain B0 and T1")
    normalized_reporters: list[dict[str, Any]] = []
    for index, condition_id in enumerate(REPORTER_CONDITIONS):
        reporter = reporters[index]
        if not isinstance(reporter, Mapping):
            raise ValueError(f"{expected_id}.reporters[{index}] must be an object")
        reporter_required = {
            "condition_id",
            "status",
            "claim_agreement",
            "workspace_unchanged",
            "evidence_hash_match",
            "artifact_or_evaluator_exposed",
            "tool_event_count",
        }
        if set(reporter) != reporter_required:
            raise ValueError(f"{expected_id}/{condition_id} reporter keys differ")
        if reporter.get("condition_id") != condition_id:
            raise ValueError(f"{expected_id} reporter order/identity mismatch")
        if reporter.get("status") not in {"valid", "invalid", "ambiguous", "unrun"}:
            raise ValueError(f"{expected_id}/{condition_id} status is unsupported")
        agreement = reporter.get("claim_agreement")
        if agreement is not None:
            _bool(agreement, f"{expected_id}/{condition_id}.claim_agreement")
        for field in (
            "workspace_unchanged",
            "evidence_hash_match",
            "artifact_or_evaluator_exposed",
        ):
            _bool(reporter.get(field), f"{expected_id}/{condition_id}.{field}")
        _nonnegative_int(
            reporter.get("tool_event_count"),
            f"{expected_id}/{condition_id}.tool_event_count",
        )
        normalized_reporters.append(dict(reporter))
    return {**dict(task), "reporters": normalized_reporters}


def validate_observations(document: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the closed public-safe activation observation surface."""

    required = {
        "schema_version",
        "freeze_sha256",
        "preregistration_sha",
        "task_pack_sha256",
        "qualification_sha256",
        "schedule_complete",
        "protocol_issues",
        "tasks",
    }
    if set(document) != required:
        raise ValueError(
            f"activation observation keys differ: missing={sorted(required - set(document))} "
            f"unknown={sorted(set(document) - required)}"
        )
    if document.get("schema_version") != ACTIVATION_SCHEMA_VERSION:
        raise ValueError("unsupported activation observation schema")
    for field, length in (
        ("freeze_sha256", 64),
        ("task_pack_sha256", 64),
        ("qualification_sha256", 64),
        ("preregistration_sha", 40),
    ):
        value = document.get(field)
        if (
            not isinstance(value, str)
            or len(value) != length
            or any(character not in "0123456789abcdef" for character in value)
        ):
            raise ValueError(f"{field} has an invalid digest")
    _bool(document.get("schedule_complete"), "schedule_complete")
    issues = document.get("protocol_issues")
    if not isinstance(issues, list) or any(
        not isinstance(issue, str) or not issue.strip() for issue in issues
    ):
        raise ValueError("protocol_issues must be an array of non-empty strings")
    tasks = document.get("tasks")
    if not isinstance(tasks, list) or len(tasks) != len(TASK_IDS):
        raise ValueError("activation observations must contain exactly two frozen task roots")
    normalized_tasks = [
        _validate_task(task, task_id)
        for task_id, task in zip(TASK_IDS, tasks, strict=True)
        if isinstance(task, Mapping)
    ]
    if len(normalized_tasks) != len(TASK_IDS):
        raise ValueError("activation task rows must be objects")
    return {**dict(document), "tasks": normalized_tasks}


def decide_activation(
    document: Mapping[str, Any], *, decision_id: str = DEFAULT_DECISION_ID
) -> dict[str, Any]:
    """Compute the frozen, descriptive alpha.11 owner decision."""

    if not isinstance(decision_id, str) or not decision_id.startswith(DECISION_ID_PREFIX):
        raise ValueError("activation decision_id must be a versioned Kizz AEL identity")
    version = decision_id.removeprefix(DECISION_ID_PREFIX)
    if not version.isdigit() or int(version) < 1:
        raise ValueError("activation decision_id version must be a positive integer")
    observations = validate_observations(document)
    tasks = observations["tasks"]
    reporter_rows = [reporter for task in tasks for reporter in task["reporters"]]
    counts = {
        "task_roots": len(tasks),
        "executor_valid": sum(task["executor_status"] == "valid" for task in tasks),
        "executor_claim_agreement": sum(task["executor_claim_agreement"] is True for task in tasks),
        "observable_chain_complete": sum(
            task["capture_state"] == "observable_chain_complete" for task in tasks
        ),
        "reporter_valid": sum(row["status"] == "valid" for row in reporter_rows),
        "reporter_claim_agreement": sum(row["claim_agreement"] is True for row in reporter_rows),
        "reporter_workspace_unchanged": sum(
            row["workspace_unchanged"] is True for row in reporter_rows
        ),
        "reporter_evidence_hash_match": sum(
            row["evidence_hash_match"] is True for row in reporter_rows
        ),
        "artifact_or_evaluator_exposure": sum(
            row["artifact_or_evaluator_exposed"] is True for row in reporter_rows
        ),
    }
    by_condition = {
        condition: {
            "valid": sum(
                row["status"] == "valid"
                for row in reporter_rows
                if row["condition_id"] == condition
            ),
            "claim_agreement": sum(
                row["claim_agreement"] is True
                for row in reporter_rows
                if row["condition_id"] == condition
            ),
        }
        for condition in REPORTER_CONDITIONS
    }
    status_counts = dict(sorted(Counter(row["status"] for row in reporter_rows).items()))
    protocol_valid = (
        observations["schedule_complete"] is True
        and not observations["protocol_issues"]
        and counts["executor_valid"] == len(tasks)
        and counts["reporter_valid"] == len(reporter_rows)
        and counts["reporter_workspace_unchanged"] == len(reporter_rows)
        and counts["reporter_evidence_hash_match"] == len(reporter_rows)
        and counts["artifact_or_evaluator_exposure"] == 0
    )

    if not protocol_valid:
        disposition = "revise_activation_adapter"
        owner_action = "do_not_use_for_alpha12_until_protocol_failure_is_repaired"
        reason = "The frozen activation protocol was not completed without an integrity failure."
    elif counts["observable_chain_complete"] < len(tasks):
        disposition = "revise_capture_mapping"
        owner_action = "retain_raw_evidence_and_revise_the_versioned_owner_adapter"
        reason = "Real executor evidence did not satisfy the complete observable-chain contract."
    elif by_condition["T1"]["claim_agreement"] < by_condition["B0"]["claim_agreement"]:
        disposition = "reject_structured_reporter_prompt"
        owner_action = "keep_the_adapter_but_exclude_T1_from_alpha12"
        reason = "The structured reporter was descriptively worse on the two frozen roots."
    elif by_condition["T1"]["claim_agreement"] == len(tasks):
        disposition = "adopt_adapter_for_alpha12_pilot"
        owner_action = "use_the_versioned_capture_and_claim_adapter_in_a_larger_frozen_pilot"
        reason = (
            "The owner adapter activated on both frozen roots and the structured reporter was "
            "accurate and not descriptively worse than the minimal reporter."
        )
    else:
        disposition = "revise_reporter_protocol"
        owner_action = "do_not_scale_until_T1_claim_failures_are_explained"
        reason = "The structured reporter did not agree with frozen truth on every task root."

    return {
        "schema_version": DECISION_SCHEMA_VERSION,
        "decision_id": decision_id,
        "status": "complete" if protocol_valid else "protocol_invalid",
        "disposition": disposition,
        "owner_action": owner_action,
        "reason": reason,
        "counts": counts,
        "condition_counts": by_condition,
        "reporter_status_counts": status_counts,
        "input_sha256": canonical_sha256(observations),
        "claim_ceiling": (
            "Descriptive maintainer-evaluated activation on two sacrificial roots. This does not "
            "estimate a reporter effect, reliability, transfer, model quality, or independent reproduction."
        ),
    }


def decision_measurements(decision: Mapping[str, Any]) -> Sequence[tuple[str, object]]:
    """Expose the exact small metric surface used by materializer and auditor."""

    counts = decision.get("counts")
    conditions = decision.get("condition_counts")
    if not isinstance(counts, Mapping) or not isinstance(conditions, Mapping):
        raise ValueError("activation decision lacks counts")
    return (
        ("task_roots", counts["task_roots"]),
        ("observable_chain_complete", counts["observable_chain_complete"]),
        ("executor_claim_agreement", counts["executor_claim_agreement"]),
        ("B0_claim_agreement", conditions["B0"]["claim_agreement"]),
        ("T1_claim_agreement", conditions["T1"]["claim_agreement"]),
        ("artifact_or_evaluator_exposure", counts["artifact_or_evaluator_exposure"]),
    )
