from __future__ import annotations

import argparse
import datetime as dt
import shutil
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from completion_integrity_activation_support import (
    canonical_sha256,
    load_json,
    parse_task_requirements,
    qualification_id_for_pack,
    sha256_path,
    write_json_atomic,
)

from ael.sandbox import DEFAULT_IMAGE, SandboxError, run_container, tree_sha256

QUALIFICATION_SCHEMA_VERSION = "ael.completion-integrity-task-qualification/0.1-pilot"


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_member(root: Path, relative: str) -> Path:
    if not relative or "\\" in relative:
        raise SandboxError(f"unsafe private task path: {relative!r}")
    candidate = Path(relative)
    if candidate.is_absolute() or any(part in {"", ".", ".."} for part in candidate.parts):
        raise SandboxError(f"unsafe private task path: {relative!r}")
    path = root / candidate
    cursor = root
    for part in candidate.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise SandboxError(f"private task path contains a symlink: {relative}")
    if not path.resolve().is_relative_to(root.resolve()):
        raise SandboxError(f"private task path escapes root: {relative}")
    return path


def _overlay(fixture: Path, overlays: Sequence[Path], target: Path) -> None:
    shutil.copytree(fixture, target, symlinks=True)
    for overlay in overlays:
        shutil.copytree(overlay, target, dirs_exist_ok=True, symlinks=True)
    tree_sha256(target)


def _run_visible(candidate: Path, output: Path, command: Sequence[str], image: str) -> bool:
    result = run_container(
        candidate,
        output,
        command,
        image=image,
        network_policy="none",
        timeout_seconds=120,
        memory="512m",
        workspace_size="512m",
    )
    return result.exit_code == 0


def _run_evaluator(
    candidate: Path,
    evaluator: Path,
    output: Path,
    image: str,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="ael-ci11-evaluator-", dir="/private/tmp") as temp:
        fixture = Path(temp)
        shutil.copytree(candidate, fixture / "candidate", symlinks=True)
        shutil.copytree(evaluator, fixture / "evaluator", symlinks=True)
        result = run_container(
            fixture,
            output,
            ["python3", "evaluator/evaluate.py", "candidate", "truth.json"],
            image=image,
            network_policy="none",
            timeout_seconds=120,
            memory="512m",
            workspace_size="512m",
        )
    truth = output / "workspace" / "truth.json"
    if result.exit_code != 0 or not truth.is_file():
        raise SandboxError("private evaluator did not produce a terminal truth document")
    document = load_json(truth)
    if document.get("schema_version") != "ael.completion-integrity-private-evaluation/0.1":
        raise SandboxError("private evaluator returned an unsupported schema")
    return document


def _case_expectation(case: Mapping[str, Any]) -> tuple[bool, bool]:
    visible = case.get("visible_pass")
    accepted = case.get("accepted")
    if not isinstance(visible, bool) or not isinstance(accepted, bool):
        raise SandboxError("qualification case expectations must be booleans")
    return visible, accepted


def validate_executor_contract(task_root: Path, dossier: Mapping[str, Any]) -> list[str]:
    """Verify the exact TASK syntax consumed by the scored executor adapter."""

    parsed = parse_task_requirements(task_root / "fixture" / "TASK.md")
    dossier_rows = dossier.get("requirements")
    if not isinstance(dossier_rows, list) or any(
        not isinstance(row, Mapping) or not isinstance(row.get("requirement_id"), str)
        for row in dossier_rows
    ):
        raise SandboxError("private dossier requirements are malformed")
    parsed_ids = [row["requirement_id"] for row in parsed]
    dossier_ids = [str(row["requirement_id"]) for row in dossier_rows]
    if parsed_ids != dossier_ids:
        raise SandboxError(
            "executor TASK requirement lines must exactly match dossier requirements in order"
        )
    return parsed_ids


def qualify_task(
    task_root: Path,
    output_root: Path,
    *,
    image: str,
) -> dict[str, Any]:
    dossier = load_json(task_root / "dossier.json")
    plan = load_json(task_root / "qualification-plan.json")
    validate_executor_contract(task_root, dossier)
    task_id = dossier.get("task_id")
    if plan.get("task_id") != task_id:
        raise SandboxError("qualification plan and dossier task identities differ")
    command = plan.get("visible_command")
    if (
        not isinstance(command, list)
        or not command
        or any(not isinstance(item, str) or not item for item in command)
    ):
        raise SandboxError(f"{task_id}: visible command is invalid")
    cases = plan.get("cases")
    if not isinstance(cases, list) or len(cases) != 8:
        raise SandboxError(f"{task_id}: qualification must contain eight named challenge cases")
    case_ids = [case.get("case_id") for case in cases if isinstance(case, Mapping)]
    expected_ids = {
        "pristine",
        "reference_solution",
        "alternative_solution",
        "partial_omission",
        "narrow_overfit",
        "collateral_regression",
        "fabricated_authority",
        "reward_hack",
    }
    if set(case_ids) != expected_ids or len(case_ids) != len(expected_ids):
        raise SandboxError(f"{task_id}: qualification cases do not cover the required states")

    task_output = output_root / str(task_id)
    if task_output.exists():
        raise SandboxError(f"qualification output already exists: {task_output}")
    task_output.mkdir(parents=True, mode=0o700)
    results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix=f"ael-ci11-{task_id}-", dir="/private/tmp") as temp:
        temp_root = Path(temp)
        for sequence, case in enumerate(cases, start=1):
            if not isinstance(case, Mapping):
                raise SandboxError(f"{task_id}: qualification case must be an object")
            case_id = str(case["case_id"])
            overlay_values = case.get("overlays")
            if not isinstance(overlay_values, list) or any(
                not isinstance(value, str) for value in overlay_values
            ):
                raise SandboxError(f"{task_id}/{case_id}: overlays must be an array")
            overlays = [_safe_member(task_root, value) for value in overlay_values]
            if any(not overlay.is_dir() for overlay in overlays):
                raise SandboxError(f"{task_id}/{case_id}: overlay is missing")
            candidate = temp_root / case_id
            _overlay(task_root / "fixture", overlays, candidate)
            visible_output = task_output / f"{sequence:02d}-{case_id}-visible"
            visible_pass = _run_visible(candidate, visible_output, command, image)
            evaluator_outputs = []
            evaluations = []
            for repeat in (1, 2):
                evaluator_output = task_output / f"{sequence:02d}-{case_id}-evaluator-{repeat}"
                evaluation = _run_evaluator(
                    candidate,
                    task_root / "evaluator",
                    evaluator_output,
                    image,
                )
                evaluator_outputs.append(evaluator_output)
                evaluations.append(evaluation)
            if evaluations[0] != evaluations[1]:
                raise SandboxError(f"{task_id}/{case_id}: evaluator repeats disagree")
            expected_visible, expected_accepted = _case_expectation(case)
            observed_accepted = evaluations[0].get("accepted")
            if visible_pass is not expected_visible or observed_accepted is not expected_accepted:
                raise SandboxError(
                    f"{task_id}/{case_id}: expected visible={expected_visible} "
                    f"accepted={expected_accepted}; observed visible={visible_pass} "
                    f"accepted={observed_accepted}"
                )
            if evaluations[0].get("operational_valid") is not True:
                raise SandboxError(f"{task_id}/{case_id}: evaluator marked the case invalid")
            results.append(
                {
                    "case_id": case_id,
                    "candidate_sha256": tree_sha256(candidate),
                    "visible_pass": visible_pass,
                    "accepted": observed_accepted,
                    "evaluation_sha256": canonical_sha256(evaluations[0]),
                    "visible_invocation_sha256": sha256_path(
                        visible_output / "sandbox-invocation.json"
                    ),
                    "evaluator_invocation_sha256": [
                        sha256_path(path / "sandbox-invocation.json") for path in evaluator_outputs
                    ],
                }
            )
    return {
        "task_id": task_id,
        "task_revision": dossier.get("revision"),
        "task_root_sha256": tree_sha256(task_root),
        "status": "pass",
        "semantic_review": {
            "status": "pass",
            "reviewer_id": "maintainer:codex-owner",
            "author_overlap": True,
            "scope": "instruction-to-oracle coverage, alternative validity, mutant meaning, and terminal-state semantics",
        },
        "adapted_after_qualification": False,
        "case_results": results,
    }


def qualify_pack(pack_root: Path, output_root: Path, *, image: str) -> dict[str, Any]:
    pack_root = pack_root.absolute()
    output_root = output_root.absolute()
    if pack_root.is_symlink() or not pack_root.is_dir():
        raise SandboxError("private Completion Integrity pack is missing or unsafe")
    if output_root.resolve(strict=False).is_relative_to(pack_root.resolve()):
        raise SandboxError("qualification output must remain outside the immutable private pack")
    if output_root.exists() and any(output_root.iterdir()):
        raise SandboxError("qualification output root must be new or empty")
    output_root.mkdir(parents=True, mode=0o700, exist_ok=True)
    pack = load_json(pack_root / "pack.json")
    entries = pack.get("tasks")
    if not isinstance(entries, list) or len(entries) != 2:
        raise SandboxError("activation qualification requires exactly two sacrificial roots")
    tasks: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise SandboxError("private pack task entry must be an object")
        task_root = _safe_member(pack_root, str(entry.get("path")))
        if task_root.is_symlink() or not task_root.is_dir():
            raise SandboxError("private task root is missing or unsafe")
        tasks.append(qualify_task(task_root, output_root / "raw", image=image))
    receipt = {
        "schema_version": QUALIFICATION_SCHEMA_VERSION,
        "qualification_id": qualification_id_for_pack(
            str(pack.get("pack_id")), int(pack.get("revision", 0))
        ),
        "recorded_at": utc_now(),
        "pack_id": pack.get("pack_id"),
        "pack_revision": pack.get("revision"),
        "pack_sha256": tree_sha256(pack_root),
        "runtime": {"image": image},
        "status": "pass",
        "task_count": len(tasks),
        "tasks": tasks,
        "claim_ceiling": (
            "Executed deterministic qualification on two sacrificial roots. This does not admit "
            "a scored pack, estimate sample size, or establish model performance."
        ),
    }
    write_json_atomic(output_root / "qualification-receipt.json", receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Execute semantic-mutant qualification for CI activation task roots"
    )
    parser.add_argument("pack_root", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    args = parser.parse_args()
    try:
        receipt = qualify_pack(args.pack_root, args.output, image=args.image)
    except SandboxError as exc:
        print(f"Completion Integrity qualification failed: {exc}")
        return 1
    print(
        f"Completion Integrity qualification {receipt['status']}: "
        f"tasks={receipt['task_count']} pack_sha256={receipt['pack_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
