from __future__ import annotations

import unittest
from pathlib import Path

from ael.result_verification import (
    AUDIT_ADAPTERS,
    AuditRequest,
    audit_adapter_names,
    audit_bundle,
    public_audit_projection,
)
from ael.sandbox import SandboxError

ROOT = Path(__file__).resolve().parents[1]
PBT_FREEZE = ROOT / "studies/agent-skills-season-1/screening/property-based-testing-v2.freeze.json"
PBT_RESULT = ROOT / "studies/agent-skills-season-1/results/property-based-testing-v2"
CI_FREEZE = ROOT / "studies/completion-integrity/freeze.json"
CI_RESULT = ROOT / "studies/completion-integrity/results/prompt-policy-v1"
CI_ACTIVATION_FREEZE = ROOT / "studies/completion-integrity/activation-v2/freeze.json"
CI_ACTIVATION_RESULT = ROOT / "studies/completion-integrity/activation-v2/results"


class ResultVerificationTests(unittest.TestCase):
    def test_registry_is_immutable_and_has_one_canonical_name_source(self) -> None:
        self.assertEqual(
            (
                "completion-integrity-activation-v1",
                "completion-integrity-prompt-policy-v1",
                "pbt-v2",
                "systematic-debugging-real-shadow-v1",
            ),
            audit_adapter_names(),
        )
        with self.assertRaises(TypeError):
            AUDIT_ADAPTERS["unsafe"] = lambda _request: {}  # type: ignore[index]

    def test_unknown_adapter_fails_closed(self) -> None:
        with self.assertRaisesRegex(SandboxError, "unknown study audit adapter"):
            audit_bundle("missing", AuditRequest(PBT_FREEZE, PBT_RESULT))

    def test_public_projection_uses_adapter_and_removes_build_only_git_state(self) -> None:
        summary = public_audit_projection(
            "pbt-v2",
            AuditRequest(PBT_FREEZE, PBT_RESULT, git_root=ROOT),
        )
        self.assertEqual(
            "kizz:ael:study:agent-skills-season-1:property-based-testing",
            summary["study"]["study_id"],
        )
        self.assertNotIn("git_verified", summary["preregistration"])
        self.assertIn("artifact ordering only", summary["preregistration"]["boundary"])

    def test_public_projection_is_identical_after_required_git_proof(self) -> None:
        without_proof = public_audit_projection(
            "completion-integrity-activation-v1",
            AuditRequest(CI_ACTIVATION_FREEZE, CI_ACTIVATION_RESULT, git_root=ROOT),
        )
        with_proof = public_audit_projection(
            "completion-integrity-activation-v1",
            AuditRequest(
                CI_ACTIVATION_FREEZE,
                CI_ACTIVATION_RESULT,
                git_root=ROOT,
                require_git_proof=True,
            ),
        )

        self.assertEqual(without_proof, with_proof)
        self.assertEqual(
            {"sha", "boundary"},
            set(with_proof["preregistration"]),
        )

    def test_real_shadow_adapter_rejects_legacy_private_roots_before_audit(self) -> None:
        with self.assertRaisesRegex(SandboxError, "legacy screening/confirmation roots"):
            audit_bundle(
                "systematic-debugging-real-shadow-v1",
                AuditRequest(PBT_FREEZE, PBT_RESULT, screening_root=ROOT),
            )

    def test_completion_integrity_projection_has_stable_rendering_counts(self) -> None:
        summary = public_audit_projection(
            "completion-integrity-prompt-policy-v1",
            AuditRequest(CI_FREEZE, CI_RESULT, git_root=ROOT),
        )

        self.assertEqual("passed", summary["status"])
        self.assertEqual(
            {"contract_documents": 56, "run_records": 52, "measurements": 521},
            summary["evidence"],
        )
        self.assertEqual("null", summary["result"]["effect_result"])


if __name__ == "__main__":
    unittest.main()
