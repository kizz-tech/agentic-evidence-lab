from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ael.cli import main
from ael.codex_runner import codex_command
from ael.sandbox import (
    SandboxError,
    _export_staged_output,
    _mount,
    _prepare_paths,
    _scan_exact_secret_values,
    _validate_cpu_value,
    _validate_image_reference,
    tree_sha256,
)


class SandboxPolicyTests(unittest.TestCase):
    def test_tree_hash_changes_with_file_content(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "input.txt"
            target.write_text("one\n", encoding="utf-8")
            before = tree_sha256(root)
            target.write_text("two\n", encoding="utf-8")
            self.assertNotEqual(before, tree_sha256(root))

    def test_tree_hash_rejects_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "target.txt").write_text("data\n", encoding="utf-8")
            (root / "link.txt").symlink_to(root / "target.txt")
            with self.assertRaises(SandboxError):
                tree_sha256(root)

    def test_output_must_be_empty_and_disjoint(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = root / "fixture"
            fixture.mkdir()
            with self.assertRaises(SandboxError):
                _prepare_paths(fixture, fixture / "output")
            output = root / "output"
            output.mkdir()
            (output / "existing.txt").write_text("occupied", encoding="utf-8")
            with self.assertRaises(SandboxError):
                _prepare_paths(fixture, output)

    def test_output_path_rejects_symlinked_parent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = root / "fixture"
            fixture.mkdir()
            actual = root / "actual"
            actual.mkdir()
            linked = root / "linked"
            linked.symlink_to(actual, target_is_directory=True)
            with self.assertRaises(SandboxError):
                _prepare_paths(fixture, linked / "output")

    def test_fixture_mount_is_explicitly_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            value = _mount(Path(temporary).resolve(), "/fixture", readonly=True)
        self.assertTrue(value.endswith(",readonly"))

    def test_staged_export_rejects_symlink_and_reserved_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            staging = root / "staging"
            output = root / "output"
            staging.mkdir()
            output.mkdir()
            (staging / "target.txt").write_text("data\n", encoding="utf-8")
            (staging / "link.txt").symlink_to(staging / "target.txt")
            with self.assertRaises(SandboxError):
                _export_staged_output(staging, output)
            (staging / "link.txt").unlink()
            (staging / "sandbox-invocation.json").write_text("{}\n", encoding="utf-8")
            with self.assertRaises(SandboxError):
                _export_staged_output(staging, output)
            self.assertEqual([], list(output.iterdir()))

    @patch("ael.sandbox.shutil.which", return_value=None)
    def test_doctor_fails_closed_without_docker(self, _which: object) -> None:
        from ael.sandbox import docker_doctor

        with self.assertRaises(SandboxError):
            docker_doctor()

    def test_codex_command_pins_noninteractive_policy(self) -> None:
        command = codex_command("gpt-5.6-sol", "xhigh")
        self.assertEqual(["codex", "exec"], command[:2])
        self.assertIn("--ephemeral", command)
        self.assertIn("--ignore-user-config", command)
        self.assertIn("danger-full-access", command)
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", command)

    def test_codex_cli_requires_trusted_input_acknowledgement(self) -> None:
        result = main(
            [
                "sandbox",
                "codex",
                "--fixture",
                "fixture",
                "--output",
                "output",
                "--auth-file",
                "auth.json",
            ]
        )
        self.assertEqual(2, result)

    def test_docker_cli_values_fail_closed(self) -> None:
        for image in ("--privileged", "valid/image:tag,readonly"):
            with self.subTest(image=image), self.assertRaises(SandboxError):
                _validate_image_reference(image)
        for cpus in ("0", "--privileged", "1,readonly"):
            with self.subTest(cpus=cpus), self.assertRaises(SandboxError):
                _validate_cpu_value(cpus)

    def test_secret_scan_reports_matches_without_exposing_values(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            auth = root / "auth.json"
            output = root / "output"
            output.mkdir()
            secret = "secret-value-that-is-long-enough"
            auth.write_text('{"token": "' + secret + '"}\n', encoding="utf-8")
            (output / "safe.txt").write_text("safe\n", encoding="utf-8")
            clean = _scan_exact_secret_values(output, auth)
            self.assertEqual(0, clean["exact_value_match_count"])
            (output / "leak.txt").write_bytes(b"x" * (1024 * 1024 - 10) + secret.encode("utf-8"))
            leaked = _scan_exact_secret_values(output, auth)
            self.assertEqual(["leak.txt"], leaked["files_with_matches"])
            self.assertNotIn(secret, str(leaked))


if __name__ == "__main__":
    unittest.main()
