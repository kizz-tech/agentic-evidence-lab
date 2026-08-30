from __future__ import annotations

# ruff: noqa: E402
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from ael.sandbox import SandboxError
from tools.qualify_completion_integrity_tasks import validate_executor_contract


class CompletionIntegrityTaskQualificationTests(unittest.TestCase):
    def test_qualification_checks_the_exact_scored_task_requirement_syntax(self) -> None:
        dossier = {
            "requirements": [
                {"requirement_id": "REQ:ONE"},
                {"requirement_id": "REQ:TWO"},
            ]
        }
        with tempfile.TemporaryDirectory(prefix="ael-task-contract-") as raw:
            task_root = Path(raw)
            fixture = task_root / "fixture"
            fixture.mkdir()
            task = fixture / "TASK.md"
            task.write_text(
                "- `REQ:ONE`: first predicate\n- `REQ:TWO`: second predicate\n",
                encoding="utf-8",
            )
            self.assertEqual(
                ["REQ:ONE", "REQ:TWO"],
                validate_executor_contract(task_root, dossier),
            )

            task.write_text(
                "- `REQ:ONE` — first predicate\n- `REQ:TWO` — second predicate\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(SandboxError, "unique explicit"):
                validate_executor_contract(task_root, dossier)

            task.write_text("- `REQ:TWO`: second predicate\n", encoding="utf-8")
            with self.assertRaisesRegex(SandboxError, "exactly match"):
                validate_executor_contract(task_root, dossier)


if __name__ == "__main__":
    unittest.main()
