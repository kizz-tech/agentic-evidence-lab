from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from ael.pbt_pilot import execution_code_sha256, paired_counts
from ael.validation import sha256_path
from tools.run_pbt_v2 import STUDY_PROMPT

ROOT = Path(__file__).resolve().parents[1]
FREEZE = (
    ROOT
    / "studies"
    / "agent-skills-season-1"
    / "screening"
    / "property-based-testing-v2.freeze.json"
)


def observation(condition: str, accepted: bool) -> dict[str, object]:
    return {
        "task_id": "P-01",
        "repeat_index": 1,
        "condition_id": condition,
        "status": "valid",
        "skill_activated": condition == "S1",
        "hidden_acceptance": accepted,
        "critical_failure": False,
    }


class PbtPairTests(unittest.TestCase):
    def test_public_freeze_binds_current_study_code_and_prompt(self) -> None:
        bundle = json.loads(FREEZE.read_text(encoding="utf-8"))
        self.assertEqual(
            bundle["analysis_code_sha256"],
            sha256_path(ROOT / "tools" / "materialize_pbt_v2.py"),
        )
        self.assertEqual(
            bundle["decision_code_sha256"],
            sha256_path(ROOT / "src" / "ael" / "pbt_pilot.py"),
        )
        self.assertEqual(bundle["execution_code_sha256"], execution_code_sha256())
        self.assertEqual(
            bundle["runner_code_sha256"],
            sha256_path(ROOT / "tools" / "run_pbt_v2.py"),
        )
        self.assertEqual(
            bundle["prompt_sha256"],
            hashlib.sha256(STUDY_PROMPT.encode("utf-8")).hexdigest(),
        )

    def test_treatment_only_pass_is_favorable(self) -> None:
        counts = paired_counts([observation("B0", False), observation("S1", True)])
        self.assertEqual(1, counts["favorable_pairs"])
        self.assertEqual(0, counts["unfavorable_pairs"])

    def test_baseline_only_pass_is_unfavorable(self) -> None:
        counts = paired_counts([observation("B0", True), observation("S1", False)])
        self.assertEqual(0, counts["favorable_pairs"])
        self.assertEqual(1, counts["unfavorable_pairs"])

    def test_equal_passes_tie_without_headroom(self) -> None:
        counts = paired_counts([observation("B0", True), observation("S1", True)])
        self.assertEqual(1, counts["tied_pairs"])
        self.assertEqual(0, counts["baseline_hidden_failures"])

    def test_equal_failures_tie_with_headroom(self) -> None:
        counts = paired_counts([observation("B0", False), observation("S1", False)])
        self.assertEqual(1, counts["tied_pairs"])
        self.assertEqual(1, counts["baseline_hidden_failures"])


if __name__ == "__main__":
    unittest.main()
