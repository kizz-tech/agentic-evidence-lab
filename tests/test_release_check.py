from __future__ import annotations

import unittest

from tools.release_check import PRIVATE_EVIDENCE_CANARY_PREFIX, payload_failures


class ReleaseCheckTests(unittest.TestCase):
    def test_private_evidence_canary_is_rejected(self) -> None:
        failures = payload_failures(
            "reports/leaked.md", f"fixture marker: {PRIVATE_EVIDENCE_CANARY_PREFIX}demo"
        )
        self.assertTrue(any("private evidence canary" in failure for failure in failures))

    def test_ordinary_public_text_passes_payload_scan(self) -> None:
        self.assertEqual([], payload_failures("README.md", "Public bounded result.\n"))


if __name__ == "__main__":
    unittest.main()
