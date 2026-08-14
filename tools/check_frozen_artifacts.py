"""Compare released evidence blobs with their source Git tag bytes.

This guard deliberately keeps a small, explicit path allowlist.  It does not
maintain a second checksum registry and does not lock shared implementation
source forever: the study audit and freeze checks own executable bindings,
while this tool protects released PBT evidence and the five Contract v0 schema
bytes that alpha.8 promises unchanged.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
PBT_FREEZE = "studies/agent-skills-season-1/screening/property-based-testing-v2.freeze.json"
PBT_RESULT_PATHS = (
    "studies/agent-skills-season-1/results/property-based-testing-v2/decision.json",
    "studies/agent-skills-season-1/results/property-based-testing-v2/evidence-receipt.json",
    "studies/agent-skills-season-1/results/property-based-testing-v2/evidence-receipt.md",
    "studies/agent-skills-season-1/results/property-based-testing-v2/freeze-ref.json",
    "studies/agent-skills-season-1/results/property-based-testing-v2/measurement-set.json",
    "studies/agent-skills-season-1/results/property-based-testing-v2/runs/P-S01-B0-R01.json",
    "studies/agent-skills-season-1/results/property-based-testing-v2/runs/P-S01-S1-R01.json",
    "studies/agent-skills-season-1/results/property-based-testing-v2/runs/P-S02-B0-R01.json",
    "studies/agent-skills-season-1/results/property-based-testing-v2/runs/P-S02-S1-R01.json",
    "studies/agent-skills-season-1/results/property-based-testing-v2/runs/P-S03-B0-R01.json",
    "studies/agent-skills-season-1/results/property-based-testing-v2/runs/P-S03-S1-R01.json",
    "studies/agent-skills-season-1/results/property-based-testing-v2/runs/P-S04-B0-R01.json",
    "studies/agent-skills-season-1/results/property-based-testing-v2/runs/P-S04-S1-R01.json",
    "studies/agent-skills-season-1/results/property-based-testing-v2/screening-decision.json",
)
PBT_FROZEN_PATHS = (PBT_FREEZE, *PBT_RESULT_PATHS)
CONTRACT_SCHEMA_PATHS = (
    "src/ael/schemas/concept.schema.json",
    "src/ael/schemas/study-manifest.schema.json",
    "src/ael/schemas/run-record.schema.json",
    "src/ael/schemas/measurement-set.schema.json",
    "src/ael/schemas/evidence-receipt.schema.json",
)


@dataclass(frozen=True)
class FrozenLock:
    """A source tag and the exact released paths it is authoritative for."""

    source_tag: str
    paths: tuple[str, ...]


@dataclass(frozen=True)
class GitAnchor:
    """A human-readable tag that must resolve to one exact commit."""

    tag: str
    commit: str


# Alpha.4 did not add or change any PBT freeze/result paths.  Keep one explicit
# lock per release tag so a later release can add a path without silently
# turning a directory glob into a compatibility promise.
DEFAULT_LOCKS: tuple[FrozenLock, ...] = (
    FrozenLock("v0.1.0-alpha.3", PBT_FROZEN_PATHS),
    FrozenLock("v0.1.0-alpha.4", PBT_FROZEN_PATHS),
    FrozenLock("v0.1.0-alpha.5", CONTRACT_SCHEMA_PATHS),
)
DEFAULT_ANCHORS: tuple[GitAnchor, ...] = (
    GitAnchor(
        "property-based-testing-v2-freeze",
        "610f0d9e1e19d9c89dd6beba8fab7900222df5dd",
    ),
)


def _git(root: Path, *arguments: str) -> subprocess.CompletedProcess[bytes] | None:
    try:
        return subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=False,
            capture_output=True,
        )
    except OSError:
        return None


def _git_error(result: subprocess.CompletedProcess[bytes] | None) -> str:
    if result is None:
        return "git executable is unavailable"
    detail = result.stderr.decode("utf-8", errors="replace").strip()
    return detail or f"git exited with status {result.returncode}"


def _valid_relative_path(relative: str) -> bool:
    path = PurePosixPath(relative)
    return (
        bool(relative)
        and not path.is_absolute()
        and all(part not in {"", ".", ".."} for part in path.parts)
    )


def _valid_tag(root: Path, source_tag: str) -> bool:
    if not source_tag or "\x00" in source_tag or "\n" in source_tag:
        return False
    result = _git(root, "check-ref-format", f"refs/tags/{source_tag}")
    return result is not None and result.returncode == 0


def _root_error(root: Path) -> list[str]:
    if not root.exists() or not root.is_dir():
        return [f"repository unavailable: root is not a directory: {root}"]
    result = _git(root, "rev-parse", "--show-toplevel")
    if result is None or result.returncode != 0:
        return [f"repository unavailable at {root}: {_git_error(result)}"]
    reported_root = Path(result.stdout.decode("utf-8", errors="replace").strip()).resolve()
    if reported_root != root.resolve():
        return [f"repository root mismatch: expected {root.resolve()}, git reports {reported_root}"]
    return []


def check_frozen_artifacts(
    root: Path,
    locks: Sequence[FrozenLock] = DEFAULT_LOCKS,
    anchors: Sequence[GitAnchor] = DEFAULT_ANCHORS,
) -> list[str]:
    """Return all failures comparing current files with declared Git tags.

    Both the tag and every path are checked before bytes are read.  A missing
    tag, missing tag path, unavailable current path, non-regular entry, or
    mismatched byte sequence is a failure; no fallback to another revision is
    attempted.
    """

    root = root.resolve()
    failures = _root_error(root)
    if failures:
        return failures

    for anchor in anchors:
        if not _valid_tag(root, anchor.tag):
            failures.append(f"invalid anchor tag declaration: {anchor.tag!r}")
            continue
        if len(anchor.commit) != 40 or any(
            character not in "0123456789abcdef" for character in anchor.commit
        ):
            failures.append(f"invalid anchor commit declaration: {anchor.commit!r}")
            continue
        resolved = _git(
            root, "rev-parse", "--verify", "--quiet", f"refs/tags/{anchor.tag}^{{commit}}"
        )
        if resolved is None or resolved.returncode != 0:
            failures.append(f"anchor tag unavailable: {anchor.tag} ({_git_error(resolved)})")
            continue
        actual = resolved.stdout.decode("ascii", errors="replace").strip()
        if actual != anchor.commit:
            failures.append(
                f"anchor mismatch: {anchor.tag} resolves to {actual}, expected {anchor.commit}"
            )

    for lock in locks:
        if not _valid_tag(root, lock.source_tag):
            failures.append(f"invalid source tag declaration: {lock.source_tag!r}")
            continue

        tag_ref = f"refs/tags/{lock.source_tag}^{{commit}}"
        tag_result = _git(root, "rev-parse", "--verify", "--quiet", tag_ref)
        if tag_result is None or tag_result.returncode != 0:
            failures.append(f"source tag unavailable: {lock.source_tag} ({_git_error(tag_result)})")
            continue

        for relative in lock.paths:
            if not _valid_relative_path(relative):
                failures.append(f"invalid locked path declaration: {relative!r}")
                continue

            object_ref = f"{lock.source_tag}:{relative}"
            object_type = _git(root, "cat-file", "-t", object_ref)
            if object_type is None or object_type.returncode != 0:
                failures.append(
                    f"source tag path unavailable: {lock.source_tag}:{relative} "
                    f"({_git_error(object_type)})"
                )
                continue

            current = root / Path(*PurePosixPath(relative).parts)
            try:
                current_is_symlink = current.is_symlink()
                current_is_file = current.is_file()
            except OSError as exc:
                failures.append(f"current locked path unavailable: {relative}: {exc}")
                continue
            if current_is_symlink or not current_is_file:
                failures.append(f"current locked path unavailable: {relative}")
                continue

            if object_type.stdout.strip() != b"blob":
                kind = object_type.stdout.decode("utf-8", errors="replace").strip() or "unknown"
                failures.append(
                    f"source tag path is not a file blob: {lock.source_tag}:{relative} ({kind})"
                )
                continue

            source = _git(root, "show", "--format=", "--no-ext-diff", object_ref)
            if source is None or source.returncode != 0:
                failures.append(
                    f"source tag blob unavailable: {lock.source_tag}:{relative} "
                    f"({_git_error(source)})"
                )
                continue
            try:
                current_bytes = current.read_bytes()
            except OSError as exc:
                failures.append(f"current locked path unavailable: {relative}: {exc}")
                continue
            if current_bytes != source.stdout:
                failures.append(
                    f"byte mismatch: {relative} differs from source tag {lock.source_tag}"
                )

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify released PBT evidence bytes against immutable Git tags."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="repository root (default: the repository containing this tool)",
    )
    args = parser.parse_args()
    failures = check_frozen_artifacts(args.root)
    if failures:
        print("frozen artifact check failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    comparisons = sum(len(lock.paths) for lock in DEFAULT_LOCKS)
    print(
        "frozen artifact check passed: "
        f"{comparisons} tag/path comparisons; {len(DEFAULT_ANCHORS)} Git anchor"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
