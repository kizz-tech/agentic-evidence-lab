from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import tempfile
from pathlib import Path
from typing import Any

from ael.completion_integrity_task_supply import assess_pack
from ael.sandbox import SandboxError

PRIVATE_CANARY_PREFIX = "AEL-HIDDEN-" + "CANARY:CI10-"
IGNORED_PUBLIC_PARTS = {".git", ".venv", "__pycache__", "build", "dist"}


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number is forbidden: {value}")


def _reject_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"non-finite JSON number is forbidden: {value}")
    return parsed


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise SandboxError(f"required JSON file is missing or unsafe: {path}")
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=_reject_constant,
            parse_float=_reject_float,
            object_pairs_hook=_pairs,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise SandboxError(f"cannot read strict JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SandboxError(f"JSON root must be an object: {path}")
    return value


def _safe_member(root: Path, relative: str) -> Path:
    if not relative or "\\" in relative:
        raise SandboxError(f"unsafe private-pack path: {relative!r}")
    raw = Path(relative)
    if raw.is_absolute() or any(part in {"", ".", ".."} for part in raw.parts):
        raise SandboxError(f"unsafe private-pack path: {relative!r}")
    candidate = root / raw
    cursor = root
    for part in raw.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise SandboxError(f"private-pack path contains a symlink: {relative}")
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise SandboxError(f"private-pack path escapes its root: {relative}")
    return candidate


def _artifact_digest(path: Path) -> str:
    if path.is_symlink() or not path.exists():
        raise SandboxError(f"bound artifact is missing or unsafe: {path}")
    digest = hashlib.sha256()
    if path.is_file():
        return hashlib.sha256(path.read_bytes()).hexdigest()
    if not path.is_dir():
        raise SandboxError(f"bound artifact must be a regular file or directory: {path}")
    members = sorted(path.rglob("*"), key=lambda member: member.relative_to(path).as_posix())
    if not members:
        raise SandboxError(f"bound artifact directory is empty: {path}")
    for member in members:
        if member.is_symlink():
            raise SandboxError(f"bound artifact tree contains a symlink: {member}")
        relative = member.relative_to(path).as_posix().encode("utf-8")
        if member.is_dir():
            digest.update(b"D\0" + relative + b"\0")
        elif member.is_file():
            digest.update(b"F\0" + relative + b"\0")
            digest.update(hashlib.sha256(member.read_bytes()).digest())
        else:
            raise SandboxError(f"bound artifact tree contains a special entry: {member}")
    return digest.hexdigest()


def _verify_artifacts(task_root: Path, dossier: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for artifact in dossier.get("artifacts", []):
        if not isinstance(artifact, dict) or not isinstance(artifact.get("path"), str):
            continue
        try:
            path = _safe_member(task_root, artifact["path"])
            observed = _artifact_digest(path)
        except SandboxError as exc:
            issues.append(str(exc))
            continue
        if observed != artifact.get("sha256"):
            issues.append(
                f"{dossier.get('task_id')}: artifact hash mismatch for {artifact['path']}"
            )
    return issues


def _scan_public_boundary(private_root: Path, public_root: Path) -> list[str]:
    private_real = private_root.resolve()
    public_real = public_root.resolve()
    if private_real == public_real or private_real.is_relative_to(public_real):
        raise SandboxError("private task supply must live outside the public repository")
    private_hashes = {
        hashlib.sha256(path.read_bytes()).hexdigest()
        for path in private_root.rglob("*")
        if path.is_file() and not path.is_symlink()
    }
    issues: list[str] = []
    for path in sorted(public_root.rglob("*")):
        if IGNORED_PUBLIC_PARTS.intersection(path.parts):
            continue
        if path.is_symlink():
            issues.append(f"public tree contains a symlink during private-boundary scan: {path}")
            continue
        if not path.is_file():
            continue
        payload = path.read_bytes()
        relative = path.relative_to(public_root).as_posix()
        if PRIVATE_CANARY_PREFIX.encode("utf-8") in payload:
            issues.append(f"private canary leaked into public tree: {relative}")
        if hashlib.sha256(payload).hexdigest() in private_hashes:
            issues.append(f"exact private file leaked into public tree: {relative}")
    return issues


def check_supply(root: Path, *, public_root: Path | None = None) -> dict[str, Any]:
    root = root.absolute()
    if root.is_symlink() or not root.is_dir():
        raise SandboxError("private task-supply root is missing or unsafe")
    canary = root / ".ael-private-canary"
    if canary.is_symlink() or not canary.is_file():
        raise SandboxError("private task supply lacks its canary")
    if PRIVATE_CANARY_PREFIX not in canary.read_text(encoding="utf-8"):
        raise SandboxError("private task supply has an unsupported canary")

    pack = _load_json(root / "pack.json")
    entries = pack.get("tasks")
    if not isinstance(entries, list) or not entries:
        raise SandboxError("task supply must list at least one candidate")
    tasks: list[dict[str, Any]] = []
    adapter_issues: list[str] = []
    seen_paths: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise SandboxError("every task-supply entry needs task_id and path")
        relative = entry["path"]
        if relative in seen_paths:
            raise SandboxError(f"duplicate task-supply path: {relative}")
        seen_paths.add(relative)
        task_root = _safe_member(root, relative)
        dossier = _load_json(task_root / "dossier.json")
        if entry.get("task_id") != dossier.get("task_id"):
            adapter_issues.append(f"task entry and dossier identity differ: {relative}")
        adapter_issues.extend(_verify_artifacts(task_root, dossier))
        tasks.append(dossier)

    assessment = assess_pack(pack, tasks)
    if public_root is not None:
        adapter_issues.extend(_scan_public_boundary(root, public_root.absolute()))
    if adapter_issues:
        assessment["issues"] = [*assessment["issues"], *adapter_issues]
        assessment["status"] = "fail"
    assessment["private_pack_sha256"] = _artifact_digest(root)
    assessment["public_boundary_checked"] = public_root is not None
    return assessment


def _write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path = path.absolute()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _require_external_output(root: Path, output: Path) -> None:
    root_real = root.absolute().resolve()
    output_real = output.absolute().resolve()
    if output_real == root_real or output_real.is_relative_to(root_real):
        raise SandboxError("assessment output must remain outside the immutable private-pack root")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check a private Completion Integrity task-supply pack"
    )
    parser.add_argument("root", type=Path)
    parser.add_argument("--public-root", type=Path)
    parser.add_argument("--json-output", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        assessment = check_supply(args.root, public_root=args.public_root)
        if args.json_output:
            _require_external_output(args.root, args.json_output)
    except SandboxError as exc:
        print(f"task-supply check failed: {exc}")
        return 1
    if args.json_output:
        _write_json_atomic(args.json_output, assessment)
    print(
        "task-supply check "
        f"{assessment['status']}: candidates={assessment['candidate_roots']} "
        f"scored={assessment['scored_roots']} issues={len(assessment['issues'])}"
    )
    for issue in assessment["issues"]:
        print(f"- {issue}")
    return 0 if assessment["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
