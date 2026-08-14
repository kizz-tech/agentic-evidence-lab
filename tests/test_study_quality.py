from __future__ import annotations

import contextlib
import hashlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from ael.cli import main
from ael.sandbox import SandboxError
from ael.study_quality import (
    QUALITY_PREFLIGHT_VERSION,
    load_profile,
    materialize_preflight,
    preflight,
    public_projection,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_ROOT = ROOT / "studies" / "quality-preflight" / "examples" / "pass"
PROFILE = EXAMPLE_ROOT / "quality-profile.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class StudyQualityTests(unittest.TestCase):
    def _temporary_directory(self) -> tempfile.TemporaryDirectory[str]:
        directory = "/private/tmp" if Path("/private/tmp").is_dir() else None
        return tempfile.TemporaryDirectory(dir=directory)

    def _profile_tree(self, temporary: str) -> tuple[Path, dict[str, object], Path]:
        root = Path(temporary)
        (root / "pyproject.toml").write_text("[project]\nname='quality-test'\n", encoding="utf-8")
        example = root / "studies" / "quality-preflight" / "examples" / "pass"
        shutil.copytree(EXAMPLE_ROOT, example)
        profile_path = example / "quality-profile.json"
        return profile_path, load_profile(profile_path), example / "study-manifest.json"

    def test_public_example_is_deterministic_and_bounded(self) -> None:
        first = preflight(PROFILE)
        second = preflight(PROFILE)
        self.assertEqual(first, second)
        self.assertEqual(QUALITY_PREFLIGHT_VERSION, first["schema_version"])
        self.assertEqual("conformant_with_warnings", first["status"])
        self.assertEqual(
            {
                "design_class": "controlled_pilot",
                "task_validity": "audited",
                "evaluator_validity": "calibrated",
                "sampling_strength": "decision_thresholded_pilot",
                "reliability_coverage": "repeated",
                "independence": "maintainer_only",
                "freshness": "current",
            },
            first["quality_axes"],
        )
        self.assertEqual(["QP-W004"], [issue["code"] for issue in first["issues"]])
        self.assertIn("do not prove scientific validity", first["boundary"])

    def test_retrospective_state_and_active_confirmation_drift_block(self) -> None:
        with self._temporary_directory() as temporary:
            profile_path, profile, _manifest = self._profile_tree(temporary)
            profile["prospective_state"]["scored_calls_executed"] = 1  # type: ignore[index]
            profile["task_quality"]["disclosure_state"] = "public_development"  # type: ignore[index]
            profile["task_quality"]["adaptive_uses"] = 2  # type: ignore[index]
            profile_path.write_text(json.dumps(profile), encoding="utf-8")
            result = preflight(profile_path, Path(temporary))
            self.assertEqual("blocked", result["status"])
            self.assertEqual(
                ["QP-E012", "QP-E018"],
                [issue["code"] for issue in result["issues"] if issue["severity"] == "error"],
            )

    def test_task_evaluator_and_analysis_omissions_fail_closed(self) -> None:
        with self._temporary_directory() as temporary:
            profile_path, profile, _manifest = self._profile_tree(temporary)
            profile["task_quality"]["audit_checks"]["oracle_validation"] = "not_assessed"  # type: ignore[index]
            profile["evaluator_quality"]["known_fail_cases"] = 0  # type: ignore[index]
            del profile["analysis_quality"]["uncertainty"]  # type: ignore[index]
            profile_path.write_text(json.dumps(profile), encoding="utf-8")
            result = preflight(profile_path, Path(temporary))
            codes = [issue["code"] for issue in result["issues"] if issue["severity"] == "error"]
            self.assertEqual("blocked", result["status"])
            self.assertIn("QP-E002", codes)
            self.assertIn("QP-E005", codes)
            self.assertIn("QP-E015", codes)

    def test_operational_stack_cannot_claim_factor_causality(self) -> None:
        with self._temporary_directory() as temporary:
            profile_path, profile, manifest_path = self._profile_tree(temporary)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["comparison_mode"] = "operational_stack"
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            profile["study_ref"]["sha256"] = _sha256(manifest_path)  # type: ignore[index]
            profile_path.write_text(json.dumps(profile), encoding="utf-8")
            result = preflight(profile_path, Path(temporary))
            self.assertEqual("blocked", result["status"])
            self.assertIn("QP-E029", [issue["code"] for issue in result["issues"]])

    def test_hash_mismatch_and_study_identity_mismatch_fail(self) -> None:
        with self._temporary_directory() as temporary:
            profile_path, profile, _manifest = self._profile_tree(temporary)
            profile["task_quality"]["audit_ref"]["sha256"] = "0" * 64  # type: ignore[index]
            profile["study_ref"]["study_id"] = "kizz:ael:study:wrong"  # type: ignore[index]
            profile_path.write_text(json.dumps(profile), encoding="utf-8")
            result = preflight(profile_path, Path(temporary))
            self.assertEqual("blocked", result["status"])
            self.assertIn("QP-E025", [issue["code"] for issue in result["issues"]])
            self.assertIn("QP-E027", [issue["code"] for issue in result["issues"]])
            with self.assertRaisesRegex(SandboxError, "preflight is blocked"):
                public_projection(profile_path, Path(temporary))

    def test_malformed_and_noncanonical_references_fail_without_crashing(self) -> None:
        with self._temporary_directory() as temporary:
            profile_path, profile, _manifest = self._profile_tree(temporary)
            profile["study_ref"] = []
            profile_path.write_text(json.dumps(profile), encoding="utf-8")
            result = preflight(profile_path, Path(temporary))
            self.assertEqual("blocked", result["status"])
            self.assertIsNone(result["study"]["study_id"])

        with self._temporary_directory() as temporary:
            profile_path, profile, _manifest = self._profile_tree(temporary)
            profile["task_quality"]["audit_ref"]["uri"] = "nested/../task-audit.md"  # type: ignore[index]
            profile_path.write_text(json.dumps(profile), encoding="utf-8")
            result = preflight(profile_path, Path(temporary))
            self.assertEqual("blocked", result["status"])
            self.assertIn("QP-E024", [issue["code"] for issue in result["issues"]])

    def test_design_strength_choices_are_stable_warnings_not_universal_gates(self) -> None:
        with self._temporary_directory() as temporary:
            profile_path, profile, _manifest = self._profile_tree(temporary)
            execution = profile["execution_declaration"]  # type: ignore[index]
            execution["repeats_per_cell"] = 1  # type: ignore[index]
            execution["order_policy"] = "fixed"  # type: ignore[index]
            execution["reliability"]["coverage"] = "single_run"  # type: ignore[index]
            profile["analysis_quality"]["uncertainty"] = {  # type: ignore[index]
                "status": "not_estimable",
                "reason": "The synthetic one-repeat screen does not identify an interval.",
            }
            profile_path.write_text(json.dumps(profile), encoding="utf-8")
            result = preflight(profile_path, Path(temporary))
            self.assertEqual("conformant_with_warnings", result["status"])
            self.assertEqual(
                ["QP-W001", "QP-W002", "QP-W003", "QP-W004"],
                [issue["code"] for issue in result["issues"]],
            )

    def test_freshness_uses_explicit_as_of_without_clock_access(self) -> None:
        due = preflight(PROFILE, as_of="2026-10-01")
        self.assertEqual("conformant_with_warnings", due["status"])
        self.assertEqual("revalidation_due", due["quality_axes"]["freshness"])
        self.assertEqual(
            ["QP-W004", "QP-W005"],
            [issue["code"] for issue in due["issues"]],
        )

        expired = preflight(PROFILE, as_of="2026-12-01")
        self.assertEqual("blocked", expired["status"])
        self.assertEqual("invalidated", expired["quality_axes"]["freshness"])
        self.assertIn("QP-E030", [issue["code"] for issue in expired["issues"]])

        predates = preflight(PROFILE, as_of="2026-08-13")
        self.assertEqual("blocked", predates["status"])
        self.assertIn("QP-E030", [issue["code"] for issue in predates["issues"]])

    def test_strict_json_rejects_duplicates_and_nonfinite_values(self) -> None:
        with self._temporary_directory() as temporary:
            profile_path = Path(temporary) / "profile.json"
            profile_path.write_text('{"a": 1, "a": 2}', encoding="utf-8")
            with self.assertRaisesRegex(SandboxError, "duplicate"):
                load_profile(profile_path)
            profile_path.write_text('{"a": 1e400}', encoding="utf-8")
            with self.assertRaisesRegex(SandboxError, "non-finite"):
                load_profile(profile_path)

    def test_materialization_check_and_cli_exit_codes(self) -> None:
        with self._temporary_directory() as temporary:
            output_root = Path(temporary)
            json_output = output_root / "preflight.json"
            markdown_output = output_root / "preflight.md"
            result = materialize_preflight(
                PROFILE,
                json_output=json_output,
                markdown_output=markdown_output,
            )
            self.assertEqual("conformant_with_warnings", result["status"])
            materialize_preflight(
                PROFILE,
                json_output=json_output,
                markdown_output=markdown_output,
                check=True,
            )
            with (
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                valid_exit = main(
                    [
                        "study",
                        "preflight",
                        str(PROFILE),
                        "--json-output",
                        str(json_output),
                        "--markdown-output",
                        str(markdown_output),
                        "--check",
                    ]
                )
            self.assertEqual(0, valid_exit)
            payload = json.loads(json_output.read_text(encoding="utf-8"))
            self.assertNotIn(str(ROOT), json.dumps(payload))

            blocked_path, blocked, _manifest = self._profile_tree(temporary)
            blocked["prospective_state"]["scored_calls_executed"] = 1  # type: ignore[index]
            blocked_path.write_text(json.dumps(blocked), encoding="utf-8")
            with (
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                blocked_exit = main(["study", "preflight", str(blocked_path)])
            self.assertEqual(1, blocked_exit)


if __name__ == "__main__":
    unittest.main()
