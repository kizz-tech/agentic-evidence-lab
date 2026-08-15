from __future__ import annotations

import unittest

from ael.codex_reporter import reporter_command
from ael.sandbox import SandboxError


class CodexReporterCommandTests(unittest.TestCase):
    def test_reporter_is_ephemeral_read_only_and_schema_bound(self) -> None:
        command = reporter_command("gpt-5.6-sol", "xhigh", prompt="Report from evidence.")
        self.assertIn("--ephemeral", command)
        self.assertEqual("read-only", command[command.index("--sandbox") + 1])
        self.assertEqual(
            "/fixture/reporter-output-schema.json",
            command[command.index("--output-schema") + 1],
        )
        self.assertEqual(
            "/output/reporter-submission.json",
            command[command.index("--output-last-message") + 1],
        )
        self.assertNotIn("danger-full-access", command)
        self.assertNotIn("resume", command)

    def test_reporter_rejects_empty_or_unknown_runtime_inputs(self) -> None:
        with self.assertRaises(SandboxError):
            reporter_command("", "xhigh", prompt="x")
        with self.assertRaises(SandboxError):
            reporter_command("gpt-5.6-sol", "unsupported", prompt="x")
        with self.assertRaises(SandboxError):
            reporter_command("gpt-5.6-sol", "xhigh", prompt=" ")


if __name__ == "__main__":
    unittest.main()
