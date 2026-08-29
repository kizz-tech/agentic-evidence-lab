from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from ael.validation import (
    IDENTITY_FIELDS,
    Document,
    ValidationIssue,
    _location,
    _relative_target,
    _schema,
    _study_reference_key,
    _validate_measurements,
    _validate_receipt,
    _validate_run,
    _validate_study,
    _walk_strings,
    load_documents,
)
from ael.validation import validate as _validate_documents


def _study_key(reference: Any) -> tuple[str, int] | None:
    if not isinstance(reference, dict):
        return None
    return _study_reference_key(reference)


def _string_run_ids(value: Any) -> Iterable[str]:
    if not isinstance(value, list):
        return ()
    return (run_id for run_id in value if isinstance(run_id, str))


def _list_value(value: Any) -> Iterable[Any]:
    return value if isinstance(value, list) else ()


class _SafeKeyDict(dict[str, Document]):
    """A document map that treats malformed schema keys as unresolved."""

    def get(self, key: object, default: Document | None = None) -> Document | None:
        try:
            return super().get(key, default)  # type: ignore[arg-type]
        except TypeError:
            return default

    def __contains__(self, key: object) -> bool:
        try:
            return super().__contains__(key)
        except TypeError:
            return False


def _safe_measurement_document(document: Document) -> Document:
    measurements = document.data.get("measurements")
    if not isinstance(measurements, list):
        data = dict(document.data)
        data["measurements"] = []
        return Document(path=document.path, root=document.root, data=data)
    normalized: list[Any] = []
    changed = False
    for measurement in measurements:
        if (
            isinstance(measurement, dict)
            and "run_ids" in measurement
            and not isinstance(measurement["run_ids"], list)
        ):
            measurement = dict(measurement)
            measurement["run_ids"] = []
            changed = True
        normalized.append(measurement)
    if not changed:
        return document
    data = dict(document.data)
    data["measurements"] = normalized
    return Document(path=document.path, root=document.root, data=data)


def _validate_documents_with_safe_maps(
    paths: list[Path],
) -> tuple[list[Document], list[ValidationIssue]]:
    """Run the frozen validator pipeline with total document lookups.

    Contract-v0 schema errors are reported before cross-document checks.  The
    frozen validator predates that ordering for malformed ``run_ids`` and can
    attempt to hash an object while looking up a run.  Keep its behavior and
    issue ordering while making those lookups fail closed for the additive
    wrapper.
    """
    documents, issues = load_documents(paths)
    format_checker = FormatChecker()
    identities: dict[tuple[str, str, int | None], Path] = {}

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
        key = document.identity_key
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

    studies = {
        (doc.identity, int(doc.data["revision"])): doc
        for doc in documents
        if doc.object_type == "study_manifest" and isinstance(doc.data.get("revision"), int)
    }
    runs = _SafeKeyDict({doc.identity: doc for doc in documents if doc.object_type == "run_record"})
    measurements = _SafeKeyDict(
        {doc.identity: doc for doc in documents if doc.object_type == "measurement_set"}
    )

    for document in documents:
        if document.object_type == "study_manifest":
            issues.extend(_validate_study(document))
        elif document.object_type == "run_record":
            issues.extend(_validate_run(document, studies))
        elif document.object_type == "measurement_set":
            issues.extend(
                _validate_measurements(_safe_measurement_document(document), runs, studies)
            )
        elif document.object_type == "evidence_receipt":
            issues.extend(_validate_receipt(document, studies, runs, measurements))

    return documents, sorted(
        issues, key=lambda issue: (str(issue.path), issue.location, issue.message)
    )


def _resolve_loaded_reference(
    document: Document,
    reference: Any,
    location: str,
    expected_type: str,
    expected_identity: str,
    documents: dict[Path, Document],
    *,
    expected_revision: int | None = None,
    require_loaded: bool = True,
) -> tuple[Document | None, bool, list[ValidationIssue]]:
    if not isinstance(reference, dict):
        return None, False, []
    target, issues = _relative_target(document, reference, location)
    if issues:
        return None, True, issues
    if target is None:
        return None, False, []
    if not target.is_file():
        if not require_loaded:
            return None, True, []
        label = expected_type.replace("_", " ")
        return None, True, [ValidationIssue(document.path, location, f"{label} was not loaded")]
    target_document = documents.get(target)
    if target_document is None:
        if not require_loaded:
            return None, True, []
        label = expected_type.replace("_", " ")
        return None, True, [ValidationIssue(document.path, location, f"{label} was not loaded")]
    target_issues: list[ValidationIssue] = []
    if target_document.object_type != expected_type:
        target_issues.append(
            ValidationIssue(
                document.path,
                f"{location}.uri",
                f"reference target object_type does not match {expected_type}",
            )
        )
    if target_document.identity != expected_identity:
        target_issues.append(
            ValidationIssue(
                document.path,
                f"{location}.{IDENTITY_FIELDS[expected_type]}",
                "reference target identity does not match declared identity",
            )
        )
    if expected_revision is not None and target_document.data.get("revision") != expected_revision:
        target_issues.append(
            ValidationIssue(
                document.path,
                f"{location}.revision",
                "reference target revision does not match declared revision",
            )
        )
    return (target_document if not target_issues else None), True, target_issues


def _measurement_run_issues(
    document: Document,
    run_ids: Any,
    location: str,
    runs: dict[str, Document],
    study_key: tuple[str, int] | None,
) -> list[ValidationIssue]:
    if not isinstance(run_ids, list):
        return []
    issues: list[ValidationIssue] = []
    for run_id in run_ids:
        run = runs.get(run_id) if isinstance(run_id, str) else None
        if run is None:
            issues.append(ValidationIssue(document.path, location, "run record was not loaded"))
            continue
        if study_key is not None and _study_key(run.data.get("study_ref")) != study_key:
            issues.append(
                ValidationIssue(
                    document.path,
                    location,
                    "run record study reference does not match measurement set study reference",
                )
            )
    return issues


def _validate_study_reference(
    document: Document,
    reference: Any,
    location: str,
    documents: dict[Path, Document],
) -> list[ValidationIssue]:
    study_key = _study_key(reference)
    if study_key is None:
        return []
    _target, _local, issues = _resolve_loaded_reference(
        document,
        reference,
        location,
        "study_manifest",
        study_key[0],
        documents,
        expected_revision=study_key[1],
    )
    return issues


def _validate_measurement_graph(
    document: Document,
    runs: dict[str, Document],
    documents: dict[Path, Document],
) -> list[ValidationIssue]:
    data = document.data
    study_key = _study_key(data.get("study_ref"))
    issues = _validate_study_reference(document, data.get("study_ref"), "study_ref", documents)
    for index, measurement in enumerate(_list_value(data.get("measurements"))):
        if isinstance(measurement, dict):
            issues.extend(
                _measurement_run_issues(
                    document,
                    measurement.get("run_ids"),
                    f"measurements.{index}.run_ids",
                    runs,
                    study_key,
                )
            )
    for index, failure in enumerate(_list_value(data.get("critical_failures"))):
        if isinstance(failure, dict):
            issues.extend(
                _measurement_run_issues(
                    document,
                    failure.get("run_ids"),
                    f"critical_failures.{index}.run_ids",
                    runs,
                    study_key,
                )
            )
    return issues


def _validate_study_concept(
    document: Document, documents: dict[Path, Document]
) -> list[ValidationIssue]:
    reference = document.data.get("concept_ref", {})
    if not isinstance(reference, dict):
        return []
    concept_id = reference.get("concept_id")
    revision = reference.get("revision")
    _target, _local, issues = _resolve_loaded_reference(
        document,
        reference,
        "concept_ref",
        "concept",
        concept_id if isinstance(concept_id, str) else "",
        documents,
        expected_revision=revision if isinstance(revision, int) else None,
        require_loaded=document.data.get("status") in {"frozen", "executing", "completed"},
    )
    return issues


def _validate_receipt_graph(
    document: Document,
    runs: dict[str, Document],
    measurement_sets: dict[str, Document],
    documents: dict[Path, Document],
) -> list[ValidationIssue]:
    data = document.data
    issues = _validate_study_reference(document, data.get("study_ref"), "study_ref", documents)
    receipt_study_key = _study_key(data.get("study_ref"))

    concept_reference = data.get("concept_ref", {})
    if isinstance(concept_reference, dict):
        concept_id = concept_reference.get("concept_id")
        revision = concept_reference.get("revision")
        _target, _local, target_issues = _resolve_loaded_reference(
            document,
            concept_reference,
            "concept_ref",
            "concept",
            concept_id if isinstance(concept_id, str) else "",
            documents,
            expected_revision=revision if isinstance(revision, int) else None,
            require_loaded=True,
        )
        issues.extend(target_issues)

    receipt_run_ids: set[str] = set()
    for index, reference in enumerate(_list_value(data.get("run_record_refs"))):
        if not isinstance(reference, dict):
            continue
        location = f"run_record_refs.{index}"
        run_id = reference.get("run_id")
        if isinstance(run_id, str) and run_id:
            receipt_run_ids.add(run_id)
        target_run, local_reference, target_issues = _resolve_loaded_reference(
            document,
            reference,
            location,
            "run_record",
            run_id if isinstance(run_id, str) else "",
            documents,
        )
        issues.extend(target_issues)
        run = target_run if local_reference else (runs.get(run_id) if run_id else None)
        if run_id and run is None and not target_issues:
            issues.append(
                ValidationIssue(document.path, f"{location}.run_id", "run record was not loaded")
            )
        elif (
            run is not None
            and receipt_study_key is not None
            and _study_key(run.data.get("study_ref")) != receipt_study_key
        ):
            issues.append(
                ValidationIssue(
                    document.path,
                    f"{location}.run_id",
                    "run record study reference does not match receipt study reference",
                )
            )

    measurement_reference = data.get("measurement_set_ref", {})
    measurement_id = (
        measurement_reference.get("measurement_set_id")
        if isinstance(measurement_reference, dict)
        else None
    )
    target_measurement_set, local_reference, target_issues = _resolve_loaded_reference(
        document,
        measurement_reference,
        "measurement_set_ref",
        "measurement_set",
        measurement_id if isinstance(measurement_id, str) else "",
        documents,
    )
    issues.extend(target_issues)
    measurement_set = (
        target_measurement_set
        if local_reference
        else (measurement_sets.get(measurement_id) if measurement_id else None)
    )
    if measurement_id and measurement_set is None and not target_issues:
        issues.append(
            ValidationIssue(document.path, "measurement_set_ref", "measurement set was not loaded")
        )
    if measurement_set is None:
        return issues

    measurement_study_key = _study_key(measurement_set.data.get("study_ref"))
    if receipt_study_key is not None and measurement_study_key != receipt_study_key:
        issues.append(
            ValidationIssue(
                document.path,
                "measurement_set_ref",
                "measurement set study reference does not match receipt study reference",
            )
        )
    for index, failure in enumerate(_list_value(measurement_set.data.get("critical_failures"))):
        if not isinstance(failure, dict):
            continue
        for run_id in _string_run_ids(failure.get("run_ids")):
            run = runs.get(run_id)
            location = f"measurement_set_ref.critical_failures.{index}.run_ids"
            if run is None:
                issues.append(ValidationIssue(document.path, location, "run record was not loaded"))
            elif (
                receipt_study_key is not None
                and _study_key(run.data.get("study_ref")) != receipt_study_key
            ):
                issues.append(
                    ValidationIssue(
                        document.path,
                        location,
                        "critical failure run study reference does not match receipt study reference",
                    )
                )
    consumed_run_ids = {
        run_id
        for measurement in _list_value(measurement_set.data.get("measurements"))
        if isinstance(measurement, dict)
        for run_id in _string_run_ids(measurement.get("run_ids"))
    }
    consumed_run_ids.update(
        run_id
        for failure in _list_value(measurement_set.data.get("critical_failures"))
        if isinstance(failure, dict)
        for run_id in _string_run_ids(failure.get("run_ids"))
    )
    for run_id in sorted(consumed_run_ids - receipt_run_ids):
        issues.append(
            ValidationIssue(
                document.path,
                "run_record_refs",
                f"measurement set references run {run_id} not included in receipt run_record_refs",
            )
        )
    return issues


def validate(paths: Iterable[Path]) -> tuple[list[Document], list[ValidationIssue]]:
    path_list = list(paths)
    try:
        documents, issues = _validate_documents(path_list)
    except TypeError:
        # The frozen validator assumes schema-valid run_ids while traversing
        # measurement sets.  Preserve its checks through the safe-map path so
        # malformed scalar/list members produce issues instead of a traceback.
        documents, issues = _validate_documents_with_safe_maps(path_list)
    documents_by_path = {document.path: document for document in documents}
    runs = {
        document.identity: document
        for document in documents
        if document.object_type == "run_record"
    }
    measurement_sets = {
        document.identity: document
        for document in documents
        if document.object_type == "measurement_set"
    }
    for document in documents:
        if document.object_type == "study_manifest":
            issues.extend(_validate_study_concept(document, documents_by_path))
        elif document.object_type == "run_record":
            issues.extend(
                _validate_study_reference(
                    document, document.data.get("study_ref"), "study_ref", documents_by_path
                )
            )
        elif document.object_type == "measurement_set":
            issues.extend(_validate_measurement_graph(document, runs, documents_by_path))
        elif document.object_type == "evidence_receipt":
            issues.extend(
                _validate_receipt_graph(document, runs, measurement_sets, documents_by_path)
            )
    return documents, sorted(
        issues, key=lambda issue: (str(issue.path), issue.location, issue.message)
    )
