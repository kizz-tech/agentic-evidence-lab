"""Pilot-local measurement-quality preflight for prospective AEL studies.

This module is intentionally adjacent to Contract v0.  It validates a
hash-bound design-quality profile before scored work and projects descriptive
quality facets.  A conformant preflight is not evidence that a study is
scientifically valid, independently replicated, or outcome-proven.
"""

from __future__ import annotations

import datetime as _datetime
import json
import math
import os
import re
import stat
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ael.sandbox import SandboxError
from ael.validation import MAX_JSON_BYTES, sha256_path, validate

QUALITY_PROFILE_SCHEMA_VERSION = "ael.study-quality-profile/0.1-pilot"
QUALITY_PREFLIGHT_VERSION = "ael.study-quality-preflight/0.1-pilot"

_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_CLAIM_CEILINGS = {
    "artifact",
    "workflow",
    "operational_stack",
    "factor_causal",
    "model_only",
}
_TASK_STATUSES = {"audited", "independently_audited"}
_EVALUATOR_STATUSES = {"calibrated", "independently_checked"}
_CONFIRMATION_ROLES = {"development", "active_confirmation", "retired_confirmation"}
_DISCLOSURE_STATES = {"public_development", "active_sequestered", "retired_public"}
_UNCERTAINTY_STATES = {"planned", "not_estimable"}
_ORDER_POLICIES = {"randomized", "blocked", "hash_keyed", "fixed"}
_RELIABILITY_COVERAGE = {
    "single_run",
    "repeated",
    "perturbation_tested",
    "fault_tested",
}
_TASK_AUDIT_CHECKS = {
    "instruction_test_alignment",
    "oracle_validation",
    "alternative_valid_solutions",
    "shortcut_rejection",
    "environment_validation",
}


@dataclass(frozen=True)
class StudyQualityIssue:
    """One stable, ordered preflight finding."""

    severity: str
    code: str
    location: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity,
            "code": self.code,
            "location": self.location,
            "message": self.message,
        }

    def __str__(self) -> str:
        return f"{self.severity} {self.code} {self.location}: {self.message}"


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


def _contains_symlink(path: Path) -> bool:
    candidate = path.absolute()
    while True:
        try:
            if candidate.is_symlink():
                return True
        except OSError:
            return True
        parent = candidate.parent
        if parent == candidate:
            return False
        candidate = parent


def _regular_file(path: Path, label: str) -> None:
    absolute = path.absolute()
    if _contains_symlink(absolute):
        raise SandboxError(f"{label} must not use symlinks: {path}")
    try:
        info = absolute.lstat()
    except OSError as exc:
        raise SandboxError(f"{label} is missing: {path}: {exc}") from exc
    if not stat.S_ISREG(info.st_mode):
        raise SandboxError(f"{label} must be a regular file: {path}")


def load_profile(path: Path) -> dict[str, Any]:
    """Load one strict JSON quality profile without evaluating its references."""

    path = path.absolute()
    _regular_file(path, "study quality profile")
    if path.stat().st_size > MAX_JSON_BYTES:
        raise SandboxError(f"study quality profile exceeds {MAX_JSON_BYTES} bytes: {path}")
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_strict_object,
            parse_float=_finite_float,
            parse_constant=_reject_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise SandboxError(f"study quality profile is unreadable: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SandboxError(f"study quality profile must be an object: {path}")
    return value


def _issue(
    issues: list[StudyQualityIssue],
    severity: str,
    code: str,
    location: str,
    message: str,
) -> None:
    issues.append(StudyQualityIssue(severity, code, location, message))


def _object(
    value: object,
    required: set[str],
    optional: set[str],
    location: str,
    issues: list[StudyQualityIssue],
) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        _issue(issues, "error", "QP-E001", location, "must be an object")
        return None
    missing = required - set(value)
    unknown = set(value) - required - optional
    if missing:
        _issue(
            issues,
            "error",
            "QP-E002",
            location,
            f"missing keys: {', '.join(sorted(missing))}",
        )
    if unknown:
        _issue(
            issues,
            "error",
            "QP-E003",
            location,
            f"unknown keys: {', '.join(sorted(unknown))}",
        )
    return value


def _string(value: object, location: str, issues: list[StudyQualityIssue]) -> str | None:
    if not isinstance(value, str) or not value.strip():
        _issue(issues, "error", "QP-E004", location, "must be a non-empty string")
        return None
    return value


def _positive_int(value: object, location: str, issues: list[StudyQualityIssue]) -> int | None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        _issue(issues, "error", "QP-E005", location, "must be a positive integer")
        return None
    return value


def _nonnegative_int(value: object, location: str, issues: list[StudyQualityIssue]) -> int | None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        _issue(issues, "error", "QP-E006", location, "must be a non-negative integer")
        return None
    return value


def _date(value: object, location: str, issues: list[StudyQualityIssue]) -> str | None:
    parsed = _string(value, location, issues)
    if parsed is None:
        return None
    if _DATE.fullmatch(parsed) is None:
        _issue(issues, "error", "QP-E007", location, "must use YYYY-MM-DD")
        return None
    try:
        _datetime.date.fromisoformat(parsed)
    except ValueError:
        _issue(issues, "error", "QP-E007", location, "must be a calendar date")
        return None
    return parsed


def _string_array(
    value: object,
    location: str,
    issues: list[StudyQualityIssue],
    *,
    allow_empty: bool = False,
) -> list[str] | None:
    if (
        not isinstance(value, list)
        or (not value and not allow_empty)
        or not all(isinstance(item, str) and item.strip() for item in value)
        or len(set(value)) != len(value)
    ):
        suffix = "unique strings" if allow_empty else "non-empty unique strings"
        _issue(issues, "error", "QP-E008", location, f"must contain {suffix}")
        return None
    return value


def _reference(
    value: object,
    location: str,
    issues: list[StudyQualityIssue],
    *,
    identity: str | None = None,
) -> dict[str, Any] | None:
    required = {"uri", "sha256"} | ({identity} if identity else set())
    ref = _object(value, required, set(), location, issues)
    if ref is None:
        return None
    _string(ref.get("uri"), f"{location}.uri", issues)
    digest = _string(ref.get("sha256"), f"{location}.sha256", issues)
    if digest is not None and _SHA256.fullmatch(digest) is None:
        _issue(
            issues,
            "error",
            "QP-E009",
            f"{location}.sha256",
            "must be 64 lowercase hexadecimal characters",
        )
    if identity:
        if identity == "revision":
            _positive_int(ref.get(identity), f"{location}.{identity}", issues)
        else:
            _string(ref.get(identity), f"{location}.{identity}", issues)
    return ref


def validate_profile(profile: Mapping[str, Any]) -> list[StudyQualityIssue]:
    """Validate pilot profile shape and intrinsic preflight declarations."""

    issues: list[StudyQualityIssue] = []
    root = _object(
        profile,
        {
            "schema_version",
            "profile_id",
            "assessed_at",
            "revalidate_after",
            "valid_through",
            "study_ref",
            "prospective_state",
            "construct",
            "task_quality",
            "evaluator_quality",
            "analysis_quality",
            "execution_declaration",
        },
        set(),
        "profile",
        issues,
    )
    if root is None:
        return _sorted_issues(issues)
    if root.get("schema_version") != QUALITY_PROFILE_SCHEMA_VERSION:
        _issue(
            issues,
            "error",
            "QP-E010",
            "schema_version",
            f"must equal {QUALITY_PROFILE_SCHEMA_VERSION}",
        )
    _string(root.get("profile_id"), "profile_id", issues)
    assessed_at = _date(root.get("assessed_at"), "assessed_at", issues)
    revalidate_after = _date(root.get("revalidate_after"), "revalidate_after", issues)
    valid_through = _date(root.get("valid_through"), "valid_through", issues)
    if (
        assessed_at
        and revalidate_after
        and valid_through
        and not assessed_at <= revalidate_after <= valid_through
    ):
        _issue(
            issues,
            "error",
            "QP-E011",
            "freshness",
            "must satisfy assessed_at <= revalidate_after <= valid_through",
        )

    study_ref = _object(
        root.get("study_ref"),
        {"study_id", "revision", "uri", "sha256"},
        set(),
        "study_ref",
        issues,
    )
    if study_ref:
        _string(study_ref.get("study_id"), "study_ref.study_id", issues)
        _positive_int(study_ref.get("revision"), "study_ref.revision", issues)
        _string(study_ref.get("uri"), "study_ref.uri", issues)
        digest = _string(study_ref.get("sha256"), "study_ref.sha256", issues)
        if digest is not None and _SHA256.fullmatch(digest) is None:
            _issue(
                issues,
                "error",
                "QP-E009",
                "study_ref.sha256",
                "must be 64 lowercase hexadecimal characters",
            )

    prospective = _object(
        root.get("prospective_state"),
        {"scored_calls_executed", "declaration"},
        set(),
        "prospective_state",
        issues,
    )
    if prospective:
        calls = _nonnegative_int(
            prospective.get("scored_calls_executed"),
            "prospective_state.scored_calls_executed",
            issues,
        )
        if calls is not None and calls != 0:
            _issue(
                issues,
                "error",
                "QP-E012",
                "prospective_state.scored_calls_executed",
                "must equal zero before scored work",
            )
        _string(prospective.get("declaration"), "prospective_state.declaration", issues)

    construct = _object(
        root.get("construct"),
        {"operational_definition", "target_claim", "claim_ceiling", "falsifier"},
        set(),
        "construct",
        issues,
    )
    if construct:
        for key in ("operational_definition", "target_claim", "falsifier"):
            _string(construct.get(key), f"construct.{key}", issues)
        if construct.get("claim_ceiling") not in _CLAIM_CEILINGS:
            _issue(
                issues,
                "error",
                "QP-E013",
                "construct.claim_ceiling",
                f"must be one of {sorted(_CLAIM_CEILINGS)}",
            )

    task_quality = _object(
        root.get("task_quality"),
        {
            "status",
            "construct_alignment",
            "provenance_ref",
            "audit_ref",
            "audit_checks",
            "confirmation_role",
            "disclosure_state",
            "adaptive_uses",
        },
        set(),
        "task_quality",
        issues,
    )
    if task_quality:
        if task_quality.get("status") not in _TASK_STATUSES:
            _issue(
                issues,
                "error",
                "QP-E014",
                "task_quality.status",
                f"must be one of {sorted(_TASK_STATUSES)}",
            )
        _string(task_quality.get("construct_alignment"), "task_quality.construct_alignment", issues)
        _reference(task_quality.get("provenance_ref"), "task_quality.provenance_ref", issues)
        _reference(task_quality.get("audit_ref"), "task_quality.audit_ref", issues)
        checks = _object(
            task_quality.get("audit_checks"),
            _TASK_AUDIT_CHECKS,
            set(),
            "task_quality.audit_checks",
            issues,
        )
        if checks:
            for key in sorted(_TASK_AUDIT_CHECKS):
                if checks.get(key) != "pass":
                    _issue(
                        issues,
                        "error",
                        "QP-E015",
                        f"task_quality.audit_checks.{key}",
                        "must equal pass",
                    )
        confirmation_role = task_quality.get("confirmation_role")
        if confirmation_role not in _CONFIRMATION_ROLES:
            _issue(
                issues,
                "error",
                "QP-E016",
                "task_quality.confirmation_role",
                f"must be one of {sorted(_CONFIRMATION_ROLES)}",
            )
        disclosure_state = task_quality.get("disclosure_state")
        if disclosure_state not in _DISCLOSURE_STATES:
            _issue(
                issues,
                "error",
                "QP-E017",
                "task_quality.disclosure_state",
                f"must be one of {sorted(_DISCLOSURE_STATES)}",
            )
        adaptive_uses = _nonnegative_int(
            task_quality.get("adaptive_uses"), "task_quality.adaptive_uses", issues
        )
        if confirmation_role == "active_confirmation" and (
            disclosure_state != "active_sequestered" or adaptive_uses != 0
        ):
            _issue(
                issues,
                "error",
                "QP-E018",
                "task_quality",
                "active confirmation requires active_sequestered disclosure and zero adaptive uses",
            )

    evaluator = _object(
        root.get("evaluator_quality"),
        {
            "status",
            "scoring_rule",
            "calibration_ref",
            "known_pass_cases",
            "known_fail_cases",
            "known_error_profile",
            "adjudication",
        },
        set(),
        "evaluator_quality",
        issues,
    )
    if evaluator:
        if evaluator.get("status") not in _EVALUATOR_STATUSES:
            _issue(
                issues,
                "error",
                "QP-E019",
                "evaluator_quality.status",
                f"must be one of {sorted(_EVALUATOR_STATUSES)}",
            )
        for key in ("scoring_rule", "known_error_profile", "adjudication"):
            _string(evaluator.get(key), f"evaluator_quality.{key}", issues)
        _reference(evaluator.get("calibration_ref"), "evaluator_quality.calibration_ref", issues)
        _positive_int(
            evaluator.get("known_pass_cases"), "evaluator_quality.known_pass_cases", issues
        )
        _positive_int(
            evaluator.get("known_fail_cases"), "evaluator_quality.known_fail_cases", issues
        )

    analysis = _object(
        root.get("analysis_quality"),
        {"decision_threshold", "missing_invalid_rule", "uncertainty"},
        set(),
        "analysis_quality",
        issues,
    )
    if analysis:
        _string(analysis.get("decision_threshold"), "analysis_quality.decision_threshold", issues)
        _string(
            analysis.get("missing_invalid_rule"), "analysis_quality.missing_invalid_rule", issues
        )
        uncertainty = _object(
            analysis.get("uncertainty"),
            {"status"},
            {"method", "reason"},
            "analysis_quality.uncertainty",
            issues,
        )
        if uncertainty:
            state = uncertainty.get("status")
            if state not in _UNCERTAINTY_STATES:
                _issue(
                    issues,
                    "error",
                    "QP-E020",
                    "analysis_quality.uncertainty.status",
                    f"must be one of {sorted(_UNCERTAINTY_STATES)}",
                )
            if state == "planned":
                _string(uncertainty.get("method"), "analysis_quality.uncertainty.method", issues)
                if "reason" in uncertainty:
                    _issue(
                        issues,
                        "error",
                        "QP-E003",
                        "analysis_quality.uncertainty.reason",
                        "is not allowed when status is planned",
                    )
            elif state == "not_estimable":
                _string(uncertainty.get("reason"), "analysis_quality.uncertainty.reason", issues)
                if "method" in uncertainty:
                    _issue(
                        issues,
                        "error",
                        "QP-E003",
                        "analysis_quality.uncertainty.method",
                        "is not allowed when status is not_estimable",
                    )

    execution = _object(
        root.get("execution_declaration"),
        {
            "task_count",
            "repeats_per_cell",
            "repeat_rationale",
            "order_policy",
            "order_rationale",
            "nuisance_factors",
            "reliability",
        },
        set(),
        "execution_declaration",
        issues,
    )
    if execution:
        _positive_int(execution.get("task_count"), "execution_declaration.task_count", issues)
        _positive_int(
            execution.get("repeats_per_cell"),
            "execution_declaration.repeats_per_cell",
            issues,
        )
        _string(execution.get("repeat_rationale"), "execution_declaration.repeat_rationale", issues)
        if execution.get("order_policy") not in _ORDER_POLICIES:
            _issue(
                issues,
                "error",
                "QP-E021",
                "execution_declaration.order_policy",
                f"must be one of {sorted(_ORDER_POLICIES)}",
            )
        _string(execution.get("order_rationale"), "execution_declaration.order_rationale", issues)
        _string_array(
            execution.get("nuisance_factors"),
            "execution_declaration.nuisance_factors",
            issues,
            allow_empty=True,
        )
        reliability = _object(
            execution.get("reliability"),
            {"coverage", "pass_k", "perturbation_plan", "fault_plan"},
            set(),
            "execution_declaration.reliability",
            issues,
        )
        if reliability:
            if reliability.get("coverage") not in _RELIABILITY_COVERAGE:
                _issue(
                    issues,
                    "error",
                    "QP-E022",
                    "execution_declaration.reliability.coverage",
                    f"must be one of {sorted(_RELIABILITY_COVERAGE)}",
                )
            pass_k = reliability.get("pass_k")
            if (
                not isinstance(pass_k, list)
                or not pass_k
                or not all(
                    isinstance(value, int) and not isinstance(value, bool) and value >= 1
                    for value in pass_k
                )
                or pass_k != sorted(set(pass_k))
            ):
                _issue(
                    issues,
                    "error",
                    "QP-E023",
                    "execution_declaration.reliability.pass_k",
                    "must be a sorted unique array of positive integers",
                )
            _string(
                reliability.get("perturbation_plan"),
                "execution_declaration.reliability.perturbation_plan",
                issues,
            )
            _string(
                reliability.get("fault_plan"),
                "execution_declaration.reliability.fault_plan",
                issues,
            )
    return _sorted_issues(issues)


def _repository_root(profile_path: Path, explicit: Path | None) -> Path:
    if explicit is not None:
        root = explicit.absolute()
        if _contains_symlink(root) or not root.is_dir():
            raise SandboxError(f"repository root is missing or unsafe: {root}")
        return root.resolve()
    start = profile_path.absolute().parent
    for candidate in (start, *start.parents):
        if (candidate / "pyproject.toml").is_file() and not _contains_symlink(
            candidate / "pyproject.toml"
        ):
            return candidate.resolve()
    raise SandboxError("could not locate repository root with pyproject.toml")


def _resolve_reference(
    profile_path: Path,
    reference: Mapping[str, Any],
    repository_root: Path,
    location: str,
    issues: list[StudyQualityIssue],
) -> Path | None:
    uri = reference.get("uri")
    digest = reference.get("sha256")
    if not isinstance(uri, str) or not isinstance(digest, str):
        return None
    parsed = urlparse(uri)
    if (
        parsed.scheme
        or parsed.netloc
        or parsed.query
        or parsed.fragment
        or uri.startswith("/")
        or "\\" in uri
        or "\x00" in uri
        or any(part in {"", ".", ".."} for part in Path(parsed.path).parts)
    ):
        _issue(issues, "error", "QP-E024", location, "must be a safe repository-relative ref")
        return None
    candidate = profile_path.parent / parsed.path
    if _contains_symlink(candidate):
        _issue(issues, "error", "QP-E024", location, "must not use symlinks")
        return None
    try:
        target = candidate.resolve()
    except OSError:
        _issue(issues, "error", "QP-E024", location, "cannot be resolved")
        return None
    if not target.is_relative_to(repository_root):
        _issue(issues, "error", "QP-E024", location, "escapes repository root")
        return None
    try:
        _regular_file(target, location)
    except SandboxError as exc:
        _issue(issues, "error", "QP-E024", location, str(exc))
        return None
    if sha256_path(target) != digest:
        _issue(issues, "error", "QP-E025", location, "SHA-256 does not match referenced bytes")
        return None
    return target


def _design_class(manifest: Mapping[str, Any]) -> str:
    roles = {
        task_pack.get("role")
        for task_pack in manifest.get("task_packs", [])
        if isinstance(task_pack, Mapping)
    }
    if "real_shadow" in roles:
        return "real_shadow"
    if roles and roles <= {"calibration", "adaptation"}:
        return "calibration"
    if manifest.get("comparison_mode") == "controlled_factor":
        return "controlled_pilot"
    return "screening"


def _independence(manifest: Mapping[str, Any]) -> str:
    claim = manifest.get("independence_claim")
    label = claim.get("label") if isinstance(claim, Mapping) else None
    if label == "independently_verified":
        return "external_replication"
    if label == "reproduced_third_party":
        return "role_separated"
    return "maintainer_only"


def _freshness(profile: Mapping[str, Any], as_of: str) -> str:
    revalidate_after = str(profile.get("revalidate_after", ""))
    valid_through = str(profile.get("valid_through", ""))
    if as_of > valid_through:
        return "invalidated"
    if as_of > revalidate_after:
        return "revalidation_due"
    return "current"


def _quality_axes(
    profile: Mapping[str, Any], manifest: Mapping[str, Any], as_of: str
) -> dict[str, str]:
    task = profile["task_quality"]
    evaluator = profile["evaluator_quality"]
    execution = profile["execution_declaration"]
    return {
        "design_class": _design_class(manifest),
        "task_validity": str(task["status"]),
        "evaluator_validity": str(evaluator["status"]),
        "sampling_strength": "decision_thresholded_pilot",
        "reliability_coverage": str(execution["reliability"]["coverage"]),
        "independence": _independence(manifest),
        "freshness": _freshness(profile, as_of),
    }


def _sorted_issues(issues: list[StudyQualityIssue]) -> list[StudyQualityIssue]:
    return sorted(issues, key=lambda item: (item.severity != "error", item.code, item.location))


def preflight(
    profile_path: Path,
    repository_root: Path | None = None,
    *,
    as_of: str | None = None,
) -> dict[str, Any]:
    """Run a deterministic offline preflight and return a machine projection."""

    profile_path = profile_path.absolute()
    profile = load_profile(profile_path)
    root = _repository_root(profile_path, repository_root)
    if not profile_path.resolve().is_relative_to(root):
        raise SandboxError("study quality profile must be inside the repository root")
    issues = validate_profile(profile)
    effective_as_of = as_of if as_of is not None else profile.get("assessed_at")
    effective_date = _date(effective_as_of, "preflight.as_of", issues)
    manifest: dict[str, Any] | None = None
    if not any(issue.severity == "error" for issue in issues):
        refs: list[tuple[str, Mapping[str, Any]]] = [
            ("study_ref", profile["study_ref"]),
            ("task_quality.provenance_ref", profile["task_quality"]["provenance_ref"]),
            ("task_quality.audit_ref", profile["task_quality"]["audit_ref"]),
            (
                "evaluator_quality.calibration_ref",
                profile["evaluator_quality"]["calibration_ref"],
            ),
        ]
        resolved: dict[str, Path] = {}
        for location, reference in refs:
            target = _resolve_reference(profile_path, reference, root, location, issues)
            if target is not None:
                resolved[location] = target
        manifest_path = resolved.get("study_ref")
        if manifest_path is not None:
            documents, validation_issues = validate([manifest_path])
            for validation_issue in validation_issues:
                _issue(
                    issues,
                    "error",
                    "QP-E026",
                    "study_ref",
                    f"referenced Contract manifest is invalid: {validation_issue.location}: {validation_issue.message}",
                )
            if len(documents) == 1 and documents[0].object_type == "study_manifest":
                manifest = documents[0].data
                if manifest.get("study_id") != profile["study_ref"].get("study_id"):
                    _issue(
                        issues,
                        "error",
                        "QP-E027",
                        "study_ref.study_id",
                        "does not match referenced manifest",
                    )
                if manifest.get("revision") != profile["study_ref"].get("revision"):
                    _issue(
                        issues,
                        "error",
                        "QP-E027",
                        "study_ref.revision",
                        "does not match referenced manifest",
                    )
                if manifest.get("status") not in {"draft", "frozen"}:
                    _issue(
                        issues,
                        "error",
                        "QP-E028",
                        "study_ref.status",
                        "referenced manifest must be draft or frozen before scored work",
                    )
                if manifest.get("comparison_mode") == "operational_stack" and profile[
                    "construct"
                ].get("claim_ceiling") in {"factor_causal", "model_only"}:
                    _issue(
                        issues,
                        "error",
                        "QP-E029",
                        "construct.claim_ceiling",
                        "operational-stack comparisons cannot claim factor or model causality",
                    )
    if manifest is not None:
        execution = profile["execution_declaration"]
        uncertainty = profile["analysis_quality"]["uncertainty"]
        if execution["repeats_per_cell"] == 1:
            _issue(
                issues,
                "warning",
                "QP-W001",
                "execution_declaration.repeats_per_cell",
                "one repeat supports a bounded pilot decision, not stability evidence",
            )
        if execution["order_policy"] in {"fixed", "hash_keyed"}:
            _issue(
                issues,
                "warning",
                "QP-W002",
                "execution_declaration.order_policy",
                "non-random order can preserve nuisance effects despite the declared rationale",
            )
        if uncertainty["status"] == "not_estimable":
            _issue(
                issues,
                "warning",
                "QP-W003",
                "analysis_quality.uncertainty",
                "effect uncertainty is explicitly not estimable",
            )
        if _independence(manifest) == "maintainer_only":
            _issue(
                issues,
                "warning",
                "QP-W004",
                "study_ref.independence_claim",
                "maintainer-only evaluation is not independent replication",
            )
        assessed_at = profile["assessed_at"]
        revalidate_after = profile["revalidate_after"]
        valid_through = profile["valid_through"]
        if effective_date is not None and effective_date < assessed_at:
            _issue(
                issues,
                "error",
                "QP-E030",
                "preflight.as_of",
                "must not predate the profile assessment",
            )
        elif effective_date is not None and effective_date > valid_through:
            _issue(
                issues,
                "error",
                "QP-E030",
                "preflight.as_of",
                "is later than the profile validity window",
            )
        elif effective_date is not None and effective_date > revalidate_after:
            _issue(
                issues,
                "warning",
                "QP-W005",
                "preflight.as_of",
                "the assessment has reached its declared revalidation window",
            )

    issues = _sorted_issues(issues)
    errors = [issue for issue in issues if issue.severity == "error"]
    warnings = [issue for issue in issues if issue.severity == "warning"]
    axes = (
        _quality_axes(profile, manifest, str(effective_as_of))
        if manifest is not None and effective_date is not None
        else {
            "design_class": "not_assessed",
            "task_validity": "not_assessed",
            "evaluator_validity": "not_assessed",
            "sampling_strength": "not_assessed",
            "reliability_coverage": "not_assessed",
            "independence": "not_assessed",
            "freshness": "not_assessed",
        }
    )
    if errors:
        status = "blocked"
    elif warnings:
        status = "conformant_with_warnings"
    else:
        status = "conformant"
    study_reference = profile.get("study_ref")
    if not isinstance(study_reference, Mapping):
        study_reference = {}
    return {
        "schema_version": QUALITY_PREFLIGHT_VERSION,
        "profile_id": profile.get("profile_id"),
        "profile_sha256": sha256_path(profile_path),
        "study": {
            "study_id": study_reference.get("study_id"),
            "revision": study_reference.get("revision"),
            "manifest_sha256": study_reference.get("sha256"),
        },
        "assessed_at": profile.get("assessed_at"),
        "as_of": effective_as_of,
        "scope": "design_preflight",
        "status": status,
        "quality_axes": axes,
        "issues": [issue.as_dict() for issue in issues],
        "boundary": (
            "Conformance checks declared, hash-bound pre-run design evidence only; they do not "
            "prove scientific validity, chronology of execution, replication, transfer, or outcome."
        ),
    }


def public_projection(
    profile_path: Path,
    repository_root: Path | None = None,
    *,
    as_of: str | None = None,
) -> dict[str, Any]:
    """Return the bounded public quality projection or fail closed."""

    result = preflight(profile_path, repository_root, as_of=as_of)
    if result["status"] == "blocked":
        codes = ", ".join(
            issue["code"] for issue in result["issues"] if issue["severity"] == "error"
        )
        raise SandboxError(f"study quality preflight is blocked: {codes}")
    return result


def render_preflight(result: Mapping[str, Any]) -> str:
    """Render one deterministic human-readable preflight summary."""

    lines = [
        f"# Study Quality Preflight: {result['profile_id']}",
        "",
        f"- Study: `{result['study']['study_id']}` revision `{result['study']['revision']}`",
        f"- Assessed at: `{result['assessed_at']}`",
        f"- As of: `{result['as_of']}`",
        f"- Status: **{result['status']}**",
        f"- Scope: `{result['scope']}`",
        "",
        "## Quality axes",
        "",
    ]
    for key, value in result["quality_axes"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Findings", ""])
    if result["issues"]:
        for issue in result["issues"]:
            lines.append(
                f"- **{issue['severity']} {issue['code']}** `{issue['location']}` — {issue['message']}"
            )
    else:
        lines.append("- No preflight findings.")
    lines.extend(["", "## Boundary", "", str(result["boundary"]), ""])
    return "\n".join(lines)


def _json_text(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"


def _write_or_check(path: Path, content: str, check: bool) -> None:
    path = path.absolute()
    parent = path.parent
    if _contains_symlink(parent):
        raise SandboxError(f"preflight output directory must not use symlinks: {parent}")
    if check:
        _regular_file(path, "preflight output")
        if path.read_text(encoding="utf-8") != content:
            raise SandboxError(f"preflight output differs: {path}")
        return
    parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        _regular_file(path, "preflight output")
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
        handle.write(content)
    try:
        temporary.chmod(0o644)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def materialize_preflight(
    profile_path: Path,
    *,
    json_output: Path | None = None,
    markdown_output: Path | None = None,
    check: bool = False,
    repository_root: Path | None = None,
    as_of: str | None = None,
) -> dict[str, Any]:
    """Run preflight and optionally materialize/check deterministic projections."""

    if check and json_output is None and markdown_output is None:
        raise SandboxError("--check requires --json-output or --markdown-output")
    result = preflight(profile_path, repository_root, as_of=as_of)
    if json_output is not None:
        _write_or_check(json_output, _json_text(result), check)
    if markdown_output is not None:
        _write_or_check(markdown_output, render_preflight(result), check)
    return result


__all__ = [
    "QUALITY_PREFLIGHT_VERSION",
    "QUALITY_PROFILE_SCHEMA_VERSION",
    "StudyQualityIssue",
    "load_profile",
    "materialize_preflight",
    "preflight",
    "public_projection",
    "render_preflight",
    "validate_profile",
]
