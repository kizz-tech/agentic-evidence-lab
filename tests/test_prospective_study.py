from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from ael.prospective_study import (
    authorize_scored_run,
    load_json_object,
    validate_admission,
    validate_freeze,
)
from ael.sandbox import SandboxError

ROOT = Path(__file__).resolve().parents[1]
ADMISSION = (
    ROOT
    / "studies"
    / "agent-skills-season-1"
    / "screening"
    / "systematic-debugging-real-shadow.admission.pilot.json"
)
FREEZE = (
    ROOT
    / "studies"
    / "agent-skills-season-1"
    / "screening"
    / "systematic-debugging-real-shadow.freeze.json"
)


class ProspectiveStudyTests(unittest.TestCase):
    def test_public_admission_and_freeze_are_valid(self) -> None:
        self.assertEqual([], validate_admission(load_json_object(ADMISSION)))
        self.assertEqual([], validate_freeze(load_json_object(FREEZE)))

    def test_admission_unknown_field_and_missing_risk_gate_fail(self) -> None:
        admission = load_json_object(ADMISSION)
        admission["invented"] = True
        admission["execution_authority"]["exact_candidate_only"] = False
        issues = validate_admission(admission)
        self.assertTrue(any("unknown keys" in issue.message for issue in issues))
        self.assertTrue(
            any(issue.location == "execution_authority.exact_candidate_only" for issue in issues)
        )

    def test_freeze_requires_manifest_and_admission_hashes(self) -> None:
        freeze = load_json_object(FREEZE)
        freeze["admission_ref"]["sha256"] = "bad"
        freeze["study_manifest_ref"]["sha256"] = "bad"
        issues = validate_freeze(freeze)
        self.assertTrue(any(issue.location == "admission_ref.sha256" for issue in issues))
        self.assertTrue(any(issue.location == "study_manifest_ref.sha256" for issue in issues))

    def test_authorization_fails_closed_on_every_observed_binding(self) -> None:
        admission = load_json_object(ADMISSION)
        freeze = load_json_object(FREEZE)
        observed = {
            "admission_sha256": freeze["admission_ref"]["sha256"],
            "manifest_sha256": freeze["study_manifest_ref"]["sha256"],
            "source_lock_sha256": freeze["source_lock_ref"]["sha256"],
            "candidate_tree_sha256": freeze["candidate"]["tree_sha256"],
            "private_pack_sha256": freeze["private_pack"]["sha256"],
            "runner_sha256": freeze["code_hashes"]["runner"],
            "decision_sha256": freeze["code_hashes"]["decision"],
            "materializer_sha256": freeze["code_hashes"]["materializer"],
            "execution_sha256": freeze["code_hashes"]["execution"],
            "prompt_sha256": freeze["prompt_sha256"],
            "runner_image_id": freeze["runtime"]["runner_image_id"],
            "proxy_image_id": freeze["runtime"]["proxy_image_id"],
            "evaluator_image_id": freeze["runtime"]["evaluator_image_id"],
        }
        authorize_scored_run(admission, freeze, observed)
        for key in tuple(observed):
            tampered = copy.deepcopy(observed)
            tampered[key] = "tampered"
            with self.subTest(key=key), self.assertRaisesRegex(SandboxError, "binding mismatch"):
                authorize_scored_run(admission, freeze, tampered)

    def test_strict_json_rejects_duplicate_and_overflow(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.json"
            path.write_text('{"a": 1, "a": 2}', encoding="utf-8")
            with self.assertRaisesRegex(SandboxError, "duplicate"):
                load_json_object(path)
            path.write_text('{"a": 1e400}', encoding="utf-8")
            with self.assertRaisesRegex(SandboxError, "non-finite"):
                load_json_object(path)


if __name__ == "__main__":
    unittest.main()
