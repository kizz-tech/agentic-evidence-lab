from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from ael.decision_utility import (
    DecisionUtilityError,
    build_schedule,
    build_views,
    score_responses,
    validate_case_pack,
    validate_protocol,
    validate_schedule,
)

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "studies/decision-utility-v1/calibration"


def _load(name: str) -> dict:
    return json.loads((STUDY / name).read_text(encoding="utf-8"))


class DecisionUtilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.protocol = _load("protocol.json")
        self.cases = _load("cases.json")
        self.participants = _load("participants.json")["participant_ids"]

    def test_protocol_and_public_calibration_pack_are_closed(self) -> None:
        frozen = validate_protocol(self.protocol)
        pack = validate_case_pack(frozen, self.cases)
        self.assertEqual("pending_pilot", frozen["sample_size"]["status"])
        self.assertEqual(6, len(pack["cases"]))
        self.assertEqual(
            {"supported", "contradicted"},
            {case["recommendation_state"] for case in pack["cases"]},
        )

        unknown = copy.deepcopy(self.protocol)
        unknown["invented"] = True
        with self.assertRaisesRegex(DecisionUtilityError, "unknown_keys"):
            validate_protocol(unknown)

        retrospective_target = copy.deepcopy(self.protocol)
        retrospective_target["sample_size"]["target_participants"] = 30
        with self.assertRaisesRegex(DecisionUtilityError, "pending_pilot"):
            validate_protocol(retrospective_target)

    def test_views_are_evidence_equivalent_and_hide_the_answer_key(self) -> None:
        views = build_views(self.protocol, self.cases)
        self.assertEqual(18, len(views))
        for case in self.cases["cases"]:
            case_views = [view for view in views if view["case_id"] == case["case_id"]]
            self.assertEqual(3, len(case_views))
            self.assertEqual(1, len({view["evidence_fingerprint"] for view in case_views}))
            serialized = json.dumps(case_views, sort_keys=True)
            self.assertNotIn("correct_action", serialized)
            self.assertNotIn(case["rationale"], serialized)

    def test_schedule_is_balanced_and_never_repeats_a_case(self) -> None:
        schedule = build_schedule(self.protocol, self.cases, self.participants)
        self.assertEqual(18, len(schedule["cells"]))
        for participant_id in self.participants:
            cells = [cell for cell in schedule["cells"] if cell["participant_id"] == participant_id]
            self.assertEqual(6, len({cell["case_id"] for cell in cells}))
            self.assertEqual(
                {"A0": 2, "A1": 2, "A2": 2},
                {arm: sum(cell["arm_id"] == arm for cell in cells) for arm in ("A0", "A1", "A2")},
            )
        for case in self.cases["cases"]:
            cells = [cell for cell in schedule["cells"] if cell["case_id"] == case["case_id"]]
            self.assertEqual({"A0", "A1", "A2"}, {cell["arm_id"] for cell in cells})

        tampered = copy.deepcopy(schedule)
        tampered["cells"][0]["arm_id"] = tampered["cells"][1]["arm_id"]
        with self.assertRaisesRegex(DecisionUtilityError, "schedule_balance|case_arm_balance"):
            validate_schedule(self.protocol, self.cases, tampered)

    def test_scoring_retains_weighted_unweighted_and_guardrail_outcomes(self) -> None:
        schedule = build_schedule(self.protocol, self.cases, self.participants)
        cases = {case["case_id"]: case for case in self.cases["cases"]}
        responses = []
        critical_key: tuple[str, str] | None = None
        for cell in schedule["cells"]:
            case = cases[cell["case_id"]]
            action = case["correct_action"]
            if case["critical"] and critical_key is None:
                action = "adopt_exact"
                critical_key = (cell["participant_id"], cell["case_id"])
            responses.append(
                {
                    "participant_id": cell["participant_id"],
                    "case_id": cell["case_id"],
                    "arm_id": cell["arm_id"],
                    "action": action,
                    "confidence_ppm": 900000,
                    "duration_ms": 60000,
                    "workload": 2,
                }
            )
        scored = score_responses(self.protocol, self.cases, schedule, responses)
        self.assertEqual(18, scored["observed_cells"])
        self.assertEqual(0, scored["missing_cells"])
        self.assertEqual(1, sum(arm["errors"] for arm in scored["by_arm"].values()))
        self.assertEqual(1, sum(arm["critical_misses"] for arm in scored["by_arm"].values()))
        self.assertEqual(
            27,
            sum(arm["weighted_error_numerator"] for arm in scored["by_arm"].values()),
        )
        self.assertEqual(
            0,
            sum(arm["burden_cap_breaches"] for arm in scored["by_arm"].values()),
        )

        duplicate = responses + [responses[0]]
        with self.assertRaisesRegex(DecisionUtilityError, "duplicate_response"):
            score_responses(self.protocol, self.cases, schedule, duplicate)


if __name__ == "__main__":
    unittest.main()
