from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from ael.sandbox import SandboxError
from ael.study_audit import audit_study_bundle

ROOT = Path(__file__).resolve().parents[1]
SEASON = ROOT / "studies" / "agent-skills-season-1"
FREEZE = SEASON / "screening" / "property-based-testing-v2.freeze.json"
RESULT = SEASON / "results" / "property-based-testing-v2"


class StudyAuditTests(unittest.TestCase):
    def copy_study(self, temporary: str) -> tuple[Path, Path]:
        root = Path(temporary)
        (root / "pyproject.toml").write_text("[project]\nname='audit-test'\n", encoding="utf-8")
        season = root / "studies" / "agent-skills-season-1"
        shutil.copytree(SEASON, season)
        return (
            season / "screening" / "property-based-testing-v2.freeze.json",
            season / "results" / "property-based-testing-v2",
        )

    def test_public_property_based_testing_bundle_passes(self) -> None:
        result = audit_study_bundle(FREEZE, RESULT, decision_adapter="pbt-v2")
        self.assertEqual("passed", result["status"])
        self.assertEqual(8, result["evidence"]["run_records"])
        self.assertEqual(88, result["evidence"]["measurements"])
        self.assertTrue(result["decision"]["public_counts_recomputed"])

    def test_git_proof_binds_freeze_and_result_order(self) -> None:
        result = audit_study_bundle(
            FREEZE, RESULT, require_git_proof=True, decision_adapter="pbt-v2"
        )
        self.assertTrue(result["preregistration"]["git_verified"])
        self.assertTrue(result["preregistration"]["freeze_bytes_verified"])
        self.assertTrue(result["preregistration"]["terminal_decision_absent_at_freeze"])
        self.assertTrue(result["preregistration"]["terminal_decision_committed_after_freeze"])

    def test_tampered_decision_alias_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            freeze, result = self.copy_study(temporary)
            decision_path = result / "decision.json"
            decision = json.loads(decision_path.read_text(encoding="utf-8"))
            decision["outcome"] = "continue"
            decision_path.write_text(json.dumps(decision), encoding="utf-8")
            with self.assertRaisesRegex(SandboxError, "terminal-decision alias"):
                audit_study_bundle(freeze, result)

    def test_pbt_adapter_rejects_outcome_not_derived_from_counts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            freeze, result = self.copy_study(temporary)
            decision_path = result / "decision.json"
            decision = json.loads(decision_path.read_text(encoding="utf-8"))
            decision["outcome"] = "continue"
            decision_path.write_text(json.dumps(decision), encoding="utf-8")
            with self.assertRaisesRegex(SandboxError, "outcome does not follow"):
                audit_study_bundle(freeze, result, decision_adapter="pbt-v2")

    def test_tampered_public_measurement_counts_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            freeze, result = self.copy_study(temporary)
            path = result / "measurement-set.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            measurement = next(
                item
                for item in data["measurements"]
                if item["metric"] == "hidden_acceptance" and item["condition_id"] == "S1"
            )
            measurement["value"] = not measurement["value"]
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(SandboxError, "reference hash does not match"):
                audit_study_bundle(freeze, result)

    def test_missing_run_fails_exact_schedule(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            freeze, result = self.copy_study(temporary)
            next((result / "runs").glob("*.json")).unlink()
            with self.assertRaisesRegex(SandboxError, "Contract v0"):
                audit_study_bundle(freeze, result)

    def test_structural_audit_does_not_claim_semantic_recomputation(self) -> None:
        result = audit_study_bundle(FREEZE, RESULT)
        self.assertFalse(result["decision"]["public_counts_recomputed"])
        self.assertIsNone(result["decision"]["adapter"])


if __name__ == "__main__":
    unittest.main()
