"""Pure admission policy for prospective Completion Integrity task supply.

This module validates task-quality facts supplied by a strict private-pack
adapter.  It performs no filesystem, runner, provider, publication, or Contract
I/O and does not alter the frozen alpha.9 study policy.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

TASK_SCHEMA_VERSION = "ael.completion-integrity-task-candidate/0.2-development"
PACK_SCHEMA_VERSION = "ael.completion-integrity-task-supply/0.2-development"
ASSESSMENT_SCHEMA_VERSION = "ael.completion-integrity-task-assessment/0.2-development"

FAMILIES = {
    "requirement_closure",
    "cross_boundary_coherence",
    "verification_integrity",
    "delivery_authority_integrity",
}
LIFECYCLE_STATES = {
    "authoring",
    "qualified",
    "role_assigned",
    "frozen",
    "retired",
}
STUDY_ROLES = {
    "none",
    "screening",
    "confirmation",
    "historical_regression",
}
SCORED_ROLES = {"screening", "confirmation"}
TRUTH_STATE_FAMILIES = {
    "already_resolved",
    "partial",
    "ordinary_incomplete",
    "uncertain",
    "legitimate_blocker",
    "false_blocker",
    "evaluator_sentinel",
}
FAILURE_SEVERITIES = {"low", "medium", "high", "critical"}
VERDICTS = {"complete", "incomplete", "uncertain"}
PROGRESS_STATES = {"continuable", "awaiting_clarification", "externally_blocked"}
MANDATORY_MUTANT_CLASSES = {
    "partial_omission",
    "narrow_overfit",
    "collateral_regression",
    "fabricated_authority",
    "reward_hack",
}
REQUIRED_ARTIFACT_KINDS = {
    "instruction",
    "fixture",
    "evaluator",
    "reference_solution",
    "alternative_solution",
    "mutant_set",
    "terminal_oracle",
    "evaluator_custody_receipt",
}

_IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9._:-]{2,127}$")
_SHA256 = re.compile(r"^[a-f0-9]{64}$")


def _identifier(value: object) -> bool:
    return isinstance(value, str) and bool(_IDENTIFIER.fullmatch(value))


def _nonblank(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _objects(value: object) -> list[Mapping[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(item, Mapping) for item in value):
        return []
    return list(value)


def _positive_int(value: object) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value > 0


def _probability(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
        and 0 < float(value) < 1
    )


def _proportion(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
        and 0 <= float(value) <= 1
    )


def _bounded_effect(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
        and 0 < float(value) <= 1
    )


def _at_least_one(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
        and float(value) >= 1.0
    )


def _truth_profile_issues(task_id: str, value: object, requirement_ids: Sequence[str]) -> list[str]:
    issues: list[str] = []
    if not isinstance(value, Mapping):
        return [f"{task_id}: truth_profile is required"]
    state_family = value.get("state_family")
    if not isinstance(state_family, str) or state_family not in TRUTH_STATE_FAMILIES:
        issues.append(f"{task_id}: truth_profile.state_family is invalid")
    severity = value.get("failure_severity")
    if not isinstance(severity, str) or severity not in FAILURE_SEVERITIES:
        issues.append(f"{task_id}: truth_profile.failure_severity is invalid")
    cases = _objects(value.get("terminal_cases"))
    if not cases:
        issues.append(f"{task_id}: truth_profile needs known-state terminal cases")
        return issues
    case_ids: list[str] = []
    verdicts: set[str] = set()
    for case in cases:
        case_id = case.get("case_id")
        if not _identifier(case_id):
            issues.append(f"{task_id}: terminal cases need stable case IDs")
        else:
            case_ids.append(str(case_id))
        verdict = case.get("verdict")
        progress = case.get("progress")
        if not isinstance(verdict, str) or verdict not in VERDICTS:
            issues.append(f"{task_id}: terminal case verdict is invalid")
        else:
            verdicts.add(verdict)
        if not isinstance(progress, str) or progress not in PROGRESS_STATES:
            issues.append(f"{task_id}: terminal case progress is invalid")
        extent = case.get("extent")
        if not isinstance(extent, Mapping) or set(extent) != {
            "verified",
            "failed",
            "unresolved",
        }:
            issues.append(f"{task_id}: terminal case extent must declare all three states")
            continue
        if any(
            isinstance(extent.get(state), bool)
            or not isinstance(extent.get(state), int)
            or int(extent.get(state, -1)) < 0
            for state in ("verified", "failed", "unresolved")
        ):
            issues.append(f"{task_id}: terminal case extent counts must be non-negative integers")
            continue
        requirement_states = case.get("requirement_states")
        if not isinstance(requirement_states, Mapping) or set(requirement_states) != set(
            requirement_ids
        ):
            issues.append(
                f"{task_id}: terminal case requirement_states must exactly cover requirements"
            )
            continue
        if any(
            not isinstance(state, str) or state not in {"verified", "failed", "unresolved"}
            for state in requirement_states.values()
        ):
            issues.append(f"{task_id}: terminal case requirement state is invalid")
            continue
        verified = int(extent["verified"])
        failed = int(extent["failed"])
        unresolved = int(extent["unresolved"])
        derived_extent = {
            state: sum(value == state for value in requirement_states.values())
            for state in ("verified", "failed", "unresolved")
        }
        if dict(extent) != derived_extent:
            issues.append(f"{task_id}: terminal case extent does not match requirement states")
        if verified + failed + unresolved < 1:
            issues.append(f"{task_id}: terminal case extent cannot be empty")
        if verdict == "complete" and (failed or unresolved or progress != "continuable"):
            issues.append(f"{task_id}: complete case must be fully verified and continuable")
        if verdict == "incomplete" and failed < 1:
            issues.append(f"{task_id}: incomplete case needs at least one failed predicate")
        if verdict == "uncertain" and (failed or unresolved < 1):
            issues.append(f"{task_id}: uncertain case needs unresolved and no failed predicates")
        if progress == "awaiting_clarification" and unresolved < 1:
            issues.append(f"{task_id}: awaiting clarification needs an unresolved predicate")
    if len(set(case_ids)) != len(case_ids):
        issues.append(f"{task_id}: terminal case IDs must be unique")
    if verdicts != VERDICTS:
        issues.append(
            f"{task_id}: terminal oracle must discriminate complete, incomplete, and uncertain"
        )
    if state_family == "legitimate_blocker" and not any(
        case.get("progress") == "externally_blocked" for case in cases
    ):
        issues.append(f"{task_id}: legitimate blocker task needs an externally blocked case")
    if state_family == "false_blocker" and not any(
        case.get("verdict") != "complete" and case.get("progress") == "continuable"
        for case in cases
    ):
        issues.append(f"{task_id}: false blocker task needs a continuable non-complete case")
    return issues


def _blocker_issues(task_id: str, state_family: object, value: object) -> list[str]:
    issues: list[str] = []
    if not isinstance(value, Mapping):
        return [f"{task_id}: blocker_feasibility is required"]
    adjudication = value.get("adjudication")
    if not isinstance(adjudication, str) or adjudication not in {
        "not_applicable",
        "legitimate_external",
        "in_scope_feasible",
    }:
        return [f"{task_id}: blocker_feasibility.adjudication is invalid"]
    if state_family == "legitimate_blocker" and adjudication != "legitimate_external":
        issues.append(f"{task_id}: legitimate blocker needs legitimate_external adjudication")
    if state_family == "false_blocker" and adjudication != "in_scope_feasible":
        issues.append(f"{task_id}: false blocker needs in_scope_feasible adjudication")
    if (
        not isinstance(state_family, str)
        or state_family not in {"legitimate_blocker", "false_blocker"}
    ) and adjudication != "not_applicable":
        issues.append(f"{task_id}: non-blocker task must use not_applicable adjudication")
    if adjudication == "not_applicable":
        if set(value) != {"adjudication"}:
            issues.append(f"{task_id}: not-applicable blocker adjudication has extra fields")
        return issues
    for field in ("dependency_owner_id", "prerequisite_id"):
        if not _identifier(value.get(field)):
            issues.append(f"{task_id}: blocker_feasibility.{field} must be a stable identifier")
    if not _nonblank(value.get("next_action")):
        issues.append(f"{task_id}: blocker_feasibility.next_action is required")
    evidence_refs = value.get("evidence_refs")
    if (
        not isinstance(evidence_refs, list)
        or not evidence_refs
        or any(not isinstance(item, str) or not _SHA256.fullmatch(item) for item in evidence_refs)
    ):
        issues.append(f"{task_id}: blocker feasibility needs SHA-bound evidence")
    exhausted = value.get("authorized_alternatives_exhausted")
    if adjudication == "legitimate_external" and exhausted is not True:
        issues.append(f"{task_id}: legitimate blocker must exhaust authorized alternatives")
    if adjudication == "in_scope_feasible" and exhausted is not False:
        issues.append(f"{task_id}: false blocker must preserve a feasible in-scope alternative")
    return issues


def _custody_issues(
    task_id: str,
    value: object,
    *,
    artifact_hashes: Mapping[object, object],
    scored: bool,
) -> list[str]:
    issues: list[str] = []
    if not isinstance(value, Mapping):
        return [f"{task_id}: evaluator_custody is required"]
    if not _identifier(value.get("custodian_id")):
        issues.append(f"{task_id}: evaluator_custody.custodian_id must be stable")
    evaluator_sha = value.get("evaluator_sha256")
    receipt_sha = value.get("receipt_sha256")
    if not isinstance(evaluator_sha, str) or not _SHA256.fullmatch(evaluator_sha):
        issues.append(f"{task_id}: evaluator_custody.evaluator_sha256 is invalid")
    elif artifact_hashes.get("evaluator") != evaluator_sha:
        issues.append(f"{task_id}: evaluator custody must bind the evaluator artifact")
    if not isinstance(receipt_sha, str) or not _SHA256.fullmatch(receipt_sha):
        issues.append(f"{task_id}: evaluator_custody.receipt_sha256 is invalid")
    elif artifact_hashes.get("evaluator_custody_receipt") != receipt_sha:
        issues.append(f"{task_id}: evaluator custody must bind its receipt artifact")
    if not isinstance(value.get("task_author_overlap"), bool):
        issues.append(f"{task_id}: evaluator custody must disclose task-author overlap")
    if value.get("reporter_pre_score_access") is not False:
        issues.append(f"{task_id}: reporter must not have pre-score evaluator access")
    access = value.get("qualification_access")
    if not isinstance(access, str) or access not in {
        "authoring_visible",
        "sealed_after_qualification",
    }:
        issues.append(f"{task_id}: evaluator_custody.qualification_access is invalid")
    if scored and access != "sealed_after_qualification":
        issues.append(f"{task_id}: scored evaluator must be sealed after qualification")
    return issues


def _task_issues(task: Mapping[str, Any]) -> list[str]:
    task_id = str(task.get("task_id", "<missing>"))
    issues: list[str] = []

    if task.get("schema_version") != TASK_SCHEMA_VERSION:
        issues.append(f"{task_id}: unsupported task schema")
    for field in ("task_id", "root_id", "lineage_group"):
        if not _identifier(task.get(field)):
            issues.append(f"{task_id}: {field} must be a stable identifier")
    if not _positive_int(task.get("revision")):
        issues.append(f"{task_id}: revision must be a positive integer")
    lifecycle_state = task.get("lifecycle_state")
    study_role = task.get("study_role")
    if not isinstance(lifecycle_state, str) or lifecycle_state not in LIFECYCLE_STATES:
        issues.append(f"{task_id}: unsupported lifecycle_state")
    if not isinstance(study_role, str) or study_role not in STUDY_ROLES:
        issues.append(f"{task_id}: unsupported study_role")
    scored_role = isinstance(study_role, str) and study_role in SCORED_ROLES
    if scored_role and lifecycle_state not in {"role_assigned", "frozen"}:
        issues.append(f"{task_id}: scored study role requires role_assigned or frozen lifecycle")
    if study_role == "none" and lifecycle_state in {"role_assigned", "frozen"}:
        issues.append(f"{task_id}: assigned/frozen lifecycle requires a study role")
    if not isinstance(task.get("family"), str) or task.get("family") not in FAMILIES:
        issues.append(f"{task_id}: unsupported Completion Integrity family")
    for field in ("stratum", "ecosystem"):
        if not _nonblank(task.get(field)):
            issues.append(f"{task_id}: {field} is required")

    truth_profile = task.get("truth_profile")
    state_family = truth_profile.get("state_family") if isinstance(truth_profile, Mapping) else None
    issues.extend(_blocker_issues(task_id, state_family, task.get("blocker_feasibility")))

    lineage = task.get("lineage")
    if not isinstance(lineage, Mapping):
        issues.append(f"{task_id}: lineage must be an object")
    else:
        for field in ("repository_graph_id", "acceptance_owner_id", "failure_mechanism_id"):
            if not _identifier(lineage.get(field)):
                issues.append(f"{task_id}: lineage.{field} must be a stable identifier")
        parents = lineage.get("parent_root_ids", [])
        if not isinstance(parents, list) or not all(_identifier(parent) for parent in parents):
            issues.append(f"{task_id}: lineage.parent_root_ids must contain stable identifiers")
        if task.get("root_id") in parents:
            issues.append(f"{task_id}: a root cannot descend from itself")

    requirements = _objects(task.get("requirements"))
    requirement_ids = [item.get("requirement_id") for item in requirements]
    if not requirements or any(not _identifier(value) for value in requirement_ids):
        issues.append(f"{task_id}: requirements need stable requirement IDs")
    valid_requirement_ids = [str(value) for value in requirement_ids if isinstance(value, str)]
    if len(set(valid_requirement_ids)) != len(requirement_ids):
        issues.append(f"{task_id}: requirement IDs must be unique")
    for requirement in requirements:
        if requirement.get("observability") not in {
            "instruction_explicit",
            "repository_inferable",
            "owner_surface_explicit",
        }:
            issues.append(f"{task_id}: every requirement needs an allowed observability class")
        if not _nonblank(requirement.get("evidence_locator")):
            issues.append(f"{task_id}: every requirement needs an evidence locator")
    issues.extend(_truth_profile_issues(task_id, truth_profile, valid_requirement_ids))

    oracle = task.get("oracle")
    if not isinstance(oracle, Mapping):
        issues.append(f"{task_id}: oracle evidence is required")
    else:
        oracle_ids = oracle.get("requirement_ids")
        if oracle_ids != requirement_ids:
            issues.append(f"{task_id}: oracle requirement coverage must exactly match requirements")

        valid_solutions = _objects(oracle.get("valid_solutions"))
        signatures = {
            solution.get("structural_signature")
            for solution in valid_solutions
            if solution.get("accepted") is True and _nonblank(solution.get("structural_signature"))
        }
        if len(valid_solutions) < 2 or len(signatures) < 2:
            issues.append(
                f"{task_id}: oracle must accept two structurally distinct valid solutions"
            )
        if any(solution.get("accepted") is not True for solution in valid_solutions):
            issues.append(f"{task_id}: every declared valid solution must be accepted")

        mutants = _objects(oracle.get("mutants"))
        classes = {
            str(mutant.get("class")) for mutant in mutants if isinstance(mutant.get("class"), str)
        }
        missing_classes = sorted(MANDATORY_MUTANT_CLASSES - classes)
        if missing_classes:
            issues.append(f"{task_id}: missing mandatory mutant classes {missing_classes}")
        mutant_ids = [
            str(mutant.get("mutant_id"))
            for mutant in mutants
            if isinstance(mutant.get("mutant_id"), str)
        ]
        if len(set(mutant_ids)) != len(mutants) or any(
            not _identifier(mutant.get("mutant_id")) for mutant in mutants
        ):
            issues.append(f"{task_id}: mutants need unique stable IDs")
        if any(
            mutant.get("rejected") is not True or mutant.get("operational_valid") is not True
            for mutant in mutants
        ):
            issues.append(
                f"{task_id}: every declared mutant must be operationally valid and rejected"
            )
        if not any(
            mutant.get("visible_checks_pass") is True
            and mutant.get("rejected") is True
            and mutant.get("class") in {"partial_omission", "narrow_overfit"}
            for mutant in mutants
        ):
            issues.append(f"{task_id}: no plausible green-check stopping trap is demonstrated")

        environment = oracle.get("environment_checks")
        if not isinstance(environment, Mapping):
            issues.append(f"{task_id}: environment checks are required")
        else:
            required_states = {
                "pristine_visible_pass": True,
                "pristine_accepted": False,
                "known_good_visible_pass": True,
                "known_good_accepted": True,
                "invalid_rejected": True,
            }
            for key, expected in required_states.items():
                if environment.get(key) is not expected:
                    issues.append(f"{task_id}: environment_checks.{key} must be {expected}")
            deterministic_repeats = environment.get("deterministic_repeats")
            if not _positive_int(deterministic_repeats) or deterministic_repeats < 2:
                issues.append(
                    f"{task_id}: at least two deterministic evaluator repeats are required"
                )

        differential = oracle.get("differential_probe")
        differential_status = (
            differential.get("status") if isinstance(differential, Mapping) else None
        )
        if (
            not isinstance(differential, Mapping)
            or not isinstance(differential_status, str)
            or differential_status not in {"passed", "not_applicable"}
        ):
            issues.append(f"{task_id}: differential probe needs passed/not_applicable status")
        elif differential.get("status") == "not_applicable" and not _nonblank(
            differential.get("reason")
        ):
            issues.append(f"{task_id}: not-applicable differential probe needs a reason")

    artifacts = _objects(task.get("artifacts"))
    artifact_kind_values = [
        str(artifact.get("kind")) for artifact in artifacts if isinstance(artifact.get("kind"), str)
    ]
    artifact_path_values = [
        str(artifact.get("path")) for artifact in artifacts if isinstance(artifact.get("path"), str)
    ]
    artifact_kinds = set(artifact_kind_values)
    if len(artifact_kinds) != len(artifacts):
        issues.append(f"{task_id}: artifact kinds must be unique and named")
    if len(set(artifact_path_values)) != len(artifacts):
        issues.append(f"{task_id}: artifact paths must be unique and named")
    missing_artifacts = sorted(REQUIRED_ARTIFACT_KINDS - artifact_kinds)
    if missing_artifacts:
        issues.append(f"{task_id}: missing bound artifact kinds {missing_artifacts}")
    for artifact in artifacts:
        if not _nonblank(artifact.get("path")) or not _SHA256.fullmatch(
            str(artifact.get("sha256", ""))
        ):
            issues.append(f"{task_id}: every artifact needs a safe path and SHA-256")

    qualification = task.get("qualification")
    if not isinstance(qualification, Mapping):
        issues.append(f"{task_id}: qualification record is required")
    else:
        status = qualification.get("status")
        if not isinstance(status, str) or status not in {"not_started", "passed", "failed"}:
            issues.append(f"{task_id}: qualification status is invalid")
        if scored_role:
            evidence_artifacts = {"qualification_receipt", "semantic_review_receipt"}
            missing_evidence = sorted(evidence_artifacts - artifact_kinds)
            if missing_evidence:
                issues.append(
                    f"{task_id}: scored role lacks qualification evidence {missing_evidence}"
                )
            if status != "passed":
                issues.append(f"{task_id}: scored roles require passed sacrificial qualification")
            if not _positive_int(qualification.get("sacrificial_attempts")):
                issues.append(f"{task_id}: scored roles require at least one sacrificial attempt")
            if qualification.get("adapted_after_last_attempt") is not False:
                issues.append(
                    f"{task_id}: scored revision was adapted after its last qualification"
                )
            review = qualification.get("semantic_review")
            if not isinstance(review, Mapping) or review.get("status") != "passed":
                issues.append(f"{task_id}: scored roles require a passed semantic review")
            elif not _identifier(review.get("reviewer_id")) or not isinstance(
                review.get("author_overlap"), bool
            ):
                issues.append(
                    f"{task_id}: semantic review must identify the reviewer and disclose overlap"
                )
            if qualification.get("task_revision") != task.get("revision"):
                issues.append(f"{task_id}: qualification must bind the exact task revision")
        if study_role == "confirmation" and qualification.get("used_for_adaptation") is not False:
            issues.append(f"{task_id}: confirmation root must remain untouched by adaptation")

    disclosure_state = task.get("disclosure_state")
    if not isinstance(disclosure_state, str) or disclosure_state not in {
        "private_active",
        "retired_public",
    }:
        issues.append(f"{task_id}: disclosure_state is invalid")
    artifact_hashes = {
        artifact.get("kind"): artifact.get("sha256")
        for artifact in artifacts
        if isinstance(artifact, Mapping)
    }
    issues.extend(
        _custody_issues(
            task_id,
            task.get("evaluator_custody"),
            artifact_hashes=artifact_hashes,
            scored=scored_role,
        )
    )
    if (
        isinstance(state_family, str)
        and state_family
        in {
            "legitimate_blocker",
            "false_blocker",
        }
        and ("blocker_adjudication_receipt" not in artifact_kinds)
    ):
        issues.append(f"{task_id}: blocker task lacks blocker_adjudication_receipt")

    if scored_role and task.get("disclosure_state") != "private_active":
        issues.append(f"{task_id}: active scored task bytes must remain private")

    return issues


def assess_task(task: Mapping[str, Any]) -> dict[str, Any]:
    """Return a deterministic non-compensating assessment for one task dossier."""

    issues = _task_issues(task)
    return {
        "schema_version": ASSESSMENT_SCHEMA_VERSION,
        "task_id": task.get("task_id"),
        "root_id": task.get("root_id"),
        "lifecycle_state": task.get("lifecycle_state"),
        "study_role": task.get("study_role"),
        "status": "pass" if not issues else "fail",
        "issues": issues,
    }


def _sample_size_issues(
    pack: Mapping[str, Any], stage: object
) -> tuple[list[str], int | None, int | None]:
    issues: list[str] = []
    plan = pack.get("sample_size_plan")
    if not isinstance(plan, Mapping):
        return ["sample_size_plan is required"], None, None
    status = plan.get("status")
    basis = plan.get("basis")
    if not isinstance(status, str) or status not in {"pending_pilot", "justified"}:
        issues.append("sample_size_plan.status must be pending_pilot or justified")
    if plan.get("independent_unit") != "task_root":
        issues.append("sample_size_plan.independent_unit must be task_root")
    if plan.get("clustering_unit") != "task_root":
        issues.append("sample_size_plan.clustering_unit must be task_root")
    for field in (
        "estimand_id",
        "endpoint_or_test_id",
        "allocation_id",
        "exclusion_policy_id",
        "stopping_rule_id",
    ):
        if not _identifier(plan.get(field)):
            issues.append(f"sample_size_plan.{field} must be a stable identifier")
    minimum = plan.get("minimum_scored_roots")
    target = plan.get("target_scored_roots")
    if not _positive_int(minimum):
        issues.append("sample_size_plan.minimum_scored_roots must be positive")
        minimum = None
    if not _positive_int(target):
        issues.append("sample_size_plan.target_scored_roots must be positive")
        target = None
    if isinstance(minimum, int) and isinstance(target, int) and target < minimum:
        issues.append("sample_size_plan target cannot be smaller than its minimum")

    calculation_ref = plan.get("calculation_ref")
    inputs = plan.get("inputs")
    if status == "pending_pilot":
        if basis != "pending_pilot":
            issues.append("pending sample-size plan must use pending_pilot basis")
        if calculation_ref is not None:
            issues.append("pending sample-size plan cannot claim a calculation_ref")
        if not isinstance(inputs, Mapping):
            issues.append("pending sample-size plan needs missing-inputs rationale")
        else:
            missing = inputs.get("missing")
            if (
                not isinstance(missing, list)
                or not missing
                or any(not _nonblank(item) for item in missing)
            ):
                issues.append("pending sample-size plan must name its missing inputs")
            if not _nonblank(inputs.get("reason")):
                issues.append("pending sample-size plan must explain why sizing is unresolved")
        if isinstance(stage, str) and stage in {"admission_ready", "frozen"}:
            issues.append("sample_size_pending blocks admission and scored freeze")
    elif status == "justified":
        if not isinstance(basis, str) or basis not in {"power", "precision"}:
            issues.append("justified sample-size plan must use power or precision basis")
        if not isinstance(calculation_ref, Mapping):
            issues.append("justified sample-size plan needs a calculation_ref")
        else:
            for field in ("calculation_id", "version"):
                if not _identifier(calculation_ref.get(field)):
                    issues.append(f"sample_size_plan.calculation_ref.{field} must be stable")
            if not isinstance(calculation_ref.get("sha256"), str) or not _SHA256.fullmatch(
                str(calculation_ref.get("sha256", ""))
            ):
                issues.append("sample_size_plan.calculation_ref.sha256 is invalid")
        if not isinstance(inputs, Mapping):
            issues.append("justified sample-size plan needs declared inputs")
        elif basis == "power":
            for field in ("alpha", "power"):
                if not _probability(inputs.get(field)):
                    issues.append(f"sample_size_plan.inputs.{field} must be between zero and one")
            if not _bounded_effect(inputs.get("minimum_useful_effect")):
                issues.append(
                    "sample_size_plan.inputs.minimum_useful_effect must be above zero and at most one"
                )
            if not _proportion(inputs.get("pilot_discordance")):
                issues.append(
                    "sample_size_plan.inputs.pilot_discordance must be between zero and one inclusive"
                )
            if not _at_least_one(inputs.get("design_effect")):
                issues.append("sample_size_plan.inputs.design_effect must be at least one")
        elif basis == "precision":
            for field in ("confidence_level",):
                if not _probability(inputs.get(field)):
                    issues.append(f"sample_size_plan.inputs.{field} must be between zero and one")
            if not _bounded_effect(inputs.get("target_interval_width")):
                issues.append(
                    "sample_size_plan.inputs.target_interval_width must be above zero and at most one"
                )
            if not _proportion(inputs.get("pilot_discordance")):
                issues.append(
                    "sample_size_plan.inputs.pilot_discordance must be between zero and one inclusive"
                )
            if not _at_least_one(inputs.get("design_effect")):
                issues.append("sample_size_plan.inputs.design_effect must be at least one")
    return issues, minimum, target


def assess_pack(pack: Mapping[str, Any], tasks: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Assess a task population without inventing task count or empirical quality."""

    issues: list[str] = []
    if pack.get("schema_version") != PACK_SCHEMA_VERSION:
        issues.append("unsupported task-supply schema")
    if not _identifier(pack.get("pack_id")):
        issues.append("pack_id must be a stable identifier")
    if not _positive_int(pack.get("revision")):
        issues.append("pack revision must be a positive integer")
    stage = pack.get("stage")
    if not isinstance(stage, str) or stage not in {
        "development",
        "qualification",
        "admission_ready",
        "frozen",
    }:
        issues.append("unsupported task-supply stage")

    sample_size_issues, minimum, target = _sample_size_issues(pack, stage)
    issues.extend(sample_size_issues)
    admission_stage = isinstance(stage, str) and stage in {"admission_ready", "frozen"}

    assessments = [assess_task(task) for task in tasks]
    for assessment in assessments:
        issues.extend(assessment["issues"])

    task_ids = [task.get("task_id") for task in tasks]
    root_ids = [task.get("root_id") for task in tasks]
    valid_task_ids = [str(value) for value in task_ids if isinstance(value, str)]
    valid_root_ids = [str(value) for value in root_ids if isinstance(value, str)]
    if len(set(valid_task_ids)) != len(task_ids):
        issues.append("task IDs must be unique")
    if len(set(valid_root_ids)) != len(root_ids):
        issues.append("task root IDs must be unique; variants and ports do not increase n")

    scored = [
        task
        for task in tasks
        if isinstance(task.get("study_role"), str) and task.get("study_role") in SCORED_ROLES
    ]
    scored_count = len(scored)
    role_counts = Counter(str(task.get("study_role")) for task in scored)
    expected_roles = pack.get("expected_scored_roles")
    if (
        not isinstance(expected_roles, Mapping)
        or set(expected_roles) != SCORED_ROLES
        or any(
            isinstance(expected_roles.get(role), bool)
            or not isinstance(expected_roles.get(role), int)
            or int(expected_roles.get(role, -1)) < 1
            for role in sorted(SCORED_ROLES)
        )
    ):
        issues.append(
            "expected_scored_roles must declare positive screening and confirmation counts"
        )
    else:
        planned_count = sum(int(expected_roles[role]) for role in SCORED_ROLES)
        if isinstance(minimum, int) and planned_count < minimum:
            issues.append("expected scored roles are below the sample-size-plan minimum")
        if isinstance(target, int) and planned_count > target:
            issues.append("expected scored roles exceed the sample-size-plan target")
        if admission_stage and role_counts != Counter(expected_roles):
            issues.append(
                f"scored role counts {dict(role_counts)} do not match frozen plan {dict(expected_roles)}"
            )

    if admission_stage:
        if isinstance(minimum, int) and scored_count < minimum:
            issues.append(
                f"only {scored_count} scored roots passed; minimum is {minimum}; padding is forbidden"
            )
        if isinstance(target, int) and scored_count > target:
            issues.append("scored roots exceed the frozen target; create a new pack revision")

        family_minimums = pack.get("family_minimums")
        if not isinstance(family_minimums, Mapping) or set(family_minimums) != FAMILIES:
            issues.append("family_minimums must cover the four Completion Integrity families")
        else:
            family_counts = Counter(str(task.get("family")) for task in scored)
            for family, required in family_minimums.items():
                if isinstance(required, bool) or not isinstance(required, int) or required < 1:
                    issues.append(f"family minimum for {family} must be positive")
                elif family_counts[family] < required:
                    issues.append(
                        f"family {family} has {family_counts[family]} roots; minimum is {required}"
                    )

        ecosystem_minimums = pack.get("ecosystem_minimums")
        if not isinstance(ecosystem_minimums, Mapping) or not ecosystem_minimums:
            issues.append("ecosystem_minimums are required for an admitted pack")
        else:
            ecosystem_counts = Counter(str(task.get("ecosystem")) for task in scored)
            for ecosystem, required in ecosystem_minimums.items():
                if isinstance(required, bool) or not isinstance(required, int) or required < 1:
                    issues.append(f"ecosystem minimum for {ecosystem} must be positive")
                elif ecosystem_counts[ecosystem] < required:
                    issues.append(
                        f"ecosystem {ecosystem} has {ecosystem_counts[ecosystem]} roots; "
                        f"minimum is {required}"
                    )

        for field in ("lineage_group",):
            values = [task.get(field) for task in scored]
            valid_values = [str(value) for value in values if isinstance(value, str)]
            if len(set(valid_values)) != len(values):
                issues.append(f"scored roots must not share {field}")
        for field in ("repository_graph_id", "acceptance_owner_id", "failure_mechanism_id"):
            values = [
                task.get("lineage", {}).get(field)
                for task in scored
                if isinstance(task.get("lineage"), Mapping)
            ]
            valid_values = [str(value) for value in values if isinstance(value, str)]
            if len(set(valid_values)) != len(values):
                issues.append(f"scored roots must not reuse lineage.{field}")

    return {
        "schema_version": ASSESSMENT_SCHEMA_VERSION,
        "pack_id": pack.get("pack_id"),
        "pack_revision": pack.get("revision"),
        "stage": stage,
        "sample_size_status": (
            pack.get("sample_size_plan", {}).get("status")
            if isinstance(pack.get("sample_size_plan"), Mapping)
            else None
        ),
        "sample_size_basis": (
            pack.get("sample_size_plan", {}).get("basis")
            if isinstance(pack.get("sample_size_plan"), Mapping)
            else None
        ),
        "status": "pass" if not issues else "fail",
        "candidate_roots": len(tasks),
        "scored_roots": scored_count,
        "role_counts": dict(sorted(role_counts.items())),
        "family_counts": dict(sorted(Counter(str(task.get("family")) for task in scored).items())),
        "ecosystem_counts": dict(
            sorted(Counter(str(task.get("ecosystem")) for task in scored).items())
        ),
        "issues": issues,
        "task_assessments": assessments,
        "count_rule": "independent task roots only; repeats, paraphrases, ports, and calibration do not increase n; pack-specific minimum and target require a bound sizing rationale",
    }
