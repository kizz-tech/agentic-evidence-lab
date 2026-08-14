"""Fail-closed projection of Contract v0 receipts into public result cards.

The result-catalog profile in ``studies/public-results.json`` is deliberately
small. It selects immutable receipt/report bytes and supplies only catalog and
handoff metadata that Contract v0 does not own. Every empirical value in
generated views is copied from a validated receipt; profile text cannot author
a finding, claim an external release, or raise a proof level.
"""

from __future__ import annotations

import datetime as _datetime
import hashlib
import json
import os
import re
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from jsonschema import Draft202012Validator, FormatChecker

from ael import result_core as _result_core
from ael import result_rendering as _result_rendering
from ael.method_policy import (
    ClaimSupportContext,
    EvidenceBinding,
    MethodPolicyError,
    validate_claim_support,
)
from ael.result_constants import (
    GENERATOR_NAME,
    GENERATOR_VERSION,
    PUBLIC_RESULTS_SCHEMA_VERSION,
    PUBLICATION_PROJECTION_POLICY,
)
from ael.result_verification import AuditRequest, audit_adapter_names, public_audit_projection
from ael.sandbox import SandboxError
from ael.study_quality import public_projection as project_study_quality
from ael.validation import SCHEMA_FILES, sha256_path, validate

ResultSurfaceError = _result_core.ResultSurfaceError
SourceLedger = _result_core.SourceLedger
_contains_symlink = _result_core.contains_symlink
_fail = _result_core.fail
_load_json_object = _result_core.load_json_object
_nonempty_string = _result_core.nonempty_string
_regular_directory = _result_core.regular_directory
_regular_file = _result_core.regular_file
_relative_path = _result_core.relative_path
_repository_root = _result_core.repository_root
_require_keys = _result_core.require_keys
_sha = _result_core.sha
_validate_date = _result_core.validate_date
_json_bytes = _result_rendering.json_bytes
_render_card = _result_rendering.render_card
_render_results = _result_rendering.render_results

_CARD_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SCHEMES = {"evidence_graph", "frozen_public_bundle"}
_VISIBILITIES = {"public", "private", "hidden", "embargoed"}
_MATERIAL_AVAILABILITY = {"public", "withheld", "not_retained", "not_collected"}
_HISTORY_UNKNOWN = "not_declared_historical"
_HISTORY_FRESHNESS_UNKNOWN = "unassessed"
_HISTORY_DERIVED = "derived_from_lifecycle"
_CATALOG_STATES = {"listed", "withdrawn"}
_MAINTAINER_RERUN_STATES = {
    "maintainer_only_new_observation",
    "not_assessed",
    "unavailable",
}
_PUBLIC_GRAPH_STATUS = {
    "evidence_graph": "graph_validatable",
    "frozen_public_bundle": "decision_recomputable",
}
_INDEPENDENT_REPLICATION_STATUS = {
    "self_review": "none_linked",
    "model_critique": "none_linked",
    "maintainer_evaluated": "none_linked",
    "reproduced_third_party": "third_party_reproduced",
    "independently_verified": "independently_verified",
}


def _load_profile(profile_path: Path) -> dict[str, Any]:
    return _load_json_object(profile_path)


def validate_public_profile(profile: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a decoded result-catalog profile and return it unchanged.

    This function performs schema-like checks without touching the filesystem;
    source hash/path checks are performed by :func:`build_result_surface`.
    """

    if not isinstance(profile, Mapping):
        _fail("result-catalog profile must be an object")
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
                "decision_claim_ids",
                "verification",
                "materials",
                "history",
                "quality",
                "catalog_state",
                "maintainer_rerun",
            },
            {"report_ref", "lifecycle"},
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
        _validate_claim_ids(study.get("decision_claim_ids"), f"{location}.decision_claim_ids")
        selected_claim_ids = set(study["claim_ids"])
        decision_claim_ids = set(study["decision_claim_ids"])
        if not decision_claim_ids.issubset(selected_claim_ids):
            _fail(f"{location}.decision_claim_ids must be a subset of claim_ids")
        _validate_verification(study.get("verification"), f"{location}.verification")
        _validate_materials(study.get("materials"), f"{location}.materials")
        _validate_maintainer_rerun(study.get("maintainer_rerun"), f"{location}.maintainer_rerun")
        lifecycle = study.get("lifecycle")
        _validate_history(study.get("history"), f"{location}.history", lifecycle is not None)
        _validate_quality(study.get("quality"), f"{location}.quality")
        if lifecycle is not None:
            _validate_lifecycle(lifecycle, f"{location}.lifecycle")
        catalog_state = study.get("catalog_state")
        if catalog_state not in _CATALOG_STATES:
            _fail(f"{location}.catalog_state must be one of {sorted(_CATALOG_STATES)}")
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
        adapters = audit_adapter_names()
        if adapter not in adapters:
            _fail(f"{location}.adapter must be one of {list(adapters)}")
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


def _validate_maintainer_rerun(value: Any, location: str) -> None:
    if not isinstance(value, Mapping):
        _fail(f"{location} must be an object")
    _require_keys(value, {"status", "boundary"}, set(), location)
    status = value.get("status")
    if status not in _MAINTAINER_RERUN_STATES:
        _fail(f"{location}.status must be one of {sorted(_MAINTAINER_RERUN_STATES)}")
    _nonempty_string(value.get("boundary"), f"{location}.boundary")


def _validate_history(value: Any, location: str, has_lifecycle: bool = False) -> None:
    if not isinstance(value, Mapping):
        _fail(f"{location} must be an object")
    _require_keys(value, {"admission", "action", "outcome_follow_up", "freshness"}, set(), location)
    expected = _HISTORY_DERIVED if has_lifecycle else _HISTORY_UNKNOWN
    for key in ("admission", "action", "outcome_follow_up"):
        if value.get(key) != expected:
            _fail(f"{location}.{key} must equal {expected}")
    freshness = _HISTORY_DERIVED if has_lifecycle else _HISTORY_FRESHNESS_UNKNOWN
    if value.get("freshness") != freshness:
        _fail(f"{location}.freshness must equal {freshness}")


def _validate_quality(value: Any, location: str) -> None:
    if not isinstance(value, Mapping):
        _fail(f"{location} must be an object")
    assessment = value.get("assessment")
    if assessment == "not_assessed_historical":
        _require_keys(value, {"assessment"}, set(), location)
        return
    if assessment == "profiled":
        _require_keys(value, {"assessment", "profile_ref"}, set(), location)
        _validate_profile_ref_shape(value.get("profile_ref"), f"{location}.profile_ref")
        return
    _fail(f"{location}.assessment must be not_assessed_historical or profiled")


def _validate_lifecycle(value: Any, location: str) -> None:
    if not isinstance(value, Mapping):
        _fail(f"{location} must be an object")
    _require_keys(
        value,
        {"admission_ref", "adoption_decision_ref", "action_record_ref", "outcome_follow_up_ref"},
        set(),
        location,
    )
    for key in (
        "admission_ref",
        "adoption_decision_ref",
        "action_record_ref",
        "outcome_follow_up_ref",
    ):
        _validate_profile_ref_shape(value.get(key), f"{location}.{key}")


def load_public_profile(profile_path: Path) -> dict[str, Any]:
    """Load and validate a result-catalog profile without resolving its sources."""

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
    sources: SourceLedger,
) -> list[Path]:
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
    sources.add(receipt_path)
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
        target, _ = sources.resolve(
            receipt_path,
            reference,
            f"receipt.{location}",
            strict=False,
        )
        paths.append(target)
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
    return paths


def _select_claim_records(
    receipt: Mapping[str, Any],
    claim_ids: list[str],
    card_id: str,
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
    for claim_id in claim_ids:
        claim = by_id.get(claim_id)
        if claim is None:
            _fail(f"selected claim {claim_id} is absent from receipt for {card_id}")
        evidence_refs = claim.get("evidence_refs")
        if not isinstance(evidence_refs, list) or not all(
            isinstance(reference, str) for reference in evidence_refs
        ):
            _fail(f"claim {claim_id} has invalid evidence references")
        selected.append(claim)
    return selected


def _admit_selected_claims(
    claims: list[dict[str, Any]], card_id: str, support_context: ClaimSupportContext
) -> None:
    for claim in claims:
        try:
            validate_claim_support(
                claim_id=str(claim["claim_id"]),
                claim_level=str(claim["claim_level"]),
                evidence_refs=claim["evidence_refs"],
                context=support_context,
            )
        except MethodPolicyError as exc:
            _fail(f"{card_id}: {exc}")


def _source_ref(
    owner: Path,
    ref: Mapping[str, Any],
    location: str,
    sources: SourceLedger,
) -> dict[str, str]:
    return sources.projected_ref(owner, ref, location)


def _material_projection(
    materials: list[Mapping[str, Any]],
    owner: Path,
    sources: SourceLedger,
) -> list[dict[str, Any]]:
    projected: list[dict[str, Any]] = []
    for index, material in enumerate(materials):
        availability = str(material["availability"])
        item: dict[str, Any] = {"label": material["label"], "availability": availability}
        if availability == "public":
            item["ref"] = _source_ref(
                owner,
                material["ref"],
                f"materials.{index}.ref",
                sources,
            )
        else:
            item["reason"] = material["reason"]
            item["reproduction_impact"] = material["reproduction_impact"]
        projected.append(item)
    return projected


def _lifecycle_projection(
    lifecycle: Mapping[str, Any],
    owner: Path,
    sources: SourceLedger,
    as_of: str,
) -> tuple[dict[str, str], dict[str, Any]]:
    refs: dict[str, dict[str, str]] = {}
    documents: dict[str, dict[str, Any]] = {}
    for key in (
        "admission_ref",
        "adoption_decision_ref",
        "action_record_ref",
        "outcome_follow_up_ref",
    ):
        refs[key] = _source_ref(
            owner,
            lifecycle[key],
            f"lifecycle.{key}",
            sources,
        )
        documents[key] = _load_json_object(sources.repository_root / refs[key]["uri"])

    admission = documents["admission_ref"]
    adoption = documents["adoption_decision_ref"]
    action = documents["action_record_ref"]
    follow_up = documents["outcome_follow_up_ref"]
    expected_schemas = {
        "admission_ref": "ael.study-admission/0.1-pilot",
        "adoption_decision_ref": "ael.adoption-decision/0.1-pilot",
        "action_record_ref": "ael.action-record/0.1-pilot",
        "outcome_follow_up_ref": "ael.outcome-follow-up/0.1-pilot",
    }
    for key, expected in expected_schemas.items():
        if documents[key].get("schema_version") != expected:
            _fail(f"lifecycle.{key} must use {expected}")
    if admission.get("status") != "admitted":
        _fail("lifecycle admission must have admitted status")
    if adoption.get("admission_ref", {}).get("sha256") != refs["admission_ref"]["sha256"]:
        _fail("lifecycle adoption decision does not bind the admission")
    if (
        action.get("adoption_decision_ref", {}).get("sha256")
        != refs["adoption_decision_ref"]["sha256"]
    ):
        _fail("lifecycle action record does not bind the adoption decision")
    if follow_up.get("action_ref", {}).get("sha256") != refs["action_record_ref"]["sha256"]:
        _fail("lifecycle follow-up does not bind the action record")
    roles = admission.get("roles")
    follow_up_plan = admission.get("follow_up_plan")
    if not isinstance(roles, Mapping) or not isinstance(follow_up_plan, Mapping):
        _fail("lifecycle admission lacks owner roles or follow-up plan")
    action_owner = roles.get("action_owner")
    if adoption.get("owner_id") != action_owner or action.get("actor_id") != action_owner:
        _fail("lifecycle action ownership differs from the admission")
    if follow_up.get("owner_id") != follow_up_plan.get("owner_id"):
        _fail("lifecycle follow-up ownership differs from the admission")
    if adoption.get("candidate") != admission.get("candidate"):
        _fail("lifecycle adoption candidate differs from the admission")

    action_state = action.get("state")
    follow_up_status = follow_up.get("status")
    follow_up_conclusion = follow_up.get("conclusion")
    if action_state not in {"verified", "blocked"}:
        _fail("lifecycle action has an unsupported state")
    if follow_up_status not in {"scheduled", "completed", "cancelled"}:
        _fail("lifecycle follow-up has an unsupported status")
    due_at = follow_up.get("planned_due_at")
    if not isinstance(due_at, str):
        _fail("lifecycle follow-up lacks planned_due_at")
    try:
        due_date = _datetime.datetime.fromisoformat(due_at.replace("Z", "+00:00")).date()
        as_of_date = _datetime.date.fromisoformat(as_of)
    except ValueError:
        _fail("lifecycle follow-up uses an invalid timestamp")
    if follow_up_status == "scheduled":
        freshness = "within_declared_window" if as_of_date <= due_date else "past_declared_due_date"
    else:
        freshness = "resolved"
    history = {
        "admission": str(admission["status"]),
        "action": str(action_state),
        "outcome_follow_up": f"{follow_up_status}:{follow_up_conclusion}",
        "freshness": freshness,
    }
    projected = {
        "refs": refs,
        "adoption_disposition": adoption.get("disposition"),
        "action_kind": action.get("action_kind"),
        "follow_up_due_at": due_at,
    }
    return history, projected


def _study_and_measurement_projection(
    receipt_path: Path,
    receipt: Mapping[str, Any],
    sources: SourceLedger,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    study_path, _ = sources.resolve(
        receipt_path,
        receipt["study_ref"],
        "receipt.study_ref",
        strict=False,
    )
    measurement_path, _ = sources.resolve(
        receipt_path,
        receipt["measurement_set_ref"],
        "receipt.measurement_set_ref",
        strict=False,
    )
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
                "intervention_class": condition["intervention_class"],
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
    return study_projection, _measurement_projection(measurement_set), measurement_set


def _measurement_projection(measurement_set: Mapping[str, Any]) -> dict[str, Any]:
    by_kind: dict[str, int] = {}
    grouped: dict[tuple[str, str, str], list[Mapping[str, Any]]] = {}
    uncertainty_measurements = 0
    for measurement in measurement_set.get("measurements", []):
        kind = str(measurement["kind"])
        by_kind[kind] = by_kind.get(kind, 0) + 1
        if "uncertainty" in measurement:
            uncertainty_measurements += 1
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
        "uncertainty": {
            "status": "reported" if uncertainty_measurements else "not_reported",
            "measurement_count": uncertainty_measurements,
        },
        "selected_summaries": summaries,
    }


def _run_projection(
    receipt_path: Path,
    receipt: Mapping[str, Any],
    sources: SourceLedger,
    task_pack_roles: Mapping[str, str],
) -> tuple[dict[str, Any], dict[str, str]]:
    by_status: dict[str, int] = {}
    by_condition: dict[str, int] = {}
    valid_repeats_by_cell: dict[tuple[str, str, str], set[int]] = {}
    run_task_pack_roles: dict[str, str] = {}
    for index, reference in enumerate(receipt["run_record_refs"]):
        run_path, _ = sources.resolve(
            receipt_path,
            reference,
            f"receipt.run_record_refs.{index}",
            strict=False,
        )
        run = _load_json_object(run_path)
        status = str(run["status"])
        condition = str(run["condition_id"])
        by_status[status] = by_status.get(status, 0) + 1
        by_condition[condition] = by_condition.get(condition, 0) + 1
        task = run["task"]
        task_pack_id = str(task["task_pack_id"])
        task_pack_role = task_pack_roles.get(task_pack_id)
        if task_pack_role is None:
            _fail(f"run {run['run_id']} references unknown task pack {task_pack_id}")
        run_id = str(run["run_id"])
        if run_id in run_task_pack_roles:
            _fail(f"receipt contains duplicate run ID {run_id}")
        run_task_pack_roles[run_id] = task_pack_role
        cell = (task_pack_id, str(task["task_id"]), condition)
        valid_repeats_by_cell.setdefault(cell, set())
        if status == "valid":
            valid_repeats_by_cell[cell].add(int(run["repeat_index"]))
    repeat_counts = [len(repeats) for repeats in valid_repeats_by_cell.values()]
    minimum = min(repeat_counts) if repeat_counts else 0
    maximum = max(repeat_counts) if repeat_counts else 0
    if not repeat_counts or minimum == 0:
        repeat_status = "retained_cell_without_valid_observation"
    elif minimum == maximum == 1:
        repeat_status = "single_valid_observation_per_retained_cell"
    elif minimum >= 2:
        repeat_status = "repeated_valid_observations_per_retained_cell"
    else:
        repeat_status = "mixed_valid_repeat_coverage"
    projection = {
        "count": len(receipt["run_record_refs"]),
        "by_status": dict(sorted(by_status.items())),
        "by_condition": dict(sorted(by_condition.items())),
        "repeat_evidence": {
            "status": repeat_status,
            "retained_task_condition_cells": len(repeat_counts),
            "minimum_valid_repeats_per_cell": minimum,
            "maximum_valid_repeats_per_cell": maximum,
        },
    }
    return projection, run_task_pack_roles


def _measurement_evidence_bindings(
    measurement_set: Mapping[str, Any], run_task_pack_roles: Mapping[str, str]
) -> dict[str, EvidenceBinding]:
    bindings: dict[str, EvidenceBinding] = {}
    for measurement in measurement_set.get("measurements", []):
        measurement_id = str(measurement["measurement_id"])
        if measurement_id in bindings:
            _fail(f"measurement set contains duplicate measurement ID {measurement_id}")
        roles: set[str] = set()
        for run_id in measurement["run_ids"]:
            role = run_task_pack_roles.get(str(run_id))
            if role is None:
                _fail(f"measurement {measurement_id} references unknown run {run_id}")
            roles.add(role)
        bindings[measurement_id] = EvidenceBinding(
            kind=str(measurement["kind"]),
            task_pack_roles=frozenset(roles),
        )
    return bindings


def _claim_evidence_bindings(
    receipt_path: Path,
    claims: list[Mapping[str, Any]],
    measurement_bindings: Mapping[str, EvidenceBinding],
    sources: SourceLedger,
) -> tuple[dict[str, EvidenceBinding], dict[str, dict[str, Any]]]:
    """Classify selected claim refs and bind resolvable public evidence."""

    bindings = dict(measurement_bindings)
    projections: dict[str, dict[str, Any]] = {
        reference: {
            "reference": reference,
            "binding": "measurement",
            "measurement_kind": binding.kind,
            "task_pack_roles": sorted(binding.task_pack_roles),
        }
        for reference, binding in bindings.items()
    }
    for claim in claims:
        for evidence_ref in claim["evidence_refs"]:
            reference = str(evidence_ref)
            if reference in projections:
                continue
            parsed = urlparse(reference)
            if reference.startswith("/") or "\\" in reference or "\x00" in reference:
                _fail(
                    f"claim {claim['claim_id']} evidence reference contains an unsafe path: "
                    f"{reference}"
                )
            if ".." in Path(parsed.path).parts:
                _fail(f"claim {claim['claim_id']} evidence reference contains traversal")
            if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
                projections[reference] = {
                    "reference": reference,
                    "binding": "opaque_receipt_reference",
                }
                continue
            candidate = receipt_path.parent / parsed.path
            if _contains_symlink(candidate):
                _fail(f"claim {claim['claim_id']} evidence sidecar must not use symlinks")
            target = candidate.resolve()
            if not target.is_relative_to(sources.repository_root):
                _fail(f"claim {claim['claim_id']} evidence sidecar escapes repository root")
            if not target.exists():
                projections[reference] = {
                    "reference": reference,
                    "binding": "opaque_receipt_reference",
                }
                continue
            _regular_file(target, f"claim {claim['claim_id']} evidence sidecar")
            relative = _relative_path(target, sources.repository_root)
            digest = sources.add(target)
            bindings[reference] = EvidenceBinding(kind="artifact", source="public_sidecar")
            projections[reference] = {
                "reference": reference,
                "binding": "public_sidecar",
                "uri": relative,
                "sha256": digest,
            }
    return bindings, projections


def _audit_projection(
    verification: Mapping[str, Any],
    profile_path: Path,
    sources: SourceLedger,
    require_git_proof: bool,
) -> dict[str, Any] | None:
    if verification["kind"] != "frozen_public_bundle":
        return None
    freeze_path, _ = sources.resolve(
        profile_path,
        verification["freeze_ref"],
        "verification.freeze_ref",
    )
    result_root_string = str(verification["result_root"])
    result_candidate = sources.repository_root / result_root_string
    if _contains_symlink(result_candidate):
        _fail("verification.result_root must not use symlinks")
    result_root = result_candidate.resolve()
    if not result_root.is_relative_to(sources.repository_root):
        _fail("verification.result_root escapes repository root")
    _regular_directory(result_root, "verification.result_root")
    sources.add_tree(result_root, "verification.result_root")
    try:
        return public_audit_projection(
            str(verification["adapter"]),
            AuditRequest(
                freeze_path,
                result_root,
                git_root=sources.repository_root,
                require_git_proof=require_git_proof,
            ),
        )
    except SandboxError as exc:
        _fail(f"frozen public bundle audit failed: {exc}")


def _quality_projection(
    value: Mapping[str, Any],
    receipt: Mapping[str, Any],
    reference_owner: Path,
    sources: SourceLedger,
    as_of: str,
) -> dict[str, Any]:
    if value["assessment"] == "not_assessed_historical":
        return {
            "scope": "design_preflight",
            "status": "not_assessed_historical",
            "quality_axes": {
                "design_class": "not_assessed_historical",
                "task_validity": "not_assessed_historical",
                "evaluator_validity": "not_assessed_historical",
                "sampling_strength": "not_assessed_historical",
                "reliability_coverage": "not_assessed_historical",
                "independence": "not_assessed_historical",
                "freshness": "not_assessed_historical",
            },
            "issues": [],
            "boundary": (
                "The study predates the pilot Study Quality Profile. No retrospective "
                "measurement-quality assessment is inferred from current artifacts."
            ),
        }
    quality_path, quality_digest = sources.resolve(
        reference_owner,
        value["profile_ref"],
        "quality.profile_ref",
    )
    try:
        projection = project_study_quality(quality_path, sources.repository_root, as_of=as_of)
    except SandboxError as exc:
        _fail(f"quality profile preflight failed: {exc}")
    study_ref = receipt.get("study_ref")
    if not isinstance(study_ref, Mapping):
        _fail("quality profile requires a receipt study_ref")
    if projection["study"]["study_id"] != study_ref.get("study_id"):
        _fail("quality profile study_id does not match receipt study_ref")
    if projection["study"]["revision"] != study_ref.get("revision"):
        _fail("quality profile revision does not match receipt study_ref")
    if projection["study"]["manifest_sha256"] != study_ref.get("sha256"):
        _fail("quality profile manifest hash does not match receipt study_ref")
    relative = _relative_path(quality_path, sources.repository_root)
    projection["profile"] = {"uri": relative, "sha256": quality_digest}
    return projection


def _reproduction_projection(
    entry: Mapping[str, Any], receipt: Mapping[str, Any]
) -> dict[str, Any]:
    verification = entry["verification"]
    verification_kind = verification["kind"]
    public_status = _PUBLIC_GRAPH_STATUS.get(verification_kind)
    if public_status is None:
        _fail(f"unsupported public verification kind: {verification_kind}")
    independence = receipt["independence"]
    independence_label = independence["label"]
    independent_status = _INDEPENDENT_REPLICATION_STATUS.get(independence_label)
    if independent_status is None:
        _fail(f"unsupported independence label: {independence_label}")
    return {
        "public_graph_verification": {
            "status": public_status,
            "boundary": verification["boundary"],
        },
        "study_rerun": dict(entry["maintainer_rerun"]),
        "independent_replication": {
            "status": independent_status,
            "boundary": independence["disclosure"],
        },
    }


def _build_card(
    profile_path: Path,
    profile: Mapping[str, Any],
    entry: Mapping[str, Any],
    repository_root: Path,
    require_git_proof: bool,
) -> tuple[dict[str, Any], dict[str, str]]:
    profile_reference_owner = repository_root / ".ael-public-results-profile"
    sources = SourceLedger(repository_root)
    receipt_path, receipt_digest = sources.resolve(
        profile_reference_owner,
        entry["receipt_ref"],
        f"{entry['card_id']}.receipt_ref",
    )
    receipt = _load_json_object(receipt_path)
    _receipt_graph(receipt_path, receipt, sources)
    sources.add(profile_path)
    report_projection: dict[str, str] | None = None
    if "report_ref" in entry:
        report_path, report_digest = sources.resolve(
            profile_reference_owner,
            entry["report_ref"],
            f"{entry['card_id']}.report_ref",
        )
        report_projection = {
            "uri": _relative_path(report_path, repository_root),
            "sha256": report_digest,
        }
    study_projection, measurement_projection, measurement_set = _study_and_measurement_projection(
        receipt_path, receipt, sources
    )
    task_pack_roles = {
        str(task_pack["task_pack_id"]): str(task_pack["role"])
        for task_pack in study_projection["task_packs"]
    }
    run_projection, run_task_pack_roles = _run_projection(
        receipt_path,
        receipt,
        sources,
        task_pack_roles,
    )
    nonbaseline_intervention_classes = {
        str(condition["intervention_class"])
        for condition in study_projection["conditions"]
        if condition["role"] != "baseline"
    }
    selected_claims = _select_claim_records(
        receipt,
        list(entry["claim_ids"]),
        str(entry["card_id"]),
    )
    measurement_bindings = _measurement_evidence_bindings(measurement_set, run_task_pack_roles)
    claim_bindings, claim_binding_projection = _claim_evidence_bindings(
        receipt_path,
        selected_claims,
        measurement_bindings,
        sources,
    )
    support_context = ClaimSupportContext(
        evidence_state=str(receipt["evidence_level"]),
        comparison_mode=str(study_projection["comparison_mode"]),
        nonbaseline_intervention_classes=frozenset(nonbaseline_intervention_classes),
        independence_label=str(receipt["independence"]["label"]),
        evidence_by_ref=claim_bindings,
    )
    _admit_selected_claims(selected_claims, str(entry["card_id"]), support_context)
    selected_claims = [
        {
            **claim,
            "evidence_bindings": [
                claim_binding_projection[str(reference)] for reference in claim["evidence_refs"]
            ],
        }
        for claim in selected_claims
    ]
    decision_claim_ids = set(entry["decision_claim_ids"])
    selected_claims = [
        {**claim, "decision_governing": claim["claim_id"] in decision_claim_ids}
        for claim in selected_claims
    ]
    for claim in selected_claims:
        if not claim["decision_governing"] and claim["claim_level"] not in {
            "artifact",
            "workflow",
        }:
            _fail(
                f"additional claim {claim['claim_id']} for {entry['card_id']} must be an "
                "artifact or workflow disclosure; causal, transfer, and outcome claims "
                "must be decision-governing"
            )
    audit = _audit_projection(
        entry["verification"], profile_reference_owner, sources, require_git_proof
    )
    verification_projection: dict[str, Any] = {
        "kind": entry["verification"]["kind"],
        "command": list(entry["verification"]["command"]),
        "boundary": entry["verification"]["boundary"],
    }
    if audit is not None:
        verification_projection["audit"] = audit
    materials = _material_projection(entry["materials"], profile_reference_owner, sources)
    quality = _quality_projection(
        entry["quality"],
        receipt,
        profile_reference_owner,
        sources,
        str(profile["as_of"]),
    )
    reproduction = _reproduction_projection(entry, receipt)
    history = dict(entry["history"])
    lifecycle_projection: dict[str, Any] | None = None
    if "lifecycle" in entry:
        history, lifecycle_projection = _lifecycle_projection(
            entry["lifecycle"],
            profile_reference_owner,
            sources,
            str(profile["as_of"]),
        )
    receipt_ref_projection = {
        "uri": _relative_path(receipt_path, repository_root),
        "sha256": receipt_digest,
    }
    card: dict[str, Any] = {
        "card_id": entry["card_id"],
        "title": entry["title"],
        "catalog_state": entry["catalog_state"],
        "receipt": receipt_ref_projection,
        "decision": receipt["decision"],
        "evidence_level": receipt["evidence_level"],
        "receipt_reproducibility": receipt["reproducibility"],
        "reproduction": reproduction,
        "independence": receipt["independence"],
        "claims": selected_claims,
        "unsupported_inferences": receipt["unsupported_inferences"],
        "limitations": receipt["limitations"],
        "invalidation_triggers": receipt["invalidation_triggers"],
        "state": receipt["state"],
        "history": history,
        "quality": quality,
        "materials": materials,
        "verification": verification_projection,
        "source_hashes": sources.snapshot(),
        "receipt_id": receipt["receipt_id"],
        "study": study_projection,
        "runs": run_projection,
        "measurements": measurement_projection,
        "generator": {"name": GENERATOR_NAME, "version": GENERATOR_VERSION},
    }
    if lifecycle_projection is not None:
        card["lifecycle"] = lifecycle_projection
    if report_projection is not None:
        card["report"] = report_projection
    # Keep an explicit selected-ID field so a consumer can distinguish the
    # profile's selection from the full receipt claim set.
    card["claim_ids"] = list(entry["claim_ids"])
    card["decision_claim_ids"] = list(entry["decision_claim_ids"])
    return card, sources.snapshot()


def build_result_surface(
    profile_path: Path,
    repository_root: Path | None = None,
    require_git_proof: bool = False,
) -> dict[str, str]:
    """Build deterministic output bytes without writing any files."""

    profile_path = Path(profile_path).absolute()
    _regular_file(profile_path, "result-catalog profile")
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
