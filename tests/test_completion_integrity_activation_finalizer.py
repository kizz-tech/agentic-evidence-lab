from __future__ import annotations

# ruff: noqa: E402
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from ael.sandbox import SandboxError
from tools.completion_integrity_activation_support import (
    append_attempt_event,
    load_json,
    sha256_path,
)
from tools.finalize_completion_integrity_activation_run import finalize_interrupted_run

FREEZE = ROOT / "studies" / "completion-integrity" / "activation-v3" / "freeze.json"
PREREGISTRATION_SHA = "7257025eab78e8894f69e6ad0677fabec8cf5542"


class CompletionIntegrityActivationFinalizerTests(unittest.TestCase):
    def test_ambiguous_attempt_is_finalized_without_retry_or_model_call(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="ael-activation-finalizer-", dir="/private/tmp"
        ) as raw:
            raw_root = Path(raw)
            journal = raw_root / "attempts" / "CI3-PY-01-E0"
            common = {
                "schema_version": "ael.completion-integrity-activation-attempt/0.1-pilot",
                "attempt_id": "attempt:test",
                "freeze_sha256": sha256_path(FREEZE),
                "sequence": 1,
                "cell_id": "CI3-PY-01-E0",
                "task_id": "CI3-PY-01",
                "role": "executor",
                "condition_id": None,
                "prepared_at": "2026-08-30T01:05:25Z",
                "input_bindings": {},
            }
            append_attempt_event(
                journal,
                {**common, "state": "prepared", "submitted_at": None, "terminal_at": None},
            )
            append_attempt_event(
                journal,
                {
                    **common,
                    "state": "submitted",
                    "submitted_at": "2026-08-30T01:05:25Z",
                    "terminal_at": None,
                },
            )
            append_attempt_event(
                journal,
                {
                    **common,
                    "state": "ambiguous",
                    "submitted_at": "2026-08-30T01:05:25Z",
                    "terminal_at": "2026-08-30T01:07:25Z",
                    "error_type": "SandboxError",
                    "error": "private requirement contract was not parseable",
                },
            )

            recovery = finalize_interrupted_run(
                freeze_path=FREEZE,
                raw_root=raw_root,
                preregistration_sha=PREREGISTRATION_SHA,
                finalized_at="2026-08-30T02:00:00Z",
            )

            self.assertEqual(0, recovery["model_calls"])
            self.assertEqual(0, recovery["retries"])
            self.assertEqual("protocol_invalid", recovery["decision_status"])
            observations = load_json(raw_root / "observations.json")
            self.assertEqual("ambiguous", observations["tasks"][0]["executor_status"])
            self.assertEqual("unrun", observations["tasks"][1]["executor_status"])
            self.assertEqual(["CI3-PY-01-E0:SandboxError"], observations["protocol_issues"])
            with self.assertRaisesRegex(SandboxError, "overwrite"):
                finalize_interrupted_run(
                    freeze_path=FREEZE,
                    raw_root=raw_root,
                    preregistration_sha=PREREGISTRATION_SHA,
                    finalized_at="2026-08-30T02:01:00Z",
                )


if __name__ == "__main__":
    unittest.main()
