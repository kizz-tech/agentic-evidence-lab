"""Pure policy kernel for AEL-CEP 0.2-development.

The module deliberately deals in already parsed JSON-like mappings.  It does
not read files, call a clock or random source, invoke providers, or import any
other AEL module.  The public functions return normalized copies and reject
ambiguous inputs rather than trying to repair them.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, NoReturn

PROTOCOL_SCHEMA_VERSION = "ael-cep-protocol-0.2-development"
BUNDLE_SCHEMA_VERSION = "ael-cep-bundle-0.2-development"
RECORD_SCHEMA_VERSION = "ael-cep-record-0.2-development"
CONTRAST_SUMMARY_AGGREGATION_VERSION = "ael-cep-stage0-contrast-summary/v1"
# Kept as a descriptive alias for callers that only consume the derived
# operating-metrics projection; the ledger seal itself is contrast_summary.
OPERATING_METRICS_AGGREGATION_VERSION = CONTRAST_SUMMARY_AGGREGATION_VERSION
CEP_PROTOCOL_VERSION = PROTOCOL_SCHEMA_VERSION
CEP_BUNDLE_VERSION = BUNDLE_SCHEMA_VERSION
CEP_RECORD_VERSION = RECORD_SCHEMA_VERSION

PROTOCOL_VERSION = PROTOCOL_SCHEMA_VERSION
BUNDLE_VERSION = BUNDLE_SCHEMA_VERSION
RECORD_VERSION = RECORD_SCHEMA_VERSION

RECORD_TYPES = frozenset(
    {
        "builder_release",
        "evaluator_release",
        "challenger_release",
        "anchor_release",
        "measurement_method",
        "evaluation_binding",
        "subject_execution_evidence",
        "score_run",
        "exposure_event",
        "confirmation_consumption",
        "anchor_observation",
        "effect_attempt",
        "bridge_observation",
        "comparability_decision",
        "independence_assessment",
        "promotion_transition",
        "trajectory_summary",
        "contrast_summary",
        "deletion_tombstone",
    }
)

_TRAJECTORY_DISPOSITION_KEYS = (
    "eligible",
    "quarantined",
    "revoked",
    "unscorable",
    "invalid",
    "missing",
)
_TRAJECTORY_PROMOTION_KEYS = ("useful", "null", "harmful", "adversarial")
_TRAJECTORY_BRIDGE_KEYS = ("attempted", "passed", "failed", "unknown", "later_reversal")
_TRAJECTORY_EXPLOIT_KEYS = ("candidates", "accepted")
_TRAJECTORY_REVOCATION_KEYS = ("declared_descendants", "complete_descendants")

REPLAY_CLASSES = frozenset(
    {"rescorable", "deterministic_replayable", "historical_only", "rerun_required"}
)

PROMOTION_STATES = (
    "registered",
    "development_eligible",
    "screening_pass",
    "screening_reject",
    "bridge_eligible",
    "new_measurement_epoch",
    "confirmation_eligible",
    "promote",
    "narrow",
    "abstain",
    "reject",
    "monitor",
    "expire",
    "revoke",
)

PROMOTION_TRANSITIONS = {
    "registered": frozenset({"development_eligible"}),
    # A tombstone may arrive after any candidate-stage decision.  The
    # authority-bound revoke transition is a containment terminal and is
    # validated separately against the exact tombstone dependency; it is not
    # a positive progression edge.
    "development_eligible": frozenset({"screening_pass", "screening_reject", "revoke"}),
    "screening_pass": frozenset({"bridge_eligible", "new_measurement_epoch", "revoke"}),
    "screening_reject": frozenset(),
    # A failed/non-comparable bridge is a terminal outcome for the current
    # measurement epoch, but it is still a prospective state transition.  It
    # must be representable after bridge_eligible rather than being inferred
    # from the earlier screening decision.
    "bridge_eligible": frozenset({"confirmation_eligible", "new_measurement_epoch", "revoke"}),
    "new_measurement_epoch": frozenset(),
    "confirmation_eligible": frozenset({"promote", "narrow", "abstain", "reject", "revoke"}),
    "promote": frozenset({"monitor", "expire", "revoke"}),
    "narrow": frozenset({"monitor", "expire", "revoke"}),
    "abstain": frozenset({"monitor", "expire", "revoke"}),
    "reject": frozenset({"monitor", "expire", "revoke"}),
    "monitor": frozenset({"expire", "revoke"}),
    "expire": frozenset(),
    "revoke": frozenset(),
}

_UNKNOWN = frozenset({"", "unknown", "unk", "unspecified", "undetermined", "tbd", "n/a", "na"})
_HEX = frozenset("0123456789abcdefABCDEF")


class CoevolutionError(ValueError):
    """A deterministic, reason-coded policy validation error."""

    def __init__(self, reason: str, detail: str = "") -> None:
        self.reason = reason
        message = reason if not detail else f"{reason}: {detail}"
        super().__init__(message)


def _error(reason: str, detail: str) -> NoReturn:
    raise CoevolutionError(reason, detail)


def _is_mapping(value: Any) -> bool:
    return isinstance(value, Mapping)


def _is_hash(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in _HEX for char in value)


def _require_hash(value: Any, path: str) -> str:
    if not _is_hash(value):
        _error("invalid_hash", f"{path} must be a lowercase/uppercase SHA-256 hex digest")
    return str(value)


def _require_string(value: Any, path: str, *, nonempty: bool = True) -> str:
    if not isinstance(value, str):
        _error("invalid_type", f"{path} must be a string")
    if nonempty and not value.strip():
        _error("blank_value", f"{path} must not be blank")
    return value


def _critical_string(value: Any, path: str) -> str:
    result = _require_string(value, path)
    if result.strip().casefold() in _UNKNOWN:
        _error("unknown_critical", f"{path} is blank or unknown")
    return result


def _require_bool(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        _error("invalid_type", f"{path} must be a boolean")
    return value


def _require_number(value: Any, path: str, *, nonnegative: bool = False) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _error("invalid_type", f"{path} must be a finite number")
    if isinstance(value, float) and not math.isfinite(value):
        _error("nonfinite", f"{path} must be finite")
    if nonnegative and value < 0:
        _error("invalid_value", f"{path} must be nonnegative")
    return value


def _strict_keys(value: Mapping[str, Any], allowed: Iterable[str], path: str) -> None:
    non_string = [key for key in value if not isinstance(key, str)]
    if non_string:
        _error("unsupported_type", f"{path} keys must be strings")
    unknown = sorted(set(value) - set(allowed))
    if unknown:
        _error("unknown_field", f"{path} contains unknown field(s): {', '.join(unknown)}")


def _clone_json(value: Any, path: str = "value") -> Any:
    """Validate and copy a JSON-like value without relying on a serializer round-trip."""

    if value is None or isinstance(value, (str, bool, int)):
        if isinstance(value, int) and not isinstance(value, bool):
            return int(value)
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            _error("nonfinite", f"{path} contains a non-finite number")
        return float(value)
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, child in value.items():
            if not isinstance(key, str):
                _error("unsupported_type", f"{path} mapping keys must be strings")
            result[key] = _clone_json(child, f"{path}.{key}")
        return result
    if isinstance(value, (list, tuple)):
        return [_clone_json(child, f"{path}[{index}]") for index, child in enumerate(value)]
    _error("unsupported_type", f"{path} contains unsupported value type {type(value).__name__}")


def canonical_json_bytes(value: Any, domain: str = "json") -> bytes:
    """Return deterministic UTF-8 bytes with explicit AEL-CEP domain separation."""

    if not isinstance(domain, str) or not domain or "\x00" in domain:
        _error("invalid_domain", "canonicalization domain must be a non-empty string without NUL")
    normalized = _clone_json(value)
    try:
        body = json.dumps(
            normalized,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        _error("canonicalization_error", str(exc))
    return f"AEL-CEP\x00{domain}\x00".encode() + body


def canonical_hash(value: Any, domain: str = "json") -> str:
    return hashlib.sha256(canonical_json_bytes(value, domain=domain)).hexdigest()


def canonical_sha256(value: Any, domain: str = "json") -> str:
    return canonical_hash(value, domain=domain)


def _nonblank(value: Any, path: str, *, critical: bool = False) -> Any:
    """Reject blank/unknown values recursively for frozen critical declarations."""

    if value is None:
        _error("unknown_critical", f"{path} is unknown") if critical else _error(
            "blank_value", f"{path} is null"
        )
    if isinstance(value, str):
        if not value.strip() or value.strip().casefold() in _UNKNOWN:
            _error("unknown_critical" if critical else "blank_value", f"{path} is blank or unknown")
        return value
    if isinstance(value, Mapping):
        if not value and critical:
            _error("unknown_critical", f"{path} is empty")
        if any(not isinstance(key, str) for key in value):
            _error("unsupported_type", f"{path} mapping keys must be strings")
        return {
            key: _nonblank(child, f"{path}.{key}", critical=critical)
            for key, child in value.items()
        }
    if isinstance(value, (list, tuple)):
        if not value and critical:
            _error("unknown_critical", f"{path} is empty")
        return [
            _nonblank(child, f"{path}[{index}]", critical=critical)
            for index, child in enumerate(value)
        ]
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return _require_number(value, path)
    _error("unsupported_type", f"{path} has unsupported type {type(value).__name__}")


def _algorithm(value: Any, path: str) -> dict[str, Any]:
    if not _is_mapping(value):
        _error("invalid_type", f"{path} must be an algorithm reference object")
    _strict_keys(value, {"ref", "hash"}, path)
    result = {
        "ref": _critical_string(value.get("ref"), f"{path}.ref"),
        "hash": _require_hash(value.get("hash"), f"{path}.hash"),
    }
    return result


def _principal(value: Any, path: str) -> dict[str, Any]:
    if not _is_mapping(value):
        _error("invalid_type", f"{path} must be a principal declaration")
    _strict_keys(value, {"principal_id", "custody", "independence", "lineage"}, path)
    result = {
        "principal_id": _critical_string(value.get("principal_id"), f"{path}.principal_id"),
        "custody": _critical_string(value.get("custody"), f"{path}.custody"),
        "independence": _critical_string(value.get("independence"), f"{path}.independence"),
    }
    if "lineage" in value:
        result["lineage"] = _nonblank(value["lineage"], f"{path}.lineage", critical=True)
    return result


def _validate_partitions(value: Any) -> dict[str, Any]:
    if not _is_mapping(value):
        _error("invalid_type", "partitions must be an object")
    expected = ("development", "screening", "bridge", "confirmation", "historical")
    if set(value) != set(expected):
        _error(
            "partition_set",
            "partitions must contain exactly development, screening, bridge, confirmation, historical",
        )
    result: dict[str, Any] = {}
    allowed = {
        "partition_id",
        "purpose",
        "feedback",
        "sealed",
        "single_use",
        "eligible_for_promotion",
        "exposure_budget",
        "task_root_hash",
    }
    for name in expected:
        item = value[name]
        if not _is_mapping(item):
            _error("invalid_type", f"partitions.{name} must be an object")
        _strict_keys(item, allowed, f"partitions.{name}")
        descriptor = {
            "partition_id": _require_string(
                item.get("partition_id"), f"partitions.{name}.partition_id"
            ),
            "purpose": _require_string(item.get("purpose"), f"partitions.{name}.purpose"),
            "feedback": _require_string(item.get("feedback"), f"partitions.{name}.feedback"),
            "sealed": _require_bool(item.get("sealed"), f"partitions.{name}.sealed"),
            "single_use": _require_bool(item.get("single_use"), f"partitions.{name}.single_use"),
            "eligible_for_promotion": _require_bool(
                item.get("eligible_for_promotion"), f"partitions.{name}.eligible_for_promotion"
            ),
            "exposure_budget": _require_number(
                item.get("exposure_budget"), f"partitions.{name}.exposure_budget", nonnegative=True
            ),
            "task_root_hash": _require_hash(
                item.get("task_root_hash"), f"partitions.{name}.task_root_hash"
            ),
        }
        if descriptor["partition_id"] != name:
            _error("partition_identity", f"partitions.{name}.partition_id must equal {name}")
        result[name] = descriptor
    confirmation = result["confirmation"]
    if (
        not confirmation["single_use"]
        or not confirmation["sealed"]
        or not confirmation["eligible_for_promotion"]
    ):
        _error(
            "confirmation_policy", "confirmation must be sealed, single-use, and promotion-eligible"
        )
    for name in ("development", "screening", "bridge", "historical"):
        if result[name]["eligible_for_promotion"]:
            _error(
                "partition_policy",
                f"{name} partition cannot be promotion-eligible",
            )
    if result["historical"]["eligible_for_promotion"]:
        _error("partition_policy", "historical partition cannot be promotion-eligible")
    task_roots = [result[name]["task_root_hash"] for name in expected]
    if len(set(task_roots)) != len(task_roots):
        _error(
            "partition_identity",
            "Stage 0 partition task roots must be pairwise distinct to prevent feedback leakage",
        )
    return result


_REQUIRED_BRIDGE_STRATA = frozenset({"good", "bad", "exploit", "semantic_mutant", "near_threshold"})


def _validate_strata(value: Any, path: str) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        _error("strata_policy", f"{path} must be a non-empty array")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    total_weight = 0.0
    for index, item in enumerate(value):
        item_path = f"{path}[{index}]"
        if not _is_mapping(item):
            _error("strata_policy", f"{item_path} must be an object")
        _strict_keys(item, {"stratum", "weight", "task_root_hash"}, item_path)
        if set(item) != {"stratum", "weight", "task_root_hash"}:
            _error(
                "strata_policy",
                f"{item_path} must declare exactly stratum, weight, task_root_hash",
            )
        name = _critical_string(item.get("stratum"), f"{item_path}.stratum")
        if name in seen:
            _error("strata_policy", f"{path} contains duplicate stratum {name}")
        weight = _require_number(item.get("weight"), f"{item_path}.weight", nonnegative=True)
        if weight <= 0:
            _error("strata_policy", f"{item_path}.weight must be positive")
        task_root_hash = _require_hash(item.get("task_root_hash"), f"{item_path}.task_root_hash")
        seen.add(name)
        total_weight += float(weight)
        result.append({"stratum": name, "weight": weight, "task_root_hash": task_root_hash})
    if seen != _REQUIRED_BRIDGE_STRATA:
        _error(
            "strata_policy",
            "protocol.bridge.strata must be exactly good, bad, exploit, semantic_mutant, near_threshold",
        )
    if not math.isclose(total_weight, 1.0, rel_tol=0.0, abs_tol=1e-12):
        _error("strata_policy", f"{path} weights must sum to 1")
    task_roots = [item["task_root_hash"] for item in result]
    if len(set(task_roots)) != len(task_roots):
        _error("strata_policy", f"{path} task_root_hash values must be distinct")
    result.sort(key=lambda item: item["stratum"])
    return result


_ARM_EXPECTATIONS = {
    "A0": {
        "builder": "fixed",
        "evaluator": "fixed",
        "loop": "open",
        "custody": "shared",
        "challenger": "absent",
        "anchor": "absent",
    },
    "A1": {
        "builder": "evolving",
        "evaluator": "fixed",
        "loop": "open",
        "custody": "shared",
        "challenger": "absent",
        "anchor": "absent",
    },
    "A2": {
        "builder": "fixed",
        "evaluator": "evolving",
        "loop": "open",
        "custody": "shared",
        "challenger": "absent",
        "anchor": "absent",
    },
    "A3": {
        "builder": "evolving",
        "evaluator": "evolving",
        "loop": "naive_closed",
        "custody": "shared",
        "challenger": "absent",
        "anchor": "absent",
    },
    "A4": {
        "builder": "evolving",
        "evaluator": "evolving",
        "loop": "custody_separated",
        "custody": "separated",
        "challenger": "absent",
        "anchor": "protected",
    },
    "A5": {
        "builder": "evolving",
        "evaluator": "evolving",
        "loop": "challenger_anchor",
        "custody": "separated",
        "challenger": "present",
        "anchor": "protected",
    },
}


def _validate_arms(value: Any) -> dict[str, Any]:
    if not _is_mapping(value) or set(value) != set(_ARM_EXPECTATIONS):
        _error("arm_set", "arms must contain exactly A0, A1, A2, A3, A4, A5")
    result = {}
    fields = {"builder", "evaluator", "loop", "custody", "challenger", "anchor"}
    for arm, expected in _ARM_EXPECTATIONS.items():
        item = value[arm]
        if not _is_mapping(item):
            _error("invalid_type", f"arms.{arm} must be an object")
        _strict_keys(item, fields, f"arms.{arm}")
        normalized = {key: _require_string(item.get(key), f"arms.{arm}.{key}") for key in fields}
        if normalized != expected:
            _error("arm_definition", f"arms.{arm} does not match the frozen A0-A5 research meaning")
        result[arm] = normalized
    return result


def _validate_treatment(value: Any, path: str) -> dict[str, Any]:
    if not _is_mapping(value):
        _error("invalid_type", f"{path} must declare exactly one treatment dimension")
    _strict_keys(value, {"dimension", "arm_a_level", "arm_b_level"}, path)
    return {
        "dimension": _require_string(value.get("dimension"), f"{path}.dimension"),
        "arm_a_level": _require_string(value.get("arm_a_level"), f"{path}.arm_a_level"),
        "arm_b_level": _require_string(value.get("arm_b_level"), f"{path}.arm_b_level"),
    }


def _validate_contrasts(
    value: Any, algorithms: Mapping[str, Any], budgets: Mapping[str, Any]
) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        _error("contrast_set", "contrasts must be a non-empty array")
    result = []
    allowed = {
        "contrast_id",
        "arm_a",
        "arm_b",
        "treatment",
        "estimand_kind",
        "eligibility",
        "task_allocation",
        "proposal_admission",
        "selection_ranking",
        "stopping",
        "analysis",
        "promotion",
        "budgets",
    }
    for index, item in enumerate(value):
        path = f"contrasts[{index}]"
        if not _is_mapping(item):
            _error("invalid_type", f"{path} must be an object")
        _strict_keys(item, allowed, path)
        arm_a = _require_string(item.get("arm_a"), f"{path}.arm_a")
        arm_b = _require_string(item.get("arm_b"), f"{path}.arm_b")
        if arm_a == arm_b:
            _error("contrast_arms", f"{path} must compare distinct arms")
        if arm_a not in _ARM_EXPECTATIONS or arm_b not in _ARM_EXPECTATIONS:
            _error("contrast_arms", f"{path} arm identities must be one of A0-A5")
        treatment = _validate_treatment(item.get("treatment"), f"{path}.treatment")
        estimand_kind = _require_string(item.get("estimand_kind"), f"{path}.estimand_kind")
        if estimand_kind not in {"component", "policy_package"}:
            _error("contrast_estimand", f"{path}.estimand_kind must be component or policy_package")
        treatment_dimension = treatment["dimension"]
        dimension_to_arm_field = {
            "builder": "builder",
            "evaluator": "evaluator",
            "loop": "loop",
            "custody": "custody",
            "challenger": "challenger",
            "anchor": "anchor",
            "role_evolution": "loop",
        }
        if estimand_kind == "policy_package":
            if treatment_dimension != "policy_package":
                _error(
                    "contrast_estimand",
                    f"{path} policy_package treatment must use dimension policy_package",
                )
            arm_field = None
        elif treatment_dimension not in dimension_to_arm_field:
            _error(
                "contrast_treatment",
                f"{path}.treatment.dimension must name one declared arm treatment",
            )
        else:
            arm_field = dimension_to_arm_field[treatment_dimension]
        differing_fields = [
            field
            for field in _ARM_EXPECTATIONS[arm_a]
            if _ARM_EXPECTATIONS[arm_a][field] != _ARM_EXPECTATIONS[arm_b][field]
        ]
        if estimand_kind == "component" and (
            len(differing_fields) != 1 or differing_fields[0] != arm_field
        ):
            _error(
                "contrast_treatment",
                f"{path} must differ in exactly its declared treatment dimension",
            )
        if estimand_kind == "component":
            expected_levels = (
                _ARM_EXPECTATIONS[arm_a][arm_field],
                _ARM_EXPECTATIONS[arm_b][arm_field],
            )
            if (treatment["arm_a_level"], treatment["arm_b_level"]) != expected_levels:
                _error(
                    "contrast_treatment",
                    f"{path}.treatment arm levels must match the frozen arm identities",
                )
        if estimand_kind == "policy_package" and not differing_fields:
            _error(
                "contrast_treatment", f"{path} policy package must compare distinct arm policies"
            )
        if estimand_kind == "policy_package" and (
            treatment["arm_a_level"] != arm_a or treatment["arm_b_level"] != arm_b
        ):
            _error(
                "contrast_treatment",
                f"{path}.treatment policy-package levels must identify the compared arms",
            )
        contrast_algorithms = {}
        for key in (
            "eligibility",
            "task_allocation",
            "proposal_admission",
            "selection_ranking",
            "stopping",
            "analysis",
            "promotion",
        ):
            contrast_algorithms[key] = _algorithm(item.get(key), f"{path}.{key}")
        # Every decision-bearing algorithm is frozen and matched across arms.
        for key in (
            "eligibility",
            "task_allocation",
            "proposal_admission",
            "selection_ranking",
            "stopping",
            "analysis",
            "promotion",
        ):
            global_key = key
            if contrast_algorithms[key] != algorithms[global_key]:
                _error(
                    "contrast_algorithm_mismatch",
                    f"{path}.{key} must equal algorithms.{global_key}",
                )
        contrast_budgets = item.get("budgets")
        if not _is_mapping(contrast_budgets):
            _error("invalid_type", f"{path}.budgets must be an object")
        normalized_budgets = {
            key: _require_number(val, f"{path}.budgets.{key}", nonnegative=True)
            for key, val in contrast_budgets.items()
        }
        if set(normalized_budgets) != set(budgets):
            _error(
                "contrast_budget_mismatch",
                f"{path}.budgets must use the frozen total-system budget keys",
            )
        if treatment_dimension in budgets:
            _error(
                "contrast_treatment",
                f"{path}.treatment.dimension cannot exempt a total-system budget",
            )
        mismatched = [key for key in budgets if normalized_budgets[key] != budgets[key]]
        if mismatched:
            _error(
                "contrast_budget_mismatch",
                f"{path}.budgets differs outside treatment dimension: {', '.join(sorted(mismatched))}",
            )
        result.append(
            {
                "contrast_id": _require_string(item.get("contrast_id"), f"{path}.contrast_id"),
                "arm_a": arm_a,
                "arm_b": arm_b,
                "treatment": treatment,
                "estimand_kind": estimand_kind,
                "eligibility": contrast_algorithms["eligibility"],
                "task_allocation": contrast_algorithms["task_allocation"],
                "proposal_admission": contrast_algorithms["proposal_admission"],
                "selection_ranking": contrast_algorithms["selection_ranking"],
                "stopping": contrast_algorithms["stopping"],
                "analysis": contrast_algorithms["analysis"],
                "promotion": contrast_algorithms["promotion"],
                "budgets": normalized_budgets,
            }
        )
    ids = [item["contrast_id"] for item in result]
    if len(ids) != len(set(ids)):
        _error("duplicate_id", "contrasts contain duplicate contrast_id values")
    return result


_PROTOCOL_FIELDS = {
    "schema_version",
    "protocol_id",
    "epoch",
    "principals",
    "intake",
    "partitions",
    "arms",
    "contrasts",
    "algorithms",
    "budgets",
    "feedback_exposure",
    "missingness",
    "stopping",
    "bridge",
    "decision_rule",
    "replay",
    "independence",
    "promotion",
    "effect_policy",
    "simulation",
}


def validate_protocol(protocol: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and return a normalized, immutable-by-convention protocol copy."""

    if not _is_mapping(protocol):
        _error("invalid_type", "protocol must be an object")
    _strict_keys(protocol, _PROTOCOL_FIELDS, "protocol")
    if protocol.get("schema_version") != PROTOCOL_SCHEMA_VERSION:
        _error("schema_version", f"protocol.schema_version must be {PROTOCOL_SCHEMA_VERSION}")
    protocol_id = _require_string(protocol.get("protocol_id"), "protocol.protocol_id")

    epoch = protocol.get("epoch")
    if not _is_mapping(epoch):
        _error("invalid_type", "protocol.epoch must be an object")
    _strict_keys(
        epoch, {"epoch_id", "state", "constitution_ref", "constitution_hash"}, "protocol.epoch"
    )
    normalized_epoch = {
        "epoch_id": _require_string(epoch.get("epoch_id"), "protocol.epoch.epoch_id"),
        "state": _require_string(epoch.get("state"), "protocol.epoch.state"),
        "constitution_ref": _require_string(
            epoch.get("constitution_ref"), "protocol.epoch.constitution_ref"
        ),
        "constitution_hash": _require_hash(
            epoch.get("constitution_hash"), "protocol.epoch.constitution_hash"
        ),
    }
    if normalized_epoch["state"] not in {"frozen", "development"}:
        _error("epoch_state", "protocol.epoch.state must be frozen or development")

    principals = protocol.get("principals")
    if not _is_mapping(principals):
        _error("invalid_type", "protocol.principals must be an object")
    principal_names = ("evidence", "confirmation", "anchor", "adjudication", "promotion")
    if set(principals) != set(principal_names):
        _error(
            "principal_set",
            "principals must declare evidence, confirmation, anchor, adjudication, promotion",
        )
    normalized_principals = {
        name: _principal(principals[name], f"protocol.principals.{name}")
        for name in principal_names
    }
    protected_principal_statuses = {
        "separate",
        "independent",
        "disjoint",
        "protected",
        "pass",
    }
    for name, principal in normalized_principals.items():
        if principal["independence"].casefold() not in protected_principal_statuses:
            _error(
                "principal_independence",
                f"protocol.principals.{name}.independence must declare protected separation",
            )
    ids = [item["principal_id"] for item in normalized_principals.values()]
    if len(set(ids)) != len(ids):
        _error(
            "principal_identity",
            "evidence, confirmation, anchor, adjudication, and promotion principals must be distinct",
        )
    custody_labels = [item["custody"] for item in normalized_principals.values()]
    if len(set(custody_labels)) != len(custody_labels):
        _error(
            "principal_custody",
            "frozen principals must declare distinct custody labels",
        )
    principal_roles = list(normalized_principals)
    for left_index, left_role in enumerate(principal_roles):
        left_labels = {
            normalized_principals[left_role]["principal_id"],
            normalized_principals[left_role]["custody"],
        }
        for right_role in principal_roles[left_index + 1 :]:
            right_labels = {
                normalized_principals[right_role]["principal_id"],
                normalized_principals[right_role]["custody"],
            }
            if left_labels & right_labels:
                _error(
                    "principal_boundary",
                    f"frozen principal labels for {left_role} and {right_role} must be disjoint",
                )

    intake = protocol.get("intake")
    if not _is_mapping(intake):
        _error("invalid_type", "protocol.intake must be an object")
    intake_fields = {
        "target_population",
        "use",
        "intake_owner",
        "sampling_custodian",
        "sampling_frame",
        "sampling_method",
        "sampling_window",
        "sampling_cutoff",
        "eligibility",
        "deduplication",
        "censoring_late_arrival",
        "oracle",
        "adjudication",
        "appeal",
        "utility",
        "harms",
        "weights",
        "margins",
        "arm_blinding",
        "allocation_proof",
        "exposure_policy",
    }
    _strict_keys(intake, intake_fields, "protocol.intake")
    if set(intake) != intake_fields:
        missing = sorted(intake_fields - set(intake))
        _error(
            "incomplete_intake", f"protocol.intake missing critical field(s): {', '.join(missing)}"
        )
    normalized_intake = {
        key: _nonblank(intake[key], f"protocol.intake.{key}", critical=True)
        for key in sorted(intake_fields)
    }

    partitions = _validate_partitions(protocol.get("partitions"))
    arms = _validate_arms(protocol.get("arms"))

    algorithms = protocol.get("algorithms")
    if not _is_mapping(algorithms):
        _error("invalid_type", "protocol.algorithms must be an object")
    _strict_keys(
        algorithms,
        {
            "eligibility",
            "task_allocation",
            "proposal_admission",
            "selection_ranking",
            "stopping",
            "analysis",
            "promotion",
        },
        "protocol.algorithms",
    )
    for key in (
        "eligibility",
        "task_allocation",
        "proposal_admission",
        "selection_ranking",
        "stopping",
        "analysis",
        "promotion",
    ):
        if key not in algorithms:
            _error("missing_field", f"protocol.algorithms.{key} is required")
    normalized_algorithms = {
        key: _algorithm(algorithms[key], f"protocol.algorithms.{key}") for key in algorithms
    }

    budgets = protocol.get("budgets")
    if not _is_mapping(budgets):
        _error("invalid_type", "protocol.budgets must be an object")
    _strict_keys(
        budgets, {"total_system", "feedback", "exposure", "confirmation"}, "protocol.budgets"
    )
    budget_keys = {"total_system", "feedback", "exposure", "confirmation"}
    if set(budgets) != budget_keys:
        _error(
            "budget_set",
            "protocol.budgets must declare total_system, feedback, exposure, confirmation",
        )
    normalized_budgets = {
        key: _require_number(budgets[key], f"protocol.budgets.{key}", nonnegative=True)
        for key in sorted(budgets)
    }

    contrasts = _validate_contrasts(
        protocol.get("contrasts"), normalized_algorithms, normalized_budgets
    )

    def object_fields(
        name: str, allowed: set[str], required: set[str] | None = None
    ) -> dict[str, Any]:
        item = protocol.get(name)
        if not _is_mapping(item):
            _error("invalid_type", f"protocol.{name} must be an object")
        _strict_keys(item, allowed, f"protocol.{name}")
        if required and set(item) != required:
            _error(
                "field_set", f"protocol.{name} must declare exactly: {', '.join(sorted(required))}"
            )
        return {key: _nonblank(item[key], f"protocol.{name}.{key}", critical=True) for key in item}

    feedback_exposure = object_fields(
        "feedback_exposure",
        {"development", "screening", "bridge", "confirmation", "total"},
        {"development", "screening", "bridge", "confirmation", "total"},
    )
    missingness = object_fields(
        "missingness",
        {"policy", "bounds", "critical_failure_rule"},
        {"policy", "bounds", "critical_failure_rule"},
    )
    stopping = object_fields(
        "stopping",
        {"algorithm_ref", "algorithm_hash", "rule", "max_looks", "missing_data"},
        {"algorithm_ref", "algorithm_hash", "rule", "max_looks", "missing_data"},
    )
    if (
        stopping["algorithm_ref"] != normalized_algorithms["stopping"]["ref"]
        or stopping["algorithm_hash"] != normalized_algorithms["stopping"]["hash"]
    ):
        _error("stopping_mismatch", "protocol.stopping must bind algorithms.stopping exactly")
    if (
        not isinstance(stopping["max_looks"], int)
        or isinstance(stopping["max_looks"], bool)
        or stopping["max_looks"] < 0
    ):
        _error("stopping_policy", "protocol.stopping.max_looks must be a nonnegative integer")
    bridge = object_fields(
        "bridge",
        {
            "global_shift_tolerance",
            "interaction_tolerance",
            "decision_agreement_min",
            "construct_required",
            "reliability_required",
            "anchor_required",
            "strata",
        },
        {
            "global_shift_tolerance",
            "interaction_tolerance",
            "decision_agreement_min",
            "construct_required",
            "reliability_required",
            "anchor_required",
            "strata",
        },
    )
    replay = object_fields(
        "replay",
        {"retention_policy", "required_surfaces", "deterministic_code_policy"},
        {"retention_policy", "required_surfaces", "deterministic_code_policy"},
    )
    independence = object_fields(
        "independence", {"protected_dimensions", "ceiling"}, {"protected_dimensions", "ceiling"}
    )
    promotion_raw = protocol.get("promotion")
    if not _is_mapping(promotion_raw):
        _error("invalid_type", "protocol.promotion must be an object")
    _strict_keys(
        promotion_raw,
        {"initial_state", "transition_table", "terminal_states"},
        "protocol.promotion",
    )
    if set(promotion_raw) != {"initial_state", "transition_table", "terminal_states"}:
        _error(
            "field_set",
            "protocol.promotion must declare exactly: initial_state, terminal_states, transition_table",
        )
    promotion_initial = _critical_string(
        promotion_raw.get("initial_state"), "protocol.promotion.initial_state"
    )
    if promotion_initial != "registered":
        _error("promotion_state", "protocol.promotion.initial_state must be registered")
    transition_table_raw = promotion_raw.get("transition_table")
    if not _is_mapping(transition_table_raw):
        _error("promotion_table", "protocol.promotion.transition_table must be an object")
    if set(transition_table_raw) != set(PROMOTION_STATES):
        _error(
            "promotion_table",
            "protocol.promotion.transition_table must declare every frozen promotion state",
        )
    normalized_transition_table: dict[str, list[str]] = {}
    for state in PROMOTION_STATES:
        outgoing = transition_table_raw[state]
        if not isinstance(outgoing, Sequence) or isinstance(outgoing, (str, bytes)):
            _error(
                "promotion_table",
                f"protocol.promotion.transition_table.{state} must be an array",
            )
        normalized_outgoing = [
            _critical_string(
                target,
                f"protocol.promotion.transition_table.{state}[{index}]",
            )
            for index, target in enumerate(outgoing)
        ]
        if len(normalized_outgoing) != len(set(normalized_outgoing)):
            _error(
                "promotion_table",
                f"protocol.promotion.transition_table.{state} contains duplicate transitions",
            )
        expected_outgoing = sorted(PROMOTION_TRANSITIONS[state])
        if sorted(normalized_outgoing) != expected_outgoing:
            _error(
                "promotion_table",
                f"protocol.promotion.transition_table.{state} does not match the code-owned transition table",
            )
        normalized_transition_table[state] = expected_outgoing
    terminal_states_raw = promotion_raw.get("terminal_states")
    if (
        not isinstance(terminal_states_raw, Sequence)
        or isinstance(terminal_states_raw, (str, bytes))
        or not terminal_states_raw
    ):
        _error("promotion_policy", "protocol.promotion.terminal_states must be a non-empty array")
    terminal_states = [
        _critical_string(item, f"protocol.promotion.terminal_states[{index}]")
        for index, item in enumerate(terminal_states_raw)
    ]
    if len(terminal_states) != len(set(terminal_states)):
        _error("promotion_policy", "protocol.promotion.terminal_states contains duplicates")
    expected_terminal_states = [
        state for state in PROMOTION_STATES if not PROMOTION_TRANSITIONS[state]
    ]
    if terminal_states != expected_terminal_states:
        _error(
            "promotion_policy",
            "protocol.promotion.terminal_states must list exactly the states with no outgoing transitions",
        )
    promotion = {
        "initial_state": promotion_initial,
        "transition_table": normalized_transition_table,
        "terminal_states": terminal_states,
    }
    simulation = object_fields(
        "simulation",
        {"config_version", "seed", "scenarios"},
        {"config_version", "seed", "scenarios"},
    )
    if (
        not isinstance(simulation["seed"], int)
        or isinstance(simulation["seed"], bool)
        or simulation["seed"] < 0
    ):
        _error("simulation_seed", "protocol.simulation.seed must be a nonnegative integer")
    scenarios_raw = simulation["scenarios"]
    if (
        not isinstance(scenarios_raw, Sequence)
        or isinstance(scenarios_raw, (str, bytes))
        or not scenarios_raw
        or len(scenarios_raw) > 64
    ):
        _error(
            "simulation_scenarios",
            "protocol.simulation.scenarios must contain 1..64 scenario objects",
        )
    normalized_scenarios: list[dict[str, Any]] = []
    scenario_names: set[str] = set()
    for index, scenario in enumerate(scenarios_raw):
        path = f"protocol.simulation.scenarios[{index}]"
        if not _is_mapping(scenario):
            _error("simulation_scenarios", f"{path} must be an object")
        _strict_keys(scenario, {"name", "tasks", "replicates"}, path)
        name = _critical_string(scenario.get("name"), f"{path}.name")
        if name in scenario_names:
            _error("simulation_scenarios", f"{path}.name is duplicated")
        scenario_names.add(name)
        tasks = scenario.get("tasks")
        replicates = scenario.get("replicates")
        if isinstance(tasks, bool) or not isinstance(tasks, int) or not 1 <= tasks <= 1024:
            _error("simulation_scenarios", f"{path}.tasks must be an integer in 1..1024")
        if (
            isinstance(replicates, bool)
            or not isinstance(replicates, int)
            or not 1 <= replicates <= 256
        ):
            _error("simulation_scenarios", f"{path}.replicates must be an integer in 1..256")
        normalized_scenarios.append(
            {"name": name, "tasks": int(tasks), "replicates": int(replicates)}
        )
    simulation["scenarios"] = normalized_scenarios
    effect_policy = protocol.get("effect_policy")
    if effect_policy != "forbidden":
        _error("effect_policy", "protocol.effect_policy must be forbidden in Stage 0")
    for key in ("global_shift_tolerance", "interaction_tolerance"):
        bridge[key] = _require_number(bridge[key], f"protocol.bridge.{key}", nonnegative=True)
    bridge["decision_agreement_min"] = _require_number(
        bridge["decision_agreement_min"], "protocol.bridge.decision_agreement_min", nonnegative=True
    )
    if bridge["decision_agreement_min"] > 1:
        _error("bridge_tolerance", "protocol.bridge.decision_agreement_min must be at most 1")
    for key in ("construct_required", "reliability_required", "anchor_required"):
        bridge[key] = _require_bool(bridge[key], f"protocol.bridge.{key}")
        if bridge[key] is not True:
            _error("bridge_policy", f"protocol.bridge.{key} must be true in Stage 0")
    bridge["strata"] = _validate_strata(bridge["strata"], "protocol.bridge.strata")
    partition_roots = {item["task_root_hash"] for item in partitions.values()}
    if partition_roots & {item["task_root_hash"] for item in bridge["strata"]}:
        _error(
            "strata_policy",
            "protocol.bridge.strata task roots must be distinct from partition task roots",
        )
    decision_rule_raw = protocol.get("decision_rule")
    if decision_rule_raw is None:
        _error("missing_field", "protocol.decision_rule is required")
    if not _is_mapping(decision_rule_raw):
        _error("invalid_type", "protocol.decision_rule must be an object")
    _strict_keys(
        decision_rule_raw,
        {
            "threshold",
            "operator",
            "value_range",
            "required_status",
            "outcome",
            "critical_failure",
        },
        "protocol.decision_rule",
    )
    if set(decision_rule_raw) != {
        "threshold",
        "operator",
        "value_range",
        "required_status",
        "outcome",
        "critical_failure",
    }:
        _error(
            "field_set",
            "protocol.decision_rule must declare exactly threshold, operator, value_range, required_status, outcome, critical_failure",
        )
    decision_rule = {
        "threshold": _require_number(
            decision_rule_raw["threshold"],
            "protocol.decision_rule.threshold",
        ),
        "operator": _require_string(
            decision_rule_raw["operator"],
            "protocol.decision_rule.operator",
        ),
        "value_range": [],
        "required_status": _require_string(
            decision_rule_raw["required_status"],
            "protocol.decision_rule.required_status",
        ),
        "outcome": _nonblank(
            decision_rule_raw["outcome"],
            "protocol.decision_rule.outcome",
            critical=True,
        ),
        "critical_failure": _require_string(
            decision_rule_raw["critical_failure"],
            "protocol.decision_rule.critical_failure",
        ),
    }
    value_range = decision_rule_raw["value_range"]
    if (
        not isinstance(value_range, Sequence)
        or isinstance(value_range, (str, bytes))
        or len(value_range) != 2
    ):
        _error("decision_rule", "protocol.decision_rule.value_range must be a two-element range")
    decision_rule["value_range"] = [
        _require_number(value_range[0], "protocol.decision_rule.value_range[0]"),
        _require_number(value_range[1], "protocol.decision_rule.value_range[1]"),
    ]
    if decision_rule["value_range"][0] > decision_rule["value_range"][1]:
        _error("decision_rule", "protocol.decision_rule.value_range lower bound exceeds upper")
    if decision_rule["value_range"] != [0.0, 1.0]:
        _error("decision_rule", "protocol.decision_rule.value_range must be exactly [0, 1]")
    if not 0 <= decision_rule["threshold"] <= 1:
        _error("decision_rule", "protocol.decision_rule.threshold must be between 0 and 1")
    if decision_rule["operator"] != "gte":
        _error("decision_rule", "protocol.decision_rule.operator must be gte")
    if decision_rule["required_status"] != "observed":
        _error("decision_rule", "protocol.decision_rule.required_status must be observed")
    if decision_rule["critical_failure"] != "block":
        _error("decision_rule", "protocol.decision_rule.critical_failure must be block")
    if not (
        decision_rule["value_range"][0]
        <= decision_rule["threshold"]
        <= decision_rule["value_range"][1]
    ):
        _error("decision_rule", "protocol.decision_rule.threshold must be within value_range")
    if (
        not isinstance(replay["required_surfaces"], Sequence)
        or isinstance(replay["required_surfaces"], (str, bytes))
        or not replay["required_surfaces"]
    ):
        _error("surface_policy", "protocol.replay.required_surfaces must be a non-empty array")
    replay["required_surfaces"] = [
        _require_string(item, f"protocol.replay.required_surfaces[{index}]")
        for index, item in enumerate(replay["required_surfaces"])
    ]
    if (
        not isinstance(independence["protected_dimensions"], Sequence)
        or isinstance(independence["protected_dimensions"], (str, bytes))
        or not independence["protected_dimensions"]
    ):
        _error(
            "independence_policy",
            "protocol.independence.protected_dimensions must be a non-empty array",
        )
    independence["protected_dimensions"] = [
        _require_string(item, f"protocol.independence.protected_dimensions[{index}]")
        for index, item in enumerate(independence["protected_dimensions"])
    ]
    if (
        not isinstance(promotion["terminal_states"], Sequence)
        or isinstance(promotion["terminal_states"], (str, bytes))
        or not promotion["terminal_states"]
    ):
        _error("promotion_policy", "protocol.promotion.terminal_states must be a non-empty array")
    promotion["terminal_states"] = [
        _require_string(item, f"protocol.promotion.terminal_states[{index}]")
        for index, item in enumerate(promotion["terminal_states"])
    ]

    return {
        "schema_version": PROTOCOL_SCHEMA_VERSION,
        "protocol_id": protocol_id,
        "epoch": normalized_epoch,
        "principals": normalized_principals,
        "intake": normalized_intake,
        "partitions": partitions,
        "arms": arms,
        "contrasts": contrasts,
        "algorithms": normalized_algorithms,
        "budgets": normalized_budgets,
        "feedback_exposure": feedback_exposure,
        "missingness": missingness,
        "stopping": stopping,
        "bridge": bridge,
        "decision_rule": decision_rule,
        "replay": replay,
        "independence": independence,
        "promotion": promotion,
        "effect_policy": effect_policy,
        "simulation": simulation,
    }


def freeze_protocol(protocol: Mapping[str, Any]) -> dict[str, Any]:
    result = validate_protocol(protocol)
    if result["epoch"]["state"] != "frozen":
        _error("epoch_state", "protocol must be frozen before ledger use")
    return result


def protocol_hash(protocol: Mapping[str, Any]) -> str:
    return canonical_hash(validate_protocol(protocol), domain="ael-cep-protocol")


def _dependency_list(value: Any, path: str) -> list[dict[str, str]]:
    if isinstance(value, Mapping):
        items = [{"record_id": key, "record_hash": val} for key, val in value.items()]
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        items = list(value)
    else:
        _error("invalid_type", f"{path} must be a mapping or dependency array")
    result = []
    seen: set[str] = set()
    for index, item in enumerate(items):
        if not _is_mapping(item):
            _error("invalid_type", f"{path}[{index}] must be an object")
        _strict_keys(item, {"record_id", "record_hash"}, f"{path}[{index}]")
        record_id = _require_string(item.get("record_id"), f"{path}[{index}].record_id")
        if record_id in seen:
            _error("duplicate_id", f"{path} contains duplicate dependency {record_id}")
        seen.add(record_id)
        result.append(
            {
                "record_id": record_id,
                "record_hash": _require_hash(
                    item.get("record_hash"), f"{path}[{index}].record_hash"
                ),
            }
        )
    result.sort(key=lambda item: item["record_id"])
    return result


_COMMON_RELEASE = {
    "release_id",
    "release_kind",
    "revision",
    "artifact_hash",
    "lineage",
    "parent_release_ref",
    "parent_release_hash",
    "custody",
    "allowed_evidence_surface",
    "changes",
    "self_certification",
}
_EVALUATOR_RELEASE = _COMMON_RELEASE | {
    "implementation",
    "prompt_or_rubric",
    "model",
    "parser_or_aggregation",
    "tools_or_environment",
    "calibration_lineage",
    "known_error_envelope",
}


def _nonnegative_count(value: Any, path: str) -> int:
    """Validate one trajectory aggregation counter.

    Python's ``bool`` is an ``int`` subclass; explicitly rejecting it here is
    important because a boolean summary flag must never masquerade as a count.
    """

    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        _error("summary_counts", f"{path} must be a nonnegative integer")
    return int(value)


def _validate_primary_endpoint(value: Any, path: str) -> dict[str, int]:
    if not _is_mapping(value):
        _error("summary_endpoint", f"{path} must be an object")
    expected = {"sum_ppm", "observed_count"}
    _strict_keys(value, expected, path)
    if set(value) != expected:
        _error("summary_endpoint", f"{path} must declare sum_ppm and observed_count")
    sum_ppm = _nonnegative_count(value["sum_ppm"], f"{path}.sum_ppm")
    observed_count = _nonnegative_count(value["observed_count"], f"{path}.observed_count")
    if sum_ppm > observed_count * 1_000_000:
        _error("summary_endpoint", f"{path}.sum_ppm exceeds observed_count * 1e6")
    return {"sum_ppm": sum_ppm, "observed_count": observed_count}


def _validate_trajectory_counts(
    value: Any,
    path: str,
    *,
    scenario: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Normalize closed trajectory counters and enforce row denominators."""

    if not _is_mapping(value):
        _error("summary_counts", f"{path} must be an object")
    expected = {
        "disposition",
        "promotion",
        "candidate_opportunities",
        "exploit",
        "critical_failures",
        "bridge",
        "tainted",
        "revocation",
        "optional_stopping",
    }
    _strict_keys(value, expected, path)
    if set(value) != expected:
        _error(
            "summary_counts",
            f"{path} must declare exactly: {', '.join(sorted(expected))}",
        )

    def nested(name: str, keys: Sequence[str]) -> dict[str, int]:
        nested_value = value[name]
        nested_path = f"{path}.{name}"
        if not _is_mapping(nested_value):
            _error("summary_counts", f"{nested_path} must be an object")
        _strict_keys(nested_value, keys, nested_path)
        if set(nested_value) != set(keys):
            _error(
                "summary_counts",
                f"{nested_path} must declare exactly: {', '.join(keys)}",
            )
        return {key: _nonnegative_count(nested_value[key], f"{nested_path}.{key}") for key in keys}

    disposition = nested("disposition", _TRAJECTORY_DISPOSITION_KEYS)
    promotion = nested("promotion", _TRAJECTORY_PROMOTION_KEYS)
    candidate_opportunities = nested("candidate_opportunities", _TRAJECTORY_PROMOTION_KEYS)
    exploit = nested("exploit", _TRAJECTORY_EXPLOIT_KEYS)
    bridge = nested("bridge", _TRAJECTORY_BRIDGE_KEYS)
    revocation = nested("revocation", _TRAJECTORY_REVOCATION_KEYS)
    optional_stopping = nested("optional_stopping", ("events", "eligible_replicates"))
    critical_failures = _nonnegative_count(value["critical_failures"], f"{path}.critical_failures")
    tainted = _nonnegative_count(value["tainted"], f"{path}.tainted")

    attempted = sum(disposition.values())
    if bridge["attempted"] != bridge["passed"] + bridge["failed"] + bridge["unknown"]:
        _error("summary_counts", f"{path}.bridge.attempted must equal passed + failed + unknown")
    if bridge["later_reversal"] > bridge["passed"]:
        _error("summary_counts", f"{path}.bridge.later_reversal cannot exceed passed")
    if exploit["candidates"] > attempted:
        _error("summary_counts", f"{path}.exploit.candidates cannot exceed attempted units")
    if exploit["accepted"] > exploit["candidates"]:
        _error("summary_counts", f"{path}.exploit.accepted cannot exceed candidates")
    if critical_failures > disposition["unscorable"]:
        _error("summary_counts", f"{path}.critical_failures cannot exceed unscorable units")
    if tainted > disposition["quarantined"]:
        _error("summary_counts", f"{path}.tainted cannot exceed quarantined units")
    if revocation["complete_descendants"] > revocation["declared_descendants"]:
        _error(
            "summary_counts",
            f"{path}.revocation.complete_descendants cannot exceed declared_descendants",
        )
    if sum(candidate_opportunities.values()) < sum(promotion.values()):
        _error(
            "summary_counts", f"{path}.promotion categories cannot exceed candidate opportunities"
        )
    for key in _TRAJECTORY_PROMOTION_KEYS:
        if promotion[key] > candidate_opportunities[key]:
            _error(
                "summary_counts",
                f"{path}.promotion.{key} cannot exceed candidate_opportunities.{key}",
            )
    if scenario is not None:
        tasks = int(scenario["tasks"])
        replicates = int(scenario["replicates"])
        if sum(candidate_opportunities.values()) != replicates:
            _error(
                "summary_denominator",
                f"{path}.candidate_opportunities must sum to scenario replicates",
            )
        if attempted > tasks * replicates:
            _error("summary_denominator", f"{path}.disposition exceeds tasks * replicates")
        optional = scenario["name"] == "optional_stopping"
        expected_eligible = replicates if optional else 0
        if optional_stopping["eligible_replicates"] != expected_eligible:
            _error(
                "summary_optional_stopping",
                f"{path}.optional_stopping.eligible_replicates does not match scenario policy",
            )
        if not optional and attempted != tasks * replicates:
            _error(
                "summary_denominator",
                f"{path}.disposition must equal tasks * replicates for non-optional scenarios",
            )
    if optional_stopping["events"] > optional_stopping["eligible_replicates"]:
        _error(
            "summary_optional_stopping",
            f"{path}.optional_stopping.events exceeds eligible_replicates",
        )
    return {
        "disposition": disposition,
        "promotion": promotion,
        "candidate_opportunities": candidate_opportunities,
        "exploit": exploit,
        "critical_failures": critical_failures,
        "bridge": bridge,
        "tainted": tainted,
        "revocation": revocation,
        "optional_stopping": optional_stopping,
    }


def _validate_trajectory_budget(value: Any, path: str) -> dict[str, int | float]:
    if not _is_mapping(value):
        _error("summary_budget", f"{path} must be an object")
    _strict_keys(value, {"target", "actual", "delta"}, path)
    if set(value) != {"target", "actual", "delta"}:
        _error("summary_budget", f"{path} must declare target, actual, delta")
    target = _require_number(value["target"], f"{path}.target", nonnegative=True)
    actual = _require_number(value["actual"], f"{path}.actual", nonnegative=True)
    delta = _require_number(value["delta"], f"{path}.delta")
    if not math.isclose(delta, actual - target, rel_tol=0.0, abs_tol=1e-12):
        _error("summary_budget", f"{path}.delta must equal actual - target")
    return {"target": target, "actual": actual, "delta": delta}


def _round_rate(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    # Integer half-up rounding avoids binary-float and platform-dependent
    # formatting differences while retaining exactly six decimal places.
    scaled = (numerator * 1_000_000 * 2 + denominator) // (2 * denominator)
    return scaled / 1_000_000


def derive_operating_metrics(
    summaries: Mapping[str, Any] | Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, int | float | None]]:
    """Derive the Stage 0 operating rates from validated count inputs.

    ``summaries`` may be one trajectory payload/counts object or a sequence of
    them.  Counts are summed before rates are calculated, so a small trajectory
    cannot be overweighted merely by having a separate summary record.
    """

    if _is_mapping(summaries):
        rows: list[Mapping[str, Any]] = [summaries]
    elif isinstance(summaries, Sequence) and not isinstance(summaries, (str, bytes)):
        rows = list(summaries)
    else:
        _error("summary_counts", "operating metric input must be a mapping or array")
    if not rows:
        rows = []
    aggregate = {
        "disposition": {key: 0 for key in _TRAJECTORY_DISPOSITION_KEYS},
        "promotion": {key: 0 for key in _TRAJECTORY_PROMOTION_KEYS},
        "candidate_opportunities": {key: 0 for key in _TRAJECTORY_PROMOTION_KEYS},
        "exploit": {key: 0 for key in _TRAJECTORY_EXPLOIT_KEYS},
        "critical_failures": 0,
        "bridge": {key: 0 for key in _TRAJECTORY_BRIDGE_KEYS},
        "tainted": 0,
        "revocation": {key: 0 for key in _TRAJECTORY_REVOCATION_KEYS},
        "optional_stopping": {"events": 0, "eligible_replicates": 0},
    }
    for index, row in enumerate(rows):
        if not _is_mapping(row):
            _error("summary_counts", f"operating metric row {index} must be an object")
        count_value = row.get("counts", row)
        counts = _validate_trajectory_counts(count_value, f"operating_metrics[{index}]")
        for group in (
            "disposition",
            "promotion",
            "candidate_opportunities",
            "exploit",
            "bridge",
            "revocation",
            "optional_stopping",
        ):
            for key, value in counts[group].items():
                aggregate[group][key] += value
        for key in ("critical_failures", "tainted"):
            aggregate[key] += counts[key]
    disposition_total = sum(aggregate["disposition"].values())
    promotion_total = sum(aggregate["promotion"].values())
    false_numerator = (
        aggregate["promotion"]["null"]
        + aggregate["promotion"]["harmful"]
        + aggregate["promotion"]["adversarial"]
    )
    metrics: dict[str, tuple[int, int]] = {
        "false_promotion_share": (
            false_numerator,
            promotion_total,
        ),
        "invalid_candidate_promotion_rate": (
            false_numerator,
            aggregate["candidate_opportunities"]["null"]
            + aggregate["candidate_opportunities"]["harmful"]
            + aggregate["candidate_opportunities"]["adversarial"],
        ),
        "useful_candidate_power": (
            aggregate["promotion"]["useful"],
            aggregate["candidate_opportunities"]["useful"],
        ),
        "exploit_acceptance": (
            aggregate["exploit"]["accepted"],
            aggregate["exploit"]["candidates"],
        ),
        "critical_failure": (
            aggregate["critical_failures"],
            disposition_total,
        ),
        "bridge_reversal": (
            aggregate["bridge"]["later_reversal"],
            aggregate["bridge"]["passed"],
        ),
        "taint": (
            aggregate["tainted"],
            disposition_total,
        ),
        "missingness": (
            aggregate["disposition"]["missing"],
            disposition_total,
        ),
        "quarantine": (
            aggregate["disposition"]["quarantined"],
            disposition_total,
        ),
        "revocation_completeness": (
            aggregate["revocation"]["complete_descendants"],
            aggregate["revocation"]["declared_descendants"],
        ),
        "optional_stopping": (
            aggregate["optional_stopping"]["events"],
            aggregate["optional_stopping"]["eligible_replicates"],
        ),
    }
    return {
        name: {
            "count": count,
            "denominator": denominator,
            "rate": _round_rate(count, denominator),
        }
        for name, (count, denominator) in metrics.items()
    }


def _summary_row_payload(row: Mapping[str, Any]) -> Mapping[str, Any]:
    if row.get("record_type") == "trajectory_summary" and _is_mapping(row.get("payload")):
        return row["payload"]
    return row


def _normalize_summary_rows(
    protocol: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    frozen = freeze_protocol(protocol)
    scenarios = _frozen_scenarios_by_ref(frozen)
    normalized: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for index, row in enumerate(rows):
        if not _is_mapping(row):
            _error("summary_rows", f"rows[{index}] must be an object")
        payload = _summary_row_payload(row)
        if not _is_mapping(payload):
            _error("summary_rows", f"rows[{index}].payload must be an object")
        arm = _critical_string(payload.get("arm"), f"rows[{index}].arm")
        scenario_ref = _critical_string(payload.get("scenario_ref"), f"rows[{index}].scenario_ref")
        if arm not in frozen["arms"]:
            _error("summary_arm", f"rows[{index}] arm is not frozen")
        scenario = scenarios.get(scenario_ref)
        if scenario is None:
            _error("summary_scenario", f"rows[{index}] scenario_ref is not frozen")
        key = (arm, scenario_ref)
        if key in seen:
            _error("summary_duplicate", f"rows[{index}] duplicates arm/scenario")
        seen.add(key)
        counts = _validate_trajectory_counts(
            payload.get("counts"), f"rows[{index}].counts", scenario=scenario
        )
        endpoint = _validate_primary_endpoint(
            payload.get("primary_endpoint"), f"rows[{index}].primary_endpoint"
        )
        if endpoint["observed_count"] > sum(counts["disposition"].values()):
            _error("summary_endpoint", f"rows[{index}].primary_endpoint exceeds disposition total")
        budget = _validate_trajectory_budget(payload.get("budget"), f"rows[{index}].budget")
        if not math.isclose(
            budget["target"], frozen["budgets"]["total_system"], rel_tol=0.0, abs_tol=1e-12
        ):
            _error(
                "summary_budget",
                f"rows[{index}] budget target differs from frozen total-system budget",
            )
        normalized.append(
            {
                "arm": arm,
                "scenario_ref": scenario_ref,
                "counts": counts,
                "primary_endpoint": endpoint,
                "budget": budget,
            }
        )
    return normalized


def derive_arm_primary_endpoints(
    protocol: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, int | None]]:
    """Aggregate each arm's primary endpoint with an integer ppm mean."""

    normalized = _normalize_summary_rows(protocol, rows)
    totals = {arm: {"sum_ppm": 0, "observed_count": 0} for arm in freeze_protocol(protocol)["arms"]}
    for row in normalized:
        totals[row["arm"]]["sum_ppm"] += row["primary_endpoint"]["sum_ppm"]
        totals[row["arm"]]["observed_count"] += row["primary_endpoint"]["observed_count"]
    return {
        arm: {
            "sum_ppm": total["sum_ppm"],
            "observed_count": total["observed_count"],
            "mean_ppm": (
                None
                if total["observed_count"] == 0
                else (total["sum_ppm"] * 2 + total["observed_count"])
                // (2 * total["observed_count"])
            ),
        }
        for arm, total in sorted(totals.items())
    }


def derive_contrast_diagnostics(
    protocol: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Derive frozen contrast status and signed endpoint deltas."""

    frozen = freeze_protocol(protocol)
    normalized = _normalize_summary_rows(frozen, rows)
    endpoints = derive_arm_primary_endpoints(frozen, rows)
    by_pair = {(row["arm"], row["scenario_ref"]): row for row in normalized}
    scenarios = _frozen_scenarios_by_ref(frozen)
    diagnostics: list[dict[str, Any]] = []
    for contrast in sorted(frozen["contrasts"], key=lambda item: item["contrast_id"]):
        arm_a = contrast["arm_a"]
        arm_b = contrast["arm_b"]
        endpoint_a = endpoints.get(arm_a, {}).get("mean_ppm")
        endpoint_b = endpoints.get(arm_b, {}).get("mean_ppm")
        endpoint_delta = (
            None if endpoint_a is None or endpoint_b is None else endpoint_a - endpoint_b
        )
        compared_rows = [row for row in normalized if row["arm"] in {arm_a, arm_b}]
        # Endpoint means are only causal when every frozen arm×scenario row
        # contributes the protocol-declared task count.  Aggregating a
        # partially observed row into an arm-level mean would silently change
        # the estimand (and can even flip the contrast sign), so missingness
        # takes precedence over optional stopping and cost diagnostics.
        missing_endpoint = any(
            row["primary_endpoint"]["observed_count"]
            != int(scenarios[row["scenario_ref"]]["tasks"])
            * int(scenarios[row["scenario_ref"]]["replicates"])
            for row in compared_rows
        )
        optional_stopping = any(
            row["counts"]["optional_stopping"]["eligible_replicates"] > 0
            or row["counts"]["optional_stopping"]["events"] > 0
            for row in compared_rows
        )
        actual_cost_mismatch = any(
            row["budget"]["actual"] != row["budget"]["target"] for row in compared_rows
        )
        scenario_refs = {row["scenario_ref"] for row in compared_rows}
        for scenario_ref in scenario_refs:
            row_a = by_pair.get((arm_a, scenario_ref))
            row_b = by_pair.get((arm_b, scenario_ref))
            if (
                row_a is not None
                and row_b is not None
                and row_a["budget"]["actual"] != row_b["budget"]["actual"]
            ):
                actual_cost_mismatch = True
        if missing_endpoint or endpoint_delta is None:
            status = "not_estimable"
            reason: str | None = "missing_endpoint"
            endpoint_delta = None
        elif optional_stopping:
            status = "diagnostic_only"
            reason = "optional_stopping"
        elif actual_cost_mismatch:
            status = "diagnostic_only"
            reason = "actual_cost_mismatch"
        else:
            status = "causal_eligible"
            reason = None
        diagnostics.append(
            {
                "contrast_id": contrast["contrast_id"],
                "status": status,
                "reason": reason,
                "endpoint_delta_ppm": endpoint_delta,
            }
        )
    return diagnostics


# Explicit names used by downstream adapters and reports.
derive_primary_endpoints = derive_arm_primary_endpoints
derive_contrast_summary = derive_contrast_diagnostics


def _frozen_scenario_refs(frozen: Mapping[str, Any]) -> set[str]:
    refs: set[str] = set()
    for scenario in frozen["simulation"]["scenarios"]:
        name = scenario.get("name") if _is_mapping(scenario) else scenario
        if not isinstance(name, str) or not name.strip():
            _error("simulation_mismatch", "frozen simulation scenario lacks a stable name")
        refs.add(f"scenario:{name}")
    return refs


def _frozen_scenarios_by_ref(frozen: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for scenario in frozen["simulation"]["scenarios"]:
        if not _is_mapping(scenario):
            _error("simulation_mismatch", "frozen simulation scenario must be an object")
        name = scenario.get("name")
        if not isinstance(name, str) or not name.strip():
            _error("simulation_mismatch", "frozen simulation scenario lacks a stable name")
        result[f"scenario:{name}"] = scenario
    return result


_PAYLOAD_FIELDS: dict[str, set[str]] = {
    "builder_release": _COMMON_RELEASE,
    "challenger_release": _COMMON_RELEASE,
    "anchor_release": _COMMON_RELEASE | {"adjudication_protocol"},
    "evaluator_release": _EVALUATOR_RELEASE,
    "measurement_method": {
        "method_id",
        "revision",
        "artifact_hash",
        "construct",
        "oracle",
        "parser",
        "aggregation",
        "validity",
        "reliability",
        "custody",
    },
    "evaluation_binding": {
        "binding_id",
        "builder_release_ref",
        "builder_release_hash",
        "evaluator_release_ref",
        "evaluator_release_hash",
        "method_ref",
        "method_hash",
        "evidence_ref",
        "evidence_hash",
        "task_partition",
        "task_ref",
        "task_hash",
        "exposure_policy",
        "analysis_ref",
        "analysis_hash",
        "environment_ref",
        "environment_hash",
        "runner_ref",
        "runner_hash",
        "promotion_policy_ref",
        "promotion_policy_hash",
        "exposure_state_ref",
        "exposure_state_hash",
        "allowed_evidence_surface",
    },
    "subject_execution_evidence": {
        "evidence_id",
        "subject_ref",
        "builder_release_ref",
        "builder_release_hash",
        "task_partition",
        "task_ref",
        "task_hash",
        "environment_ref",
        "environment_hash",
        "runner_ref",
        "runner_hash",
        "exposure_state_ref",
        "exposure_state_hash",
        "partition",
        "surface_refs",
        "artifact_hash",
        "status",
        "tainted",
    },
    "score_run": {
        "score_run_id",
        "binding_ref",
        "binding_hash",
        "evidence_ref",
        "evidence_hash",
        "evaluator_release_ref",
        "evaluator_release_hash",
        "builder_release_ref",
        "builder_release_hash",
        "method_ref",
        "method_hash",
        "score",
        "score_status",
        "scoring_actor",
        "partition",
        "surface_refs",
        "critical_failure",
        "score_key",
        "exposure_policy",
    },
    "exposure_event": {
        "exposure_id",
        "target_ref",
        "target_hash",
        "partition",
        "exposure_kind",
        "amount",
        "tainted",
    },
    "confirmation_consumption": {
        "consumption_id",
        "partition",
        "confirmation_ref",
        "confirmation_hash",
        "candidate_ref",
        "candidate_hash",
        "authority",
        "consumed",
    },
    "anchor_observation": {
        "anchor_observation_id",
        "candidate_ref",
        "candidate_hash",
        "anchor_release_ref",
        "anchor_release_hash",
        "evidence_ref",
        "evidence_hash",
        "confirmation_consumption_ref",
        "confirmation_consumption_hash",
        "partition",
        "authority",
        "arm_blinded",
        "outcome",
        "value",
        "critical_failure",
        "status",
    },
    "effect_attempt": {
        "effect_attempt_id",
        "candidate_ref",
        "candidate_hash",
        "evidence_ref",
        "evidence_hash",
        "binding_ref",
        "binding_hash",
        "partition",
        "observation_authority",
        "effect_request_hash",
        "idempotency_key_hash",
        "disposition",
        "postcondition_status",
        "receipt_ref",
        "receipt_hash",
        "reason_code",
    },
    "bridge_observation": {
        "bridge_id",
        "old_builder_ref",
        "old_builder_hash",
        "new_builder_ref",
        "new_builder_hash",
        "old_evaluator_ref",
        "old_evaluator_hash",
        "new_evaluator_ref",
        "new_evaluator_hash",
        "old_evidence_ref",
        "old_evidence_hash",
        "new_evidence_ref",
        "new_evidence_hash",
        "old_builder_old_evaluator_score_ref",
        "old_builder_old_evaluator_score_hash",
        "old_builder_new_evaluator_score_ref",
        "old_builder_new_evaluator_score_hash",
        "new_builder_old_evaluator_score_ref",
        "new_builder_old_evaluator_score_hash",
        "new_builder_new_evaluator_score_ref",
        "new_builder_new_evaluator_score_hash",
        "anchor_release_ref",
        "anchor_release_hash",
        "decision_threshold",
        "global_shift_interval",
        "interaction_interval",
        "decision_agreement",
        "anchor_agreement",
        "construct_evidence",
        "reliability_evidence",
        "strata",
        "outcome",
    },
    "comparability_decision": {
        "decision_id",
        "bridge_ref",
        "bridge_hash",
        "outcome",
        "reason",
        "eligible",
    },
    "independence_assessment": {
        "assessment_id",
        "claim_ref",
        "stage",
        "dimensions",
        "overall",
        "authority",
        "evidence_refs",
    },
    "promotion_transition": {
        "transition_id",
        "candidate_ref",
        "candidate_hash",
        "from_state",
        "to_state",
        "predecessor_transition_ref",
        "predecessor_transition_hash",
        "actor",
        "approval_actor",
        "independence",
        "confirmation_status",
        "bridge_status",
        "critical_failure",
        "effect_attempt",
        "revoked_ancestry",
        "reason",
        "evidence_refs",
    },
    "trajectory_summary": {
        "summary_id",
        "arm",
        "scenario_ref",
        "counts",
        "primary_endpoint",
        "budget",
    },
    "contrast_summary": {"summary_id", "aggregation_version", "contrasts"},
    "deletion_tombstone": {
        "tombstone_id",
        "targets",
        "authority",
        "reason",
        "descendant_policy",
        "deleted_surfaces",
    },
}


def _validate_payload(record_type: str, payload: Any, path: str = "payload") -> dict[str, Any]:
    if record_type not in RECORD_TYPES:
        _error("record_type", f"unknown record type {record_type}")
    if not _is_mapping(payload):
        _error("invalid_type", f"{path} must be an object")
    allowed = _PAYLOAD_FIELDS[record_type]
    _strict_keys(payload, allowed, path)
    if not payload:
        _error("empty_payload", f"{path} must not be empty")
    result: dict[str, Any] = {}
    for key, value in payload.items():
        if key.endswith("_hash") or key == "artifact_hash":
            result[key] = _require_hash(value, f"{path}.{key}")
        elif key in {"score", "amount", "seed", "value"}:
            if (
                key == "score"
                and record_type == "score_run"
                and value is None
                or key == "value"
                and record_type == "anchor_observation"
                and value is None
            ):
                result[key] = None
            else:
                result[key] = _require_number(
                    value, f"{path}.{key}", nonnegative=key in {"amount", "seed"}
                )
        elif key in {
            "critical_failure",
            "effect_attempt",
            "revoked_ancestry",
            "tainted",
            "consumed",
            "eligible",
            "self_certification",
            "arm_blinded",
            "attempted",
            "accepted",
            "blocked",
            "quarantined",
        }:
            result[key] = _require_bool(value, f"{path}.{key}")
        elif key.endswith("_interval"):
            if (
                not isinstance(value, Sequence)
                or isinstance(value, (str, bytes))
                or len(value) != 2
            ):
                _error("interval", f"{path}.{key} must be a two-element interval")
            result[key] = [
                _require_number(value[0], f"{path}.{key}[0]"),
                _require_number(value[1], f"{path}.{key}[1]"),
            ]
            if result[key][0] > result[key][1]:
                _error("interval", f"{path}.{key} lower bound exceeds upper bound")
        elif key == "decision_agreement" or key in {"anchor_agreement", "decision_threshold"}:
            result[key] = _require_number(value, f"{path}.{key}")
            if not 0 <= result[key] <= 1:
                _error("range", f"{path}.{key} must be between 0 and 1")
        elif (
            key == "targets"
            or key == "surface_refs"
            or key == "allowed_evidence_surface"
            or key == "scenario_refs"
            or key == "evidence_refs"
            or key == "deleted_surfaces"
        ):
            if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
                _error("invalid_type", f"{path}.{key} must be an array")
            result[key] = [
                _require_string(item, f"{path}.{key}[{index}]") for index, item in enumerate(value)
            ]
        elif key == "dimensions":
            if not _is_mapping(value):
                _error("invalid_type", f"{path}.dimensions must be an object")
            result[key] = {
                str(dim): _require_string(status, f"{path}.dimensions.{dim}")
                for dim, status in value.items()
            }
        else:
            result[key] = _clone_json(value, f"{path}.{key}")

    string_payload_fields = {
        "release_id",
        "release_kind",
        "revision",
        "parent_release_ref",
        "method_id",
        "binding_id",
        "builder_release_ref",
        "evaluator_release_ref",
        "method_ref",
        "task_partition",
        "task_ref",
        "environment_ref",
        "runner_ref",
        "exposure_state_ref",
        "evidence_id",
        "subject_ref",
        "binding_ref",
        "partition",
        "status",
        "score_run_id",
        "evidence_ref",
        "score_status",
        "scoring_actor",
        "confirmation_consumption_ref",
        "score_key",
        "exposure_id",
        "target_ref",
        "exposure_kind",
        "consumption_id",
        "confirmation_ref",
        "candidate_ref",
        "authority",
        "anchor_observation_id",
        "effect_attempt_id",
        "observation_authority",
        "disposition",
        "receipt_ref",
        "reason_code",
        "bridge_id",
        "old_builder_ref",
        "new_builder_ref",
        "old_evaluator_ref",
        "new_evaluator_ref",
        "old_evidence_ref",
        "new_evidence_ref",
        "old_builder_old_evaluator_score_ref",
        "old_builder_new_evaluator_score_ref",
        "new_builder_old_evaluator_score_ref",
        "new_builder_new_evaluator_score_ref",
        "anchor_release_ref",
        "outcome",
        "decision_id",
        "bridge_ref",
        "assessment_id",
        "claim_ref",
        "stage",
        "overall",
        "transition_id",
        "from_state",
        "to_state",
        "predecessor_transition_ref",
        "actor",
        "approval_actor",
        "summary_id",
        "arm",
        "scenario_ref",
        "aggregation_version",
        "config_version",
        "tombstone_id",
        "descendant_policy",
        "postcondition_status",
    }
    for key in string_payload_fields & set(result):
        result[key] = _require_string(result[key], f"{path}.{key}")
    if record_type == "bridge_observation":
        strata_value = result.get("strata")
        if not isinstance(strata_value, Sequence) or isinstance(strata_value, (str, bytes)):
            _error("strata_policy", f"{path}.strata must be an array")
        normalized_strata: list[dict[str, Any]] = []
        seen_strata: set[str] = set()
        stratum_fields = {
            "stratum",
            "weight",
            "old_evidence_ref",
            "old_evidence_hash",
            "new_evidence_ref",
            "new_evidence_hash",
            "b0e0_score_ref",
            "b0e0_score_hash",
            "b0e1_score_ref",
            "b0e1_score_hash",
            "b1e0_score_ref",
            "b1e0_score_hash",
            "b1e1_score_ref",
            "b1e1_score_hash",
            "b0_anchor_ref",
            "b0_anchor_hash",
            "b1_anchor_ref",
            "b1_anchor_hash",
        }
        required_stratum_fields = stratum_fields
        for index, item in enumerate(strata_value):
            if not _is_mapping(item):
                _error("strata_policy", f"{path}.strata[{index}] must be an object")
            item_path = f"{path}.strata[{index}]"
            _strict_keys(item, stratum_fields, item_path)
            missing_stratum = sorted(required_stratum_fields - set(item))
            if missing_stratum:
                _error(
                    "bridge_insufficient",
                    f"{item_path} missing required field(s): {', '.join(missing_stratum)}",
                )
            stratum = _critical_string(item["stratum"], f"{item_path}.stratum")
            if stratum in seen_strata:
                _error("strata_policy", f"{path}.strata contains duplicate stratum {stratum}")
            seen_strata.add(stratum)
            normalized_item: dict[str, Any] = {
                "stratum": stratum,
                "weight": _require_number(item["weight"], f"{item_path}.weight", nonnegative=True),
            }
            if normalized_item["weight"] <= 0:
                _error("strata_policy", f"{item_path}.weight must be positive")
            for field in sorted(stratum_fields - {"stratum", "weight"}):
                if field.endswith("_hash"):
                    normalized_item[field] = _require_hash(item[field], f"{item_path}.{field}")
                else:
                    normalized_item[field] = _require_string(item[field], f"{item_path}.{field}")
            normalized_strata.append(normalized_item)
        normalized_strata.sort(key=lambda item: item["stratum"])
        result["strata"] = normalized_strata

    if record_type == "trajectory_summary":
        result["arm"] = _critical_string(result.get("arm"), f"{path}.arm")
        result["scenario_ref"] = _critical_string(
            result.get("scenario_ref"), f"{path}.scenario_ref"
        )
        result["counts"] = _validate_trajectory_counts(result.get("counts"), f"{path}.counts")
        result["primary_endpoint"] = _validate_primary_endpoint(
            result.get("primary_endpoint"), f"{path}.primary_endpoint"
        )
        if result["primary_endpoint"]["observed_count"] > sum(
            result["counts"]["disposition"].values()
        ):
            _error(
                "summary_endpoint",
                f"{path}.primary_endpoint.observed_count exceeds disposition total",
            )
        result["budget"] = _validate_trajectory_budget(result.get("budget"), f"{path}.budget")
    elif record_type == "exposure_event":
        amount = result.get("amount")
        if not isinstance(amount, int) or isinstance(amount, bool) or amount < 1:
            _error("exposure_amount", f"{path}.amount must be an integer >= 1")
    elif record_type == "contrast_summary":
        aggregation_version = _critical_string(
            result.get("aggregation_version"), f"{path}.aggregation_version"
        )
        if aggregation_version != CONTRAST_SUMMARY_AGGREGATION_VERSION:
            _error(
                "summary_version",
                f"{path}.aggregation_version must be {CONTRAST_SUMMARY_AGGREGATION_VERSION}",
            )
        result["aggregation_version"] = aggregation_version
        contrasts = result.get("contrasts")
        if not isinstance(contrasts, Sequence) or isinstance(contrasts, (str, bytes)):
            _error("contrast_summary", f"{path}.contrasts must be an array")
        normalized_contrasts: list[dict[str, Any]] = []
        seen_contrasts: set[str] = set()
        contrast_fields = {"contrast_id", "status", "reason", "endpoint_delta_ppm"}
        for index, item in enumerate(contrasts):
            item_path = f"{path}.contrasts[{index}]"
            if not _is_mapping(item):
                _error("contrast_summary", f"{item_path} must be an object")
            _strict_keys(item, contrast_fields, item_path)
            if set(item) != contrast_fields:
                _error("contrast_summary", f"{item_path} must declare exactly four fields")
            contrast_id = _critical_string(item.get("contrast_id"), f"{item_path}.contrast_id")
            if contrast_id in seen_contrasts:
                _error("contrast_summary", f"{item_path}.contrast_id is duplicated")
            seen_contrasts.add(contrast_id)
            status = _critical_string(item.get("status"), f"{item_path}.status")
            if status not in {"causal_eligible", "diagnostic_only", "not_estimable"}:
                _error("contrast_summary", f"{item_path}.status is not admitted")
            reason = item.get("reason")
            if reason is not None:
                reason = _critical_string(reason, f"{item_path}.reason")
                if reason not in {"optional_stopping", "actual_cost_mismatch", "missing_endpoint"}:
                    _error("contrast_summary", f"{item_path}.reason is not admitted")
            delta = item.get("endpoint_delta_ppm")
            if delta is not None:
                if isinstance(delta, bool) or not isinstance(delta, int):
                    _error(
                        "contrast_summary",
                        f"{item_path}.endpoint_delta_ppm must be an integer or null",
                    )
                delta = int(delta)
            normalized_contrasts.append(
                {
                    "contrast_id": contrast_id,
                    "status": status,
                    "reason": reason,
                    "endpoint_delta_ppm": delta,
                }
            )
        if [item["contrast_id"] for item in normalized_contrasts] != sorted(seen_contrasts):
            _error("contrast_summary", f"{path}.contrasts must be sorted by contrast_id")
        result["contrasts"] = normalized_contrasts

    # Record variant identities and required decision-bearing fields.
    required_by_type: dict[str, set[str]] = {
        "builder_release": {
            "release_id",
            "release_kind",
            "revision",
            "artifact_hash",
            "custody",
            "allowed_evidence_surface",
        },
        "challenger_release": {
            "release_id",
            "release_kind",
            "revision",
            "artifact_hash",
            "custody",
            "allowed_evidence_surface",
        },
        "anchor_release": {
            "release_id",
            "release_kind",
            "revision",
            "artifact_hash",
            "custody",
            "allowed_evidence_surface",
            "adjudication_protocol",
        },
        "evaluator_release": {
            "release_id",
            "release_kind",
            "revision",
            "artifact_hash",
            "implementation",
            "prompt_or_rubric",
            "model",
            "parser_or_aggregation",
            "tools_or_environment",
            "calibration_lineage",
            "known_error_envelope",
            "custody",
            "allowed_evidence_surface",
        },
        "measurement_method": {
            "method_id",
            "revision",
            "artifact_hash",
            "construct",
            "oracle",
            "parser",
            "aggregation",
            "validity",
            "reliability",
            "custody",
        },
        "evaluation_binding": {
            "binding_id",
            "builder_release_ref",
            "builder_release_hash",
            "evaluator_release_ref",
            "evaluator_release_hash",
            "method_ref",
            "method_hash",
            "evidence_ref",
            "evidence_hash",
            "task_partition",
            "task_ref",
            "task_hash",
            "exposure_policy",
            "analysis_ref",
            "analysis_hash",
            "environment_ref",
            "environment_hash",
            "runner_ref",
            "runner_hash",
            "promotion_policy_ref",
            "promotion_policy_hash",
            "exposure_state_ref",
            "exposure_state_hash",
            "allowed_evidence_surface",
        },
        "subject_execution_evidence": {
            "evidence_id",
            "subject_ref",
            "builder_release_ref",
            "builder_release_hash",
            "task_partition",
            "task_ref",
            "task_hash",
            "environment_ref",
            "environment_hash",
            "runner_ref",
            "runner_hash",
            "exposure_state_ref",
            "exposure_state_hash",
            "partition",
            "surface_refs",
            "artifact_hash",
            "status",
        },
        "score_run": {
            "score_run_id",
            "binding_ref",
            "binding_hash",
            "evidence_ref",
            "evidence_hash",
            "evaluator_release_ref",
            "evaluator_release_hash",
            "builder_release_ref",
            "builder_release_hash",
            "method_ref",
            "method_hash",
            "score",
            "score_status",
            "scoring_actor",
            "partition",
            "surface_refs",
        },
        "exposure_event": {
            "exposure_id",
            "target_ref",
            "target_hash",
            "partition",
            "exposure_kind",
            "amount",
        },
        "confirmation_consumption": {
            "consumption_id",
            "partition",
            "confirmation_ref",
            "confirmation_hash",
            "candidate_ref",
            "candidate_hash",
            "authority",
            "consumed",
        },
        "anchor_observation": {
            "anchor_observation_id",
            "candidate_ref",
            "candidate_hash",
            "anchor_release_ref",
            "anchor_release_hash",
            "partition",
            "authority",
            "arm_blinded",
            "outcome",
            "value",
            "critical_failure",
            "status",
        },
        "effect_attempt": {
            "effect_attempt_id",
            "candidate_ref",
            "candidate_hash",
            "evidence_ref",
            "evidence_hash",
            "binding_ref",
            "binding_hash",
            "partition",
            "observation_authority",
            "effect_request_hash",
            "idempotency_key_hash",
            "disposition",
            "postcondition_status",
            "reason_code",
        },
        "bridge_observation": {
            "bridge_id",
            "old_builder_ref",
            "old_builder_hash",
            "new_builder_ref",
            "new_builder_hash",
            "old_evaluator_ref",
            "old_evaluator_hash",
            "new_evaluator_ref",
            "new_evaluator_hash",
            "old_evidence_ref",
            "old_evidence_hash",
            "new_evidence_ref",
            "new_evidence_hash",
            "old_builder_old_evaluator_score_ref",
            "old_builder_old_evaluator_score_hash",
            "old_builder_new_evaluator_score_ref",
            "old_builder_new_evaluator_score_hash",
            "new_builder_old_evaluator_score_ref",
            "new_builder_old_evaluator_score_hash",
            "new_builder_new_evaluator_score_ref",
            "new_builder_new_evaluator_score_hash",
            "anchor_release_ref",
            "anchor_release_hash",
            "decision_threshold",
            "global_shift_interval",
            "interaction_interval",
            "decision_agreement",
            "anchor_agreement",
            "construct_evidence",
            "reliability_evidence",
            "strata",
            "outcome",
        },
        "comparability_decision": {
            "decision_id",
            "bridge_ref",
            "bridge_hash",
            "outcome",
            "reason",
            "eligible",
        },
        "independence_assessment": {
            "assessment_id",
            "claim_ref",
            "dimensions",
            "overall",
            "authority",
            "evidence_refs",
        },
        "promotion_transition": {
            "transition_id",
            "candidate_ref",
            "candidate_hash",
            "from_state",
            "to_state",
            "predecessor_transition_hash",
            "actor",
            "approval_actor",
            "independence",
            "confirmation_status",
            "bridge_status",
            "critical_failure",
            "effect_attempt",
            "revoked_ancestry",
            "reason",
            "evidence_refs",
        },
        "trajectory_summary": {
            "summary_id",
            "arm",
            "scenario_ref",
            "counts",
            "primary_endpoint",
            "budget",
        },
        "contrast_summary": {"summary_id", "aggregation_version", "contrasts"},
        "deletion_tombstone": {
            "tombstone_id",
            "targets",
            "authority",
            "reason",
            "descendant_policy",
            "deleted_surfaces",
        },
    }
    missing = sorted(required_by_type[record_type] - set(result))
    if missing:
        _error("missing_field", f"{path} missing required field(s): {', '.join(missing)}")
    if record_type == "score_run":
        score_status = result.get("score_status")
        allowed_score_statuses = {
            "observed",
            "missing",
            "unavailable",
            "unscorable",
            "revoked",
            "failed",
            "retained",
            "sealed",
            "pass",
            "passed",
        }
        if score_status not in allowed_score_statuses:
            _error("score_status", f"{path}.score_status is not admitted")
        if score_status == "observed":
            score_value = result.get("score")
            if score_value is None or not 0 <= score_value <= 1:
                _error(
                    "score_range",
                    f"{path}.observed score must be a number between 0 and 1",
                )
        elif result.get("score") is not None:
            _error(
                "score_missingness",
                f"{path}.non-observed score must be null",
            )
    if (
        record_type == "promotion_transition"
        and result.get("from_state") != "registered"
        and "predecessor_transition_ref" not in result
    ):
        _error(
            "missing_field",
            f"{path} missing required field(s): predecessor_transition_ref",
        )
    if record_type.endswith("_release") and result.get(
        "release_kind", ""
    ).casefold() != record_type.removesuffix("_release"):
        _error("release_kind", f"{path}.release_kind must exactly match record type role")
    if record_type.endswith("_release"):
        if not result.get("allowed_evidence_surface"):
            _error("missing_surface", f"{path}.allowed_evidence_surface must not be empty")
        result["custody"] = _critical_string(result.get("custody"), f"{path}.custody")
        if record_type == "evaluator_release":
            for field in (
                "implementation",
                "prompt_or_rubric",
                "model",
                "parser_or_aggregation",
                "tools_or_environment",
                "calibration_lineage",
                "known_error_envelope",
            ):
                _nonblank(result[field], f"{path}.{field}", critical=True)
    if record_type == "measurement_method":
        for field in (
            "construct",
            "oracle",
            "parser",
            "aggregation",
            "validity",
            "reliability",
            "custody",
        ):
            if field == "custody":
                result[field] = _critical_string(result[field], f"{path}.{field}")
            else:
                _nonblank(result[field], f"{path}.{field}", critical=True)
    if record_type in {
        "evaluation_binding",
        "subject_execution_evidence",
        "score_run",
        "exposure_event",
        "confirmation_consumption",
        "anchor_observation",
    }:
        partition = result.get("task_partition", result.get("partition"))
        if partition not in {"development", "screening", "bridge", "confirmation", "historical"}:
            _error("partition_identity", f"{path} names an unknown task partition")
    if record_type == "evaluation_binding":
        if not result["allowed_evidence_surface"]:
            _error("missing_surface", f"{path}.allowed_evidence_surface must not be empty")
        for field in (
            "task_ref",
            "analysis_ref",
            "environment_ref",
            "runner_ref",
            "promotion_policy_ref",
            "exposure_state_ref",
        ):
            result[field] = _critical_string(result[field], f"{path}.{field}")
    if record_type == "subject_execution_evidence":
        if result["partition"] != result["task_partition"]:
            _error("partition_identity", f"{path}.partition must equal task_partition")
        if not result["surface_refs"]:
            _error("missing_surface", f"{path}.surface_refs must not be empty")
        for field in (
            "task_ref",
            "environment_ref",
            "runner_ref",
            "exposure_state_ref",
        ):
            result[field] = _critical_string(result[field], f"{path}.{field}")
    if record_type == "anchor_observation":
        if result["partition"] not in {"confirmation", "bridge"}:
            _error("anchor_policy", f"{path}.partition must be confirmation or bridge")
        if result["arm_blinded"] is not True:
            _error("anchor_policy", f"{path}.arm_blinded must be true")
        for field in ("authority", "outcome", "status"):
            result[field] = _critical_string(result[field], f"{path}.{field}")
        negative_statuses = {
            "missing",
            "unavailable",
            "tainted",
            "failed",
            "unscorable",
            "revoked",
        }
        if result["partition"] == "bridge":
            if result["value"] is None or not 0 <= result["value"] <= 1:
                _error("anchor_policy", f"{path}.value must be between 0 and 1")
            if result["status"] != "observed":
                _error("anchor_policy", f"{path} bridge anchor status must be observed")
        elif result["value"] is None:
            if result["status"] not in negative_statuses:
                _error(
                    "anchor_policy",
                    f"{path}.value may be null only for an unusable confirmation status",
                )
        elif result["status"] in negative_statuses:
            _error("anchor_policy", f"{path}.negative confirmation status must not carry a value")
        elif not 0 <= result["value"] <= 1:
            _error("anchor_policy", f"{path}.value must be between 0 and 1")
        has_consumption_ref = "confirmation_consumption_ref" in result
        has_consumption_hash = "confirmation_consumption_hash" in result
        if result["partition"] == "confirmation":
            if has_consumption_ref != has_consumption_hash or not has_consumption_ref:
                _error(
                    "anchor_policy",
                    f"{path} confirmation anchor requires confirmation_consumption_ref/hash",
                )
        elif has_consumption_ref or has_consumption_hash:
            _error(
                "anchor_policy",
                f"{path} bridge anchor must not bind a confirmation consumption",
            )
    if record_type == "independence_assessment":
        result["authority"] = _critical_string(result["authority"], f"{path}.authority")
        if result["stage"] not in {"bridge", "confirmation"}:
            _error("independence_stage", f"{path}.stage must be bridge or confirmation")
    if record_type == "effect_attempt":
        if result["partition"] not in {
            "development",
            "screening",
            "bridge",
            "confirmation",
            "historical",
        }:
            _error("partition_identity", f"{path}.partition names an unknown task partition")
        result["observation_authority"] = _critical_string(
            result["observation_authority"], f"{path}.observation_authority"
        )
        if result["disposition"] not in {"blocked", "accepted", "quarantined"}:
            _error("effect_disposition", f"{path}.disposition is unknown")
        if result["postcondition_status"] not in {
            "not_dispatched",
            "confirmed_not_applied",
            "confirmed_applied",
            "ambiguous",
        }:
            _error("effect_postcondition", f"{path}.postcondition_status is unknown")
        disposition = result["disposition"]
        postcondition = result["postcondition_status"]
        if disposition == "blocked" and postcondition not in {
            "not_dispatched",
            "confirmed_not_applied",
        }:
            _error("effect_postcondition", f"{path} blocked effect must not be applied")
        if disposition == "accepted" and (
            postcondition != "confirmed_applied" or "receipt_ref" not in result
        ):
            _error("effect_postcondition", f"{path} accepted effect requires applied receipt")
        if disposition == "quarantined" and postcondition != "ambiguous":
            _error("effect_postcondition", f"{path} quarantined effect must be ambiguous")
        if disposition != "blocked" or postcondition != "not_dispatched":
            _error("effect_forbidden", f"{path} Stage 0 admits only blocked/not_dispatched effects")
        if "receipt_ref" in result or "receipt_hash" in result:
            _error("effect_forbidden", f"{path} blocked effect cannot carry a receipt")
    if record_type == "effect_attempt" and ("receipt_ref" in result) != ("receipt_hash" in result):
        _error("effect_receipt", f"{path}.receipt_ref and receipt_hash must be supplied together")
    if record_type.endswith("_release") and ("parent_release_ref" in result) != (
        "parent_release_hash" in result
    ):
        _error(
            "parent_identity",
            f"{path}.parent_release_ref and parent_release_hash must be supplied together",
        )
    return result


def record_hash(record: Mapping[str, Any]) -> str:
    if not _is_mapping(record):
        _error("invalid_type", "record must be an object")
    body = {key: value for key, value in record.items() if key != "record_hash"}
    return canonical_hash(body, domain="ael-cep-record")


def create_record(
    *,
    record_id: str,
    record_type: str,
    epoch_id: str,
    sequence: int,
    previous_record_hash: str | None,
    payload: Mapping[str, Any],
    dependency_refs: Mapping[str, str] | Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    _require_string(record_id, "record_id")
    _require_string(epoch_id, "epoch_id")
    if record_type not in RECORD_TYPES:
        _error("record_type", f"unknown record type {record_type}")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 0:
        _error("sequence", "sequence must be a nonnegative integer")
    if previous_record_hash is not None:
        _require_hash(previous_record_hash, "previous_record_hash")
    normalized_payload = _validate_payload(record_type, payload)
    record = {
        "schema_version": RECORD_SCHEMA_VERSION,
        "record_id": record_id,
        "record_type": record_type,
        "epoch_id": epoch_id,
        "sequence": sequence,
        "previous_record_hash": previous_record_hash,
        "dependency_refs": _dependency_list(dependency_refs, "dependency_refs"),
        "payload": normalized_payload,
    }
    record["record_hash"] = record_hash(record)
    return record


def _record_id(record: Mapping[str, Any]) -> str:
    return _require_string(record.get("record_id"), "record.record_id")


def _record_hash(record: Mapping[str, Any]) -> str:
    return _require_hash(record.get("record_hash"), f"record {_record_id(record)}.record_hash")


def _bound_dependency(
    record: Mapping[str, Any],
    by_id: Mapping[str, Mapping[str, Any]],
    ref: Any,
    digest: Any,
    field: str,
    *,
    expected_types: set[str] | None = None,
) -> None:
    """Require a payload identity/hash to resolve through an explicit ledger edge."""

    record_id = _require_string(ref, f"{record['record_id']}.payload.{field}")
    declared_hash = _require_hash(
        digest, f"{record['record_id']}.payload.{field.replace('_ref', '_hash')}"
    )
    parent = by_id.get(record_id)
    if parent is None or parent["sequence"] >= record["sequence"]:
        _error(
            "dangling_dependency",
            f"{record['record_id']} payload {field} points to a missing/future record",
        )
    if declared_hash != parent["record_hash"]:
        _error(
            "dependency_hash_mismatch", f"{record['record_id']} payload {field} has the wrong hash"
        )
    if expected_types and parent["record_type"] not in expected_types:
        _error(
            "dependency_type",
            f"{record['record_id']} payload {field} points to the wrong record type",
        )
    deps = {item["record_id"]: item["record_hash"] for item in record["dependency_refs"]}
    if deps.get(record_id) != declared_hash:
        _error(
            "missing_dependency_edge",
            f"{record['record_id']} must explicitly depend on {record_id} with its exact hash",
        )


def _derive_anchor_decision_agreement(
    scores: Mapping[str, Mapping[str, Any]],
    anchors: Mapping[str, Mapping[str, Any]],
    threshold: float,
    path: str,
) -> float:
    """Compare each Builder generation's anchor decision to both evaluator cells.

    Anchor status and critical-failure labels are descriptive metadata; the
    protected endpoint is authoritative only through its observed value.  A
    bridge therefore compares the thresholded B0 anchor value with B0/E0 and
    B0/E1, and the thresholded B1 anchor value with B1/E0 and B1/E1.
    """

    b0_anchor = _require_number(anchors["b0_anchor"].get("value"), f"{path}.b0_anchor.value")
    b1_anchor = _require_number(anchors["b1_anchor"].get("value"), f"{path}.b1_anchor.value")
    b0_decision = b0_anchor >= threshold
    b1_decision = b1_anchor >= threshold
    matches = (
        b0_decision
        == (_require_number(scores["b0e0"].get("score"), f"{path}.b0e0.score") >= threshold),
        b0_decision
        == (_require_number(scores["b0e1"].get("score"), f"{path}.b0e1.score") >= threshold),
        b1_decision
        == (_require_number(scores["b1e0"].get("score"), f"{path}.b1e0.score") >= threshold),
        b1_decision
        == (_require_number(scores["b1e1"].get("score"), f"{path}.b1e1.score") >= threshold),
    )
    return sum(float(match) for match in matches) / len(matches)


def _derive_bridge_panel_gate(
    payload: Mapping[str, Any],
    by_id: Mapping[str, Mapping[str, Any]],
    *,
    threshold: float,
    global_tolerance: float,
    interaction_tolerance: float,
    agreement_min: float,
    path: str,
) -> dict[str, Any]:
    """Derive weighted panel metrics and a no-cancellation per-stratum gate.

    The bridge record has already passed structural dependency checks when this
    helper is called.  It deliberately reads observed score/anchor values from
    the addressed records rather than trusting summary/pass flags in payload.
    """

    weighted_global = 0.0
    weighted_interaction = 0.0
    weighted_decision = 0.0
    weighted_anchor = 0.0
    stratum_gate = True
    for index, stratum in enumerate(payload["strata"]):
        item_path = f"{path}.strata[{index}]"
        try:
            scores = {
                cell: by_id[stratum[f"{cell}_score_ref"]]["payload"]
                for cell in ("b0e0", "b0e1", "b1e0", "b1e1")
            }
            anchors = {
                anchor: by_id[stratum[f"{anchor}_ref"]]["payload"]
                for anchor in ("b0_anchor", "b1_anchor")
            }
        except (KeyError, TypeError) as exc:
            _error(
                "bridge_insufficient",
                f"{item_path} panel dependency is not resolvable: {exc}",
            )
        y00 = _require_number(scores["b0e0"].get("score"), f"{item_path}.b0e0.score")
        y01 = _require_number(scores["b0e1"].get("score"), f"{item_path}.b0e1.score")
        y10 = _require_number(scores["b1e0"].get("score"), f"{item_path}.b1e0.score")
        y11 = _require_number(scores["b1e1"].get("score"), f"{item_path}.b1e1.score")
        global_shift = ((y01 - y00) + (y11 - y10)) / 2.0
        interaction = (y11 - y01) - (y10 - y00)
        decision_agreement = 0.5 * float((y00 >= threshold) == (y01 >= threshold)) + 0.5 * float(
            (y10 >= threshold) == (y11 >= threshold)
        )
        anchor_agreement = _derive_anchor_decision_agreement(scores, anchors, threshold, item_path)
        weight = _require_number(stratum["weight"], f"{item_path}.weight", nonnegative=True)
        weighted_global += float(weight) * global_shift
        weighted_interaction += float(weight) * interaction
        weighted_decision += float(weight) * decision_agreement
        weighted_anchor += float(weight) * anchor_agreement
        stratum_gate = stratum_gate and (
            abs(global_shift) <= global_tolerance
            and abs(interaction) <= interaction_tolerance
            and decision_agreement >= agreement_min
            and anchor_agreement >= agreement_min
        )
    return {
        "global": weighted_global,
        "interaction": weighted_interaction,
        "decision": weighted_decision,
        "anchor": weighted_anchor,
        "strata_gate": stratum_gate,
    }


def _bundle_body(bundle: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in bundle.items() if key != "bundle_hash"}


def bundle_hash(bundle: Mapping[str, Any]) -> str:
    return canonical_hash(_bundle_body(bundle), domain="ael-cep-bundle")


def create_bundle(
    protocol: Mapping[str, Any],
    *,
    bundle_id: str,
    records: Sequence[Mapping[str, Any]] = (),
    predecessor: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    frozen = freeze_protocol(protocol)
    normalized_records = [_clone_json(record) for record in records]
    bundle: dict[str, Any] = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "bundle_id": _require_string(bundle_id, "bundle_id"),
        "protocol_ref": frozen["protocol_id"],
        "protocol_hash": canonical_hash(frozen, domain="ael-cep-protocol"),
        "predecessor": None
        if predecessor is None
        else {
            "bundle_ref": _require_string(predecessor.get("bundle_ref"), "predecessor.bundle_ref"),
            "bundle_hash": _require_hash(predecessor.get("bundle_hash"), "predecessor.bundle_hash"),
        },
        "records": normalized_records,
    }
    bundle["bundle_hash"] = bundle_hash(bundle)
    # A metadata-only predecessor is useful when constructing an empty
    # successor placeholder (the adapter later proves the actual prefix from
    # the supplied predecessor path).  Do not silently permit an unproved
    # prefix when records are supplied.
    return validate_bundle(
        bundle,
        protocol=frozen,
        _allow_unresolved_predecessor=predecessor is not None and not normalized_records,
    )


_BUNDLE_FIELDS = {
    "schema_version",
    "bundle_id",
    "protocol_ref",
    "protocol_hash",
    "predecessor",
    "records",
    "bundle_hash",
}
_RECORD_FIELDS = {
    "schema_version",
    "record_id",
    "record_type",
    "epoch_id",
    "sequence",
    "previous_record_hash",
    "dependency_refs",
    "payload",
    "record_hash",
}


def _normalize_record(record: Mapping[str, Any], index: int) -> dict[str, Any]:
    path = f"records[{index}]"
    if not _is_mapping(record):
        _error("invalid_type", f"{path} must be an object")
    _strict_keys(record, _RECORD_FIELDS, path)
    if record.get("schema_version") != RECORD_SCHEMA_VERSION:
        _error("schema_version", f"{path}.schema_version must be {RECORD_SCHEMA_VERSION}")
    record_type = _require_string(record.get("record_type"), f"{path}.record_type")
    if record_type not in RECORD_TYPES:
        _error("record_type", f"{path}.record_type unknown: {record_type}")
    sequence = record.get("sequence")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 0:
        _error("sequence", f"{path}.sequence must be a nonnegative integer")
    previous = record.get("previous_record_hash")
    if previous is not None:
        _require_hash(previous, f"{path}.previous_record_hash")
    normalized = {
        "schema_version": RECORD_SCHEMA_VERSION,
        "record_id": _require_string(record.get("record_id"), f"{path}.record_id"),
        "record_type": record_type,
        "epoch_id": _require_string(record.get("epoch_id"), f"{path}.epoch_id"),
        "sequence": sequence,
        "previous_record_hash": previous,
        "dependency_refs": _dependency_list(
            record.get("dependency_refs"), f"{path}.dependency_refs"
        ),
        "payload": _validate_payload(record_type, record.get("payload"), f"{path}.payload"),
    }
    identity_field = {
        "builder_release": "release_id",
        "evaluator_release": "release_id",
        "challenger_release": "release_id",
        "anchor_release": "release_id",
        "measurement_method": "method_id",
        "evaluation_binding": "binding_id",
        "subject_execution_evidence": "evidence_id",
        "score_run": "score_run_id",
        "exposure_event": "exposure_id",
        "confirmation_consumption": "consumption_id",
        "bridge_observation": "bridge_id",
        "comparability_decision": "decision_id",
        "independence_assessment": "assessment_id",
        "promotion_transition": "transition_id",
        "trajectory_summary": "summary_id",
        "contrast_summary": "summary_id",
        "deletion_tombstone": "tombstone_id",
        "anchor_observation": "anchor_observation_id",
        "effect_attempt": "effect_attempt_id",
    }[record_type]
    if normalized["record_id"] != normalized["payload"][identity_field]:
        _error("identity_mismatch", f"{path}.record_id must equal payload.{identity_field}")
    given_hash = _require_hash(record.get("record_hash"), f"{path}.record_hash")
    expected_hash = record_hash(normalized)
    if given_hash != expected_hash:
        _error("hash_mismatch", f"{path}.record_hash does not match canonical record bytes")
    normalized["record_hash"] = given_hash
    return normalized


_STAGE_SLOT_TYPES: dict[str, dict[str, set[str]]] = {
    "screening": {
        "evidence": {"subject_execution_evidence"},
        "binding": {"evaluation_binding"},
        "score": {"score_run"},
        "exposure": {"exposure_event"},
    },
    "bridge": {
        "bridge": {"bridge_observation"},
        "comparability": {"comparability_decision"},
        "independence": {"independence_assessment"},
        "evidence": {"subject_execution_evidence"},
        "binding": {"evaluation_binding"},
        "score": {"score_run"},
        "anchor": {"anchor_observation"},
        "exposure": {"exposure_event"},
    },
    "confirmation": {
        "evidence": {"subject_execution_evidence"},
        "binding": {"evaluation_binding"},
        "score": {"score_run"},
        "consumption": {"confirmation_consumption"},
        "anchor": {"anchor_observation"},
        "independence": {"independence_assessment"},
        "exposure": {"exposure_event"},
    },
}


def _stage_record_matches(
    record: Mapping[str, Any],
    *,
    stage: str,
    candidate_ref: str,
    candidate_hash: str,
    by_id: Mapping[str, Mapping[str, Any]],
) -> bool:
    """Return whether a prior typed record belongs to one candidate/stage."""

    record_type = record["record_type"]
    payload = record["payload"]

    def target_matches(target_ref: Any, target_hash: Any, partition: str) -> bool:
        """Resolve every validator-admitted typed exposure target transitively."""

        pending = [(target_ref, target_hash)]
        seen: set[str] = set()
        while pending:
            ref, digest = pending.pop()
            if not isinstance(ref, str) or ref in seen:
                continue
            seen.add(ref)
            target = by_id.get(ref)
            if target is None or target.get("record_hash") != digest:
                continue
            target_payload = target["payload"]
            target_partition = target_payload.get("task_partition", target_payload.get("partition"))
            if target_partition != partition:
                continue
            if (
                target_payload.get("builder_release_ref") == candidate_ref
                and target_payload.get("builder_release_hash") == candidate_hash
            ) or (
                target_payload.get("candidate_ref") == candidate_ref
                and target_payload.get("candidate_hash") == candidate_hash
            ):
                return True
            target_type = target["record_type"]
            if target_type in {"evaluation_binding", "score_run"}:
                evidence_ref = target_payload.get("evidence_ref")
                evidence_hash = target_payload.get("evidence_hash")
                if evidence_ref and evidence_hash:
                    pending.append((evidence_ref, evidence_hash))
            elif target_type == "confirmation_consumption":
                confirmation_ref = target_payload.get("confirmation_ref")
                confirmation_hash = target_payload.get("confirmation_hash")
                if confirmation_ref and confirmation_hash:
                    pending.append((confirmation_ref, confirmation_hash))
            elif target_type == "anchor_observation":
                evidence_ref = target_payload.get("evidence_ref")
                evidence_hash = target_payload.get("evidence_hash")
                if evidence_ref and evidence_hash:
                    pending.append((evidence_ref, evidence_hash))
                consumption_ref = target_payload.get("confirmation_consumption_ref")
                consumption_hash = target_payload.get("confirmation_consumption_hash")
                if consumption_ref and consumption_hash:
                    pending.append((consumption_ref, consumption_hash))
        return False

    if stage in {"screening", "confirmation"}:
        partition = stage
        if record_type == "subject_execution_evidence":
            return (
                payload.get("partition") == partition
                and payload.get("builder_release_ref") == candidate_ref
                and payload.get("builder_release_hash") == candidate_hash
            )
        if record_type == "evaluation_binding":
            return (
                payload.get("task_partition") == partition
                and payload.get("builder_release_ref") == candidate_ref
                and payload.get("builder_release_hash") == candidate_hash
            )
        if record_type == "score_run":
            return (
                payload.get("partition") == partition
                and payload.get("builder_release_ref") == candidate_ref
                and payload.get("builder_release_hash") == candidate_hash
            )
        if record_type == "exposure_event":
            if payload.get("partition") != partition:
                return False
            return target_matches(payload.get("target_ref"), payload.get("target_hash"), partition)
        if record_type == "confirmation_consumption":
            return (
                stage == "confirmation"
                and payload.get("partition") == "confirmation"
                and payload.get("candidate_ref") == candidate_ref
                and payload.get("candidate_hash") == candidate_hash
            )
        if record_type == "anchor_observation":
            return (
                stage == "confirmation"
                and payload.get("partition") == "confirmation"
                and payload.get("candidate_ref") == candidate_ref
                and payload.get("candidate_hash") == candidate_hash
            )
        if record_type == "independence_assessment":
            if stage != payload.get("stage") or payload.get("claim_ref") != candidate_ref:
                return False
            return any(
                target_matches(ref, by_id.get(ref, {}).get("record_hash"), "confirmation")
                for ref in payload.get("evidence_refs", [])
            )
    elif stage == "bridge":
        panel_builder_refs = {candidate_ref}
        for panel in by_id.values():
            if panel["record_type"] != "bridge_observation":
                continue
            panel_payload = panel["payload"]
            if (
                panel_payload.get("new_builder_ref") != candidate_ref
                or panel_payload.get("new_builder_hash") != candidate_hash
            ):
                continue
            panel_builder_refs.update(
                ref
                for ref in (
                    panel_payload.get("old_builder_ref"),
                    panel_payload.get("new_builder_ref"),
                )
                if isinstance(ref, str)
            )
        if record_type == "subject_execution_evidence":
            return (
                payload.get("partition") == "bridge"
                and payload.get("builder_release_ref") in panel_builder_refs
                and payload.get("builder_release_hash")
                == (by_id.get(payload.get("builder_release_ref"), {}).get("record_hash"))
            )
        if record_type == "evaluation_binding":
            return (
                payload.get("task_partition") == "bridge"
                and payload.get("builder_release_ref") in panel_builder_refs
            )
        if record_type == "score_run":
            return (
                payload.get("partition") == "bridge"
                and payload.get("builder_release_ref") in panel_builder_refs
            )
        if record_type == "anchor_observation":
            return (
                payload.get("partition") == "bridge"
                and payload.get("candidate_ref") in panel_builder_refs
            )
        if record_type == "exposure_event":
            return payload.get("partition") == "bridge" and target_matches(
                payload.get("target_ref"), payload.get("target_hash"), "bridge"
            )
        if record_type == "bridge_observation":
            return (
                payload.get("new_builder_ref") == candidate_ref
                and payload.get("new_builder_hash") == candidate_hash
            )
        if record_type == "comparability_decision":
            bridge = by_id.get(payload.get("bridge_ref"))
            return bool(
                bridge
                and bridge["record_type"] == "bridge_observation"
                and bridge["payload"].get("new_builder_ref") == candidate_ref
                and bridge["payload"].get("new_builder_hash") == candidate_hash
            )
        if record_type == "independence_assessment":
            return (
                payload.get("stage") == "bridge"
                and payload.get("claim_ref") == candidate_ref
                and any(
                    (by_id.get(ref) or {}).get("record_type")
                    in {"bridge_observation", "comparability_decision"}
                    for ref in payload.get("evidence_refs", [])
                )
            )
    return False


def _derive_candidate_stage_snapshot(
    records: Sequence[Mapping[str, Any]],
    by_id: Mapping[str, Mapping[str, Any]],
    *,
    candidate_ref: str,
    candidate_hash: str,
    stage: str,
    frozen: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Derive the exact prior fact set for one candidate's frozen stage.

    This is intentionally private and code-owned.  It is not a caller-defined
    manifest: every slot is discovered from typed refs/hashes in the ledger,
    and all same-candidate facts are included so a transition cannot omit a
    tainted, unavailable, or otherwise blocking sibling record.
    """

    if stage not in _STAGE_SLOT_TYPES:
        _error("promotion_stage", f"unknown candidate stage {stage}")
    prefix_by_id = {record["record_id"]: record for record in records}
    slots: dict[str, list[Mapping[str, Any]]] = {slot: [] for slot in _STAGE_SLOT_TYPES[stage]}
    for record in records:
        if not _stage_record_matches(
            record,
            stage=stage,
            candidate_ref=candidate_ref,
            candidate_hash=candidate_hash,
            by_id=prefix_by_id,
        ):
            continue
        for slot, allowed_types in _STAGE_SLOT_TYPES[stage].items():
            if record["record_type"] in allowed_types:
                slots[slot].append(record)
                break
    scope_records = [record for values in slots.values() for record in values]
    scope_ids = {record["record_id"] for record in scope_records}
    blockers: set[str] = set()
    positive_statuses = {"retained", "sealed", "observed", "available"}
    for slot, values in slots.items():
        for record in values:
            payload = record["payload"]
            is_blocker = (
                (
                    slot == "evidence"
                    and (payload.get("tainted") or payload.get("status") not in positive_statuses)
                )
                or (
                    slot == "score"
                    and (
                        payload.get("score_status") != "observed" or payload.get("critical_failure")
                    )
                )
                or (slot == "exposure" and payload.get("tainted"))
                or (
                    slot in {"bridge", "comparability"}
                    and payload.get("outcome") not in {None, "bridge_comparable"}
                    and payload.get("eligible") is not True
                )
                or (
                    slot == "independence"
                    and (
                        payload.get("overall") != "separate"
                        or any(
                            str(status).casefold()
                            not in {
                                "separate",
                                "independent",
                                "disjoint",
                                "protected",
                                "pass",
                            }
                            for status in payload.get("dimensions", {}).values()
                        )
                    )
                )
                or (slot == "consumption" and not payload.get("consumed"))
                or (
                    slot == "anchor"
                    and (
                        payload.get("critical_failure")
                        or payload.get("status") not in positive_statuses
                    )
                )
            )
            if is_blocker:
                blockers.add(record["record_id"])
    required_slots = set(_STAGE_SLOT_TYPES[stage])
    if stage in {"bridge", "confirmation"}:
        # The three typed roots are the direct bridge closure contract.  Raw
        # panel cells/anchors/exposures are discovered through their exact
        # dependency graph and remain part of scope/blocker reconciliation,
        # but are not required as redundant direct evidence_refs.
        required_slots = (
            {"bridge", "comparability", "independence"}
            if stage == "bridge"
            else {"evidence", "binding", "score", "consumption", "anchor", "independence"}
        )
    return {
        "stage": stage,
        "candidate_ref": candidate_ref,
        "candidate_hash": candidate_hash,
        "slots": slots,
        "scope_ids": scope_ids,
        "blockers": blockers,
        "required_slots": required_slots,
    }


def _validate_predecessor_chain(
    chain: Sequence[Mapping[str, Any]], *, protocol: Mapping[str, Any] | None
) -> list[dict[str, Any]]:
    """Validate a genesis-to-immediate predecessor chain exactly once.

    Each successor is checked against the normalized predecessor immediately
    before it.  The first bundle must be a genesis bundle; callers therefore
    cannot smuggle an unproved ancestor through an immediate-only alias.
    """

    if not isinstance(chain, Sequence) or isinstance(chain, (str, bytes)) or not chain:
        _error("predecessor_chain_required", "predecessor_chain must be a non-empty array")
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(chain):
        if not _is_mapping(item):
            _error("invalid_type", f"predecessor_chain[{index}] must be a bundle object")
        if index == 0:
            current = validate_bundle(item, protocol=protocol)
        else:
            current = validate_bundle(
                item,
                protocol=protocol,
                predecessor=normalized[-1],
                _allow_unresolved_predecessor=True,
            )
        normalized.append(current)
    return normalized


def validate_bundle(
    bundle: Mapping[str, Any],
    *,
    protocol: Mapping[str, Any] | None = None,
    predecessor: Mapping[str, Any] | None = None,
    predecessor_chain: Sequence[Mapping[str, Any]] | None = None,
    _allow_unresolved_predecessor: bool = False,
) -> dict[str, Any]:
    """Validate hash-linked records and return a normalized bundle copy."""

    if not _is_mapping(bundle):
        _error("invalid_type", "bundle must be an object")
    _strict_keys(bundle, _BUNDLE_FIELDS, "bundle")
    if bundle.get("schema_version") != BUNDLE_SCHEMA_VERSION:
        _error("schema_version", f"bundle.schema_version must be {BUNDLE_SCHEMA_VERSION}")
    bundle_id = _require_string(bundle.get("bundle_id"), "bundle.bundle_id")
    protocol_ref = _require_string(bundle.get("protocol_ref"), "bundle.protocol_ref")
    protocol_digest = _require_hash(bundle.get("protocol_hash"), "bundle.protocol_hash")
    frozen: dict[str, Any] | None = None
    if protocol is not None:
        frozen = freeze_protocol(protocol)
        expected_protocol_hash = canonical_hash(frozen, domain="ael-cep-protocol")
        if protocol_ref != frozen["protocol_id"] or protocol_digest != expected_protocol_hash:
            _error(
                "protocol_mismatch",
                "bundle protocol_ref/hash does not match supplied frozen protocol",
            )
        epoch_id = frozen["epoch"]["epoch_id"]
    else:
        epoch_id = None

    predecessor_ref = bundle.get("predecessor")
    normalized_predecessor = None
    if predecessor_ref is not None:
        if not _is_mapping(predecessor_ref):
            _error("invalid_type", "bundle.predecessor must be an object or null")
        _strict_keys(predecessor_ref, {"bundle_ref", "bundle_hash"}, "bundle.predecessor")
        normalized_predecessor = {
            "bundle_ref": _require_string(
                predecessor_ref.get("bundle_ref"), "bundle.predecessor.bundle_ref"
            ),
            "bundle_hash": _require_hash(
                predecessor_ref.get("bundle_hash"), "bundle.predecessor.bundle_hash"
            ),
        }
    if predecessor is not None and predecessor_chain is not None:
        _error("predecessor_arguments", "supply predecessor or predecessor_chain, not both")
    prior: dict[str, Any] | None = None
    if predecessor_chain is not None:
        validated_chain = _validate_predecessor_chain(predecessor_chain, protocol=protocol)
        prior = validated_chain[-1]
        expected_predecessor = {
            "bundle_ref": prior["bundle_id"],
            "bundle_hash": prior["bundle_hash"],
        }
        if normalized_predecessor is None or normalized_predecessor != expected_predecessor:
            _error(
                "predecessor_mismatch",
                "bundle.predecessor does not identify the supplied predecessor_chain tail",
            )
    elif predecessor is not None:
        if not _is_mapping(predecessor):
            _error("invalid_type", "predecessor must be a bundle object")
        nested_predecessor = predecessor.get("predecessor")
        if nested_predecessor is not None and not _allow_unresolved_predecessor:
            _error(
                "predecessor_chain_required",
                "predecessor itself declares ancestry; supply the full predecessor_chain",
            )
        prior = validate_bundle(
            predecessor,
            protocol=protocol,
            _allow_unresolved_predecessor=_allow_unresolved_predecessor,
        )
        expected_predecessor = {
            "bundle_ref": prior["bundle_id"],
            "bundle_hash": prior["bundle_hash"],
        }
        if normalized_predecessor is None or normalized_predecessor != expected_predecessor:
            _error(
                "predecessor_mismatch",
                "bundle.predecessor does not identify the supplied predecessor",
            )
    elif normalized_predecessor is not None and not _allow_unresolved_predecessor:
        _error(
            "predecessor_required",
            "bundle declares a predecessor; supply and validate the predecessor bundle",
        )
    records_value = bundle.get("records")
    if not isinstance(records_value, Sequence) or isinstance(records_value, (str, bytes)):
        _error("invalid_type", "bundle.records must be an array")
    records = [_normalize_record(record, index) for index, record in enumerate(records_value)]
    if records:
        first_sequence = records[0]["sequence"]
        if first_sequence not in {0, 1}:
            _error("sequence_gap", "ledger sequence must start at 0 or 1")
    ids: set[str] = set()
    hashes: set[str] = set()
    by_id: dict[str, dict[str, Any]] = {}
    exposure_totals: dict[str, int | float] = {}
    total_exposure: int | float = 0
    consumed_confirmation_refs: set[str] = set()
    # A sealed confirmation task pack is globally single-use.  Candidate
    # labels are not part of this key: a second candidate cannot consume the
    # same frozen task root under a fresh evidence id.
    consumed_confirmation_task_roots: set[str] = set()
    consumed_bridge_roots: dict[str, str] = {}
    promotion_confirmation_consumers: dict[str, str] = {}
    promotion_candidate_hashes: dict[str, str] = {}
    promotion_states_by_candidate: dict[tuple[str, str], dict[str, str]] = {}
    promotion_transition_history: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    effect_idempotency_keys: dict[str, tuple[str, ...]] = {}
    confirmation_exposure_task_roots: set[str] = set()

    def _confirmation_task_root(target_ref: Any, target_hash: Any) -> str | None:
        """Resolve a confirmation exposure alias to its immutable task hash.

        Exposure records may target any typed evaluation surface admitted by
        the ledger (subject evidence, binding, score, consumption, or anchor).
        Candidate and record labels are mutable aliases; the frozen task hash
        is the single-use identity.  Resolution is deliberately local to the
        already-addressed prefix represented by ``by_id``.
        """

        pending: list[tuple[Any, Any]] = [(target_ref, target_hash)]
        seen: set[str] = set()
        while pending:
            ref, digest = pending.pop()
            if not isinstance(ref, str) or ref in seen:
                continue
            seen.add(ref)
            target = by_id.get(ref)
            if target is None or target.get("record_hash") != digest:
                continue
            payload = target["payload"]
            partition = payload.get("task_partition", payload.get("partition"))
            if partition != "confirmation":
                continue
            task_hash = payload.get("task_hash")
            if target["record_type"] == "subject_execution_evidence":
                return task_hash if isinstance(task_hash, str) else None
            if target["record_type"] in {"evaluation_binding", "score_run"}:
                evidence_ref = payload.get("evidence_ref")
                evidence_hash = payload.get("evidence_hash")
                if evidence_ref and evidence_hash:
                    pending.append((evidence_ref, evidence_hash))
            elif target["record_type"] == "confirmation_consumption":
                confirmation_ref = payload.get("confirmation_ref")
                confirmation_hash = payload.get("confirmation_hash")
                if confirmation_ref and confirmation_hash:
                    pending.append((confirmation_ref, confirmation_hash))
            elif target["record_type"] == "anchor_observation":
                consumption_ref = payload.get("confirmation_consumption_ref")
                consumption_hash = payload.get("confirmation_consumption_hash")
                if consumption_ref and consumption_hash:
                    pending.append((consumption_ref, consumption_hash))
        return None

    def _bridge_builder_axes(record: Mapping[str, Any]) -> set[tuple[str, str]]:
        """Resolve the builder generations represented by bridge-scoped facts.

        Bridge panel cells intentionally contain both the old and new builder
        generations.  A raw cell therefore resolves to its direct builder,
        while bridge/comparability/independence roots resolve to the candidate
        builder they claim.  Exposure targets are followed transitively so a
        bridge exposure cannot evade the stage-order gate by targeting an
        indirect score/binding surface.
        """

        record_type = record["record_type"]
        payload = record["payload"]
        axes: set[tuple[str, str]] = set()

        def add(ref: Any, digest: Any) -> None:
            if isinstance(ref, str) and isinstance(digest, str):
                axes.add((ref, digest))

        if record_type in {"subject_execution_evidence", "evaluation_binding", "score_run"}:
            partition = payload.get("partition", payload.get("task_partition"))
            if partition == "bridge":
                add(payload.get("builder_release_ref"), payload.get("builder_release_hash"))
        elif record_type == "anchor_observation":
            if payload.get("partition") == "bridge":
                add(payload.get("candidate_ref"), payload.get("candidate_hash"))
        elif record_type == "bridge_observation":
            add(payload.get("new_builder_ref"), payload.get("new_builder_hash"))
        elif record_type == "comparability_decision":
            bridge = by_id.get(payload.get("bridge_ref"))
            if bridge is not None and bridge["record_type"] == "bridge_observation":
                bridge_payload = bridge["payload"]
                add(bridge_payload.get("new_builder_ref"), bridge_payload.get("new_builder_hash"))
        elif record_type == "independence_assessment" and payload.get("stage") == "bridge":
            claim_ref = payload.get("claim_ref")
            claim = by_id.get(claim_ref)
            if claim is not None:
                add(claim_ref, claim["record_hash"])
        elif record_type == "exposure_event" and payload.get("partition") == "bridge":
            pending = [(payload.get("target_ref"), payload.get("target_hash"))]
            seen: set[str] = set()
            while pending:
                target_ref, target_hash = pending.pop()
                if not isinstance(target_ref, str) or target_ref in seen:
                    continue
                seen.add(target_ref)
                target = by_id.get(target_ref)
                if target is None or target.get("record_hash") != target_hash:
                    continue
                target_payload = target["payload"]
                target_partition = target_payload.get(
                    "partition", target_payload.get("task_partition")
                )
                if target_partition != "bridge":
                    continue
                target_type = target["record_type"]
                if target_type in {"subject_execution_evidence", "evaluation_binding", "score_run"}:
                    add(
                        target_payload.get("builder_release_ref"),
                        target_payload.get("builder_release_hash"),
                    )
                elif target_type == "anchor_observation":
                    add(target_payload.get("candidate_ref"), target_payload.get("candidate_hash"))
                elif target_type == "bridge_observation":
                    add(
                        target_payload.get("new_builder_ref"),
                        target_payload.get("new_builder_hash"),
                    )
                elif target_type == "comparability_decision":
                    bridge = by_id.get(target_payload.get("bridge_ref"))
                    if bridge is not None and bridge["record_type"] == "bridge_observation":
                        bridge_payload = bridge["payload"]
                        add(
                            bridge_payload.get("new_builder_ref"),
                            bridge_payload.get("new_builder_hash"),
                        )
                elif target_type == "independence_assessment":
                    claim = by_id.get(target_payload.get("claim_ref"))
                    if claim is not None:
                        add(target_payload.get("claim_ref"), claim["record_hash"])
                for dependency in target.get("dependency_refs", []):
                    if target_type in {
                        "evaluation_binding",
                        "score_run",
                        "anchor_observation",
                        "comparability_decision",
                        "independence_assessment",
                    }:
                        pending.append((dependency["record_id"], dependency["record_hash"]))
        return axes

    def _release_descends(candidate: tuple[str, str], ancestor: tuple[str, str]) -> bool:
        """Return whether a frozen candidate release descends one panel builder."""

        candidate_ref, candidate_hash = candidate
        ancestor_ref, ancestor_hash = ancestor
        current = by_id.get(candidate_ref)
        if current is None or current.get("record_hash") != candidate_hash:
            return False
        if candidate == ancestor:
            return True
        seen: set[str] = set()
        while current is not None and current["record_id"] not in seen:
            seen.add(current["record_id"])
            payload = current["payload"]
            parent_ref = payload.get("parent_release_ref")
            parent_hash = payload.get("parent_release_hash")
            if parent_ref == ancestor_ref and parent_hash == ancestor_hash:
                return True
            if not isinstance(parent_ref, str) or not isinstance(parent_hash, str):
                return False
            current = by_id.get(parent_ref)
            if current is None or current.get("record_hash") != parent_hash:
                return False
        return False

    def _has_prior_bridge_eligibility(axes: set[tuple[str, str]], sequence: int) -> bool:
        for transition in records:
            if transition["sequence"] >= sequence:
                break
            if transition["record_type"] != "promotion_transition":
                continue
            transition_payload = transition["payload"]
            if transition_payload.get("to_state") != "bridge_eligible":
                continue
            candidate = (
                transition_payload.get("candidate_ref"),
                transition_payload.get("candidate_hash"),
            )
            if not all(isinstance(value, str) for value in candidate):
                continue
            if any(_release_descends(candidate, axis) for axis in axes):
                return True
        return False

    for index, record in enumerate(records):
        record_id = record["record_id"]
        digest = record["record_hash"]
        if record_id in ids:
            _error("duplicate_id", f"ledger contains duplicate record_id {record_id}")
        if digest in hashes:
            _error("duplicate_hash", f"ledger contains duplicate record hash {digest}")
        ids.add(record_id)
        hashes.add(digest)
        by_id[record_id] = record
        expected_sequence = records[0]["sequence"] + index
        if record["sequence"] != expected_sequence:
            _error("sequence_gap", f"records[{index}].sequence is not contiguous")
        if index == 0:
            if record["previous_record_hash"] is not None:
                _error("chain_fork", "first record must have null previous_record_hash")
        elif record["previous_record_hash"] != records[index - 1]["record_hash"]:
            _error(
                "chain_fork",
                f"records[{index}] previous_record_hash does not bind the prior record",
            )
        if epoch_id is None:
            epoch_id = record["epoch_id"]
        if record["epoch_id"] != epoch_id:
            _error("epoch_mismatch", f"records[{index}] belongs to a different epoch")
        for dependency in record["dependency_refs"]:
            dependency_id = dependency["record_id"]
            if dependency_id not in by_id:
                _error(
                    "dangling_dependency",
                    f"records[{index}] depends on missing/future record {dependency_id}",
                )
            parent = by_id[dependency_id]
            if dependency["record_hash"] != parent["record_hash"]:
                _error(
                    "dependency_hash_mismatch",
                    f"records[{index}] dependency {dependency_id} has the wrong hash",
                )
        payload = record["payload"]
        bridge_axes = _bridge_builder_axes(record)
        if bridge_axes and not _has_prior_bridge_eligibility(bridge_axes, record["sequence"]):
            _error(
                "bridge_order",
                f"{record['record_id']} bridge evidence requires a prior candidate bridge_eligible transition",
            )
        if (
            record["record_type"]
            in {"builder_release", "evaluator_release", "challenger_release", "anchor_release"}
            and "parent_release_ref" in payload
        ):
            _bound_dependency(
                record,
                by_id,
                payload["parent_release_ref"],
                payload["parent_release_hash"],
                "parent_release_ref",
                expected_types={record["record_type"]},
            )
        if (
            record["record_type"] == "evaluator_release"
            and payload.get("self_certification") is True
        ):
            _error(
                "self_certification",
                f"{record['record_id']} evaluator self-certification is forbidden",
            )
        if frozen is not None and record["record_type"] in {
            "builder_release",
            "challenger_release",
            "evaluator_release",
        }:
            protected_labels = {
                label
                for principal in frozen["principals"].values()
                for label in (principal["principal_id"], principal["custody"])
            }
            if payload["custody"] in protected_labels:
                _error(
                    "custody_conflict",
                    f"{record['record_id']} release custody overlaps a frozen protected principal",
                )
        if (
            frozen is not None
            and record["record_type"] == "anchor_release"
            and payload["custody"] != frozen["principals"]["anchor"]["custody"]
        ):
            _error(
                "anchor_custody",
                f"{record['record_id']} anchor release custody differs from frozen anchor custody",
            )
        if record["record_type"] == "evaluation_binding":
            _bound_dependency(
                record,
                by_id,
                payload["builder_release_ref"],
                payload["builder_release_hash"],
                "builder_release_ref",
                expected_types={"builder_release"},
            )
            _bound_dependency(
                record,
                by_id,
                payload["evaluator_release_ref"],
                payload["evaluator_release_hash"],
                "evaluator_release_ref",
                expected_types={"evaluator_release"},
            )
            _bound_dependency(
                record,
                by_id,
                payload["method_ref"],
                payload["method_hash"],
                "method_ref",
                expected_types={"measurement_method"},
            )
            _bound_dependency(
                record,
                by_id,
                payload["evidence_ref"],
                payload["evidence_hash"],
                "evidence_ref",
                expected_types={"subject_execution_evidence"},
            )
            if payload["task_partition"] not in {
                "development",
                "screening",
                "bridge",
                "confirmation",
                "historical",
            }:
                _error(
                    "partition_identity", f"{record['record_id']} binds an unknown task partition"
                )
            evaluator = by_id[payload["evaluator_release_ref"]]
            evidence = by_id[payload["evidence_ref"]]
            for field in (
                "builder_release_ref",
                "builder_release_hash",
                "task_partition",
                "task_ref",
                "task_hash",
                "environment_ref",
                "environment_hash",
                "runner_ref",
                "runner_hash",
                "exposure_state_ref",
                "exposure_state_hash",
            ):
                if evidence["payload"].get(field) != payload.get(field):
                    _error(
                        "binding_identity",
                        f"{record['record_id']} evidence {field} differs from binding",
                    )
            if evidence["payload"].get("partition") != payload["task_partition"]:
                _error(
                    "binding_identity",
                    f"{record['record_id']} evidence partition differs from binding",
                )
            permitted_surfaces = set(evaluator["payload"].get("allowed_evidence_surface", []))
            if not set(payload["allowed_evidence_surface"]).issubset(permitted_surfaces):
                _error(
                    "surface_mismatch",
                    f"{record['record_id']} binding requests an evaluator-forbidden evidence surface",
                )
            allowed_task_hashes = (
                {frozen["partitions"][payload["task_partition"]]["task_root_hash"]}
                if frozen is not None
                else set()
            )
            if frozen is not None and payload["task_partition"] == "bridge":
                allowed_task_hashes.update(
                    item["task_root_hash"] for item in frozen["bridge"]["strata"]
                )
            if frozen is not None and payload["task_hash"] not in allowed_task_hashes:
                _error(
                    "task_identity",
                    f"{record['record_id']} task_hash must equal the frozen partition task root",
                )
            if frozen is not None:
                for binding_field, algorithm_key in (
                    ("analysis", "analysis"),
                    ("promotion_policy", "promotion"),
                ):
                    if (
                        payload[f"{binding_field}_ref"]
                        != frozen["algorithms"][algorithm_key]["ref"]
                        or payload[f"{binding_field}_hash"]
                        != frozen["algorithms"][algorithm_key]["hash"]
                    ):
                        _error(
                            "algorithm_identity",
                            f"{record['record_id']} {binding_field} identity must match the frozen protocol algorithm",
                        )
        elif record["record_type"] == "subject_execution_evidence":
            _bound_dependency(
                record,
                by_id,
                payload["builder_release_ref"],
                payload["builder_release_hash"],
                "builder_release_ref",
                expected_types={"builder_release"},
            )
            if payload["partition"] != payload["task_partition"]:
                _error(
                    "partition_identity",
                    f"{record['record_id']} evidence partition differs from task_partition",
                )
            allowed_task_hashes = (
                {frozen["partitions"][payload["task_partition"]]["task_root_hash"]}
                if frozen is not None
                else set()
            )
            if frozen is not None and payload["task_partition"] == "bridge":
                allowed_task_hashes.update(
                    item["task_root_hash"] for item in frozen["bridge"]["strata"]
                )
            if frozen is not None and payload["task_hash"] not in allowed_task_hashes:
                _error(
                    "task_identity",
                    f"{record['record_id']} evidence task_hash must equal the frozen partition task root",
                )
        elif record["record_type"] == "score_run":
            _bound_dependency(
                record,
                by_id,
                payload["binding_ref"],
                payload["binding_hash"],
                "binding_ref",
                expected_types={"evaluation_binding"},
            )
            if "receipt_ref" in payload:
                _bound_dependency(
                    record,
                    by_id,
                    payload["receipt_ref"],
                    payload["receipt_hash"],
                    "receipt_ref",
                )
            _bound_dependency(
                record,
                by_id,
                payload["evidence_ref"],
                payload["evidence_hash"],
                "evidence_ref",
                expected_types={"subject_execution_evidence"},
            )
            _bound_dependency(
                record,
                by_id,
                payload["evaluator_release_ref"],
                payload["evaluator_release_hash"],
                "evaluator_release_ref",
                expected_types={"evaluator_release"},
            )
            binding = by_id[payload["binding_ref"]]
            evidence = by_id[payload["evidence_ref"]]
            evaluator = by_id[payload["evaluator_release_ref"]]
            scoring_actor = _critical_string(
                payload["scoring_actor"], f"{record['record_id']}.payload.scoring_actor"
            )
            if frozen is not None:
                expected_actor = frozen["principals"]["adjudication"]["principal_id"]
                if scoring_actor != expected_actor:
                    _error(
                        "scoring_authority",
                        f"{record['record_id']} scoring_actor is not the frozen adjudication principal",
                    )
            evaluator_custody = evaluator["payload"].get("custody")
            adjudication_authorities = set()
            if frozen is not None:
                adjudication_authorities = {
                    frozen["principals"]["adjudication"]["principal_id"],
                    frozen["principals"]["adjudication"]["custody"],
                }
            if isinstance(evaluator_custody, str) and (
                scoring_actor == evaluator_custody or evaluator_custody in adjudication_authorities
            ):
                _error(
                    "self_certification",
                    f"{record['record_id']} evaluator custody overlaps scoring authority",
                )
            if (
                payload["evaluator_release_ref"] != binding["payload"]["evaluator_release_ref"]
                or payload["evaluator_release_hash"] != binding["payload"]["evaluator_release_hash"]
            ):
                _error(
                    "binding_identity",
                    f"{record['record_id']} score uses an evaluator different from its binding",
                )
            if (
                payload["evidence_ref"] != binding["payload"]["evidence_ref"]
                or payload["evidence_hash"] != binding["payload"]["evidence_hash"]
            ):
                _error(
                    "binding_identity",
                    f"{record['record_id']} score evidence differs from its binding",
                )
            if (
                payload["builder_release_ref"] != binding["payload"]["builder_release_ref"]
                or payload["builder_release_hash"] != binding["payload"]["builder_release_hash"]
                or payload["method_ref"] != binding["payload"]["method_ref"]
                or payload["method_hash"] != binding["payload"]["method_hash"]
            ):
                _error(
                    "binding_identity",
                    f"{record['record_id']} score uses a builder or method different from its binding",
                )
            if (
                payload["partition"] != binding["payload"]["task_partition"]
                or evidence["payload"]["partition"] != binding["payload"]["task_partition"]
            ):
                _error(
                    "binding_identity",
                    f"{record['record_id']} score/evidence partition differs from its binding",
                )
            for field in (
                "builder_release_ref",
                "builder_release_hash",
                "task_partition",
                "task_ref",
                "task_hash",
                "environment_ref",
                "environment_hash",
                "runner_ref",
                "runner_hash",
                "exposure_state_ref",
                "exposure_state_hash",
            ):
                if evidence["payload"].get(field) != binding["payload"].get(field):
                    _error(
                        "binding_identity",
                        f"{record['record_id']} evidence {field} differs from its binding",
                    )
            permitted = (
                set(binding["payload"].get("allowed_evidence_surface", []))
                & set(evidence["payload"].get("surface_refs", []))
                & set(evaluator["payload"].get("allowed_evidence_surface", []))
            )
            if not set(payload["surface_refs"]).issubset(permitted):
                _error(
                    "surface_mismatch",
                    f"{record['record_id']} score uses a surface not retained and permitted by its binding",
                )
        elif record["record_type"] == "exposure_event":
            target = by_id.get(payload["target_ref"])
            if (
                target is None
                or target["sequence"] >= record["sequence"]
                or payload["target_hash"] != target["record_hash"]
            ):
                _error(
                    "dangling_dependency",
                    f"{record['record_id']} exposure target is missing, future, or hash-mismatched",
                )
            if payload["target_ref"] not in {
                item["record_id"] for item in record["dependency_refs"]
            }:
                _error(
                    "missing_dependency_edge",
                    f"{record['record_id']} must bind exposure target {payload['target_ref']}",
                )
            target_partition = target["payload"].get(
                "task_partition", target["payload"].get("partition")
            )
            if target_partition != payload["partition"]:
                _error(
                    "partition_identity",
                    f"{record['record_id']} exposure partition differs from its target",
                )
            if frozen is not None:
                partition = payload["partition"]
                partition_total = exposure_totals.get(partition, 0) + payload["amount"]
                if partition_total > frozen["partitions"][partition]["exposure_budget"]:
                    _error(
                        "exposure_budget",
                        f"{record['record_id']} exceeds the frozen {partition} exposure budget",
                    )
                if total_exposure + payload["amount"] > frozen["budgets"]["exposure"]:
                    _error(
                        "exposure_budget",
                        f"{record['record_id']} exceeds the frozen total exposure budget",
                    )
                exposure_totals[partition] = partition_total
                total_exposure += payload["amount"]
                if partition == "confirmation":
                    confirmation_root = _confirmation_task_root(
                        payload["target_ref"], payload["target_hash"]
                    )
                    if confirmation_root is not None:
                        confirmation_exposure_task_roots.add(confirmation_root)
        elif record["record_type"] == "confirmation_consumption":
            target = by_id.get(payload["confirmation_ref"])
            if (
                target is None
                or target["record_type"] != "subject_execution_evidence"
                or target["sequence"] >= record["sequence"]
                or payload["confirmation_hash"] != target["record_hash"]
            ):
                _error(
                    "dangling_dependency",
                    f"{record['record_id']} confirmation reference is missing, future, or hash-mismatched",
                )
            if (
                target["payload"].get("partition") != "confirmation"
                and target["payload"].get("task_partition") != "confirmation"
            ):
                _error(
                    "confirmation_policy",
                    f"{record['record_id']} must consume a confirmation-partition record",
                )
            target_payload = target["payload"]
            if (
                target_payload.get("builder_release_ref") != payload["candidate_ref"]
                or target_payload.get("builder_release_hash") != payload["candidate_hash"]
            ):
                _error(
                    "confirmation_binding",
                    f"{record['record_id']} confirmation evidence must bind its candidate builder",
                )
            if target_payload.get("status") not in {
                "retained",
                "sealed",
                "observed",
                "available",
                "missing",
                "unavailable",
                "tainted",
                "failed",
                "unscorable",
                "revoked",
            }:
                _error(
                    "confirmation_policy",
                    f"{record['record_id']} confirmation evidence status is not admitted",
                )
            candidate = by_id.get(payload["candidate_ref"])
            if (
                candidate is None
                or candidate["sequence"] >= record["sequence"]
                or payload["candidate_hash"] != candidate["record_hash"]
            ):
                _error(
                    "dangling_dependency",
                    f"{record['record_id']} candidate reference is missing, future, or hash-mismatched",
                )
            deps = {item["record_id"]: item["record_hash"] for item in record["dependency_refs"]}
            if deps.get(payload["confirmation_ref"]) != target["record_hash"]:
                _error(
                    "missing_dependency_edge",
                    f"{record['record_id']} must bind its confirmation pack",
                )
            if deps.get(payload["candidate_ref"]) != candidate["record_hash"]:
                _error("missing_dependency_edge", f"{record['record_id']} must bind its candidate")
            if frozen is not None:
                expected_authority = frozen["principals"]["confirmation"]["principal_id"]
                if payload["authority"] != expected_authority:
                    _error(
                        "confirmation_authority",
                        f"{record['record_id']} is not opened by the frozen confirmation principal",
                    )
            if payload.get("consumed"):
                if payload["confirmation_ref"] in consumed_confirmation_refs:
                    _error(
                        "confirmation_reuse",
                        f"{record['record_id']} confirmation artifact is consumed more than once",
                    )
                task_root = target_payload.get("task_hash")
                if not isinstance(task_root, str) or not task_root:
                    _error(
                        "confirmation_policy",
                        f"{record['record_id']} confirmation evidence must carry a task hash",
                    )
                if task_root in consumed_confirmation_task_roots:
                    _error(
                        "confirmation_reuse",
                        f"{record['record_id']} duplicates a consumed confirmation task/root",
                    )
                consumed_confirmation_refs.add(payload["confirmation_ref"])
                consumed_confirmation_task_roots.add(task_root)
        elif record["record_type"] == "anchor_observation":
            candidate = by_id.get(payload["candidate_ref"])
            if (
                candidate is None
                or candidate["sequence"] >= record["sequence"]
                or candidate["record_hash"] != payload["candidate_hash"]
                or candidate["record_type"] in {"promotion_transition", "deletion_tombstone"}
            ):
                _error(
                    "anchor_candidate",
                    f"{record['record_id']} anchor candidate_ref/hash must resolve to a stable prior record",
                )
            _bound_dependency(
                record,
                by_id,
                payload["candidate_ref"],
                payload["candidate_hash"],
                "candidate_ref",
            )
            _bound_dependency(
                record,
                by_id,
                payload["anchor_release_ref"],
                payload["anchor_release_hash"],
                "anchor_release_ref",
                expected_types={"anchor_release"},
            )
            if payload["partition"] == "confirmation":
                if "evidence_ref" in payload or "evidence_hash" in payload:
                    _error(
                        "anchor_policy",
                        f"{record['record_id']} confirmation anchor must not bind bridge evidence",
                    )
                _bound_dependency(
                    record,
                    by_id,
                    payload["confirmation_consumption_ref"],
                    payload["confirmation_consumption_hash"],
                    "confirmation_consumption_ref",
                    expected_types={"confirmation_consumption"},
                )
                consumption = by_id[payload["confirmation_consumption_ref"]]
                consumption_payload = consumption["payload"]
                if (
                    consumption_payload["partition"] != "confirmation"
                    or consumption_payload["candidate_ref"] != payload["candidate_ref"]
                    or consumption_payload["candidate_hash"] != payload["candidate_hash"]
                ):
                    _error(
                        "anchor_policy",
                        f"{record['record_id']} anchor observation must bind the same confirmation candidate",
                    )
                if not consumption_payload.get("consumed"):
                    _error(
                        "confirmation_policy",
                        f"{record['record_id']} confirmation anchor requires consumed confirmation evidence",
                    )
                if frozen is not None:
                    decision_rule = frozen["decision_rule"]
                    allowed_confirmation_statuses = {
                        decision_rule["required_status"],
                        "missing",
                        "unavailable",
                        "tainted",
                        "failed",
                        "unscorable",
                        "revoked",
                    }
                    if payload["status"] not in allowed_confirmation_statuses:
                        _error(
                            "confirmation_policy",
                            f"{record['record_id']} confirmation anchor status is not admitted",
                        )
            elif payload["partition"] == "bridge":
                if "evidence_ref" not in payload or "evidence_hash" not in payload:
                    _error(
                        "anchor_policy",
                        f"{record['record_id']} bridge anchor must bind exact subject evidence",
                    )
                _bound_dependency(
                    record,
                    by_id,
                    payload["evidence_ref"],
                    payload["evidence_hash"],
                    "evidence_ref",
                    expected_types={"subject_execution_evidence"},
                )
                evidence = by_id[payload["evidence_ref"]]["payload"]
                if (
                    evidence.get("partition") != "bridge"
                    or evidence.get("builder_release_ref") != payload["candidate_ref"]
                    or evidence.get("builder_release_hash") != payload["candidate_hash"]
                ):
                    _error(
                        "anchor_policy",
                        f"{record['record_id']} bridge anchor evidence must match its builder candidate",
                    )
                if (
                    "confirmation_consumption_ref" in payload
                    or "confirmation_consumption_hash" in payload
                ):
                    _error(
                        "anchor_policy",
                        f"{record['record_id']} bridge anchor must not bind confirmation consumption",
                    )
            if frozen is not None:
                expected_authority = frozen["principals"]["anchor"]["principal_id"]
                if payload["authority"] != expected_authority:
                    _error(
                        "anchor_authority",
                        f"{record['record_id']} is not adjudicated by the frozen anchor principal",
                    )
                anchor_release = by_id[payload["anchor_release_ref"]]["payload"]
                if anchor_release.get("custody") != frozen["principals"]["anchor"].get("custody"):
                    _error(
                        "anchor_custody",
                        f"{record['record_id']} anchor release custody differs from frozen anchor custody",
                    )
        elif record["record_type"] == "effect_attempt":
            # AEL-CEP Stage 0 is a forbidden-effect policy.  ``accepted`` is
            # retained in the language-neutral schema so future stages can
            # represent a receipt, but this frozen protocol admits only a
            # blocked request that was never dispatched.  Quarantine,
            # ambiguity, or any applied/confirmed postcondition is not a
            # valid Stage 0 ledger fact.
            if (
                payload.get("disposition") != "blocked"
                or payload.get("postcondition_status") != "not_dispatched"
            ):
                _error(
                    "effect_forbidden",
                    f"{record['record_id']} effect disposition/postcondition is not admitted by the frozen protocol",
                )
            if "receipt_ref" in payload or "receipt_hash" in payload:
                _error(
                    "effect_forbidden",
                    f"{record['record_id']} blocked Stage 0 effect cannot carry a receipt",
                )
            idempotency_key = payload["idempotency_key_hash"]
            effect_identity = (
                payload["candidate_ref"],
                payload["candidate_hash"],
                payload["binding_ref"],
                payload["binding_hash"],
                payload["evidence_ref"],
                payload["evidence_hash"],
                payload["effect_request_hash"],
            )
            prior_effect_identity = effect_idempotency_keys.get(idempotency_key)
            if prior_effect_identity is not None and prior_effect_identity != effect_identity:
                _error(
                    "duplicate_idempotency",
                    f"{record['record_id']} idempotency hash is reused for different effect inputs",
                )
            effect_idempotency_keys[idempotency_key] = effect_identity
            candidate = by_id.get(payload["candidate_ref"])
            if (
                candidate is None
                or candidate["sequence"] >= record["sequence"]
                or candidate["record_hash"] != payload["candidate_hash"]
                or candidate["record_type"] in {"promotion_transition", "deletion_tombstone"}
            ):
                _error(
                    "effect_binding",
                    f"{record['record_id']} effect candidate is missing or unstable",
                )
            _bound_dependency(
                record,
                by_id,
                payload["candidate_ref"],
                payload["candidate_hash"],
                "candidate_ref",
            )
            _bound_dependency(
                record,
                by_id,
                payload["evidence_ref"],
                payload["evidence_hash"],
                "evidence_ref",
                expected_types={"subject_execution_evidence"},
            )
            _bound_dependency(
                record,
                by_id,
                payload["binding_ref"],
                payload["binding_hash"],
                "binding_ref",
                expected_types={"evaluation_binding"},
            )
            evidence = by_id[payload["evidence_ref"]]["payload"]
            binding = by_id[payload["binding_ref"]]["payload"]
            if (
                binding.get("evidence_ref") != payload["evidence_ref"]
                or binding.get("evidence_hash") != payload["evidence_hash"]
                or evidence.get("partition") != payload["partition"]
                or binding.get("task_partition") != payload["partition"]
            ):
                _error(
                    "effect_binding",
                    f"{record['record_id']} effect axes do not match evidence/binding",
                )
            if candidate["record_type"] == "builder_release" and (
                evidence.get("builder_release_ref") != payload["candidate_ref"]
                or evidence.get("builder_release_hash") != payload["candidate_hash"]
            ):
                _error(
                    "effect_binding",
                    f"{record['record_id']} effect candidate differs from evidence builder",
                )
            if candidate["record_type"] == "score_run" and (
                candidate["payload"].get("evidence_ref") != payload["evidence_ref"]
                or candidate["payload"].get("evidence_hash") != payload["evidence_hash"]
            ):
                _error(
                    "effect_binding",
                    f"{record['record_id']} effect candidate differs from score evidence",
                )
            if (
                frozen is not None
                and payload["observation_authority"]
                != frozen["principals"]["evidence"]["principal_id"]
            ):
                _error(
                    "effect_authority",
                    f"{record['record_id']} effect authority is not frozen evidence",
                )
        elif record["record_type"] == "bridge_observation":
            if payload["old_builder_ref"] == payload["new_builder_ref"]:
                _error(
                    "bridge_identity",
                    f"{record['record_id']} bridge builders must be distinct generations",
                )
            if payload["old_evaluator_ref"] == payload["new_evaluator_ref"]:
                _error(
                    "bridge_identity",
                    f"{record['record_id']} bridge old/new evaluator releases must be distinct",
                )
            _bound_dependency(
                record,
                by_id,
                payload["old_builder_ref"],
                payload["old_builder_hash"],
                "old_builder_ref",
                expected_types={"builder_release"},
            )
            _bound_dependency(
                record,
                by_id,
                payload["new_builder_ref"],
                payload["new_builder_hash"],
                "new_builder_ref",
                expected_types={"builder_release"},
            )
            _bound_dependency(
                record,
                by_id,
                payload["old_evaluator_ref"],
                payload["old_evaluator_hash"],
                "old_evaluator_ref",
                expected_types={"evaluator_release"},
            )
            _bound_dependency(
                record,
                by_id,
                payload["new_evaluator_ref"],
                payload["new_evaluator_hash"],
                "new_evaluator_ref",
                expected_types={"evaluator_release"},
            )
            _bound_dependency(
                record,
                by_id,
                payload["anchor_release_ref"],
                payload["anchor_release_hash"],
                "anchor_release_ref",
                expected_types={"anchor_release"},
            )
            new_builder = by_id[payload["new_builder_ref"]]
            new_evaluator = by_id[payload["new_evaluator_ref"]]
            if (
                new_builder["payload"].get("parent_release_ref") != payload["old_builder_ref"]
                or new_builder["payload"].get("parent_release_hash") != payload["old_builder_hash"]
            ):
                _error(
                    "bridge_identity", f"{record['record_id']} new builder must descend old builder"
                )
            if (
                new_evaluator["payload"].get("parent_release_ref") != payload["old_evaluator_ref"]
                or new_evaluator["payload"].get("parent_release_hash")
                != payload["old_evaluator_hash"]
            ):
                _error(
                    "bridge_identity",
                    f"{record['record_id']} new evaluator must descend old evaluator",
                )
            if frozen is not None:
                anchor_release = by_id[payload["anchor_release_ref"]]["payload"]
                if anchor_release.get("custody") != frozen["principals"]["anchor"].get("custody"):
                    _error(
                        "anchor_custody",
                        f"{record['record_id']} bridge anchor release custody is not the frozen anchor custody",
                    )
            threshold = _require_number(
                payload["decision_threshold"], f"{record['record_id']}.decision_threshold"
            )
            if not 0 <= threshold <= 1:
                _error(
                    "bridge_threshold",
                    f"{record['record_id']} decision_threshold must be between 0 and 1",
                )
            if frozen is not None and not math.isclose(
                threshold,
                float(frozen["decision_rule"]["threshold"]),
                rel_tol=0.0,
                abs_tol=1e-12,
            ):
                _error(
                    "bridge_threshold",
                    f"{record['record_id']} decision_threshold must equal the frozen decision rule",
                )
            expected_strata = {
                item["stratum"]: item for item in (frozen or {}).get("bridge", {}).get("strata", [])
            }
            if not expected_strata:
                _error("bridge_insufficient", f"{record['record_id']} has no frozen bridge strata")
            supplied_names = {item["stratum"] for item in payload["strata"]}
            if supplied_names != set(expected_strata):
                _error(
                    "bridge_insufficient",
                    f"{record['record_id']} bridge strata do not match frozen strata",
                )
            designated_stratum = payload["strata"][0]
            designated_fields = (
                "old_evidence",
                "new_evidence",
                "b0e0_score",
                "b0e1_score",
                "b1e0_score",
                "b1e1_score",
            )
            top_level_fields = {
                "old_evidence": "old_evidence",
                "new_evidence": "new_evidence",
                "b0e0_score": "old_builder_old_evaluator_score",
                "b0e1_score": "old_builder_new_evaluator_score",
                "b1e0_score": "new_builder_old_evaluator_score",
                "b1e1_score": "new_builder_new_evaluator_score",
            }
            for designated_field in designated_fields:
                top_level_field = top_level_fields[designated_field]
                for suffix in ("_ref", "_hash"):
                    if (
                        payload[f"{top_level_field}{suffix}"]
                        != designated_stratum[f"{designated_field}{suffix}"]
                    ):
                        _error(
                            "bridge_identity",
                            f"{record['record_id']} top-level {top_level_field} must resolve the designated {designated_stratum['stratum']} stratum",
                        )
            cell_names = (
                (
                    "b0e0",
                    payload["old_builder_ref"],
                    payload["old_evaluator_ref"],
                    "old_evidence_ref",
                ),
                (
                    "b0e1",
                    payload["old_builder_ref"],
                    payload["new_evaluator_ref"],
                    "old_evidence_ref",
                ),
                (
                    "b1e0",
                    payload["new_builder_ref"],
                    payload["old_evaluator_ref"],
                    "new_evidence_ref",
                ),
                (
                    "b1e1",
                    payload["new_builder_ref"],
                    payload["new_evaluator_ref"],
                    "new_evidence_ref",
                ),
            )
            weighted_global = 0.0
            weighted_interaction = 0.0
            weighted_decision = 0.0
            weighted_anchor = 0.0
            stratum_gate_ok = True
            bridge_method_identity: tuple[str, str] | None = None
            seen_panel_refs: set[str] = set()
            seen_panel_hashes: set[str] = set()
            for stratum in payload["strata"]:
                name = stratum["stratum"]
                if not math.isclose(
                    float(stratum["weight"]),
                    float(expected_strata[name]["weight"]),
                    rel_tol=0.0,
                    abs_tol=1e-12,
                ):
                    _error(
                        "bridge_insufficient",
                        f"{record['record_id']} stratum weight differs from protocol",
                    )
                expected_task_root = expected_strata[name]["task_root_hash"]
                current_panel_refs = {stratum[field] for field in stratum if field.endswith("_ref")}
                current_panel_hashes = {
                    stratum[field] for field in stratum if field.endswith("_hash")
                }
                if seen_panel_refs & current_panel_refs or seen_panel_hashes & current_panel_hashes:
                    _error(
                        "bridge_insufficient",
                        f"{record['record_id']} bridge strata must not reuse evidence, cell, or anchor identities",
                    )
                seen_panel_refs.update(current_panel_refs)
                seen_panel_hashes.update(current_panel_hashes)
                scores: dict[str, Mapping[str, Any]] = {}
                anchors: dict[str, Mapping[str, Any]] = {}
                for cell, builder_ref, evaluator_ref, evidence_key in cell_names:
                    score_ref = stratum[f"{cell}_score_ref"]
                    score_hash = stratum[f"{cell}_score_hash"]
                    _bound_dependency(
                        record,
                        by_id,
                        score_ref,
                        score_hash,
                        f"strata.{name}.{cell}_score_ref",
                        expected_types={"score_run"},
                    )
                    score_record = by_id[score_ref]
                    score_payload = score_record["payload"]
                    binding_record = by_id.get(score_payload.get("binding_ref"))
                    evidence_ref = stratum[f"{evidence_key}"]
                    evidence_hash = stratum[f"{evidence_key.replace('_ref', '_hash')}"]
                    _bound_dependency(
                        record,
                        by_id,
                        evidence_ref,
                        evidence_hash,
                        f"strata.{name}.{evidence_key}",
                        expected_types={"subject_execution_evidence"},
                    )
                    evidence_record = by_id[evidence_ref]
                    if (
                        score_payload.get("builder_release_ref") != builder_ref
                        or score_payload.get("builder_release_hash")
                        != by_id[builder_ref]["record_hash"]
                        or score_payload.get("evaluator_release_ref") != evaluator_ref
                        or score_payload.get("evaluator_release_hash")
                        != by_id[evaluator_ref]["record_hash"]
                        or score_payload.get("evidence_ref") != evidence_ref
                        or score_payload.get("evidence_hash") != evidence_record["record_hash"]
                        or score_payload.get("partition") != "bridge"
                        or score_payload.get("score_status") != "observed"
                        or binding_record is None
                        or binding_record["payload"].get("method_ref")
                        != score_payload.get("method_ref")
                        or binding_record["payload"].get("method_hash")
                        != score_payload.get("method_hash")
                    ):
                        _error(
                            "bridge_insufficient",
                            f"{record['record_id']} {name}/{cell} score axes are not exact",
                        )
                    method_identity = (
                        str(score_payload["method_ref"]),
                        str(score_payload["method_hash"]),
                    )
                    if bridge_method_identity is None:
                        bridge_method_identity = method_identity
                    elif bridge_method_identity != method_identity:
                        _error(
                            "bridge_insufficient",
                            f"{record['record_id']} bridge score cells must share one measurement method",
                        )
                    scores[cell] = score_payload
                old_evidence_ref = stratum["old_evidence_ref"]
                new_evidence_ref = stratum["new_evidence_ref"]
                old_evidence = by_id[old_evidence_ref]["payload"]
                new_evidence = by_id[new_evidence_ref]["payload"]
                for evidence in (old_evidence, new_evidence):
                    if evidence.get("partition") != "bridge":
                        _error(
                            "bridge_insufficient",
                            f"{record['record_id']} bridge evidence must be bridge partition",
                        )
                    if evidence.get("status") not in {
                        "retained",
                        "observed",
                        "available",
                        "sealed",
                    }:
                        _error(
                            "bridge_insufficient",
                            f"{record['record_id']} bridge evidence status is not an admitted positive status",
                        )
                    if evidence.get("task_hash") != expected_task_root:
                        _error(
                            "bridge_insufficient",
                            f"{record['record_id']} {name} evidence must bind its frozen stratum task root",
                        )
                if frozen is not None and frozen["partitions"]["bridge"]["single_use"]:
                    previous_bridge = consumed_bridge_roots.get(expected_task_root)
                    if previous_bridge is not None and previous_bridge != record["record_id"]:
                        _error(
                            "bridge_reuse",
                            f"{record['record_id']} reuses frozen bridge task root {expected_task_root}",
                        )
                    consumed_bridge_roots[expected_task_root] = record["record_id"]
                for field in (
                    "task_ref",
                    "task_hash",
                    "environment_ref",
                    "environment_hash",
                    "runner_ref",
                    "runner_hash",
                    "exposure_state_ref",
                    "exposure_state_hash",
                ):
                    if old_evidence.get(field) != new_evidence.get(field):
                        _error(
                            "bridge_insufficient",
                            f"{record['record_id']} bridge evidence {field} differs across builder generations",
                        )
                for anchor_key, builder_ref in (
                    ("b0_anchor", payload["old_builder_ref"]),
                    ("b1_anchor", payload["new_builder_ref"]),
                ):
                    anchor_ref = stratum[f"{anchor_key}_ref"]
                    anchor_hash = stratum[f"{anchor_key}_hash"]
                    _bound_dependency(
                        record,
                        by_id,
                        anchor_ref,
                        anchor_hash,
                        f"strata.{name}.{anchor_key}_ref",
                        expected_types={"anchor_observation"},
                    )
                    anchor_payload = by_id[anchor_ref]["payload"]
                    if (
                        anchor_payload.get("partition") != "bridge"
                        or anchor_payload.get("candidate_ref") != builder_ref
                        or anchor_payload.get("candidate_hash") != by_id[builder_ref]["record_hash"]
                        or anchor_payload.get("anchor_release_ref") != payload["anchor_release_ref"]
                        or anchor_payload.get("anchor_release_hash")
                        != payload["anchor_release_hash"]
                        or anchor_payload.get("status") != "observed"
                    ):
                        _error(
                            "bridge_insufficient",
                            f"{record['record_id']} {name}/{anchor_key} is not a valid bridge anchor",
                        )
                    expected_evidence_key = (
                        "old_evidence_ref" if anchor_key == "b0_anchor" else "new_evidence_ref"
                    )
                    expected_evidence_ref = stratum[expected_evidence_key]
                    expected_evidence_hash = stratum[expected_evidence_key.replace("_ref", "_hash")]
                    if (
                        anchor_payload.get("evidence_ref") != expected_evidence_ref
                        or anchor_payload.get("evidence_hash") != expected_evidence_hash
                    ):
                        _error(
                            "bridge_insufficient",
                            f"{record['record_id']} {name}/{anchor_key} must bind its exact generation evidence",
                        )
                    anchors[anchor_key] = anchor_payload
                y00, y01, y10, y11 = (
                    float(scores[cell]["score"]) for cell in ("b0e0", "b0e1", "b1e0", "b1e1")
                )
                global_shift = ((y01 - y00) + (y11 - y10)) / 2.0
                interaction = (y11 - y01) - (y10 - y00)
                decision_agreement = 0.5 * float(
                    (y00 >= threshold) == (y01 >= threshold)
                ) + 0.5 * float((y10 >= threshold) == (y11 >= threshold))
                anchor_agreement = _derive_anchor_decision_agreement(
                    scores,
                    anchors,
                    threshold,
                    f"{record['record_id']}.strata.{name}",
                )
                stratum_gate_ok = stratum_gate_ok and (
                    abs(global_shift) <= float(frozen["bridge"]["global_shift_tolerance"])
                    and abs(interaction) <= float(frozen["bridge"]["interaction_tolerance"])
                    and decision_agreement >= float(frozen["bridge"]["decision_agreement_min"])
                    and anchor_agreement >= float(frozen["bridge"]["decision_agreement_min"])
                )
                weighted_global += float(stratum["weight"]) * global_shift
                weighted_interaction += float(stratum["weight"]) * interaction
                weighted_decision += float(stratum["weight"]) * decision_agreement
                weighted_anchor += float(stratum["weight"]) * anchor_agreement
            for key, expected in (
                ("global_shift_interval", weighted_global),
                ("interaction_interval", weighted_interaction),
            ):
                interval = payload[key]
                if (
                    len(interval) != 2
                    or not math.isclose(float(interval[0]), expected, rel_tol=0.0, abs_tol=1e-12)
                    or not math.isclose(float(interval[1]), expected, rel_tol=0.0, abs_tol=1e-12)
                ):
                    _error(
                        "bridge_mismatch",
                        f"{record['record_id']} {key} must be the exact derived degenerate interval",
                    )
            if not math.isclose(
                float(payload["decision_agreement"]), weighted_decision, rel_tol=0.0, abs_tol=1e-12
            ) or not math.isclose(
                float(payload["anchor_agreement"]), weighted_anchor, rel_tol=0.0, abs_tol=1e-12
            ):
                _error(
                    "bridge_mismatch",
                    f"{record['record_id']} agreement metrics do not match bridge cells",
                )
            expected_outcome = evaluate_bridge(
                payload,
                tolerances={
                    "global_shift": frozen["bridge"]["global_shift_tolerance"] if frozen else 0.0,
                    "interaction": frozen["bridge"]["interaction_tolerance"] if frozen else 0.0,
                    "agreement": frozen["bridge"]["decision_agreement_min"] if frozen else 1.0,
                },
                expected_strata=frozen["bridge"]["strata"] if frozen else None,
                per_stratum_gate=stratum_gate_ok,
            )["outcome"]
            if payload.get("outcome") != expected_outcome:
                _error(
                    "bridge_mismatch",
                    f"{record['record_id']} outcome does not match frozen bridge policy",
                )
        elif record["record_type"] == "comparability_decision":
            _bound_dependency(
                record,
                by_id,
                payload["bridge_ref"],
                payload["bridge_hash"],
                "bridge_ref",
                expected_types={"bridge_observation"},
            )
            if frozen is not None:
                bridge = by_id[payload["bridge_ref"]]["payload"]
                tolerances = {
                    "global_shift": frozen["bridge"]["global_shift_tolerance"],
                    "interaction": frozen["bridge"]["interaction_tolerance"],
                    "agreement": frozen["bridge"]["decision_agreement_min"],
                }
                panel_gate = _derive_bridge_panel_gate(
                    bridge,
                    by_id,
                    threshold=float(bridge["decision_threshold"]),
                    global_tolerance=float(tolerances["global_shift"]),
                    interaction_tolerance=float(tolerances["interaction"]),
                    agreement_min=float(tolerances["agreement"]),
                    path=f"{record['record_id']}.bridge",
                )
                expected = evaluate_bridge(
                    bridge,
                    tolerances=tolerances,
                    expected_strata=frozen["bridge"]["strata"],
                    per_stratum_gate=panel_gate["strata_gate"],
                )["outcome"]
                if payload["outcome"] != expected or payload["eligible"] != (
                    expected == "bridge_comparable"
                ):
                    _error(
                        "comparability_mismatch",
                        f"{record['record_id']} does not match the frozen bridge decision",
                    )
        elif record["record_type"] == "independence_assessment":
            if (
                frozen is not None
                and payload["authority"] != frozen["principals"]["adjudication"]["principal_id"]
            ):
                _error(
                    "independence_authority",
                    f"{record['record_id']} independence assessment is not issued by the frozen adjudication principal",
                )
            if frozen is not None:
                protected = set(frozen["independence"]["protected_dimensions"])
                if set(payload["dimensions"]) != protected:
                    _error(
                        "independence_dimensions",
                        f"{record['record_id']} independence dimensions must equal the frozen protected dimensions",
                    )
            allowed_independence = {
                "separate",
                "independent",
                "disjoint",
                "protected",
                "pass",
            }
            expected_overall = (
                "separate"
                if all(
                    str(status).casefold() in allowed_independence
                    for status in payload["dimensions"].values()
                )
                else "overlap"
            )
            if payload["overall"].casefold() != expected_overall:
                _error(
                    "independence_mismatch",
                    f"{record['record_id']} overall does not match the worst-case independence dimension",
                )
            dependencies = {
                item["record_id"]: item["record_hash"] for item in record["dependency_refs"]
            }
            if len(payload["evidence_refs"]) != len(set(payload["evidence_refs"])):
                _error(
                    "independence_evidence",
                    f"{record['record_id']} independence evidence contains duplicate references",
                )
            for evidence_ref in payload["evidence_refs"]:
                evidence_record = by_id.get(evidence_ref)
                if evidence_record is None or evidence_record["sequence"] >= record["sequence"]:
                    _error(
                        "dangling_dependency",
                        f"{record['record_id']} independence evidence is missing or future",
                    )
                if dependencies.get(evidence_ref) != evidence_record["record_hash"]:
                    _error(
                        "missing_dependency_edge",
                        f"{record['record_id']} must bind independence evidence {evidence_ref}",
                    )
            custody_status = payload["dimensions"].get("custody")
            if str(custody_status).casefold() in {
                "separate",
                "independent",
                "disjoint",
                "protected",
                "pass",
            }:
                release_ids: set[str] = set()

                def collect_release_ids(
                    item: Mapping[str, Any] | None, target: set[str] = release_ids
                ) -> None:
                    if item is None:
                        return
                    item_type = item["record_type"]
                    item_payload = item["payload"]
                    if item_type.endswith("_release"):
                        target.add(item["record_id"])
                        return
                    if item_type == "bridge_observation":
                        for field in (
                            "old_builder_ref",
                            "new_builder_ref",
                            "old_evaluator_ref",
                            "new_evaluator_ref",
                            "anchor_release_ref",
                        ):
                            collect_release_ids(by_id.get(item_payload.get(field)))
                    elif item_type == "comparability_decision":
                        collect_release_ids(by_id.get(item_payload.get("bridge_ref")))
                    elif item_type == "anchor_observation":
                        collect_release_ids(by_id.get(item_payload.get("candidate_ref")))
                        collect_release_ids(by_id.get(item_payload.get("anchor_release_ref")))
                    elif item_type in {"score_run", "evaluation_binding"}:
                        for field in ("builder_release_ref", "evaluator_release_ref"):
                            collect_release_ids(by_id.get(item_payload.get(field)))

                collect_release_ids(by_id.get(payload["claim_ref"]))
                for evidence_ref in payload["evidence_refs"]:
                    collect_release_ids(by_id.get(evidence_ref))
                release_types = {
                    by_id[release_id]["record_type"]
                    for release_id in release_ids
                    if release_id in by_id
                }
                required_release_types = {
                    "builder_release",
                    "evaluator_release",
                    "anchor_release",
                }
                missing_release_types = sorted(required_release_types - release_types)
                if missing_release_types:
                    _error(
                        "independence_custody",
                        f"{record['record_id']} protected custody assessment is missing release role(s): {', '.join(missing_release_types)}",
                    )
                role_custodies = {
                    "builder_release": set(),
                    "evaluator_release": set(),
                    "anchor_release": set(),
                }
                for release_id in release_ids:
                    release_record = by_id.get(release_id)
                    if release_record is None:
                        continue
                    release_type = release_record["record_type"]
                    if release_type in role_custodies:
                        role_custodies[release_type].add(release_record["payload"].get("custody"))
                role_pairs = (
                    ("builder_release", "evaluator_release"),
                    ("builder_release", "anchor_release"),
                    ("evaluator_release", "anchor_release"),
                )
                if any(role_custodies[left] & role_custodies[right] for left, right in role_pairs):
                    _error(
                        "independence_custody",
                        f"{record['record_id']} protected custody assessment has overlapping release custody",
                    )
        elif record["record_type"] == "trajectory_summary":
            if frozen is not None:
                if payload["arm"] not in frozen["arms"]:
                    _error(
                        "summary_arm",
                        f"{record['record_id']} trajectory summary arm is not a frozen A0-A5 arm",
                    )
                if payload["scenario_ref"] not in _frozen_scenario_refs(frozen):
                    _error(
                        "summary_scenario",
                        f"{record['record_id']} scenario_ref must identify one frozen simulation scenario",
                    )
                if not math.isclose(
                    payload["budget"]["target"],
                    frozen["budgets"]["total_system"],
                    rel_tol=0.0,
                    abs_tol=1e-12,
                ):
                    _error(
                        "summary_budget",
                        f"{record['record_id']} budget target differs from frozen total-system budget",
                    )
                scenario = _frozen_scenarios_by_ref(frozen).get(payload["scenario_ref"])
                if scenario is None:
                    _error(
                        "summary_scenario",
                        f"{record['record_id']} scenario_ref must identify a frozen scenario",
                    )
                _validate_trajectory_counts(
                    payload["counts"], f"{record['record_id']}.counts", scenario=scenario
                )
            else:
                _validate_trajectory_counts(payload["counts"], f"{record['record_id']}.counts")
            _validate_primary_endpoint(
                payload["primary_endpoint"], f"{record['record_id']}.primary_endpoint"
            )
        elif record["record_type"] == "contrast_summary":
            if payload["aggregation_version"] != CONTRAST_SUMMARY_AGGREGATION_VERSION:
                _error(
                    "summary_version",
                    f"{record['record_id']} uses an unsupported aggregation version",
                )
        elif record["record_type"] == "promotion_transition":
            candidate = by_id.get(payload["candidate_ref"])
            if (
                candidate is None
                or candidate["sequence"] >= record["sequence"]
                or candidate["record_hash"] != payload["candidate_hash"]
                or candidate["record_type"] in {"promotion_transition", "deletion_tombstone"}
            ):
                _error(
                    "promotion_candidate",
                    f"{record['record_id']} candidate_ref/hash must resolve to a stable prior record",
                )
            dependencies = {
                item["record_id"]: item["record_hash"] for item in record["dependency_refs"]
            }
            if dependencies.get(payload["candidate_ref"]) != candidate["record_hash"]:
                _error(
                    "missing_dependency_edge",
                    f"{record['record_id']} must bind its stable candidate",
                )
            predecessor_ref = payload.get("predecessor_transition_ref")
            if payload["from_state"] == "registered":
                if predecessor_ref is not None:
                    _error(
                        "promotion_predecessor",
                        f"{record['record_id']} registered transition cannot name a predecessor record",
                    )
                if payload["predecessor_transition_hash"] != "0" * 64:
                    _error(
                        "promotion_predecessor",
                        f"{record['record_id']} registered transition must use the zero predecessor hash",
                    )
            else:
                if not isinstance(predecessor_ref, str) or not predecessor_ref:
                    _error(
                        "missing_dependency_edge",
                        f"{record['record_id']} must bind predecessor_transition_ref/hash",
                    )
                _bound_dependency(
                    record,
                    by_id,
                    predecessor_ref,
                    payload["predecessor_transition_hash"],
                    "predecessor_transition_ref",
                    expected_types={"promotion_transition"},
                )
                predecessor_record = by_id[predecessor_ref]
                predecessor_payload = predecessor_record["payload"]
                if (
                    predecessor_payload.get("candidate_ref") != payload["candidate_ref"]
                    or predecessor_payload.get("candidate_hash") != payload["candidate_hash"]
                    or predecessor_payload.get("to_state") != payload["from_state"]
                ):
                    _error(
                        "promotion_predecessor",
                        f"{record['record_id']} predecessor transition does not continue this candidate state",
                    )
            evidence_refs = payload.get("evidence_refs", [])
            if len(evidence_refs) != len(set(evidence_refs)):
                _error(
                    "promotion_evidence",
                    f"{record['record_id']} promotion evidence contains duplicate references",
                )
            evidence_records: list[Mapping[str, Any]] = []
            for evidence_ref in evidence_refs:
                evidence_record = by_id.get(evidence_ref)
                if evidence_record is None or evidence_record["sequence"] >= record["sequence"]:
                    _error(
                        "dangling_dependency",
                        f"{record['record_id']} promotion evidence is missing or future",
                    )
                if dependencies.get(evidence_ref) != evidence_record["record_hash"]:
                    _error(
                        "missing_dependency_edge",
                        f"{record['record_id']} must bind promotion evidence {evidence_ref}",
                    )
                evidence_records.append(evidence_record)
            if payload["to_state"] == "revoke":
                tombstone_evidence = [
                    item for item in evidence_records if item["record_type"] == "deletion_tombstone"
                ]
                if (
                    payload["from_state"]
                    in {
                        "development_eligible",
                        "screening_pass",
                        "bridge_eligible",
                        "confirmation_eligible",
                    }
                    and not tombstone_evidence
                ):
                    _error(
                        "revocation_evidence",
                        f"{record['record_id']} early-stage revoke requires an exact tombstone record",
                    )
                if tombstone_evidence:
                    # A revoke that repairs a tombstoned promotion must name
                    # the exact tombstone record and prove that one of its
                    # targets lies in this candidate's prior evidence graph.
                    lineage_ids: set[str] = set()
                    # Resolve the candidate's prior graph independently of
                    # the tombstone records themselves.  Seeding traversal
                    # with a tombstone would include that tombstone's own
                    # unrelated target and make the ancestry check tautological.
                    pending_lineage = [payload["candidate_ref"]]
                    predecessor_ref = payload.get("predecessor_transition_ref")
                    if predecessor_ref:
                        pending_lineage.append(predecessor_ref)
                    pending_lineage.extend(
                        evidence_ref
                        for evidence_ref in evidence_refs
                        if by_id.get(evidence_ref, {}).get("record_type") != "deletion_tombstone"
                    )
                    while pending_lineage:
                        lineage_ref = pending_lineage.pop()
                        if lineage_ref in lineage_ids:
                            continue
                        lineage_record = by_id.get(lineage_ref)
                        if lineage_record is None:
                            continue
                        lineage_ids.add(lineage_ref)
                        pending_lineage.extend(
                            dependency["record_id"]
                            for dependency in lineage_record["dependency_refs"]
                        )
                    if not any(
                        target in lineage_ids
                        for tombstone_record in tombstone_evidence
                        for target in tombstone_record["payload"].get("targets", [])
                    ):
                        _error(
                            "revocation_evidence",
                            f"{record['record_id']} revoke tombstone does not target this candidate ancestry",
                        )
            positive_transition = payload["to_state"] not in {
                "screening_reject",
                "reject",
                "revoke",
            }
            if positive_transition:
                # Promotion evidence is a graph, not just the transition's
                # direct refs.  A tainted bridge cell, score, subject
                # execution, or tombstoned parent must block the positive
                # transition even when the immediate bridge/score record was
                # left with its old summary flags.
                ancestry_ids: set[str] = set()
                pending = [payload["candidate_ref"], *evidence_refs]
                while pending:
                    ancestor_ref = pending.pop()
                    if ancestor_ref in ancestry_ids:
                        continue
                    ancestor = by_id.get(ancestor_ref)
                    if ancestor is None:
                        continue
                    ancestry_ids.add(ancestor_ref)
                    pending.extend(
                        dependency["record_id"] for dependency in ancestor["dependency_refs"]
                    )
                tombstoned_ids = {
                    target
                    for prior_record in records[:index]
                    if prior_record["record_type"] == "deletion_tombstone"
                    for target in prior_record["payload"].get("targets", [])
                }
                tainted_ancestors = {
                    ancestor_ref
                    for ancestor_ref in ancestry_ids
                    if ancestor_ref in tombstoned_ids
                    or by_id[ancestor_ref]["payload"].get("tainted")
                    or by_id[ancestor_ref]["payload"].get("revoked_ancestry")
                    or by_id[ancestor_ref]["payload"].get("score_status")
                    in {"unscorable", "revoked"}
                    or by_id[ancestor_ref]["payload"].get("status")
                    in {"unscorable", "revoked", "deleted", "unavailable"}
                }
                if tainted_ancestors:
                    _error(
                        "revoked_ancestry",
                        f"{record['record_id']} promotion depends on tainted/revoked ancestry: {', '.join(sorted(tainted_ancestors))}",
                    )
            prior_candidate_hash = promotion_candidate_hashes.get(payload["candidate_ref"])
            if (
                prior_candidate_hash is not None
                and prior_candidate_hash != payload["candidate_hash"]
            ):
                _error(
                    "promotion_candidate",
                    f"{record['record_id']} reuses a candidate_ref with a different hash",
                )
            promotion_candidate_hashes[payload["candidate_ref"]] = payload["candidate_hash"]
            candidate_key = (payload["candidate_ref"], payload["candidate_hash"])
            promotion_current = promotion_states_by_candidate.get(
                candidate_key,
                {"state": "registered", "transition_hash": "0" * 64},
            )
            candidate_history = promotion_transition_history.get(candidate_key, [])
            bridge_candidate_axes: set[tuple[str, str]] = set()
            for bridge_root in evidence_records:
                if bridge_root["record_type"] != "bridge_observation":
                    continue
                bridge_payload = bridge_root["payload"]
                if (
                    bridge_payload.get("new_builder_ref") == payload["candidate_ref"]
                    and bridge_payload.get("new_builder_hash") == payload["candidate_hash"]
                ):
                    bridge_candidate_axes.update(
                        {
                            (
                                bridge_payload.get("old_builder_ref"),
                                bridge_payload.get("old_builder_hash"),
                            ),
                            (
                                bridge_payload.get("new_builder_ref"),
                                bridge_payload.get("new_builder_hash"),
                            ),
                        }
                    )
            for evidence_record in evidence_records:
                evidence_payload = evidence_record["payload"]
                if "candidate_ref" in evidence_payload and (
                    evidence_payload.get("candidate_ref") != payload["candidate_ref"]
                    or evidence_payload.get("candidate_hash") != payload["candidate_hash"]
                ):
                    if (
                        evidence_payload.get("partition", evidence_payload.get("task_partition"))
                        == "bridge"
                        and evidence_record["record_type"]
                        in {
                            "subject_execution_evidence",
                            "evaluation_binding",
                            "score_run",
                            "anchor_observation",
                        }
                        and (
                            evidence_payload.get(
                                "candidate_ref", evidence_payload.get("builder_release_ref")
                            ),
                            evidence_payload.get(
                                "candidate_hash", evidence_payload.get("builder_release_hash")
                            ),
                        )
                        in bridge_candidate_axes
                    ):
                        continue
                    _error(
                        "promotion_evidence",
                        f"{record['record_id']} evidence {evidence_record['record_id']} names a different candidate",
                    )

            failed_bridge_transition = (
                payload["from_state"] == "bridge_eligible"
                and payload["to_state"] == "new_measurement_epoch"
            )
            stage_closure: str | None = None
            if payload["to_state"] in {"screening_pass", "screening_reject"}:
                stage_closure = "screening"
            elif payload["to_state"] == "confirmation_eligible" or (
                payload["from_state"] == "bridge_eligible"
                and payload["to_state"] == "new_measurement_epoch"
            ):
                stage_closure = "bridge"
            elif payload["to_state"] in {"promote", "narrow", "abstain", "reject"}:
                stage_closure = "confirmation"
            stage_snapshot = (
                _derive_candidate_stage_snapshot(
                    records[:index],
                    by_id,
                    candidate_ref=payload["candidate_ref"],
                    candidate_hash=payload["candidate_hash"],
                    stage=stage_closure,
                    frozen=frozen,
                )
                if stage_closure is not None
                else None
            )
            if stage_snapshot is not None:
                floor_state = {
                    "screening": "development_eligible",
                    "bridge": "bridge_eligible",
                    "confirmation": "confirmation_eligible",
                }[stage_closure]
                floor_transition = next(
                    (
                        item
                        for item in reversed(candidate_history)
                        if item["payload"].get("to_state") == floor_state
                    ),
                    None,
                )
                if floor_transition is not None and any(
                    item["sequence"] <= floor_transition["sequence"]
                    for values in stage_snapshot["slots"].values()
                    for item in values
                ):
                    _error(
                        "promotion_order",
                        f"{record['record_id']} {stage_closure} facts must follow {floor_state}",
                    )
                missing_slots = sorted(
                    slot
                    for slot in stage_snapshot["required_slots"]
                    if not stage_snapshot["slots"][slot]
                )
                positive_closure = (
                    payload["to_state"]
                    not in {
                        "screening_reject",
                        "reject",
                        "revoke",
                        "abstain",
                    }
                    and not failed_bridge_transition
                )
                # A selected root covers its exact dependency closure.  This
                # keeps the public transition compact while still making every
                # raw panel cell/anchor/exposure discovered for the candidate
                # part of the closure and blocker checks.
                evidence_id_set: set[str] = set()
                pending_evidence = list(evidence_refs)
                while pending_evidence:
                    evidence_id = pending_evidence.pop()
                    if evidence_id in evidence_id_set:
                        continue
                    evidence_id_set.add(evidence_id)
                    evidence_record = by_id.get(evidence_id)
                    if evidence_record is not None:
                        pending_evidence.extend(
                            dependency["record_id"]
                            for dependency in evidence_record["dependency_refs"]
                        )
                if missing_slots and (
                    positive_closure or stage_closure == "confirmation" or failed_bridge_transition
                ):
                    _error(
                        "promotion_stage_closure",
                        f"{record['record_id']} missing required {stage_closure} slot(s): {', '.join(missing_slots)}",
                    )
                abstain_missing_only = False
                if payload["to_state"] == "abstain" and stage_snapshot["blockers"]:
                    scoped_records = {
                        item["record_id"]: item
                        for values in stage_snapshot["slots"].values()
                        for item in values
                    }
                    abstain_missing_only = all(
                        scoped_records[blocker]["payload"].get("status")
                        in {"missing", "unavailable"}
                        for blocker in stage_snapshot["blockers"]
                        if blocker in scoped_records
                    )
                if positive_closure and stage_snapshot["blockers"]:
                    _error(
                        "promotion_stage_blocker",
                        f"{record['record_id']} has blocking {stage_closure} fact(s): {', '.join(sorted(stage_snapshot['blockers']))}",
                    )
                missing_scope = stage_snapshot["scope_ids"] - evidence_id_set
                if (positive_closure or failed_bridge_transition) and missing_scope:
                    _error(
                        "promotion_stage_coverage",
                        f"{record['record_id']} omits same-candidate {stage_closure} fact(s): {', '.join(sorted(missing_scope))}",
                    )
                missing_blockers = stage_snapshot["blockers"] - evidence_id_set
                if missing_blockers and not abstain_missing_only:
                    _error(
                        "promotion_stage_blocker",
                        f"{record['record_id']} omits blocking {stage_closure} fact(s): {', '.join(sorted(missing_blockers))}",
                    )

            bridge_records = [
                item
                for item in evidence_records
                if item["record_type"] in {"bridge_observation", "comparability_decision"}
            ]
            for bridge_record in bridge_records:
                bridge_observation = bridge_record
                if bridge_record["record_type"] == "comparability_decision":
                    bridge_observation = by_id.get(bridge_record["payload"].get("bridge_ref"))
                if (
                    bridge_observation is None
                    or bridge_observation["record_type"] != "bridge_observation"
                    or bridge_observation["payload"].get("new_builder_ref")
                    != payload["candidate_ref"]
                    or bridge_observation["payload"].get("new_builder_hash")
                    != payload["candidate_hash"]
                ):
                    _error(
                        "promotion_evidence",
                        f"{record['record_id']} bridge evidence must bind the promoted candidate generation",
                    )
            confirmation_records = [
                item
                for item in evidence_records
                if item["record_type"] == "confirmation_consumption"
                and item["payload"].get("partition") == "confirmation"
            ]
            anchor_records = [
                item
                for item in evidence_records
                if item["record_type"] == "anchor_observation"
                and item["payload"].get("partition") == "confirmation"
            ]
            independence_records = [
                item
                for item in evidence_records
                if item["record_type"] == "independence_assessment"
            ]
            requires_decision_evidence = payload["to_state"] in {
                "promote",
                "narrow",
                "abstain",
                "reject",
            }
            final_confirmation_decision = payload["to_state"] in {
                "promote",
                "narrow",
                "abstain",
                "reject",
            }
            if payload["to_state"] == "confirmation_eligible" and (
                confirmation_records or anchor_records
            ):
                _error(
                    "confirmation_early",
                    f"{record['record_id']} confirmation consumption/anchor is not allowed before the final decision",
                )
            if payload["to_state"] == "confirmation_eligible":
                bridge_eligible = next(
                    (
                        item
                        for item in reversed(candidate_history)
                        if item["payload"].get("to_state") == "bridge_eligible"
                    ),
                    None,
                )
                if bridge_eligible is None:
                    _error(
                        "promotion_order",
                        f"{record['record_id']} confirmation eligibility lacks a prior bridge_eligible transition",
                    )
                bridge_floor = bridge_eligible["sequence"]
                if any(item["sequence"] <= bridge_floor for item in bridge_records):
                    _error(
                        "promotion_order",
                        f"{record['record_id']} bridge evidence must be collected after bridge_eligible",
                    )
            if (requires_decision_evidence or failed_bridge_transition) and not bridge_records:
                _error("promotion_evidence", "promotion requires exact bridge evidence")
            if final_confirmation_decision and not confirmation_records:
                _error(
                    "promotion_evidence",
                    "promotion requires exact confirmation consumption evidence",
                )
            if final_confirmation_decision and not anchor_records:
                _error(
                    "promotion_evidence",
                    "promotion requires exact protected anchor observation evidence",
                )
            if requires_decision_evidence and not independence_records:
                _error("promotion_evidence", "promotion requires exact independence evidence")
            if requires_decision_evidence:
                required_independence_refs = {item["record_id"] for item in bridge_records}
                for independence_record in independence_records:
                    observed_refs = set(independence_record["payload"].get("evidence_refs", []))
                    missing_bridge = required_independence_refs - observed_refs
                    missing_anchor = [
                        item
                        for item in anchor_records
                        if item["record_id"] not in observed_refs
                        and item["payload"]["anchor_release_ref"] not in observed_refs
                    ]
                    if missing_bridge or missing_anchor:
                        _error(
                            "promotion_evidence",
                            f"{record['record_id']} independence evidence must bind this transition's bridge and anchor facts",
                        )

            # A final decision has one sealed confirmation pack.  The direct
            # consumption record and confirmation anchor are a single pair;
            # accepting two same-candidate packs would allow the anchor for one
            # pack to certify a different pack listed by the transition.
            selected_confirmation_records: list[Mapping[str, Any]] = []
            for anchor_record in anchor_records:
                anchor_payload = anchor_record["payload"]
                if anchor_payload.get("partition") != "confirmation":
                    continue
                consumption_ref = anchor_payload.get("confirmation_consumption_ref")
                consumption_hash = anchor_payload.get("confirmation_consumption_hash")
                direct_consumption = next(
                    (item for item in confirmation_records if item["record_id"] == consumption_ref),
                    None,
                )
                if direct_consumption is None:
                    _error(
                        "promotion_confirmation_binding",
                        f"{record['record_id']} anchor {anchor_record['record_id']} must bind a directly included confirmation consumption",
                    )
                if consumption_hash != direct_consumption["record_hash"]:
                    _error(
                        "promotion_confirmation_binding",
                        f"{record['record_id']} anchor {anchor_record['record_id']} has a mismatched confirmation consumption hash",
                    )
                selected_confirmation_records.append(direct_consumption)
            if final_confirmation_decision:
                if len(confirmation_records) != 1 or len(anchor_records) != 1:
                    _error(
                        "promotion_confirmation_binding",
                        f"{record['record_id']} final decision must select exactly one confirmation consumption and anchor",
                    )
                if len(selected_confirmation_records) != 1:
                    _error(
                        "promotion_confirmation_binding",
                        f"{record['record_id']} final decision anchor must select its exact confirmation consumption",
                    )
                confirmation_eligible = next(
                    (
                        item
                        for item in reversed(candidate_history)
                        if item["payload"].get("to_state") == "confirmation_eligible"
                    ),
                    None,
                )
                if confirmation_eligible is None:
                    _error(
                        "promotion_order",
                        f"{record['record_id']} final decision lacks a prior confirmation_eligible transition",
                    )
                confirmation_floor = confirmation_eligible["sequence"]
                confirmation_refs = {
                    item["record_id"] for item in selected_confirmation_records
                } | {item["record_id"] for item in anchor_records}
                confirmation_refs.update(
                    item["payload"]["confirmation_ref"] for item in selected_confirmation_records
                )
                confirmation_refs.update(
                    item["record_id"]
                    for item in evidence_records
                    if item["record_type"]
                    in {
                        "evaluation_binding",
                        "score_run",
                        "subject_execution_evidence",
                    }
                    and item["payload"].get("partition") == "confirmation"
                )
                for confirmation_ref in confirmation_refs:
                    confirmation_record = by_id.get(confirmation_ref)
                    if confirmation_record is None:
                        continue
                    if confirmation_record["sequence"] <= confirmation_floor:
                        _error(
                            "promotion_order",
                            f"{record['record_id']} confirmation evidence must follow confirmation_eligible",
                        )

            matching_effects = [
                item
                for item in records[:index]
                if item["record_type"] == "effect_attempt"
                and item["payload"].get("candidate_ref") == payload["candidate_ref"]
                and item["payload"].get("candidate_hash") == payload["candidate_hash"]
            ]
            containment_transition = payload["to_state"] in {
                "screening_reject",
                "reject",
                "revoke",
            }
            if matching_effects:
                matching_effect_ids = {item["record_id"] for item in matching_effects}
                if not matching_effect_ids.issubset(set(evidence_refs)):
                    _error(
                        "promotion_effect_evidence",
                        f"{record['record_id']} must include every matching effect attempt in evidence_refs",
                    )

            confirmation_reused_across_promotions = False
            if payload["to_state"] in {"promote", "narrow", "abstain", "reject"}:
                # Account for the exact anchor-bound pack, not an arbitrary
                # same-candidate consumption also listed by the transition.
                records_for_consumption = (
                    selected_confirmation_records
                    if final_confirmation_decision
                    else confirmation_records
                )
                for confirmation_record in records_for_consumption:
                    confirmation_payload = confirmation_record["payload"]
                    if not confirmation_payload.get("consumed"):
                        continue
                    confirmation_ref = confirmation_payload["confirmation_ref"]
                    prior_consumer = promotion_confirmation_consumers.get(confirmation_ref)
                    if prior_consumer is not None and prior_consumer != record["record_id"]:
                        confirmation_reused_across_promotions = True
                    else:
                        promotion_confirmation_consumers[confirmation_ref] = record["record_id"]

            derived_evidence: dict[str, Any] = {
                "critical_failure": False,
                # Effect facts are authoritative; do not let a transition's
                # duplicate boolean manufacture (or omit) the ledger event.
                "effect_attempt": False,
                "revoked_ancestry": False,
            }
            if confirmation_reused_across_promotions:
                derived_evidence["confirmation_reused"] = True
            if matching_effects and not containment_transition:
                derived_evidence["effect_attempt"] = True
            elif matching_effects and containment_transition:
                # Containment is allowed to record a blocked/quarantined
                # effect attempt, but an applied effect remains a critical
                # failure.  Stage 0's frozen policy rejects accepted events
                # before this reducer is reached.
                derived_evidence["effect_attempt"] = True
                if any(
                    item["payload"].get("disposition") == "accepted" for item in matching_effects
                ):
                    derived_evidence["accepted_effect_attempt"] = True
            if candidate["payload"].get("tainted") or candidate["payload"].get("effect_attempt"):
                derived_evidence["revoked_ancestry"] = True
            if candidate["payload"].get("score_status") in {"unscorable", "revoked"}:
                derived_evidence["critical_failure"] = True
            derived_independence: Mapping[str, Any] | None = None
            bridge_status: str | bool | None = None
            confirmation_status: str | bool | None = None
            confirmation_seen = False
            confirmation_valid = True
            confirmation_unusable_status: str | None = None
            anchor_seen = False
            anchor_valid = True
            anchor_pass: bool | None = None
            for evidence_record in evidence_records:
                evidence_payload = evidence_record["payload"]
                if evidence_payload.get("tainted") or evidence_payload.get("effect_attempt"):
                    derived_evidence["revoked_ancestry"] = True
                if evidence_payload.get("critical_failure") or evidence_payload.get(
                    "score_status"
                ) in {"unscorable", "revoked"}:
                    derived_evidence["critical_failure"] = True
                if evidence_record["record_type"] == "independence_assessment":
                    if evidence_payload["claim_ref"] != payload["candidate_ref"]:
                        _error(
                            "promotion_evidence",
                            f"{record['record_id']} independence evidence must name the stable candidate",
                        )
                    if derived_independence is not None and dict(derived_independence) != dict(
                        evidence_payload["dimensions"]
                    ):
                        _error(
                            "promotion_evidence",
                            f"{record['record_id']} independence evidence disagrees across records",
                        )
                    derived_independence = evidence_payload["dimensions"]
                elif evidence_record["record_type"] == "comparability_decision":
                    bridge_status = (
                        evidence_payload["outcome"]
                        if evidence_payload["eligible"]
                        else "new_epoch_not_comparable"
                    )
                elif evidence_record["record_type"] == "bridge_observation":
                    panel_gate = None
                    if frozen is not None:
                        panel_gate = _derive_bridge_panel_gate(
                            evidence_payload,
                            by_id,
                            threshold=float(evidence_payload["decision_threshold"]),
                            global_tolerance=float(frozen["bridge"]["global_shift_tolerance"]),
                            interaction_tolerance=float(frozen["bridge"]["interaction_tolerance"]),
                            agreement_min=float(frozen["bridge"]["decision_agreement_min"]),
                            path=f"{record['record_id']}.bridge",
                        )["strata_gate"]
                    bridge_result = evaluate_bridge(
                        evidence_payload,
                        tolerances=(
                            {
                                "global_shift": frozen["bridge"]["global_shift_tolerance"],
                                "interaction": frozen["bridge"]["interaction_tolerance"],
                                "agreement": frozen["bridge"]["decision_agreement_min"],
                            }
                            if frozen is not None
                            else None
                        ),
                        expected_strata=frozen["bridge"]["strata"] if frozen is not None else None,
                        per_stratum_gate=panel_gate,
                    )
                    bridge_status = bridge_result["outcome"]
                elif evidence_record["record_type"] == "confirmation_consumption":
                    confirmation_seen = True
                    confirmation_target = by_id.get(evidence_payload.get("confirmation_ref"))
                    target_status = (
                        confirmation_target["payload"].get("status")
                        if confirmation_target is not None
                        else None
                    )
                    if target_status in {"missing", "unavailable"}:
                        confirmation_unusable_status = target_status
                    if not evidence_payload.get("consumed"):
                        confirmation_valid = False
                        confirmation_status = "tainted"
                    elif (
                        evidence_payload["candidate_ref"] != payload["candidate_ref"]
                        or evidence_payload["candidate_hash"] != payload["candidate_hash"]
                    ):
                        _error(
                            "promotion_evidence",
                            f"{record['record_id']} confirmation evidence names a different candidate",
                        )
                    else:
                        confirmation_status = "single_use"
                elif evidence_record["record_type"] == "anchor_observation":
                    anchor_seen = True
                    anchor_payload = evidence_payload
                    if (
                        anchor_payload["candidate_ref"] != payload["candidate_ref"]
                        or anchor_payload["candidate_hash"] != payload["candidate_hash"]
                    ):
                        _error(
                            "promotion_evidence",
                            f"{record['record_id']} anchor evidence names a different candidate",
                        )
                    anchor_status = anchor_payload.get("status")
                    if anchor_status in {"missing", "unavailable"}:
                        confirmation_unusable_status = anchor_status
                        anchor_valid = False
                        confirmation_status = "tainted"
                    elif anchor_payload.get("critical_failure") or anchor_status in {
                        "unscorable",
                        "revoked",
                        "fail",
                        "failed",
                    }:
                        anchor_valid = False
                        derived_evidence["critical_failure"] = True
                        confirmation_status = "tainted"
                    elif anchor_status in {"retained", "observed", "pass", "passed"}:
                        confirmation_status = "single_use"
                    else:
                        anchor_valid = False
                        confirmation_status = "tainted"
                    if anchor_payload.get("partition") == "confirmation" and frozen is not None:
                        decision_rule = frozen["decision_rule"]
                        anchor_pass = bool(
                            anchor_payload.get("status") == decision_rule["required_status"]
                            and anchor_payload.get("outcome") == decision_rule["outcome"]
                            and (
                                decision_rule["critical_failure"] != "block"
                                or not anchor_payload.get("critical_failure")
                            )
                            and anchor_payload.get("value") is not None
                            and float(anchor_payload["value"]) >= float(decision_rule["threshold"])
                        )
                elif evidence_record["record_type"] == "effect_attempt":
                    if evidence_payload.get("disposition") in {
                        "blocked",
                        "accepted",
                        "quarantined",
                    }:
                        derived_evidence["effect_attempt"] = True
                    if evidence_payload.get("disposition") == "accepted":
                        derived_evidence["critical_failure"] = True
                        derived_evidence["accepted_effect_attempt"] = True
            if failed_bridge_transition and bridge_status not in {
                "new_epoch_not_comparable",
                "bridge_insufficient",
                "linked_with_uncertainty",
            }:
                _error(
                    "bridge_outcome",
                    f"{record['record_id']} new_measurement_epoch requires a failed or uncertain bridge",
                )
            if confirmation_seen and not confirmation_valid:
                derived_evidence["tainted_confirmation"] = True
                confirmation_status = "tainted"
            if anchor_seen and not anchor_valid:
                derived_evidence["tainted_confirmation"] = True
                confirmation_status = "tainted"
            if requires_decision_evidence and (
                not confirmation_seen
                or not confirmation_valid
                or not anchor_seen
                or not anchor_valid
            ):
                derived_evidence["tainted_confirmation"] = True
                confirmation_status = "tainted"
            exposure_before_confirmation = False
            for confirmation_record in confirmation_records:
                target_record = by_id.get(confirmation_record["payload"].get("confirmation_ref"))
                if (
                    target_record is not None
                    and target_record["payload"].get("task_hash")
                    in confirmation_exposure_task_roots
                ):
                    exposure_before_confirmation = True
                    break
            if exposure_before_confirmation:
                confirmation_status = "tainted"
            if len(confirmation_records) > 1 or len(
                {item["payload"]["confirmation_ref"] for item in confirmation_records}
            ) != len(confirmation_records):
                derived_evidence["confirmation_reused"] = True
            if derived_independence is not None:
                derived_evidence["independence"] = derived_independence
            if bridge_status is not None:
                derived_evidence["bridge_status"] = bridge_status
            if confirmation_status is not None:
                derived_evidence["confirmation_status"] = confirmation_status
            if confirmation_unusable_status is not None:
                derived_evidence["confirmation_unusable_status"] = confirmation_unusable_status
            if anchor_pass is not None:
                derived_evidence["anchor_pass"] = anchor_pass
            for claim_key in ("critical_failure", "effect_attempt", "revoked_ancestry"):
                if bool(payload.get(claim_key)) != bool(derived_evidence.get(claim_key)):
                    _error(
                        "promotion_claim",
                        f"{record['record_id']} {claim_key} does not match derived ledger evidence",
                    )
            if derived_independence is not None and payload.get("independence") != dict(
                derived_independence
            ):
                _error(
                    "promotion_claim",
                    f"{record['record_id']} independence claim does not match its assessment",
                )
            if bridge_status is not None and payload.get("bridge_status") != bridge_status:
                _error(
                    "promotion_claim",
                    f"{record['record_id']} bridge_status does not match derived bridge evidence",
                )
            if (
                confirmation_status is not None
                and payload.get("confirmation_status") != confirmation_status
            ):
                _error(
                    "promotion_claim",
                    f"{record['record_id']} confirmation_status does not match derived confirmation evidence",
                )
            reduced = reduce_promotion(
                promotion_current,
                payload,
                evidence=derived_evidence,
                protocol=frozen,
            )
            promotion_states_by_candidate[candidate_key] = {
                "state": reduced["state"],
                # Ledger transitions bind the addressed record hash.  The
                # standalone reducer returns a payload hash for pure callers;
                # the bundle reducer must advance using the exact addressed
                # record hash that the next record carries.
                "transition_hash": record["record_hash"],
            }
            promotion_transition_history.setdefault(candidate_key, []).append(record)
        elif record["record_type"] == "deletion_tombstone":
            if (
                frozen is not None
                and payload["authority"] != frozen["principals"]["evidence"]["principal_id"]
            ):
                _error(
                    "tombstone_authority",
                    f"{record['record_id']} tombstone authority is not the frozen evidence principal",
                )
            if (
                frozen is not None
                and payload["descendant_policy"] != "revoke-or-unscorable-all-dependants"
            ):
                _error(
                    "tombstone_policy",
                    f"{record['record_id']} tombstone descendant_policy is not the frozen Stage 0 policy",
                )
            for target_ref in payload["targets"]:
                target_record = by_id.get(target_ref)
                if target_record is None or target_record["sequence"] >= record["sequence"]:
                    _error(
                        "tombstone_target",
                        f"{record['record_id']} tombstone target {target_ref} must precede the tombstone",
                    )
                deps = {
                    item["record_id"]: item["record_hash"] for item in record["dependency_refs"]
                }
                if deps.get(target_ref) != target_record["record_hash"]:
                    _error(
                        "missing_dependency_edge",
                        f"{record['record_id']} must bind tombstone target {target_ref}",
                    )

    trajectory_records = [item for item in records if item["record_type"] == "trajectory_summary"]
    contrast_records = [item for item in records if item["record_type"] == "contrast_summary"]
    if contrast_records:
        if len(contrast_records) != 1:
            _error("summary_duplicate", "ledger may contain exactly one contrast_summary seal")
        contrast_record = contrast_records[0]
        if trajectory_records and any(
            contrast_record["sequence"] <= trajectory["sequence"]
            for trajectory in trajectory_records
        ):
            _error("summary_order", "contrast_summary must follow every trajectory_summary")
        expected_pairs = {
            (arm, scenario_ref)
            for arm in (frozen["arms"] if frozen is not None else ())
            for scenario_ref in (_frozen_scenario_refs(frozen) if frozen is not None else ())
        }
        actual_pairs = {
            (item["payload"]["arm"], item["payload"]["scenario_ref"]) for item in trajectory_records
        }
        if frozen is not None and actual_pairs != expected_pairs:
            _error(
                "summary_coverage",
                "trajectory summaries must cover each frozen arm and scenario exactly once",
            )
        if len(actual_pairs) != len(trajectory_records):
            _error("summary_duplicate", "trajectory summaries contain duplicate arm/scenario rows")
        dependencies = {
            item["record_id"]: item["record_hash"] for item in contrast_record["dependency_refs"]
        }
        trajectory_ids = {item["record_id"] for item in trajectory_records}
        if set(dependencies) != trajectory_ids:
            _error(
                "summary_dependencies",
                "contrast_summary dependencies must be exactly all trajectory summaries",
            )
        for trajectory in trajectory_records:
            if dependencies.get(trajectory["record_id"]) != trajectory["record_hash"]:
                _error(
                    "summary_dependencies",
                    f"contrast_summary dependency hash mismatch for {trajectory['record_id']}",
                )
        if frozen is not None:
            expected_contrasts = derive_contrast_diagnostics(
                frozen, [item["payload"] for item in trajectory_records]
            )
            if contrast_record["payload"]["contrasts"] != expected_contrasts:
                _error(
                    "summary_contrasts",
                    "contrast_summary contrasts do not match the frozen rows",
                )
    elif trajectory_records:
        _error(
            "summary_missing",
            "trajectory summaries require one dependency-bound contrast_summary seal",
        )

    for effect in records:
        if effect["record_type"] != "effect_attempt":
            continue
        effect_payload = effect["payload"]
        contained = False
        for later in records:
            if (
                later["record_type"] != "promotion_transition"
                or later["sequence"] <= effect["sequence"]
                or later["payload"].get("candidate_ref") != effect_payload.get("candidate_ref")
                or later["payload"].get("candidate_hash") != effect_payload.get("candidate_hash")
                or later["payload"].get("to_state") not in {"screening_reject", "reject", "revoke"}
                or effect["record_id"] not in later["payload"].get("evidence_refs", [])
            ):
                continue
            dependency_hashes = {
                item["record_id"]: item["record_hash"] for item in later["dependency_refs"]
            }
            if dependency_hashes.get(effect["record_id"]) == effect["record_hash"]:
                contained = True
                break
        if not contained:
            _error(
                "effect_orphan",
                f"effect attempt {effect['record_id']} lacks a later candidate containment transition",
            )

    if prior is not None:
        prior_records = prior["records"]
        if len(records) < len(prior_records):
            _error("predecessor_prefix", "successor bundle is shorter than its predecessor")
        for index, prior_record in enumerate(prior_records):
            if canonical_json_bytes(
                records[index], domain="ael-cep-record"
            ) != canonical_json_bytes(prior_record, domain="ael-cep-record"):
                _error(
                    "predecessor_prefix", f"successor changed predecessor record at index {index}"
                )
        if (
            len(records) > len(prior_records)
            and prior_records
            and records[len(prior_records)]["previous_record_hash"]
            != prior_records[-1]["record_hash"]
        ):
            _error("chain_fork", "successor append does not bind predecessor tail")

    normalized = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "bundle_id": bundle_id,
        "protocol_ref": protocol_ref,
        "protocol_hash": protocol_digest,
        "predecessor": normalized_predecessor,
        "records": records,
    }
    given_bundle_hash = _require_hash(bundle.get("bundle_hash"), "bundle.bundle_hash")
    expected_bundle_hash = bundle_hash(normalized)
    if given_bundle_hash != expected_bundle_hash:
        _error("hash_mismatch", "bundle.bundle_hash does not match canonical bundle bytes")
    normalized["bundle_hash"] = given_bundle_hash

    # Tombstones are historical facts, but a later record may not create a new
    # descendant through a tombstoned dependency.
    tombstoned: set[str] = set()
    tombstone_records: set[str] = set()
    for record in records:
        if record["record_type"] == "deletion_tombstone":
            tombstone_records.add(record["record_id"])
            tombstoned.update(record["payload"]["targets"])
    # Preserve historical descendants that precede a tombstone, but reject a
    # new direct or transitive extension after the tombstone sequence.  The
    # origin map is a fixed point because a post-tombstone record may depend on
    # an already-derived descendant rather than the target itself.
    tombstone_origin: dict[str, int] = {}
    for record in records:
        if record["record_type"] == "deletion_tombstone":
            for target in record["payload"]["targets"]:
                tombstone_origin[target] = min(
                    record["sequence"], tombstone_origin.get(target, record["sequence"])
                )
            tombstone_origin[record["record_id"]] = record["sequence"]
    changed = True
    while changed:
        changed = False
        for record in records:
            origins = [
                tombstone_origin[dep["record_id"]]
                for dep in record["dependency_refs"]
                if dep["record_id"] in tombstone_origin
            ]
            if not origins:
                continue
            origin = min(origins)
            # A historical record before the tombstone is not itself a new
            # descendant; keep it valid while retaining the target's origin.
            if record["sequence"] <= origin:
                continue
            if tombstone_origin.get(record["record_id"]) != origin:
                tombstone_origin[record["record_id"]] = origin
                changed = True

    def _authorized_tombstone_revoke(record: Mapping[str, Any], origin: int | None) -> bool:
        if (
            origin is None
            or record["record_type"] != "promotion_transition"
            or record["payload"].get("to_state") != "revoke"
        ):
            return False
        tombstone_refs = [
            ref
            for ref in record["payload"].get("evidence_refs", [])
            if by_id.get(ref, {}).get("record_type") == "deletion_tombstone"
        ]
        if not tombstone_refs:
            return False
        dependency_hashes = {
            item["record_id"]: item["record_hash"] for item in record["dependency_refs"]
        }
        if any(dependency_hashes.get(ref) != by_id[ref]["record_hash"] for ref in tombstone_refs):
            return False
        return any(tombstone_origin.get(ref) == origin for ref in tombstone_refs)

    for record in records:
        origin = tombstone_origin.get(record["record_id"])
        if origin is not None and record["sequence"] > origin:
            if _authorized_tombstone_revoke(record, origin):
                continue
            _error(
                "tombstone_descendant",
                f"record {record['record_id']} extends a tombstoned ancestor after sequence {origin}",
            )
    return normalized


def append_bundle(
    bundle: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
    *,
    bundle_id: str | None = None,
    protocol: Mapping[str, Any] | None = None,
    predecessor: Mapping[str, Any] | None = None,
    predecessor_chain: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create a successor without mutating the input bundle."""

    if predecessor is not None and predecessor_chain is not None:
        _error("predecessor_arguments", "supply predecessor or predecessor_chain, not both")
    prior = validate_bundle(
        bundle,
        protocol=protocol,
        predecessor=predecessor,
        predecessor_chain=predecessor_chain,
    )
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        _error("invalid_type", "records to append must be an array")
    existing = prior["records"]
    sequence = existing[-1]["sequence"] + 1 if existing else 0
    previous_hash = existing[-1]["record_hash"] if existing else None
    additions = []
    for offset, candidate in enumerate(records):
        item = _normalize_record(candidate, offset)
        if item["sequence"] != sequence + offset:
            _error("sequence", "appended record sequence does not continue the ledger")
        if item["previous_record_hash"] != (
            previous_hash if offset == 0 else additions[-1]["record_hash"]
        ):
            _error("chain_fork", "appended record does not bind the prior record")
        additions.append(item)
    result = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "bundle_id": bundle_id or f"{prior['bundle_id']}.successor.{sequence}",
        "protocol_ref": prior["protocol_ref"],
        "protocol_hash": prior["protocol_hash"],
        "predecessor": {"bundle_ref": prior["bundle_id"], "bundle_hash": prior["bundle_hash"]},
        "records": existing + additions,
    }
    result["bundle_hash"] = bundle_hash(result)
    if predecessor_chain is not None:
        successor_chain = tuple(predecessor_chain) + (prior,)
        return validate_bundle(result, protocol=protocol, predecessor_chain=successor_chain)
    if predecessor is not None:
        return validate_bundle(
            result,
            protocol=protocol,
            predecessor_chain=(predecessor, prior),
        )
    return validate_bundle(result, protocol=protocol, predecessor=prior)


def _record_refs(bundle: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {record["record_id"]: record for record in bundle["records"]}


def project_bundle(
    bundle: Mapping[str, Any],
    *,
    protocol: Mapping[str, Any] | None = None,
    predecessor: Mapping[str, Any] | None = None,
    predecessor_chain: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Derive current taint, score, comparability, and promotion views."""

    normalized = validate_bundle(
        bundle,
        protocol=protocol,
        predecessor=predecessor,
        predecessor_chain=predecessor_chain,
    )
    records = normalized["records"]
    revoked: set[str] = set()
    unscorable: set[str] = set()
    tombstones: list[str] = []
    by_id = {record["record_id"]: record for record in records}
    live_tombstone_ids: set[str] = set()
    for record in records:
        if record["record_type"] != "deletion_tombstone":
            continue
        payload = record["payload"]
        if protocol is None or (
            payload.get("authority") == protocol["principals"]["evidence"]["principal_id"]
            and payload.get("descendant_policy") == "revoke-or-unscorable-all-dependants"
        ):
            # A tombstone is an authority-bound control fact.  Its target and
            # descendants become revoked, but the control itself remains live
            # so projection can explain the revocation and its later closure.
            live_tombstone_ids.add(record["record_id"])
    authorized_tombstone_revoke_ids: set[str] = set()
    for record in records:
        if (
            record["record_type"] != "promotion_transition"
            or record["payload"].get("to_state") != "revoke"
        ):
            continue
        dependency_hashes = {
            item["record_id"]: item["record_hash"] for item in record["dependency_refs"]
        }
        tombstone_refs = [
            ref
            for ref in record["payload"].get("evidence_refs", [])
            if by_id.get(ref, {}).get("record_type") == "deletion_tombstone"
        ]
        if tombstone_refs and all(
            dependency_hashes.get(ref) == by_id[ref]["record_hash"] for ref in tombstone_refs
        ):
            authorized_tombstone_revoke_ids.add(record["record_id"])
    for record in records:
        if record["record_type"] == "deletion_tombstone":
            tombstones.append(record["record_id"])
            revoked.update(record["payload"]["targets"])
    changed = True
    while changed:
        changed = False
        for record in records:
            # The exact authority-bound revoke control is a valid containment
            # action even though it necessarily depends on tombstoned history.
            # Keep the control live so projection can expose terminal revoke;
            # its historical evidence remains revoked/quarantined.
            if (
                record["record_id"] in authorized_tombstone_revoke_ids
                or record["record_id"] in live_tombstone_ids
            ):
                continue
            if record["record_id"] in revoked:
                continue
            payload = record["payload"]
            if payload.get("tainted") or (
                record["record_type"] == "effect_attempt"
                and payload.get("disposition") == "accepted"
            ):
                revoked.add(record["record_id"])
                changed = True
                continue
            if any(dep["record_id"] in revoked for dep in record["dependency_refs"]):
                revoked.add(record["record_id"])
                changed = True
    for record in records:
        payload = record["payload"]
        if record["record_type"] == "score_run" and (
            payload.get("score_status") in {"unscorable", "revoked"}
            or record["record_id"] in revoked
        ):
            unscorable.add(record["record_id"])
    # A confirmation partition is single-use.  Duplicate consumption events
    # make every associated score unscorable, while preserving old bytes.
    seen_confirmations: dict[str, str] = {}
    for record in records:
        if record["record_type"] != "confirmation_consumption" or not record["payload"].get(
            "consumed"
        ):
            continue
        key = record["payload"]["confirmation_ref"]
        if key in seen_confirmations:
            for score in records:
                if score["record_type"] == "score_run" and score["payload"].get(
                    "confirmation_consumption_ref"
                ) in {seen_confirmations[key], record["record_id"]}:
                    unscorable.add(score["record_id"])
        else:
            seen_confirmations[key] = record["record_id"]

    scores = [record for record in records if record["record_type"] == "score_run"]
    all_scores = [
        {
            "record_id": item["record_id"],
            "score": item["payload"].get("score"),
            "status": "unscorable"
            if item["record_id"] in unscorable
            else item["payload"].get("score_status", "observed"),
        }
        for item in scores
    ]
    latest_scores: dict[str, dict[str, Any]] = {}
    for record in scores:
        if (
            record["record_id"] in unscorable
            or record["record_id"] in revoked
            or record["payload"].get("score_status") != "observed"
        ):
            continue
        payload = record["payload"]
        key = payload.get("score_key") or payload.get("evidence_ref") or payload.get("binding_ref")
        if key is None:
            key = record["record_id"]
        latest_scores[str(key)] = {
            "record_id": record["record_id"],
            "score": payload.get("score"),
            "status": payload.get("score_status", "observed"),
        }

    comparability: dict[str, Any] = {}
    for record in records:
        if record["record_type"] == "comparability_decision" and record["record_id"] not in revoked:
            comparability[record["payload"]["bridge_ref"]] = {
                "record_id": record["record_id"],
                "outcome": record["payload"]["outcome"],
                "eligible": record["payload"]["eligible"],
            }
    promotion_state_map: dict[str, dict[str, Any]] = {}
    promotion_hashes: dict[str, str] = {}
    for record in records:
        if record["record_type"] == "promotion_transition":
            payload = record["payload"]
            candidate_ref = payload["candidate_ref"]
            candidate_hash = payload["candidate_hash"]
            prior_hash = promotion_hashes.get(candidate_ref, "0" * 64)
            previous = promotion_state_map.get(
                candidate_ref,
                {"state": "registered", "transition_hash": None, "candidate_hash": candidate_hash},
            )
            # Validation has already enforced this per-candidate automaton;
            # projection remains defensive for bundles built by callers that
            # bypassed the reducer.
            if (
                previous.get("candidate_hash") == candidate_hash
                and payload["from_state"] == previous["state"]
                and payload["predecessor_transition_hash"] == prior_hash
            ):
                promotion_state_map[candidate_ref] = {
                    "candidate_hash": candidate_hash,
                    "state": payload["to_state"],
                    "transition_hash": record["record_hash"],
                }
                promotion_hashes[candidate_ref] = record["record_hash"]
            elif candidate_ref not in promotion_state_map:
                promotion_state_map[candidate_ref] = {
                    "candidate_hash": candidate_hash,
                    "state": "registered",
                    "transition_hash": None,
                }
    for candidate_ref, state in promotion_state_map.items():
        candidate_hash = state["candidate_hash"]
        effect = any(
            item["record_type"] == "effect_attempt"
            and item["payload"].get("candidate_ref") == candidate_ref
            and item["payload"].get("candidate_hash") == candidate_hash
            for item in records
        )
        candidate_transition_ids = {
            item["record_id"]
            for item in records
            if item["record_type"] == "promotion_transition"
            and item["payload"].get("candidate_ref") == candidate_ref
        }
        revoked_candidate = bool(candidate_transition_ids & revoked)
        state["promotion_quarantined"] = bool(effect or revoked_candidate)
        state["revoke_required"] = bool(
            (revoked_candidate and state["state"] != "revoke")
            or (effect and state["state"] not in {"screening_reject", "reject", "revoke"})
        )
    promotion_states = {key: promotion_state_map[key] for key in sorted(promotion_state_map)}
    legacy_promotion = (
        next(iter(promotion_states.values()), None) if len(promotion_states) == 1 else None
    )
    trajectory_payloads = [
        item["payload"] for item in records if item["record_type"] == "trajectory_summary"
    ]
    contrast_seals = [item for item in records if item["record_type"] == "contrast_summary"]
    seal_valid = bool(contrast_seals) and contrast_seals[0]["record_id"] not in revoked
    if seal_valid and trajectory_payloads and protocol is not None:
        operating_metrics = derive_operating_metrics(trajectory_payloads)
        primary_endpoints = derive_arm_primary_endpoints(protocol, trajectory_payloads)
        contrast_diagnostics = derive_contrast_diagnostics(protocol, trajectory_payloads)
    else:
        operating_metrics = {}
        primary_endpoints = {}
        contrast_diagnostics = []
    return {
        "bundle_id": normalized["bundle_id"],
        "bundle_hash": normalized["bundle_hash"],
        "tainted_record_ids": sorted(revoked),
        "revoked_record_ids": sorted(revoked),
        "unscorable_record_ids": sorted(unscorable),
        "tombstone_record_ids": tombstones,
        "all_score_runs": all_scores,
        "latest_scores": latest_scores,
        "comparability": comparability,
        "promotion_states": promotion_states,
        "promotion_state": legacy_promotion,
        "promotion": legacy_promotion,
        "promotion_quarantined": bool(
            legacy_promotion and legacy_promotion.get("promotion_quarantined")
        ),
        "revoke_required": bool(legacy_promotion and legacy_promotion.get("revoke_required")),
        "operating_metrics": operating_metrics,
        "primary_endpoints": primary_endpoints,
        "contrast_diagnostics": contrast_diagnostics,
        "record_count": len(records),
    }


def derive_projection(
    bundle: Mapping[str, Any],
    *,
    protocol: Mapping[str, Any] | None = None,
    predecessor: Mapping[str, Any] | None = None,
    predecessor_chain: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    return project_bundle(
        bundle,
        protocol=protocol,
        predecessor=predecessor,
        predecessor_chain=predecessor_chain,
    )


def classify_replay(
    old_evaluator: Mapping[str, Any] | None = None,
    new_evaluator: Mapping[str, Any] | None = None,
    *,
    retained_surfaces: Iterable[str] = (),
    required_surfaces: Iterable[str] = (),
    revoked: bool = False,
    unavailable: bool = False,
    deterministic_code: bool = False,
    changes: Iterable[str] | None = None,
) -> str:
    """Classify whether a score can be rescored, replayed, or must be rerun."""

    retained = set(retained_surfaces)
    required = set(required_surfaces)
    if revoked or unavailable or not retained or not required or not required.issubset(retained):
        return "historical_only"
    material = set(changes or ())
    if (
        old_evaluator is not None
        and new_evaluator is not None
        and _is_mapping(old_evaluator)
        and _is_mapping(new_evaluator)
    ):
        evaluator_axes = {
            "implementation",
            "prompt_or_rubric",
            "model",
            "parser_or_aggregation",
            "tools_or_environment",
            "calibration_lineage",
            "known_error_envelope",
            "revision",
            "artifact_hash",
            "release_id",
            "release_kind",
            "custody",
            "allowed_evidence_surface",
            "parent_release_ref",
            "parent_release_hash",
        }
        # A release payload is already namespaced as an evaluator artifact.
        # Normalize changed evaluator fields to one evaluator-only axis so a
        # rubric/model/parser/tool change remains rescorable.  Subject model,
        # environment, builder, task, or external-world changes are separate
        # caller axes and remain rerun-required.
        material.update(
            {
                "evaluator" if key in evaluator_axes else key
                for key in set(old_evaluator) | set(new_evaluator)
                if old_evaluator.get(key) != new_evaluator.get(key)
            }
        )
    rerun_dimensions = {
        "builder",
        "model",
        "subject_model",
        "prompt",
        "tools",
        "retrieval",
        "environment",
        "external_world",
        "subject",
        "task",
        "runner",
    }
    if material & rerun_dimensions:
        return "rerun_required"
    if deterministic_code:
        return "deterministic_replayable"
    evaluator_only = {
        "evaluator",
        "evaluator_model",
        "evaluator_prompt",
        "evaluator_parser",
        "evaluator_tools",
        "rubric",
        "parser",
        "aggregation",
        "implementation",
        "calibration",
    }
    if not material or material.issubset(evaluator_only):
        return "rescorable"
    return "rerun_required"


def rescore_classification(*args: Any, **kwargs: Any) -> str:
    return classify_replay(*args, **kwargs)


def evaluate_bridge(
    observation: Mapping[str, Any],
    *,
    tolerances: Mapping[str, Any] | None = None,
    expected_strata: Iterable[str] | None = None,
    per_stratum_gate: bool | None = None,
) -> dict[str, Any]:
    """Evaluate a frozen evaluator bridge without silently equating scales."""

    if not _is_mapping(observation):
        _error("invalid_type", "bridge observation must be an object")
    required = {
        "global_shift_interval",
        "interaction_interval",
        "decision_agreement",
        "anchor_agreement",
        "construct_evidence",
        "reliability_evidence",
        "strata",
    }
    missing = sorted(required - set(observation))
    if missing:
        _error("bridge_incomplete", f"bridge observation missing: {', '.join(missing)}")
    if tolerances is None:
        return {
            "outcome": "new_epoch_not_comparable",
            "reason": "frozen bridge tolerances were not supplied",
        }
    tol = {"global_shift": 0.0, "interaction": 0.0, "agreement": 1.0}
    for key in tol:
        if key in tolerances:
            tol[key] = _require_number(tolerances[key], f"tolerances.{key}", nonnegative=True)

    def interval_ok(interval: Any, limit: float) -> bool:
        if (
            not isinstance(interval, Sequence)
            or isinstance(interval, (str, bytes))
            or len(interval) != 2
        ):
            return False
        return all(
            isinstance(item, (int, float))
            and not isinstance(item, bool)
            and math.isfinite(float(item))
            and abs(float(item)) <= limit
            for item in interval
        )

    global_ok = interval_ok(observation["global_shift_interval"], float(tol["global_shift"]))
    interaction_ok = interval_ok(observation["interaction_interval"], float(tol["interaction"]))
    agreement = observation["decision_agreement"]
    agreement_value = (
        agreement
        if isinstance(agreement, (int, float)) and not isinstance(agreement, bool)
        else None
    )
    agreement_ok = agreement_value is not None and agreement_value >= float(tol["agreement"])
    construct_ok = observation["construct_evidence"] == "synthetic_pass"
    reliability_ok = observation["reliability_evidence"] == "synthetic_pass"
    anchor_ok = observation["anchor_agreement"] is not None and float(
        observation["anchor_agreement"]
    ) >= float(tol["agreement"])
    strata = observation["strata"]
    expected_names = None
    expected_weights: dict[str, float] | None = None
    if expected_strata is not None:
        expected_weights = {}
        expected_names = []
        for item in expected_strata:
            if _is_mapping(item):
                name = _critical_string(item.get("stratum"), "expected_strata.stratum")
                expected_weights[name] = float(
                    _require_number(item.get("weight"), "expected_strata.weight", nonnegative=True)
                )
                expected_names.append(name)
            else:
                expected_names.append(_critical_string(item, "expected_strata"))
    strata_names: list[str] = []
    if isinstance(strata, Sequence) and not isinstance(strata, (str, bytes)):
        for item in strata:
            if _is_mapping(item) and isinstance(item.get("stratum"), str):
                strata_names.append(item["stratum"])
    strata_shape_ok = (
        isinstance(strata, Sequence)
        and not isinstance(strata, (str, bytes))
        and bool(strata)
        and all(
            _is_mapping(item)
            and "stratum" in item
            and "weight" in item
            and (
                item.get("pass") is True
                or item.get("outcome") == "pass"
                or "b0e0_score_ref" in item
            )
            for item in strata
        )
    )
    strata_ok = strata_shape_ok and (
        expected_names is None
        or (
            set(strata_names) == set(expected_names) and len(strata_names) == len(set(strata_names))
        )
    )
    hard_fail = (
        not global_ok
        or not interaction_ok
        or not construct_ok
        or not reliability_ok
        or not anchor_ok
        or not strata_ok
        or per_stratum_gate is False
    )
    if not strata_shape_ok or (
        expected_names is not None and set(strata_names) != set(expected_names)
    ):
        outcome = "bridge_insufficient"
    elif hard_fail:
        outcome = "new_epoch_not_comparable"
    elif not agreement_ok or not anchor_ok:
        outcome = "linked_with_uncertainty"
    else:
        outcome = "bridge_comparable"
    return {
        "outcome": outcome,
        "global_shift_pass": global_ok,
        "interaction_pass": interaction_ok,
        "decision_agreement_pass": agreement_ok,
        "construct_pass": construct_ok,
        "reliability_pass": reliability_ok,
        "anchor_pass": anchor_ok,
        "strata_pass": strata_ok,
    }


def bridge_policy(
    observation: Mapping[str, Any],
    *,
    tolerances: Mapping[str, Any] | None = None,
    expected_strata: Iterable[str] | None = None,
    per_stratum_gate: bool | None = None,
) -> dict[str, Any]:
    return evaluate_bridge(
        observation,
        tolerances=tolerances,
        expected_strata=expected_strata,
        per_stratum_gate=per_stratum_gate,
    )


def _protected_independence(value: Any) -> bool:
    if not _is_mapping(value) or not value:
        return False
    allowed = {"separate", "independent", "disjoint", "protected", "pass"}
    statuses = {str(status).casefold() for status in value.values()}
    return statuses.issubset(allowed)


def _validate_independence(value: Any, protocol: Mapping[str, Any] | None) -> bool:
    if not _is_mapping(value):
        return False
    if protocol is None:
        return _protected_independence(value)
    declaration = protocol.get("independence")
    if not _is_mapping(declaration) or not isinstance(
        declaration.get("protected_dimensions"), Sequence
    ):
        return False
    dimensions = [str(item) for item in declaration["protected_dimensions"]]
    if set(value) != set(dimensions):
        return False
    if not _protected_independence(value):
        return False
    ceiling = str(declaration.get("ceiling", "")).casefold()
    return not (
        ceiling in {"separate", "disjoint", "strict"}
        and any(
            str(status).casefold()
            not in {"separate", "independent", "disjoint", "protected", "pass"}
            for status in value.values()
        )
    )


def reduce_promotion(
    current: Mapping[str, Any] | str,
    transition: Mapping[str, Any],
    *,
    evidence: Mapping[str, Any] | None = None,
    protocol: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply one frozen promotion transition, failing closed on blockers."""

    current_state = current if isinstance(current, str) else current.get("state")
    if not isinstance(current_state, str) or current_state not in PROMOTION_STATES:
        _error("promotion_state", "current promotion state is unknown")
    if isinstance(current, Mapping):
        if "transition_hash" not in current:
            _error("promotion_predecessor", "current promotion state must expose transition_hash")
        expected_predecessor = _require_hash(
            current.get("transition_hash"), "current.transition_hash"
        )
    elif current_state == "registered":
        expected_predecessor = "0" * 64
    else:
        _error(
            "promotion_predecessor",
            "non-registered promotion state must expose its predecessor transition hash",
        )
    if not _is_mapping(transition):
        _error("invalid_type", "promotion transition must be an object")
    _strict_keys(
        transition,
        {
            "transition_id",
            "candidate_ref",
            "candidate_hash",
            "from_state",
            "to_state",
            "predecessor_transition_ref",
            "predecessor_transition_hash",
            "actor",
            "approval_actor",
            "independence",
            "confirmation_status",
            "bridge_status",
            "critical_failure",
            "effect_attempt",
            "revoked_ancestry",
            "reason",
            "evidence_refs",
        },
        "promotion_transition",
    )
    required = {"from_state", "to_state", "predecessor_transition_hash", "actor", "approval_actor"}
    missing = sorted(required - set(transition))
    if missing:
        _error("promotion_incomplete", f"promotion transition missing: {', '.join(missing)}")
    from_state = _require_string(transition["from_state"], "transition.from_state")
    to_state = _require_string(transition["to_state"], "transition.to_state")
    if from_state != current_state:
        _error(
            "promotion_predecessor",
            f"transition from_state {from_state} does not match current {current_state}",
        )
    if to_state not in PROMOTION_STATES or to_state not in PROMOTION_TRANSITIONS[from_state]:
        _error(
            "illegal_transition", f"promotion transition {from_state} -> {to_state} is not legal"
        )
    predecessor_hash = _require_hash(
        transition["predecessor_transition_hash"], "transition.predecessor_transition_hash"
    )
    if predecessor_hash != expected_predecessor:
        _error(
            "promotion_predecessor",
            "transition does not bind the exact predecessor transition hash",
        )
    actor = _require_string(transition["actor"], "transition.actor")
    approval_actor = _require_string(transition["approval_actor"], "transition.approval_actor")
    if actor == approval_actor:
        _error("self_approval", "promotion actor and approval actor must be distinct")
    if protocol is not None:
        principals = protocol.get("principals")
        expected_approval = (
            principals.get("promotion", {}).get("principal_id")
            if _is_mapping(principals) and _is_mapping(principals.get("promotion"))
            else None
        )
        if approval_actor != expected_approval:
            _error("approval_authority", "approval_actor is not the frozen promotion principal")
    ev = evidence or {}
    effect_containment = to_state in {"screening_reject", "reject", "revoke"} or (
        from_state == "bridge_eligible" and to_state == "new_measurement_epoch"
    )
    if ev.get("accepted_effect_attempt"):
        _error(
            "effect_quarantine",
            "accepted effect attempt is a critical forbidden-effect failure",
        )
    if (ev.get("effect_attempt") or transition.get("effect_attempt")) and not effect_containment:
        _error(
            "effect_quarantine", "effect attempt quarantines promotion; Stage 0 policy is forbidden"
        )
    if (
        ev.get("critical_failure") or transition.get("critical_failure")
    ) and not effect_containment:
        _error("critical_failure", "critical failure blocks promotion")
    if (
        ev.get("revoked_ancestry") or transition.get("revoked_ancestry")
    ) and not effect_containment:
        _error("revoked_ancestry", "revoked ancestry blocks promotion")
    if not effect_containment and not _validate_independence(
        ev.get("independence", transition.get("independence", {})), protocol
    ):
        _error(
            "independence_ceiling", "unknown or overlapping protected independence blocks promotion"
        )
    abstain_missing = to_state == "abstain" and ev.get("confirmation_unusable_status") in {
        "missing",
        "unavailable",
    }
    if (
        (ev.get("confirmation_reused") or ev.get("tainted_confirmation"))
        and not effect_containment
        and not abstain_missing
    ):
        _error("confirmation_reuse", "reused or tainted confirmation blocks promotion")
    if to_state in {"confirmation_eligible", "promote", "narrow", "abstain"}:
        bridge_status = ev.get("bridge_status", transition.get("bridge_status"))
        if bridge_status not in {"bridge_comparable", "pass", True}:
            _error("missing_bridge", "promotion requires a passing evaluator bridge")
    if from_state == "bridge_eligible" and to_state == "new_measurement_epoch":
        bridge_status = ev.get("bridge_status", transition.get("bridge_status"))
        if bridge_status not in {
            "new_epoch_not_comparable",
            "bridge_insufficient",
            "linked_with_uncertainty",
        }:
            _error(
                "bridge_outcome",
                "new_measurement_epoch requires a failed or uncertain evaluator bridge",
            )
    confirmation_status = ev.get("confirmation_status", transition.get("confirmation_status"))
    allowed_confirmation_statuses = {"fresh", "single_use", "pass", True}
    if to_state == "abstain":
        allowed_confirmation_statuses |= {"tainted", "missing", "unavailable"}
    if (
        to_state in {"promote", "narrow", "abstain"}
        and confirmation_status not in allowed_confirmation_statuses
    ):
        _error("confirmation_ineligible", "promotion requires fresh, single-use confirmation")
    if to_state in {"promote", "narrow"} and ev.get("anchor_pass") is not True:
        _error(
            "confirmation_ineligible",
            "promotion requires the frozen confirmation anchor decision to pass",
        )
    return {
        "state": to_state,
        "transition_hash": canonical_hash(
            _clone_json(transition), domain="ael-cep-promotion-transition"
        ),
        "actor": actor,
        "approval_actor": approval_actor,
    }


def apply_promotion_transition(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return reduce_promotion(*args, **kwargs)


def append_rescore(
    bundle: Mapping[str, Any],
    evaluator_release: Mapping[str, Any],
    score_payload: Mapping[str, Any],
    *,
    actor: str | None = None,
    retained_surfaces: Iterable[str] = (),
    required_surfaces: Iterable[str] = (),
    changes: Iterable[str] | None = None,
    deterministic_code: bool = False,
    protocol: Mapping[str, Any] | None = None,
    predecessor: Mapping[str, Any] | None = None,
    predecessor_chain: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Append a new evaluator release, binding and score without rewriting history."""

    prior = validate_bundle(
        bundle,
        protocol=protocol,
        predecessor=predecessor,
        predecessor_chain=predecessor_chain,
    )
    release_payload = (
        evaluator_release.get("payload")
        if evaluator_release.get("record_type")
        else evaluator_release
    )
    if not _is_mapping(release_payload):
        _error("invalid_type", "evaluator_release must be an evaluator payload or record")
    release_payload = _validate_payload("evaluator_release", release_payload, "evaluator_release")
    release_id = release_payload.get("release_id")
    if not isinstance(release_id, str) or not release_id:
        _error("missing_field", "evaluator release requires release_id")
    refs = _record_refs(prior)
    if release_id in refs:
        _error("duplicate_id", f"evaluator release {release_id} already exists")
    if release_payload.get("self_certification") is True:
        _error("self_certification", "evaluator self-certification is forbidden")
    if actor is None:
        _error(
            "custody_unknown", "append_rescore requires a caller distinct from evaluator custody"
        )
    if (
        protocol is not None
        and actor != freeze_protocol(protocol)["principals"]["adjudication"]["principal_id"]
    ):
        _error("scoring_authority", "append_rescore actor is not the frozen adjudication principal")
    if actor == release_payload.get("custody"):
        _error("self_certification", "evaluator custodian cannot certify its own rescore")
    if protocol is not None:
        adjudication = freeze_protocol(protocol)["principals"]["adjudication"]
        if release_payload.get("custody") in {
            adjudication["principal_id"],
            adjudication["custody"],
        }:
            _error(
                "custody_conflict",
                "evaluator custody must be distinct from adjudication principal and custody",
            )
    if not _is_mapping(score_payload):
        _error("invalid_type", "score_payload must be an object")
    score = _clone_json(score_payload)
    retained = set(retained_surfaces) or set(score.get("surface_refs", ()))
    required = set(required_surfaces) or set(release_payload.get("allowed_evidence_surface", ()))
    if protocol is not None:
        frozen_protocol = freeze_protocol(protocol)
        frozen_required = set(frozen_protocol["replay"]["required_surfaces"])
        if not frozen_required.issubset(required):
            _error(
                "missing_surface",
                "append_rescore cannot weaken the frozen protocol replay surface set",
            )
    if not retained or not required or not required.issubset(retained):
        _error(
            "missing_surface",
            "append_rescore requires retained evidence surfaces covering the evaluator release",
        )
    classification = classify_replay(
        retained_surfaces=retained,
        required_surfaces=required,
        revoked=False,
        changes=changes,
        deterministic_code=deterministic_code,
    )
    if classification != "rescorable":
        _error("rescore_not_allowed", f"replay classifier returned {classification}")
    projection = project_bundle(
        prior,
        protocol=protocol,
        predecessor=predecessor,
        predecessor_chain=predecessor_chain,
    )
    required_score_fields = {
        "evidence_ref",
        "evidence_hash",
        "builder_release_ref",
        "builder_release_hash",
        "method_ref",
        "method_hash",
        "partition",
        "score",
    }
    missing_score = sorted(required_score_fields - set(score))
    if missing_score:
        _error(
            "missing_field",
            f"score_payload missing exact rescore binding field(s): {', '.join(missing_score)}",
        )
    score["evaluator_release_ref"] = release_id
    score["scoring_actor"] = actor
    score.setdefault("score_status", "observed")
    if score.get("score_status") != "observed":
        _error(
            "rescore_status",
            "append_rescore requires score_payload.score_status=observed",
        )
    score.setdefault("surface_refs", sorted(required))
    score_id = score.get("score_run_id")
    if not isinstance(score_id, str) or not score_id:
        _error("missing_field", "score_payload requires score_run_id")
    if score_id in refs:
        _error("duplicate_id", f"score run {score_id} already exists")
    sequence = prior["records"][-1]["sequence"] + 1 if prior["records"] else 0
    previous = prior["records"][-1]["record_hash"] if prior["records"] else None
    release_dependencies: dict[str, str] = {}
    if "parent_release_ref" in release_payload:
        parent_record = refs.get(release_payload["parent_release_ref"])
        if (
            parent_record is None
            or parent_record["record_hash"] != release_payload["parent_release_hash"]
        ):
            _error("parent_identity", "evaluator parent release is not an existing exact record")
        release_dependencies[parent_record["record_id"]] = parent_record["record_hash"]
    epoch_id = (
        prior["records"][0]["epoch_id"]
        if prior["records"]
        else (protocol or {}).get("epoch", {}).get("epoch_id", "epoch")
    )
    release_record = create_record(
        record_id=release_id,
        record_type="evaluator_release",
        epoch_id=epoch_id,
        sequence=sequence,
        previous_record_hash=previous,
        payload=release_payload,
        dependency_refs=release_dependencies,
    )
    score["evaluator_release_hash"] = release_record["record_hash"]
    binding_id = str(score.get("binding_ref") or f"binding:{release_id}:{score_id}")
    builder_record = refs.get(score["builder_release_ref"])
    method_record = refs.get(score["method_ref"])
    evidence_record = refs.get(score["evidence_ref"])
    if (
        builder_record is None
        or builder_record["record_type"] != "builder_release"
        or builder_record["record_hash"] != score["builder_release_hash"]
    ):
        _error(
            "binding_identity",
            "score builder_release_ref/hash must resolve to an existing Builder release",
        )
    if (
        method_record is None
        or method_record["record_type"] != "measurement_method"
        or method_record["record_hash"] != score["method_hash"]
    ):
        _error(
            "binding_identity",
            "score method_ref/hash must resolve to an existing measurement method",
        )
    if evidence_record is None or evidence_record["record_type"] != "subject_execution_evidence":
        _error(
            "historical_only",
            "rescore evidence surface is missing or is not subject execution evidence",
        )
    if evidence_record is not None and evidence_record["record_hash"] != score["evidence_hash"]:
        _error(
            "binding_identity",
            "score evidence_ref/hash must match the existing subject evidence record",
        )
    if (
        evidence_record is not None
        and evidence_record["payload"].get(
            "partition", evidence_record["payload"].get("task_partition")
        )
        == "confirmation"
    ):
        _error(
            "historical_only",
            "confirmation evidence is sealed single-use decision evidence and cannot be rescored",
        )
    rescorable_evidence_statuses = {"observed", "retained", "sealed", "pass", "passed"}
    if (
        evidence_record is not None
        and evidence_record["payload"].get("status") not in rescorable_evidence_statuses
    ):
        _error(
            "historical_only",
            "rescore evidence surface is missing, unavailable, or not in a rescorable status",
        )
    if evidence_record["record_id"] not in refs:
        _error("missing_evidence", "rescore evidence surface is unavailable")
    evidence_payload = evidence_record["payload"]
    prior_scores = [
        item
        for item in prior["records"]
        if item["record_type"] == "score_run"
        and item["payload"].get("evidence_ref") == score["evidence_ref"]
        and item["payload"].get("evidence_hash") == score["evidence_hash"]
    ]
    if not prior_scores:
        _error("binding_identity", "rescore evidence has no prior score binding to replay")
    prior_score = prior_scores[-1]
    canonical_score_key = prior_score["payload"].get("score_key") or prior_score["payload"].get(
        "evidence_ref"
    )
    if "score_key" in score and score.get("score_key") != canonical_score_key:
        _error(
            "score_key",
            "rescore score_key must match the prior canonical score key",
        )
    score["score_key"] = canonical_score_key
    old_binding_record = refs.get(prior_score["payload"].get("binding_ref"))
    if old_binding_record is None or old_binding_record["record_type"] != "evaluation_binding":
        _error("binding_identity", "prior score binding is unavailable for rescore")
    old_binding = old_binding_record["payload"]
    tainted_ids = set(projection["tainted_record_ids"])
    target_ancestry = {
        evidence_record["record_id"],
        prior_score["record_id"],
        old_binding_record["record_id"],
        score["builder_release_ref"],
        score["method_ref"],
    }
    if tainted_ids & target_ancestry:
        _error("tainted_ancestry", "tainted or revoked records block rescore target ancestry")
    if (
        old_binding.get("evidence_ref") != evidence_record["record_id"]
        or old_binding.get("evidence_hash") != evidence_record["record_hash"]
    ):
        _error(
            "binding_identity", "prior evaluation binding does not bind the exact subject evidence"
        )
    for field in (
        "builder_release_ref",
        "builder_release_hash",
        "task_partition",
        "task_ref",
        "task_hash",
        "environment_ref",
        "environment_hash",
        "runner_ref",
        "runner_hash",
        "exposure_state_ref",
        "exposure_state_hash",
    ):
        if evidence_payload.get(field) != old_binding.get(field):
            _error("binding_identity", f"evidence {field} does not match its prior binding")
    for field in (
        "builder_release_ref",
        "builder_release_hash",
        "method_ref",
        "method_hash",
    ):
        if score.get(field) != old_binding.get(field):
            _error(
                "binding_identity",
                f"rescore {field} must match the evidence evaluation binding",
            )
    if score.get("partition") != old_binding.get("task_partition"):
        _error("binding_identity", "rescore partition must match the evidence evaluation binding")
    required_binding_fields = {
        "task_ref",
        "task_hash",
        "analysis_ref",
        "analysis_hash",
        "environment_ref",
        "environment_hash",
        "runner_ref",
        "runner_hash",
        "promotion_policy_ref",
        "promotion_policy_hash",
        "exposure_state_ref",
        "exposure_state_hash",
    }
    missing_binding = sorted(required_binding_fields - set(old_binding))
    if missing_binding:
        _error(
            "binding_identity",
            "existing evaluation binding is missing required identity field(s): "
            + ", ".join(missing_binding),
        )
    evidence_surfaces = set(evidence_payload.get("surface_refs", ()))
    binding_surfaces = set(old_binding.get("allowed_evidence_surface", ()))
    evaluator_surfaces = set(release_payload.get("allowed_evidence_surface", ()))
    if not required.issubset(evidence_surfaces):
        _error("missing_surface", "required rescore surfaces were not retained in subject evidence")
    if not required.issubset(binding_surfaces) or not required.issubset(evaluator_surfaces):
        _error(
            "missing_surface", "required rescore surfaces are not allowed by binding and evaluator"
        )
    old_binding_evaluator_ref = old_binding.get("evaluator_release_ref")
    old_binding_evaluator_hash = old_binding.get("evaluator_release_hash")
    if old_binding_evaluator_ref in tainted_ids:
        _error("tainted_ancestry", "tainted evaluator ancestry blocks rescore target")
    old_evaluator_record = refs.get(old_binding_evaluator_ref)
    if (
        old_evaluator_record is None
        or old_evaluator_record["record_type"] != "evaluator_release"
        or old_evaluator_record["record_hash"] != old_binding_evaluator_hash
    ):
        _error("binding_identity", "existing evaluation binding evaluator identity is unavailable")
    evaluator_identity_fields = (
        "implementation",
        "prompt_or_rubric",
        "model",
        "parser_or_aggregation",
        "tools_or_environment",
        "calibration_lineage",
        "known_error_envelope",
        "allowed_evidence_surface",
    )
    inferred_classification = classify_replay(
        old_evaluator={
            key: old_evaluator_record["payload"].get(key) for key in evaluator_identity_fields
        },
        new_evaluator={key: release_payload.get(key) for key in evaluator_identity_fields},
        retained_surfaces=retained,
        required_surfaces=required,
        deterministic_code=deterministic_code,
        changes=changes,
    )
    if inferred_classification != "rescorable":
        _error("rescore_not_allowed", f"replay classifier returned {inferred_classification}")
    if binding_id in refs:
        _error("duplicate_id", f"evaluation binding {binding_id} already exists")
    binding_payload = {
        "binding_id": binding_id,
        "builder_release_ref": score["builder_release_ref"],
        "builder_release_hash": score["builder_release_hash"],
        "evaluator_release_ref": release_id,
        "evaluator_release_hash": release_record["record_hash"],
        "method_ref": score["method_ref"],
        "method_hash": score["method_hash"],
        "evidence_ref": evidence_record["record_id"],
        "evidence_hash": evidence_record["record_hash"],
        "task_partition": old_binding["task_partition"],
        "task_ref": old_binding["task_ref"],
        "task_hash": old_binding["task_hash"],
        "exposure_policy": old_binding["exposure_policy"],
        "analysis_ref": old_binding["analysis_ref"],
        "analysis_hash": old_binding["analysis_hash"],
        "environment_ref": old_binding["environment_ref"],
        "environment_hash": old_binding["environment_hash"],
        "runner_ref": old_binding["runner_ref"],
        "runner_hash": old_binding["runner_hash"],
        "promotion_policy_ref": old_binding["promotion_policy_ref"],
        "promotion_policy_hash": old_binding["promotion_policy_hash"],
        "exposure_state_ref": old_binding["exposure_state_ref"],
        "exposure_state_hash": old_binding["exposure_state_hash"],
        "allowed_evidence_surface": sorted(required),
    }
    binding_dependencies = {
        release_id: release_record["record_hash"],
        builder_record["record_id"]: builder_record["record_hash"],
        method_record["record_id"]: method_record["record_hash"],
        evidence_record["record_id"]: evidence_record["record_hash"],
    }
    binding_record = create_record(
        record_id=binding_id,
        record_type="evaluation_binding",
        epoch_id=release_record["epoch_id"],
        sequence=sequence + 1,
        previous_record_hash=release_record["record_hash"],
        payload=binding_payload,
        dependency_refs=binding_dependencies,
    )
    score["binding_ref"] = binding_id
    score["binding_hash"] = binding_record["record_hash"]
    evidence_ref = score.get("evidence_ref")
    dependencies = {
        binding_id: binding_record["record_hash"],
        evidence_ref: evidence_record["record_hash"],
        release_id: release_record["record_hash"],
    }
    score_record = create_record(
        record_id=score_id,
        record_type="score_run",
        epoch_id=release_record["epoch_id"],
        sequence=sequence + 2,
        previous_record_hash=binding_record["record_hash"],
        payload=score,
        dependency_refs=dependencies,
    )
    if predecessor_chain is not None:
        return append_bundle(
            prior,
            [release_record, binding_record, score_record],
            bundle_id=f"{prior['bundle_id']}.rescore.{release_id}",
            protocol=protocol,
            predecessor_chain=predecessor_chain,
        )
    return append_bundle(
        prior,
        [release_record, binding_record, score_record],
        bundle_id=f"{prior['bundle_id']}.rescore.{release_id}",
        protocol=protocol,
        predecessor=predecessor,
    )


def append_rescore_bundle(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return append_rescore(*args, **kwargs)


# Alpha.12 supports the CLI and versioned file/schema contracts, not direct
# imports from the policy kernel.  Repository-owned tests and adapters may use
# these symbols internally, but star imports intentionally expose nothing and
# no Python compatibility promise attaches to their current signatures.
__all__: tuple[str, ...] = ()
