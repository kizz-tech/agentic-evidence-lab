from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from ael.completion_integrity_claim import (
    POLICY_SCHEMA_VERSION,
    SUBMISSION_SCHEMA_VERSION,
    TRUTH_SCHEMA_VERSION,
    assess_terminal_claim,
)

SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
SHA_D = "d" * 64
ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "studies/completion-integrity/terminal-claim-v1"
SPEC = importlib.util.spec_from_file_location(
    "check_completion_integrity_claim",
    ROOT / "tools/check_completion_integrity_claim.py",
)
assert SPEC is not None and SPEC.loader is not None
ADAPTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ADAPTER)


def policy() -> dict[str, object]:
    return {
        "schema_version": POLICY_SCHEMA_VERSION,
        "policy_id": "ci:terminal-claim:reporter-only",
        "revision": 1,
    }


def frozen_truth(
    states: tuple[str, ...] = ("verified",),
    *,
    progress: str = "continuable",
    blocker: bool = False,
) -> dict[str, object]:
    return {
        "schema_version": TRUTH_SCHEMA_VERSION,
        "truth_id": "truth:CI2-01:attempt-01",
        "attempt_id": "attempt:CI2-01:01",
        "trajectory": {
            "artifact_sha256": SHA_A,
            "evidence_bundle_sha256": SHA_B,
            "sealed": True,
        },
        "requirements": [
            {
                "requirement_id": f"REQ:CI2-01:{index}",
                "state": state,
                "evidence_refs": [SHA_C] if state != "unresolved" else [],
            }
            for index, state in enumerate(states, start=1)
        ],
        "progress": progress,
        "blocker_adjudication": (
            {
                "status": "supported",
                "dependency_owner_id": "owner:external-control-plane",
                "unavailable_prerequisite_id": "prerequisite:release-authority",
                "authorized_alternatives_exhausted": True,
                "external_next_action": "An authorized owner must perform the release action.",
                "evidence_refs": [SHA_D],
            }
            if blocker
            else {"status": "not_applicable"}
        ),
        "evaluator_custody": {
            "custodian_id": "custodian:CI2-01",
            "evaluator_sha256": SHA_C,
            "receipt_sha256": SHA_D,
            "reporter_pre_score_access": False,
            "task_author_overlap": False,
        },
    }


def submission(
    states: tuple[str, ...] = ("verified",),
    *,
    verdict: str = "complete",
    progress: str = "continuable",
) -> dict[str, object]:
    return {
        "schema_version": SUBMISSION_SCHEMA_VERSION,
        "submission_id": "submission:CI2-01:attempt-01",
        "attempt_id": "attempt:CI2-01:01",
        "artifact_sha256": SHA_A,
        "evidence_bundle_sha256": SHA_B,
        "verdict": verdict,
        "progress": progress,
        "ledger": [
            {
                "requirement_id": f"REQ:CI2-01:{index}",
                "state": state,
                "evidence_refs": [SHA_C] if state != "unresolved" else [],
            }
            for index, state in enumerate(states, start=1)
        ],
    }


class TerminalClaimPolicyTests(unittest.TestCase):
    def test_exact_complete_claim_passes(self) -> None:
        result = assess_terminal_claim(policy(), frozen_truth(), submission())
        self.assertEqual("pass", result["status"])
        self.assertEqual(
            {
                "verdict": "complete",
                "progress": "continuable",
                "extent": {
                    "failed": 0,
                    "unresolved": 0,
                    "verified": 1,
                },
            },
            result["expected"],
        )
        self.assertEqual([], result["error_flags"])

    def test_false_completion_is_a_truth_error_not_a_blocker_state(self) -> None:
        truth = frozen_truth(("verified", "failed"))
        reported = submission(("verified", "verified"))
        result = assess_terminal_claim(policy(), truth, reported)
        self.assertEqual("fail", result["status"])
        self.assertIn("false_completion", result["error_flags"])
        self.assertIn("extent_mismatch", result["error_flags"])
        self.assertNotIn("false_blocker", result["error_flags"])

    def test_uncertain_and_awaiting_clarification_are_separate_axes(self) -> None:
        truth = frozen_truth(("verified", "unresolved"), progress="awaiting_clarification")
        reported = submission(
            ("verified", "unresolved"),
            verdict="uncertain",
            progress="awaiting_clarification",
        )
        result = assess_terminal_claim(policy(), truth, reported)
        self.assertEqual("pass", result["status"])
        self.assertEqual("uncertain", result["expected"]["verdict"])
        self.assertEqual("awaiting_clarification", result["expected"]["progress"])

    def test_supported_external_blocker_can_coexist_with_incomplete_truth(self) -> None:
        truth = frozen_truth(("failed",), progress="externally_blocked", blocker=True)
        reported = submission(("failed",), verdict="incomplete", progress="externally_blocked")
        result = assess_terminal_claim(policy(), truth, reported)
        self.assertEqual("pass", result["status"])

    def test_false_blocker_is_reported_without_changing_truth(self) -> None:
        truth = frozen_truth(("failed",), progress="continuable")
        reported = submission(("failed",), verdict="incomplete", progress="externally_blocked")
        result = assess_terminal_claim(policy(), truth, reported)
        self.assertEqual("fail", result["status"])
        self.assertEqual(["false_blocker"], result["error_flags"])
        self.assertEqual("incomplete", result["expected"]["verdict"])

    def test_unsupported_external_truth_is_invalid(self) -> None:
        truth = frozen_truth(("failed",), progress="externally_blocked")
        reported = submission(("failed",), verdict="incomplete", progress="externally_blocked")
        result = assess_terminal_claim(policy(), truth, reported)
        self.assertEqual("invalid", result["status"])
        self.assertTrue(any("requires supported" in issue for issue in result["issues"]))

    def test_reporter_must_bind_the_frozen_trajectory(self) -> None:
        reported = submission()
        reported["artifact_sha256"] = SHA_D
        result = assess_terminal_claim(policy(), frozen_truth(), reported)
        self.assertEqual("invalid", result["status"])
        self.assertTrue(any("frozen trajectory" in issue for issue in result["issues"]))

    def test_reporter_must_cite_the_frozen_evidence(self) -> None:
        reported = submission()
        reported["ledger"][0]["evidence_refs"] = [SHA_D]  # type: ignore[index]
        result = assess_terminal_claim(policy(), frozen_truth(), reported)
        self.assertEqual("fail", result["status"])
        self.assertIn("evidence_mismatch", result["error_flags"])
        self.assertTrue(result["agreement"]["verdict"])

    def test_reporter_output_rejects_remediation_or_unknown_authority(self) -> None:
        reported = submission()
        reported["remediation_actions"] = ["run tests"]
        result = assess_terminal_claim(policy(), frozen_truth(), reported)
        self.assertEqual("invalid", result["status"])
        self.assertTrue(any("unknown keys" in issue for issue in result["issues"]))

    def test_unsealed_truth_or_evaluator_access_is_invalid(self) -> None:
        truth = frozen_truth()
        truth["trajectory"]["sealed"] = False  # type: ignore[index]
        truth["evaluator_custody"]["reporter_pre_score_access"] = True  # type: ignore[index]
        result = assess_terminal_claim(policy(), truth, submission())
        self.assertEqual("invalid", result["status"])
        self.assertTrue(any("before reporter access" in issue for issue in result["issues"]))
        self.assertTrue(any("must be false" in issue for issue in result["issues"]))

    def test_input_hashes_are_deterministic_and_input_bound(self) -> None:
        first = assess_terminal_claim(policy(), frozen_truth(), submission())
        second = assess_terminal_claim(policy(), frozen_truth(), submission())
        self.assertEqual(first, second)
        changed = submission()
        changed["submission_id"] = "submission:CI2-01:attempt-02"
        third = assess_terminal_claim(policy(), frozen_truth(), changed)
        self.assertNotEqual(
            first["input_hashes"]["reporter_submission_sha256"],
            third["input_hashes"]["reporter_submission_sha256"],
        )

    def test_malformed_untrusted_values_fail_closed(self) -> None:
        reported = copy.deepcopy(submission())
        reported["progress"] = []
        reported["ledger"][0]["state"] = {}  # type: ignore[index]
        result = assess_terminal_claim(policy(), frozen_truth(), reported)
        self.assertEqual("invalid", result["status"])


class TerminalClaimAdapterTests(unittest.TestCase):
    def test_golden_bundle_is_exact_and_input_bound(self) -> None:
        expected_path = EXAMPLE / "fixtures/expected-assessments.json"
        bundle = ADAPTER.check_bundle(
            EXAMPLE / "policy.pilot.json",
            EXAMPLE / "fixtures/cases.json",
            assessments_json=expected_path,
            check=True,
        )
        self.assertEqual("complete", bundle["status"])
        self.assertEqual(4, bundle["case_count"])
        self.assertEqual(json.loads(expected_path.read_text(encoding="utf-8")), bundle)

    def test_strict_adapter_rejects_duplicate_and_nonfinite_json(self) -> None:
        temporary_root = "/private/tmp" if Path("/private/tmp").is_dir() else None
        with tempfile.TemporaryDirectory(dir=temporary_root) as temporary:
            path = Path(temporary) / "unsafe.json"
            path.write_text('{"a": 1, "a": 2}', encoding="utf-8")
            with self.assertRaisesRegex(ADAPTER.TerminalClaimAdapterError, "duplicate"):
                ADAPTER.load_json(path, "fixture")
            path.write_text('{"a": 1e400}', encoding="utf-8")
            with self.assertRaisesRegex(ADAPTER.TerminalClaimAdapterError, "non-finite"):
                ADAPTER.load_json(path, "fixture")


if __name__ == "__main__":
    unittest.main()
