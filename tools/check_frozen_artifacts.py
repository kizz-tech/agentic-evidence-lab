"""Compare released evidence blobs with their source Git tag bytes.

This guard deliberately keeps a small, explicit path allowlist.  It does not
maintain a second checksum registry and does not lock shared implementation
source forever: the study audit and freeze checks own executable bindings,
while this tool protects released evidence and Contract v0 schema bytes that
the release promises unchanged.

The alpha.11 public-results graph is derived from the *tagged* profile.  The
working tree can therefore project a later view of a result without changing
which historical evidence bytes the compatibility guard protects.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_RESULTS_TAG = "v0.1.0-alpha.11"
PUBLIC_RESULTS_PROFILE = "studies/public-results.json"
PUBLIC_RESULTS_COMMIT = "35a5ad9e3a25553f2be9a28a8b0dd1bca928df70"

# These limits keep a malformed or unexpectedly large tagged profile/tree from
# turning a release check into an unbounded parser or subprocess result.  They
# are deliberately generous for the current six-card profile.
MAX_PUBLIC_RESULTS_PROFILE_BYTES = 1_048_576
MAX_PUBLIC_RESULTS_PROFILE_NODES = 16_384
MAX_PUBLIC_RESULTS_PROFILE_MEMBERS = 32_768
MAX_PUBLIC_RESULT_TREE_MEMBERS = 4_096
MAX_PUBLIC_RESULT_TREE_BYTES = 8_388_608

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


@dataclass(frozen=True)
class ReleasedGraphLock:
    """One immutable tag/profile contract for a released public graph."""

    source_tag: str
    expected_commit: str
    profile_path: str


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
DEFAULT_RELEASED_GRAPH_LOCK = ReleasedGraphLock(
    PUBLIC_RESULTS_TAG,
    PUBLIC_RESULTS_COMMIT,
    PUBLIC_RESULTS_PROFILE,
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
    if "\x00" in relative or "\n" in relative or "\r" in relative or "\\" in relative:
        return False
    path = PurePosixPath(relative)
    return (
        bool(relative)
        and not path.is_absolute()
        and str(path) == relative
        and all(part not in {"", ".", ".."} for part in path.parts)
    )


def _valid_tag(root: Path, source_tag: str) -> bool:
    if not source_tag or "\x00" in source_tag or "\n" in source_tag or "\r" in source_tag:
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


def _verify_released_graph_lock(root: Path, lock: ReleasedGraphLock, failures: list[str]) -> None:
    """Verify the graph tag's exact peeled commit before reading its profile."""

    if not _valid_tag(root, lock.source_tag):
        failures.append(f"invalid released graph tag declaration: {lock.source_tag!r}")
        return
    if len(lock.expected_commit) != 40 or any(
        character not in "0123456789abcdef" for character in lock.expected_commit
    ):
        failures.append(f"invalid released graph commit declaration: {lock.expected_commit!r}")
        return
    if not _valid_relative_path(lock.profile_path):
        failures.append(f"invalid released graph profile declaration: {lock.profile_path!r}")
        return
    resolved = _git(
        root,
        "rev-parse",
        "--verify",
        "--quiet",
        f"refs/tags/{lock.source_tag}^{{commit}}",
    )
    if resolved is None or resolved.returncode != 0:
        failures.append(
            f"released graph tag unavailable: {lock.source_tag} ({_git_error(resolved)})"
        )
        return
    actual = resolved.stdout.decode("ascii", errors="replace").strip()
    if actual != lock.expected_commit:
        failures.append(
            f"released graph anchor mismatch: {lock.source_tag} resolves to {actual}, "
            f"expected {lock.expected_commit}"
        )


def _tag_tree_entry(
    root: Path,
    source_tag: str,
    relative: str,
    *,
    source_revision: str | None = None,
) -> tuple[str, str] | None:
    """Return ``(mode, type)`` for one exact tag path, or ``None`` if absent.

    ``git cat-file -t`` reports a symlink as a blob, so the tree mode is also
    checked to keep source-tag symlinks from being treated as regular files.
    Paths are passed after ``--`` and are validated before this helper is used.
    """

    revision = source_revision or source_tag
    result = _git(root, "ls-tree", "-z", revision, "--", relative)
    if result is None or result.returncode != 0:
        return None
    for record in result.stdout.split(b"\0"):
        if not record:
            continue
        try:
            header, path_bytes = record.split(b"\t", 1)
            mode_bytes, type_bytes, _object_id = header.split()
            path = path_bytes.decode("utf-8")
            mode = mode_bytes.decode("ascii")
            object_type = type_bytes.decode("ascii")
        except (UnicodeDecodeError, ValueError):
            return None
        if path == relative:
            return mode, object_type
    return None


def _tag_blob_bytes(
    root: Path,
    source_tag: str,
    relative: str,
    failures: list[str],
    *,
    max_bytes: int | None = None,
    source_revision: str | None = None,
) -> bytes | None:
    """Read one regular file blob from a tag, recording fail-closed errors."""

    if not _valid_relative_path(relative):
        failures.append(f"invalid locked path declaration: {relative!r}")
        return None

    revision = source_revision or source_tag
    object_ref = f"{revision}:{relative}"
    object_type = _git(root, "cat-file", "-t", object_ref)
    if object_type is None or object_type.returncode != 0:
        failures.append(
            f"source tag path unavailable: {source_tag}:{relative} ({_git_error(object_type)})"
        )
        return None

    metadata = _tag_tree_entry(root, source_tag, relative, source_revision=revision)
    if metadata is None:
        failures.append(f"source tag path unavailable: {source_tag}:{relative}")
        return None
    mode, tree_type = metadata
    if tree_type != "blob" or object_type.stdout.strip() != b"blob":
        kind = tree_type or object_type.stdout.decode("utf-8", errors="replace").strip()
        failures.append(
            f"source tag path is not a file blob: {source_tag}:{relative} ({kind or 'unknown'})"
        )
        return None
    if mode.startswith("12"):
        failures.append(f"source tag path is a symlink: {source_tag}:{relative}")
        return None

    source = _git(root, "show", "--format=", "--no-ext-diff", object_ref)
    if source is None or source.returncode != 0:
        failures.append(
            f"source tag blob unavailable: {source_tag}:{relative} ({_git_error(source)})"
        )
        return None
    if max_bytes is not None and len(source.stdout) > max_bytes:
        failures.append(
            f"tag file exceeds bounded size: {source_tag}:{relative} "
            f"({len(source.stdout)} > {max_bytes} bytes)"
        )
        return None
    return source.stdout


def _has_symlink_component(root: Path, current: Path) -> bool:
    """Return whether a locked path or one of its parent components is a link."""

    try:
        relative_parts = current.relative_to(root).parts
    except ValueError:
        return True
    candidate = root
    for part in relative_parts:
        candidate /= part
        try:
            if candidate.is_symlink():
                return True
        except OSError:
            return True
    return False


def _bounded_profile(value: object) -> str | None:
    """Validate bounded JSON shape and return an error, if any."""

    pending: list[object] = [value]
    nodes = 0
    members = 0
    while pending:
        item = pending.pop()
        nodes += 1
        if nodes > MAX_PUBLIC_RESULTS_PROFILE_NODES:
            return (
                "tag public-results profile exceeds bounded JSON node count "
                f"({MAX_PUBLIC_RESULTS_PROFILE_NODES})"
            )
        if isinstance(item, dict):
            members += len(item)
            if members > MAX_PUBLIC_RESULTS_PROFILE_MEMBERS:
                return (
                    "tag public-results profile exceeds bounded JSON member count "
                    f"({MAX_PUBLIC_RESULTS_PROFILE_MEMBERS})"
                )
            pending.extend(item.values())
        elif isinstance(item, list):
            members += len(item)
            if members > MAX_PUBLIC_RESULTS_PROFILE_MEMBERS:
                return (
                    "tag public-results profile exceeds bounded JSON member count "
                    f"({MAX_PUBLIC_RESULTS_PROFILE_MEMBERS})"
                )
            pending.extend(item)
    return None


def _tag_public_results_profile(
    root: Path,
    source_tag: str,
    profile_path: str,
    failures: list[str],
    *,
    source_revision: str | None = None,
) -> dict[str, object] | None:
    profile_bytes = _tag_blob_bytes(
        root,
        source_tag,
        profile_path,
        failures,
        max_bytes=MAX_PUBLIC_RESULTS_PROFILE_BYTES,
        source_revision=source_revision,
    )
    if profile_bytes is None:
        return None
    try:
        profile_text = profile_bytes.decode("utf-8")
        profile = json.loads(profile_text)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        failures.append(f"tag public-results profile is invalid JSON: {exc}")
        return None
    bounded_error = _bounded_profile(profile)
    if bounded_error:
        failures.append(bounded_error)
        return None
    if not isinstance(profile, dict):
        failures.append("tag public-results profile must be a JSON object")
        return None
    studies = profile.get("studies")
    if not isinstance(studies, list):
        failures.append("tag public-results profile has no studies array")
        return None
    return profile


def _tag_tree_files(
    root: Path,
    source_tag: str,
    result_root: str,
    failures: list[str],
    *,
    source_revision: str | None = None,
) -> tuple[str, ...]:
    """List regular files in one tag-owned result tree, with hard bounds."""

    if not _valid_relative_path(result_root):
        failures.append(f"invalid public result root declaration: {result_root!r}")
        return ()
    revision = source_revision or source_tag
    root_ref = f"{revision}:{result_root}"
    root_type = _git(root, "cat-file", "-t", root_ref)
    if root_type is None or root_type.returncode != 0:
        failures.append(f"source result root unavailable: {source_tag}:{result_root}")
        return ()
    if root_type.stdout.strip() != b"tree":
        kind = root_type.stdout.decode("utf-8", errors="replace").strip() or "unknown"
        failures.append(f"source result root is not a tree: {source_tag}:{result_root} ({kind})")
        return ()

    listing = _git(root, "ls-tree", "-r", "-z", revision, "--", result_root)
    if listing is None or listing.returncode != 0:
        failures.append(
            f"source result tree unavailable: {source_tag}:{result_root} ({_git_error(listing)})"
        )
        return ()
    if len(listing.stdout) > MAX_PUBLIC_RESULT_TREE_BYTES:
        failures.append(
            f"source result tree exceeds bounded bytes: {source_tag}:{result_root} "
            f"({len(listing.stdout)} > {MAX_PUBLIC_RESULT_TREE_BYTES})"
        )
        return ()

    paths: list[str] = []
    seen: set[str] = set()
    path_bytes = 0
    for record in listing.stdout.split(b"\0"):
        if not record:
            continue
        if len(paths) >= MAX_PUBLIC_RESULT_TREE_MEMBERS:
            failures.append(
                f"source result tree exceeds bounded member count: {source_tag}:{result_root} "
                f"({MAX_PUBLIC_RESULT_TREE_MEMBERS})"
            )
            return tuple(paths)
        try:
            header, path_bytes_value = record.split(b"\t", 1)
            mode_bytes, type_bytes, _object_id = header.split()
            relative = path_bytes_value.decode("utf-8")
            mode = mode_bytes.decode("ascii")
            object_type = type_bytes.decode("ascii")
        except (UnicodeDecodeError, ValueError):
            failures.append(f"malformed source result tree entry: {source_tag}:{result_root}")
            continue
        if not _valid_relative_path(relative):
            failures.append(f"unsafe source result tree path: {relative!r}")
            continue
        if relative != result_root and not relative.startswith(f"{result_root}/"):
            failures.append(f"source result tree path escapes root: {source_tag}:{relative}")
            continue
        if relative in seen:
            failures.append(f"duplicate source result tree path: {source_tag}:{relative}")
            continue
        seen.add(relative)
        path_bytes += len(path_bytes_value)
        if path_bytes > MAX_PUBLIC_RESULT_TREE_BYTES:
            failures.append(
                f"source result tree exceeds bounded path bytes: {source_tag}:{result_root} "
                f"({path_bytes} > {MAX_PUBLIC_RESULT_TREE_BYTES})"
            )
            return tuple(paths)
        if object_type != "blob" or mode.startswith("12"):
            failures.append(
                f"source result tree member is not a regular file: {source_tag}:{relative}"
            )
            continue
        paths.append(relative)
    if not paths:
        failures.append(f"source result tree has no tracked files: {source_tag}:{result_root}")
    return tuple(paths)


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _add_public_ref(
    value: object,
    label: str,
    paths: dict[str, None],
    expected_hashes: dict[str, str],
    failures: list[str],
) -> str | None:
    """Validate and register one public URI/SHA-256 reference."""

    if not isinstance(value, dict):
        failures.append(f"tag public-results {label} is not a reference object")
        return None
    relative = value.get("uri")
    digest = value.get("sha256")
    if not isinstance(relative, str) or not _valid_relative_path(relative):
        failures.append(f"unsafe tag public-results {label} URI: {relative!r}")
        return None
    if not isinstance(digest, str) or _SHA256_RE.fullmatch(digest) is None:
        failures.append(f"invalid tag public-results {label} SHA-256: {digest!r}")
        return None
    previous = expected_hashes.get(relative)
    if previous is not None and previous != digest:
        failures.append(f"conflicting tag public-results hashes for {relative}")
    expected_hashes[relative] = digest
    paths.setdefault(relative, None)
    return relative


def _add_public_result_root(
    value: object,
    label: str,
    roots: dict[str, None],
    failures: list[str],
) -> str | None:
    if not isinstance(value, str) or not _valid_relative_path(value):
        failures.append(f"unsafe tag public-results {label}: {value!r}")
        return None
    roots.setdefault(value, None)
    return value


def _resolve_receipt_uri(
    receipt_path: str, uri: object, label: str, failures: list[str]
) -> str | None:
    """Resolve one Contract reference URI relative to its tagged receipt."""

    if not isinstance(uri, str) or "\x00" in uri or "\n" in uri or "\r" in uri:
        failures.append(f"unsafe tag receipt {label} URI: {uri!r}")
        return None
    if uri.startswith("/") or "\\" in uri:
        failures.append(f"unsafe tag receipt {label} URI: {uri!r}")
        return None
    components = list(PurePosixPath(receipt_path).parent.parts)
    for part in uri.split("/"):
        if part in {"", "."}:
            failures.append(f"unsafe tag receipt {label} URI: {uri!r}")
            return None
        if part == "..":
            if not components:
                failures.append(f"unsafe tag receipt {label} URI: {uri!r}")
                return None
            components.pop()
        else:
            components.append(part)
    resolved = "/".join(components)
    if not _valid_relative_path(resolved):
        failures.append(f"unsafe tag receipt {label} URI: {uri!r}")
        return None
    return resolved


def _add_receipt_ref(
    receipt_path: str,
    value: object,
    label: str,
    paths: dict[str, None],
    expected_hashes: dict[str, str],
    failures: list[str],
) -> str | None:
    if not isinstance(value, dict):
        failures.append(f"tag receipt {label} is not a reference object")
        return None
    relative = _resolve_receipt_uri(receipt_path, value.get("uri"), label, failures)
    if relative is None:
        return None
    return _add_public_ref(
        {"uri": relative, "sha256": value.get("sha256")},
        f"receipt.{label}",
        paths,
        expected_hashes,
        failures,
    )


def _add_tagged_receipt_contract_refs(
    root: Path,
    lock: ReleasedGraphLock,
    receipt_path: str,
    paths: dict[str, None],
    expected_hashes: dict[str, str],
    failures: list[str],
) -> None:
    """Read one tagged receipt and add its public Contract-v0 graph refs."""

    receipt_bytes = _tag_blob_bytes(
        root,
        lock.source_tag,
        receipt_path,
        failures,
        max_bytes=MAX_PUBLIC_RESULTS_PROFILE_BYTES,
        source_revision=lock.expected_commit,
    )
    if receipt_bytes is None:
        return
    try:
        receipt = json.loads(receipt_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        failures.append(f"tag receipt is invalid JSON: {receipt_path}: {exc}")
        return
    if not isinstance(receipt, dict):
        failures.append(f"tag receipt is not a JSON object: {receipt_path}")
        return

    for field in ("concept_ref", "study_ref", "measurement_set_ref"):
        if field not in receipt:
            failures.append(f"tag receipt missing {field}: {receipt_path}")
            continue
        _add_receipt_ref(
            receipt_path,
            receipt[field],
            field,
            paths,
            expected_hashes,
            failures,
        )

    run_refs = receipt.get("run_record_refs")
    if not isinstance(run_refs, list):
        failures.append(f"tag receipt run_record_refs is not an array: {receipt_path}")
        return
    for index, run_ref in enumerate(run_refs):
        _add_receipt_ref(
            receipt_path,
            run_ref,
            f"run_record_refs[{index}]",
            paths,
            expected_hashes,
            failures,
        )


def _public_results_paths(
    root: Path, lock: ReleasedGraphLock, failures: list[str]
) -> tuple[tuple[str, ...], dict[str, str]]:
    """Derive the alpha.11 protected graph exclusively from tagged JSON/tree data."""

    profile = _tag_public_results_profile(
        root,
        lock.source_tag,
        lock.profile_path,
        failures,
        source_revision=lock.expected_commit,
    )
    if profile is None:
        return (), {}
    studies = profile.get("studies")
    if not isinstance(studies, list):  # guarded by _tag_public_results_profile
        return (), {}

    paths: dict[str, None] = {}
    expected_hashes: dict[str, str] = {}
    roots: dict[str, None] = {}

    for index, card in enumerate(studies):
        label = f"study[{index}]"
        if not isinstance(card, dict):
            failures.append(f"tag public-results {label} is not an object")
            continue

        receipt_uri = _add_public_ref(
            card.get("receipt_ref"), f"{label}.receipt_ref", paths, expected_hashes, failures
        )
        if receipt_uri is not None:
            _add_tagged_receipt_contract_refs(
                root,
                lock,
                receipt_uri,
                paths,
                expected_hashes,
                failures,
            )
        _add_public_ref(
            card.get("report_ref"), f"{label}.report_ref", paths, expected_hashes, failures
        )

        verification = card.get("verification")
        if verification is not None and not isinstance(verification, dict):
            failures.append(f"tag public-results {label}.verification is not an object")
            verification = {}
        if not isinstance(verification, dict):
            verification = {}

        freeze_ref = verification.get("freeze_ref")
        if verification.get("kind") == "frozen_public_bundle" and freeze_ref is None:
            failures.append(f"tag public-results {label} is missing verification.freeze_ref")
        if freeze_ref is not None:
            _add_public_ref(
                freeze_ref,
                f"{label}.verification.freeze_ref",
                paths,
                expected_hashes,
                failures,
            )

        result_root = verification.get("result_root")
        if result_root is not None:
            _add_public_result_root(
                result_root, f"{label}.verification.result_root", roots, failures
            )
        elif receipt_uri is not None:
            # Contract result cards predate ``verification.result_root``.  Their
            # receipt's parent is a bounded, tag-owned graph root.
            receipt_parent = str(PurePosixPath(receipt_uri).parent)
            _add_public_result_root(
                receipt_parent, f"{label}.receipt_ref parent result root", roots, failures
            )

        quality = card.get("quality")
        if quality is not None and not isinstance(quality, dict):
            failures.append(f"tag public-results {label}.quality is not an object")
            quality = {}
        if isinstance(quality, dict) and quality.get("profile_ref") is not None:
            _add_public_ref(
                quality.get("profile_ref"),
                f"{label}.quality.profile_ref",
                paths,
                expected_hashes,
                failures,
            )

        materials = card.get("materials")
        if materials is not None and not isinstance(materials, list):
            failures.append(f"tag public-results {label}.materials is not an array")
            materials = []
        if isinstance(materials, list):
            for material_index, material in enumerate(materials):
                if not isinstance(material, dict):
                    failures.append(
                        f"tag public-results {label}.materials[{material_index}] is not an object"
                    )
                    continue
                if "ref" in material:
                    _add_public_ref(
                        material.get("ref"),
                        f"{label}.materials[{material_index}].ref",
                        paths,
                        expected_hashes,
                        failures,
                    )

        lifecycle = card.get("lifecycle")
        if lifecycle is not None and not isinstance(lifecycle, dict):
            failures.append(f"tag public-results {label}.lifecycle is not an object")
            lifecycle = {}
        if isinstance(lifecycle, dict):
            for lifecycle_key, lifecycle_value in lifecycle.items():
                if lifecycle_key.endswith("_ref"):
                    _add_public_ref(
                        lifecycle_value,
                        f"{label}.lifecycle.{lifecycle_key}",
                        paths,
                        expected_hashes,
                        failures,
                    )

    # Result-root membership comes from ``git ls-tree`` at the immutable tag;
    # additions in the current checkout are intentionally not enumerated.
    for result_root in roots:
        for relative in _tag_tree_files(
            root,
            lock.source_tag,
            result_root,
            failures,
            source_revision=lock.expected_commit,
        ):
            paths.setdefault(relative, None)

    return tuple(paths), expected_hashes


def _compare_tag_path(
    root: Path,
    source_tag: str,
    relative: str,
    failures: list[str],
    *,
    expected_hash: str | None = None,
    source_revision: str | None = None,
) -> None:
    source_bytes = _tag_blob_bytes(
        root,
        source_tag,
        relative,
        failures,
        source_revision=source_revision,
    )
    if source_bytes is None:
        return

    current = root / Path(*PurePosixPath(relative).parts)
    if _has_symlink_component(root, current):
        failures.append(f"current locked path unavailable: {relative}")
        return
    try:
        current_is_file = current.is_file()
    except OSError as exc:
        failures.append(f"current locked path unavailable: {relative}: {exc}")
        return
    if not current_is_file:
        failures.append(f"current locked path unavailable: {relative}")
        return

    if expected_hash is not None:
        source_hash = hashlib.sha256(source_bytes).hexdigest()
        if source_hash != expected_hash:
            failures.append(
                f"tag hash mismatch: {relative} differs from declared SHA-256 "
                f"for source tag {source_tag}"
            )
    try:
        current_bytes = current.read_bytes()
    except OSError as exc:
        failures.append(f"current locked path unavailable: {relative}: {exc}")
        return
    if current_bytes != source_bytes:
        failures.append(f"byte mismatch: {relative} differs from source tag {source_tag}")


def check_frozen_artifacts(
    root: Path,
    locks: Sequence[FrozenLock] = DEFAULT_LOCKS,
    anchors: Sequence[GitAnchor] = DEFAULT_ANCHORS,
    released_graph: ReleasedGraphLock | None = None,
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

    # Keep the historical custom-lock API lightweight while making the default
    # release graph's tag/commit/profile contract impossible to omit.
    if released_graph is None and locks == DEFAULT_LOCKS:
        released_graph = DEFAULT_RELEASED_GRAPH_LOCK

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
            _compare_tag_path(root, lock.source_tag, relative, failures)

    if released_graph is not None:
        _verify_released_graph_lock(root, released_graph, failures)
        graph_paths, expected_hashes = _public_results_paths(root, released_graph, failures)
        for relative in graph_paths:
            _compare_tag_path(
                root,
                released_graph.source_tag,
                relative,
                failures,
                expected_hash=expected_hashes.get(relative),
                source_revision=released_graph.expected_commit,
            )

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify released evidence graph bytes against immutable Git tags."
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
    graph_paths, _ = _public_results_paths(args.root.resolve(), DEFAULT_RELEASED_GRAPH_LOCK, [])
    comparisons += len(graph_paths)
    print(
        "frozen artifact check passed: "
        f"{comparisons} tag/path comparisons; {len(DEFAULT_ANCHORS)} Git anchor"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
