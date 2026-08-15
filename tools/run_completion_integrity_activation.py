from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import shutil
import subprocess
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from completion_integrity_activation_support import (
    append_attempt_event,
    assess_executor_claim,
    build_frozen_truth,
    build_reporter_submission,
    canonical_sha256,
    evidence_payload,
    load_json,
    normalize_executor_capture,
    parse_codex_events,
    parse_task_requirements,
    read_attempt_journal,
    reporter_tool_event_count,
    sha256_path,
    write_json_atomic,
)
from prepare_completion_integrity_activation import verify_freeze

from ael.codex_activation_runner import run_activation_executor
from ael.codex_reporter import run_codex_reporter
from ael.completion_integrity_activation import (
    ACTIVATION_SCHEMA_VERSION,
    decide_activation,
    decision_id_from_study_id,
    validate_observations,
)
from ael.completion_integrity_claim import assess_terminal_claim
from ael.completion_integrity_engagement import diagnose_policy_enactment
from ael.sandbox import SandboxError, run_container, tree_sha256

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STUDY_ROOT = ROOT / "studies" / "completion-integrity" / "activation-v1"
ATTEMPT_SCHEMA = "ael.completion-integrity-activation-attempt/0.1-pilot"
CELL_SCHEMA = "ael.completion-integrity-activation-cell/0.1-pilot"


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _attempt_id(freeze_sha256: str, cell_id: str) -> str:
    return hashlib.sha256(f"{freeze_sha256}:{cell_id}".encode()).hexdigest()[:32]


def _tree_size(path: Path) -> int:
    return sum(member.stat().st_size for member in path.rglob("*") if member.is_file())


def _private_root(raw_root: Path) -> Path:
    raw_root = raw_root.absolute()
    if raw_root.is_symlink() or raw_root.resolve(strict=False).is_relative_to(ROOT.resolve()):
        raise SandboxError("activation raw evidence must remain outside Git and non-symlinked")
    if raw_root.exists() and any(raw_root.iterdir()):
        raise SandboxError("activation raw root must be new or empty; never overwrite or retry")
    raw_root.mkdir(parents=True, mode=0o700, exist_ok=True)
    return raw_root


def _git(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            ["git", "-C", str(ROOT), *arguments],
            check=check,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SandboxError(f"activation Git proof failed: {' '.join(arguments)}") from exc


def verify_preregistration(freeze_path: Path, preregistration_sha: str) -> None:
    if len(preregistration_sha) != 40 or any(
        character not in "0123456789abcdef" for character in preregistration_sha
    ):
        raise SandboxError("preregistration SHA must be 40 lowercase hexadecimal characters")
    relative = freeze_path.resolve().relative_to(ROOT.resolve()).as_posix()
    _git("cat-file", "-e", f"{preregistration_sha}^{{commit}}")
    head = _git("rev-parse", "HEAD").stdout.decode().strip()
    remote = _git("rev-parse", "origin/main").stdout.decode().strip()
    if head != preregistration_sha or remote != preregistration_sha:
        raise SandboxError("execution requires clean local and origin/main preregistration parity")
    if _git("status", "--porcelain").stdout:
        raise SandboxError("execution requires a clean preregistration checkout")
    frozen_bytes = _git("show", f"{preregistration_sha}:{relative}").stdout
    if hashlib.sha256(frozen_bytes).hexdigest() != sha256_path(freeze_path):
        raise SandboxError("preregistration commit contains different freeze bytes")
    result_relative = (
        (freeze_path.parent / "results" / "decision.json").relative_to(ROOT).as_posix()
    )
    if (
        _git("cat-file", "-e", f"{preregistration_sha}:{result_relative}", check=False).returncode
        == 0
    ):
        raise SandboxError("terminal activation decision existed at preregistration")


def _safe_task_root(pack_root: Path, relative: str) -> Path:
    raw = Path(relative)
    if raw.is_absolute() or "\\" in relative or any(part in {"", ".", ".."} for part in raw.parts):
        raise SandboxError("private pack contains an unsafe task path")
    task_root = pack_root / raw
    if task_root.is_symlink() or not task_root.is_dir():
        raise SandboxError("private activation task root is missing or unsafe")
    if not task_root.resolve().is_relative_to(pack_root.resolve()):
        raise SandboxError("private activation task root escapes its pack")
    return task_root


def _task_map(pack_root: Path) -> dict[str, Path]:
    pack = load_json(pack_root / "pack.json")
    entries = pack.get("tasks")
    if not isinstance(entries, list) or len(entries) != 2:
        raise SandboxError("activation pack must contain exactly two task roots")
    result: dict[str, Path] = {}
    for entry in entries:
        if not isinstance(entry, Mapping) or not isinstance(entry.get("task_id"), str):
            raise SandboxError("activation pack task entry is malformed")
        task_id = str(entry["task_id"])
        if task_id in result or not isinstance(entry.get("path"), str):
            raise SandboxError("activation pack task identity is ambiguous")
        result[task_id] = _safe_task_root(pack_root, str(entry["path"]))
    return result


def _executor_fixture(*, task_root: Path, study_root: Path, raw_root: Path, task_id: str) -> Path:
    source = task_root / "fixture"
    schema = study_root / "executor-output-schema.json"
    if not schema.exists():
        return source
    if schema.is_symlink() or not schema.is_file():
        raise SandboxError("activation executor schema is missing or unsafe")
    derived = raw_root / "derived" / task_id / "executor-fixture"
    if derived.exists() or derived.is_symlink():
        raise SandboxError("derived executor fixture must be new")
    shutil.copytree(source, derived, symlinks=True)
    target = derived / ".ael" / "executor-output-schema.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(schema, target)
    tree_sha256(derived)
    return derived


def _evaluate_candidate(
    *, candidate: Path, evaluator: Path, output: Path, image: str, timeout_seconds: int
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="ael-ci11-evaluate-", dir="/private/tmp") as temp:
        fixture = Path(temp)
        shutil.copytree(candidate, fixture / "candidate", symlinks=True)
        shutil.copytree(evaluator, fixture / "evaluator", symlinks=True)
        result = run_container(
            fixture,
            output,
            ["python3", "evaluator/evaluate.py", "candidate", "truth.json"],
            image=image,
            network_policy="none",
            timeout_seconds=timeout_seconds,
            cpus="1",
            memory="512m",
            pids_limit=128,
            workspace_size="512m",
            tmp_size="128m",
        )
    if result.exit_code != 0:
        raise SandboxError("private evaluator did not terminate successfully")
    truth = load_json(output / "workspace" / "truth.json")
    if (
        truth.get("schema_version") != "ael.completion-integrity-private-evaluation/0.1"
        or truth.get("operational_valid") is not True
    ):
        raise SandboxError("private evaluator returned invalid or operationally invalid truth")
    return truth


def _new_attempt(
    *, freeze_sha256: str, entry: Mapping[str, Any], journal: Path, bindings: Mapping[str, Any]
) -> dict[str, Any]:
    attempt = {
        "schema_version": ATTEMPT_SCHEMA,
        "attempt_id": _attempt_id(freeze_sha256, str(entry["cell_id"])),
        "freeze_sha256": freeze_sha256,
        "sequence": entry["sequence"],
        "cell_id": entry["cell_id"],
        "task_id": entry["task_id"],
        "role": entry["role"],
        "condition_id": entry["condition_id"],
        "state": "prepared",
        "prepared_at": utc_now(),
        "submitted_at": None,
        "terminal_at": None,
        "input_bindings": dict(bindings),
    }
    append_attempt_event(journal, attempt)
    return attempt


def _submit(attempt: dict[str, Any], journal: Path) -> None:
    attempt["state"] = "submitted"
    attempt["submitted_at"] = utc_now()
    append_attempt_event(journal, attempt)


def _terminal(attempt: dict[str, Any], journal: Path, *, status: str, cell_path: Path) -> None:
    attempt["state"] = "terminal"
    attempt["terminal_at"] = utc_now()
    attempt["status"] = status
    attempt["cell_sha256"] = sha256_path(cell_path)
    append_attempt_event(journal, attempt)


def _ambiguous(attempt: dict[str, Any], journal: Path, error: BaseException) -> None:
    attempt["state"] = "ambiguous"
    attempt["terminal_at"] = utc_now()
    attempt["error_type"] = type(error).__name__
    attempt["error"] = str(error)
    append_attempt_event(journal, attempt)


def _run_executor(
    *,
    entry: Mapping[str, Any],
    task_root: Path,
    raw_root: Path,
    freeze: Mapping[str, Any],
    freeze_sha256: str,
    auth_file: Path,
    study_root: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    cell_id = str(entry["cell_id"])
    task_id = str(entry["task_id"])
    prompt_path = study_root / "prompts" / "executor.txt"
    prompt = prompt_path.read_text(encoding="utf-8")
    fixture = _executor_fixture(
        task_root=task_root,
        study_root=study_root,
        raw_root=raw_root,
        task_id=task_id,
    )
    journal = raw_root / "attempts" / cell_id
    attempt = _new_attempt(
        freeze_sha256=freeze_sha256,
        entry=entry,
        journal=journal,
        bindings={
            "fixture_sha256": tree_sha256(fixture),
            "prompt_sha256": sha256_path(prompt_path),
            "model": freeze["runtime"]["model"],
            "reasoning_effort": freeze["runtime"]["reasoning_effort"],
            "image_id": freeze["runtime"]["executor_image_id"],
        },
    )
    output = raw_root / "runs" / cell_id
    evaluation_output = raw_root / "evaluations" / cell_id
    _submit(attempt, journal)
    try:
        result = run_activation_executor(
            fixture,
            output,
            auth_file,
            prompt=prompt,
            model=str(freeze["runtime"]["model"]),
            reasoning_effort=str(freeze["runtime"]["reasoning_effort"]),
            image=str(freeze["runtime"]["executor_image"]),
            proxy_image=str(freeze["runtime"]["proxy_image"]),
            timeout_seconds=int(freeze["budget"]["executor_timeout_seconds"]),
        )
    except BaseException as exc:
        _ambiguous(attempt, journal, exc)
        raise
    issues: list[str] = []
    if result.exit_code != 0:
        issues.append("executor_nonzero_exit")
    if _tree_size(output) > int(freeze["budget"]["max_output_bytes_per_cell"]):
        issues.append("executor_output_limit_exceeded")
    invocation = load_json(output / "sandbox-invocation.json")
    if (
        invocation.get("fixture_sha256_before") != invocation.get("fixture_sha256_after")
        or invocation.get("image_id") != freeze["runtime"]["executor_image_id"]
    ):
        issues.append("executor_fixture_or_image_binding_failed")
    secret_scan = invocation.get("secret_persistence_scan")
    if not isinstance(secret_scan, Mapping) or secret_scan.get("exact_value_match_count") != 0:
        issues.append("executor_credential_persistence_scan_failed")
    event_bundle = parse_codex_events(output / "stdout.log")
    final_output = load_json(output / "workspace" / "AEL_FINAL.json")
    candidate = output / "workspace"
    evaluation = _evaluate_candidate(
        candidate=candidate,
        evaluator=task_root / "evaluator",
        output=evaluation_output,
        image=str(freeze["runtime"]["evaluator_image"]),
        timeout_seconds=int(freeze["budget"]["evaluator_timeout_seconds"]),
    )
    requirements = parse_task_requirements(task_root / "fixture" / "TASK.md")
    method_plan = load_json(study_root / "method-plan.json")
    normalized = normalize_executor_capture(
        task_id=task_id,
        requirement_ids=[row["requirement_id"] for row in requirements],
        method_plan=method_plan,
        policy_bytes=prompt_path.read_bytes(),
        executor_output=final_output,
        codex_events=event_bundle["events"],
    )
    capture = diagnose_policy_enactment(
        normalized["method_plan"], normalized["observation"], prompt_path.read_bytes()
    )
    executor_assessment = assess_executor_claim(
        executor_output=final_output,
        evaluation=evaluation,
        codex_events=event_bundle["events"],
    )
    artifact_sha256 = tree_sha256(candidate)
    evidence = evidence_payload(
        task_id=task_id,
        attempt_id=str(attempt["attempt_id"]),
        artifact_sha256=artifact_sha256,
        requirements=requirements,
        evaluation=evaluation,
        capture=capture,
    )
    evidence_bundle_sha256 = canonical_sha256(evidence)
    dossier = load_json(task_root / "dossier.json")
    evaluator_binding = dossier.get("evaluator_custody")
    if not isinstance(evaluator_binding, Mapping):
        raise SandboxError("private task lacks evaluator custody binding")
    truth = build_frozen_truth(
        task_id=task_id,
        attempt_id=str(attempt["attempt_id"]),
        artifact_sha256=artifact_sha256,
        evidence_bundle_sha256=evidence_bundle_sha256,
        evaluation=evaluation,
        evaluator_sha256=str(evaluator_binding["evaluator_sha256"]),
        custody_receipt_sha256=str(evaluator_binding["receipt_sha256"]),
    )
    task_derived = raw_root / "derived" / task_id
    evidence_root = task_derived / "reporter-evidence"
    evidence_root.mkdir(parents=True, mode=0o700)
    write_json_atomic(evidence_root / "EVIDENCE.json", evidence)
    shutil.copyfile(
        study_root / "reporter-output-schema.json",
        evidence_root / "reporter-output-schema.json",
    )
    write_json_atomic(task_derived / "truth.json", truth)
    write_json_atomic(task_derived / "capture.json", capture)
    write_json_atomic(task_derived / "executor-assessment.json", executor_assessment)
    status = "valid" if not issues else "invalid"
    cell = {
        "schema_version": CELL_SCHEMA,
        **dict(entry),
        "attempt_id": attempt["attempt_id"],
        "status": status,
        "issues": issues,
        "usage": {
            **event_bundle["usage"],
            "wall_time_ms": result.duration_ms,
        },
        "event_count": event_bundle["event_count"],
        "artifact_sha256": artifact_sha256,
        "evidence_bundle_sha256": evidence_bundle_sha256,
        "evidence_tree_sha256": tree_sha256(evidence_root),
        "truth_sha256": canonical_sha256(truth),
        "capture_state": capture["state"],
        "executor_claim_agreement": executor_assessment.get("agreement"),
        "private_refs": {
            "events_sha256": sha256_path(output / "stdout.log"),
            "candidate_tree_sha256": artifact_sha256,
            "evaluation_sha256": canonical_sha256(evaluation),
            "capture_sha256": canonical_sha256(capture),
            "assessment_sha256": canonical_sha256(executor_assessment),
        },
    }
    cell_path = raw_root / "cells" / f"{cell_id}.json"
    write_json_atomic(cell_path, cell)
    _terminal(attempt, journal, status=status, cell_path=cell_path)
    context = {
        "task_id": task_id,
        "executor_attempt_id": attempt["attempt_id"],
        "artifact_sha256": artifact_sha256,
        "evidence_bundle_sha256": evidence_bundle_sha256,
        "evidence_tree_sha256": tree_sha256(evidence_root),
        "truth": truth,
        "evidence_root": str(evidence_root),
    }
    return cell, context


def _run_reporter(
    *,
    entry: Mapping[str, Any],
    context: Mapping[str, Any],
    raw_root: Path,
    freeze: Mapping[str, Any],
    freeze_sha256: str,
    auth_file: Path,
    study_root: Path,
) -> dict[str, Any]:
    cell_id = str(entry["cell_id"])
    task_id = str(entry["task_id"])
    condition_id = str(entry["condition_id"])
    prompt_path = study_root / "prompts" / f"reporter-{condition_id}.txt"
    prompt = prompt_path.read_text(encoding="utf-8")
    evidence_root = Path(str(context["evidence_root"]))
    expected_tree = str(context["evidence_tree_sha256"])
    if tree_sha256(evidence_root) != expected_tree:
        raise SandboxError("sealed reporter evidence changed before submission")
    journal = raw_root / "attempts" / cell_id
    attempt = _new_attempt(
        freeze_sha256=freeze_sha256,
        entry=entry,
        journal=journal,
        bindings={
            "evidence_tree_sha256": expected_tree,
            "evidence_bundle_sha256": context["evidence_bundle_sha256"],
            "prompt_sha256": sha256_path(prompt_path),
            "output_schema_sha256": sha256_path(study_root / "reporter-output-schema.json"),
            "model": freeze["runtime"]["model"],
            "reasoning_effort": freeze["runtime"]["reasoning_effort"],
            "image_id": freeze["runtime"]["reporter_image_id"],
        },
    )
    output = raw_root / "runs" / cell_id
    _submit(attempt, journal)
    try:
        result = run_codex_reporter(
            evidence_root,
            output,
            auth_file,
            prompt=prompt,
            model=str(freeze["runtime"]["model"]),
            reasoning_effort=str(freeze["runtime"]["reasoning_effort"]),
            image=str(freeze["runtime"]["reporter_image"]),
            proxy_image=str(freeze["runtime"]["proxy_image"]),
            timeout_seconds=int(freeze["budget"]["reporter_timeout_seconds"]),
        )
    except BaseException as exc:
        _ambiguous(attempt, journal, exc)
        raise
    issues: list[str] = []
    if result.exit_code != 0:
        issues.append("reporter_nonzero_exit")
    if _tree_size(output) > int(freeze["budget"]["max_output_bytes_per_cell"]):
        issues.append("reporter_output_limit_exceeded")
    event_bundle = parse_codex_events(output / "stdout.log")
    invocation = load_json(output / "sandbox-invocation.json")
    container_result = load_json(output / "container-result.json")
    model_output = load_json(output / "reporter-submission.json")
    submission = build_reporter_submission(
        task_id=task_id,
        condition_id=condition_id,
        attempt_id=str(context["executor_attempt_id"]),
        artifact_sha256=str(context["artifact_sha256"]),
        evidence_bundle_sha256=str(context["evidence_bundle_sha256"]),
        model_output=model_output,
    )
    assessment = assess_terminal_claim(
        load_json(study_root / "terminal-claim-policy.json"),
        context["truth"],
        submission,
    )
    evidence_hash_match = (
        invocation.get("fixture_sha256_before") == expected_tree
        and invocation.get("fixture_sha256_after") == expected_tree
        and container_result.get("evidence_sha256_before") == expected_tree
        and container_result.get("evidence_sha256_after") == expected_tree
        and tree_sha256(evidence_root) == expected_tree
    )
    workspace_unchanged = evidence_hash_match
    exposed = any(
        container_result.get(key) is not False
        for key in (
            "task_artifact_mounted",
            "evaluator_mounted",
            "executor_workspace_mounted",
        )
    )
    secret_scan = invocation.get("secret_persistence_scan")
    if not isinstance(secret_scan, Mapping) or secret_scan.get("exact_value_match_count") != 0:
        issues.append("reporter_credential_persistence_scan_failed")
    if invocation.get("image_id") != freeze["runtime"]["reporter_image_id"]:
        issues.append("reporter_image_binding_failed")
    if not evidence_hash_match:
        issues.append("reporter_evidence_identity_failed")
    if exposed:
        issues.append("reporter_forbidden_mount_exposed")
    if assessment.get("status") == "invalid":
        issues.append("reporter_claim_structure_invalid")
    status = "valid" if not issues else "invalid"
    agreement = assessment.get("status") == "pass"
    cell = {
        "schema_version": CELL_SCHEMA,
        **dict(entry),
        "attempt_id": attempt["attempt_id"],
        "status": status,
        "issues": issues,
        "usage": {
            **event_bundle["usage"],
            "wall_time_ms": result.duration_ms,
        },
        "event_count": event_bundle["event_count"],
        "tool_event_count": reporter_tool_event_count(event_bundle["events"]),
        "claim_agreement": agreement,
        "workspace_unchanged": workspace_unchanged,
        "evidence_hash_match": evidence_hash_match,
        "artifact_or_evaluator_exposed": exposed,
        "evidence_tree_sha256": expected_tree,
        "private_refs": {
            "events_sha256": sha256_path(output / "stdout.log"),
            "submission_sha256": canonical_sha256(submission),
            "assessment_sha256": canonical_sha256(assessment),
        },
    }
    write_json_atomic(raw_root / "assessments" / f"{cell_id}.json", assessment)
    cell_path = raw_root / "cells" / f"{cell_id}.json"
    write_json_atomic(cell_path, cell)
    _terminal(attempt, journal, status=status, cell_path=cell_path)
    return cell


def _observations(
    *,
    freeze: Mapping[str, Any],
    freeze_sha256: str,
    preregistration_sha: str,
    cells: Mapping[str, Mapping[str, Any]],
    protocol_issues: list[str],
) -> dict[str, Any]:
    tasks = []
    for task_id, ecosystem in (("CI2-PY-01", "python"), ("CI2-TS-01", "typescript")):
        executor = cells.get(f"{task_id}-E0")
        reporter_rows = []
        for condition_id in ("B0", "T1"):
            reporter = cells.get(f"{task_id}-{condition_id}")
            reporter_rows.append(
                {
                    "condition_id": condition_id,
                    "status": reporter.get("status", "unrun") if reporter else "unrun",
                    "claim_agreement": reporter.get("claim_agreement") if reporter else None,
                    "workspace_unchanged": bool(reporter and reporter.get("workspace_unchanged")),
                    "evidence_hash_match": bool(reporter and reporter.get("evidence_hash_match")),
                    "artifact_or_evaluator_exposed": bool(
                        reporter and reporter.get("artifact_or_evaluator_exposed")
                    ),
                    "tool_event_count": int(reporter.get("tool_event_count", 0)) if reporter else 0,
                }
            )
        tasks.append(
            {
                "task_id": task_id,
                "ecosystem": ecosystem,
                "executor_status": executor.get("status", "unrun") if executor else "unrun",
                "executor_claim_agreement": executor.get("executor_claim_agreement")
                if executor
                else None,
                "capture_state": executor.get("capture_state", "not_assessable")
                if executor
                else "not_assessable",
                "evidence_packet_sha256": executor.get("evidence_bundle_sha256", "0" * 64)
                if executor
                else "0" * 64,
                "truth_sha256": executor.get("truth_sha256", "0" * 64) if executor else "0" * 64,
                "artifact_sha256": executor.get("artifact_sha256", "0" * 64)
                if executor
                else "0" * 64,
                "reporters": reporter_rows,
            }
        )
    schedule_complete = len(cells) == len(freeze["schedule"]) and not protocol_issues
    return {
        "schema_version": ACTIVATION_SCHEMA_VERSION,
        "freeze_sha256": freeze_sha256,
        "preregistration_sha": preregistration_sha,
        "task_pack_sha256": freeze["private_pack"]["supply_artifact_sha256"],
        "qualification_sha256": freeze["qualification"]["receipt_sha256"],
        "schedule_complete": schedule_complete,
        "protocol_issues": sorted(set(protocol_issues)),
        "tasks": tasks,
    }


def run_activation(args: argparse.Namespace) -> dict[str, Any]:
    freeze_path = args.freeze.absolute()
    study_root = freeze_path.parent
    if (
        study_root.is_symlink()
        or not study_root.is_dir()
        or not study_root.resolve().is_relative_to(ROOT.resolve())
    ):
        raise SandboxError("activation study root is missing or unsafe")
    pack_root = args.pack_root.absolute()
    qualification_root = args.qualification_root.absolute()
    assessment_path = args.assessment.absolute()
    freeze = verify_freeze(
        freeze_path,
        pack_root=pack_root,
        qualification_root=qualification_root,
        assessment_path=assessment_path,
    )
    verify_preregistration(freeze_path, args.preregistration_sha)
    raw_root = _private_root(args.raw_root)
    if shutil.disk_usage(raw_root).free < int(freeze["budget"]["minimum_free_disk_bytes"]):
        raise SandboxError("insufficient free disk for frozen activation budget")
    task_roots = _task_map(pack_root)
    cells: dict[str, dict[str, Any]] = {}
    contexts: dict[str, dict[str, Any]] = {}
    protocol_issues: list[str] = []
    freeze_sha256 = sha256_path(freeze_path)
    for entry in freeze["schedule"]:
        cell_id = str(entry["cell_id"])
        task_id = str(entry["task_id"])
        try:
            if entry["role"] == "executor":
                cell, context = _run_executor(
                    entry=entry,
                    task_root=task_roots[task_id],
                    raw_root=raw_root,
                    freeze=freeze,
                    freeze_sha256=freeze_sha256,
                    auth_file=args.auth_file,
                    study_root=study_root,
                )
                cells[cell_id] = cell
                contexts[task_id] = context
            else:
                if task_id not in contexts:
                    raise SandboxError("reporter schedule reached before terminal executor context")
                cells[cell_id] = _run_reporter(
                    entry=entry,
                    context=contexts[task_id],
                    raw_root=raw_root,
                    freeze=freeze,
                    freeze_sha256=freeze_sha256,
                    auth_file=args.auth_file,
                    study_root=study_root,
                )
        except BaseException as exc:
            journal = raw_root / "attempts" / cell_id
            events = read_attempt_journal(journal)
            if events and events[-1].get("state") == "submitted":
                _ambiguous(dict(events[-1]), journal, exc)
            protocol_issues.append(f"{cell_id}:{type(exc).__name__}")
            break
        if cells[cell_id]["status"] != "valid":
            protocol_issues.extend(f"{cell_id}:{issue}" for issue in cells[cell_id]["issues"])
            break
    observations = _observations(
        freeze=freeze,
        freeze_sha256=freeze_sha256,
        preregistration_sha=args.preregistration_sha,
        cells=cells,
        protocol_issues=protocol_issues,
    )
    validate_observations(observations)
    decision = decide_activation(
        observations,
        decision_id=decision_id_from_study_id(freeze["study_id"]),
    )
    write_json_atomic(raw_root / "observations.json", observations)
    write_json_atomic(raw_root / "decision.json", decision)
    write_json_atomic(
        raw_root / "run-summary.json",
        {
            "schema_version": "ael.completion-integrity-activation-run-summary/0.1-pilot",
            "freeze_sha256": freeze_sha256,
            "preregistration_sha": args.preregistration_sha,
            "terminal_cells": len(cells),
            "scheduled_cells": len(freeze["schedule"]),
            "protocol_issues": protocol_issues,
            "decision_disposition": decision["disposition"],
            "observations_sha256": canonical_sha256(observations),
        },
    )
    return decision


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Execute a frozen Completion Integrity activation schedule"
    )
    parser.add_argument("--freeze", type=Path, default=DEFAULT_STUDY_ROOT / "freeze.json")
    parser.add_argument("--preregistration-sha", required=True)
    parser.add_argument("--pack-root", required=True, type=Path)
    parser.add_argument("--qualification-root", required=True, type=Path)
    parser.add_argument("--assessment", required=True, type=Path)
    parser.add_argument("--raw-root", required=True, type=Path)
    parser.add_argument("--auth-file", required=True, type=Path)
    args = parser.parse_args()
    try:
        decision = run_activation(args)
    except SandboxError as exc:
        print(f"Completion Integrity activation stopped: {exc}")
        return 1
    print(
        "Completion Integrity activation terminal: "
        f"status={decision['status']} disposition={decision['disposition']}"
    )
    return 0 if decision["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
