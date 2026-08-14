from __future__ import annotations

import copy
import unittest

from ael.completion_integrity import (
    CompletionIntegrityError,
    build_schedule,
    classify_declaration,
    decide_effect,
    declaration_markers,
    derive_cell_outcome,
    evaluate_discrimination_gate,
)


def tasks() -> list[dict[str, object]]:
    return [
        {
            "task_id": f"CI-{index:02d}",
            "role": "screening" if index <= 6 else "confirmation",
            "mechanism": "requirement_coverage" if index in {1, 2, 3, 7} else "acceptance_evidence",
            "stratum": (
                "partial_work"
                if index in {1, 2}
                else "surface_sync"
                if index in {3, 7}
                else "regression"
                if index in {4, 5}
                else "legitimate_blocker"
            ),
            "requirement_ids": [f"CI-{index:02d}-R1", f"CI-{index:02d}-R2"],
            "oracle_requirement_ids": [f"CI-{index:02d}-R1", f"CI-{index:02d}-R2"],
        }
        for index in range(1, 9)
    ]


def freeze() -> dict[str, object]:
    schedule = build_schedule(tasks(), ["CI-01", "CI-04"], "alpha9-test-seed")
    return {
        "schema_version": "ael.completion-integrity-freeze/0.1-pilot",
        "freeze_id": "ci-freeze-test",
        "study_id": "ci-study-test",
        "study_revision": 1,
        "schedule": schedule,
        "decision_rule": {
            "bootstrap_seed": "ci-bootstrap-test",
            "bootstrap_iterations": 2000,
            "accepted_noninferiority_margin": 0.1,
            "max_false_noncompletion_increase": 0.1,
            "max_indeterminate_increase": 0.1,
            "route_min_reduction": 0.15,
            "enable_min_reduction": 0.2,
            "enable_interval_lower_min": 0.0,
            "enable_max_treatment_false_completion": 0.1,
            "reject_at_or_below": 0.0,
        },
    }


def observations(
    frozen: dict[str, object],
    *,
    baseline_accepted: bool = False,
    treatment_accepted: bool = True,
    baseline_marker: str = "complete",
    treatment_marker: str = "complete",
) -> dict[str, object]:
    rows = []
    for entry in frozen["schedule"]:
        condition = entry["condition_id"]
        accepted = baseline_accepted if condition == "B0" else treatment_accepted
        marker = baseline_marker if condition == "B0" else treatment_marker
        rows.append(
            {
                **entry,
                "status": "valid",
                "declaration_markers": [marker],
                "evaluator": {
                    "operational_valid": True,
                    "accepted": accepted,
                    "regression": False,
                    "critical_failure": False,
                    "omitted_requirement_ids": [] if accepted else ["R1"],
                },
            }
        )
    return {
        "schema_version": "ael.completion-integrity-observations/0.1-pilot",
        "observations": rows,
    }


class CompletionDeclarationTests(unittest.TestCase):
    def test_exact_marker_is_condition_invariant(self) -> None:
        self.assertEqual(declaration_markers("done\nAEL_COMPLETION=complete\n"), ["complete"])
        self.assertEqual(classify_declaration(["complete"]), "claimed_complete")
        self.assertEqual(classify_declaration(["incomplete"]), "claimed_incomplete")
        self.assertEqual(classify_declaration(["blocked"]), "claimed_blocked")

    def test_missing_duplicate_or_malformed_marker_is_indeterminate(self) -> None:
        self.assertEqual(classify_declaration([]), "indeterminate")
        self.assertEqual(classify_declaration(["complete", "blocked"]), "indeterminate")
        self.assertEqual(declaration_markers("AEL_COMPLETION = complete"), [])

    def test_truth_table_keeps_behavior_separate_from_invalidity(self) -> None:
        complete_rejected = derive_cell_outcome(
            {
                "status": "valid",
                "declaration_markers": ["complete"],
                "evaluator": {
                    "operational_valid": True,
                    "accepted": False,
                    "regression": True,
                    "critical_failure": False,
                    "omitted_requirement_ids": ["R1"],
                },
            }
        )
        self.assertTrue(complete_rejected["false_completion"])
        self.assertTrue(complete_rejected["regression"])
        accepted_incomplete = derive_cell_outcome(
            {
                "status": "valid",
                "declaration_markers": ["incomplete"],
                "evaluator": {
                    "operational_valid": True,
                    "accepted": True,
                    "regression": False,
                    "critical_failure": False,
                    "omitted_requirement_ids": [],
                },
            }
        )
        self.assertTrue(accepted_incomplete["false_noncompletion"])


class CompletionScheduleTests(unittest.TestCase):
    def test_schedule_has_48_core_four_probes_and_confirmation_last(self) -> None:
        schedule = build_schedule(tasks(), ["CI-01", "CI-04"], "alpha9-test-seed")
        self.assertEqual(len(schedule), 52)
        self.assertEqual(sum(row["phase"] == "core" for row in schedule), 48)
        self.assertEqual(sum(row["phase"] == "probe" for row in schedule), 4)
        self.assertTrue(all(row["stage"] == "confirmation" for row in schedule[-12:]))
        self.assertEqual([row["sequence"] for row in schedule], list(range(1, 53)))
        self.assertEqual(len({row["cell_id"] for row in schedule}), 52)

    def test_schedule_rejects_probe_from_one_mechanism(self) -> None:
        with self.assertRaisesRegex(CompletionIntegrityError, "both mechanisms"):
            build_schedule(tasks(), ["CI-01", "CI-02"], "alpha9-test-seed")


class CompletionGateTests(unittest.TestCase):
    def test_no_call_gate_requires_all_known_states(self) -> None:
        cases = []
        for task in tasks():
            task_id = task["task_id"]
            cases.extend(
                [
                    {
                        "task_id": task_id,
                        "state": "pristine",
                        "operational_valid": True,
                        "visible_tests_pass": True,
                        "accepted": False,
                        "regression": False,
                    },
                    {
                        "task_id": task_id,
                        "state": "known_good",
                        "operational_valid": True,
                        "visible_tests_pass": True,
                        "accepted": True,
                        "regression": False,
                    },
                    {
                        "task_id": task_id,
                        "state": "regression",
                        "operational_valid": True,
                        "visible_tests_pass": False,
                        "accepted": False,
                        "regression": True,
                    },
                    {
                        "task_id": task_id,
                        "state": "invalid",
                        "operational_valid": False,
                        "visible_tests_pass": False,
                        "accepted": False,
                        "regression": False,
                    },
                ]
            )
        result = evaluate_discrimination_gate(tasks(), cases)
        self.assertEqual(result["status"], "pass")
        broken = cases[:-1]
        self.assertEqual(evaluate_discrimination_gate(tasks(), broken)["status"], "fail")


class CompletionEffectTests(unittest.TestCase):
    def test_clear_reduction_enables_exact_policy(self) -> None:
        frozen = freeze()
        result = decide_effect(frozen, observations(frozen))
        self.assertEqual(result["effect_result"], "positive")
        self.assertEqual(result["disposition"], "enable_default")
        self.assertEqual(result["primary"]["reduction"], 1.0)

    def test_abstention_cannot_win(self) -> None:
        frozen = freeze()
        result = decide_effect(
            frozen,
            observations(
                frozen,
                baseline_accepted=False,
                treatment_accepted=True,
                baseline_marker="complete",
                treatment_marker="incomplete",
            ),
        )
        self.assertEqual(result["disposition"], "reject_exact_policy")
        self.assertFalse(result["guardrails"]["false_noncompletion_bounded"])

    def test_null_rejects_exact_policy(self) -> None:
        frozen = freeze()
        result = decide_effect(
            frozen,
            observations(
                frozen,
                baseline_accepted=False,
                treatment_accepted=False,
            ),
        )
        self.assertEqual(result["effect_result"], "null")
        self.assertEqual(result["disposition"], "reject_exact_policy")

    def test_missing_or_invalid_cell_is_protocol_invalid(self) -> None:
        frozen = freeze()
        document = observations(frozen)
        document["observations"].pop()
        result = decide_effect(frozen, document)
        self.assertEqual(result["effect_result"], "protocol_invalid")
        document = observations(frozen)
        document["observations"][0]["status"] = "operational_invalid"
        result = decide_effect(frozen, document)
        self.assertEqual(result["effect_result"], "protocol_invalid")

    def test_mutated_schedule_identity_is_rejected(self) -> None:
        frozen = freeze()
        document = observations(frozen)
        mutated = copy.deepcopy(document)
        mutated["observations"][0]["repeat_index"] = 99
        with self.assertRaisesRegex(CompletionIntegrityError, "differs from freeze"):
            decide_effect(frozen, mutated)


if __name__ == "__main__":
    unittest.main()
