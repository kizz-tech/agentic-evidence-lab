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


class ResultVerificationTests(unittest.TestCase):
    def test_registry_is_immutable_and_has_one_canonical_name_source(self) -> None:
        self.assertEqual(
            ("pbt-v2", "systematic-debugging-real-shadow-v1"),
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

    def test_real_shadow_adapter_rejects_legacy_private_roots_before_audit(self) -> None:
        with self.assertRaisesRegex(SandboxError, "legacy screening/confirmation roots"):
            audit_bundle(
                "systematic-debugging-real-shadow-v1",
                AuditRequest(PBT_FREEZE, PBT_RESULT, screening_root=ROOT),
            )


if __name__ == "__main__":
    unittest.main()
