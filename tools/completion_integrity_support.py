"""Study-local I/O adapters shared by Completion Integrity operator tools."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ael.prospective_study import load_json_object
from ael.sandbox import DEFAULT_IMAGE, SandboxError, run_container

PRIVATE_CANARY_PREFIX = "AEL-HIDDEN-" + "CANARY:CI9-"
ATTEMPT_EVENT_FILES = {
    "prepared": "01-prepared.json",
    "submitted": "02-submitted.json",
    "terminal": "03-terminal.json",
    "ambiguous": "03-ambiguous.json",
}


def without_canary(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: child for key, child in value.items() if key != "_ael_private_canary"}


def read_pack(pack_root: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    pack_root = pack_root.absolute()
    if pack_root.is_symlink() or not pack_root.is_dir():
        raise SandboxError("Completion Integrity pack root is missing or unsafe")
    canary = pack_root / ".ael-private-canary"
    if not canary.is_file() or PRIVATE_CANARY_PREFIX not in canary.read_text(encoding="utf-8"):
        raise SandboxError("Completion Integrity pack lacks its private canary")
    pack = without_canary(load_json_object(pack_root / "pack.json"))
    if pack.get("schema_version") != "ael.completion-integrity-private-pack/0.1-pilot":
        raise SandboxError("Completion Integrity pack has an unsupported schema")
    entries = pack.get("tasks")
    if not isinstance(entries, list) or len(entries) != 10:
        raise SandboxError(
            "Completion Integrity pack must contain eight core and two calibration tasks"
        )
    tasks: dict[str, dict[str, Any]] = {}
    for value in entries:
        if not isinstance(value, dict):
            raise SandboxError("Completion Integrity task entry must be an object")
        task_id = value.get("task_id")
        relative = value.get("path")
        if not isinstance(task_id, str) or not isinstance(relative, str):
            raise SandboxError("Completion Integrity task lacks identity or path")
        task_root = (pack_root / relative).resolve()
        if not task_root.is_relative_to(pack_root.resolve()):
            raise SandboxError(f"Completion Integrity task escapes the pack: {task_id}")
        required = (
            task_root / "fixture" / "TASK.md",
            task_root / "evaluator" / "test_score.py",
            task_root / "evaluator" / "oracle.json",
            task_root / "reference",
            task_root / "regression",
            task_root / "dossier.json",
        )
        if any(path.is_symlink() or not path.exists() for path in required):
            raise SandboxError(f"Completion Integrity task is incomplete or unsafe: {task_id}")
        if task_id in tasks:
            raise SandboxError(f"duplicate Completion Integrity task ID: {task_id}")
        dossier = without_canary(load_json_object(task_root / "dossier.json"))
        if dossier.get("task_id") != task_id:
            raise SandboxError(f"Completion Integrity dossier identity mismatch: {task_id}")
        tasks[task_id] = {**value, **dossier, "root": task_root}
    return pack, tasks


def overlay_candidate(fixture: Path, overlay: Path, target: Path) -> None:
    shutil.copytree(fixture, target, symlinks=True)
    shutil.copytree(overlay, target, dirs_exist_ok=True, symlinks=True)


def evaluate_candidate(
    task_root: Path,
    candidate: Path | None,
    output: Path,
    *,
    evaluator_image: str = DEFAULT_IMAGE,
) -> dict[str, Any]:
    output = output.absolute()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ael-ci9-evaluator-", dir="/private/tmp") as temporary:
        staging = Path(temporary)
        if candidate is not None:
            shutil.copytree(candidate, staging / "candidate", symlinks=True)
        shutil.copytree(task_root / "evaluator", staging / "evaluator", symlinks=True)
        result = run_container(
            staging,
            output,
            ["python", "evaluator/test_score.py", "candidate", "score.json"],
            image=evaluator_image,
            network_policy="none",
            timeout_seconds=120,
            memory="512m",
            workspace_size="512m",
        )
    score_path = output / "workspace" / "score.json"
    if result.exit_code != 0 or not score_path.is_file():
        raise SandboxError("Completion Integrity evaluator did not produce a score")
    score = without_canary(load_json_object(score_path))
    if score.get("schema_version") != "ael.completion-integrity-score/0.1":
        raise SandboxError("Completion Integrity evaluator produced an unsupported score")
    return score


def write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=False, allow_nan=False) + "\n"
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


def read_attempt_journal(journal: Path) -> list[dict[str, Any]]:
    if not journal.exists():
        return []
    if journal.is_symlink() or not journal.is_dir():
        raise SandboxError(f"attempt journal is unsafe: {journal}")
    paths = sorted(journal.iterdir())
    if any(path.is_symlink() or not path.is_file() for path in paths):
        raise SandboxError(f"attempt journal contains an unsafe member: {journal}")
    allowed = set(ATTEMPT_EVENT_FILES.values())
    if any(path.name not in allowed for path in paths):
        raise SandboxError(f"attempt journal contains an unknown event: {journal}")
    events = [load_json_object(path) for path in paths]
    states = [event.get("state") for event in events]
    if states not in (
        ["prepared"],
        ["prepared", "submitted"],
        ["prepared", "submitted", "terminal"],
        ["prepared", "submitted", "ambiguous"],
    ):
        raise SandboxError(f"attempt journal has an invalid transition sequence: {journal}")
    attempt_ids = {event.get("attempt_id") for event in events}
    cell_ids = {event.get("cell_id") for event in events}
    if len(attempt_ids) != 1 or len(cell_ids) != 1:
        raise SandboxError(f"attempt journal identity changed across events: {journal}")
    return events


def append_attempt_event(journal: Path, event: Mapping[str, Any]) -> None:
    state = event.get("state")
    filename = ATTEMPT_EVENT_FILES.get(str(state))
    if filename is None:
        raise SandboxError(f"unsupported attempt event state: {state}")
    journal.mkdir(parents=True, mode=0o700, exist_ok=True)
    path = journal / filename
    payload = json.dumps(event, indent=2, sort_keys=False, allow_nan=False) + "\n"
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise SandboxError(f"attempt event already exists and is immutable: {path}") from exc
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def scan_public_boundary(private_root: Path, public_root: Path) -> dict[str, Any]:
    """Fail closed on canaries or exact private-file copies in the public tree."""

    private_root = private_root.resolve()
    public_root = public_root.resolve()
    if private_root == public_root or private_root.is_relative_to(public_root):
        raise SandboxError("private pack must remain outside the public repository")
    private_hashes: set[str] = set()
    for path in sorted(private_root.rglob("*")):
        if path.is_symlink():
            raise SandboxError(f"private corpus contains a symlink: {path}")
        if path.is_file():
            private_hashes.add(hashlib.sha256(path.read_bytes()).hexdigest())
    canary_hits: list[str] = []
    exact_hits: list[str] = []
    ignored_parts = {".git", ".venv", "__pycache__", "build", "dist"}
    for path in sorted(public_root.rglob("*")):
        if path.is_symlink() or not path.is_file() or ignored_parts.intersection(path.parts):
            continue
        payload = path.read_bytes()
        relative = path.relative_to(public_root).as_posix()
        if PRIVATE_CANARY_PREFIX.encode() in payload:
            canary_hits.append(relative)
        if hashlib.sha256(payload).hexdigest() in private_hashes:
            exact_hits.append(relative)
    if canary_hits or exact_hits:
        raise SandboxError(
            "private corpus crossed the public boundary: "
            f"canaries={canary_hits} exact_files={exact_hits}"
        )
    return {
        "status": "pass",
        "private_file_hash_count": len(private_hashes),
        "public_canary_hits": canary_hits,
        "public_exact_file_hits": exact_hits,
        "scope": "unique canary prefix and exact whole-file SHA-256 matches",
    }
