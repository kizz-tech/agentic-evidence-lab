from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.check_frozen_artifacts import (
    DEFAULT_ANCHORS,
    DEFAULT_LOCKS,
    FrozenLock,
    GitAnchor,
    check_frozen_artifacts,
)

ROOT = Path(__file__).resolve().parents[1]
PBT_FREEZE = (
    ROOT
    / "studies"
    / "agent-skills-season-1"
    / "screening"
    / "property-based-testing-v2.freeze.json"
)


def _git(root: Path, *arguments: str) -> None:
    subprocess.run(["git", *arguments], cwd=root, check=True, capture_output=True)


def _temporary_repository(root: Path) -> FrozenLock:
    (root / "freeze.json").write_bytes(b"freeze\x00bytes\n")
    (root / "results" / "decision.json").parent.mkdir(parents=True)
    (root / "results" / "decision.json").write_bytes(b"result bytes\n")
    _git(root, "init", "--quiet")
    _git(root, "config", "user.email", "tests@example.invalid")
    _git(root, "config", "user.name", "Release compatibility tests")
    _git(root, "add", "freeze.json", "results/decision.json")
    _git(root, "commit", "--quiet", "-m", "fixture")
    _git(root, "tag", "fixture-release")
    return FrozenLock("fixture-release", ("freeze.json", "results/decision.json"))


class ReleaseCompatibilityTests(unittest.TestCase):
    def test_current_release_bytes_match_alpha_tags(self) -> None:
        self.assertEqual([], check_frozen_artifacts(ROOT))

    def test_mutation_fails_without_touching_actual_evidence(self) -> None:
        before = PBT_FREEZE.read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            fixture_root = Path(temporary)
            lock = _temporary_repository(fixture_root)
            (fixture_root / "results" / "decision.json").write_bytes(b"mutated\n")

            failures = check_frozen_artifacts(fixture_root, (lock,), ())

        self.assertTrue(any("byte mismatch" in failure for failure in failures))
        self.assertEqual(before, PBT_FREEZE.read_bytes())

    def test_missing_tag_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture_root = Path(temporary)
            lock = _temporary_repository(fixture_root)
            missing_tag = FrozenLock("does-not-exist", lock.paths)

            failures = check_frozen_artifacts(fixture_root, (missing_tag,), ())

        self.assertTrue(any("source tag unavailable" in failure for failure in failures))

    def test_missing_tag_path_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture_root = Path(temporary)
            lock = _temporary_repository(fixture_root)
            missing_path = FrozenLock(lock.source_tag, (*lock.paths, "results/missing.json"))

            failures = check_frozen_artifacts(fixture_root, (missing_path,), ())

        self.assertTrue(any("source tag path unavailable" in failure for failure in failures))

    def test_default_locks_are_explicit_and_do_not_use_directory_globs(self) -> None:
        self.assertEqual(3, len(DEFAULT_LOCKS))
        for lock in DEFAULT_LOCKS[:2]:
            self.assertEqual(15, len(lock.paths))
            self.assertTrue(all("*" not in path and "?" not in path for path in lock.paths))
        self.assertEqual("v0.1.0-alpha.5", DEFAULT_LOCKS[2].source_tag)
        self.assertEqual(5, len(DEFAULT_LOCKS[2].paths))
        self.assertTrue(all("*" not in path and "?" not in path for path in DEFAULT_LOCKS[2].paths))

        self.assertEqual(
            (
                GitAnchor(
                    "property-based-testing-v2-freeze",
                    "610f0d9e1e19d9c89dd6beba8fab7900222df5dd",
                ),
            ),
            DEFAULT_ANCHORS,
        )

    def test_anchor_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture_root = Path(temporary)
            lock = _temporary_repository(fixture_root)
            wrong_anchor = GitAnchor(lock.source_tag, "0" * 40)

            failures = check_frozen_artifacts(fixture_root, (), (wrong_anchor,))

        self.assertTrue(any("anchor mismatch" in failure for failure in failures))


if __name__ == "__main__":
    unittest.main()
