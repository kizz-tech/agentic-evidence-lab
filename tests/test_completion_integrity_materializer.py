from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ael.completion_integrity import derive_cell_outcome
from ael.completion_integrity_audit import audit_completion_integrity_bundle
from ael.prospective_study import load_json_object, sha256_path

ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "studies" / "completion-integrity" / "freeze.json"
MATERIALIZER = ROOT / "tools" / "materialize_completion_integrity.py"


def synthetic_observations() -> dict[str, object]:
    freeze = load_json_object(FREEZE)
    rows = []
    for entry in freeze["schedule"]:
        accepted = entry["condition_id"] == "T1"
        observation = {
            "schema_version": "ael.completion-integrity-cell/0.1-pilot",
            **entry,
            "attempt_id": "f" * 32,
            "status": "valid",
            "invalid_reasons": [],
            "operator_recorded_started_at": "2026-08-14T21:40:00Z",
            "operator_recorded_completed_at": "2026-08-14T21:41:00Z",
            "declaration_markers": ["complete"],
            "final_message_sha256": "1" * 64,
            "evaluator": {
                "operational_valid": True,
                "visible_tests_pass": True,
                "accepted": accepted,
                "regression": False,
                "critical_failure": False,
                "requirements": {},
                "omitted_requirement_ids": [] if accepted else ["SYNTHETIC-R1"],
            },
            "budget_exceeded": False,
            "usage": {
                "input_tokens": 100,
                "cached_input_tokens": 50,
                "output_tokens": 20,
                "reasoning_output_tokens": 10,
                "generated_tokens": 30,
                "wall_time_ms": 1000,
            },
            "event_count": 3,
            "private_refs": {
                "invocation_sha256": "2" * 64,
                "events_sha256": "3" * 64,
                "stderr_sha256": "4" * 64,
                "score_sha256": "5" * 64,
                "candidate_tree_sha256": "6" * 64,
            },
        }
        observation["derived"] = derive_cell_outcome(observation)
        rows.append(observation)
    return {
        "schema_version": "ael.completion-integrity-observations/0.1-pilot",
        "freeze_sha256": sha256_path(FREEZE),
        "stopped_reason": None,
        "observations": rows,
    }


class CompletionIntegrityMaterializerTests(unittest.TestCase):
    def test_materializer_and_independent_audit_close_the_public_loop(self) -> None:
        with tempfile.TemporaryDirectory(prefix=".ci9-materializer-test-", dir=ROOT) as temporary:
            temporary_root = Path(temporary)
            observations_path = temporary_root / "observations.json"
            observations_path.write_text(
                json.dumps(synthetic_observations(), indent=2) + "\n", encoding="utf-8"
            )
            result_root = temporary_root / "result"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(MATERIALIZER),
                    "--freeze",
                    str(FREEZE),
                    "--observations",
                    str(observations_path),
                    "--output",
                    str(result_root),
                    "--generated-at",
                    "2026-08-14T21:42:00Z",
                    "--preregistration-sha",
                    "a" * 40,
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            self.assertEqual(52, len(list((result_root / "runs").glob("*.json"))))

            audited = audit_completion_integrity_bundle(FREEZE, result_root, git_root=ROOT)

            self.assertEqual("positive", audited["result"]["effect_result"])
            self.assertEqual("enable_default", audited["result"]["disposition"])
            self.assertFalse(audited["preregistration"]["git_verified"])


if __name__ == "__main__":
    unittest.main()
