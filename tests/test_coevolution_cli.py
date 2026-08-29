from __future__ import annotations

import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path

from ael import coevolution as core
from ael.cli import main
from ael.coevolution_bundle import write_json_atomic
from ael.coevolution_simulator import default_protocol, simulate


class CoevolutionCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)
        self.protocol_path = self.root / "protocol.json"
        # One scenario keeps direct CLI coverage fast while still exercising
        # the complete protocol, evidence, and projection contracts.
        write_json_atomic(self.protocol_path, default_protocol(seed=71, scenarios=["null"]))
        self.bundle_path = self.root / "trajectory.json"
        self.report_path = self.root / "trajectory.md"

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def _main(self, argv: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = main(argv)
        return result, stdout.getvalue(), stderr.getvalue()

    def _simulate(self) -> None:
        result, _, stderr = self._main(
            [
                "coevolution",
                "simulate",
                str(self.protocol_path),
                "--bundle-output",
                str(self.bundle_path),
                "--report-output",
                str(self.report_path),
            ]
        )
        self.assertEqual(0, result, stderr)

    def test_simulate_check_and_stale_check_fail_closed(self) -> None:
        self._simulate()
        result, _, stderr = self._main(
            [
                "coevolution",
                "simulate",
                str(self.protocol_path),
                "--bundle-output",
                str(self.bundle_path),
                "--report-output",
                str(self.report_path),
                "--check",
            ]
        )
        self.assertEqual(0, result, stderr)
        result, stdout, stderr = self._main(
            [
                "coevolution",
                "check",
                str(self.protocol_path),
                str(self.bundle_path),
                "--report",
                str(self.report_path),
                "--check-report",
            ]
        )
        self.assertEqual(0, result, stderr)
        self.assertIn("coevolution check passed", stdout)

        self.report_path.write_text("stale\n", encoding="utf-8")
        result, _, stderr = self._main(
            [
                "coevolution",
                "check",
                str(self.protocol_path),
                str(self.bundle_path),
                "--report",
                str(self.report_path),
                "--check-report",
            ]
        )
        self.assertEqual(2, result)
        self.assertIn("output_drift", stderr)
        self.assertNotIn("Traceback", stderr)

        result, _, stderr = self._main(
            [
                "coevolution",
                "simulate",
                str(self.protocol_path),
                "--bundle-output",
                str(self.bundle_path),
                "--report-output",
                str(self.report_path),
                "--check",
            ]
        )
        self.assertEqual(2, result)
        self.assertIn("output_drift", stderr)
        self.assertNotIn("Traceback", stderr)

    def test_invalid_protocol_fails_closed_without_traceback(self) -> None:
        bad_protocol = self.root / "bad-protocol.json"
        write_json_atomic(bad_protocol, {})
        result, _, stderr = self._main(
            [
                "coevolution",
                "simulate",
                str(bad_protocol),
                "--bundle-output",
                str(self.bundle_path),
                "--report-output",
                str(self.report_path),
            ]
        )
        self.assertEqual(2, result)
        self.assertIn("coevolution simulate failed", stderr)
        self.assertNotIn("Traceback", stderr)
        self.assertFalse(self.bundle_path.exists())
        self.assertFalse(self.report_path.exists())

    def test_rescore_appends_successor_and_preserves_source_bytes(self) -> None:
        protocol = default_protocol(seed=72, scenarios=["null"])
        # Use the complete observation prefix before aggregate summaries. A
        # partial summary set is invalid without its simulation-summary seal,
        # while this prefix retains the original A0 score and remains
        # available for evaluator-only rescoring.
        simulated = simulate(protocol)
        first_summary_index = next(
            index
            for index, record in enumerate(simulated["records"])
            if record["record_type"] == "trajectory_summary"
        )
        source = core.create_bundle(
            protocol,
            bundle_id="cli-rescore-source",
            records=simulated["records"][:first_summary_index],
        )
        write_json_atomic(self.protocol_path, protocol)
        write_json_atomic(self.bundle_path, source)
        source_bytes = self.bundle_path.read_bytes()

        old_score = next(
            record
            for record in source["records"]
            if record["record_type"] == "score_run"
            and record["record_id"] == "score:A0:screening:original"
        )
        old_evaluator_id = old_score["payload"]["evaluator_release_ref"]
        old_evaluator = next(
            record for record in source["records"] if record["record_id"] == old_evaluator_id
        )
        evaluator_payload = copy.deepcopy(old_evaluator["payload"])
        evaluator_payload["release_id"] = "evaluator:cli:rescore:v1"
        evaluator_payload["artifact_hash"] = "b" * 64
        score_payload = copy.deepcopy(old_score["payload"])
        score_payload["score_run_id"] = "score:cli:rescore:v1"
        for key in (
            "binding_ref",
            "binding_hash",
            "evaluator_release_ref",
            "evaluator_release_hash",
        ):
            score_payload.pop(key, None)
        request_path = self.root / "rescore-request.json"
        write_json_atomic(
            request_path,
            {
                "evaluator_release": evaluator_payload,
                "score_payload": score_payload,
                # The rescore actor is the frozen scoring/adjudication
                # authority, distinct from the new evaluator's custody.
                "actor": protocol["principals"]["adjudication"]["principal_id"],
                "retained_surfaces": ["subject-output", "task-input", "runner-trace"],
                "required_surfaces": ["subject-output", "task-input", "runner-trace"],
                "changes": ["evaluator"],
            },
        )
        successor_path = self.root / "rescore-successor.json"
        result, stdout, stderr = self._main(
            [
                "coevolution",
                "rescore",
                str(self.protocol_path),
                str(self.bundle_path),
                str(request_path),
                "--output",
                str(successor_path),
            ]
        )
        self.assertEqual(0, result, stderr)
        self.assertIn("coevolution rescore materialized", stdout)
        self.assertEqual(source_bytes, self.bundle_path.read_bytes())
        successor = json.loads(successor_path.read_text(encoding="utf-8"))
        self.assertEqual(source["records"], successor["records"][: len(source["records"])])
        self.assertEqual(len(source["records"]) + 3, len(successor["records"]))

        second_request = json.loads(request_path.read_text(encoding="utf-8"))
        second_request["evaluator_release"]["release_id"] = "evaluator:cli:rescore:v2"
        second_request["evaluator_release"]["artifact_hash"] = "c" * 64
        second_request["score_payload"]["score_run_id"] = "score:cli:rescore:v2"
        second_request_path = self.root / "rescore-request-v2.json"
        write_json_atomic(second_request_path, second_request)
        successor_v2_path = self.root / "rescore-successor-v2.json"
        result, _, stderr = self._main(
            [
                "coevolution",
                "rescore",
                str(self.protocol_path),
                str(successor_path),
                str(second_request_path),
                "--predecessor",
                str(self.bundle_path),
                "--output",
                str(successor_v2_path),
            ]
        )
        self.assertEqual(0, result, stderr)
        result, _, stderr = self._main(
            [
                "coevolution",
                "check",
                str(self.protocol_path),
                str(successor_v2_path),
                "--predecessor",
                str(self.bundle_path),
                "--predecessor",
                str(successor_path),
                "--report",
                str(self.root / "rescore-successor-v2.md"),
            ]
        )
        self.assertEqual(0, result, stderr)


if __name__ == "__main__":
    unittest.main()
