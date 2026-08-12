from __future__ import annotations

import re
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from ael.sandbox import SandboxError, tree_sha256
from ael.validation import sha256_path

SOURCE_LOCK_SCHEMA_VERSION = "ael.source-lock/0.1-dev"
SOURCE_STATES = {"metadata_registered", "quarantined", "verified_snapshot", "excluded"}
PUBLIC_REFERENCE_STATES = {"allowed", "blocked"}
HOSTED_EXECUTION_STATES = {"blocked", "maintainer_controlled_only", "eligible"}
OFFLINE_EXECUTION_STATES = {"requires_quarantine_gate", "eligible", "blocked"}
_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_GIT_REVISION = re.compile(r"^[a-f0-9]{40}$")


@dataclass(frozen=True)
class SourceLockIssue:
    location: str
    message: str

    def __str__(self) -> str:
        return f"{self.location}: {self.message}"


def load_source_lock(path: Path) -> dict[str, Any]:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise SandboxError(f"source lock is not readable TOML: {exc}") from exc
    if not isinstance(data, dict):
        raise SandboxError("source lock must be a TOML table")
    return data


def _relative_source_path(value: object) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts and "." not in path.parts


def _contains_symlink(path: Path) -> bool:
    candidate = path.absolute()
    while True:
        if candidate.is_symlink():
            return True
        parent = candidate.parent
        if parent == candidate:
            return False
        candidate = parent


def validate_source_lock(data: dict[str, Any]) -> list[SourceLockIssue]:
    issues: list[SourceLockIssue] = []
    if data.get("schema_version") != SOURCE_LOCK_SCHEMA_VERSION:
        issues.append(SourceLockIssue("schema_version", f"must equal {SOURCE_LOCK_SCHEMA_VERSION}"))
    if not isinstance(data.get("lock_id"), str) or not data.get("lock_id"):
        issues.append(SourceLockIssue("lock_id", "must be a non-empty string"))
    sources = data.get("sources")
    if not isinstance(sources, list) or not sources:
        issues.append(SourceLockIssue("sources", "must contain at least one source"))
        return issues

    identifiers: set[str] = set()
    for index, source in enumerate(sources):
        location = f"sources.{index}"
        if not isinstance(source, dict):
            issues.append(SourceLockIssue(location, "must be a table"))
            continue
        source_id = source.get("source_id")
        if not isinstance(source_id, str) or not source_id:
            issues.append(SourceLockIssue(f"{location}.source_id", "must be non-empty"))
        elif source_id in identifiers:
            issues.append(SourceLockIssue(f"{location}.source_id", "must be unique"))
        else:
            identifiers.add(source_id)
        repository = source.get("repository")
        if not isinstance(repository, str) or not repository.startswith("https://github.com/"):
            issues.append(
                SourceLockIssue(
                    f"{location}.repository", "must be an explicit https://github.com URL"
                )
            )
        if not _GIT_REVISION.fullmatch(str(source.get("revision", ""))):
            issues.append(SourceLockIssue(f"{location}.revision", "must be a 40-hex Git commit"))
        if not _relative_source_path(source.get("path")):
            issues.append(
                SourceLockIssue(f"{location}.path", "must be a normalized relative POSIX path")
            )
        if not _SHA256.fullmatch(str(source.get("tree_sha256", ""))):
            issues.append(SourceLockIssue(f"{location}.tree_sha256", "must be 64 lowercase hex"))
        if not _relative_source_path(source.get("license_path")):
            issues.append(
                SourceLockIssue(
                    f"{location}.license_path", "must be a normalized relative POSIX path"
                )
            )
        if not _SHA256.fullmatch(str(source.get("license_sha256", ""))):
            issues.append(SourceLockIssue(f"{location}.license_sha256", "must be 64 lowercase hex"))
        if not isinstance(source.get("declared_license"), str) or not source.get(
            "declared_license"
        ):
            issues.append(
                SourceLockIssue(f"{location}.declared_license", "must be a non-empty string")
            )
        if source.get("source_state") not in SOURCE_STATES:
            issues.append(
                SourceLockIssue(
                    f"{location}.source_state", f"must be one of {sorted(SOURCE_STATES)}"
                )
            )
        if source.get("public_reference") not in PUBLIC_REFERENCE_STATES:
            issues.append(
                SourceLockIssue(
                    f"{location}.public_reference",
                    f"must be one of {sorted(PUBLIC_REFERENCE_STATES)}",
                )
            )
        if source.get("hosted_model_execution") not in HOSTED_EXECUTION_STATES:
            issues.append(
                SourceLockIssue(
                    f"{location}.hosted_model_execution",
                    f"must be one of {sorted(HOSTED_EXECUTION_STATES)}",
                )
            )
        if source.get("offline_execution") not in OFFLINE_EXECUTION_STATES:
            issues.append(
                SourceLockIssue(
                    f"{location}.offline_execution",
                    f"must be one of {sorted(OFFLINE_EXECUTION_STATES)}",
                )
            )
        if (
            source.get("source_state") == "metadata_registered"
            and source.get("hosted_model_execution") == "eligible"
        ):
            issues.append(
                SourceLockIssue(
                    f"{location}.hosted_model_execution",
                    "metadata-only registration cannot be hosted-execution eligible",
                )
            )
        if source.get("public_reference") == "blocked" and not source.get("block_reason"):
            issues.append(
                SourceLockIssue(
                    f"{location}.block_reason", "is required when public reference is blocked"
                )
            )
    return issues


def source_by_id(data: dict[str, Any], source_id: str) -> dict[str, Any]:
    matches = [item for item in data.get("sources", []) if item.get("source_id") == source_id]
    if len(matches) != 1:
        raise SandboxError(f"source_id must resolve exactly once: {source_id}")
    return matches[0]


def verify_checkout(source: dict[str, Any], checkout: Path) -> dict[str, str]:
    if checkout.is_symlink():
        raise SandboxError("source checkout must not be a symlink")
    checkout = checkout.resolve()
    if not checkout.is_dir():
        raise SandboxError(f"source checkout is unavailable: {checkout}")
    revision = subprocess.run(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    if revision.returncode != 0:
        raise SandboxError("source checkout is not a readable Git worktree")
    actual_revision = revision.stdout.strip()
    if actual_revision != source["revision"]:
        raise SandboxError(
            f"source revision mismatch: expected {source['revision']}, observed {actual_revision}"
        )
    source_root = checkout / source["path"]
    if _contains_symlink(source_root):
        raise SandboxError("locked source path and its existing parents must not be symlinks")
    if not source_root.is_dir():
        raise SandboxError(f"locked source path is unavailable: {source['path']}")
    actual_tree = tree_sha256(source_root)
    if actual_tree != source["tree_sha256"]:
        raise SandboxError(
            f"source tree mismatch: expected {source['tree_sha256']}, observed {actual_tree}"
        )
    license_path = checkout / source["license_path"]
    if _contains_symlink(license_path) or not license_path.is_file():
        raise SandboxError(f"license evidence is unavailable: {source['license_path']}")
    actual_license = sha256_path(license_path)
    if actual_license != source["license_sha256"]:
        raise SandboxError(
            "license evidence mismatch: "
            f"expected {source['license_sha256']}, observed {actual_license}"
        )
    return {
        "source_id": str(source["source_id"]),
        "revision": actual_revision,
        "tree_sha256": actual_tree,
        "license_path": str(source["license_path"]),
        "license_sha256": actual_license,
        "verification": "pass",
    }
