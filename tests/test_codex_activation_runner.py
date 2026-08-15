from __future__ import annotations

import unittest

from ael.codex_activation_runner import activation_executor_command
from ael.sandbox import SandboxError


class CodexActivationRunnerTests(unittest.TestCase):
    def test_executor_is_ephemeral_and_schema_bound(self) -> None:
        command = activation_executor_command("gpt-5.6-sol", "xhigh", prompt="Do the task.")
        self.assertIn("--ephemeral", command)
        self.assertEqual(
            "/fixture/.ael/executor-output-schema.json",
            command[command.index("--output-schema") + 1],
        )
        self.assertEqual(
            "/workspace/repo/AEL_FINAL.json",
            command[command.index("--output-last-message") + 1],
        )
        self.assertNotIn("resume", command)

    def test_executor_validates_runtime_inputs(self) -> None:
        with self.assertRaises(SandboxError):
            activation_executor_command("", "xhigh", prompt="x")
        with self.assertRaises(SandboxError):
            activation_executor_command("gpt-5.6-sol", "unknown", prompt="x")
        with self.assertRaises(SandboxError):
            activation_executor_command("gpt-5.6-sol", "xhigh", prompt=" ")


if __name__ == "__main__":
    unittest.main()
