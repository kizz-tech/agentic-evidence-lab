"""Pure claim-admission policy for public AEL result projections.

Contract v0 records evidence states and evaluated claims, but it deliberately
does not define a total order between heterogeneous predicates.  This module
keeps the publication rule explicit and independently testable: a claim must
be admitted by the receipt state, the comparison design, and evidence
references bound to that exact claim.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType


class MethodPolicyError(ValueError):
    """Raised when a selected claim exceeds its bound support."""


@dataclass(frozen=True)
class EvidenceBinding:
    """The public graph facts resolved for one claim evidence reference."""

    kind: str
    source: str = "measurement"
    task_pack_roles: frozenset[str] = frozenset()


@dataclass(frozen=True)
class ClaimSupportContext:
    """Study-level predicates available to the claim-admission policy."""

    evidence_state: str
    comparison_mode: str
    nonbaseline_intervention_classes: frozenset[str]
    independence_label: str
    evidence_by_ref: Mapping[str, EvidenceBinding]


# This is intentionally a relation, not a rank.  A state omitted from a claim
# class cannot authorize that class even if its name sounds operationally later
# or commercially stronger.
CLAIMS_BY_EVIDENCE_STATE: Mapping[str, frozenset[str]] = MappingProxyType(
    {
        "structurally_valid": frozenset({"artifact"}),
        "runtime_conformant": frozenset({"artifact", "workflow"}),
        "controlled_effect_observed": frozenset(
            {"artifact", "workflow", "operational_stack", "factor_causal", "model_only"}
        ),
        "effect_reproduced": frozenset(
            {"artifact", "workflow", "operational_stack", "factor_causal", "model_only"}
        ),
        "downstream_outcome_observed": frozenset({"artifact", "workflow", "outcome"}),
        "transferred": frozenset({"artifact", "workflow", "transfer"}),
        "externally_decision_changing": frozenset({"artifact", "workflow"}),
        "paid_repeated_use": frozenset({"artifact", "workflow"}),
        "independently_outcome_verified": frozenset({"artifact", "workflow", "outcome"}),
    }
)

CLAIM_LEVELS = frozenset(
    {
        "artifact",
        "workflow",
        "operational_stack",
        "factor_causal",
        "model_only",
        "transfer",
        "outcome",
    }
)

_MEASUREMENT_BOUND_CLAIMS = frozenset(
    {"factor_causal", "model_only", "operational_stack", "transfer", "outcome"}
)


def validate_claim_support(
    *,
    claim_id: str,
    claim_level: str,
    evidence_refs: Sequence[str],
    context: ClaimSupportContext,
) -> None:
    """Fail unless one exact selected claim is admitted by all predicates."""

    if claim_level not in CLAIM_LEVELS:
        raise MethodPolicyError(f"claim {claim_id} has unknown claim class {claim_level}")

    allowed_claims = CLAIMS_BY_EVIDENCE_STATE.get(context.evidence_state)
    if allowed_claims is None:
        raise MethodPolicyError(f"unknown receipt evidence state {context.evidence_state}")
    if claim_level not in allowed_claims:
        raise MethodPolicyError(
            f"claim {claim_id} is not admitted by receipt evidence state "
            f"{context.evidence_state}: {claim_level} requires its own support predicate"
        )

    if (
        context.evidence_state == "independently_outcome_verified"
        and context.independence_label != "independently_verified"
    ):
        raise MethodPolicyError(
            f"claim {claim_id} uses independently verified outcome evidence but "
            f"independence is {context.independence_label}"
        )

    if claim_level in {"factor_causal", "model_only"} and (
        context.comparison_mode != "controlled_factor"
    ):
        raise MethodPolicyError(f"claim {claim_id} requires a controlled-factor comparison")
    if claim_level == "model_only" and context.nonbaseline_intervention_classes != frozenset(
        {"model"}
    ):
        observed = ", ".join(sorted(context.nonbaseline_intervention_classes)) or "none"
        raise MethodPolicyError(
            f"claim {claim_id} requires model-only non-baseline intervention classes; "
            f"observed {observed}"
        )
    if claim_level == "operational_stack" and context.comparison_mode != "operational_stack":
        raise MethodPolicyError(f"claim {claim_id} requires an operational-stack comparison")

    bindings = [
        context.evidence_by_ref[ref] for ref in evidence_refs if ref in context.evidence_by_ref
    ]
    measurement_bindings = [binding for binding in bindings if binding.source == "measurement"]
    if claim_level in _MEASUREMENT_BOUND_CLAIMS and not measurement_bindings:
        raise MethodPolicyError(
            f"claim {claim_id} requires at least one claim-local Measurement Set reference"
        )
    if not bindings:
        raise MethodPolicyError(
            f"claim {claim_id} requires at least one claim-local public evidence binding"
        )
    if claim_level == "transfer" and not any(
        "transfer" in binding.task_pack_roles for binding in measurement_bindings
    ):
        raise MethodPolicyError(
            f"claim {claim_id} requires a claim-local measurement bound to a transfer task pack"
        )
    if claim_level == "outcome" and not any(
        binding.kind == "outcome" for binding in measurement_bindings
    ):
        raise MethodPolicyError(
            f"claim {claim_id} requires a claim-local outcome measurement reference"
        )
