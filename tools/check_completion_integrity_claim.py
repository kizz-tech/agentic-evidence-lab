from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import tempfile
from pathlib import Path
from typing import Any

from ael.completion_integrity_claim import assess_terminal_claim

BUNDLE_SCHEMA_VERSION = "ael.completion-integrity-terminal-claim-bundle/0.1-development"


class TerminalClaimAdapterError(ValueError):
    pass


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number is forbidden: {value}")


def _finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"non-finite JSON number is forbidden: {value}")
    return parsed


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _regular_file(path: Path, label: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise TerminalClaimAdapterError(f"{label} is missing or unsafe: {path}")


def load_json(path: Path, label: str) -> object:
    path = path.absolute()
    _regular_file(path, label)
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_pairs,
            parse_float=_finite_float,
            parse_constant=_reject_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise TerminalClaimAdapterError(f"{label} is unreadable: {path}: {exc}") from exc


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"


def _contains_symlink(path: Path) -> bool:
    absolute = path.absolute()
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _write_or_check(path: Path, content: str, check: bool) -> None:
    path = path.absolute()
    if _contains_symlink(path.parent):
        raise TerminalClaimAdapterError(f"output directory must not use symlinks: {path.parent}")
    if check:
        _regular_file(path, "terminal-claim output")
        if path.read_text(encoding="utf-8") != content:
            raise TerminalClaimAdapterError(f"terminal-claim output differs: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        _regular_file(path, "terminal-claim output")
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
        handle.write(content)
    try:
        temporary.chmod(0o644)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def check_bundle(
    policy_path: Path,
    cases_path: Path,
    *,
    assessments_json: Path | None = None,
    check: bool = False,
) -> dict[str, Any]:
    """Assess normalized reporter-only cases without claiming runtime isolation."""

    policy = load_json(policy_path, "terminal-claim policy")
    cases = load_json(cases_path, "terminal-claim cases")
    if not isinstance(policy, dict):
        raise TerminalClaimAdapterError("terminal-claim policy must be an object")
    if not isinstance(cases, list) or not cases:
        raise TerminalClaimAdapterError("terminal-claim cases must be a non-empty array")
    seen: set[str] = set()
    assessments: list[dict[str, Any]] = []
    for index, case in enumerate(cases):
        if not isinstance(case, dict) or set(case) != {
            "case_id",
            "frozen_truth",
            "reporter_submission",
        }:
            raise TerminalClaimAdapterError(
                f"case {index} must contain only case_id, frozen_truth, and reporter_submission"
            )
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not case_id.strip() or case_id in seen:
            raise TerminalClaimAdapterError(f"case {index} has an invalid or duplicate case_id")
        seen.add(case_id)
        truth = case.get("frozen_truth")
        submission = case.get("reporter_submission")
        if not isinstance(truth, dict) or not isinstance(submission, dict):
            raise TerminalClaimAdapterError(f"case {case_id} inputs must be objects")
        assessments.append(
            {
                "case_id": case_id,
                "assessment": assess_terminal_claim(policy, truth, submission),
            }
        )
    invalid_count = sum(item["assessment"]["status"] == "invalid" for item in assessments)
    bundle = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "status": "complete" if invalid_count == 0 else "blocked",
        "case_count": len(assessments),
        "invalid_count": invalid_count,
        "input_hashes": {
            "policy_sha256": _sha256(policy_path),
            "cases_sha256": _sha256(cases_path),
        },
        "assessments": assessments,
        "boundary": (
            "These normalized fixtures exercise claim semantics and immutable bindings. They do not prove that a real reporter lacked edit, tool, retry, executor, evaluator, or remediation authority."
        ),
    }
    if assessments_json is not None:
        _write_or_check(assessments_json, _json_text(bundle), check)
    return bundle


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check Completion Integrity terminal-claim fixtures"
    )
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--cases", required=True, type=Path)
    parser.add_argument("--assessments-json", required=True, type=Path)
    parser.add_argument("--check", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        bundle = check_bundle(
            args.policy,
            args.cases,
            assessments_json=args.assessments_json,
            check=args.check,
        )
    except TerminalClaimAdapterError as exc:
        print(f"terminal-claim check failed: {exc}", file=os.sys.stderr)
        return 1
    print(
        f"terminal-claim check {bundle['status']}: "
        f"cases={bundle['case_count']} invalid={bundle['invalid_count']}"
    )
    return 0 if bundle["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
