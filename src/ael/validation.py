from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from jsonschema import Draft202012Validator, FormatChecker

SCHEMA_FILES = {
    "concept": "concept.schema.json",
    "study_manifest": "study-manifest.schema.json",
    "run_record": "run-record.schema.json",
    "measurement_set": "measurement-set.schema.json",
    "evidence_receipt": "evidence-receipt.schema.json",
}

IDENTITY_FIELDS = {
    "concept": "concept_id",
    "study_manifest": "study_id",
    "run_record": "run_id",
    "measurement_set": "measurement_set_id",
    "evidence_receipt": "receipt_id",
}

EVALUATIVE_MEASUREMENT_KINDS = {"outcome", "subjective"}
MAX_JSON_DOCUMENTS = 10_000
MAX_JSON_BYTES = 8 * 1024 * 1024


@dataclass(frozen=True)
class Document:
    path: Path
    root: Path
    data: dict[str, Any]

    @property
    def object_type(self) -> str:
        return str(self.data.get("object_type", ""))

    @property
    def identity(self) -> str:
        field = IDENTITY_FIELDS.get(self.object_type)
        return str(self.data.get(field, "")) if field else ""


@dataclass(frozen=True)
class ValidationIssue:
    path: Path
    location: str
    message: str

    def __str__(self) -> str:
        suffix = f" at {self.location}" if self.location else ""
        return f"{self.path}{suffix}: {self.message}"


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _schema(object_type: str) -> dict[str, Any]:
    filename = SCHEMA_FILES[object_type]
    resource = resources.files("ael").joinpath("schemas", filename)
    return json.loads(resource.read_text(encoding="utf-8"))


def _contains_symlink(path: Path) -> bool:
    candidate = path.absolute()
    while True:
        if candidate.is_symlink():
            return True
        parent = candidate.parent
        if parent == candidate:
            return False
        candidate = parent


def _validation_root(path: Path) -> Path:
    start = path if path.is_dir() else path.parent
    for candidate in (start, *start.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate.resolve()
    return start.resolve()


def _json_paths(paths: Iterable[Path]) -> list[tuple[Path, Path]]:
    found: dict[Path, Path] = {}
    for supplied in paths:
        path = supplied.absolute()
        root = _validation_root(path)
        if path.is_dir():
            for candidate in path.rglob("*.json"):
                found[candidate.absolute()] = root
        else:
            found[path] = root
    return sorted(found.items())


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate object member: {key}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise ValueError(f"non-finite JSON number: {value}")


def load_documents(paths: Iterable[Path]) -> tuple[list[Document], list[ValidationIssue]]:
    documents: list[Document] = []
    issues: list[ValidationIssue] = []
    discovered = _json_paths(paths)
    if len(discovered) > MAX_JSON_DOCUMENTS:
        path = discovered[0][0] if discovered else Path.cwd()
        return [], [
            ValidationIssue(path, "", f"validation input exceeds {MAX_JSON_DOCUMENTS} JSON files")
        ]
    for path, root in discovered:
        if path.is_symlink():
            issues.append(ValidationIssue(path, "", "JSON document path must not use symlinks"))
            continue
        if not path.is_file():
            issues.append(ValidationIssue(path, "", "file does not exist"))
            continue
        if path.stat().st_size > MAX_JSON_BYTES:
            issues.append(
                ValidationIssue(path, "", f"JSON document exceeds {MAX_JSON_BYTES} bytes")
            )
            continue
        try:
            data = json.loads(
                path.read_text(encoding="utf-8"),
                object_pairs_hook=_strict_object,
                parse_constant=_reject_nonfinite,
            )
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
            issues.append(ValidationIssue(path, "", f"invalid JSON: {exc}"))
            continue
        if not isinstance(data, dict):
            issues.append(ValidationIssue(path, "", "top-level JSON value must be an object"))
            continue
        object_type = data.get("object_type")
        if object_type not in SCHEMA_FILES:
            issues.append(
                ValidationIssue(
                    path,
                    "object_type",
                    f"must be one of {sorted(SCHEMA_FILES)}",
                )
            )
            continue
        documents.append(Document(path=path.resolve(), root=root, data=data))
    return documents, issues


def _location(parts: Iterable[Any]) -> str:
    return ".".join(str(part) for part in parts)


def _walk_strings(
    value: Any, location: tuple[Any, ...] = ()
) -> Iterable[tuple[tuple[Any, ...], str]]:
    if isinstance(value, str):
        yield location, value
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk_strings(item, location + (index,))
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _walk_strings(item, location + (key,))


def _relative_target(
    document: Document, reference: dict[str, Any], location: str
) -> tuple[Path | None, list[ValidationIssue]]:
    uri = reference.get("uri")
    if not isinstance(uri, str):
        return None, []
    parsed = urlparse(uri)
    if parsed.scheme or uri.startswith("/"):
        return None, []
    root = document.root.resolve()
    candidate = document.path.resolve().parent / parsed.path
    if _contains_symlink(candidate):
        return None, [
            ValidationIssue(document.path, location, "local reference path must not use symlinks")
        ]
    target = candidate.resolve()
    if not target.is_relative_to(root):
        return None, [
            ValidationIssue(document.path, location, "local reference escapes validation root")
        ]
    return target, []


def _validate_reference_hash(
    document: Document,
    reference: dict[str, Any],
    location: str,
) -> list[ValidationIssue]:
    target, issues = _relative_target(document, reference, location)
    if issues:
        return issues
    if target is None:
        return []
    if not target.is_file():
        return [
            ValidationIssue(document.path, location, f"referenced file does not exist: {target}")
        ]
    expected = reference.get("sha256")
    if expected and sha256_path(target) != expected:
        return [ValidationIssue(document.path, location, f"SHA-256 does not match {target}")]
    return []


def _validate_study(document: Document) -> list[ValidationIssue]:
    data = document.data
    issues: list[ValidationIssue] = []
    candidates = data.get("conditions", [])
    condition_ids = [condition.get("condition_id") for condition in candidates]
    if len(condition_ids) != len(set(condition_ids)):
        issues.append(
            ValidationIssue(document.path, "conditions", "condition_id values must be unique")
        )
    roles = {condition.get("role") for condition in candidates}
    if "baseline" not in roles or "treatment" not in roles:
        issues.append(
            ValidationIssue(document.path, "conditions", "must include a baseline and a treatment")
        )
    for index, condition in enumerate(candidates):
        if condition.get("role") == "treatment" and not condition.get("changed_factors"):
            issues.append(
                ValidationIssue(
                    document.path,
                    f"conditions.{index}.changed_factors",
                    "treatment must declare at least one changed factor",
                )
            )
    task_keys = [
        (task.get("task_pack_id"), task.get("revision"), task.get("role"))
        for task in data.get("task_packs", [])
    ]
    if len(task_keys) != len(set(task_keys)):
        issues.append(
            ValidationIssue(document.path, "task_packs", "task-pack assignments must be unique")
        )
    if data.get("status") in {"frozen", "executing", "completed"}:
        refs: list[tuple[str, dict[str, Any]]] = [
            ("concept_ref", data.get("concept_ref", {})),
            ("analysis_plan", data.get("analysis_plan", {})),
        ]
        refs.extend(
            (f"conditions.{index}.intervention_ref", condition.get("intervention_ref", {}))
            for index, condition in enumerate(candidates)
        )
        refs.extend(
            (f"task_packs.{index}.artifact_ref", task.get("artifact_ref", {}))
            for index, task in enumerate(data.get("task_packs", []))
        )
        for location, reference in refs:
            if not reference.get("sha256"):
                issues.append(
                    ValidationIssue(
                        document.path, location, "hash-bound study reference requires SHA-256"
                    )
                )
            issues.extend(_validate_reference_hash(document, reference, location))
    return issues


def _validate_run(document: Document, studies: dict[str, Document]) -> list[ValidationIssue]:
    data = document.data
    issues: list[ValidationIssue] = []
    study_id = data.get("study_ref", {}).get("study_id")
    study = studies.get(study_id)
    if study:
        conditions = {item["condition_id"] for item in study.data.get("conditions", [])}
        if data.get("condition_id") not in conditions:
            issues.append(
                ValidationIssue(
                    document.path, "condition_id", "condition is absent from referenced study"
                )
            )
        task_packs = {item["task_pack_id"] for item in study.data.get("task_packs", [])}
        if data.get("task", {}).get("task_pack_id") not in task_packs:
            issues.append(
                ValidationIssue(
                    document.path, "task.task_pack_id", "task pack is absent from referenced study"
                )
            )
        expected_hash = data.get("study_ref", {}).get("sha256")
        if expected_hash and sha256_path(study.path) != expected_hash:
            issues.append(
                ValidationIssue(
                    document.path, "study_ref.sha256", "referenced study hash does not match"
                )
            )
    issues.extend(_validate_reference_hash(document, data.get("study_ref", {}), "study_ref"))
    return issues


def _validate_measurements(document: Document, runs: dict[str, Document]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    measurement_ids: list[str] = []
    for index, measurement in enumerate(document.data.get("measurements", [])):
        measurement_ids.append(measurement.get("measurement_id"))
        for run_id in measurement.get("run_ids", []):
            run = runs.get(run_id)
            if (
                run
                and run.data.get("status") != "valid"
                and measurement.get("kind") in EVALUATIVE_MEASUREMENT_KINDS
            ):
                issues.append(
                    ValidationIssue(
                        document.path,
                        f"measurements.{index}.run_ids",
                        f"evaluative measurement references non-valid run {run_id}",
                    )
                )
    if len(measurement_ids) != len(set(measurement_ids)):
        issues.append(
            ValidationIssue(document.path, "measurements", "measurement_id values must be unique")
        )
    return issues


def _validate_receipt(
    document: Document,
    studies: dict[str, Document],
    runs: dict[str, Document],
    measurement_sets: dict[str, Document],
) -> list[ValidationIssue]:
    data = document.data
    issues: list[ValidationIssue] = []
    study_ref = data.get("study_ref", {})
    study = studies.get(study_ref.get("study_id"))
    if study:
        expected_hash = study_ref.get("sha256")
        if expected_hash and sha256_path(study.path) != expected_hash:
            issues.append(
                ValidationIssue(
                    document.path, "study_ref.sha256", "referenced study hash does not match"
                )
            )
        if study.data.get("comparison_mode") == "operational_stack":
            for index, claim in enumerate(data.get("evaluated_claims", [])):
                if claim.get("claim_level") in {"model_only", "factor_causal"}:
                    issues.append(
                        ValidationIssue(
                            document.path,
                            f"evaluated_claims.{index}.claim_level",
                            "operational stack study cannot support model-only or factor-causal claim",
                        )
                    )
    independence = data.get("independence", {})
    if independence.get("label") == "independently_verified" and independence.get("role_overlaps"):
        issues.append(
            ValidationIssue(
                document.path,
                "independence.role_overlaps",
                "independently verified receipt cannot declare role overlap",
            )
        )
    for location, reference in [
        ("concept_ref", data.get("concept_ref", {})),
        ("study_ref", study_ref),
        ("measurement_set_ref", data.get("measurement_set_ref", {})),
    ]:
        issues.extend(_validate_reference_hash(document, reference, location))
    for index, reference in enumerate(data.get("run_record_refs", [])):
        issues.extend(_validate_reference_hash(document, reference, f"run_record_refs.{index}"))
        run_id = reference.get("run_id")
        if run_id and run_id not in runs:
            issues.append(
                ValidationIssue(
                    document.path, f"run_record_refs.{index}.run_id", "run record was not loaded"
                )
            )
    measurement_id = data.get("measurement_set_ref", {}).get("measurement_set_id")
    if measurement_id and measurement_id not in measurement_sets:
        issues.append(
            ValidationIssue(document.path, "measurement_set_ref", "measurement set was not loaded")
        )
    return issues


def validate(paths: Iterable[Path]) -> tuple[list[Document], list[ValidationIssue]]:
    documents, issues = load_documents(paths)
    format_checker = FormatChecker()
    identities: dict[tuple[str, str], Path] = {}

    for document in documents:
        validator = Draft202012Validator(
            _schema(document.object_type), format_checker=format_checker
        )
        for error in sorted(
            validator.iter_errors(document.data), key=lambda item: list(item.absolute_path)
        ):
            issues.append(
                ValidationIssue(document.path, _location(error.absolute_path), error.message)
            )
        key = (document.object_type, document.identity)
        if key in identities:
            issues.append(
                ValidationIssue(
                    document.path,
                    IDENTITY_FIELDS[document.object_type],
                    f"duplicates {identities[key]}",
                )
            )
        else:
            identities[key] = document.path
        for location, value in _walk_strings(document.data):
            personal_root = "/" + "Users/"
            if value.startswith(personal_root) or value.startswith("file://"):
                issues.append(
                    ValidationIssue(
                        document.path,
                        _location(location),
                        "personal absolute filesystem paths are forbidden",
                    )
                )

    studies = {doc.identity: doc for doc in documents if doc.object_type == "study_manifest"}
    runs = {doc.identity: doc for doc in documents if doc.object_type == "run_record"}
    measurements = {doc.identity: doc for doc in documents if doc.object_type == "measurement_set"}

    for document in documents:
        if document.object_type == "study_manifest":
            issues.extend(_validate_study(document))
        elif document.object_type == "run_record":
            issues.extend(_validate_run(document, studies))
        elif document.object_type == "measurement_set":
            issues.extend(_validate_measurements(document, runs))
        elif document.object_type == "evidence_receipt":
            issues.extend(_validate_receipt(document, studies, runs, measurements))

    return documents, sorted(
        issues, key=lambda issue: (str(issue.path), issue.location, issue.message)
    )
