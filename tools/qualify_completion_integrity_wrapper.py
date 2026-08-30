from __future__ import annotations

import argparse
import json
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from completion_integrity_activation_support import (
    activation_attempt_id,
    activation_namespace,
    activation_schedule,
    build_frozen_truth,
    build_reporter_submission,
    canonical_sha256,
    load_json,
    qualification_id_for_pack,
    sha256_path,
)

from ael.completion_integrity_claim import assess_terminal_claim
from ael.sandbox import SandboxError, tree_sha256

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "ael.completion-integrity-wrapper-qualification/0.1-pilot"


def _safe_task_root(pack_root: Path, relative: str) -> Path:
    raw = Path(relative)
    if raw.is_absolute() or "\\" in relative or any(part in {"", ".", ".."} for part in raw.parts):
        raise SandboxError("wrapper qualification pack contains an unsafe task path")
    task_root = pack_root / raw
    if task_root.is_symlink() or not task_root.is_dir():
        raise SandboxError("wrapper qualification task root is missing or unsafe")
    if not task_root.resolve().is_relative_to(pack_root.resolve()):
        raise SandboxError("wrapper qualification task root escapes its pack")
    return task_root


def _write_json(path: Path, value: Mapping[str, Any], *, check: bool) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if check:
        if path.is_symlink() or not path.is_file() or path.read_text(encoding="utf-8") != payload:
            raise SandboxError("wrapper qualification output is missing or stale")
        return
    path = path.absolute()
    if path.is_symlink() or path.parent.is_symlink():
        raise SandboxError("wrapper qualification output path is unsafe")
    path.parent.mkdir(parents=True, exist_ok=True)
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


def _task_entries(pack: Mapping[str, Any]) -> dict[str, str]:
    entries = pack.get("tasks")
    if not isinstance(entries, list) or len(entries) != 2:
        raise SandboxError("wrapper qualification requires exactly two task roots")
    result: dict[str, str] = {}
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise SandboxError("wrapper qualification task entry is malformed")
        task_id = entry.get("task_id")
        path = entry.get("path")
        if not isinstance(task_id, str) or not isinstance(path, str) or task_id in result:
            raise SandboxError("wrapper qualification task identity is invalid")
        result[task_id] = path
    return result


def _reference_evaluation(
    qualification_root: Path, task: Mapping[str, Any]
) -> tuple[dict[str, Any], Mapping[str, Any]]:
    task_id = task.get("task_id")
    cases = task.get("case_results")
    if not isinstance(task_id, str) or not isinstance(cases, list):
        raise SandboxError("wrapper qualification task receipt is malformed")
    for sequence, case in enumerate(cases, start=1):
        if isinstance(case, Mapping) and case.get("case_id") == "reference_solution":
            root = (
                qualification_root
                / "raw"
                / task_id
                / f"{sequence:02d}-reference_solution-evaluator-1"
            )
            evaluation = load_json(root / "workspace" / "truth.json")
            if canonical_sha256(evaluation) != case.get("evaluation_sha256"):
                raise SandboxError("wrapper qualification reference evaluation drifted")
            if (
                evaluation.get("accepted") is not True
                or evaluation.get("operational_valid") is not True
            ):
                raise SandboxError("wrapper qualification reference solution is not accepted")
            return evaluation, case
    raise SandboxError("wrapper qualification has no reference-solution evaluation")


def qualify_wrapper(
    *,
    study_root: Path,
    pack_root: Path,
    qualification_root: Path,
) -> dict[str, Any]:
    study_root = study_root.absolute()
    pack_root = pack_root.absolute()
    qualification_root = qualification_root.absolute()
    if not study_root.resolve().is_relative_to(ROOT.resolve()) or study_root.is_symlink():
        raise SandboxError("wrapper qualification study root is unsafe")
    manifest = load_json(study_root / "study-manifest.json")
    policy = load_json(study_root / "terminal-claim-policy.json")
    pack = load_json(pack_root / "pack.json")
    receipt_path = qualification_root / "qualification-receipt.json"
    receipt = load_json(receipt_path)
    pack_id = str(pack.get("pack_id"))
    pack_revision = int(pack.get("revision", 0))
    if receipt.get("qualification_id") != qualification_id_for_pack(pack_id, pack_revision):
        raise SandboxError("wrapper qualification receipt identity differs from the pack")
    if receipt.get("pack_sha256") != tree_sha256(pack_root) or receipt.get("status") != "pass":
        raise SandboxError("wrapper qualification receipt does not bind a passing pack")
    tasks = receipt.get("tasks")
    if not isinstance(tasks, list) or len(tasks) != 2:
        raise SandboxError("wrapper qualification receipt task count differs")
    task_paths = _task_entries(pack)
    task_ids = [str(task.get("task_id")) for task in tasks if isinstance(task, Mapping)]
    if set(task_ids) != set(task_paths):
        raise SandboxError("wrapper qualification task identities differ")
    for _task_id, relative in task_paths.items():
        _safe_task_root(pack_root, relative)

    study_id = str(manifest.get("study_id"))
    study_revision = int(manifest.get("revision", 0))
    activation_id = activation_namespace(study_id)
    binding_sha256 = canonical_sha256(
        {
            "study_id": study_id,
            "study_revision": study_revision,
            "pack_id": pack_id,
            "pack_revision": pack_revision,
            "pack_sha256": tree_sha256(pack_root),
            "qualification_sha256": sha256_path(receipt_path),
            "policy_sha256": sha256_path(study_root / "terminal-claim-policy.json"),
        }
    )
    schedule = activation_schedule(task_ids)
    task_contexts: dict[str, dict[str, Any]] = {}
    cells: list[dict[str, Any]] = []
    for task in tasks:
        if not isinstance(task, Mapping):
            raise SandboxError("wrapper qualification task is malformed")
        task_id = str(task["task_id"])
        evaluation, case = _reference_evaluation(qualification_root, task)
        executor_cell_id = f"{task_id}-E0"
        executor_attempt_id = activation_attempt_id(binding_sha256, executor_cell_id)
        artifact_sha256 = str(case.get("candidate_sha256"))
        evidence_bundle_sha256 = canonical_sha256(
            {"task_id": task_id, "evaluation_sha256": canonical_sha256(evaluation)}
        )
        dossier = load_json(_safe_task_root(pack_root, task_paths[task_id]) / "dossier.json")
        custody = dossier.get("evaluator_custody")
        if not isinstance(custody, Mapping):
            raise SandboxError("wrapper qualification task lacks evaluator custody")
        truth = build_frozen_truth(
            task_id=task_id,
            attempt_id=executor_attempt_id,
            artifact_sha256=artifact_sha256,
            evidence_bundle_sha256=evidence_bundle_sha256,
            evaluation=evaluation,
            evaluator_sha256=str(custody.get("evaluator_sha256")),
            custody_receipt_sha256=str(custody.get("receipt_sha256")),
            activation_id=activation_id,
        )
        task_contexts[task_id] = {
            "attempt_id": executor_attempt_id,
            "artifact_sha256": artifact_sha256,
            "evidence_bundle_sha256": evidence_bundle_sha256,
            "truth": truth,
            "evaluation": evaluation,
        }

    for entry in schedule:
        task_id = str(entry["task_id"])
        context = task_contexts[task_id]
        journal_attempt_id = activation_attempt_id(binding_sha256, str(entry["cell_id"]))
        if entry["role"] == "executor":
            cells.append(
                {
                    **entry,
                    "journal_attempt_id": journal_attempt_id,
                    "truth_id": context["truth"]["truth_id"],
                    "submission_id": None,
                    "terminal_assessment": "not_applicable_executor",
                    "status": "pass",
                }
            )
            continue
        model_output = {
            "verdict": "complete",
            "progress": "continuable",
            "ledger": [
                {
                    "requirement_id": row["requirement_id"],
                    "state": row["state"],
                    "evidence_refs": [row["evidence_sha256"]],
                }
                for row in context["evaluation"]["requirements"]
            ],
        }
        submission = build_reporter_submission(
            task_id=task_id,
            condition_id=str(entry["condition_id"]),
            attempt_id=context["attempt_id"],
            artifact_sha256=context["artifact_sha256"],
            evidence_bundle_sha256=context["evidence_bundle_sha256"],
            model_output=model_output,
            activation_id=activation_id,
        )
        assessment = assess_terminal_claim(policy, context["truth"], submission)
        if assessment.get("status") != "pass":
            raise SandboxError("full wrapper qualification did not compose")
        cells.append(
            {
                **entry,
                "journal_attempt_id": journal_attempt_id,
                "truth_id": context["truth"]["truth_id"],
                "submission_id": submission["submission_id"],
                "terminal_assessment": assessment["status"],
                "status": "pass",
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "qualification_id": f"{study_id}:full-wrapper-qualification:{study_revision}",
        "study_id": study_id,
        "study_revision": study_revision,
        "activation_namespace": activation_id,
        "pack_id": pack_id,
        "pack_revision": pack_revision,
        "pack_sha256": tree_sha256(pack_root),
        "qualification_receipt_sha256": sha256_path(receipt_path),
        "binding_sha256": binding_sha256,
        "status": "pass",
        "task_count": len(tasks),
        "cell_count": len(cells),
        "cells": cells,
        "model_calls": 0,
        "claim_ceiling": "Synthetic full-wrapper composition over retained qualification truth; no runtime isolation, reporter accuracy, effect, reliability, or transfer claim.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Qualify versioned Completion Integrity owner-wrapper composition"
    )
    parser.add_argument("--study-root", required=True, type=Path)
    parser.add_argument("--pack-root", required=True, type=Path)
    parser.add_argument("--qualification-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        result = qualify_wrapper(
            study_root=args.study_root,
            pack_root=args.pack_root,
            qualification_root=args.qualification_root,
        )
        _write_json(args.output, result, check=args.check)
    except SandboxError as exc:
        print(f"Completion Integrity wrapper qualification failed: {exc}")
        return 1
    verb = "checked" if args.check else "pass"
    print(
        f"Completion Integrity wrapper qualification {verb}: "
        f"tasks={result['task_count']} cells={result['cell_count']} model_calls=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
