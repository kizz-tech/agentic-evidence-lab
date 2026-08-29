from __future__ import annotations

import hashlib
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from ael.coevolution_bundle import AdapterError, load_bundle, load_protocol
from tools.materialize_ael_cep_stage0 import materialize

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "studies" / "ael-cep" / "stage-0"

# These are checksums of the canonical pretty-JSON/text bytes, not the
# content-addressed protocol/bundle hashes. Keeping both layers explicit
# catches accidental reserialization as well as ledger identity drift.
EXPECTED_FILES = {
    "protocol.json": (35152, "abf1dc16410a22a9fe728d0cfad2598942e0287e13af47b50e3b0c434c7252da"),
    "trajectory-bundle.json": (
        449098,
        "c5ac778628285bc71537752e80b25c1597eeea119e9101059d01edf24056f4e2",
    ),
    "report.md": (4868, "4fc9abaf7db39a2c9808b42876baeba87849cc537d9f9a8b19bc976ddf34f889"),
    "README.md": (1805, "04acd6826d781f4e8ac13e26be2d0fe1fdf91531adefa2d884cc01fed40ffbb8"),
}
EXPECTED_PROTOCOL_HASH = "f9afea54b022a889ad74584093dbcac40a0c64eaa86a349ee0e5b71f4be04de9"
EXPECTED_BUNDLE_HASH = "77405678c8688883576329dfb7d2ec62d92298aebeca928a670bf21f07eea949"


class CoevolutionStage0GoldenTests(unittest.TestCase):
    def test_golden_identity_checksums_and_bounds(self) -> None:
        for name, (size, digest) in EXPECTED_FILES.items():
            path = GOLDEN / name
            self.assertTrue(path.is_file(), name)
            content = path.read_bytes()
            self.assertEqual(size, len(content), name)
            self.assertEqual(digest, hashlib.sha256(content).hexdigest(), name)
            self.assertLess(len(content), 2 * 1024 * 1024, name)

        protocol, raw_sha256 = load_protocol(GOLDEN / "protocol.json")
        bundle = load_bundle(GOLDEN / "trajectory-bundle.json", protocol=protocol)
        self.assertEqual("ael-cep-stage0-20260815", protocol["protocol_id"])
        self.assertEqual(20260815, protocol["simulation"]["seed"])
        self.assertEqual("forbidden", protocol["effect_policy"])
        self.assertEqual(
            "abf1dc16410a22a9fe728d0cfad2598942e0287e13af47b50e3b0c434c7252da", raw_sha256
        )
        self.assertEqual(EXPECTED_PROTOCOL_HASH, bundle["protocol_hash"])
        self.assertEqual(EXPECTED_BUNDLE_HASH, bundle["bundle_hash"])
        self.assertEqual(204, len(bundle["records"]))
        self.assertEqual(
            {
                "trajectory_summary": 72,
                "evaluation_binding": 30,
                "score_run": 30,
                "subject_execution_evidence": 19,
                "evaluator_release": 8,
                "builder_release": 8,
                "promotion_transition": 7,
                "confirmation_consumption": 1,
                "anchor_observation": 11,
                "independence_assessment": 2,
                "challenger_release": 1,
                "anchor_release": 1,
                "measurement_method": 1,
                "exposure_event": 6,
                "effect_attempt": 3,
                "bridge_observation": 1,
                "comparability_decision": 1,
                "deletion_tombstone": 1,
                "contrast_summary": 1,
            },
            Counter(record["record_type"] for record in bundle["records"]),
        )

        # Stage 0 exercises the forbidden-effect path without ever dispatching
        # a real operation.  Only the represented A5 promotion-chain facts are
        # authoritative; the simulator carries the remaining arm attempts in
        # the validated aggregate contrast summary.
        effect_attempts = [
            record for record in bundle["records"] if record["record_type"] == "effect_attempt"
        ]
        self.assertEqual(3, len(effect_attempts))
        self.assertEqual(
            {"blocked"},
            {record["payload"]["disposition"] for record in effect_attempts},
        )
        self.assertEqual(
            {"not_dispatched"},
            {record["payload"]["postcondition_status"] for record in effect_attempts},
        )
        self.assertEqual(
            {"forbidden_effect_policy"},
            {record["payload"]["reason_code"] for record in effect_attempts},
        )

        report = (GOLDEN / "report.md").read_text(encoding="utf-8")
        readme = (GOLDEN / "README.md").read_text(encoding="utf-8")
        self.assertIn("synthetic / provisional / no-effect Stage 0", report)
        self.assertIn("not authority", report)
        self.assertIn("Primary prospective endpoints", report)
        self.assertIn("Contrast diagnostics", report)
        self.assertIn("missing_endpoint", report)
        for metric in (
            "false_promotion_share",
            "invalid_candidate_promotion_rate",
            "useful_candidate_power",
            "exploit_acceptance",
            "critical_failure",
            "bridge_reversal",
            "taint",
            "missingness",
            "quarantine",
            "optional_stopping",
            "revocation_completeness",
        ):
            self.assertIn(f"`{metric}`:", report)
        self.assertIn("no real", readme)
        self.assertIn("never rewrites", readme)

    def test_regeneration_is_byte_identical_and_check_is_non_mutating(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            first = materialize(output)
            original = {name: (output / name).read_bytes() for name in EXPECTED_FILES}
            self.assertEqual("materialized", first["status"])
            checked = materialize(output, check=True)
            self.assertEqual("checked", checked["status"])
            for name, content in original.items():
                self.assertEqual(content, (output / name).read_bytes(), name)
            self.assertEqual(EXPECTED_BUNDLE_HASH, first["bundle_hash"])
            self.assertEqual(204, first["record_count"])

    def test_check_fails_closed_without_rewriting_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            materialize(output)
            report_path = output / "report.md"
            report_path.write_bytes(report_path.read_bytes() + b"drift\n")
            before = report_path.read_bytes()
            with self.assertRaisesRegex(AdapterError, "output_drift"):
                materialize(output, check=True)
            self.assertEqual(before, report_path.read_bytes())


if __name__ == "__main__":
    unittest.main()
