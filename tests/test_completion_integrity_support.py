from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ael.sandbox import SandboxError
from tools.completion_integrity_support import append_attempt_event, read_attempt_journal


def event(state: str, *, attempt_id: str = "attempt-1", cell_id: str = "CI-01-B0-R01"):
    return {
        "schema_version": "ael.completion-integrity-attempt/0.1-pilot",
        "attempt_id": attempt_id,
        "cell_id": cell_id,
        "state": state,
    }


class AttemptJournalTests(unittest.TestCase):
    def test_events_are_immutable_and_form_one_terminal_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            journal = Path(temporary) / "attempt"
            append_attempt_event(journal, event("prepared"))
            append_attempt_event(journal, event("submitted"))
            append_attempt_event(journal, event("terminal"))

            self.assertEqual(
                ["prepared", "submitted", "terminal"],
                [row["state"] for row in read_attempt_journal(journal)],
            )
            with self.assertRaisesRegex(SandboxError, "immutable"):
                append_attempt_event(journal, event("submitted"))

    def test_submitted_without_terminal_remains_ambiguous_and_retained(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            journal = Path(temporary) / "attempt"
            append_attempt_event(journal, event("prepared"))
            append_attempt_event(journal, event("submitted"))

            self.assertEqual("submitted", read_attempt_journal(journal)[-1]["state"])

    def test_identity_drift_and_invalid_transition_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            journal = Path(temporary) / "attempt"
            append_attempt_event(journal, event("prepared"))
            append_attempt_event(journal, event("submitted", attempt_id="attempt-2"))
            with self.assertRaisesRegex(SandboxError, "identity changed"):
                read_attempt_journal(journal)

        with tempfile.TemporaryDirectory() as temporary:
            journal = Path(temporary) / "attempt"
            append_attempt_event(journal, event("terminal"))
            with self.assertRaisesRegex(SandboxError, "invalid transition"):
                read_attempt_journal(journal)


if __name__ == "__main__":
    unittest.main()
