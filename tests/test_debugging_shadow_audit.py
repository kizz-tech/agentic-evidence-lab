from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from ael.debugging_shadow_audit import audit_debugging_shadow_bundle
from ael.sandbox import SandboxError

ROOT = Path(__file__).resolve().parents[1]
FREEZE_RELATIVE = Path(
    "studies/agent-skills-season-1/screening/systematic-debugging-real-shadow.freeze.json"
)
RESULT_RELATIVE = Path("studies/agent-skills-season-1/results/systematic-debugging-real-shadow-v1")


class DebuggingShadowAuditTests(unittest.TestCase):
    def _copy_public_tree(self, temporary: str) -> Path:
        target = Path(temporary)
        shutil.copy2(ROOT / "pyproject.toml", target / "pyproject.toml")
        season_target = target / "studies" / "agent-skills-season-1"
        season_target.parent.mkdir(parents=True)
        shutil.copytree(ROOT / "studies" / "agent-skills-season-1", season_target)
        tool_target = target / "tools"
        tool_target.mkdir()
        shutil.copy2(
            ROOT / "tools" / "repair_systematic_debugging_shadow_projection.py",
            tool_target / "repair_systematic_debugging_shadow_projection.py",
        )
        return target

    def test_current_public_bundle_recomputes_effect_and_lifecycle(self) -> None:
        summary = audit_debugging_shadow_bundle(ROOT / FREEZE_RELATIVE, ROOT / RESULT_RELATIVE)
        self.assertEqual("passed", summary["status"])
        self.assertEqual("treatment_critical_failure", summary["decision"]["outcome"])
        self.assertEqual(8, summary["evidence"]["run_records"])
        self.assertEqual(80, summary["evidence"]["measurements"])
        self.assertTrue(summary["evidence"]["public_recomputation"])
        self.assertEqual("reject_exact_version", summary["lifecycle"]["adoption"])
        self.assertEqual("verified", summary["lifecycle"]["action"])
        self.assertEqual("disclosed_and_verified", summary["projection_deviation"]["status"])

    def test_lifecycle_hash_tamper_fails_closed(self) -> None:
        directory = "/private/tmp" if Path("/private/tmp").is_dir() else None
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            root = self._copy_public_tree(temporary)
            action_path = root / RESULT_RELATIVE / "action-record.pilot.json"
            action = json.loads(action_path.read_text(encoding="utf-8"))
            action["state"] = "blocked"
            action_path.write_text(json.dumps(action, indent=2) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(SandboxError, "owner action is not verified"):
                audit_debugging_shadow_bundle(
                    root / FREEZE_RELATIVE,
                    root / RESULT_RELATIVE,
                    git_root=root,
                )

    def test_measurement_tamper_fails_contract_hash_validation(self) -> None:
        directory = "/private/tmp" if Path("/private/tmp").is_dir() else None
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            root = self._copy_public_tree(temporary)
            measurement_path = root / RESULT_RELATIVE / "measurement-set.json"
            measurement = json.loads(measurement_path.read_text(encoding="utf-8"))
            measurement["measurements"][0]["value"] = not measurement["measurements"][0]["value"]
            measurement_path.write_text(json.dumps(measurement, indent=2) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(SandboxError, "Contract v0 graph is invalid"):
                audit_debugging_shadow_bundle(
                    root / FREEZE_RELATIVE,
                    root / RESULT_RELATIVE,
                    git_root=root,
                )


if __name__ == "__main__":
    unittest.main()
