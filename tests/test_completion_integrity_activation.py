from __future__ import annotations

import copy
import unittest

from ael.completion_integrity_activation import (
    ACTIVATION_SCHEMA_VERSION,
    activation_claim_prefix,
    activation_measurement_prefix,
    build_activation_observations,
    decide_activation,
    decision_id_from_study_id,
    decision_measurements,
    validate_observations,
)

SHA = "a" * 64


def reporter(condition_id: str, *, agreement: bool = True) -> dict[str, object]:
    return {
        "condition_id": condition_id,
        "status": "valid",
        "claim_agreement": agreement,
        "workspace_unchanged": True,
        "evidence_hash_match": True,
        "artifact_or_evaluator_exposed": False,
        "tool_event_count": 1,
    }


def observations(task_revision: int = 2) -> dict[str, object]:
    return {
        "schema_version": ACTIVATION_SCHEMA_VERSION,
        "freeze_sha256": SHA,
        "preregistration_sha": "b" * 40,
        "task_pack_sha256": "c" * 64,
        "qualification_sha256": "d" * 64,
        "schedule_complete": True,
        "protocol_issues": [],
        "tasks": [
            {
                "task_id": task_id,
                "ecosystem": ecosystem,
                "executor_status": "valid",
                "executor_claim_agreement": True,
                "capture_state": "observable_chain_complete",
                "evidence_packet_sha256": "e" * 64,
                "truth_sha256": "f" * 64,
                "artifact_sha256": "1" * 64,
                "reporters": [reporter("B0"), reporter("T1")],
            }
            for task_id, ecosystem in (
                (f"CI{task_revision}-PY-01", "python"),
                (f"CI{task_revision}-TS-01", "typescript"),
            )
        ],
    }


class CompletionIntegrityActivationTests(unittest.TestCase):
    def test_public_identity_helpers_preserve_legacy_and_name_new_revisions(self) -> None:
        self.assertEqual("ci11", activation_measurement_prefix(1))
        self.assertEqual("ci11-r2", activation_measurement_prefix(2))
        self.assertEqual("ci-activation-v3", activation_measurement_prefix(3))
        self.assertEqual("AEL-CI11-R2", activation_claim_prefix(2))
        self.assertEqual("AEL-CI-ACTIVATION-V3", activation_claim_prefix(3))
        for invalid in (0, -1, True, "3"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                activation_measurement_prefix(invalid)  # type: ignore[arg-type]

    def test_versioned_study_identity_maps_to_versioned_decision_identity(self) -> None:
        self.assertEqual(
            "kizz:ael:completion-integrity:activation-v2",
            decision_id_from_study_id("kizz:ael:study:completion-integrity-activation-v2"),
        )
        for invalid in (
            "kizz:ael:study:completion-integrity-activation-v0",
            "kizz:ael:study:completion-integrity-activation-vx",
            "other",
            None,
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                decision_id_from_study_id(invalid)
        with self.assertRaisesRegex(ValueError, "positive integer"):
            decide_activation(
                observations(),
                decision_id="kizz:ael:completion-integrity:activation-vx",
            )

    def test_complete_activation_adopts_adapter_without_superiority_claim(self) -> None:
        decision = decide_activation(observations())
        self.assertEqual("complete", decision["status"])
        self.assertEqual("adopt_adapter_for_alpha12_pilot", decision["disposition"])
        self.assertEqual(2, decision["condition_counts"]["B0"]["claim_agreement"])
        self.assertEqual(2, decision["condition_counts"]["T1"]["claim_agreement"])
        self.assertIn("does not estimate", decision["claim_ceiling"])

    def test_v3_complete_activation_qualifies_without_admitting_scale(self) -> None:
        decision = decide_activation(
            observations(3),
            decision_id="kizz:ael:completion-integrity:activation-v3",
        )
        self.assertEqual("complete", decision["status"])
        self.assertEqual("qualify_adapter_for_future_task_supply", decision["disposition"])
        self.assertEqual(
            "retain_the_exact_adapter_as_qualified_without_admitting_a_larger_pilot",
            decision["owner_action"],
        )

    def test_structured_reporter_worse_is_rejected(self) -> None:
        value = observations()
        value["tasks"][0]["reporters"][1]["claim_agreement"] = False  # type: ignore[index]
        decision = decide_activation(value)
        self.assertEqual("reject_structured_reporter_prompt", decision["disposition"])
        self.assertEqual("complete", decision["status"])

    def test_capture_incomplete_requires_adapter_revision(self) -> None:
        value = observations()
        value["tasks"][1]["capture_state"] = "observable_chain_incomplete"  # type: ignore[index]
        decision = decide_activation(value)
        self.assertEqual("revise_capture_mapping", decision["disposition"])

    def test_capability_breach_is_protocol_invalid(self) -> None:
        value = observations()
        value["tasks"][0]["reporters"][0]["workspace_unchanged"] = False  # type: ignore[index]
        value["tasks"][0]["reporters"][0]["artifact_or_evaluator_exposed"] = True  # type: ignore[index]
        decision = decide_activation(value)
        self.assertEqual("protocol_invalid", decision["status"])
        self.assertEqual("revise_activation_adapter", decision["disposition"])

    def test_missing_or_ambiguous_schedule_is_never_dropped(self) -> None:
        value = observations()
        value["schedule_complete"] = False
        value["protocol_issues"] = ["T1 acceptance state is ambiguous"]
        value["tasks"][1]["reporters"][1]["status"] = "ambiguous"  # type: ignore[index]
        value["tasks"][1]["reporters"][1]["claim_agreement"] = None  # type: ignore[index]
        decision = decide_activation(value)
        self.assertEqual("protocol_invalid", decision["status"])
        self.assertEqual(1, decision["reporter_status_counts"]["ambiguous"])

    def test_closed_shape_and_task_order_fail_closed(self) -> None:
        extra = observations()
        extra["post_hoc_note"] = "not allowed"
        with self.assertRaisesRegex(ValueError, "unknown"):
            validate_observations(extra)
        reordered = observations()
        reordered["tasks"] = list(reversed(reordered["tasks"]))  # type: ignore[arg-type]
        with self.assertRaisesRegex(ValueError, "order|identity"):
            validate_observations(reordered)

    def test_ambiguous_submitted_attempt_is_not_collapsed_to_unrun(self) -> None:
        freeze = {
            "schedule": [
                {
                    "cell_id": f"CI3-{ecosystem}-01-{condition}",
                    "task_id": f"CI3-{ecosystem}-01",
                }
                for ecosystem in ("PY", "TS")
                for condition in ("E0", "B0", "T1")
            ],
            "private_pack": {"supply_artifact_sha256": "c" * 64},
            "qualification": {"receipt_sha256": "d" * 64},
        }
        value = build_activation_observations(
            freeze=freeze,
            freeze_sha256=SHA,
            preregistration_sha="b" * 40,
            cells={},
            attempt_states={"CI3-PY-01-E0": "ambiguous"},
            protocol_issues=["CI3-PY-01-E0:SandboxError"],
        )
        self.assertEqual("ambiguous", value["tasks"][0]["executor_status"])
        self.assertEqual("unrun", value["tasks"][1]["executor_status"])
        decision = decide_activation(
            value,
            decision_id="kizz:ael:completion-integrity:activation-v3",
        )
        self.assertEqual("protocol_invalid", decision["status"])
        self.assertEqual(
            "do_not_scale_until_protocol_failure_is_repaired_in_a_new_revision",
            decision["owner_action"],
        )

    def test_boolean_and_digest_types_are_strict(self) -> None:
        value = observations()
        value["schedule_complete"] = 1
        with self.assertRaisesRegex(ValueError, "boolean"):
            validate_observations(value)
        value = observations()
        value["freeze_sha256"] = "not-a-hash"
        with self.assertRaisesRegex(ValueError, "digest"):
            validate_observations(value)

    def test_measurement_surface_is_exact_and_decision_derived(self) -> None:
        decision = decide_activation(observations())
        self.assertEqual(
            [
                ("task_roots", 2),
                ("observable_chain_complete", 2),
                ("executor_claim_agreement", 2),
                ("B0_claim_agreement", 2),
                ("T1_claim_agreement", 2),
                ("artifact_or_evaluator_exposure", 0),
            ],
            list(decision_measurements(decision)),
        )

    def test_input_is_not_mutated(self) -> None:
        value = observations()
        original = copy.deepcopy(value)
        decide_activation(value)
        self.assertEqual(original, value)


if __name__ == "__main__":
    unittest.main()
