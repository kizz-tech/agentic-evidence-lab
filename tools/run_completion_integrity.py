from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from completion_integrity_support import (
    append_attempt_event,
    evaluate_candidate,
    read_attempt_journal,
    read_pack,
    scan_public_boundary,
    write_json_atomic,
)

from ael.codex_runner import run_codex_task
from ael.completion_integrity import (
    OBSERVATIONS_SCHEMA_VERSION,
    declaration_markers,
    derive_cell_outcome,
    text_sha256,
)
from ael.prospective_study import load_json_object, sha256_path
from ael.sandbox import SandboxError, inspect_image, tree_sha256

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "src" / "ael" / "completion_integrity.py"
RUNNER_PATH = Path(__file__).resolve()
MATERIALIZER_PATH = ROOT / "tools" / "materialize_completion_integrity.py"
AUDIT_PATH = ROOT / "src" / "ael" / "completion_integrity_audit.py"
SUPPORT_PATH = ROOT / "tools" / "completion_integrity_support.py"
CODEX_RUNNER_PATH = ROOT / "src" / "ael" / "codex_runner.py"
SANDBOX_PATH = ROOT / "src" / "ael" / "sandbox.py"
PROSPECTIVE_PATH = ROOT / "src" / "ael" / "prospective_study.py"
VALIDATION_PATH = ROOT / "src" / "ael" / "validation.py"
SCHEMAS_PATH = ROOT / "src" / "ael" / "schemas"


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_usage(events: Path) -> tuple[dict[str, int], int]:
    usage = {
        "input_tokens": 0,
        "cached_input_tokens": 0,
        "output_tokens": 0,
        "reasoning_output_tokens": 0,
    }
    event_count = 0
    try:
        lines = events.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise SandboxError(f"Codex event stream is unreadable: {exc}") from exc
    for line in lines:
        if not line.strip():
            continue
        event_count += 1
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SandboxError(f"Codex event stream contains invalid JSON: {exc}") from exc
        if event.get("type") == "turn.completed" and isinstance(event.get("usage"), dict):
            for key in usage:
                value = event["usage"].get(key, 0)
                if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                    usage[key] = value
    return usage, event_count


def prompt_bytes(common_path: Path, policy_path: Path) -> tuple[str, str]:
    common = common_path.read_text(encoding="utf-8").rstrip("\n")
    policy = policy_path.read_text(encoding="utf-8").rstrip("\n")
    if not common or not policy:
        raise SandboxError("Completion Integrity prompt files must be non-empty")
    return common, f"{common}\n\n{policy}"


def prepared_fixture(task: Mapping[str, Any], variant: str, root: Path) -> Path:
    source = Path(task["root"]) / "fixture"
    target = root / str(task["task_id"]) / variant
    shutil.copytree(source, target, symlinks=True)
    if variant == "paraphrase":
        paraphrase = Path(task["root"]) / "paraphrase" / "TASK.md"
        if paraphrase.is_symlink() or not paraphrase.is_file():
            raise SandboxError(f"task lacks its frozen paraphrase: {task['task_id']}")
        shutil.copyfile(paraphrase, target / "TASK.md")
    elif variant != "original":
        raise SandboxError(f"unsupported task variant: {variant}")
    tree_sha256(target)
    return target


def _tree_size(root: Path) -> int:
    total = 0
    for path in root.rglob("*"):
        if path.is_symlink():
            raise SandboxError(f"run output contains a symlink: {path}")
        if path.is_file():
            total += path.stat().st_size
    return total


def _private_refs(run_output: Path, evaluation_output: Path) -> dict[str, str]:
    paths = {
        "invocation_sha256": run_output / "sandbox-invocation.json",
        "events_sha256": run_output / "stdout.log",
        "stderr_sha256": run_output / "stderr.log",
        "score_sha256": evaluation_output / "workspace" / "score.json",
    }
    refs: dict[str, str] = {}
    for key, path in paths.items():
        refs[key] = sha256_path(path) if path.is_file() and not path.is_symlink() else "0" * 64
    workspace = run_output / "workspace"
    refs["candidate_tree_sha256"] = tree_sha256(workspace) if workspace.is_dir() else "0" * 64
    return refs


def _attempt_id(freeze_sha256: str, cell_id: str) -> str:
    return hashlib.sha256(f"{freeze_sha256}:{cell_id}".encode()).hexdigest()[:32]


def _assert_private_raw_root(raw_root: Path) -> None:
    absolute = raw_root.absolute()
    repository = ROOT.resolve()
    if absolute.resolve(strict=False).is_relative_to(repository):
        raise SandboxError("raw Completion Integrity evidence must remain outside the Git root")
    if raw_root.is_symlink():
        raise SandboxError("raw Completion Integrity evidence root must not be a symlink")


def run_cell(
    *,
    entry: Mapping[str, Any],
    task: Mapping[str, Any],
    fixture: Path,
    raw_root: Path,
    auth_file: Path,
    prompt: str,
    runner_image: str,
    proxy_image: str,
    evaluator_image: str,
    model: str,
    reasoning_effort: str,
    timeout_seconds: int,
    max_generated_tokens: int,
    max_output_bytes: int,
    freeze_sha256: str,
) -> dict[str, Any]:
    cell_id = str(entry["cell_id"])
    attempt_journal = raw_root / "attempts" / cell_id
    observation_path = raw_root / "cells" / f"{cell_id}.json"
    attempt_id = _attempt_id(freeze_sha256, cell_id)
    events = read_attempt_journal(attempt_journal)
    if observation_path.exists():
        if not events or events[-1].get("state") != "terminal":
            raise SandboxError(f"cell observation exists without terminal attempt: {cell_id}")
        return load_json_object(observation_path)
    if events:
        attempt = events[-1]
        if attempt.get("state") in {"submitted", "ambiguous"}:
            raise SandboxError(
                f"cell has an ambiguous submitted attempt and cannot retry: {cell_id}"
            )
        if attempt.get("state") != "prepared":
            raise SandboxError(f"cell has an unsupported attempt state: {cell_id}")
    else:
        attempt = {
            "schema_version": "ael.completion-integrity-attempt/0.1-pilot",
            "attempt_id": attempt_id,
            "freeze_sha256": freeze_sha256,
            "cell_id": cell_id,
            "sequence": entry["sequence"],
            "state": "prepared",
            "prepared_at": utc_now(),
            "submitted_at": None,
            "terminal_at": None,
            "input_bindings": {
                "fixture_sha256": tree_sha256(fixture),
                "prompt_sha256": text_sha256(prompt),
                "task_id": entry["task_id"],
                "condition_id": entry["condition_id"],
                "variant": entry["variant"],
                "model": model,
                "reasoning_effort": reasoning_effort,
            },
        }
        append_attempt_event(attempt_journal, attempt)

    run_output = raw_root / "runs" / cell_id
    evaluation_output = raw_root / "evaluations" / cell_id
    if run_output.exists() or evaluation_output.exists():
        raise SandboxError(f"non-terminal cell already has output and cannot retry: {cell_id}")
    attempt["state"] = "submitted"
    attempt["submitted_at"] = utc_now()
    append_attempt_event(attempt_journal, attempt)
    started_at = utc_now()
    try:
        result = run_codex_task(
            fixture,
            run_output,
            auth_file,
            model=model,
            reasoning_effort=reasoning_effort,
            image=runner_image,
            proxy_image=proxy_image,
            timeout_seconds=timeout_seconds,
            prompt=prompt,
        )
    except BaseException as exc:
        attempt["state"] = "ambiguous"
        attempt["terminal_at"] = utc_now()
        attempt["error"] = f"{type(exc).__name__}: {exc}"
        append_attempt_event(attempt_journal, attempt)
        raise
    completed_at = utc_now()

    invalid_reasons: list[str] = []
    invocation_path = run_output / "sandbox-invocation.json"
    events_path = run_output / "stdout.log"
    invocation = load_json_object(invocation_path)
    if result.exit_code != 0:
        invalid_reasons.append("Codex did not reach a normal terminal state")
    if invocation.get("fixture_sha256_before") != invocation.get("fixture_sha256_after"):
        invalid_reasons.append("canonical fixture identity changed")
    secret_scan = invocation.get("secret_persistence_scan")
    if not isinstance(secret_scan, dict) or secret_scan.get("exact_value_match_count") != 0:
        invalid_reasons.append("credential persistence scan failed")
    usage, event_count = parse_usage(events_path)
    generated_tokens = usage["output_tokens"] + usage["reasoning_output_tokens"]
    budget_exceeded = generated_tokens > max_generated_tokens
    if _tree_size(run_output) > max_output_bytes:
        invalid_reasons.append("persisted run output exceeded the frozen byte ceiling")

    try:
        score = evaluate_candidate(
            Path(task["root"]),
            run_output / "workspace",
            evaluation_output,
            evaluator_image=evaluator_image,
        )
    except SandboxError as exc:
        invalid_reasons.append(f"evaluator failure: {exc}")
        score = {
            "operational_valid": False,
            "visible_tests_pass": False,
            "accepted": False,
            "regression": False,
            "critical_failure": False,
            "requirements": {},
            "omitted_requirement_ids": [],
            "error": str(exc),
        }

    status = "operational_invalid" if invalid_reasons else "valid"
    if budget_exceeded and status == "valid":
        score["accepted"] = False
        score["omitted_requirement_ids"] = sorted(
            {*score["omitted_requirement_ids"], "AEL-RUNTIME-BUDGET"}
        )
    final_path = run_output / "workspace" / "AEL_FINAL.md"
    final_text = final_path.read_text(encoding="utf-8") if final_path.is_file() else ""
    markers = declaration_markers(final_text)
    observation: dict[str, Any] = {
        "schema_version": "ael.completion-integrity-cell/0.1-pilot",
        **entry,
        "attempt_id": attempt_id,
        "status": status,
        "invalid_reasons": invalid_reasons,
        "operator_recorded_started_at": started_at,
        "operator_recorded_completed_at": completed_at,
        "declaration_markers": markers,
        "final_message_sha256": text_sha256(final_text),
        "evaluator": {
            "operational_valid": bool(score["operational_valid"]),
            "visible_tests_pass": bool(score["visible_tests_pass"]),
            "accepted": bool(score["accepted"]),
            "regression": bool(score["regression"]),
            "critical_failure": bool(score["critical_failure"]),
            "requirements": score["requirements"],
            "omitted_requirement_ids": score["omitted_requirement_ids"],
        },
        "budget_exceeded": budget_exceeded,
        "usage": {
            **usage,
            "generated_tokens": generated_tokens,
            "wall_time_ms": result.duration_ms,
        },
        "event_count": event_count,
        "private_refs": _private_refs(run_output, evaluation_output),
    }
    observation["derived"] = derive_cell_outcome(observation)
    write_json_atomic(observation_path, observation)
    attempt["state"] = "terminal"
    attempt["terminal_at"] = utc_now()
    attempt["observation_sha256"] = sha256_path(observation_path)
    append_attempt_event(attempt_journal, attempt)
    return observation


def _aggregate_observations(
    freeze_sha256: str,
    schedule: list[dict[str, Any]],
    retained: Mapping[str, Mapping[str, Any]],
    *,
    stopped_reason: str | None,
) -> dict[str, Any]:
    observations: list[dict[str, Any]] = []
    for entry in schedule:
        cell_id = str(entry["cell_id"])
        if cell_id in retained:
            observations.append(dict(retained[cell_id]))
        else:
            observations.append(
                {
                    "schema_version": "ael.completion-integrity-cell/0.1-pilot",
                    **entry,
                    "attempt_id": None,
                    "status": "missing",
                    "invalid_reasons": [stopped_reason or "cell was not submitted"],
                    "operator_recorded_started_at": None,
                    "operator_recorded_completed_at": None,
                    "declaration_markers": [],
                    "final_message_sha256": "0" * 64,
                    "evaluator": None,
                    "budget_exceeded": False,
                    "usage": None,
                    "event_count": 0,
                    "private_refs": {},
                    "derived": derive_cell_outcome({"status": "missing"}),
                }
            )
    return {
        "schema_version": OBSERVATIONS_SCHEMA_VERSION,
        "freeze_sha256": freeze_sha256,
        "stopped_reason": stopped_reason,
        "observations": observations,
    }


def _calibrate(args: argparse.Namespace) -> int:
    pack_root = args.pack_root.absolute()
    gate = load_json_object(args.gate)
    if gate.get("status") != "pass" or gate.get("private_pack_ref", {}).get(
        "sha256"
    ) != tree_sha256(pack_root):
        raise SandboxError("sacrificial calibration requires the passing gate for this pack")
    pack, tasks = read_pack(pack_root)
    calibration_tasks = [tasks["CAL-01"], tasks["CAL-02"]]
    common = args.common_prompt.read_text(encoding="utf-8").rstrip("\n")
    raw_root = args.raw_root.absolute()
    _assert_private_raw_root(raw_root)
    if raw_root.exists() and any(raw_root.iterdir()):
        raise SandboxError("sacrificial calibration root must be new or empty")
    raw_root.mkdir(parents=True, mode=0o700, exist_ok=True)
    scan_public_boundary(pack_root, ROOT)
    observations: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="ael-ci9-calibration-", dir="/private/tmp") as temp:
        for sequence, task in enumerate(calibration_tasks, start=1):
            entry = {
                "cell_id": f"{task['task_id']}-B0-CAL01-original",
                "sequence": sequence,
                "phase": "calibration",
                "stage": "sacrificial",
                "variant": "original",
                "task_id": task["task_id"],
                "task_role": "calibration",
                "mechanism": task["mechanism"],
                "stratum": task["stratum"],
                "condition_id": "B0",
                "repeat_index": 1,
            }
            fixture = prepared_fixture(task, "original", Path(temp))
            observation = run_cell(
                entry=entry,
                task=task,
                fixture=fixture,
                raw_root=raw_root,
                auth_file=args.auth_file,
                prompt=common,
                runner_image=args.runner_image,
                proxy_image=args.proxy_image,
                evaluator_image=args.evaluator_image,
                model=args.model,
                reasoning_effort=args.reasoning_effort,
                timeout_seconds=args.timeout_seconds,
                max_generated_tokens=args.max_generated_tokens,
                max_output_bytes=args.max_output_bytes,
                freeze_sha256=sha256_path(args.gate),
            )
            observations.append(observation)
            print(
                f"calibration {entry['cell_id']}: status={observation['status']} "
                f"false_completion={observation['derived']['false_completion']}"
            )
            if observation["status"] != "valid":
                break
    false_completion_count = sum(
        observation["derived"]["false_completion"] is True for observation in observations
    )
    status = (
        "pass"
        if len(observations) == 2
        and all(observation["status"] == "valid" for observation in observations)
        and false_completion_count >= 1
        else "fail"
    )
    public = {
        "schema_version": "ael.completion-integrity-headroom/0.1-pilot",
        "headroom_id": "kizz:ael:completion-integrity:baseline-headroom:1",
        "status": status,
        "recorded_at": args.recorded_at,
        "gate_ref": {"uri": str(args.gate), "sha256": sha256_path(args.gate)},
        "private_pack_sha256": tree_sha256(pack_root),
        "private_pack_revision": pack["revision"],
        "condition_id": "B0",
        "runtime": {
            "model": args.model,
            "reasoning_effort": args.reasoning_effort,
            "harness": "codex-cli",
            "harness_version": "0.146.0",
        },
        "task_count": 2,
        "retained_count": len(observations),
        "false_completion_count": false_completion_count,
        "cells": [
            {
                "task_id": row["task_id"],
                "mechanism": row["mechanism"],
                "status": row["status"],
                "declaration_state": row["derived"]["declaration_state"],
                "accepted_final_state": row["derived"]["accepted_final_state"],
                "false_completion": row["derived"]["false_completion"],
                "private_refs": row["private_refs"],
            }
            for row in observations
        ],
        "interpretation": (
            "A pass establishes baseline headroom on two excluded sacrificial cases; "
            "it is not part of the scored effect estimate."
        ),
    }
    write_json_atomic(args.output, public)
    if status != "pass":
        raise SandboxError("sacrificial baseline calibration did not establish headroom")
    print(f"baseline headroom passed: {args.output} sha256={sha256_path(args.output)}")
    return 0


def _execute(args: argparse.Namespace) -> int:
    freeze_path = args.freeze.resolve()
    freeze = load_json_object(freeze_path)
    freeze_sha256 = sha256_path(freeze_path)
    pack_root = args.pack_root.absolute()
    _, tasks = read_pack(pack_root)
    if freeze.get("schema_version") != "ael.completion-integrity-freeze/0.1-pilot":
        raise SandboxError("unsupported Completion Integrity freeze")
    if freeze.get("private_pack", {}).get("sha256") != tree_sha256(pack_root):
        raise SandboxError("private pack no longer matches the freeze")
    code = freeze.get("code_hashes", {})
    observed_code = {
        "policy": sha256_path(POLICY_PATH),
        "runner": sha256_path(RUNNER_PATH),
        "support": sha256_path(SUPPORT_PATH),
        "codex_runner": sha256_path(CODEX_RUNNER_PATH),
        "sandbox": sha256_path(SANDBOX_PATH),
        "prospective_study": sha256_path(PROSPECTIVE_PATH),
        "materializer": sha256_path(MATERIALIZER_PATH),
        "audit": sha256_path(AUDIT_PATH),
        "validation": sha256_path(VALIDATION_PATH),
        "contract_schemas": tree_sha256(SCHEMAS_PATH),
    }
    if code != observed_code:
        raise SandboxError("freeze-bound Completion Integrity code has drifted")
    runtime = freeze["runtime"]
    for image_key, id_key in (
        ("runner_image", "runner_image_id"),
        ("proxy_image", "proxy_image_id"),
        ("evaluator_image", "evaluator_image_id"),
    ):
        if inspect_image(runtime[image_key]) != runtime[id_key]:
            raise SandboxError(f"freeze-bound runtime image drifted: {image_key}")
    common, treatment = prompt_bytes(args.common_prompt, args.policy_prompt)
    if text_sha256(common) != freeze["prompts"]["B0"]["sha256"]:
        raise SandboxError("baseline prompt no longer matches the freeze")
    if text_sha256(treatment) != freeze["prompts"]["T1"]["sha256"]:
        raise SandboxError("treatment prompt no longer matches the freeze")
    scan_public_boundary(pack_root, ROOT)
    raw_root = args.raw_root.absolute()
    _assert_private_raw_root(raw_root)
    raw_root.mkdir(parents=True, mode=0o700, exist_ok=True)
    lock_path = raw_root / ".operator-lock"
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise SandboxError("Completion Integrity operator lock already exists") from exc
    os.close(descriptor)
    retained: dict[str, Mapping[str, Any]] = {}
    stopped_reason: str | None = None
    try:
        schedule = freeze["schedule"]
        if len(schedule) != freeze["budget"]["max_scored_calls"]:
            raise SandboxError("freeze call budget does not equal schedule length")
        submitted = (
            len(list((raw_root / "attempts").glob("*/02-submitted.json")))
            if (raw_root / "attempts").is_dir()
            else 0
        )
        if submitted > len(schedule):
            raise SandboxError("attempt ledger exceeds the frozen call budget")
        for entry in schedule:
            free_bytes = shutil.disk_usage(raw_root).free
            if free_bytes < freeze["budget"]["minimum_free_disk_bytes"]:
                stopped_reason = "host disk reserve fell below the frozen minimum"
                break
            cell_path = raw_root / "cells" / f"{entry['cell_id']}.json"
            if cell_path.is_file():
                observation = load_json_object(cell_path)
                retained[str(entry["cell_id"])] = observation
                if observation.get("status") != "valid":
                    stopped_reason = "a retained cell is operationally invalid"
                    break
                continue
            expected_sequence = len(retained) + 1
            if entry["sequence"] != expected_sequence:
                raise SandboxError("strict schedule sequence cannot be resumed safely")
            task = tasks[str(entry["task_id"])]
            with tempfile.TemporaryDirectory(
                prefix=f"ael-ci9-{entry['task_id']}-", dir="/private/tmp"
            ) as temporary:
                fixture = prepared_fixture(task, str(entry["variant"]), Path(temporary))
                try:
                    observation = run_cell(
                        entry=entry,
                        task=task,
                        fixture=fixture,
                        raw_root=raw_root,
                        auth_file=args.auth_file,
                        prompt=common if entry["condition_id"] == "B0" else treatment,
                        runner_image=runtime["runner_image"],
                        proxy_image=runtime["proxy_image"],
                        evaluator_image=runtime["evaluator_image"],
                        model=runtime["model"],
                        reasoning_effort=runtime["reasoning_effort"],
                        timeout_seconds=freeze["budget"]["per_cell_timeout_seconds"],
                        max_generated_tokens=freeze["budget"]["max_generated_tokens_per_cell"],
                        max_output_bytes=freeze["budget"]["max_output_bytes_per_cell"],
                        freeze_sha256=freeze_sha256,
                    )
                except BaseException as exc:
                    stopped_reason = f"ambiguous or failed submission at {entry['cell_id']}: {exc}"
                    break
            retained[str(entry["cell_id"])] = observation
            print(
                f"cell {entry['sequence']:02d}/52 {entry['cell_id']}: "
                f"status={observation['status']} accepted={observation['derived']['accepted_final_state']} "
                f"declaration={observation['derived']['declaration_state']}"
            )
            if observation["status"] != "valid":
                stopped_reason = f"operationally invalid cell: {entry['cell_id']}"
                break
        document = _aggregate_observations(
            freeze_sha256, schedule, retained, stopped_reason=stopped_reason
        )
        write_json_atomic(raw_root / "observations.json", document)
    finally:
        lock_path.unlink(missing_ok=True)
    if stopped_reason:
        raise SandboxError(stopped_reason)
    print(f"scored schedule completed: {len(retained)} cells")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    calibrate = commands.add_parser("calibrate")
    calibrate.add_argument("--pack-root", required=True, type=Path)
    calibrate.add_argument("--gate", required=True, type=Path)
    calibrate.add_argument("--common-prompt", required=True, type=Path)
    calibrate.add_argument("--raw-root", required=True, type=Path)
    calibrate.add_argument("--auth-file", required=True, type=Path)
    calibrate.add_argument("--output", required=True, type=Path)
    calibrate.add_argument("--recorded-at", required=True)
    calibrate.add_argument("--runner-image", default="kizz/ael-codex-runner:0.146.0")
    calibrate.add_argument("--proxy-image", default="kizz/ael-egress-proxy:0.1.0-alpha.1")
    calibrate.add_argument("--evaluator-image", default="kizz/ael-runner:0.1.0-alpha.1")
    calibrate.add_argument("--model", default="gpt-5.6-sol")
    calibrate.add_argument("--reasoning-effort", default="xhigh")
    calibrate.add_argument("--timeout-seconds", type=int, default=900)
    calibrate.add_argument("--max-generated-tokens", type=int, default=30000)
    calibrate.add_argument("--max-output-bytes", type=int, default=134217728)
    calibrate.set_defaults(handler=_calibrate)

    execute = commands.add_parser("execute")
    execute.add_argument("--freeze", required=True, type=Path)
    execute.add_argument("--pack-root", required=True, type=Path)
    execute.add_argument("--common-prompt", required=True, type=Path)
    execute.add_argument("--policy-prompt", required=True, type=Path)
    execute.add_argument("--raw-root", required=True, type=Path)
    execute.add_argument("--auth-file", required=True, type=Path)
    execute.set_defaults(handler=_execute)
    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
