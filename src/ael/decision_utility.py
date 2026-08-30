"""Pure policy for the AEL decision-surface calibration instrument.

The module validates one family-local human decision study, renders equivalent
evidence into three presentation arms, builds a deterministic balanced
schedule, and scores retained responses.  It performs no filesystem, clock,
random, network, provider, or participant operation.

This is an experimental repository-owned implementation detail.  The public
contract remains the study files and their checked projections.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any, NoReturn

PROTOCOL_SCHEMA_VERSION = "ael.decision-utility-protocol/0.1-development"
CASE_PACK_SCHEMA_VERSION = "ael.decision-utility-case-pack/0.1-development"
SCHEDULE_SCHEMA_VERSION = "ael.decision-utility-schedule/0.1-development"
SCORE_SCHEMA_VERSION = "ael.decision-utility-score/0.1-development"

ARM_IDS = ("A0", "A1", "A2")
ACTIONS = ("adopt_exact", "narrow", "reject_exact", "retest")
SEVERITIES = ("low", "medium", "high", "critical")
BLOCKING_ACTIONS = frozenset({"reject_exact", "retest"})
POSITIVE_ACTIONS = frozenset({"adopt_exact", "narrow"})


class DecisionUtilityError(ValueError):
    """A deterministic, reason-coded instrument error."""

    def __init__(self, reason: str, detail: str = "") -> None:
        self.reason = reason
        super().__init__(reason if not detail else f"{reason}: {detail}")


def _fail(reason: str, detail: str) -> NoReturn:
    raise DecisionUtilityError(reason, detail)


def _object(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail("invalid_type", f"{path} must be an object")
    return value


def _strict_keys(
    value: Mapping[str, Any], required: set[str], optional: set[str], path: str
) -> None:
    missing = required - set(value)
    unknown = set(value) - required - optional
    if missing:
        _fail("missing_keys", f"{path}: {', '.join(sorted(missing))}")
    if unknown:
        _fail("unknown_keys", f"{path}: {', '.join(sorted(unknown))}")


def _string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail("invalid_string", f"{path} must be non-empty")
    return value


def _integer(value: Any, path: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        _fail("invalid_integer", f"{path} must be an integer >= {minimum}")
    return value


def _boolean(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        _fail("invalid_boolean", f"{path} must be boolean")
    return value


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        _fail("invalid_json_value", str(exc))


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def validate_protocol(value: Mapping[str, Any]) -> dict[str, Any]:
    protocol = _object(value, "protocol")
    _strict_keys(
        protocol,
        {
            "schema_version",
            "protocol_id",
            "revision",
            "arms",
            "actions",
            "severity_weights",
            "strata",
            "primary_estimand",
            "burden_cap_ms",
            "schedule",
            "sample_size",
            "missingness_policy",
            "human_evidence_required",
            "claim_ceiling",
        },
        set(),
        "protocol",
    )
    if protocol["schema_version"] != PROTOCOL_SCHEMA_VERSION:
        _fail("schema_version", f"protocol must use {PROTOCOL_SCHEMA_VERSION}")
    _string(protocol["protocol_id"], "protocol.protocol_id")
    _integer(protocol["revision"], "protocol.revision", minimum=1)

    arms = protocol["arms"]
    if not isinstance(arms, list) or len(arms) != len(ARM_IDS):
        _fail("arm_set", "protocol.arms must contain exactly A0, A1, and A2")
    observed_arms: list[str] = []
    for index, raw_arm in enumerate(arms):
        arm = _object(raw_arm, f"protocol.arms[{index}]")
        _strict_keys(arm, {"arm_id", "label", "format"}, set(), f"protocol.arms[{index}]")
        observed_arms.append(_string(arm["arm_id"], f"protocol.arms[{index}].arm_id"))
        _string(arm["label"], f"protocol.arms[{index}].label")
        _string(arm["format"], f"protocol.arms[{index}].format")
    if tuple(observed_arms) != ARM_IDS:
        _fail("arm_set", f"protocol arms must be ordered {ARM_IDS}")

    actions = protocol["actions"]
    if not isinstance(actions, list) or tuple(actions) != ACTIONS:
        _fail("action_set", f"protocol.actions must be ordered {ACTIONS}")

    weights = _object(protocol["severity_weights"], "protocol.severity_weights")
    _strict_keys(weights, set(SEVERITIES), set(), "protocol.severity_weights")
    weight_values = [
        _integer(weights[severity], f"protocol.severity_weights.{severity}", minimum=1)
        for severity in SEVERITIES
    ]
    if weight_values != sorted(weight_values) or len(set(weight_values)) != len(weight_values):
        _fail("severity_weights", "severity weights must be strictly increasing")

    strata = protocol["strata"]
    if not isinstance(strata, list) or len(strata) < 4:
        _fail("strata", "protocol.strata must contain at least four named strata")
    parsed_strata = [
        _string(item, f"protocol.strata[{index}]") for index, item in enumerate(strata)
    ]
    if len(set(parsed_strata)) != len(parsed_strata):
        _fail("strata", "protocol.strata must be unique")

    if protocol["primary_estimand"] != "severity_weighted_action_error":
        _fail("primary_estimand", "must equal severity_weighted_action_error")
    _integer(protocol["burden_cap_ms"], "protocol.burden_cap_ms", minimum=1)

    schedule = _object(protocol["schedule"], "protocol.schedule")
    _strict_keys(
        schedule,
        {"cases_per_participant", "balanced_arms", "no_repeat_case", "sequence_rule"},
        set(),
        "protocol.schedule",
    )
    cases_per_participant = _integer(
        schedule["cases_per_participant"], "protocol.schedule.cases_per_participant", minimum=3
    )
    if cases_per_participant % len(ARM_IDS):
        _fail("schedule", "cases_per_participant must be divisible by three")
    if not _boolean(schedule["balanced_arms"], "protocol.schedule.balanced_arms"):
        _fail("schedule", "balanced_arms must be true")
    if not _boolean(schedule["no_repeat_case"], "protocol.schedule.no_repeat_case"):
        _fail("schedule", "no_repeat_case must be true")
    if schedule["sequence_rule"] != "cyclic_latin_square":
        _fail("schedule", "sequence_rule must equal cyclic_latin_square")

    sample = _object(protocol["sample_size"], "protocol.sample_size")
    _strict_keys(
        sample,
        {"status", "independent_unit", "pilot_participants", "target_participants", "basis"},
        set(),
        "protocol.sample_size",
    )
    if sample["status"] not in {"pending_pilot", "admitted"}:
        _fail("sample_size", "status must be pending_pilot or admitted")
    if sample["independent_unit"] != "human_participant":
        _fail("sample_size", "independent_unit must equal human_participant")
    pilot = sample["pilot_participants"]
    target = sample["target_participants"]
    if pilot is not None:
        _integer(pilot, "protocol.sample_size.pilot_participants", minimum=1)
    if target is not None:
        _integer(target, "protocol.sample_size.target_participants", minimum=1)
    if sample["status"] == "pending_pilot" and target is not None:
        _fail("sample_size", "pending_pilot cannot declare a target_participants value")
    if sample["status"] == "admitted" and (pilot is None or target is None):
        _fail("sample_size", "admitted sample size requires pilot and target counts")
    _string(sample["basis"], "protocol.sample_size.basis")

    if protocol["missingness_policy"] != "retain_as_missing_no_imputation":
        _fail("missingness_policy", "must retain missing responses without imputation")
    if not _boolean(protocol["human_evidence_required"], "protocol.human_evidence_required"):
        _fail("human_evidence_required", "must be true")
    if protocol["claim_ceiling"] != "instrument_qualification_only_until_human_outcomes":
        _fail("claim_ceiling", "must remain instrument qualification until human outcomes exist")
    return json.loads(_canonical(protocol))


def validate_case_pack(protocol: Mapping[str, Any], value: Mapping[str, Any]) -> dict[str, Any]:
    frozen = validate_protocol(protocol)
    pack = _object(value, "case_pack")
    _strict_keys(
        pack,
        {"schema_version", "pack_id", "revision", "role", "cases"},
        set(),
        "case_pack",
    )
    if pack["schema_version"] != CASE_PACK_SCHEMA_VERSION:
        _fail("schema_version", f"case pack must use {CASE_PACK_SCHEMA_VERSION}")
    _string(pack["pack_id"], "case_pack.pack_id")
    _integer(pack["revision"], "case_pack.revision", minimum=1)
    if pack["role"] != "public_instrument_calibration_only":
        _fail("case_pack_role", "public case pack must be calibration-only")
    cases = pack["cases"]
    if not isinstance(cases, list) or len(cases) != frozen["schedule"]["cases_per_participant"]:
        _fail("case_count", "calibration pack must match cases_per_participant")

    case_ids: set[str] = set()
    seen_strata: set[str] = set()
    seen_recommendation_states: set[str] = set()
    for index, raw_case in enumerate(cases):
        case = _object(raw_case, f"case_pack.cases[{index}]")
        _strict_keys(
            case,
            {
                "case_id",
                "title",
                "decision_question",
                "stratum",
                "severity",
                "critical",
                "presented_recommendation",
                "correct_action",
                "recommendation_state",
                "facts",
                "rationale",
            },
            set(),
            f"case_pack.cases[{index}]",
        )
        case_id = _string(case["case_id"], f"case_pack.cases[{index}].case_id")
        if case_id in case_ids:
            _fail("duplicate_case", case_id)
        case_ids.add(case_id)
        _string(case["title"], f"case_pack.cases[{index}].title")
        _string(case["decision_question"], f"case_pack.cases[{index}].decision_question")
        stratum = _string(case["stratum"], f"case_pack.cases[{index}].stratum")
        if stratum not in frozen["strata"]:
            _fail("unknown_stratum", f"{case_id}: {stratum}")
        seen_strata.add(stratum)
        severity = _string(case["severity"], f"case_pack.cases[{index}].severity")
        if severity not in SEVERITIES:
            _fail("unknown_severity", f"{case_id}: {severity}")
        critical = _boolean(case["critical"], f"case_pack.cases[{index}].critical")
        if critical != (severity == "critical"):
            _fail("critical_flag", f"{case_id}: critical must match critical severity")
        for key in ("presented_recommendation", "correct_action"):
            if case[key] not in ACTIONS:
                _fail("unknown_action", f"{case_id}.{key}: {case[key]}")
        expected_state = (
            "supported"
            if case["presented_recommendation"] == case["correct_action"]
            else "contradicted"
        )
        if case["recommendation_state"] != expected_state:
            _fail("recommendation_state", f"{case_id}: expected {expected_state}")
        seen_recommendation_states.add(expected_state)
        facts = case["facts"]
        if not isinstance(facts, list) or len(facts) < 4:
            _fail("fact_count", f"{case_id} must contain at least four facts")
        fact_ids: set[str] = set()
        for fact_index, raw_fact in enumerate(facts):
            fact = _object(raw_fact, f"{case_id}.facts[{fact_index}]")
            _strict_keys(
                fact,
                {"fact_id", "label", "value"},
                set(),
                f"{case_id}.facts[{fact_index}]",
            )
            fact_id = _string(fact["fact_id"], f"{case_id}.facts[{fact_index}].fact_id")
            if fact_id in fact_ids:
                _fail("duplicate_fact", f"{case_id}: {fact_id}")
            fact_ids.add(fact_id)
            _string(fact["label"], f"{case_id}.facts[{fact_index}].label")
            _string(fact["value"], f"{case_id}.facts[{fact_index}].value")
        _string(case["rationale"], f"case_pack.cases[{index}].rationale")

    if len(seen_strata) < 4:
        _fail("strata_coverage", "calibration pack must cover at least four strata")
    if seen_recommendation_states != {"supported", "contradicted"}:
        _fail("recommendation_coverage", "pack must include right and wrong recommendations")
    return json.loads(_canonical(pack))


def _evidence_payload(case: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "decision_question": case["decision_question"],
        "presented_recommendation": case["presented_recommendation"],
        "facts": [
            {"fact_id": fact["fact_id"], "label": fact["label"], "value": fact["value"]}
            for fact in case["facts"]
        ],
    }


def render_case(case: Mapping[str, Any], arm_id: str) -> dict[str, Any]:
    if arm_id not in ARM_IDS:
        _fail("unknown_arm", arm_id)
    evidence = _evidence_payload(case)
    fingerprint = canonical_sha256(evidence)
    facts = evidence["facts"]
    if arm_id == "A0":
        content: dict[str, Any] = {
            "heading": case["title"],
            "recommendation": evidence["presented_recommendation"],
            "narrative": [f"{fact['label']}: {fact['value']}" for fact in facts],
        }
        format_name = "ordinary_decision_note"
    elif arm_id == "A1":
        content = {
            "heading": case["title"],
            "recommendation": evidence["presented_recommendation"],
            "narrative": [f"{fact['label']}: {fact['value']}" for fact in facts],
            "checklist": [
                {"fact_id": fact["fact_id"], "checked": True, "label": fact["label"]}
                for fact in facts
            ],
        }
        format_name = "decision_note_with_static_checklist"
    else:
        content = {
            "decision": evidence["presented_recommendation"],
            "question": evidence["decision_question"],
            "claim_first_facts": facts,
            "scope": {"stratum": case["stratum"], "severity": case["severity"]},
        }
        format_name = "ael_claim_first_card"
    return {
        "schema_version": "ael.decision-utility-view/0.1-development",
        "case_id": case["case_id"],
        "arm_id": arm_id,
        "format": format_name,
        "evidence_fingerprint": fingerprint,
        "content": content,
    }


def build_views(protocol: Mapping[str, Any], case_pack: Mapping[str, Any]) -> list[dict[str, Any]]:
    frozen_pack = validate_case_pack(protocol, case_pack)
    views = [render_case(case, arm_id) for case in frozen_pack["cases"] for arm_id in ARM_IDS]
    for case in frozen_pack["cases"]:
        fingerprints = {
            view["evidence_fingerprint"] for view in views if view["case_id"] == case["case_id"]
        }
        if len(fingerprints) != 1:
            _fail("evidence_drift", case["case_id"])
    return views


def build_schedule(
    protocol: Mapping[str, Any], case_pack: Mapping[str, Any], participant_ids: Sequence[str]
) -> dict[str, Any]:
    frozen = validate_protocol(protocol)
    pack = validate_case_pack(frozen, case_pack)
    if len(participant_ids) < len(ARM_IDS) or len(participant_ids) % len(ARM_IDS):
        _fail("participant_block", "calibration participants must be a positive multiple of three")
    parsed_participants = [
        _string(item, f"participant_ids[{index}]") for index, item in enumerate(participant_ids)
    ]
    if len(set(parsed_participants)) != len(parsed_participants):
        _fail("duplicate_participant", "participant IDs must be unique")
    cases = pack["cases"]
    cells: list[dict[str, Any]] = []
    for participant_index, participant_id in enumerate(parsed_participants):
        rotation = participant_index % len(cases)
        ordered_cases = cases[rotation:] + cases[:rotation]
        for position, case in enumerate(ordered_cases):
            # Cases rotate by one position for each participant.  Advancing the
            # arm by two positions prevents that rotation from cancelling the
            # arm change, so every case appears in A0/A1/A2 across a
            # three-participant block while every participant remains balanced.
            arm_id = ARM_IDS[(position + 2 * participant_index) % len(ARM_IDS)]
            cells.append(
                {
                    "participant_id": participant_id,
                    "position": position + 1,
                    "case_id": case["case_id"],
                    "arm_id": arm_id,
                }
            )
    for participant_id in parsed_participants:
        participant_cells = [cell for cell in cells if cell["participant_id"] == participant_id]
        if len({cell["case_id"] for cell in participant_cells}) != len(cases):
            _fail("schedule_repeat", participant_id)
        counts = {arm: sum(cell["arm_id"] == arm for cell in participant_cells) for arm in ARM_IDS}
        if len(set(counts.values())) != 1:
            _fail("schedule_balance", f"{participant_id}: {counts}")
    schedule = {
        "schema_version": SCHEDULE_SCHEMA_VERSION,
        "protocol_id": frozen["protocol_id"],
        "protocol_revision": frozen["revision"],
        "case_pack_id": pack["pack_id"],
        "case_pack_revision": pack["revision"],
        "participant_count": len(parsed_participants),
        "cells": cells,
    }
    return validate_schedule(frozen, pack, schedule)


def validate_schedule(
    protocol: Mapping[str, Any], case_pack: Mapping[str, Any], value: Mapping[str, Any]
) -> dict[str, Any]:
    frozen = validate_protocol(protocol)
    pack = validate_case_pack(frozen, case_pack)
    schedule = _object(value, "schedule")
    _strict_keys(
        schedule,
        {
            "schema_version",
            "protocol_id",
            "protocol_revision",
            "case_pack_id",
            "case_pack_revision",
            "participant_count",
            "cells",
        },
        set(),
        "schedule",
    )
    if schedule["schema_version"] != SCHEDULE_SCHEMA_VERSION:
        _fail("schema_version", f"schedule must use {SCHEDULE_SCHEMA_VERSION}")
    if (
        schedule["protocol_id"] != frozen["protocol_id"]
        or schedule["protocol_revision"] != frozen["revision"]
    ):
        _fail("schedule_protocol", "schedule protocol identity does not match")
    if (
        schedule["case_pack_id"] != pack["pack_id"]
        or schedule["case_pack_revision"] != pack["revision"]
    ):
        _fail("schedule_pack", "schedule case-pack identity does not match")
    participant_count = _integer(
        schedule["participant_count"], "schedule.participant_count", minimum=3
    )
    if participant_count % len(ARM_IDS):
        _fail("participant_block", "schedule participant count must be divisible by three")
    cells = schedule["cells"]
    expected_cell_count = participant_count * len(pack["cases"])
    if not isinstance(cells, list) or len(cells) != expected_cell_count:
        _fail("schedule_cells", f"schedule must contain exactly {expected_cell_count} cells")
    case_ids = {case["case_id"] for case in pack["cases"]}
    participant_ids: set[str] = set()
    seen_pairs: set[tuple[str, str]] = set()
    parsed_cells: list[dict[str, Any]] = []
    for index, raw_cell in enumerate(cells):
        cell = _object(raw_cell, f"schedule.cells[{index}]")
        _strict_keys(
            cell,
            {"participant_id", "position", "case_id", "arm_id"},
            set(),
            f"schedule.cells[{index}]",
        )
        participant_id = _string(cell["participant_id"], f"schedule.cells[{index}].participant_id")
        participant_ids.add(participant_id)
        position = _integer(cell["position"], f"schedule.cells[{index}].position", minimum=1)
        if position > len(pack["cases"]):
            _fail("schedule_position", f"schedule.cells[{index}].position")
        case_id = _string(cell["case_id"], f"schedule.cells[{index}].case_id")
        if case_id not in case_ids:
            _fail("unknown_case", f"schedule.cells[{index}]: {case_id}")
        arm_id = _string(cell["arm_id"], f"schedule.cells[{index}].arm_id")
        if arm_id not in ARM_IDS:
            _fail("unknown_arm", f"schedule.cells[{index}]: {arm_id}")
        pair = (participant_id, case_id)
        if pair in seen_pairs:
            _fail("schedule_repeat", f"{participant_id}:{case_id}")
        seen_pairs.add(pair)
        parsed_cells.append(
            {
                "participant_id": participant_id,
                "position": position,
                "case_id": case_id,
                "arm_id": arm_id,
            }
        )
    if len(participant_ids) != participant_count:
        _fail("participant_count", "schedule participant_count does not match unique IDs")
    for participant_id in participant_ids:
        participant_cells = [
            cell for cell in parsed_cells if cell["participant_id"] == participant_id
        ]
        if {cell["position"] for cell in participant_cells} != set(
            range(1, len(pack["cases"]) + 1)
        ):
            _fail("schedule_position", f"{participant_id} positions are incomplete")
        counts = {arm: sum(cell["arm_id"] == arm for cell in participant_cells) for arm in ARM_IDS}
        if len(set(counts.values())) != 1:
            _fail("schedule_balance", f"{participant_id}: {counts}")
    for case_id in case_ids:
        case_cells = [cell for cell in parsed_cells if cell["case_id"] == case_id]
        arm_counts = {arm: sum(cell["arm_id"] == arm for cell in case_cells) for arm in ARM_IDS}
        if len(set(arm_counts.values())) != 1:
            _fail("case_arm_balance", f"{case_id}: {arm_counts}")
    normalized = dict(schedule)
    normalized["cells"] = parsed_cells
    return json.loads(_canonical(normalized))


def score_responses(
    protocol: Mapping[str, Any],
    case_pack: Mapping[str, Any],
    schedule: Mapping[str, Any],
    responses: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    frozen = validate_protocol(protocol)
    pack = validate_case_pack(frozen, case_pack)
    cases = {case["case_id"]: case for case in pack["cases"]}
    frozen_schedule = validate_schedule(frozen, pack, schedule)
    schedule_cells = {
        (cell["participant_id"], cell["case_id"]): cell for cell in frozen_schedule["cells"]
    }
    expected_cells = len(schedule_cells)
    seen: set[tuple[str, str]] = set()
    by_arm = {
        arm: {
            "observed": 0,
            "errors": 0,
            "weighted_error_numerator": 0,
            "weighted_error_denominator": 0,
            "critical_misses": 0,
            "false_blocks": 0,
            "duration_ms_sum": 0,
            "workload_sum": 0,
            "burden_cap_breaches": 0,
            "calibration_abs_error_ppm_sum": 0,
            "severity": {severity: {"observed": 0, "errors": 0} for severity in SEVERITIES},
        }
        for arm in ARM_IDS
    }
    for index, raw_response in enumerate(responses):
        response = _object(raw_response, f"responses[{index}]")
        _strict_keys(
            response,
            {
                "participant_id",
                "case_id",
                "arm_id",
                "action",
                "confidence_ppm",
                "duration_ms",
                "workload",
            },
            set(),
            f"responses[{index}]",
        )
        participant_id = _string(response["participant_id"], f"responses[{index}].participant_id")
        case_id = _string(response["case_id"], f"responses[{index}].case_id")
        key = (participant_id, case_id)
        if key in seen:
            _fail("duplicate_response", f"{participant_id}:{case_id}")
        seen.add(key)
        scheduled = schedule_cells.get(key)
        if scheduled is None:
            _fail("unscheduled_response", f"{participant_id}:{case_id}")
        arm_id = response["arm_id"]
        if arm_id != scheduled["arm_id"]:
            _fail("arm_mismatch", f"{participant_id}:{case_id}")
        action = response["action"]
        if action not in ACTIONS:
            _fail("unknown_action", f"responses[{index}].action")
        confidence = _integer(response["confidence_ppm"], f"responses[{index}].confidence_ppm")
        if confidence > 1_000_000:
            _fail("confidence_range", f"responses[{index}].confidence_ppm")
        duration = _integer(response["duration_ms"], f"responses[{index}].duration_ms", minimum=1)
        workload = _integer(response["workload"], f"responses[{index}].workload", minimum=1)
        if workload > 7:
            _fail("workload_range", f"responses[{index}].workload")
        case = cases[case_id]
        correct = action == case["correct_action"]
        severity = case["severity"]
        weight = frozen["severity_weights"][severity]
        metrics = by_arm[arm_id]
        metrics["observed"] += 1
        metrics["errors"] += int(not correct)
        metrics["weighted_error_numerator"] += weight * int(not correct)
        metrics["weighted_error_denominator"] += weight
        metrics["critical_misses"] += int(case["critical"] and not correct)
        metrics["false_blocks"] += int(
            action in BLOCKING_ACTIONS and case["correct_action"] in POSITIVE_ACTIONS
        )
        metrics["duration_ms_sum"] += duration
        metrics["workload_sum"] += workload
        metrics["burden_cap_breaches"] += int(duration > frozen["burden_cap_ms"])
        truth_ppm = 1_000_000 if correct else 0
        metrics["calibration_abs_error_ppm_sum"] += abs(confidence - truth_ppm)
        metrics["severity"][severity]["observed"] += 1
        metrics["severity"][severity]["errors"] += int(not correct)
    return {
        "schema_version": SCORE_SCHEMA_VERSION,
        "protocol_id": frozen["protocol_id"],
        "case_pack_id": pack["pack_id"],
        "state": "calibration_only_not_human_utility_evidence",
        "expected_cells": expected_cells,
        "observed_cells": len(seen),
        "missing_cells": expected_cells - len(seen),
        "by_arm": by_arm,
    }


# No compatibility-bearing Python API is published for the development study.
__all__: tuple[str, ...] = ()
