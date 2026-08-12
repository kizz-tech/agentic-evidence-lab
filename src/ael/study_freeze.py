from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ael.sandbox import SandboxError, tree_sha256
from ael.validation import sha256_path

FREEZE_SCHEMA_VERSION = "ael.study-freeze/0.1"
OBSERVATIONS_SCHEMA_VERSION = "ael.study-observations/0.1"
DECISION_SCHEMA_VERSION = "ael.study-decision/0.1"
PRIVATE_CANARY_PREFIX = "AEL-HIDDEN-" + "CANARY:"
_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")


@dataclass(frozen=True)
class FreezeIssue:
    location: str
    message: str

    def __str__(self) -> str:
        return f"{self.location}: {self.message}"


def load_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SandboxError(f"JSON object is unreadable: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SandboxError(f"JSON document must be an object: {path}")
    return value


def _required_string(
    data: dict[str, Any], key: str, issues: list[FreezeIssue], prefix: str = ""
) -> str | None:
    value = data.get(key)
    location = f"{prefix}.{key}" if prefix else key
    if not isinstance(value, str) or not value.strip():
        issues.append(FreezeIssue(location, "must be a non-empty string"))
        return None
    return value


def _required_positive_int(
    data: dict[str, Any], key: str, issues: list[FreezeIssue], prefix: str = ""
) -> int | None:
    value = data.get(key)
    location = f"{prefix}.{key}" if prefix else key
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        issues.append(FreezeIssue(location, "must be a positive integer"))
        return None
    return value


def _validate_private_pack(
    phase: str, pack: object, issues: list[FreezeIssue]
) -> tuple[set[str], str | None]:
    prefix = f"private_packs.{phase}"
    if not isinstance(pack, dict):
        issues.append(FreezeIssue(prefix, "must be an object"))
        return set(), None
    uri = _required_string(pack, "uri", issues, prefix)
    digest = _required_string(pack, "sha256", issues, prefix)
    if uri and not uri.startswith("urn:kizz:ael:private-pack:"):
        issues.append(FreezeIssue(f"{prefix}.uri", "must use a private-pack URN"))
    if digest and not _SHA256.fullmatch(digest):
        issues.append(FreezeIssue(f"{prefix}.sha256", "must be 64 lowercase hex"))
    task_ids = pack.get("task_ids")
    if not isinstance(task_ids, list) or not task_ids:
        issues.append(FreezeIssue(f"{prefix}.task_ids", "must contain at least one task ID"))
        return set(), digest
    result: set[str] = set()
    for index, task_id in enumerate(task_ids):
        if not isinstance(task_id, str) or not _ID.fullmatch(task_id):
            issues.append(
                FreezeIssue(f"{prefix}.task_ids.{index}", "must be a normalized opaque ID")
            )
        elif task_id in result:
            issues.append(FreezeIssue(f"{prefix}.task_ids.{index}", "must be unique"))
        else:
            result.add(task_id)
    return result, digest


def _schedule_keys(
    entries: object, prefix: str, issues: list[FreezeIssue]
) -> list[tuple[str, str, int]]:
    if not isinstance(entries, list) or not entries:
        issues.append(FreezeIssue(prefix, "must contain schedule entries"))
        return []
    keys: list[tuple[str, str, int]] = []
    sequences: set[int] = set()
    for index, entry in enumerate(entries):
        location = f"{prefix}.{index}"
        if not isinstance(entry, dict):
            issues.append(FreezeIssue(location, "must be an object"))
            continue
        sequence = entry.get("sequence")
        task_id = entry.get("task_id")
        condition_id = entry.get("condition_id")
        repeat_index = entry.get("repeat_index")
        if not isinstance(sequence, int) or sequence < 1:
            issues.append(FreezeIssue(f"{location}.sequence", "must be a positive integer"))
        elif sequence in sequences:
            issues.append(FreezeIssue(f"{location}.sequence", "must be unique"))
        else:
            sequences.add(sequence)
        if not isinstance(task_id, str):
            issues.append(FreezeIssue(f"{location}.task_id", "must be a string"))
            continue
        if not isinstance(condition_id, str):
            issues.append(FreezeIssue(f"{location}.condition_id", "must be a string"))
            continue
        if not isinstance(repeat_index, int) or repeat_index < 1:
            issues.append(FreezeIssue(f"{location}.repeat_index", "must be a positive integer"))
            continue
        keys.append((task_id, condition_id, repeat_index))
    if sequences and sequences != set(range(1, len(entries) + 1)):
        issues.append(FreezeIssue(prefix, "sequence values must be contiguous from one"))
    if len(keys) != len(set(keys)):
        issues.append(FreezeIssue(prefix, "task, condition, and repeat tuples must be unique"))
    return keys


def validate_freeze_bundle(data: dict[str, Any]) -> list[FreezeIssue]:
    issues: list[FreezeIssue] = []
    if data.get("schema_version") != FREEZE_SCHEMA_VERSION:
        issues.append(FreezeIssue("schema_version", f"must equal {FREEZE_SCHEMA_VERSION}"))
    for key in (
        "freeze_id",
        "study_id",
        "frozen_at",
        "analysis_code_sha256",
        "decision_code_sha256",
        "execution_code_sha256",
        "runner_code_sha256",
        "prompt_sha256",
    ):
        value = _required_string(data, key, issues)
        if key.endswith("sha256") and value and not _SHA256.fullmatch(value):
            issues.append(FreezeIssue(key, "must be 64 lowercase hex"))
    _required_positive_int(data, "study_revision", issues)
    if data.get("scored_calls_executed") != 0:
        issues.append(FreezeIssue("scored_calls_executed", "must equal zero at freeze"))

    conditions = data.get("conditions")
    condition_ids: set[str] = set()
    roles: set[str] = set()
    if not isinstance(conditions, list) or len(conditions) < 2:
        issues.append(FreezeIssue("conditions", "must contain baseline and treatment"))
    else:
        for index, condition in enumerate(conditions):
            location = f"conditions.{index}"
            if not isinstance(condition, dict):
                issues.append(FreezeIssue(location, "must be an object"))
                continue
            condition_id = _required_string(condition, "condition_id", issues, location)
            role = _required_string(condition, "role", issues, location)
            if condition_id in condition_ids:
                issues.append(FreezeIssue(f"{location}.condition_id", "must be unique"))
            elif condition_id:
                condition_ids.add(condition_id)
            if role:
                roles.add(role)
            digest = condition.get("intervention_sha256")
            if role == "treatment" and not isinstance(digest, str):
                issues.append(
                    FreezeIssue(f"{location}.intervention_sha256", "is required for treatment")
                )
            elif digest is not None and (
                not isinstance(digest, str) or not _SHA256.fullmatch(digest)
            ):
                issues.append(
                    FreezeIssue(f"{location}.intervention_sha256", "must be 64 lowercase hex")
                )
        if not {"baseline", "treatment"}.issubset(roles):
            issues.append(FreezeIssue("conditions", "must include baseline and treatment roles"))

    packs = data.get("private_packs")
    if not isinstance(packs, dict):
        issues.append(FreezeIssue("private_packs", "must be an object"))
        screening_tasks: set[str] = set()
        confirmation_tasks: set[str] = set()
    else:
        screening_tasks, _ = _validate_private_pack("screening", packs.get("screening"), issues)
        confirmation_tasks, _ = _validate_private_pack(
            "confirmation", packs.get("confirmation"), issues
        )
        if screening_tasks & confirmation_tasks:
            issues.append(
                FreezeIssue("private_packs", "screening and confirmation IDs must differ")
            )

    for key in ("primary_endpoint", "critical_failure_gates", "invalid_run_policy", "retry_policy"):
        value = data.get(key)
        if key == "critical_failure_gates":
            if (
                not isinstance(value, list)
                or not value
                or not all(isinstance(item, str) and item for item in value)
            ):
                issues.append(FreezeIssue(key, "must contain non-empty string gates"))
        elif not isinstance(value, str) or not value.strip():
            issues.append(FreezeIssue(key, "must be a non-empty string"))

    runtime = data.get("runtime")
    if not isinstance(runtime, dict):
        issues.append(FreezeIssue("runtime", "must be an object"))
    else:
        for key in (
            "harness",
            "harness_version",
            "model",
            "reasoning_effort",
            "runner_image_id",
            "proxy_image_id",
        ):
            _required_string(runtime, key, issues, "runtime")

    budget = data.get("budget")
    if not isinstance(budget, dict):
        issues.append(FreezeIssue("budget", "must be an object"))
        initial_repeats = None
        max_repeats = None
        max_runs = None
    else:
        initial_repeats = _required_positive_int(budget, "initial_repeats", issues, "budget")
        max_repeats = _required_positive_int(budget, "max_repeats", issues, "budget")
        max_runs = _required_positive_int(budget, "max_scored_runs", issues, "budget")
        _required_positive_int(budget, "per_run_timeout_seconds", issues, "budget")
        _required_positive_int(budget, "max_generated_tokens", issues, "budget")
        if initial_repeats and max_repeats and initial_repeats > max_repeats:
            issues.append(FreezeIssue("budget", "initial repeats cannot exceed maximum repeats"))

    schedule = data.get("schedule")
    if not isinstance(schedule, dict):
        issues.append(FreezeIssue("schedule", "must be an object"))
        screening_keys: list[tuple[str, str, int]] = []
        confirmation_keys: list[tuple[str, str, int]] = []
    else:
        _required_string(schedule, "algorithm", issues, "schedule")
        _required_string(schedule, "seed", issues, "schedule")
        screening_keys = _schedule_keys(schedule.get("screening"), "schedule.screening", issues)
        confirmation_keys = _schedule_keys(
            schedule.get("confirmation"), "schedule.confirmation", issues
        )
    for phase, keys, tasks in (
        ("screening", screening_keys, screening_tasks),
        ("confirmation", confirmation_keys, confirmation_tasks),
    ):
        for task_id, condition_id, repeat_index in keys:
            if task_id not in tasks:
                issues.append(FreezeIssue(f"schedule.{phase}", f"unknown task ID {task_id}"))
            if condition_id not in condition_ids:
                issues.append(
                    FreezeIssue(f"schedule.{phase}", f"unknown condition ID {condition_id}")
                )
            if max_repeats and repeat_index > max_repeats:
                issues.append(FreezeIssue(f"schedule.{phase}", "repeat exceeds budget.max_repeats"))
        expected = {
            (task_id, condition_id, repeat_index)
            for task_id in tasks
            for condition_id in condition_ids
            for repeat_index in range(1, (max_repeats or 0) + 1)
        }
        if max_repeats and set(keys) != expected:
            issues.append(
                FreezeIssue(f"schedule.{phase}", "must cover every frozen task-condition-repeat")
            )
    if max_runs and len(screening_keys) + len(confirmation_keys) > max_runs:
        issues.append(FreezeIssue("budget.max_scored_runs", "is lower than the frozen schedule"))

    for rule_name in ("continuation_rule", "selection_rule", "confirmation_rule"):
        rule = data.get(rule_name)
        if not isinstance(rule, dict):
            issues.append(FreezeIssue(rule_name, "must be an object"))
            continue
        for key in ("minimum_favorable_pairs", "maximum_unfavorable_pairs"):
            value = rule.get(key)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                issues.append(FreezeIssue(f"{rule_name}.{key}", "must be a non-negative integer"))
        if rule.get("require_zero_treatment_critical_failures") is not True:
            issues.append(
                FreezeIssue(f"{rule_name}.require_zero_treatment_critical_failures", "must be true")
            )
        if rule_name == "continuation_rule":
            available_pairs = len(screening_tasks) * (initial_repeats or 0)
        elif rule_name == "selection_rule":
            available_pairs = len(screening_tasks) * (max_repeats or 0)
        else:
            available_pairs = len(confirmation_tasks) * (max_repeats or 0)
        for key in ("minimum_favorable_pairs", "maximum_unfavorable_pairs"):
            value = rule.get(key)
            if isinstance(value, int) and not isinstance(value, bool) and value > available_pairs:
                issues.append(
                    FreezeIssue(f"{rule_name}.{key}", "cannot exceed available matched pairs")
                )

    roles = data.get("roles")
    if not isinstance(roles, dict) or not all(
        isinstance(roles.get(key), str) and roles[key]
        for key in ("task_author", "operator", "evaluator", "decision_owner")
    ):
        issues.append(FreezeIssue("roles", "must name all required research roles"))
    return issues


def verify_private_pack(bundle: dict[str, Any], phase: str, root: Path) -> None:
    issues = validate_freeze_bundle(bundle)
    if issues:
        raise SandboxError(f"freeze bundle has {len(issues)} issue(s)")
    root = root.resolve()
    canary = root / ".ael-private-canary"
    if not canary.is_file() or not canary.read_text(encoding="utf-8").startswith(
        PRIVATE_CANARY_PREFIX
    ):
        raise SandboxError(f"{phase} pack lacks the private canary")
    expected = bundle["private_packs"][phase]["sha256"]
    actual = tree_sha256(root)
    if actual != expected:
        raise SandboxError(f"{phase} pack hash mismatch: expected {expected}, observed {actual}")


def _expected_observation_keys(
    bundle: dict[str, Any], phase: str, stage: str
) -> dict[tuple[str, str, int], int]:
    schedule = bundle["schedule"][phase]
    if stage == "continuation":
        repeat_limit = bundle["budget"]["initial_repeats"]
        schedule = [entry for entry in schedule if entry["repeat_index"] <= repeat_limit]
    return {
        (entry["task_id"], entry["condition_id"], entry["repeat_index"]): entry["sequence"]
        for entry in schedule
    }


def validate_observation_identity(
    bundle_path: Path,
    bundle: dict[str, Any],
    document: dict[str, Any],
    observations: list[dict[str, Any]],
    phase: str,
    stage: str,
) -> None:
    if document.get("freeze_sha256") != sha256_path(bundle_path):
        raise SandboxError("observations are not bound to the supplied freeze bundle")
    expected = _expected_observation_keys(bundle, phase, stage)
    observed: dict[tuple[str, str, int], int] = {}
    for observation in observations:
        task_id = observation.get("task_id")
        condition_id = observation.get("condition_id")
        repeat_index = observation.get("repeat_index")
        sequence = observation.get("schedule_sequence")
        if not isinstance(task_id, str) or not isinstance(condition_id, str):
            raise SandboxError("observation lacks task or condition identity")
        if not isinstance(repeat_index, int) or not isinstance(sequence, int):
            raise SandboxError("observation lacks repeat or schedule identity")
        key = (task_id, condition_id, repeat_index)
        if key in observed:
            raise SandboxError("observations contain a duplicate scheduled cell")
        observed[key] = sequence
    if set(observed) != set(expected):
        raise SandboxError(f"{stage} observations do not cover the exact frozen schedule")
    if observed != expected:
        raise SandboxError("observation sequence does not match the frozen schedule")


def deterministic_schedule(
    task_ids: list[str], condition_ids: list[str], repeats: int, seed: str
) -> list[dict[str, object]]:
    entries = [
        {"task_id": task_id, "condition_id": condition_id, "repeat_index": repeat_index}
        for repeat_index in range(1, repeats + 1)
        for task_id in task_ids
        for condition_id in condition_ids
    ]
    entries.sort(
        key=lambda entry: hashlib.sha256(
            f"{seed}:{entry['task_id']}:{entry['condition_id']}:{entry['repeat_index']}".encode()
        ).digest()
    )
    return [{"sequence": index, **entry} for index, entry in enumerate(entries, start=1)]
