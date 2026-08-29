from __future__ import annotations

import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from ael.cli import _audit_result_fields, main
from ael.sandbox import SandboxError

ROOT = Path(__file__).resolve().parents[1]


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


class ContractGraphCliTests(unittest.TestCase):
    def test_validate_rejects_receipt_reference_with_swapped_run_identity(self) -> None:
        """The CLI must enforce the exact URI-to-identity graph, not just hashes."""

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "council-generation-1"
            shutil.copytree(ROOT / "examples" / "council-generation-1", root)
            receipt_path = root / "evidence-receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["run_record_refs"][0]["run_id"] = "kizz:ael:run:council-generation-1:E1-C1"
            receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                result = main(["validate", str(root)])

            self.assertEqual(1, result)
            self.assertIn(
                "reference target identity does not match declared identity", stderr.getvalue()
            )


if __name__ == "__main__":
    unittest.main()
