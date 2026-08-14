"""Safe, deterministic boundary primitives for public result projection.

This module owns filesystem and JSON trust checks.  Projection policy and
rendering depend on it; it does not depend on either of them.  Keeping this
boundary in one place prevents every new public facet from inventing its own
path, hash, symlink, or non-finite-number behavior.
"""

from __future__ import annotations

import datetime as _datetime
import json
import math
import re
import stat
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, NoReturn
from urllib.parse import urlparse

from ael.sandbox import SandboxError
from ael.validation import MAX_JSON_BYTES, sha256_path

_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")


class ResultSurfaceError(SandboxError):
    """Raised when a result profile or its source graph is unsafe."""


def fail(message: str) -> NoReturn:
    raise ResultSurfaceError(message)


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate object member: {key}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise ValueError(f"non-finite JSON number: {value}")


def _strict_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"non-finite JSON number: {value}")
    return parsed


def load_json_object(path: Path) -> dict[str, Any]:
    regular_file(path, "JSON source")
    if path.stat().st_size > MAX_JSON_BYTES:
        fail(f"JSON source exceeds {MAX_JSON_BYTES} bytes: {path}")
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_strict_object,
            parse_constant=_reject_nonfinite,
            parse_float=_strict_float,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        fail(f"JSON source is unreadable: {path}: {exc}")
    if not isinstance(value, dict):
        fail(f"JSON source must contain an object: {path}")
    return value


def regular_file(path: Path, label: str) -> None:
    """Require a regular non-symlink file, including every parent component."""

    candidate = Path(path)
    absolute = candidate.absolute()
    if contains_symlink(absolute):
        fail(f"{label} must not use symlinks: {path}")
    try:
        info = absolute.lstat()
    except OSError as exc:
        fail(f"{label} does not exist: {path}: {exc}")
    if not stat.S_ISREG(info.st_mode):
        fail(f"{label} must be a regular file: {path}")


def regular_directory(path: Path, label: str) -> None:
    absolute = Path(path).absolute()
    if contains_symlink(absolute):
        fail(f"{label} must not use symlinks: {path}")
    try:
        info = absolute.lstat()
    except OSError as exc:
        fail(f"{label} does not exist: {path}: {exc}")
    if not stat.S_ISDIR(info.st_mode):
        fail(f"{label} must be a directory: {path}")


def contains_symlink(path: Path) -> bool:
    candidate = Path(path).absolute()
    while True:
        try:
            if candidate.is_symlink():
                return True
        except OSError:
            return True
        parent = candidate.parent
        if parent == candidate:
            return False
        candidate = parent


def repository_root(profile_path: Path, explicit: Path | None) -> Path:
    if explicit is not None:
        regular_directory(explicit, "repository root")
        root = Path(explicit).resolve()
    else:
        start = Path(profile_path).absolute()
        for candidate in (start.parent, *start.parents):
            if (candidate / "pyproject.toml").is_file() and not contains_symlink(
                candidate / "pyproject.toml"
            ):
                root = candidate.resolve()
                break
        else:
            fail("could not locate repository root with pyproject.toml")
    profile_resolved = Path(profile_path).resolve()
    if not profile_resolved.is_relative_to(root):
        fail("result-catalog profile must be inside the repository root")
    return root


def require_keys(
    value: Mapping[str, Any], required: set[str], optional: set[str], location: str
) -> None:
    unknown = set(value) - required - optional
    missing = required - set(value)
    if unknown:
        fail(f"{location} contains unknown key(s): {', '.join(sorted(unknown))}")
    if missing:
        fail(f"{location} is missing required key(s): {', '.join(sorted(missing))}")


def nonempty_string(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        fail(f"{location} must be a non-empty string")
    return value


def sha(value: Any, location: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        fail(f"{location} must be 64 lowercase hexadecimal characters")
    return value


def validate_date(value: Any, location: str) -> str:
    date = nonempty_string(value, location)
    if _DATE.fullmatch(date) is None:
        fail(f"{location} must use YYYY-MM-DD")
    try:
        _datetime.date.fromisoformat(date)
    except ValueError:
        fail(f"{location} is not a calendar date: {date}")
    return date


def local_reference(
    owner: Path,
    reference: Mapping[str, Any],
    repository: Path,
    location: str,
    *,
    dereference: bool = True,
    strict: bool = True,
) -> tuple[Path | None, str]:
    if not isinstance(reference, Mapping):
        fail(f"{location} must be an object")
    if strict:
        require_keys(reference, {"uri", "sha256"}, set(), location)
    elif "uri" not in reference or "sha256" not in reference:
        fail(f"{location} requires uri and sha256")
    uri = nonempty_string(reference.get("uri"), f"{location}.uri")
    digest = sha(reference.get("sha256"), f"{location}.sha256")
    parsed = urlparse(uri)
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment or uri.startswith("/"):
        fail(f"{location}.uri must be a repository-relative path")
    if "\\" in uri or "\x00" in uri:
        fail(f"{location}.uri contains an unsafe path character")
    if not parsed.path or parsed.path == ".":
        fail(f"{location}.uri must identify a file")
    candidate = owner.parent / parsed.path
    if contains_symlink(candidate):
        fail(f"{location}.uri must not use symlinks")
    target = candidate.resolve()
    if not target.is_relative_to(repository):
        fail(f"{location}.uri escapes repository root")
    if not dereference:
        return None, digest
    regular_file(target, f"{location} target")
    actual = sha256_path(target)
    if actual != digest:
        fail(f"{location}.sha256 does not match {target}")
    return target, digest


def relative_path(path: Path, repository: Path) -> str:
    try:
        return path.resolve().relative_to(repository).as_posix()
    except ValueError as exc:
        fail(f"source path is outside repository root: {path}")
        raise AssertionError from exc


@dataclass
class SourceLedger:
    """Single owner for every dereferenced byte in a public projection."""

    repository_root: Path
    _hashes: dict[str, str] = field(default_factory=dict)

    def add(self, path: Path, digest: str | None = None) -> str:
        regular_file(path, "projection source")
        relative = relative_path(path, self.repository_root)
        actual = sha256_path(path)
        if digest is not None and actual != digest:
            fail(f"source digest does not match {path}")
        previous = self._hashes.get(relative)
        if previous is not None and previous != actual:
            fail(f"projection source changed during materialization: {relative}")
        self._hashes[relative] = actual
        return actual

    def resolve(
        self,
        owner: Path,
        reference: Mapping[str, Any],
        location: str,
        *,
        strict: bool = True,
    ) -> tuple[Path, str]:
        target, digest = local_reference(
            owner,
            reference,
            self.repository_root,
            location,
            strict=strict,
        )
        assert target is not None
        self.add(target, digest)
        return target, digest

    def projected_ref(
        self,
        owner: Path,
        reference: Mapping[str, Any],
        location: str,
    ) -> dict[str, str]:
        target, digest = self.resolve(owner, reference, location)
        return {"uri": relative_path(target, self.repository_root), "sha256": digest}

    def add_tree(self, root: Path, label: str) -> int:
        """Account for one complete public bundle without following links."""

        regular_directory(root, label)
        count = 0
        for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
            if contains_symlink(path):
                fail(f"{label} must not contain symlinks: {path}")
            try:
                info = path.lstat()
            except OSError as exc:
                fail(f"{label} entry is unreadable: {path}: {exc}")
            if stat.S_ISDIR(info.st_mode):
                continue
            if not stat.S_ISREG(info.st_mode):
                fail(f"{label} must contain only directories and regular files: {path}")
            self.add(path)
            count += 1
        return count

    def snapshot(self) -> dict[str, str]:
        return dict(sorted(self._hashes.items()))
