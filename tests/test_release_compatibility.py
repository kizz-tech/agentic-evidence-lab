from __future__ import annotations

import hashlib
import io
import json
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path

from tools.check_frozen_artifacts import (
    DEFAULT_ANCHORS,
    DEFAULT_LOCKS,
    DEFAULT_RELEASED_GRAPH_LOCK,
    PUBLIC_RESULTS_COMMIT,
    PUBLIC_RESULTS_PROFILE,
    PUBLIC_RESULTS_TAG,
    FrozenLock,
    GitAnchor,
    ReleasedGraphLock,
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


def _temporary_public_repository(
    root: Path,
    *,
    mutate: callable | None = None,
) -> ReleasedGraphLock:
    """Create a detached alpha.11 fixture with the real tagged public graph."""

    archive = subprocess.run(
        ["git", "archive", "v0.1.0-alpha.11"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    with tarfile.open(fileobj=io.BytesIO(archive.stdout), mode="r:") as source:
        source.extractall(root)
    if mutate is not None:
        mutate(root)
    _git(root, "init", "--quiet")
    _git(root, "config", "user.email", "tests@example.invalid")
    _git(root, "config", "user.name", "Release compatibility tests")
    _git(root, "add", ".")
    _git(root, "commit", "--quiet", "-m", "alpha.11 fixture")
    _git(root, "tag", PUBLIC_RESULTS_TAG)
    commit = subprocess.run(
        ["git", "rev-parse", f"refs/tags/{PUBLIC_RESULTS_TAG}^{{commit}}"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return ReleasedGraphLock(PUBLIC_RESULTS_TAG, commit, PUBLIC_RESULTS_PROFILE)


def _public_graph_check(root: Path, lock: ReleasedGraphLock) -> list[str]:
    return check_frozen_artifacts(root, (), (), lock)


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
        self.assertEqual(PUBLIC_RESULTS_TAG, DEFAULT_RELEASED_GRAPH_LOCK.source_tag)
        self.assertEqual(PUBLIC_RESULTS_COMMIT, DEFAULT_RELEASED_GRAPH_LOCK.expected_commit)
        self.assertEqual(PUBLIC_RESULTS_PROFILE, DEFAULT_RELEASED_GRAPH_LOCK.profile_path)

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

    def test_alpha11_public_graph_current_bytes_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture_root = Path(temporary)
            lock = _temporary_public_repository(fixture_root)

            self.assertEqual([], _public_graph_check(fixture_root, lock))

    def test_alpha11_protects_activation_and_released_result_decisions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture_root = Path(temporary)
            lock = _temporary_public_repository(fixture_root)
            changed_paths = (
                "studies/completion-integrity/activation-v2/results/decision.json",
                "studies/completion-integrity/results/prompt-policy-v1/effect-decision.json",
                "studies/agent-skills-season-1/results/systematic-debugging-real-shadow-v1/effect-decision.json",
                "studies/completion-integrity/concept.json",
                "studies/completion-integrity/activation-v2/study-manifest.json",
            )
            for relative in changed_paths:
                path = fixture_root / relative
                path.write_bytes(path.read_bytes() + b"\nmutated")

            failures = _public_graph_check(fixture_root, lock)

        for relative in changed_paths:
            self.assertTrue(
                any("byte mismatch" in failure and relative in failure for failure in failures),
                relative,
            )

    def test_alpha11_profile_tag_membership_is_authoritative(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture_root = Path(temporary)
            lock = _temporary_public_repository(fixture_root)
            profile_path = fixture_root / PUBLIC_RESULTS_PROFILE
            profile = json.loads(profile_path.read_text())
            profile["studies"][0]["verification"]["result_root"] = "current-only-root"
            profile_path.write_text(json.dumps(profile, indent=2) + "\n")
            (fixture_root / "current-only-root").mkdir()
            (fixture_root / "current-only-root" / "new.json").write_bytes(b"current only")
            failures = _public_graph_check(fixture_root, lock)

        self.assertEqual([], failures)

    def test_alpha11_current_profile_can_add_next_release_card(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture_root = Path(temporary)
            lock = _temporary_public_repository(fixture_root)
            profile_path = fixture_root / PUBLIC_RESULTS_PROFILE
            profile = json.loads(profile_path.read_text())
            profile["studies"].append(
                {
                    "card_id": "next-release-card",
                    "receipt_ref": {
                        "uri": "studies/next-release/results/evidence-receipt.json",
                        "sha256": "0" * 64,
                    },
                    "report_ref": {
                        "uri": "reports/next-release.md",
                        "sha256": "0" * 64,
                    },
                }
            )
            profile_path.write_text(json.dumps(profile, indent=2) + "\n")

            self.assertEqual([], _public_graph_check(fixture_root, lock))

    def test_alpha11_added_file_under_old_result_root_is_not_locked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture_root = Path(temporary)
            lock = _temporary_public_repository(fixture_root)
            added = (
                fixture_root
                / "studies"
                / "completion-integrity"
                / "activation-v2"
                / "results"
                / "current-projection.json"
            )
            added.write_bytes(b"current projection")

            self.assertEqual([], _public_graph_check(fixture_root, lock))

    def test_alpha11_unsafe_and_missing_refs_fail_closed(self) -> None:
        def unsafe_profile(root: Path) -> None:
            profile_path = root / PUBLIC_RESULTS_PROFILE
            profile = json.loads(profile_path.read_text())
            profile["studies"][0]["report_ref"] = {
                "uri": "../outside-report.md",
                "sha256": hashlib.sha256(b"outside").hexdigest(),
            }
            profile_path.write_text(json.dumps(profile, indent=2) + "\n")

        with tempfile.TemporaryDirectory() as temporary:
            fixture_root = Path(temporary)
            unsafe_lock = _temporary_public_repository(fixture_root, mutate=unsafe_profile)
            unsafe_failures = _public_graph_check(fixture_root, unsafe_lock)
        self.assertTrue(any("unsafe tag public-results" in failure for failure in unsafe_failures))

        def missing_ref(root: Path) -> None:
            (root / "reports" / "2026-08-15-completion-integrity-activation-v2.md").unlink()

        with tempfile.TemporaryDirectory() as temporary:
            fixture_root = Path(temporary)
            missing_lock = _temporary_public_repository(fixture_root, mutate=missing_ref)
            missing_failures = _public_graph_check(fixture_root, missing_lock)
        self.assertTrue(
            any("source tag path unavailable" in failure for failure in missing_failures)
        )

    def test_alpha11_moved_tag_fails_anchor_check(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture_root = Path(temporary)
            lock = _temporary_public_repository(fixture_root)
            moved_path = (
                fixture_root
                / "studies"
                / "completion-integrity"
                / "activation-v2"
                / "results"
                / "decision.json"
            )
            original_bytes = moved_path.read_bytes()
            moved_path.write_bytes(original_bytes + b"\ntag moved")
            _git(fixture_root, "add", str(moved_path.relative_to(fixture_root)))
            _git(fixture_root, "commit", "--quiet", "-m", "move tag")
            _git(fixture_root, "tag", "--force", PUBLIC_RESULTS_TAG)
            moved_path.write_bytes(original_bytes)

            failures = _public_graph_check(fixture_root, lock)

        self.assertTrue(any("released graph anchor mismatch" in failure for failure in failures))
        self.assertFalse(any("byte mismatch" in failure for failure in failures))

    def test_alpha11_tagged_receipt_hash_mismatch_fails_closed(self) -> None:
        def mutate_receipt(root: Path) -> None:
            receipt_path = (
                root
                / "studies"
                / "completion-integrity"
                / "activation-v2"
                / "results"
                / "evidence-receipt.json"
            )
            receipt = json.loads(receipt_path.read_text())
            receipt["measurement_set_ref"]["sha256"] = "0" * 64
            receipt_bytes = (json.dumps(receipt, indent=2) + "\n").encode()
            receipt_path.write_bytes(receipt_bytes)

            profile_path = root / PUBLIC_RESULTS_PROFILE
            profile = json.loads(profile_path.read_text())
            profile["studies"][0]["receipt_ref"]["sha256"] = hashlib.sha256(
                receipt_bytes
            ).hexdigest()
            profile_path.write_text(json.dumps(profile, indent=2) + "\n")

        with tempfile.TemporaryDirectory() as temporary:
            fixture_root = Path(temporary)
            lock = _temporary_public_repository(fixture_root, mutate=mutate_receipt)
            failures = _public_graph_check(fixture_root, lock)

        self.assertTrue(
            any(
                "tag hash mismatch" in failure
                and "studies/completion-integrity/activation-v2/results/measurement-set.json"
                in failure
                for failure in failures
            )
        )


if __name__ == "__main__":
    unittest.main()
