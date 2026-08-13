from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ael.prospective_study import OBSERVATIONS_SCHEMA_VERSION, load_json_object, sha256_path
from ael.systematic_debugging_shadow import decide_effect

ROOT = Path(__file__).resolve().parents[1]
FREEZE = (
    ROOT
    / "studies"
    / "agent-skills-season-1"
    / "screening"
    / "systematic-debugging-real-shadow.freeze.json"
)


def observation(entry: dict[str, object], *, accepted: bool) -> dict[str, object]:
    condition = entry["condition_id"]
    return {
        "observation_id": f"test:{entry['task_id']}:{condition}",
        "task_id": entry["task_id"],
        "stratum": "test",
        "condition_id": condition,
        "repeat_index": 1,
        "schedule_sequence": entry["sequence"],
        "status": "valid",
        "invalid_reasons": [],
        "skill_activated": condition == "S1",
        "critical_failure": False,
        "accepted": accepted,
    }


class DebuggingShadowDecisionTests(unittest.TestCase):
    def decide(
        self,
        accepted: dict[tuple[str, str], bool],
        changes: dict[tuple[str, str], dict[str, object]] | None = None,
    ) -> dict[str, object]:
        freeze = load_json_object(FREEZE)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            freeze_path = root / "freeze.json"
            freeze_path.write_bytes(FREEZE.read_bytes())
            observations = []
            for entry in freeze["schedule"]:
                item = observation(
                    entry, accepted=accepted[(entry["task_id"], entry["condition_id"])]
                )
                key = (entry["task_id"], entry["condition_id"])
                if changes and key in changes:
                    item.update(changes[key])
                observations.append(item)
            observations_path = root / "observations.json"
            observations_path.write_text(
                json.dumps(
                    {
                        "schema_version": OBSERVATIONS_SCHEMA_VERSION,
                        "freeze_sha256": sha256_path(freeze_path),
                        "observations": observations,
                    }
                ),
                encoding="utf-8",
            )
            return decide_effect(freeze_path, observations_path)

    @staticmethod
    def ties(value: bool = False) -> dict[tuple[str, str], bool]:
        return {
            (task, condition): value
            for task in ("D-S01", "D-S02", "D-S03", "D-S04")
            for condition in ("B0", "S1")
        }

    def test_two_favorable_tasks_route_only_their_stratum(self) -> None:
        accepted = self.ties(False)
        accepted[("D-S01", "S1")] = True
        accepted[("D-S02", "S1")] = True
        decision = self.decide(accepted)
        self.assertEqual("bounded_favorable_signal", decision["effect_outcome"])
        self.assertEqual(["cross-boundary-contract"], decision["eligible_strata"])
        self.assertEqual(2, decision["counts"]["favorable_pairs"])

    def test_two_unfavorable_pairs_reject_exact_treatment(self) -> None:
        accepted = self.ties(False)
        for task in ("D-S01", "D-S02"):
            accepted[(task, "B0")] = True
        decision = self.decide(accepted)
        self.assertEqual("treatment_harm_signal", decision["effect_outcome"])
        self.assertEqual([], decision["eligible_strata"])

    def test_mixed_or_no_headroom_stays_optional(self) -> None:
        decision = self.decide(self.ties(True))
        self.assertEqual("mixed_or_no_headroom", decision["effect_outcome"])

    def test_invalid_or_activation_failure_blocks_route(self) -> None:
        accepted = self.ties(False)
        decision = self.decide(
            accepted,
            {("D-S01", "B0"): {"status": "invalid", "invalid_reasons": ["test"]}},
        )
        self.assertEqual("invalid_manual_review", decision["effect_outcome"])
        decision = self.decide(
            accepted,
            {("D-S01", "S1"): {"skill_activated": False}},
        )
        self.assertEqual("treatment_activation_failure", decision["effect_outcome"])


if __name__ == "__main__":
    unittest.main()
