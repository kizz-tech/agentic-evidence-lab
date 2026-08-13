"""Experimental prospective admission and freeze contract.

This module is deliberately adjacent to, not a replacement for, the byte-locked
``ael.study-freeze/0.1`` implementation.  The pilot must complete one full
lifecycle before any of these shapes are considered stable Contract objects.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ael.sandbox import SandboxError

ADMISSION_SCHEMA_VERSION = "ael.study-admission/0.1-pilot"
FREEZE_SCHEMA_VERSION = "ael.study-freeze/0.2-dev"
EFFECT_DECISION_SCHEMA_VERSION = "ael.study-effect-decision/0.1-pilot"
ADOPTION_DECISION_SCHEMA_VERSION = "ael.adoption-decision/0.1-pilot"
ACTION_RECORD_SCHEMA_VERSION = "ael.action-record/0.1-pilot"
FOLLOW_UP_SCHEMA_VERSION = "ael.outcome-follow-up/0.1-pilot"
OBSERVATIONS_SCHEMA_VERSION = "ael.study-observations/0.2-dev"
PRIVATE_CANARY_PREFIX = "AEL-HIDDEN-" + "CANARY:"

_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_DISPOSITIONS = {
    "install_globally",
    "route_selectively",
    "keep_optional",
    "reject_exact_version",
}


@dataclass(frozen=True)
class StudyIssue:
    location: str
    message: str

    def __str__(self) -> str:
        return f"{self.location}: {self.message}"


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate object member: {key}")
        result[key] = value
    return result


def _finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"non-finite JSON number: {value}")
    return parsed


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number: {value}")


def load_json_object(path: Path) -> dict[str, Any]:
    path = path.absolute()
    if path.is_symlink() or not path.is_file():
        raise SandboxError(f"JSON object is missing or unsafe: {path}")
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_strict_object,
            parse_float=_finite_float,
            parse_constant=_reject_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise SandboxError(f"JSON object is unreadable: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SandboxError(f"JSON document must be an object: {path}")
    return value


def canonical_sha256(value: Mapping[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _keys(
    value: object,
    required: set[str],
    optional: set[str],
    location: str,
    issues: list[StudyIssue],
) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        issues.append(StudyIssue(location, "must be an object"))
        return None
    missing = required - set(value)
    unknown = set(value) - required - optional
    if missing:
        issues.append(StudyIssue(location, f"missing keys: {', '.join(sorted(missing))}"))
    if unknown:
        issues.append(StudyIssue(location, f"unknown keys: {', '.join(sorted(unknown))}"))
    return value


def _string(value: object, location: str, issues: list[StudyIssue]) -> str | None:
    if not isinstance(value, str) or not value.strip():
        issues.append(StudyIssue(location, "must be a non-empty string"))
        return None
    return value


def _sha(value: object, location: str, issues: list[StudyIssue]) -> str | None:
    parsed = _string(value, location, issues)
    if parsed is not None and _SHA256.fullmatch(parsed) is None:
        issues.append(StudyIssue(location, "must be 64 lowercase hexadecimal characters"))
    return parsed


def _positive_int(value: object, location: str, issues: list[StudyIssue]) -> int | None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        issues.append(StudyIssue(location, "must be a positive integer"))
        return None
    return value


def _timestamp(value: object, location: str, issues: list[StudyIssue]) -> str | None:
    parsed = _string(value, location, issues)
    if parsed is not None and _TIMESTAMP.fullmatch(parsed) is None:
        issues.append(StudyIssue(location, "must use UTC YYYY-MM-DDTHH:MM:SSZ"))
    return parsed


def _ref(
    value: object,
    location: str,
    issues: list[StudyIssue],
    *,
    identity_key: str,
) -> dict[str, Any] | None:
    ref = _keys(value, {identity_key, "uri", "sha256"}, set(), location, issues)
    if ref is None:
        return None
    _string(ref.get(identity_key), f"{location}.{identity_key}", issues)
    _string(ref.get("uri"), f"{location}.uri", issues)
    _sha(ref.get("sha256"), f"{location}.sha256", issues)
    return ref


def validate_admission(data: Mapping[str, Any]) -> list[StudyIssue]:
    issues: list[StudyIssue] = []
    root = _keys(
        data,
        {
            "schema_version",
            "admission_id",
            "case_id",
            "case_revision",
            "status",
            "admitted_at",
            "expires_at",
            "decision_question",
            "study_manifest_ref",
            "candidate",
            "execution_authority",
            "evidence_boundary",
            "owner_action_policy",
            "roles",
            "role_overlaps",
            "stop_rules",
            "follow_up_plan",
        },
        set(),
        "admission",
        issues,
    )
    if root is None:
        return issues
    if root.get("schema_version") != ADMISSION_SCHEMA_VERSION:
        issues.append(StudyIssue("schema_version", f"must equal {ADMISSION_SCHEMA_VERSION}"))
    for key in ("admission_id", "case_id", "decision_question"):
        _string(root.get(key), key, issues)
    _positive_int(root.get("case_revision"), "case_revision", issues)
    if root.get("status") != "admitted":
        issues.append(StudyIssue("status", "must equal admitted before scored work"))
    _timestamp(root.get("admitted_at"), "admitted_at", issues)
    _timestamp(root.get("expires_at"), "expires_at", issues)
    _ref(root.get("study_manifest_ref"), "study_manifest_ref", issues, identity_key="study_id")

    candidate = _keys(
        root.get("candidate"),
        {"source_id", "repository", "revision", "path", "tree_sha256", "license"},
        set(),
        "candidate",
        issues,
    )
    if candidate:
        for key in ("source_id", "repository", "revision", "path", "license"):
            _string(candidate.get(key), f"candidate.{key}", issues)
        _sha(candidate.get("tree_sha256"), "candidate.tree_sha256", issues)

    authority = _keys(
        root.get("execution_authority"),
        {
            "credential_mode",
            "risk_accepted_by",
            "risk_accepted_at",
            "risk_scope",
            "exact_candidate_only",
            "sanitized_private_fixtures_only",
            "max_scored_calls",
            "network_policy",
            "allowed_hosts",
        },
        set(),
        "execution_authority",
        issues,
    )
    if authority:
        if authority.get("credential_mode") not in {
            "short_lived_brokered",
            "owner_accepted_reusable_local_auth",
        }:
            issues.append(StudyIssue("execution_authority.credential_mode", "is unsupported"))
        for key in ("risk_accepted_by", "risk_scope", "network_policy"):
            _string(authority.get(key), f"execution_authority.{key}", issues)
        _timestamp(
            authority.get("risk_accepted_at"), "execution_authority.risk_accepted_at", issues
        )
        for key in ("exact_candidate_only", "sanitized_private_fixtures_only"):
            if authority.get(key) is not True:
                issues.append(StudyIssue(f"execution_authority.{key}", "must be true"))
        _positive_int(
            authority.get("max_scored_calls"), "execution_authority.max_scored_calls", issues
        )
        hosts = authority.get("allowed_hosts")
        if (
            not isinstance(hosts, list)
            or not hosts
            or not all(isinstance(x, str) and x for x in hosts)
        ):
            issues.append(
                StudyIssue("execution_authority.allowed_hosts", "must be non-empty strings")
            )

    boundary = _keys(
        root.get("evidence_boundary"),
        {
            "task_material",
            "provider_transfer",
            "public_projection",
            "chronology_claim",
            "claim_ceiling",
        },
        set(),
        "evidence_boundary",
        issues,
    )
    if boundary:
        for key in boundary:
            _string(boundary.get(key), f"evidence_boundary.{key}", issues)

    policy = _keys(
        root.get("owner_action_policy"),
        {"policy_id", "owner_id", "rules", "fallback", "global_install_eligible"},
        set(),
        "owner_action_policy",
        issues,
    )
    if policy:
        _string(policy.get("policy_id"), "owner_action_policy.policy_id", issues)
        _string(policy.get("owner_id"), "owner_action_policy.owner_id", issues)
        if policy.get("global_install_eligible") is not False:
            issues.append(
                StudyIssue(
                    "owner_action_policy.global_install_eligible", "must be false in this pilot"
                )
            )
        rules = policy.get("rules")
        seen: set[str] = set()
        if not isinstance(rules, list) or not rules:
            issues.append(StudyIssue("owner_action_policy.rules", "must be a non-empty array"))
        else:
            for index, rule_value in enumerate(rules):
                location = f"owner_action_policy.rules.{index}"
                rule = _keys(
                    rule_value,
                    {"rule_id", "effect_outcomes", "disposition", "scope", "action_kind"},
                    set(),
                    location,
                    issues,
                )
                if not rule:
                    continue
                rule_id = _string(rule.get("rule_id"), f"{location}.rule_id", issues)
                if rule_id in seen:
                    issues.append(StudyIssue(f"{location}.rule_id", "must be unique"))
                elif rule_id:
                    seen.add(rule_id)
                outcomes = rule.get("effect_outcomes")
                if (
                    not isinstance(outcomes, list)
                    or not outcomes
                    or not all(isinstance(x, str) and x for x in outcomes)
                ):
                    issues.append(
                        StudyIssue(f"{location}.effect_outcomes", "must be non-empty strings")
                    )
                if rule.get("disposition") not in _DISPOSITIONS:
                    issues.append(StudyIssue(f"{location}.disposition", "is unsupported"))
                _string(rule.get("scope"), f"{location}.scope", issues)
                _string(rule.get("action_kind"), f"{location}.action_kind", issues)
        fallback = policy.get("fallback")
        if fallback not in {"keep_optional", "manual_review"}:
            issues.append(StudyIssue("owner_action_policy.fallback", "is unsupported"))

    roles = root.get("roles")
    required_roles = {"task_author", "operator", "evaluator", "decision_owner", "action_owner"}
    if (
        not isinstance(roles, dict)
        or set(roles) != required_roles
        or not all(isinstance(value, str) and value for value in roles.values())
    ):
        issues.append(StudyIssue("roles", f"must name exactly {sorted(required_roles)}"))
    overlaps = root.get("role_overlaps")
    if (
        not isinstance(overlaps, list)
        or not overlaps
        or not all(isinstance(value, str) and value for value in overlaps)
    ):
        issues.append(StudyIssue("role_overlaps", "must disclose at least one overlap"))
    stop_rules = root.get("stop_rules")
    if (
        not isinstance(stop_rules, list)
        or not stop_rules
        or not all(isinstance(value, str) and value for value in stop_rules)
    ):
        issues.append(StudyIssue("stop_rules", "must contain non-empty strings"))
    follow_up = _keys(
        root.get("follow_up_plan"),
        {"owner_id", "due_at", "window", "signals", "reversal_trigger"},
        set(),
        "follow_up_plan",
        issues,
    )
    if follow_up:
        _string(follow_up.get("owner_id"), "follow_up_plan.owner_id", issues)
        _timestamp(follow_up.get("due_at"), "follow_up_plan.due_at", issues)
        _string(follow_up.get("window"), "follow_up_plan.window", issues)
        _string(follow_up.get("reversal_trigger"), "follow_up_plan.reversal_trigger", issues)
        signals = follow_up.get("signals")
        if (
            not isinstance(signals, list)
            or not signals
            or not all(isinstance(value, str) and value for value in signals)
        ):
            issues.append(StudyIssue("follow_up_plan.signals", "must be non-empty strings"))
    return issues


def validate_freeze(data: Mapping[str, Any]) -> list[StudyIssue]:
    issues: list[StudyIssue] = []
    root = _keys(
        data,
        {
            "schema_version",
            "freeze_id",
            "study_id",
            "study_revision",
            "frozen_at",
            "scored_calls_executed",
            "study_manifest_ref",
            "admission_ref",
            "source_lock_ref",
            "candidate",
            "conditions",
            "private_pack",
            "code_hashes",
            "prompt_sha256",
            "runtime",
            "budget",
            "schedule",
            "decision_rule",
            "roles",
        },
        set(),
        "freeze",
        issues,
    )
    if root is None:
        return issues
    if root.get("schema_version") != FREEZE_SCHEMA_VERSION:
        issues.append(StudyIssue("schema_version", f"must equal {FREEZE_SCHEMA_VERSION}"))
    for key in ("freeze_id", "study_id"):
        value = _string(root.get(key), key, issues)
        if value and _ID.fullmatch(value) is None:
            issues.append(StudyIssue(key, "must be a normalized ID"))
    _positive_int(root.get("study_revision"), "study_revision", issues)
    _timestamp(root.get("frozen_at"), "frozen_at", issues)
    if root.get("scored_calls_executed") != 0:
        issues.append(StudyIssue("scored_calls_executed", "must equal zero"))
    manifest_ref = _ref(
        root.get("study_manifest_ref"), "study_manifest_ref", issues, identity_key="study_id"
    )
    admission_ref = _ref(
        root.get("admission_ref"), "admission_ref", issues, identity_key="admission_id"
    )
    lock_ref = _ref(
        root.get("source_lock_ref"), "source_lock_ref", issues, identity_key="source_id"
    )
    if manifest_ref and manifest_ref.get("study_id") != root.get("study_id"):
        issues.append(StudyIssue("study_manifest_ref.study_id", "must match study_id"))
    if admission_ref and not str(admission_ref.get("admission_id", "")).startswith(
        str(root.get("study_id", ""))
    ):
        issues.append(StudyIssue("admission_ref.admission_id", "must belong to the study"))
    if lock_ref:
        _string(lock_ref.get("source_id"), "source_lock_ref.source_id", issues)

    candidate = _keys(
        root.get("candidate"),
        {"source_id", "revision", "path", "tree_sha256"},
        set(),
        "candidate",
        issues,
    )
    if candidate:
        for key in ("source_id", "revision", "path"):
            _string(candidate.get(key), f"candidate.{key}", issues)
        _sha(candidate.get("tree_sha256"), "candidate.tree_sha256", issues)
        if lock_ref and candidate.get("source_id") != lock_ref.get("source_id"):
            issues.append(StudyIssue("candidate.source_id", "must match source_lock_ref"))

    condition_ids: set[str] = set()
    conditions = root.get("conditions")
    if not isinstance(conditions, list) or len(conditions) != 2:
        issues.append(StudyIssue("conditions", "must contain exactly B0 and S1"))
    else:
        for index, value in enumerate(conditions):
            location = f"conditions.{index}"
            condition = _keys(
                value,
                {"condition_id", "role", "intervention_sha256"},
                set(),
                location,
                issues,
            )
            if not condition:
                continue
            condition_id = _string(
                condition.get("condition_id"), f"{location}.condition_id", issues
            )
            if condition_id:
                condition_ids.add(condition_id)
            role = condition.get("role")
            if role not in {"baseline", "treatment"}:
                issues.append(StudyIssue(f"{location}.role", "must be baseline or treatment"))
            digest = condition.get("intervention_sha256")
            if role == "baseline" and digest is not None:
                issues.append(StudyIssue(f"{location}.intervention_sha256", "must be null"))
            if role == "treatment":
                _sha(digest, f"{location}.intervention_sha256", issues)
    if condition_ids != {"B0", "S1"}:
        issues.append(StudyIssue("conditions", "must use exact IDs B0 and S1"))

    pack = _keys(
        root.get("private_pack"),
        {"uri", "sha256", "task_ids", "strata"},
        set(),
        "private_pack",
        issues,
    )
    task_ids: set[str] = set()
    if pack:
        uri = _string(pack.get("uri"), "private_pack.uri", issues)
        if uri and not uri.startswith("urn:kizz:ael:private-pack:"):
            issues.append(StudyIssue("private_pack.uri", "must use a private-pack URN"))
        _sha(pack.get("sha256"), "private_pack.sha256", issues)
        values = pack.get("task_ids")
        if not isinstance(values, list) or len(values) != 4:
            issues.append(StudyIssue("private_pack.task_ids", "must contain exactly four IDs"))
        else:
            for index, value in enumerate(values):
                parsed = _string(value, f"private_pack.task_ids.{index}", issues)
                if parsed:
                    task_ids.add(parsed)
            if len(task_ids) != len(values):
                issues.append(StudyIssue("private_pack.task_ids", "must be unique"))
        strata = pack.get("strata")
        if not isinstance(strata, dict) or set(strata) != task_ids:
            issues.append(StudyIssue("private_pack.strata", "must map every task ID"))
        elif set(strata.values()) != {"cross-boundary-contract", "state-order-lifecycle"}:
            issues.append(StudyIssue("private_pack.strata", "must contain the two admitted strata"))
        elif any(list(strata.values()).count(value) != 2 for value in set(strata.values())):
            issues.append(StudyIssue("private_pack.strata", "must contain two tasks per stratum"))

    code_hashes = _keys(
        root.get("code_hashes"),
        {"runner", "decision", "materializer", "execution"},
        set(),
        "code_hashes",
        issues,
    )
    if code_hashes:
        for key in code_hashes:
            _sha(code_hashes.get(key), f"code_hashes.{key}", issues)
    _sha(root.get("prompt_sha256"), "prompt_sha256", issues)

    runtime = _keys(
        root.get("runtime"),
        {
            "harness",
            "harness_version",
            "model",
            "reasoning_effort",
            "runner_image",
            "runner_image_id",
            "proxy_image",
            "proxy_image_id",
            "evaluator_image",
            "evaluator_image_id",
            "network_policy",
        },
        set(),
        "runtime",
        issues,
    )
    if runtime:
        for key in runtime:
            _string(runtime.get(key), f"runtime.{key}", issues)
        for key in ("runner_image_id", "proxy_image_id", "evaluator_image_id"):
            value = runtime.get(key)
            if isinstance(value, str) and not value.startswith("sha256:"):
                issues.append(StudyIssue(f"runtime.{key}", "must be a Docker sha256 ID"))

    budget = _keys(
        root.get("budget"),
        {"max_scored_calls", "per_run_timeout_seconds", "max_generated_tokens"},
        set(),
        "budget",
        issues,
    )
    max_calls = None
    if budget:
        max_calls = _positive_int(budget.get("max_scored_calls"), "budget.max_scored_calls", issues)
        _positive_int(
            budget.get("per_run_timeout_seconds"), "budget.per_run_timeout_seconds", issues
        )
        _positive_int(budget.get("max_generated_tokens"), "budget.max_generated_tokens", issues)

    schedule = root.get("schedule")
    keys: set[tuple[str, str, int]] = set()
    sequences: set[int] = set()
    if not isinstance(schedule, list) or not schedule:
        issues.append(StudyIssue("schedule", "must contain frozen cells"))
    else:
        for index, value in enumerate(schedule):
            location = f"schedule.{index}"
            entry = _keys(
                value,
                {"sequence", "task_id", "condition_id", "repeat_index"},
                set(),
                location,
                issues,
            )
            if not entry:
                continue
            sequence = _positive_int(entry.get("sequence"), f"{location}.sequence", issues)
            task_id = _string(entry.get("task_id"), f"{location}.task_id", issues)
            condition_id = _string(entry.get("condition_id"), f"{location}.condition_id", issues)
            repeat = _positive_int(entry.get("repeat_index"), f"{location}.repeat_index", issues)
            if sequence:
                sequences.add(sequence)
            if task_id and condition_id and repeat:
                keys.add((task_id, condition_id, repeat))
        expected = {(task, condition, 1) for task in task_ids for condition in condition_ids}
        if keys != expected:
            issues.append(StudyIssue("schedule", "must cover every task-condition pair once"))
        if sequences != set(range(1, len(schedule) + 1)):
            issues.append(StudyIssue("schedule", "sequence must be contiguous from one"))
        if len(keys) != len(schedule):
            issues.append(StudyIssue("schedule", "must not contain duplicate cells"))
        if max_calls and len(schedule) != max_calls:
            issues.append(StudyIssue("budget.max_scored_calls", "must equal schedule length"))
        if len(schedule) != 8:
            issues.append(StudyIssue("schedule", "this pilot requires exactly eight cells"))

    decision = _keys(
        root.get("decision_rule"),
        {
            "route_requires_favorable_tasks_per_stratum",
            "maximum_unfavorable_for_route",
            "reject_at_unfavorable_pairs",
            "require_zero_treatment_critical_failures",
            "require_all_treatment_activations",
            "invalid_outcome",
        },
        set(),
        "decision_rule",
        issues,
    )
    if decision:
        if decision.get("route_requires_favorable_tasks_per_stratum") != 2:
            issues.append(
                StudyIssue(
                    "decision_rule.route_requires_favorable_tasks_per_stratum", "must equal two"
                )
            )
        if decision.get("maximum_unfavorable_for_route") != 0:
            issues.append(StudyIssue("decision_rule.maximum_unfavorable_for_route", "must be zero"))
        if decision.get("reject_at_unfavorable_pairs") != 2:
            issues.append(StudyIssue("decision_rule.reject_at_unfavorable_pairs", "must equal two"))
        for key in (
            "require_zero_treatment_critical_failures",
            "require_all_treatment_activations",
        ):
            if decision.get(key) is not True:
                issues.append(StudyIssue(f"decision_rule.{key}", "must be true"))
        if decision.get("invalid_outcome") != "invalid_manual_review":
            issues.append(
                StudyIssue("decision_rule.invalid_outcome", "must equal invalid_manual_review")
            )
    roles = root.get("roles")
    if not isinstance(roles, dict) or not all(
        isinstance(value, str) and value for value in roles.values()
    ):
        issues.append(StudyIssue("roles", "must name research roles"))
    return issues


def deterministic_schedule(
    task_ids: list[str], condition_ids: list[str], seed: str
) -> list[dict[str, object]]:
    entries = [
        {"task_id": task_id, "condition_id": condition_id, "repeat_index": 1}
        for task_id in task_ids
        for condition_id in condition_ids
    ]
    entries.sort(
        key=lambda entry: hashlib.sha256(
            f"{seed}:{entry['task_id']}:{entry['condition_id']}:1".encode()
        ).digest()
    )
    return [{"sequence": index, **entry} for index, entry in enumerate(entries, start=1)]


def verify_private_pack(freeze: Mapping[str, Any], root: Path, tree_digest: str) -> None:
    root = root.absolute()
    if root.is_symlink() or not root.is_dir():
        raise SandboxError("private pack root is missing or unsafe")
    canary = root / ".ael-private-canary"
    if not canary.is_file() or not canary.read_text(encoding="utf-8").startswith(
        PRIVATE_CANARY_PREFIX
    ):
        raise SandboxError("private pack lacks its publication canary")
    expected = freeze["private_pack"]["sha256"]
    if tree_digest != expected:
        raise SandboxError(
            f"private pack hash mismatch: expected {expected}, observed {tree_digest}"
        )


def validate_observations(
    freeze_path: Path, freeze: Mapping[str, Any], document: Mapping[str, Any]
) -> list[dict[str, Any]]:
    if document.get("schema_version") != OBSERVATIONS_SCHEMA_VERSION:
        raise SandboxError(f"observations must use {OBSERVATIONS_SCHEMA_VERSION}")
    if document.get("freeze_sha256") != sha256_path(freeze_path):
        raise SandboxError("observations are not bound to the supplied freeze")
    observations = document.get("observations")
    if not isinstance(observations, list) or not observations:
        raise SandboxError("observations must contain scored cells")
    expected = {
        (entry["task_id"], entry["condition_id"], entry["repeat_index"]): entry["sequence"]
        for entry in freeze["schedule"]
    }
    actual: dict[tuple[str, str, int], int] = {}
    for observation in observations:
        if not isinstance(observation, dict):
            raise SandboxError("observation must be an object")
        key = (
            observation.get("task_id"),
            observation.get("condition_id"),
            observation.get("repeat_index"),
        )
        if (
            not isinstance(key[0], str)
            or not isinstance(key[1], str)
            or not isinstance(key[2], int)
        ):
            raise SandboxError("observation lacks cell identity")
        if key in actual:
            raise SandboxError("observations contain a duplicate cell")
        sequence = observation.get("schedule_sequence")
        if not isinstance(sequence, int):
            raise SandboxError("observation lacks schedule sequence")
        actual[key] = sequence
    if actual != expected:
        raise SandboxError("observations do not cover the exact frozen schedule")
    return observations


def authorize_scored_run(
    admission: Mapping[str, Any],
    freeze: Mapping[str, Any],
    observed: Mapping[str, Any],
) -> None:
    admission_issues = validate_admission(admission)
    freeze_issues = validate_freeze(freeze)
    if admission_issues:
        raise SandboxError(f"admission has {len(admission_issues)} issue(s): {admission_issues[0]}")
    if freeze_issues:
        raise SandboxError(f"freeze has {len(freeze_issues)} issue(s): {freeze_issues[0]}")
    expected = {
        "admission_sha256": freeze["admission_ref"]["sha256"],
        "manifest_sha256": freeze["study_manifest_ref"]["sha256"],
        "source_lock_sha256": freeze["source_lock_ref"]["sha256"],
        "candidate_tree_sha256": freeze["candidate"]["tree_sha256"],
        "private_pack_sha256": freeze["private_pack"]["sha256"],
        "runner_sha256": freeze["code_hashes"]["runner"],
        "decision_sha256": freeze["code_hashes"]["decision"],
        "materializer_sha256": freeze["code_hashes"]["materializer"],
        "execution_sha256": freeze["code_hashes"]["execution"],
        "prompt_sha256": freeze["prompt_sha256"],
        "runner_image_id": freeze["runtime"]["runner_image_id"],
        "proxy_image_id": freeze["runtime"]["proxy_image_id"],
        "evaluator_image_id": freeze["runtime"]["evaluator_image_id"],
    }
    mismatches = [key for key, value in expected.items() if observed.get(key) != value]
    if mismatches:
        raise SandboxError(
            f"scored run is not authorized; binding mismatch: {', '.join(mismatches)}"
        )
    if admission["study_manifest_ref"]["sha256"] != freeze["study_manifest_ref"]["sha256"]:
        raise SandboxError("admission and freeze bind different manifests")
    if admission["candidate"]["tree_sha256"] != freeze["candidate"]["tree_sha256"]:
        raise SandboxError("admission and freeze bind different candidates")
    if admission["execution_authority"]["max_scored_calls"] < len(freeze["schedule"]):
        raise SandboxError("freeze schedule exceeds admitted scored-call authority")
