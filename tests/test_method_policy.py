from __future__ import annotations

import unittest

from ael.method_policy import (
    CLAIMS_BY_EVIDENCE_STATE,
    ClaimSupportContext,
    EvidenceBinding,
    MethodPolicyError,
    validate_claim_support,
)


class MethodPolicyTests(unittest.TestCase):
    def _context(self, **overrides: object) -> ClaimSupportContext:
        values: dict[str, object] = {
            "evidence_state": "controlled_effect_observed",
            "comparison_mode": "controlled_factor",
            "nonbaseline_intervention_classes": frozenset({"skill"}),
            "independence_label": "maintainer_evaluated",
            "evidence_by_ref": {
                "outcome:m1": EvidenceBinding(kind="outcome"),
                "transfer:m1": EvidenceBinding(
                    kind="outcome", task_pack_roles=frozenset({"transfer"})
                ),
            },
        }
        values.update(overrides)
        return ClaimSupportContext(**values)  # type: ignore[arg-type]

    def test_evidence_state_relation_is_exact_and_not_ordinal(self) -> None:
        expected = {
            "structurally_valid": {"artifact"},
            "runtime_conformant": {"artifact", "workflow"},
            "controlled_effect_observed": {
                "artifact",
                "workflow",
                "operational_stack",
                "factor_causal",
                "model_only",
            },
            "effect_reproduced": {
                "artifact",
                "workflow",
                "operational_stack",
                "factor_causal",
                "model_only",
            },
            "downstream_outcome_observed": {"artifact", "workflow", "outcome"},
            "transferred": {"artifact", "workflow", "transfer"},
            "externally_decision_changing": {"artifact", "workflow"},
            "paid_repeated_use": {"artifact", "workflow"},
            "independently_outcome_verified": {"artifact", "workflow", "outcome"},
        }
        self.assertEqual(
            expected, {key: set(value) for key, value in CLAIMS_BY_EVIDENCE_STATE.items()}
        )
        with self.assertRaises(TypeError):
            CLAIMS_BY_EVIDENCE_STATE["paid_repeated_use"] = frozenset({"outcome"})  # type: ignore[index]

    def test_commercial_or_external_state_does_not_authorize_transfer_or_outcome(self) -> None:
        for state, claim_level in (
            ("externally_decision_changing", "transfer"),
            ("paid_repeated_use", "outcome"),
            ("downstream_outcome_observed", "factor_causal"),
        ):
            with (
                self.subTest(state=state, claim_level=claim_level),
                self.assertRaisesRegex(MethodPolicyError, "requires its own support predicate"),
            ):
                validate_claim_support(
                    claim_id="C1",
                    claim_level=claim_level,
                    evidence_refs=["outcome:m1"],
                    context=self._context(evidence_state=state),
                )

    def test_causal_claim_requires_claim_local_measurement_binding(self) -> None:
        with self.assertRaisesRegex(MethodPolicyError, "claim-local Measurement Set reference"):
            validate_claim_support(
                claim_id="C1",
                claim_level="factor_causal",
                evidence_refs=["unresolved-sidecar.json"],
                context=self._context(),
            )
        validate_claim_support(
            claim_id="C1",
            claim_level="factor_causal",
            evidence_refs=["outcome:m1"],
            context=self._context(),
        )

        with self.assertRaisesRegex(MethodPolicyError, "claim-local Measurement Set reference"):
            validate_claim_support(
                claim_id="C1",
                claim_level="factor_causal",
                evidence_refs=["sidecar.json"],
                context=self._context(
                    evidence_by_ref={
                        "sidecar.json": EvidenceBinding(kind="artifact", source="public_sidecar")
                    }
                ),
            )

    def test_artifact_and_workflow_claims_require_one_public_binding(self) -> None:
        for claim_level, state in (
            ("artifact", "structurally_valid"),
            ("workflow", "runtime_conformant"),
        ):
            with (
                self.subTest(claim_level=claim_level),
                self.assertRaisesRegex(MethodPolicyError, "claim-local public evidence binding"),
            ):
                validate_claim_support(
                    claim_id="C1",
                    claim_level=claim_level,
                    evidence_refs=["opaque"],
                    context=self._context(evidence_state=state, evidence_by_ref={}),
                )

    def test_model_only_and_operational_stack_require_matching_design(self) -> None:
        with self.assertRaisesRegex(MethodPolicyError, "model-only non-baseline"):
            validate_claim_support(
                claim_id="C1",
                claim_level="model_only",
                evidence_refs=["outcome:m1"],
                context=self._context(
                    nonbaseline_intervention_classes=frozenset({"model", "prompt"})
                ),
            )
        with self.assertRaisesRegex(MethodPolicyError, "operational-stack comparison"):
            validate_claim_support(
                claim_id="C2",
                claim_level="operational_stack",
                evidence_refs=["outcome:m1"],
                context=self._context(),
            )

    def test_transfer_requires_claim_local_measurement_on_transfer_pack(self) -> None:
        context = self._context(evidence_state="transferred")
        with self.assertRaisesRegex(MethodPolicyError, "bound to a transfer task pack"):
            validate_claim_support(
                claim_id="C1",
                claim_level="transfer",
                evidence_refs=["outcome:m1"],
                context=context,
            )
        validate_claim_support(
            claim_id="C1",
            claim_level="transfer",
            evidence_refs=["transfer:m1"],
            context=context,
        )

    def test_outcome_requires_claim_local_outcome_measurement(self) -> None:
        context = self._context(
            evidence_state="downstream_outcome_observed",
            evidence_by_ref={"cost:m1": EvidenceBinding(kind="cost")},
        )
        with self.assertRaisesRegex(MethodPolicyError, "claim-local outcome measurement"):
            validate_claim_support(
                claim_id="C1",
                claim_level="outcome",
                evidence_refs=["cost:m1"],
                context=context,
            )

    def test_independent_outcome_state_requires_independent_ownership(self) -> None:
        with self.assertRaisesRegex(MethodPolicyError, "independence is maintainer_evaluated"):
            validate_claim_support(
                claim_id="C1",
                claim_level="outcome",
                evidence_refs=["outcome:m1"],
                context=self._context(evidence_state="independently_outcome_verified"),
            )


if __name__ == "__main__":
    unittest.main()
