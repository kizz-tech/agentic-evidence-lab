from __future__ import annotations

import unittest

from tools.release_check import (
    PRIVATE_EVIDENCE_CANARY_PREFIX,
    REQUIRED_FILES,
    payload_failures,
)


class ReleaseCheckTests(unittest.TestCase):
    def test_private_evidence_canary_is_rejected(self) -> None:
        failures = payload_failures(
            "reports/leaked.md", f"fixture marker: {PRIVATE_EVIDENCE_CANARY_PREFIX}demo"
        )
        self.assertTrue(any("private evidence canary" in failure for failure in failures))

    def test_ordinary_public_text_passes_payload_scan(self) -> None:
        self.assertEqual([], payload_failures("README.md", "Public bounded result.\n"))

    def test_cross_platform_personal_paths_are_rejected(self) -> None:
        for payload in (
            "/" + "home/alice/private/run.json",
            "C:\\Users" + "\\alice\\private\\run.json",
        ):
            with self.subTest(payload=payload):
                failures = payload_failures("docs/results/card.md", payload)
                self.assertTrue(any("personal absolute path" in failure for failure in failures))

    def test_signed_url_is_rejected(self) -> None:
        failures = payload_failures(
            "docs/results/card.md",
            "https://storage.example/x?X-Amz-Sig" + "nature=abcdef0123456789abcdef0123456789",
        )
        self.assertTrue(any("signed URL query" in failure for failure in failures))

    def test_ael_cep_stage0_golden_package_is_required(self) -> None:
        self.assertTrue(
            {
                "tools/materialize_ael_cep_stage0.py",
                "studies/ael-cep/stage-0/README.md",
                "studies/ael-cep/stage-0/protocol.json",
                "studies/ael-cep/stage-0/trajectory-bundle.json",
                "studies/ael-cep/stage-0/report.md",
            }.issubset(REQUIRED_FILES)
        )


if __name__ == "__main__":
    unittest.main()
