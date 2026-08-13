from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

import ael.systematic_debugging_shadow as debugging_shadow
from ael.codex_runner import run_codex_task
from ael.prospective_study import (
    OBSERVATIONS_SCHEMA_VERSION,
    authorize_scored_run,
    load_json_object,
    sha256_path,
    validate_admission,
    validate_freeze,
    verify_private_pack,
)
from ael.sandbox import SandboxError, inspect_image, run_container, tree_sha256

STUDY_PROMPT = (
    "Implement the task described in TASK.md in this workspace. Work autonomously: reproduce the "
    "reported defect, inspect the relevant code and tests, identify the supportable root cause, make "
    "a focused repair, add or strengthen a regression test where useful, and run the checks needed "
    "for your claims. Do not access external services. In the final response, report the root cause, "
    "changed files, exact checks and results, limitations, and precise completion state."
)
SKILL_NAME = "systematic-debugging"
SCORE_SCHEMA_VERSION = "ael.debugging-shadow-score/0.1"


def _utc_now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_pack(root: Path) -> dict[str, object]:
    pack = load_json_object(root / "pack.json")
    if pack.get("schema_version") != "ael.private-task-pack/0.1":
        raise SandboxError("private task pack has an unsupported schema")
    tasks = pack.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise SandboxError("private task pack has no tasks")
    return pack


def task_map(root: Path, pack: dict[str, object]) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for task in pack["tasks"]:
        if not isinstance(task, dict):
            raise SandboxError("private task entry must be an object")
        task_id = task.get("task_id")
        relative = task.get("path")
        stratum = task.get("stratum")
        if not all(isinstance(value, str) and value for value in (task_id, relative, stratum)):
            raise SandboxError("private task entry lacks identity, path, or stratum")
        task_root = (root / str(relative)).resolve()
        if not task_root.is_relative_to(root):
            raise SandboxError(f"private task path escapes its pack: {task_id}")
        required = (
            task_root / "fixture" / "TASK.md",
            task_root / "evaluator" / "test_score.py",
            task_root / "dossier.json",
        )
        if any(path.is_symlink() or not path.is_file() for path in required):
            raise SandboxError(f"private task is incomplete or unsafe: {task_id}")
        if str(task_id) in result:
            raise SandboxError(f"duplicate private task ID: {task_id}")
        result[str(task_id)] = {**task, "root": task_root}
    return result


def parse_usage(events: Path) -> tuple[dict[str, int], int, bool]:
    usage = {
        "input_tokens": 0,
        "cached_input_tokens": 0,
        "output_tokens": 0,
        "reasoning_output_tokens": 0,
    }
    count = 0
    activated = False
    marker = f"home/.codex/skills/{SKILL_NAME}/SKILL.md"
    for line in events.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        count += 1
        event = json.loads(line)
        if event.get("type") == "turn.completed" and isinstance(event.get("usage"), dict):
            usage.update(event["usage"])
        if marker in line:
            activated = True
    return usage, count, activated


def evaluate(task_root: Path, pack_root: Path, candidate: Path, output: Path) -> dict[str, object]:
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ael-debug-score-", dir=output.parent) as temporary:
        staging = Path(temporary)
        shutil.copytree(candidate, staging / "candidate", symlinks=True)
        shutil.copytree(task_root / "evaluator", staging / "evaluator", symlinks=True)
        shutil.copyfile(pack_root / "evaluator_common.py", staging / "evaluator_common.py")
        result = run_container(
            staging,
            output,
            ["python", "evaluator/test_score.py", "candidate", "score.json"],
        )
    score_path = output / "workspace" / "score.json"
    if result.exit_code != 0 or not score_path.is_file():
        raise SandboxError("debugging evaluator did not produce a score")
    score = load_json_object(score_path)
    if score.get("schema_version") != SCORE_SCHEMA_VERSION:
        raise SandboxError("debugging evaluator produced an unsupported score")
    return score


def _bindings(
    *,
    admission_path: Path,
    manifest_path: Path,
    source_lock_path: Path,
    pack_root: Path,
    skill_root: Path,
    freeze: dict[str, object],
) -> dict[str, object]:
    root = Path(__file__).resolve().parents[1]
    materializer = root / "tools" / "materialize_systematic_debugging_shadow.py"
    return {
        "admission_sha256": sha256_path(admission_path),
        "manifest_sha256": sha256_path(manifest_path),
        "source_lock_sha256": sha256_path(source_lock_path),
        "candidate_tree_sha256": tree_sha256(skill_root),
        "private_pack_sha256": tree_sha256(pack_root),
        "runner_sha256": sha256_path(Path(__file__).resolve()),
        "decision_sha256": sha256_path(Path(debugging_shadow.__file__).resolve()),
        "materializer_sha256": sha256_path(materializer),
        "execution_sha256": debugging_shadow.execution_code_sha256(),
        "prompt_sha256": hashlib.sha256(STUDY_PROMPT.encode("utf-8")).hexdigest(),
        "runner_image_id": inspect_image(str(freeze["runtime"]["runner_image"])),
        "proxy_image_id": inspect_image(str(freeze["runtime"]["proxy_image"])),
        "evaluator_image_id": inspect_image(str(freeze["runtime"]["evaluator_image"])),
    }


def health_check(pack_root: Path) -> None:
    pack = read_pack(pack_root)
    tasks = task_map(pack_root, pack)
    with tempfile.TemporaryDirectory(prefix="ael-debug-health-", dir="/private/tmp") as temporary:
        output_root = Path(temporary)
        for task_id, task in sorted(tasks.items()):
            score = evaluate(
                Path(task["root"]),
                pack_root,
                Path(task["root"]) / "fixture",
                output_root / task_id,
            )
            expected = {
                "visible_tests_pass": True,
                "hidden_acceptance": False,
                "reference_compatible_tests": True,
                "critical_failure": False,
                "accepted": False,
            }
            if any(score.get(key) is not value for key, value in expected.items()):
                raise SandboxError(f"private task health failed: {task_id}: {score}")
            print(f"task health passed: {task_id} stratum={task['stratum']}")


def run_cell(
    *,
    entry: dict[str, object],
    task: dict[str, object],
    pack_root: Path,
    raw_root: Path,
    auth_file: Path,
    skill_root: Path,
    timeout_seconds: int,
    max_generated_tokens: int,
) -> dict[str, object]:
    task_id = str(entry["task_id"])
    condition_id = str(entry["condition_id"])
    stem = f"{task_id}-{condition_id}-R01"
    run_output = raw_root / stem
    evaluation_output = raw_root / f"{stem}-evaluation"
    observation_path = raw_root / f"{stem}-observation.json"
    if run_output.exists() or evaluation_output.exists() or observation_path.exists():
        raise SandboxError(f"scored cell path already exists; reconcile manually: {stem}")
    intervention = skill_root if condition_id == "S1" else None
    started_at = _utc_now()
    result = run_codex_task(
        Path(task["root"]) / "fixture",
        run_output,
        auth_file,
        intervention=intervention,
        skill_name=SKILL_NAME if intervention else None,
        timeout_seconds=timeout_seconds,
        prompt=STUDY_PROMPT,
    )
    completed_at = _utc_now()
    invocation_path = run_output / "sandbox-invocation.json"
    events_path = run_output / "stdout.log"
    invocation = load_json_object(invocation_path)
    usage, event_count, activated = parse_usage(events_path)
    status = "valid"
    invalid_reasons: list[str] = []
    if result.exit_code != 0:
        invalid_reasons.append("Codex did not reach a normal terminal state")
    if invocation.get("fixture_sha256_before") != invocation.get("fixture_sha256_after"):
        invalid_reasons.append("canonical fixture changed")
    secret_scan = invocation.get("secret_persistence_scan", {})
    if not isinstance(secret_scan, dict) or secret_scan.get("exact_value_match_count") != 0:
        invalid_reasons.append("credential persistence scan failed")
    generated = int(usage["output_tokens"]) + int(usage["reasoning_output_tokens"])
    if generated > max_generated_tokens:
        invalid_reasons.append("generated-token budget exceeded")
    try:
        score = evaluate(Path(task["root"]), pack_root, run_output / "workspace", evaluation_output)
    except SandboxError as exc:
        invalid_reasons.append(str(exc))
        score = {
            "visible_tests_pass": False,
            "hidden_acceptance": False,
            "root_cause_invariant_pass": False,
            "reference_compatible_tests": False,
            "safe_change_scope": False,
            "critical_failure": True,
            "accepted": False,
        }
    if invalid_reasons:
        status = "invalid"
    score_path = evaluation_output / "workspace" / "score.json"
    private_refs = {
        "invocation_sha256": sha256_path(invocation_path),
        "events_sha256": sha256_path(events_path),
        "candidate_tree_sha256": tree_sha256(run_output / "workspace"),
        "score_sha256": sha256_path(score_path) if score_path.is_file() else "0" * 64,
    }
    observation = {
        "observation_id": f"debug-shadow:{task_id}:{condition_id}:1",
        "task_id": task_id,
        "stratum": task["stratum"],
        "condition_id": condition_id,
        "repeat_index": 1,
        "schedule_sequence": entry["sequence"],
        "status": status,
        "invalid_reasons": invalid_reasons,
        "operator_recorded_started_at": started_at,
        "operator_recorded_completed_at": completed_at,
        "skill_activated": activated if condition_id == "S1" else False,
        "visible_tests_pass": bool(score["visible_tests_pass"]),
        "hidden_acceptance": bool(score["hidden_acceptance"]),
        "root_cause_invariant_pass": bool(score["root_cause_invariant_pass"]),
        "reference_compatible_tests": bool(score["reference_compatible_tests"]),
        "safe_change_scope": bool(score["safe_change_scope"]),
        "critical_failure": bool(score["critical_failure"]),
        "accepted": bool(score["accepted"]),
        "usage": {**usage, "generated_tokens": generated, "wall_time_ms": result.duration_ms},
        "event_count": event_count,
        "private_refs": private_refs,
    }
    observation_path.write_text(
        json.dumps(observation, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return observation


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--health-check", action="store_true")
    parser.add_argument("--pack-root", required=True, type=Path)
    parser.add_argument("--raw-root", type=Path)
    parser.add_argument("--auth-file", type=Path)
    parser.add_argument("--skill-root", type=Path)
    parser.add_argument("--freeze", type=Path)
    parser.add_argument("--admission", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--source-lock", type=Path)
    args = parser.parse_args()

    pack_root = args.pack_root.resolve()
    if args.health_check:
        health_check(pack_root)
        return 0
    required = {
        "raw_root": args.raw_root,
        "auth_file": args.auth_file,
        "skill_root": args.skill_root,
        "freeze": args.freeze,
        "admission": args.admission,
        "manifest": args.manifest,
        "source_lock": args.source_lock,
    }
    missing = sorted(key for key, value in required.items() if value is None)
    if missing:
        raise SandboxError(f"scored execution is missing arguments: {', '.join(missing)}")
    raw_root = args.raw_root.absolute()
    if raw_root.exists() and any(raw_root.iterdir()):
        raise SandboxError("scored run root must be new or empty")
    raw_root.mkdir(parents=True, mode=0o700, exist_ok=True)
    freeze_path = args.freeze.resolve()
    admission_path = args.admission.resolve()
    manifest_path = args.manifest.resolve()
    source_lock_path = args.source_lock.resolve()
    skill_root = args.skill_root.resolve()
    freeze = load_json_object(freeze_path)
    admission = load_json_object(admission_path)
    freeze_issues = validate_freeze(freeze)
    admission_issues = validate_admission(admission)
    if freeze_issues:
        raise SandboxError(f"freeze has {len(freeze_issues)} issue(s): {freeze_issues[0]}")
    if admission_issues:
        raise SandboxError(f"admission has {len(admission_issues)} issue(s): {admission_issues[0]}")
    pack = read_pack(pack_root)
    tasks = task_map(pack_root, pack)
    pack_digest = tree_sha256(pack_root)
    verify_private_pack(freeze, pack_root, pack_digest)
    observed = _bindings(
        admission_path=admission_path,
        manifest_path=manifest_path,
        source_lock_path=source_lock_path,
        pack_root=pack_root,
        skill_root=skill_root,
        freeze=freeze,
    )
    authorize_scored_run(admission, freeze, observed)
    observations: list[dict[str, object]] = []
    for entry in freeze["schedule"]:
        task_id = str(entry["task_id"])
        if task_id not in tasks:
            raise SandboxError(f"scheduled task is missing: {task_id}")
        authorize_scored_run(admission, freeze, observed)
        observation = run_cell(
            entry=entry,
            task=tasks[task_id],
            pack_root=pack_root,
            raw_root=raw_root,
            auth_file=args.auth_file.resolve(),
            skill_root=skill_root,
            timeout_seconds=int(freeze["budget"]["per_run_timeout_seconds"]),
            max_generated_tokens=int(freeze["budget"]["max_generated_tokens"]),
        )
        observations.append(observation)
        print(
            f"cell complete: sequence={entry['sequence']} task={task_id} "
            f"condition={entry['condition_id']} status={observation['status']}"
        )
        if observation["status"] != "valid":
            raise SandboxError("scored schedule stopped after an invalid cell")
    output = {
        "schema_version": OBSERVATIONS_SCHEMA_VERSION,
        "run_set_id": f"{freeze['freeze_id']}:run-set-1",
        "freeze_sha256": sha256_path(freeze_path),
        "chronology": "operator_recorded_not_independently_timestamped",
        "observations": observations,
    }
    (raw_root / "observations.json").write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
