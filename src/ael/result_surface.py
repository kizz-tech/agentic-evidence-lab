"""Fail-closed projection of Contract v0 receipts into public result cards.

The publication profile in ``studies/public-results.json`` is deliberately
small.  It selects immutable receipt/report bytes and supplies only publication
metadata that Contract v0 does not own.  Every empirical value in generated
views is copied from a validated receipt; profile text cannot author a finding
or raise its proof level.
"""

from __future__ import annotations

import datetime as _datetime
import hashlib
import json
import math
import os
import re
import stat
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any, NoReturn
from urllib.parse import urlparse

from jsonschema import Draft202012Validator, FormatChecker

from ael import __version__
from ael.sandbox import SandboxError
from ael.study_audit import audit_study_bundle
from ael.validation import MAX_JSON_BYTES, SCHEMA_FILES, sha256_path, validate

PUBLIC_RESULTS_SCHEMA_VERSION = "ael.public-results/0.1"
PUBLICATION_PROJECTION_POLICY = "ael.publication-projection/0.1"
GENERATOR_NAME = "agentic-evidence-lab"
GENERATOR_VERSION = __version__

_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_CARD_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
_SCHEMES = {"evidence_graph", "frozen_public_bundle"}
_VISIBILITIES = {"public", "private", "hidden", "embargoed"}
_MATERIAL_AVAILABILITY = {"public", "withheld", "not_retained", "not_collected"}
_HISTORY_UNKNOWN = "not_declared_historical"
_HISTORY_FRESHNESS_UNKNOWN = "unassessed"
_ADAPTERS = {"pbt-v2"}

# Contract v0 has two independent ladders: claim levels describe what a
# statement says, while evidence levels describe what the receipt established.
# A projection can only select a claim at or below this ceiling.  In
# particular, operational-stack and factor-causal claims are not model-only
# claims, and no receipt can acquire transfer/outcome proof from an audit.
_CLAIM_RANK = {
    "artifact": 0,
    "workflow": 1,
    "operational_stack": 2,
    "factor_causal": 2,
    "model_only": 2,
    "transfer": 4,
    "outcome": 5,
}
_EVIDENCE_CEILING = {
    "structurally_valid": 0,
    "runtime_conformant": 1,
    "controlled_effect_observed": 2,
    "effect_reproduced": 2,
    "downstream_outcome_observed": 5,
    "transferred": 4,
    "externally_decision_changing": 4,
    "paid_repeated_use": 5,
    "independently_outcome_verified": 5,
}


class ResultSurfaceError(SandboxError):
    """Raised when a publication profile or its source graph is unsafe."""


def _fail(message: str) -> NoReturn:
    raise ResultSurfaceError(message)


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate object member: {key}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise ValueError(f"non-finite JSON number: {value}")


def _strict_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"non-finite JSON number: {value}")
    return parsed


def _load_json_object(path: Path) -> dict[str, Any]:
    _regular_file(path, "JSON source")
    if path.stat().st_size > MAX_JSON_BYTES:
        _fail(f"JSON source exceeds {MAX_JSON_BYTES} bytes: {path}")
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_strict_object,
            parse_constant=_reject_nonfinite,
            parse_float=_strict_float,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        _fail(f"JSON source is unreadable: {path}: {exc}")
    if not isinstance(value, dict):
        _fail(f"JSON source must contain an object: {path}")
    return value


def _regular_file(path: Path, label: str) -> None:
    """Require a regular non-symlink file, including every parent component."""

    candidate = Path(path)
    absolute = candidate.absolute()
    if _contains_symlink(absolute):
        _fail(f"{label} must not use symlinks: {path}")
    try:
        info = absolute.lstat()
    except OSError as exc:
        _fail(f"{label} does not exist: {path}: {exc}")
    if not stat.S_ISREG(info.st_mode):
        _fail(f"{label} must be a regular file: {path}")


def _regular_directory(path: Path, label: str) -> None:
    absolute = Path(path).absolute()
    if _contains_symlink(absolute):
        _fail(f"{label} must not use symlinks: {path}")
    try:
        info = absolute.lstat()
    except OSError as exc:
        _fail(f"{label} does not exist: {path}: {exc}")
    if not stat.S_ISDIR(info.st_mode):
        _fail(f"{label} must be a directory: {path}")


def _contains_symlink(path: Path) -> bool:
    candidate = Path(path).absolute()
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


def _repository_root(profile_path: Path, explicit: Path | None) -> Path:
    if explicit is not None:
        _regular_directory(explicit, "repository root")
        root = Path(explicit).resolve()
    else:
        start = Path(profile_path).absolute()
        for candidate in (start.parent, *start.parents):
            if (candidate / "pyproject.toml").is_file() and not _contains_symlink(
                candidate / "pyproject.toml"
            ):
                root = candidate.resolve()
                break
        else:
            _fail("could not locate repository root with pyproject.toml")
    profile_resolved = Path(profile_path).resolve()
    if not profile_resolved.is_relative_to(root):
        _fail("publication profile must be inside the repository root")
    return root


def _require_keys(
    value: Mapping[str, Any], required: set[str], optional: set[str], location: str
) -> None:
    unknown = set(value) - required - optional
    missing = required - set(value)
    if unknown:
        _fail(f"{location} contains unknown key(s): {', '.join(sorted(unknown))}")
    if missing:
        _fail(f"{location} is missing required key(s): {', '.join(sorted(missing))}")


def _nonempty_string(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(f"{location} must be a non-empty string")
    return value


def _sha(value: Any, location: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        _fail(f"{location} must be 64 lowercase hexadecimal characters")
    return value


def _validate_date(value: Any, location: str) -> str:
    date = _nonempty_string(value, location)
    if _DATE.fullmatch(date) is None:
        _fail(f"{location} must use YYYY-MM-DD")
    try:
        _datetime.date.fromisoformat(date)
    except ValueError:
        _fail(f"{location} is not a calendar date: {date}")
    return date


def _local_reference(
    owner: Path,
    reference: Mapping[str, Any],
    repository_root: Path,
    location: str,
    *,
    dereference: bool = True,
    strict: bool = True,
) -> tuple[Path | None, str]:
    if not isinstance(reference, Mapping):
        _fail(f"{location} must be an object")
    if strict:
        _require_keys(reference, {"uri", "sha256"}, set(), location)
    elif "uri" not in reference or "sha256" not in reference:
        _fail(f"{location} requires uri and sha256")
    uri = _nonempty_string(reference.get("uri"), f"{location}.uri")
    digest = _sha(reference.get("sha256"), f"{location}.sha256")
    parsed = urlparse(uri)
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment or uri.startswith("/"):
        _fail(f"{location}.uri must be a repository-relative path")
    if "\\" in uri or "\x00" in uri:
        _fail(f"{location}.uri contains an unsafe path character")
    if not parsed.path or parsed.path == ".":
        _fail(f"{location}.uri must identify a file")
    candidate = owner.parent / parsed.path
    if _contains_symlink(candidate):
        _fail(f"{location}.uri must not use symlinks")
    target = candidate.resolve()
    if not target.is_relative_to(repository_root):
        _fail(f"{location}.uri escapes repository root")
    if not dereference:
        return None, digest
    _regular_file(target, f"{location} target")
    actual = sha256_path(target)
    if actual != digest:
        _fail(f"{location}.sha256 does not match {target}")
    return target, digest


def _relative_path(path: Path, repository_root: Path) -> str:
    try:
        return path.resolve().relative_to(repository_root).as_posix()
    except ValueError as exc:
        _fail(f"source path is outside repository root: {path}")
        raise AssertionError from exc


def _load_profile(profile_path: Path) -> dict[str, Any]:
    return _load_json_object(profile_path)


def validate_public_profile(profile: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a decoded publication profile and return it unchanged.

    This function performs schema-like checks without touching the filesystem;
    source hash/path checks are performed by :func:`build_result_surface`.
    """

    if not isinstance(profile, Mapping):
        _fail("publication profile must be an object")
    _require_keys(
        profile, {"schema_version", "as_of", "projection_policy", "studies"}, set(), "profile"
    )
    if profile.get("schema_version") != PUBLIC_RESULTS_SCHEMA_VERSION:
        _fail(f"profile.schema_version must equal {PUBLIC_RESULTS_SCHEMA_VERSION}")
    _validate_date(profile.get("as_of"), "profile.as_of")
    if profile.get("projection_policy") != PUBLICATION_PROJECTION_POLICY:
        _fail(f"profile.projection_policy must equal {PUBLICATION_PROJECTION_POLICY}")
    studies = profile.get("studies")
    if not isinstance(studies, list) or not studies:
        _fail("profile.studies must be a non-empty ordered array")
    seen_cards: set[str] = set()
    for index, study in enumerate(studies):
        location = f"profile.studies.{index}"
        if not isinstance(study, Mapping):
            _fail(f"{location} must be an object")
        _require_keys(
            study,
            {
                "card_id",
                "title",
                "receipt_ref",
                "claim_ids",
                "verification",
                "materials",
                "history",
                "publication",
            },
            {"report_ref"},
            location,
        )
        card_id = _nonempty_string(study.get("card_id"), f"{location}.card_id")
        if _CARD_ID.fullmatch(card_id) is None:
            _fail(f"{location}.card_id must be a lowercase hyphenated slug")
        if card_id in seen_cards:
            _fail(f"duplicate card_id: {card_id}")
        seen_cards.add(card_id)
        _nonempty_string(study.get("title"), f"{location}.title")
        _validate_profile_ref_shape(study.get("receipt_ref"), f"{location}.receipt_ref")
        if "report_ref" in study:
            _validate_profile_ref_shape(study.get("report_ref"), f"{location}.report_ref")
        _validate_claim_ids(study.get("claim_ids"), f"{location}.claim_ids")
        _validate_verification(study.get("verification"), f"{location}.verification")
        _validate_materials(study.get("materials"), f"{location}.materials")
        _validate_history(study.get("history"), f"{location}.history")
        publication = study.get("publication")
        if publication not in {"published", "unpublished", "withdrawn"}:
            _fail(f"{location}.publication must be published, unpublished, or withdrawn")
    return dict(profile)


def _validate_profile_ref_shape(value: Any, location: str) -> None:
    if not isinstance(value, Mapping):
        _fail(f"{location} must be an object")
    _require_keys(value, {"uri", "sha256"}, set(), location)
    _nonempty_string(value.get("uri"), f"{location}.uri")
    _sha(value.get("sha256"), f"{location}.sha256")


def _validate_claim_ids(value: Any, location: str) -> None:
    if not isinstance(value, list) or not value:
        _fail(f"{location} must be a non-empty array")
    seen: set[str] = set()
    for index, claim_id in enumerate(value):
        claim = _nonempty_string(claim_id, f"{location}.{index}")
        if claim in seen:
            _fail(f"{location} must contain unique claim IDs")
        seen.add(claim)


def _validate_verification(value: Any, location: str) -> None:
    if not isinstance(value, Mapping):
        _fail(f"{location} must be an object")
    _require_keys(
        value, {"kind", "command", "boundary"}, {"freeze_ref", "result_root", "adapter"}, location
    )
    kind = value.get("kind")
    if kind not in _SCHEMES:
        _fail(f"{location}.kind must be one of {sorted(_SCHEMES)}")
    command = value.get("command")
    if not isinstance(command, list) or not command:
        _fail(f"{location}.command must be a non-empty array")
    for index, item in enumerate(command):
        _nonempty_string(item, f"{location}.command.{index}")
    _nonempty_string(value.get("boundary"), f"{location}.boundary")
    optional_present = {key for key in ("freeze_ref", "result_root", "adapter") if key in value}
    if kind == "frozen_public_bundle":
        required = {"freeze_ref", "result_root", "adapter"}
        if required - optional_present:
            _fail(
                f"{location} frozen_public_bundle requires {', '.join(sorted(required - optional_present))}"
            )
        _validate_profile_ref_shape(value.get("freeze_ref"), f"{location}.freeze_ref")
        root = _nonempty_string(value.get("result_root"), f"{location}.result_root")
        _validate_relative_uri(root, f"{location}.result_root")
        adapter = value.get("adapter")
        if adapter not in _ADAPTERS:
            _fail(f"{location}.adapter must be one of {sorted(_ADAPTERS)}")
    elif optional_present:
        _fail(f"{location} evidence_graph must not include frozen-bundle fields")


def _validate_relative_uri(value: str, location: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment or value.startswith("/"):
        _fail(f"{location} must be a repository-relative path")
    if "\\" in value or "\x00" in value or not parsed.path or parsed.path == ".":
        _fail(f"{location} is not a safe relative path")
    if any(part in {"", ".", ".."} for part in Path(parsed.path).parts):
        _fail(f"{location} must use a canonical relative path")


def _validate_materials(value: Any, location: str) -> None:
    if not isinstance(value, list):
        _fail(f"{location} must be an array")
    for index, material in enumerate(value):
        item_location = f"{location}.{index}"
        if not isinstance(material, Mapping):
            _fail(f"{item_location} must be an object")
        _require_keys(
            material,
            {"label", "availability"},
            {"ref", "reason", "reproduction_impact"},
            item_location,
        )
        _nonempty_string(material.get("label"), f"{item_location}.label")
        availability = material.get("availability")
        if availability not in _MATERIAL_AVAILABILITY:
            _fail(f"{item_location}.availability must be one of {sorted(_MATERIAL_AVAILABILITY)}")
        if availability == "public":
            if "ref" not in material:
                _fail(f"{item_location} public material requires ref")
            if "reason" in material or "reproduction_impact" in material:
                _fail(
                    f"{item_location} public material must not include reason or reproduction_impact"
                )
            _validate_profile_ref_shape(material.get("ref"), f"{item_location}.ref")
        else:
            if "ref" in material:
                _fail(f"{item_location} non-public material must not include ref")
            _nonempty_string(material.get("reason"), f"{item_location}.reason")
            _nonempty_string(
                material.get("reproduction_impact"), f"{item_location}.reproduction_impact"
            )


def _validate_history(value: Any, location: str) -> None:
    if not isinstance(value, Mapping):
        _fail(f"{location} must be an object")
    _require_keys(value, {"admission", "action", "outcome_follow_up", "freshness"}, set(), location)
    for key in ("admission", "action", "outcome_follow_up"):
        if value.get(key) != _HISTORY_UNKNOWN:
            _fail(f"{location}.{key} must equal {_HISTORY_UNKNOWN}")
    if value.get("freshness") != _HISTORY_FRESHNESS_UNKNOWN:
        _fail(f"{location}.freshness must equal {_HISTORY_FRESHNESS_UNKNOWN}")


def load_public_profile(profile_path: Path) -> dict[str, Any]:
    """Load and validate a publication profile without resolving its sources."""

    profile_path = Path(profile_path).absolute()
    profile = _load_profile(profile_path)
    return validate_public_profile(profile)


def _validate_receipt_schema(receipt: dict[str, Any], path: Path) -> None:
    validator = Draft202012Validator(
        # Importing the existing helper keeps Contract v0 schema ownership in
        # validation.py while this sidecar remains outside SCHEMA_FILES.
        _receipt_schema(),
        format_checker=FormatChecker(),
    )
    errors = sorted(validator.iter_errors(receipt), key=lambda item: list(item.absolute_path))
    if errors:
        _fail(f"receipt schema validation failed at {path}: {errors[0].message}")


def _receipt_schema() -> dict[str, Any]:
    from importlib import resources

    resource = resources.files("ael").joinpath("schemas", SCHEMA_FILES["evidence_receipt"])
    return json.loads(resource.read_text(encoding="utf-8"))


def _receipt_graph(
    receipt_path: Path,
    receipt: dict[str, Any],
    repository_root: Path,
) -> tuple[list[Path], dict[str, str]]:
    """Resolve every public Contract v0 document owned by a receipt."""

    _validate_receipt_schema(receipt, receipt_path)
    refs: list[tuple[str, Mapping[str, Any]]] = [
        ("concept_ref", receipt["concept_ref"]),
        ("study_ref", receipt["study_ref"]),
        ("measurement_set_ref", receipt["measurement_set_ref"]),
    ]
    refs.extend(
        (f"run_record_refs.{index}", reference)
        for index, reference in enumerate(receipt["run_record_refs"])
    )
    paths = [receipt_path]
    source_hashes = {_relative_path(receipt_path, repository_root): sha256_path(receipt_path)}
    for location, reference in refs:
        if not isinstance(reference, Mapping):
            _fail(f"receipt.{location} must be an object")
        visibility = reference.get("visibility")
        if visibility not in _VISIBILITIES:
            _fail(f"receipt.{location}.visibility is invalid")
        if visibility != "public":
            # A public projection must not dereference private/hidden graph
            # material.  The receipt schema still records its opaque identity.
            continue
        target, digest = _local_reference(
            receipt_path, reference, repository_root, f"receipt.{location}", strict=False
        )
        assert target is not None
        paths.append(target)
        source_hashes[_relative_path(target, repository_root)] = digest
    # Public cards must be backed by one complete public graph.  If an opaque
    # run/material reference exists, do not silently turn it into a partial
    # validation: make the boundary explicit in the profile instead.
    if any(
        isinstance(reference, Mapping) and reference.get("visibility") != "public"
        for _, reference in refs
    ):
        _fail(
            "receipt graph contains non-public references; expose them as profile materials instead"
        )
    documents, issues = validate(paths)
    if issues:
        _fail(f"Contract v0 receipt graph validation failed: {issues[0]}")
    expected_types = {
        "evidence_receipt",
        "concept",
        "study_manifest",
        "measurement_set",
        "run_record",
    }
    if {document.object_type for document in documents} != expected_types:
        _fail("receipt graph does not contain all five Contract v0 document types")
    return paths, source_hashes


def _selected_claims(
    receipt: Mapping[str, Any], claim_ids: list[str], card_id: str
) -> list[dict[str, Any]]:
    claims = receipt.get("evaluated_claims")
    if not isinstance(claims, list):
        _fail(f"receipt for {card_id} has no evaluated claims")
    by_id: dict[str, dict[str, Any]] = {}
    for claim in claims:
        if not isinstance(claim, Mapping):
            _fail(f"receipt for {card_id} contains a non-object claim")
        claim_id = claim.get("claim_id")
        if not isinstance(claim_id, str) or not claim_id:
            _fail(f"receipt for {card_id} contains a claim without an ID")
        if claim_id in by_id:
            _fail(f"receipt for {card_id} contains duplicate claim ID {claim_id}")
        by_id[claim_id] = dict(claim)
    selected: list[dict[str, Any]] = []
    ceiling = _EVIDENCE_CEILING.get(str(receipt.get("evidence_level")))
    if ceiling is None:
        _fail(f"receipt for {card_id} has unknown evidence level")
    for claim_id in claim_ids:
        claim = by_id.get(claim_id)
        if claim is None:
            _fail(f"selected claim {claim_id} is absent from receipt for {card_id}")
        rank = _CLAIM_RANK.get(str(claim.get("claim_level")))
        if rank is None:
            _fail(f"claim {claim_id} has unknown claim level")
        if rank > ceiling:
            _fail(
                f"claim {claim_id} exceeds evidence ceiling for {card_id}: "
                f"{claim.get('claim_level')} > {receipt.get('evidence_level')}"
            )
        selected.append(claim)
    return selected


def _source_ref(
    owner: Path,
    ref: Mapping[str, Any],
    repository_root: Path,
    location: str,
    source_hashes: dict[str, str],
) -> dict[str, str]:
    target, digest = _local_reference(owner, ref, repository_root, location)
    assert target is not None
    relative = _relative_path(target, repository_root)
    source_hashes[relative] = digest
    return {"uri": relative, "sha256": digest}


def _material_projection(
    materials: list[Mapping[str, Any]],
    owner: Path,
    repository_root: Path,
    source_hashes: dict[str, str],
) -> list[dict[str, Any]]:
    projected: list[dict[str, Any]] = []
    for index, material in enumerate(materials):
        availability = str(material["availability"])
        item: dict[str, Any] = {"label": material["label"], "availability": availability}
        if availability == "public":
            item["ref"] = _source_ref(
                owner,
                material["ref"],
                repository_root,
                f"materials.{index}.ref",
                source_hashes,
            )
        else:
            item["reason"] = material["reason"]
            item["reproduction_impact"] = material["reproduction_impact"]
        projected.append(item)
    return projected


def _study_and_measurement_projection(
    receipt_path: Path,
    receipt: Mapping[str, Any],
    repository_root: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    study_path, _ = _local_reference(
        receipt_path,
        receipt["study_ref"],
        repository_root,
        "receipt.study_ref",
        strict=False,
    )
    measurement_path, _ = _local_reference(
        receipt_path,
        receipt["measurement_set_ref"],
        repository_root,
        "receipt.measurement_set_ref",
        strict=False,
    )
    assert study_path is not None and measurement_path is not None
    study = _load_json_object(study_path)
    measurement_set = _load_json_object(measurement_path)
    decision_owners = [
        role["actor_id"]
        for role in study.get("roles", [])
        if isinstance(role, Mapping) and role.get("role") == "decision_owner"
    ]
    study_projection = {
        "study_id": study["study_id"],
        "revision": study["revision"],
        "status": study["status"],
        "decision_question": study["decision_question"],
        "comparison_mode": study["comparison_mode"],
        "primary_estimand": study["primary_estimand"],
        "conditions": [
            {
                "condition_id": condition["condition_id"],
                "label": condition["label"],
                "role": condition["role"],
            }
            for condition in study["conditions"]
        ],
        "task_packs": [
            {
                "task_pack_id": task_pack["task_pack_id"],
                "role": task_pack["role"],
                "strata": task_pack["strata"],
            }
            for task_pack in study["task_packs"]
        ],
        "decision_owners": decision_owners,
    }
    return study_projection, _measurement_projection(measurement_set)


def _measurement_projection(measurement_set: Mapping[str, Any]) -> dict[str, Any]:
    by_kind: dict[str, int] = {}
    grouped: dict[tuple[str, str, str], list[Mapping[str, Any]]] = {}
    for measurement in measurement_set.get("measurements", []):
        kind = str(measurement["kind"])
        by_kind[kind] = by_kind.get(kind, 0) + 1
        metric = str(measurement["metric"])
        condition = str(measurement.get("condition_id", "all"))
        unit = str(measurement["unit"])
        grouped.setdefault((metric, condition, unit), []).append(measurement)

    summaries: list[dict[str, Any]] = []
    for (metric, condition, unit), measurements in sorted(grouped.items()):
        lower_metric = metric.lower()
        category: str | None = None
        if any(token in lower_metric for token in ("token", "cost", "wall_time", "latency")):
            category = "cost_or_latency"
        elif "critical" in lower_metric:
            category = "critical_failure"
        elif "activat" in lower_metric or "skill_read" in lower_metric:
            category = "activation"
        if category is None:
            continue
        aggregate_measurements = [
            measurement for measurement in measurements if measurement["kind"] == "aggregate"
        ]
        selected_measurements = aggregate_measurements or [
            measurement for measurement in measurements if measurement["kind"] != "aggregate"
        ]
        values = [measurement["value"] for measurement in selected_measurements]
        numeric_values = [
            float(value)
            for value in values
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        ]
        boolean_values = [value for value in values if isinstance(value, bool)]
        summary: dict[str, Any] = {
            "category": category,
            "metric": metric,
            "condition_id": condition,
            "unit": unit,
            "observations": len(values),
            "aggregation_basis": (
                "aggregate_measurements" if aggregate_measurements else "non_aggregate_measurements"
            ),
        }
        if len(numeric_values) == len(values):
            summary["total"] = sum(numeric_values)
        elif len(boolean_values) == len(values):
            summary["true"] = sum(boolean_values)
            summary["false"] = len(boolean_values) - sum(boolean_values)
        else:
            summary["aggregation"] = "not_applicable_mixed_values"
        summaries.append(summary)
    return {
        "measurement_set_id": measurement_set["measurement_set_id"],
        "count": len(measurement_set.get("measurements", [])),
        "by_kind": dict(sorted(by_kind.items())),
        "selected_summaries": summaries,
    }


def _run_projection(
    receipt_path: Path, receipt: Mapping[str, Any], repository_root: Path
) -> dict[str, Any]:
    by_status: dict[str, int] = {}
    by_condition: dict[str, int] = {}
    for index, reference in enumerate(receipt["run_record_refs"]):
        run_path, _ = _local_reference(
            receipt_path,
            reference,
            repository_root,
            f"receipt.run_record_refs.{index}",
            strict=False,
        )
        assert run_path is not None
        run = _load_json_object(run_path)
        status = str(run["status"])
        condition = str(run["condition_id"])
        by_status[status] = by_status.get(status, 0) + 1
        by_condition[condition] = by_condition.get(condition, 0) + 1
    return {
        "count": len(receipt["run_record_refs"]),
        "by_status": dict(sorted(by_status.items())),
        "by_condition": dict(sorted(by_condition.items())),
    }


def _audit_projection(
    verification: Mapping[str, Any],
    profile_path: Path,
    repository_root: Path,
    require_git_proof: bool,
) -> dict[str, Any] | None:
    if verification["kind"] != "frozen_public_bundle":
        return None
    freeze_path, _ = _local_reference(
        profile_path,
        verification["freeze_ref"],
        repository_root,
        "verification.freeze_ref",
    )
    assert freeze_path is not None
    result_root_string = str(verification["result_root"])
    result_candidate = repository_root / result_root_string
    if _contains_symlink(result_candidate):
        _fail("verification.result_root must not use symlinks")
    result_root = result_candidate.resolve()
    if not result_root.is_relative_to(repository_root):
        _fail("verification.result_root escapes repository root")
    _regular_directory(result_root, "verification.result_root")
    try:
        return audit_study_bundle(
            freeze_path,
            result_root,
            git_root=repository_root,
            require_git_proof=require_git_proof,
            decision_adapter=verification["adapter"],
        )
    except SandboxError as exc:
        _fail(f"frozen public bundle audit failed: {exc}")


def _build_card(
    profile_path: Path,
    profile: Mapping[str, Any],
    entry: Mapping[str, Any],
    repository_root: Path,
    require_git_proof: bool,
) -> tuple[dict[str, Any], dict[str, str]]:
    profile_reference_owner = repository_root / ".ael-public-results-profile"
    receipt_path, receipt_digest = _local_reference(
        profile_reference_owner,
        entry["receipt_ref"],
        repository_root,
        f"{entry['card_id']}.receipt_ref",
    )
    assert receipt_path is not None
    receipt = _load_json_object(receipt_path)
    graph_paths, source_hashes = _receipt_graph(receipt_path, receipt, repository_root)
    source_hashes[_relative_path(profile_path, repository_root)] = sha256_path(profile_path)
    report_projection: dict[str, str] | None = None
    if "report_ref" in entry:
        report_path, report_digest = _local_reference(
            profile_reference_owner,
            entry["report_ref"],
            repository_root,
            f"{entry['card_id']}.report_ref",
        )
        assert report_path is not None
        report_projection = {
            "uri": _relative_path(report_path, repository_root),
            "sha256": report_digest,
        }
        source_hashes[report_projection["uri"]] = report_digest
    selected_claims = _selected_claims(receipt, list(entry["claim_ids"]), str(entry["card_id"]))
    study_projection, measurement_projection = _study_and_measurement_projection(
        receipt_path, receipt, repository_root
    )
    run_projection = _run_projection(receipt_path, receipt, repository_root)
    audit = _audit_projection(
        entry["verification"], profile_reference_owner, repository_root, require_git_proof
    )
    verification_projection: dict[str, Any] = {
        "kind": entry["verification"]["kind"],
        "command": list(entry["verification"]["command"]),
        "boundary": entry["verification"]["boundary"],
    }
    if audit is not None:
        verification_projection["audit"] = audit
    materials = _material_projection(
        entry["materials"], profile_reference_owner, repository_root, source_hashes
    )
    # ``graph_paths`` is intentionally consumed here: source_hashes includes
    # every graph byte, and this assertion prevents accidental partial graph
    # construction if the validator's implementation changes.
    if len(graph_paths) != len(source_hashes) - 1 - (1 if report_projection else 0):
        # The count can differ when two references intentionally point at one
        # immutable file; compare by path rather than failing for aliases.
        source_hashes.update(
            {_relative_path(path, repository_root): sha256_path(path) for path in graph_paths}
        )
    receipt_ref_projection = {
        "uri": _relative_path(receipt_path, repository_root),
        "sha256": receipt_digest,
    }
    card: dict[str, Any] = {
        "card_id": entry["card_id"],
        "title": entry["title"],
        "publication": entry["publication"],
        "receipt": receipt_ref_projection,
        "decision": receipt["decision"],
        "evidence_level": receipt["evidence_level"],
        "reproducibility": receipt["reproducibility"],
        "independence": receipt["independence"],
        "claims": selected_claims,
        "unsupported_inferences": receipt["unsupported_inferences"],
        "limitations": receipt["limitations"],
        "invalidation_triggers": receipt["invalidation_triggers"],
        "state": receipt["state"],
        "history": entry["history"],
        "materials": materials,
        "verification": verification_projection,
        "source_hashes": dict(sorted(source_hashes.items())),
        "receipt_id": receipt["receipt_id"],
        "study": study_projection,
        "runs": run_projection,
        "measurements": measurement_projection,
        "generator": {"name": GENERATOR_NAME, "version": GENERATOR_VERSION},
    }
    if report_projection is not None:
        card["report"] = report_projection
    # Keep an explicit selected-ID field so a consumer can distinguish the
    # profile's selection from the full receipt claim set.
    card["claim_ids"] = list(entry["claim_ids"])
    return card, source_hashes


def _json_bytes(value: Any) -> str:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            separators=(",", ": "),
            allow_nan=False,
        )
        + "\n"
    )


def _markdown_link(label: str, path: str, from_dir: str) -> str:
    target = Path(os.path.relpath(path, from_dir)).as_posix()
    return f"[{label}]({target})"


def _render_card(card: Mapping[str, Any]) -> str:
    card_directory = "docs/results"
    lines = [
        f"# {card['title']}",
        "",
        f"- Card ID: `{card['card_id']}`",
        f"- Current publication: **{card['publication']}**",
        f"- Receipt: {_markdown_link('machine-readable evidence', card['receipt']['uri'], card_directory)}",
        f"- Receipt SHA-256: `{card['receipt']['sha256']}`",
        f"- Evidence level: `{card['evidence_level']}`",
        f"- Reproducibility: `{card['reproducibility']}`",
        f"- Independence: `{card['independence']['label']}`",
        "",
        "## Decision",
        "",
        f"**{card['decision']['disposition']}** — {card['decision']['summary']}",
        "",
        "Scope:",
        *[f"- {item}" for item in card["decision"]["scope"]],
        "",
        f"Reversal trigger: {card['decision']['reversal_trigger']}",
        "",
    ]
    if "report" in card:
        lines.insert(
            6,
            f"- Report: {_markdown_link('narrative result', card['report']['uri'], card_directory)}",
        )
    study = card["study"]
    lines.extend(
        [
            "## What was tested",
            "",
            study["decision_question"],
            "",
            f"Comparison mode: `{study['comparison_mode']}`. Study state: `{study['status']}`.",
            "",
            f"Primary estimand: **{study['primary_estimand']['name']}** — {study['primary_estimand']['description']}",
            "",
            "Conditions:",
            *[
                f"- `{condition['condition_id']}` — {condition['label']} (`{condition['role']}`)"
                for condition in study["conditions"]
            ],
            "",
            "Task strata:",
            *[
                f"- `{task_pack['task_pack_id']}` (`{task_pack['role']}`): "
                + ", ".join(task_pack["strata"])
                for task_pack in study["task_packs"]
            ],
            "",
            "Decision owner(s): "
            + (", ".join(f"`{owner}`" for owner in study["decision_owners"]) or "not declared"),
            "",
            "## Runs and measurements",
            "",
            f"Runs: `{card['runs']['count']}`; by status: "
            + ", ".join(
                f"`{status}={count}`" for status, count in card["runs"]["by_status"].items()
            )
            + ".",
            "",
            f"Measurements: `{card['measurements']['count']}`; by kind: "
            + ", ".join(
                f"`{kind}={count}`" for kind, count in card["measurements"]["by_kind"].items()
            )
            + ".",
            "",
        ]
    )
    if card["measurements"]["selected_summaries"]:
        lines.extend(["Selected descriptive totals (not stable effects):", ""])
        for summary in card["measurements"]["selected_summaries"]:
            if "total" in summary:
                value = f"total `{summary['total']:g} {summary['unit']}`"
            elif "true" in summary:
                value = f"true `{summary['true']}/{summary['observations']}`"
            else:
                value = str(summary["aggregation"])
            lines.append(
                f"- `{summary['metric']}` / `{summary['condition_id']}`: {value} "
                f"(`{summary['category']}`)"
            )
        lines.append("")
    lines.extend(["## Claims", ""])
    for claim in card["claims"]:
        lines.extend(
            [
                f"### {claim['claim_id']} — {claim['status']}",
                "",
                claim["statement"],
                "",
                f"Claim level: `{claim['claim_level']}`",
                "",
                f"Falsifier: {claim['falsifier']}",
                "",
            ]
        )
    lines.extend(["## Verification boundary", "", f"Kind: `{card['verification']['kind']}`", ""])
    lines.append(card["verification"]["boundary"])
    lines.extend(["", "Command (presentation only; not executed by this generator):", "", "```sh"])
    lines.extend(str(item) for item in card["verification"]["command"])
    lines.extend(["```", ""])
    if "audit" in card["verification"]:
        audit = card["verification"]["audit"]
        lines.extend(
            [
                f"Audit status: `{audit['status']}`.",
                f"Contract documents checked: `{audit['evidence']['contract_documents']}`; run records: `{audit['evidence']['run_records']}`.",
                "",
            ]
        )
    lines.extend(["## Independence", "", card["independence"]["disclosure"], ""])
    lines.extend(["## Historical status", ""])
    for key in ("admission", "action", "outcome_follow_up", "freshness"):
        lines.append(f"- {key}: `{card['history'][key]}`")
    lines.extend(["", "## Materials", ""])
    for material in card["materials"]:
        lines.append(f"- **{material['label']}** — `{material['availability']}`")
        if material["availability"] == "public":
            lines.append(
                f"  - Ref: `{material['ref']['uri']}` (SHA-256 `{material['ref']['sha256']}`)"
            )
        else:
            lines.append(f"  - Reason: {material['reason']}")
            lines.append(f"  - Reproduction impact: {material['reproduction_impact']}")
    lines.extend(["", "## Unsupported inferences", ""])
    lines.extend(f"- {item}" for item in card["unsupported_inferences"])
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in card["limitations"])
    lines.extend(["", "## Invalidation triggers", ""])
    lines.extend(f"- {item}" for item in card["invalidation_triggers"])
    lines.extend(["", "## Source hashes", ""])
    lines.extend(f"- `{path}` — `{digest}`" for path, digest in card["source_hashes"].items())
    lines.extend(
        [
            "",
            f"Generated by `{GENERATOR_NAME}` `{GENERATOR_VERSION}` under `{PUBLICATION_PROJECTION_POLICY}`.",
            "",
        ]
    )
    return "\n".join(lines)


def _render_results(results: list[Mapping[str, Any]], as_of: str) -> str:
    lines = [
        "# Results Index",
        "",
        f"Generated as of `{as_of}` from the explicit publication profile.",
        "",
        "This page is a deterministic projection. Decisions, evidence levels, claims, reproducibility, independence, and state are copied from hash-bound Contract v0 receipts; profile publication status is current metadata and is not proof.",
        "",
        "| Study | Publication | Evidence | Reproducibility | Decision |",
        "| --- | --- | --- | --- | --- |",
    ]
    for card in results:
        decision = card["decision"]["disposition"]
        lines.append(
            f"| [{card['title']}](docs/results/{card['card_id']}.md) | {card['publication']} | "
            f"`{card['evidence_level']}` | `{card['reproducibility']}` | `{decision}` |"
        )
    lines.extend(
        [
            "",
            f"Generated by `{GENERATOR_NAME}` `{GENERATOR_VERSION}` under `{PUBLICATION_PROJECTION_POLICY}`.",
            "",
        ]
    )
    return "\n".join(lines)


def build_result_surface(
    profile_path: Path,
    repository_root: Path | None = None,
    require_git_proof: bool = False,
) -> dict[str, str]:
    """Build deterministic output bytes without writing any files."""

    profile_path = Path(profile_path).absolute()
    _regular_file(profile_path, "publication profile")
    root = _repository_root(profile_path, repository_root)
    profile = load_public_profile(profile_path)
    cards: list[dict[str, Any]] = []
    for entry in profile["studies"]:
        card, _ = _build_card(profile_path, profile, entry, root, require_git_proof)
        cards.append(card)
    # Card IDs are a stable public key; output order is canonical regardless of
    # incidental profile editing order.  The profile remains an ordered source.
    cards.sort(key=lambda card: str(card["card_id"]))
    profile_hash = sha256_path(profile_path)
    index = {
        "schema_version": PUBLIC_RESULTS_SCHEMA_VERSION,
        "as_of": profile["as_of"],
        "projection_policy": profile["projection_policy"],
        "generator": {"name": GENERATOR_NAME, "version": GENERATOR_VERSION},
        "source_hashes": {_relative_path(profile_path, root): profile_hash},
        "studies": cards,
    }
    outputs: dict[str, str] = {
        "RESULTS.md": _render_results(cards, profile["as_of"]),
        "docs/results/index.json": _json_bytes(index),
    }
    outputs.update({f"docs/results/{card['card_id']}.md": _render_card(card) for card in cards})
    return dict(sorted(outputs.items()))


def materialize_result_surface(
    profile_path: Path,
    repository_root: Path | None = None,
    check: bool = False,
    require_git_proof: bool = False,
) -> dict[str, Any]:
    """Safely materialize or check generated result-surface files.

    ``check=True`` never writes.  Both modes return output hashes so a caller
    can record a deterministic receipt without relying on wall-clock metadata.
    """

    profile_path = Path(profile_path).absolute()
    root = _repository_root(profile_path, repository_root)
    outputs = build_result_surface(profile_path, root, require_git_proof=require_git_proof)
    result_directory = root / "docs" / "results"
    if result_directory.exists() or result_directory.is_symlink():
        _regular_directory(result_directory, "generated result directory")
        expected_result_paths = {
            (root / relative).resolve()
            for relative in outputs
            if relative.startswith("docs/results/")
        }
        for existing in result_directory.iterdir():
            if existing.is_symlink() or not existing.is_file():
                _fail(f"generated result directory contains an unmanaged entry: {existing}")
            if existing.resolve() not in expected_result_paths:
                _fail(f"generated result directory contains a stale output: {existing}")
    output_hashes = {
        path: hashlib.sha256(content.encode("utf-8")).hexdigest()
        for path, content in outputs.items()
    }
    if check:
        for relative, content in outputs.items():
            target = root / relative
            _regular_file(target, f"generated output {relative}")
            if target.read_text(encoding="utf-8") != content:
                _fail(f"generated output differs: {relative}")
        return {
            "status": "checked",
            "check": True,
            "materialized": False,
            "outputs": output_hashes,
            "generator": {"name": GENERATOR_NAME, "version": GENERATOR_VERSION},
        }
    for relative, content in outputs.items():
        target = root / relative
        parent = target.parent
        if _contains_symlink(parent):
            _fail(f"generated output directory must not use symlinks: {parent}")
        parent.mkdir(parents=True, exist_ok=True)
        if target.exists() or target.is_symlink():
            _regular_file(target, f"generated output {relative}")
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
        try:
            temporary.chmod(0o644)
            os.replace(temporary, target)
        finally:
            if temporary.exists():
                temporary.unlink()
    return {
        "status": "materialized",
        "check": False,
        "materialized": True,
        "outputs": output_hashes,
        "generator": {"name": GENERATOR_NAME, "version": GENERATOR_VERSION},
    }


# Small compatibility aliases for thin callers that prefer explicit verbs.
load_profile = load_public_profile
validate_profile = validate_public_profile


__all__ = [
    "GENERATOR_NAME",
    "GENERATOR_VERSION",
    "PUBLICATION_PROJECTION_POLICY",
    "PUBLIC_RESULTS_SCHEMA_VERSION",
    "ResultSurfaceError",
    "build_result_surface",
    "load_profile",
    "load_public_profile",
    "materialize_result_surface",
    "validate_profile",
    "validate_public_profile",
]
