from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ael.codex_events import audit_skill_activation
from ael.sandbox import SandboxError


class CodexEventTests(unittest.TestCase):
    def write_events(self, root: Path, events: list[dict[str, object]]) -> Path:
        path = root / "events.jsonl"
        path.write_text("".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")
        return path

    def test_successful_completed_retrieval_is_activation_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = self.write_events(
                root,
                [
                    {
                        "type": "item.completed",
                        "item": {
                            "id": "item-1",
                            "type": "command_execution",
                            "command": "sed -n 1,200p /workspace/home/.codex/skills/example-skill/SKILL.md",
                            "aggregated_output": "# Example skill\n",
                            "exit_code": 0,
                            "status": "completed",
                        },
                    }
                ],
            )
            result = audit_skill_activation(path, "example-skill")
            self.assertTrue(result["activated"])
            self.assertEqual(1, len(result["matched_commands"]))

    def test_string_mentions_and_started_commands_are_not_activation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = self.write_events(
                root,
                [
                    {
                        "type": "item.completed",
                        "item": {
                            "id": "message-1",
                            "type": "agent_message",
                            "text": "/home/.codex/skills/example-skill/SKILL.md",
                        },
                    },
                    {
                        "type": "item.started",
                        "item": {
                            "id": "item-1",
                            "type": "command_execution",
                            "command": "cat /home/.codex/skills/example-skill/SKILL.md",
                            "aggregated_output": "",
                            "exit_code": None,
                            "status": "in_progress",
                        },
                    },
                ],
            )
            result = audit_skill_activation(path, "example-skill")
            self.assertFalse(result["activated"])

    def test_failed_or_empty_retrieval_is_not_activation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = self.write_events(
                root,
                [
                    {
                        "type": "item.completed",
                        "item": {
                            "id": "item-1",
                            "type": "command_execution",
                            "command": "cat /home/.codex/skills/example-skill/SKILL.md",
                            "aggregated_output": "not found",
                            "exit_code": 1,
                            "status": "failed",
                        },
                    },
                    {
                        "type": "item.completed",
                        "item": {
                            "id": "item-2",
                            "type": "command_execution",
                            "command": "cat /home/.codex/skills/example-skill/SKILL.md",
                            "aggregated_output": "",
                            "exit_code": 0,
                            "status": "completed",
                        },
                    },
                ],
            )
            result = audit_skill_activation(path, "example-skill")
            self.assertFalse(result["activated"])

    def test_symlinked_event_input_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = self.write_events(root, [])
            link = root / "linked.jsonl"
            link.symlink_to(target)
            with self.assertRaisesRegex(SandboxError, "non-symlink"):
                audit_skill_activation(link, "example-skill")

    def test_echo_and_compound_shell_mentions_are_not_activation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = self.write_events(
                root,
                [
                    {
                        "type": "item.completed",
                        "item": {
                            "id": "item-1",
                            "type": "command_execution",
                            "command": "echo /home/.codex/skills/example-skill/SKILL.md",
                            "aggregated_output": "fake skill content",
                            "exit_code": 0,
                            "status": "completed",
                        },
                    },
                    {
                        "type": "item.completed",
                        "item": {
                            "id": "item-2",
                            "type": "command_execution",
                            "command": "bash -lc 'cat unrelated; echo /home/.codex/skills/example-skill/SKILL.md'",
                            "aggregated_output": "fake skill content",
                            "exit_code": 0,
                            "status": "completed",
                        },
                    },
                ],
            )
            result = audit_skill_activation(path, "example-skill")
            self.assertFalse(result["activated"])

    def test_successful_and_chain_may_contain_exact_read_segment(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = self.write_events(
                root,
                [
                    {
                        "type": "item.completed",
                        "item": {
                            "id": "item-1",
                            "type": "command_execution",
                            "command": "bash -lc 'pwd && sed -n 1,200p /home/.codex/skills/example-skill/SKILL.md && sed -n 1,80p TASK.md'",
                            "aggregated_output": "/workspace\n# Example skill\n# Task\n",
                            "exit_code": 0,
                            "status": "completed",
                        },
                    }
                ],
            )
            result = audit_skill_activation(path, "example-skill")
            self.assertTrue(result["activated"])


if __name__ == "__main__":
    unittest.main()
