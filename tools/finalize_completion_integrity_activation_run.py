"""Finalize an interrupted activation from immutable journals without retrying.

This command is intentionally incapable of invoking Codex, Docker, or an
evaluator.  It closes the private normalized record after a submitted attempt
became ambiguous or the live runner stopped before writing terminal documents.
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from completion_integrity_activation_support import (
    canonical_sha256,
    load_json,
    read_attempt_journal,
    sha256_path,
    write_json_atomic,
)

from ael.completion_integrity_activation import (
    build_activation_observations,
    decide_activation,
    decision_id_from_study_id,
)
from ael.sandbox import SandboxError

ROOT = Path(__file__).resolve().parents[1]
FREEZE_SCHEMA = "ael.completion-integrity-activation-freeze/0.1-pilot"
RECOVERY_SCHEMA = "ael.completion-integrity-activation-recovery/0.1-pilot"


def _fail(message: str) -> None:
    raise SandboxError(f"activation finalizer failed: {message}")


def _git(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        ["git", "-C", str(ROOT), *arguments],
        capture_output=True,
        check=False,
    )
    if check and result.returncode != 0:
        _fail(f"git {' '.join(arguments)} failed")
    return result


def _verify_preregistration(freeze_path: Path, preregistration_sha: str) -> None:
    if len(preregistration_sha) != 40 or any(
        character not in "0123456789abcdef" for character in preregistration_sha
    ):
        _fail("preregistration SHA must be 40 lowercase hexadecimal characters")
    try:
        relative = freeze_path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError as exc:
        raise SandboxError("activation finalizer failed: freeze is outside Git") from exc
    _git("cat-file", "-e", f"{preregistration_sha}^{{commit}}")
    frozen_bytes = _git("show", f"{preregistration_sha}:{relative}").stdout
    if hashlib.sha256(frozen_bytes).hexdigest() != sha256_path(freeze_path):
        _fail("preregistration commit contains different freeze bytes")
    decision_relative = (freeze_path.parent / "results" / "decision.json").relative_to(ROOT)
    if (
        _git(
            "cat-file",
            "-e",
            f"{preregistration_sha}:{decision_relative.as_posix()}",
            check=False,
        ).returncode
        == 0
    ):
        _fail("terminal public decision already existed at preregistration")


def _safe_raw_root(raw_root: Path) -> Path:
    raw_root = raw_root.absolute()
    if (
        raw_root.is_symlink()
        or not raw_root.is_dir()
        or raw_root.resolve().is_relative_to(ROOT.resolve())
    ):
        _fail("raw evidence root must be an existing non-symlink outside Git")
    for name in ("observations.json", "decision.json", "run-summary.json", "recovery.json"):
        if (raw_root / name).exists() or (raw_root / name).is_symlink():
            _fail(f"refusing to overwrite existing terminal artifact: {name}")
    return raw_root


def _load_cells(raw_root: Path) -> dict[str, dict[str, Any]]:
    cell_root = raw_root / "cells"
    if not cell_root.exists():
        return {}
    if cell_root.is_symlink() or not cell_root.is_dir():
        _fail("cell root is unsafe")
    cells: dict[str, dict[str, Any]] = {}
    for path in sorted(cell_root.iterdir()):
        if path.is_symlink() or not path.is_file() or path.suffix != ".json":
            _fail("cell root contains an unsafe member")
        cells[path.stem] = load_json(path)
    return cells


def finalize_interrupted_run(
    *,
    freeze_path: Path,
    raw_root: Path,
    preregistration_sha: str,
    finalized_at: str,
) -> dict[str, Any]:
    freeze_path = freeze_path.absolute()
    if freeze_path.is_symlink() or not freeze_path.is_file():
        _fail("freeze is missing or unsafe")
    freeze = load_json(freeze_path)
    if freeze.get("schema_version") != FREEZE_SCHEMA:
        _fail("freeze schema differs")
    _verify_preregistration(freeze_path, preregistration_sha)
    raw_root = _safe_raw_root(raw_root)

    schedule = freeze.get("schedule")
    if not isinstance(schedule, list) or not schedule:
        _fail("freeze schedule is missing")
    cells = _load_cells(raw_root)
    scheduled_ids = [str(entry.get("cell_id")) for entry in schedule if isinstance(entry, Mapping)]
    if len(scheduled_ids) != len(schedule) or len(set(scheduled_ids)) != len(scheduled_ids):
        _fail("freeze schedule identities are malformed")
    if not set(cells).issubset(scheduled_ids):
        _fail("private cells contain an identity outside the frozen schedule")

    attempt_states: dict[str, str] = {}
    journal_refs: dict[str, list[dict[str, str]]] = {}
    protocol_issues: list[str] = []
    stop_seen = False
    for entry in schedule:
        cell_id = str(entry["cell_id"])
        events = read_attempt_journal(raw_root / "attempts" / cell_id)
        if stop_seen and (events or cell_id in cells):
            _fail("a later frozen cell exists after the first non-terminal stop")
        if not events:
            continue
        for event in events:
            if event.get("cell_id") != cell_id or event.get("freeze_sha256") != sha256_path(
                freeze_path
            ):
                _fail("attempt journal differs from its frozen cell binding")
        state = str(events[-1]["state"])
        attempt_states[cell_id] = state
        journal_refs[cell_id] = [
            {"name": path.name, "sha256": sha256_path(path)}
            for path in sorted((raw_root / "attempts" / cell_id).iterdir())
        ]
        if state == "terminal":
            if cell_id not in cells:
                _fail("terminal journal has no terminal cell")
            if events[-1].get("cell_sha256") != canonical_sha256(cells[cell_id]):
                # Files are pretty-printed while canonical_sha256 hashes the JSON
                # value.  Accept the immutable file hash recorded by the runner.
                cell_path = raw_root / "cells" / f"{cell_id}.json"
                if events[-1].get("cell_sha256") != sha256_path(cell_path):
                    _fail("terminal cell hash differs from its journal")
            if cells[cell_id].get("status") != "valid":
                issues = cells[cell_id].get("issues")
                if isinstance(issues, list) and issues:
                    protocol_issues.extend(f"{cell_id}:{issue}" for issue in issues)
                else:
                    protocol_issues.append(f"{cell_id}:InvalidCell")
                stop_seen = True
        elif state == "ambiguous":
            error_type = events[-1].get("error_type")
            protocol_issues.append(
                f"{cell_id}:{error_type if isinstance(error_type, str) and error_type else 'AmbiguousAttempt'}"
            )
            stop_seen = True
        elif state == "submitted":
            protocol_issues.append(f"{cell_id}:AmbiguousSubmission")
            stop_seen = True
        elif state == "prepared":
            protocol_issues.append(f"{cell_id}:PreparedOnly")
            stop_seen = True
        else:
            _fail("attempt journal ended in an unsupported state")

    if not attempt_states:
        _fail("no immutable attempt journal exists to finalize")
    for cell_id in cells:
        if attempt_states.get(cell_id) != "terminal":
            _fail("a cell exists without a matching terminal journal")

    observations = build_activation_observations(
        freeze=freeze,
        freeze_sha256=sha256_path(freeze_path),
        preregistration_sha=preregistration_sha,
        cells=cells,
        attempt_states=attempt_states,
        protocol_issues=protocol_issues,
    )
    decision = decide_activation(
        observations,
        decision_id=decision_id_from_study_id(freeze.get("study_id")),
    )
    write_json_atomic(raw_root / "observations.json", observations)
    write_json_atomic(raw_root / "decision.json", decision)
    write_json_atomic(
        raw_root / "run-summary.json",
        {
            "schema_version": "ael.completion-integrity-activation-run-summary/0.1-pilot",
            "freeze_sha256": sha256_path(freeze_path),
            "preregistration_sha": preregistration_sha,
            "terminal_cells": len(cells),
            "scheduled_cells": len(schedule),
            "protocol_issues": sorted(set(protocol_issues)),
            "decision_disposition": decision["disposition"],
            "observations_sha256": canonical_sha256(observations),
        },
    )
    recovery = {
        "schema_version": RECOVERY_SCHEMA,
        "finalized_at": finalized_at,
        "operation": "normalize_existing_attempts_without_retry",
        "model_calls": 0,
        "retries": 0,
        "freeze_sha256": sha256_path(freeze_path),
        "preregistration_sha": preregistration_sha,
        "scheduled_cells": len(schedule),
        "terminal_cells": len(cells),
        "attempt_state_counts": dict(sorted(Counter(attempt_states.values()).items())),
        "journal_refs": journal_refs,
        "observations_sha256": sha256_path(raw_root / "observations.json"),
        "decision_sha256": sha256_path(raw_root / "decision.json"),
        "run_summary_sha256": sha256_path(raw_root / "run-summary.json"),
        "decision_status": decision["status"],
        "decision_disposition": decision["disposition"],
    }
    write_json_atomic(raw_root / "recovery.json", recovery)
    return recovery


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Finalize an interrupted Completion Integrity activation without retrying"
    )
    parser.add_argument("--freeze", required=True, type=Path)
    parser.add_argument("--raw-root", required=True, type=Path)
    parser.add_argument("--preregistration-sha", required=True)
    parser.add_argument("--finalized-at", required=True)
    args = parser.parse_args()
    try:
        recovery = finalize_interrupted_run(
            freeze_path=args.freeze,
            raw_root=args.raw_root,
            preregistration_sha=args.preregistration_sha,
            finalized_at=args.finalized_at,
        )
    except SandboxError as exc:
        print(exc)
        return 1
    print(
        "activation finalizer pass: "
        f"terminal_cells={recovery['terminal_cells']}/{recovery['scheduled_cells']} "
        f"status={recovery['decision_status']} "
        f"disposition={recovery['decision_disposition']} retries=0 model_calls=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
