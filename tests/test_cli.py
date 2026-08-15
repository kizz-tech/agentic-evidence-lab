from __future__ import annotations

import unittest

from ael.cli import _audit_result_fields
from ael.sandbox import SandboxError


class StudyAuditSummaryTests(unittest.TestCase):
    def test_legacy_result_owned_counts_remain_supported(self) -> None:
        self.assertEqual(
            "stage=terminal outcome=clear_reduction disposition=adopt runs=52 measurements=100",
            _audit_result_fields(
                {
                    "result": {
                        "effect_result": "clear_reduction",
                        "disposition": "adopt",
                        "run_count": 52,
                        "measurement_count": 100,
                    }
                }
            ),
        )

    def test_activation_evidence_owned_counts_are_supported(self) -> None:
        self.assertEqual(
            "stage=terminal outcome=protocol_invalid disposition=revise_adapter "
            "runs=6 measurements=24",
            _audit_result_fields(
                {
                    "result": {
                        "status": "protocol_invalid",
                        "disposition": "revise_adapter",
                    },
                    "evidence": {"run_records": 6, "measurements": 24},
                }
            ),
        )

    def test_incomplete_adapter_summary_fails_closed(self) -> None:
        with self.assertRaisesRegex(SandboxError, "incomplete result fields"):
            _audit_result_fields({"result": {"status": "complete", "disposition": "adopt"}})


if __name__ == "__main__":
    unittest.main()
