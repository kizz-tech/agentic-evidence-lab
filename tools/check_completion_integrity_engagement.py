from __future__ import annotations

import argparse
import json
import math
import os
import stat
import tempfile
from collections.abc import Mapping
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any

from ael.completion_integrity_engagement import diagnose_cells

MAX_INPUT_BYTES = 2 * 1024 * 1024
BUNDLE_VERSION = "ael.completion-integrity-enactment-bundle/0.1-pilot"


class EngagementAdapterError(ValueError):
    """Unsafe, malformed, or stale candidate input/output."""


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate object member: {key}")
        result[key] = value
    return result


def _finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"non-finite JSON number: {value}")
    return parsed


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number: {value}")


def _contains_symlink(path: Path) -> bool:
    candidate = path.absolute()
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


def _regular_file(path: Path, label: str) -> None:
    if _contains_symlink(path):
        raise EngagementAdapterError(f"{label} must not use symlinks: {path}")
    try:
        info = path.lstat()
    except OSError as exc:
        raise EngagementAdapterError(f"{label} is missing: {path}: {exc}") from exc
    if not stat.S_ISREG(info.st_mode):
        raise EngagementAdapterError(f"{label} must be a regular file: {path}")
    if info.st_size > MAX_INPUT_BYTES:
        raise EngagementAdapterError(f"{label} exceeds {MAX_INPUT_BYTES} bytes: {path}")


def load_json(path: Path, label: str) -> Any:
    """Load strict JSON from one regular, non-symlinked file."""

    path = path.absolute()
    _regular_file(path, label)
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_strict_object,
            parse_float=_finite_float,
            parse_constant=_reject_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise EngagementAdapterError(f"{label} is unreadable: {path}: {exc}") from exc


def _sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _json_text(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"


def _policy_file(method_plan_path: Path, method_plan: Mapping[str, Any]) -> tuple[Path, str]:
    policy_ref = method_plan.get("policy_ref")
    if not isinstance(policy_ref, Mapping) or not isinstance(policy_ref.get("uri"), str):
        raise EngagementAdapterError("method plan policy_ref.uri must be a string")
    uri = str(policy_ref["uri"])
    pure = PurePosixPath(uri)
    if pure.is_absolute() or "\\" in uri or any(part in {"", ".", ".."} for part in pure.parts):
        raise EngagementAdapterError("policy_ref.uri must be a safe relative POSIX path")
    path = method_plan_path.absolute().parent.joinpath(*pure.parts)
    _regular_file(path, "policy fixture")
    digest = _sha256(path)
    if digest != policy_ref.get("sha256"):
        raise EngagementAdapterError("policy fixture SHA-256 does not match method plan")
    return path, digest


def _write_or_check(path: Path, content: str, check: bool) -> None:
    path = path.absolute()
    if _contains_symlink(path.parent):
        raise EngagementAdapterError(f"output directory must not use symlinks: {path.parent}")
    if check:
        _regular_file(path, "diagnostic output")
        if path.read_text(encoding="utf-8") != content:
            raise EngagementAdapterError(f"diagnostic output differs: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        _regular_file(path, "diagnostic output")
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
        if temporary.exists():
            temporary.unlink()


def check_bundle(
    method_plan_path: Path,
    observations_path: Path,
    *,
    diagnostics_json: Path | None = None,
    check: bool = False,
) -> dict[str, Any]:
    """Verify the real policy fixture and classify normalized synthetic cells."""

    method_plan = load_json(method_plan_path, "method plan")
    observations = load_json(observations_path, "normalized observations")
    if not isinstance(method_plan, dict):
        raise EngagementAdapterError("method plan must be an object")
    if not isinstance(observations, list) or not all(
        isinstance(item, dict) for item in observations
    ):
        raise EngagementAdapterError("normalized observations must be an array of objects")
    policy_path, policy_digest = _policy_file(method_plan_path, method_plan)
    report = diagnose_cells(method_plan, observations, policy_path.read_bytes())
    bundle = {
        "schema_version": BUNDLE_VERSION,
        "input_hashes": {
            "method_plan_sha256": _sha256(method_plan_path),
            "observations_sha256": _sha256(observations_path),
            "policy_fixture_sha256": policy_digest,
        },
        "policy_fixture": {
            "uri": str(method_plan["policy_ref"]["uri"]),
            "sha256": policy_digest,
        },
        "report": report,
        "boundary": (
            "The policy fixture bytes and input projections are bound. Normalized event labels remain caller-provided synthetic declarations until a future owner adapter captures real harness events."
        ),
    }
    if diagnostics_json is not None:
        _write_or_check(diagnostics_json, _json_text(bundle), check)
    return bundle


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check Completion Integrity observable-chain candidate fixtures"
    )
    parser.add_argument("--method-plan", required=True)
    parser.add_argument("--observations", required=True)
    parser.add_argument("--diagnostics-json", required=True)
    parser.add_argument("--check", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = check_bundle(
            Path(args.method_plan),
            Path(args.observations),
            diagnostics_json=Path(args.diagnostics_json),
            check=args.check,
        )
    except (EngagementAdapterError, ValueError) as exc:
        print(f"engagement check failed: {exc}", file=os.sys.stderr)
        return 1
    report = result["report"]
    print(f"engagement check complete: cells={report['cell_count']} diagnostics={report['status']}")
    return 1 if report["status"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
