from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ael.completion_integrity_claim import assess_terminal_claim
from ael.sandbox import SandboxError
from tools.completion_integrity_activation_support import (
    activation_attempt_id,
    assess_executor_claim,
    build_frozen_truth,
    build_reporter_submission,
    parse_codex_events,
    parse_task_requirements,
)


def command_event(command: str, exit_code: int) -> dict[str, object]:
    return {
        "type": "item.completed",
        "_line_number": 4,
        "item": {
            "type": "command_execution",
            "command": command,
            "exit_code": exit_code,
        },
    }


def evaluation() -> dict[str, object]:
    return {
        "requirements": [
            {
                "requirement_id": "REQ:ONE",
                "state": "verified",
                "evidence_sha256": "a" * 64,
                "evidence_code": "owner-check:one",
            },
            {
                "requirement_id": "REQ:TWO",
                "state": "verified",
                "evidence_sha256": "b" * 64,
                "evidence_code": "owner-check:two",
            },
        ]
    }


def executor_output(command: str) -> dict[str, object]:
    return {
        "verdict": "complete",
        "progress": "continuable",
        "ledger": [
            {
                "requirement_id": "REQ:ONE",
                "state": "verified",
                "evidence_commands": [command],
            },
            {
                "requirement_id": "REQ:TWO",
                "state": "verified",
                "evidence_commands": [command],
            },
        ],
    }


class ActivationSupportTests(unittest.TestCase):
    def test_attempt_id_is_valid_by_construction_across_digit_leading_digests(self) -> None:
        freeze_sha256 = "e" * 64
        attempt_id = activation_attempt_id(freeze_sha256, "CI2-PY-01-B0")
        self.assertRegex(attempt_id, r"^[A-Za-z][A-Za-z0-9._:-]{2,127}$")
        self.assertEqual(attempt_id, activation_attempt_id(freeze_sha256, "CI2-PY-01-B0"))
        self.assertNotEqual(attempt_id, activation_attempt_id(freeze_sha256, "CI2-PY-01-T1"))
        with self.assertRaisesRegex(SandboxError, "SHA-256"):
            activation_attempt_id("not-a-hash", "CI2-PY-01-B0")

    def test_generated_attempt_id_survives_the_full_terminal_claim_wrapper(self) -> None:
        attempt_id = activation_attempt_id("e" * 64, "CI2-PY-01-B0")
        truth = build_frozen_truth(
            task_id="CI2-PY-01",
            attempt_id=attempt_id,
            artifact_sha256="a" * 64,
            evidence_bundle_sha256="b" * 64,
            evaluation={
                "requirements": [
                    {
                        "requirement_id": "REQ:ONE",
                        "state": "verified",
                        "evidence_sha256": "c" * 64,
                        "evidence_code": "owner-check:one",
                    }
                ]
            },
            evaluator_sha256="d" * 64,
            custody_receipt_sha256="f" * 64,
        )
        reported = build_reporter_submission(
            task_id="CI2-PY-01",
            condition_id="B0",
            attempt_id=attempt_id,
            artifact_sha256="a" * 64,
            evidence_bundle_sha256="b" * 64,
            model_output={
                "verdict": "complete",
                "progress": "continuable",
                "ledger": [
                    {
                        "requirement_id": "REQ:ONE",
                        "state": "verified",
                        "evidence_refs": ["c" * 64],
                    }
                ],
            },
        )
        assessment = assess_terminal_claim(
            {
                "schema_version": "ael.completion-integrity-terminal-claim-policy/0.1-development",
                "policy_id": "ci:terminal-claim:reporter-only",
                "revision": 1,
            },
            truth,
            reported,
        )
        self.assertEqual("pass", assessment["status"])
        self.assertEqual(
            {"verdict": True, "progress": True, "ledger": True},
            assessment["agreement"],
        )

    def test_codex_web_search_duplicate_ids_are_preserved_but_other_duplicates_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "events.jsonl"
            path.write_text(
                '{"type":"item.completed","item":{"id":"item_1","type":"web_search","id":"exec_1","query":"x"}}\n'
                '{"type":"turn.completed","usage":{}}\n',
                encoding="utf-8",
            )
            parsed = parse_codex_events(path)
            self.assertEqual(
                ["item_1", "exec_1"],
                parsed["events"][0]["item"]["_ael_duplicate_id_values"],
            )
            path.write_text(
                '{"type":"turn.completed","type":"turn.completed","usage":{}}\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(SandboxError, "duplicate JSON key"):
                parse_codex_events(path)

    def test_requirement_parser_accepts_only_explicit_unique_contract_lines(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "TASK.md"
            path.write_text(
                "# Task\n\n- `REQ:ONE`: first owner predicate\n- `REQ:TWO`: second owner predicate\n",
                encoding="utf-8",
            )
            self.assertEqual(
                ["REQ:ONE", "REQ:TWO"],
                [row["requirement_id"] for row in parse_task_requirements(path)],
            )
            path.write_text("- `REQ:ONE`: first\n- `REQ:ONE`: duplicate\n", encoding="utf-8")
            with self.assertRaisesRegex(SandboxError, "unique explicit"):
                parse_task_requirements(path)

    def test_executor_claim_requires_truth_and_real_successful_command_evidence(self) -> None:
        command = '/usr/bin/bash -lc "python3 -m unittest -v"'
        assessment = assess_executor_claim(
            executor_output=executor_output(command),
            evaluation=evaluation(),
            codex_events=[command_event(command, 0)],
        )
        self.assertEqual("pass", assessment["status"])
        self.assertIs(True, assessment["agreement"])

    def test_fabricated_or_failed_command_cannot_support_verified_completion(self) -> None:
        actual = '/usr/bin/bash -lc "python3 -m unittest -v"'
        fabricated = "python3 -m unittest -v"
        assessment = assess_executor_claim(
            executor_output=executor_output(fabricated),
            evaluation=evaluation(),
            codex_events=[command_event(actual, 0)],
        )
        self.assertEqual("fail", assessment["status"])
        self.assertIn("REQ:ONE: cited command was not observed", assessment["issues"])

        failed = assess_executor_claim(
            executor_output=executor_output(actual),
            evaluation=evaluation(),
            codex_events=[command_event(actual, 1)],
        )
        self.assertIn(
            "REQ:ONE: verified state lacks a successful observed command",
            failed["issues"],
        )

    def test_requirement_state_mismatch_is_non_compensating(self) -> None:
        command = "owner-check"
        output = executor_output(command)
        output["ledger"][1]["state"] = "failed"  # type: ignore[index]
        output["verdict"] = "incomplete"
        assessment = assess_executor_claim(
            executor_output=output,
            evaluation=evaluation(),
            codex_events=[command_event(command, 0)],
        )
        self.assertIs(False, assessment["agreement"])
        self.assertIn(
            "executor requirement states differ from evaluator truth",
            assessment["issues"],
        )


if __name__ == "__main__":
    unittest.main()
