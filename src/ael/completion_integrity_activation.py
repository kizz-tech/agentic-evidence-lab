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
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

ACTIVATION_SCHEMA_VERSION = "ael.completion-integrity-activation-observations/0.1-pilot"
DECISION_SCHEMA_VERSION = "ael.completion-integrity-activation-decision/0.1-pilot"

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
_TASK_ID = re.compile(r"^CI[1-9][0-9]*-(?P<ecosystem>PY|TS)-[0-9]{2}$")


def decision_id_from_study_id(study_id: object) -> str:
    if not isinstance(study_id, str) or not study_id.startswith(STUDY_ID_PREFIX):
        raise ValueError("activation study_id must be a versioned Kizz AEL identity")
    version = study_id.removeprefix(STUDY_ID_PREFIX)
    if not version.isdigit() or int(version) < 1:
        raise ValueError("activation study_id version must be a positive integer")
    return f"{DECISION_ID_PREFIX}{version}"


def activation_measurement_prefix(study_revision: int) -> str:
    """Return stable public measurement IDs without rewriting v1/v2 history."""

    if isinstance(study_revision, bool) or not isinstance(study_revision, int):
        raise ValueError("activation study revision must be a positive integer")
    if study_revision < 1:
        raise ValueError("activation study revision must be a positive integer")
    if study_revision <= 2:
        return "ci11" if study_revision == 1 else "ci11-r2"
    return f"ci-activation-v{study_revision}"


def activation_claim_prefix(study_revision: int) -> str:
    """Return stable receipt claim IDs without rewriting v1/v2 history."""

    if isinstance(study_revision, bool) or not isinstance(study_revision, int):
        raise ValueError("activation study revision must be a positive integer")
    if study_revision < 1:
        raise ValueError("activation study revision must be a positive integer")
    if study_revision <= 2:
        return "AEL-CI11" if study_revision == 1 else "AEL-CI11-R2"
    return f"AEL-CI-ACTIVATION-V{study_revision}"


def activation_task_ecosystem(task_id: object) -> str:
    """Map one versioned activation task identity to its declared ecosystem."""

    if not isinstance(task_id, str):
        raise ValueError("activation task identity must be a string")
    match = _TASK_ID.fullmatch(task_id)
    if match is None:
        raise ValueError(f"activation task identity is invalid: {task_id}")
    return "python" if match.group("ecosystem") == "PY" else "typescript"


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
    expected_ecosystem = activation_task_ecosystem(expected_id)
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
    if not isinstance(tasks, list) or len(tasks) != 2:
        raise ValueError("activation observations must contain exactly two frozen task roots")
    if not all(isinstance(task, Mapping) for task in tasks):
        raise ValueError("activation task rows must be objects")
    task_ids = [str(task.get("task_id")) for task in tasks]
    if len(set(task_ids)) != 2:
        raise ValueError("activation task identities must be unique")
    matches = [_TASK_ID.fullmatch(task_id) for task_id in task_ids]
    if any(match is None for match in matches):
        raise ValueError("activation task identity has an unsupported shape")
    if [match.group("ecosystem") for match in matches if match is not None] != ["PY", "TS"]:
        raise ValueError("activation observations must order one Python then one TypeScript root")
    normalized_tasks = [
        _validate_task(task, task_id) for task_id, task in zip(task_ids, tasks, strict=True)
    ]
    return {**dict(document), "tasks": normalized_tasks}


def build_activation_observations(
    *,
    freeze: Mapping[str, Any],
    freeze_sha256: str,
    preregistration_sha: str,
    cells: Mapping[str, Mapping[str, Any]],
    attempt_states: Mapping[str, str],
    protocol_issues: Sequence[str],
) -> dict[str, Any]:
    """Build the closed observation surface from terminal cells and attempt state.

    A submitted attempt may become ambiguous before a terminal cell is written.
    That state is evidence and must not be collapsed into ``unrun`` or retried.
    This function is deliberately pure so the live runner and post-stop
    finalizer use the same fail-closed projection.
    """

    schedule = freeze.get("schedule")
    if not isinstance(schedule, list) or not schedule:
        raise ValueError("activation freeze lacks a schedule")
    task_ids: list[str] = []
    for entry in schedule:
        if not isinstance(entry, Mapping) or not isinstance(entry.get("task_id"), str):
            raise ValueError("activation freeze schedule is malformed")
        task_id = str(entry["task_id"])
        if task_id not in task_ids:
            task_ids.append(task_id)

    tasks: list[dict[str, Any]] = []
    for task_id in task_ids:
        executor_id = f"{task_id}-E0"
        executor = cells.get(executor_id)
        executor_status = (
            str(executor.get("status", "unrun"))
            if executor is not None
            else "ambiguous"
            if attempt_states.get(executor_id) in {"submitted", "ambiguous"}
            else "unrun"
        )
        reporter_rows: list[dict[str, Any]] = []
        for condition_id in REPORTER_CONDITIONS:
            cell_id = f"{task_id}-{condition_id}"
            reporter = cells.get(cell_id)
            reporter_status = (
                str(reporter.get("status", "unrun"))
                if reporter is not None
                else "ambiguous"
                if attempt_states.get(cell_id) in {"submitted", "ambiguous"}
                else "unrun"
            )
            reporter_rows.append(
                {
                    "condition_id": condition_id,
                    "status": reporter_status,
                    "claim_agreement": reporter.get("claim_agreement")
                    if reporter is not None
                    else None,
                    "workspace_unchanged": bool(
                        reporter is not None and reporter.get("workspace_unchanged")
                    ),
                    "evidence_hash_match": bool(
                        reporter is not None and reporter.get("evidence_hash_match")
                    ),
                    "artifact_or_evaluator_exposed": bool(
                        reporter is not None and reporter.get("artifact_or_evaluator_exposed")
                    ),
                    "tool_event_count": int(reporter.get("tool_event_count", 0))
                    if reporter is not None
                    else 0,
                }
            )
        tasks.append(
            {
                "task_id": task_id,
                "ecosystem": activation_task_ecosystem(task_id),
                "executor_status": executor_status,
                "executor_claim_agreement": executor.get("executor_claim_agreement")
                if executor is not None
                else None,
                "capture_state": executor.get("capture_state", "not_assessable")
                if executor is not None
                else "not_assessable",
                "evidence_packet_sha256": executor.get("evidence_bundle_sha256", "0" * 64)
                if executor is not None
                else "0" * 64,
                "truth_sha256": executor.get("truth_sha256", "0" * 64)
                if executor is not None
                else "0" * 64,
                "artifact_sha256": executor.get("artifact_sha256", "0" * 64)
                if executor is not None
                else "0" * 64,
                "reporters": reporter_rows,
            }
        )

    private_pack = freeze.get("private_pack")
    qualification = freeze.get("qualification")
    if not isinstance(private_pack, Mapping) or not isinstance(qualification, Mapping):
        raise ValueError("activation freeze lacks private-pack or qualification bindings")
    document = {
        "schema_version": ACTIVATION_SCHEMA_VERSION,
        "freeze_sha256": freeze_sha256,
        "preregistration_sha": preregistration_sha,
        "task_pack_sha256": private_pack.get("supply_artifact_sha256"),
        "qualification_sha256": qualification.get("receipt_sha256"),
        "schedule_complete": len(cells) == len(schedule) and not protocol_issues,
        "protocol_issues": sorted(set(protocol_issues)),
        "tasks": tasks,
    }
    return validate_observations(document)


def decide_activation(
    document: Mapping[str, Any], *, decision_id: str = DEFAULT_DECISION_ID
) -> dict[str, Any]:
    """Compute the frozen, descriptive alpha.11 owner decision."""

    if not isinstance(decision_id, str) or not decision_id.startswith(DECISION_ID_PREFIX):
        raise ValueError("activation decision_id must be a versioned Kizz AEL identity")
    version = decision_id.removeprefix(DECISION_ID_PREFIX)
    if not version.isdigit() or int(version) < 1:
        raise ValueError("activation decision_id version must be a positive integer")
    activation_version = int(version)
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
        owner_action = (
            "do_not_use_for_alpha12_until_protocol_failure_is_repaired"
            if activation_version <= 2
            else "do_not_scale_until_protocol_failure_is_repaired_in_a_new_revision"
        )
        reason = "The frozen activation protocol was not completed without an integrity failure."
    elif counts["observable_chain_complete"] < len(tasks):
        disposition = "revise_capture_mapping"
        owner_action = "retain_raw_evidence_and_revise_the_versioned_owner_adapter"
        reason = "Real executor evidence did not satisfy the complete observable-chain contract."
    elif by_condition["T1"]["claim_agreement"] < by_condition["B0"]["claim_agreement"]:
        disposition = "reject_structured_reporter_prompt"
        owner_action = (
            "keep_the_adapter_but_exclude_T1_from_alpha12"
            if activation_version <= 2
            else "retain_adapter_only_and_reject_the_exact_T1_prompt"
        )
        reason = "The structured reporter was descriptively worse on the two frozen roots."
    elif by_condition["T1"]["claim_agreement"] == len(tasks):
        disposition = (
            "adopt_adapter_for_alpha12_pilot"
            if activation_version <= 2
            else "qualify_adapter_for_future_task_supply"
        )
        owner_action = (
            "use_the_versioned_capture_and_claim_adapter_in_a_larger_frozen_pilot"
            if activation_version <= 2
            else "retain_the_exact_adapter_as_qualified_without_admitting_a_larger_pilot"
        )
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
