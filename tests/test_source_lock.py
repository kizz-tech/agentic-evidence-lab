from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from ael.sandbox import SandboxError, tree_sha256
from ael.source_lock import load_source_lock, source_by_id, validate_source_lock, verify_checkout
from ael.validation import sha256_path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "studies" / "agent-skills-season-1" / "sources.lock.toml"


class SourceLockTests(unittest.TestCase):
    def test_season_one_source_lock_is_valid(self) -> None:
        data = load_source_lock(LOCK)
        self.assertEqual([], [str(issue) for issue in validate_source_lock(data)])
        self.assertEqual(12, len(data["sources"]))

    def test_metadata_registration_cannot_claim_hosted_eligibility(self) -> None:
        data = load_source_lock(LOCK)
        data["sources"][0]["source_state"] = "metadata_registered"
        data["sources"][0]["hosted_model_execution"] = "eligible"
        self.assertTrue(
            any("metadata-only" in issue.message for issue in validate_source_lock(data))
        )

    def test_checkout_verification_checks_revision_tree_and_license(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            checkout = Path(temporary)
            subprocess.run(["git", "init", "-q", str(checkout)], check=True)
            subprocess.run(
                ["git", "-C", str(checkout), "config", "user.name", "AEL Test"], check=True
            )
            subprocess.run(
                ["git", "-C", str(checkout), "config", "user.email", "test@example.invalid"],
                check=True,
            )
            skill = checkout / "skills" / "demo"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("# Demo\n", encoding="utf-8")
            (checkout / "LICENSE").write_text("test license\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(checkout), "add", "."], check=True)
            subprocess.run(["git", "-C", str(checkout), "commit", "-qm", "fixture"], check=True)
            revision = subprocess.run(
                ["git", "-C", str(checkout), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            source = {
                "source_id": "fixture",
                "revision": revision,
                "path": "skills/demo",
                "tree_sha256": tree_sha256(skill),
                "license_path": "LICENSE",
                "license_sha256": sha256_path(checkout / "LICENSE"),
            }
            self.assertEqual("pass", verify_checkout(source, checkout)["verification"])
            (skill / "SKILL.md").write_text("# Changed\n", encoding="utf-8")
            with self.assertRaises(SandboxError):
                verify_checkout(source, checkout)

    def test_source_id_must_resolve_once(self) -> None:
        data = load_source_lock(LOCK)
        self.assertEqual(
            "superpowers-verification", source_by_id(data, "superpowers-verification")["source_id"]
        )


if __name__ == "__main__":
    unittest.main()
