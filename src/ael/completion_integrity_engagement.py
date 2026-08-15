"""Pure observable-chain classifier for the Completion Integrity candidate.

The classifier consumes normalized pilot fixtures. It does not claim that the
normalized events were captured by a real harness, and it never infers an
agent's cognition, attention, or causal mediation.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

METHOD_PLAN_VERSION = "ael.completion-integrity-enactment-plan/0.1-pilot"
OBSERVATION_VERSION = "ael.completion-integrity-enactment-observation/0.1-pilot"
DIAGNOSTIC_VERSION = "ael.completion-integrity-enactment-diagnostic/0.1-pilot"
REPORT_VERSION = "ael.completion-integrity-enactment-report/0.1-pilot"

_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_STAGES = ("inspect", "change", "verify", "reconcile")
_FACETS = (
    "policy_bytes_bound",
    "ledger_materialized",
    "checks_evidenced",
    "terminal_reconciled",
)


@dataclass(frozen=True)
class EngagementIssue:
    """One stable, ordered validation finding."""

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


def _issue(issues: list[EngagementIssue], code: str, location: str, message: str) -> None:
    issues.append(EngagementIssue("error", code, location, message))


def _sorted(issues: Sequence[EngagementIssue]) -> tuple[EngagementIssue, ...]:
    return tuple(sorted(issues, key=lambda item: (item.code, item.location)))


def _object(
    value: object,
    required: set[str],
    optional: set[str],
    location: str,
    issues: list[EngagementIssue],
) -> Mapping[str, Any] | None:
    if not isinstance(value, Mapping):
        _issue(issues, "CI10-E001", location, "must be an object")
        return None
    missing = required - set(value)
    unknown = set(value) - required - optional
    if missing:
        _issue(issues, "CI10-E002", location, f"missing keys: {', '.join(sorted(missing))}")
    if unknown:
        _issue(issues, "CI10-E003", location, f"unknown keys: {', '.join(sorted(unknown))}")
    return value


def _identifier(value: object, location: str, issues: list[EngagementIssue]) -> str | None:
    if not isinstance(value, str) or _IDENTIFIER.fullmatch(value) is None:
        _issue(issues, "CI10-E004", location, "must be a bounded opaque identifier")
        return None
    return value


def _text(value: object, location: str, issues: list[EngagementIssue]) -> str | None:
    if not isinstance(value, str) or not value.strip():
        _issue(issues, "CI10-E005", location, "must be a non-empty string")
        return None
    return value


def _sha(value: object, location: str, issues: list[EngagementIssue]) -> str | None:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        _issue(issues, "CI10-E006", location, "must be a lowercase SHA-256 digest")
        return None
    return value


def _positive_int(value: object, location: str, issues: list[EngagementIssue]) -> int | None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        _issue(issues, "CI10-E007", location, "must be a positive integer")
        return None
    return value


def _identifier_array(
    value: object,
    location: str,
    issues: list[EngagementIssue],
    *,
    allow_empty: bool = False,
) -> list[str] | None:
    if not isinstance(value, list) or (not allow_empty and not value):
        qualifier = "an array" if allow_empty else "a non-empty array"
        _issue(issues, "CI10-E008", location, f"must be {qualifier}")
        return None
    parsed: list[str] = []
    for index, item in enumerate(value):
        identifier = _identifier(item, f"{location}[{index}]", issues)
        if identifier is not None:
            parsed.append(identifier)
    if len(set(parsed)) != len(parsed):
        _issue(issues, "CI10-E009", location, "must not contain duplicates")
    return parsed


def canonical_ledger_sha256(value: object) -> str:
    """Return the one canonical digest used for normalized ledger entries."""

    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_method_plan(plan: Mapping[str, Any]) -> tuple[EngagementIssue, ...]:
    """Validate the family-local pilot declaration."""

    issues: list[EngagementIssue] = []
    root = _object(
        plan,
        {"schema_version", "plan_id", "policy_ref", "engagement_rule", "causal_boundary"},
        set(),
        "method_plan",
        issues,
    )
    if root is None:
        return _sorted(issues)
    if root.get("schema_version") != METHOD_PLAN_VERSION:
        _issue(
            issues,
            "CI10-E010",
            "method_plan.schema_version",
            f"must equal {METHOD_PLAN_VERSION}",
        )
    _identifier(root.get("plan_id"), "method_plan.plan_id", issues)
    policy_ref = _object(
        root.get("policy_ref"),
        {"policy_id", "uri", "sha256"},
        set(),
        "method_plan.policy_ref",
        issues,
    )
    if policy_ref:
        _identifier(policy_ref.get("policy_id"), "method_plan.policy_ref.policy_id", issues)
        _text(policy_ref.get("uri"), "method_plan.policy_ref.uri", issues)
        _sha(policy_ref.get("sha256"), "method_plan.policy_ref.sha256", issues)
    rule = _object(
        root.get("engagement_rule"),
        {
            "missing_evidence",
            "unknown_requirement",
            "duplicate_requirement",
            "successful_check_required",
            "check_before_terminal_required",
            "all_requirements_reconciled",
            "repair_loops_allowed",
        },
        set(),
        "method_plan.engagement_rule",
        issues,
    )
    if rule:
        expected = {
            "missing_evidence": "not_assessable",
            "unknown_requirement": "invalid",
            "duplicate_requirement": "invalid",
            "successful_check_required": True,
            "check_before_terminal_required": True,
            "all_requirements_reconciled": True,
            "repair_loops_allowed": True,
        }
        for key, expected_value in expected.items():
            if rule.get(key) != expected_value:
                _issue(
                    issues,
                    "CI10-E011",
                    f"method_plan.engagement_rule.{key}",
                    f"must equal {expected_value!r} for this pilot revision",
                )
    _text(root.get("causal_boundary"), "method_plan.causal_boundary", issues)
    return _sorted(issues)


def _empty_diagnostic(
    observation: Mapping[str, Any], state: str, issues: Sequence[EngagementIssue], boundary: str
) -> dict[str, Any]:
    return {
        "schema_version": DIAGNOSTIC_VERSION,
        "cell_id": observation.get("cell_id"),
        "state": state,
        "facets": {facet: "not_assessable" for facet in _FACETS},
        "stage_vector": {
            **{stage: "not_assessable" for stage in _STAGES},
            "declare": "not_assessable",
        },
        "counts": {
            "requirements": 0,
            "ledger_entries": 0,
            "successful_preterminal_checks": 0,
            "supported_blockers": 0,
            "unresolved_requirements": 0,
        },
        "source_hashes": {},
        "issues": [issue.as_dict() for issue in _sorted(issues)],
        "boundary": boundary,
    }


def diagnose_policy_enactment(
    method_plan: Mapping[str, Any], observation: Mapping[str, Any], policy_bytes: bytes
) -> dict[str, Any]:
    """Classify one normalized candidate fixture without inferring cognition.

    The pure policy receives immutable policy bytes from its outward adapter and
    hashes them itself.  Matching caller-provided digest strings alone cannot
    satisfy the policy-byte facet.
    """

    issues = list(validate_method_plan(method_plan))
    root = _object(
        observation,
        {"schema_version", "cell_id", "capture_state"},
        {
            "reason",
            "policy_sha256",
            "ledger_sha256",
            "requirement_ids",
            "ledger_entries",
            "events",
            "terminal_marker",
        },
        "observation",
        issues,
    )
    if root is None:
        return _empty_diagnostic(
            observation, "invalid", issues, "Invalid input supports no observable-chain claim."
        )
    if root.get("schema_version") != OBSERVATION_VERSION:
        _issue(
            issues,
            "CI10-E012",
            "observation.schema_version",
            f"must equal {OBSERVATION_VERSION}",
        )
    _identifier(root.get("cell_id"), "observation.cell_id", issues)
    capture_state = root.get("capture_state")
    if capture_state not in {"assessable", "unavailable_historical"}:
        _issue(
            issues,
            "CI10-E013",
            "observation.capture_state",
            "must be assessable or unavailable_historical",
        )
    if capture_state == "unavailable_historical":
        if set(root) != {"schema_version", "cell_id", "capture_state", "reason"}:
            _issue(
                issues,
                "CI10-E014",
                "observation",
                "historical unavailable input may contain only its reason",
            )
        _text(root.get("reason"), "observation.reason", issues)
        if issues:
            return _empty_diagnostic(
                observation, "invalid", issues, "Invalid input supports no observable-chain claim."
            )
        return _empty_diagnostic(
            observation,
            "not_assessable",
            (),
            "The required normalized ledger and event bindings were not retained; alpha.9 supports neither an enactment nor a non-enactment claim.",
        )

    required = {
        "policy_sha256",
        "ledger_sha256",
        "requirement_ids",
        "ledger_entries",
        "events",
        "terminal_marker",
    }
    missing = required - set(root)
    if missing:
        _issue(
            issues,
            "CI10-E002",
            "observation",
            f"assessable input is missing keys: {', '.join(sorted(missing))}",
        )
        return _empty_diagnostic(
            observation, "invalid", issues, "Invalid input supports no observable-chain claim."
        )

    expected_policy = (
        method_plan.get("policy_ref", {}).get("sha256")
        if isinstance(method_plan.get("policy_ref"), Mapping)
        else None
    )
    if not isinstance(policy_bytes, bytes):
        _issue(
            issues,
            "CI10-E028",
            "policy_bytes",
            "must be immutable bytes supplied by the evidence-owning adapter",
        )
        observed_policy_bytes = None
    else:
        observed_policy_bytes = hashlib.sha256(policy_bytes).hexdigest()
        if observed_policy_bytes != expected_policy:
            _issue(
                issues,
                "CI10-E029",
                "policy_bytes",
                "SHA-256 does not match the method plan policy reference",
            )
    supplied_policy = _sha(root.get("policy_sha256"), "observation.policy_sha256", issues)
    if supplied_policy is not None and supplied_policy != expected_policy:
        _issue(
            issues,
            "CI10-E015",
            "observation.policy_sha256",
            "does not match the method plan policy hash",
        )
    supplied_ledger = _sha(root.get("ledger_sha256"), "observation.ledger_sha256", issues)
    requirements = (
        _identifier_array(root.get("requirement_ids"), "observation.requirement_ids", issues) or []
    )

    events_value = root.get("events")
    events: list[Mapping[str, Any]] = []
    if not isinstance(events_value, list):
        _issue(issues, "CI10-E016", "observation.events", "must be an array")
    else:
        for index, value in enumerate(events_value):
            event = _object(
                value,
                {"event_id", "stage", "sequence", "outcome", "sha256"},
                set(),
                f"observation.events[{index}]",
                issues,
            )
            if event is not None:
                events.append(event)
    event_ids: list[str] = []
    sequences: list[int] = []
    for index, event in enumerate(events):
        location = f"observation.events[{index}]"
        event_id = _identifier(event.get("event_id"), f"{location}.event_id", issues)
        if event_id is not None:
            event_ids.append(event_id)
        if event.get("stage") not in _STAGES:
            _issue(issues, "CI10-E017", f"{location}.stage", f"must be one of {list(_STAGES)}")
        sequence = _positive_int(event.get("sequence"), f"{location}.sequence", issues)
        if sequence is not None:
            sequences.append(sequence)
        if event.get("outcome") not in {"observed", "success", "failure"}:
            _issue(
                issues,
                "CI10-E018",
                f"{location}.outcome",
                "must be observed, success, or failure",
            )
        _sha(event.get("sha256"), f"{location}.sha256", issues)
    if len(set(event_ids)) != len(event_ids):
        _issue(issues, "CI10-E009", "observation.events.event_id", "must be unique")
    if len(set(sequences)) != len(sequences):
        _issue(issues, "CI10-E009", "observation.events.sequence", "must be unique")

    terminal = _object(
        root.get("terminal_marker"),
        {"state", "sequence", "sha256"},
        set(),
        "observation.terminal_marker",
        issues,
    )
    terminal_state: str | None = None
    terminal_sequence: int | None = None
    if terminal:
        if terminal.get("state") not in {
            "claimed_complete",
            "claimed_incomplete",
            "claimed_blocked",
            "indeterminate",
        }:
            _issue(
                issues,
                "CI10-E019",
                "observation.terminal_marker.state",
                "has an unsupported terminal state",
            )
        else:
            terminal_state = str(terminal.get("state"))
        terminal_sequence = _positive_int(
            terminal.get("sequence"), "observation.terminal_marker.sequence", issues
        )
        _sha(terminal.get("sha256"), "observation.terminal_marker.sha256", issues)
        if terminal_sequence is not None and any(
            sequence >= terminal_sequence for sequence in sequences
        ):
            _issue(
                issues,
                "CI10-E020",
                "observation.terminal_marker.sequence",
                "must follow every normalized process event",
            )

    ledger_value = root.get("ledger_entries")
    ledger: list[Mapping[str, Any]] = []
    if not isinstance(ledger_value, list):
        _issue(issues, "CI10-E021", "observation.ledger_entries", "must be an array")
    else:
        for index, value in enumerate(ledger_value):
            entry = _object(
                value,
                {"requirement_id", "status", "evidence_event_ids"},
                set(),
                f"observation.ledger_entries[{index}]",
                issues,
            )
            if entry is not None:
                ledger.append(entry)
    if supplied_ledger is not None and supplied_ledger != canonical_ledger_sha256(ledger_value):
        _issue(
            issues,
            "CI10-E022",
            "observation.ledger_sha256",
            "does not match the canonical ledger_entries bytes",
        )

    event_by_id = {
        str(event.get("event_id")): event
        for event in events
        if isinstance(event.get("event_id"), str)
    }
    latest_change_sequence = max(
        (
            int(event["sequence"])
            for event in events
            if event.get("stage") == "change" and isinstance(event.get("sequence"), int)
        ),
        default=0,
    )
    ledger_ids: list[str] = []
    checks_valid = bool(events)
    successful_checks: set[str] = set()
    supported_blockers: set[str] = set()
    cited_preterminal_sequences: list[int] = []
    statuses: list[str] = []
    for index, entry in enumerate(ledger):
        location = f"observation.ledger_entries[{index}]"
        requirement_id = _identifier(
            entry.get("requirement_id"), f"{location}.requirement_id", issues
        )
        if requirement_id is not None:
            ledger_ids.append(requirement_id)
            if requirement_id not in requirements:
                _issue(
                    issues,
                    "CI10-E023",
                    f"{location}.requirement_id",
                    "is not declared by the task requirement set",
                )
        status = entry.get("status")
        if status not in {"satisfied", "unmet", "blocked"}:
            _issue(
                issues,
                "CI10-E024",
                f"{location}.status",
                "must be satisfied, unmet, or blocked",
            )
        else:
            statuses.append(str(status))
        evidence_ids = (
            _identifier_array(
                entry.get("evidence_event_ids"),
                f"{location}.evidence_event_ids",
                issues,
                allow_empty=True,
            )
            or []
        )
        referenced_events: list[Mapping[str, Any]] = []
        for evidence_id in evidence_ids:
            event = event_by_id.get(evidence_id)
            if event is None:
                _issue(
                    issues,
                    "CI10-E025",
                    f"{location}.evidence_event_ids",
                    f"references unknown event {evidence_id}",
                )
            else:
                referenced_events.append(event)
        preterminal = [
            event
            for event in referenced_events
            if terminal_sequence is not None
            and isinstance(event.get("sequence"), int)
            and int(event["sequence"]) < terminal_sequence
        ]
        cited_preterminal_sequences.extend(int(event["sequence"]) for event in preterminal)
        if status == "satisfied":
            successful = [
                event
                for event in preterminal
                if event.get("stage") == "verify"
                and event.get("outcome") == "success"
                and int(event["sequence"]) > latest_change_sequence
            ]
            if not successful:
                checks_valid = False
            successful_checks.update(str(event["event_id"]) for event in successful)
        elif status == "blocked":
            blocker_events = [
                event
                for event in preterminal
                if event.get("stage") == "verify" and event.get("outcome") == "failure"
            ]
            if not blocker_events:
                checks_valid = False
            else:
                supported_blockers.add(str(requirement_id))
    if len(set(ledger_ids)) != len(ledger_ids):
        _issue(
            issues,
            "CI10-E026",
            "observation.ledger_entries.requirement_id",
            "must not contain duplicate requirements",
        )

    if issues:
        return _empty_diagnostic(
            observation, "invalid", issues, "Invalid input supports no observable-chain claim."
        )

    ledger_complete = set(ledger_ids) == set(requirements) and len(ledger_ids) == len(requirements)
    reconciliation_floor = max(
        [latest_change_sequence, *cited_preterminal_sequences],
        default=latest_change_sequence,
    )
    has_reconcile = any(
        event.get("stage") == "reconcile"
        and terminal_sequence is not None
        and isinstance(event.get("sequence"), int)
        and reconciliation_floor < int(event["sequence"]) < terminal_sequence
        for event in events
    )
    if terminal_state == "claimed_complete":
        terminal_consistent = bool(statuses) and all(status == "satisfied" for status in statuses)
    elif terminal_state == "claimed_incomplete":
        terminal_consistent = "unmet" in statuses and "blocked" not in statuses
    elif terminal_state == "claimed_blocked":
        terminal_consistent = "blocked" in statuses
    else:
        terminal_consistent = False

    facets = {
        "policy_bytes_bound": "satisfied",
        "ledger_materialized": "satisfied" if ledger_complete else "unsatisfied",
        "checks_evidenced": "satisfied" if ledger_complete and checks_valid else "unsatisfied",
        "terminal_reconciled": (
            "satisfied"
            if ledger_complete and checks_valid and has_reconcile and terminal_consistent
            else "unsatisfied"
        ),
    }
    state = (
        "observable_chain_complete"
        if all(value == "satisfied" for value in facets.values())
        else "observable_chain_incomplete"
    )
    return {
        "schema_version": DIAGNOSTIC_VERSION,
        "cell_id": root.get("cell_id"),
        "state": state,
        "facets": facets,
        "stage_vector": {
            **{
                stage: "observed"
                if any(event.get("stage") == stage for event in events)
                else "missing"
                for stage in _STAGES
            },
            "declare": "observed" if terminal else "missing",
        },
        "counts": {
            "requirements": len(requirements),
            "ledger_entries": len(ledger),
            "successful_preterminal_checks": len(successful_checks),
            "supported_blockers": len(supported_blockers),
            "unresolved_requirements": sum(status != "satisfied" for status in statuses),
        },
        "source_hashes": {
            "policy_sha256": observed_policy_bytes,
            "ledger_sha256": supplied_ledger,
            "terminal_sha256": terminal.get("sha256") if terminal else None,
            "reported_event_sha256": sorted(
                str(event.get("sha256")) for event in events if isinstance(event.get("sha256"), str)
            ),
        },
        "issues": [],
        "boundary": (
            "This classifies caller-provided normalized pilot facts. Event labels and event digests are reported declarations, not proof of real harness capture or causal mediation."
        ),
    }


def diagnose_cells(
    method_plan: Mapping[str, Any], observations: Sequence[Mapping[str, Any]], policy_bytes: bytes
) -> dict[str, Any]:
    """Return one deterministic report over normalized candidate fixtures."""

    diagnostics = [
        diagnose_policy_enactment(method_plan, item, policy_bytes) for item in observations
    ]
    report_issues: list[EngagementIssue] = []
    cell_ids = [item.get("cell_id") for item in observations]
    if not observations:
        _issue(
            report_issues,
            "CI10-R001",
            "observations",
            "must contain at least one normalized cell",
        )
    if len(cell_ids) != len(set(cell_ids)):
        _issue(
            report_issues,
            "CI10-R002",
            "observations.cell_id",
            "must not contain duplicate cell identities",
        )
    states = (
        "observable_chain_complete",
        "observable_chain_incomplete",
        "not_assessable",
        "invalid",
    )
    counts = {state: sum(item["state"] == state for item in diagnostics) for state in states}
    return {
        "schema_version": REPORT_VERSION,
        "status": "blocked" if counts["invalid"] or report_issues else "complete",
        "cell_count": len(diagnostics),
        "state_counts": counts,
        "diagnostics": diagnostics,
        "issues": [issue.as_dict() for issue in _sorted(report_issues)],
        "boundary": (
            "Synthetic normalized fixtures test classifier behavior only. They are not empirical evidence that a real agent enacted a policy or that the policy improved outcomes."
        ),
    }
