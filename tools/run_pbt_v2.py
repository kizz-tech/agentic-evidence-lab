from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

import ael.pbt_pilot as pbt_pilot
from ael.codex_runner import run_codex_task
from ael.pbt_pilot import pbt_confirmation_unlocked
from ael.sandbox import SandboxError, run_container, tree_sha256
from ael.study_freeze import (
    OBSERVATIONS_SCHEMA_VERSION,
    load_json_object,
    validate_freeze_bundle,
    verify_private_pack,
)
from ael.validation import sha256_path

STUDY_PROMPT = (
    "Implement the task described in TASK.md in this workspace. Work autonomously: inspect the "
    "relevant code, make only supportable changes, strengthen tests where useful, and run the "
    "checks needed for your claims. Do not access external services. In the final response, report "
    "the intended effect, changed files, exact checks and results, limitations, and the precise "
    "completion state."
)
SKILL_NAME = "property-based-testing"


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
        if not isinstance(task_id, str) or not isinstance(relative, str):
            raise SandboxError("private task entry lacks identity or path")
        task_root = (root / relative).resolve()
        if not task_root.is_relative_to(root) or not (task_root / "fixture" / "TASK.md").is_file():
            raise SandboxError(f"private task is unavailable: {task_id}")
        if not (task_root / "evaluator" / "test_score.py").is_file():
            raise SandboxError(f"private evaluator is unavailable: {task_id}")
        result[task_id] = {**task, "root": task_root}
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
        if event.get("type") == "turn.completed":
            usage.update(event.get("usage", {}))
        if marker in line:
            activated = True
    return usage, count, activated


def evaluate(task_root: Path, pack_root: Path, candidate: Path, output: Path) -> dict[str, object]:
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ael-pbt-score-", dir=output.parent) as temporary:
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
        raise SandboxError("PBT evaluator did not produce a score")
    score = load_json_object(score_path)
    if score.get("schema_version") != "ael.pbt-score/0.1":
        raise SandboxError("PBT evaluator produced an unsupported score")
    return score


def write_observations(root: Path, phase: str, freeze_hash: str | None) -> Path:
    observations = [load_json_object(path) for path in sorted(root.glob("*-R*-observation.json"))]
    document = {
        "schema_version": OBSERVATIONS_SCHEMA_VERSION,
        "phase": phase,
        "freeze_sha256": freeze_hash,
        "observations": observations,
    }
    output = root / "observations.json"
    output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def schedule_for(
    phase: str,
    bundle: dict[str, object] | None,
    tasks: dict[str, dict[str, object]],
    repeat_limit: int,
) -> list[dict[str, object]]:
    if phase == "sacrificial":
        return [
            {
                "sequence": index,
                "task_id": task_id,
                "condition_id": "B0",
                "repeat_index": 1,
            }
            for index, task_id in enumerate(sorted(tasks), start=1)
        ]
    assert bundle is not None
    return [
        entry for entry in bundle["schedule"][phase] if int(entry["repeat_index"]) <= repeat_limit
    ]


def run_cell(
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
    repeat_index = int(entry["repeat_index"])
    stem = f"{task_id}-{condition_id}-R{repeat_index:02d}"
    run_output = raw_root / stem
    evaluation_output = raw_root / f"{stem}-evaluation"
    observation_path = raw_root / f"{stem}-observation.json"
    if observation_path.exists():
        return load_json_object(observation_path)
    intervention = skill_root if condition_id == "S1" else None
    result = run_codex_task(
        Path(task["root"]) / "fixture",
        run_output,
        auth_file,
        intervention=intervention,
        skill_name=SKILL_NAME if intervention else None,
        timeout_seconds=timeout_seconds,
        prompt=STUDY_PROMPT,
    )
    invocation_path = run_output / "sandbox-invocation.json"
    events_path = run_output / "stdout.log"
    invocation = load_json_object(invocation_path)
    usage, event_count, activated = parse_usage(events_path)
    status = "valid"
    invalid_reasons: list[str] = []
    if result.exit_code != 0:
        status = "invalid"
        invalid_reasons.append("Codex did not reach a normal terminal state")
    if invocation.get("fixture_sha256_before") != invocation.get("fixture_sha256_after"):
        status = "invalid"
        invalid_reasons.append("canonical fixture changed")
    secret_scan = invocation.get("secret_persistence_scan", {})
    if secret_scan.get("exact_value_match_count", 0) != 0:
        status = "invalid"
        invalid_reasons.append("credential material appeared in persisted output")
    generated = int(usage["output_tokens"]) + int(usage["reasoning_output_tokens"])
    if generated > max_generated_tokens:
        status = "invalid"
        invalid_reasons.append("generated-token budget exceeded")
    try:
        score = evaluate(Path(task["root"]), pack_root, run_output / "workspace", evaluation_output)
    except SandboxError as exc:
        status = "invalid"
        invalid_reasons.append(str(exc))
        score = {
            "schema_version": "ael.pbt-score/0.1",
            "hidden_acceptance": False,
            "candidate_tests_pass": False,
            "reference_compatible_tests": False,
            "invalid_property": False,
            "flaky": False,
            "edge_test_added": False,
            "critical_failure": True,
            "accepted": False,
        }
        fallback_score = evaluation_output / "workspace" / "score.json"
        fallback_score.parent.mkdir(parents=True, exist_ok=True)
        fallback_score.write_text(
            json.dumps(score, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    observation = {
        "observation_id": f"pbt-v2:{task_id}:{condition_id}:{repeat_index}",
        "task_id": task_id,
        "stratum": task["stratum"],
        "condition_id": condition_id,
        "repeat_index": repeat_index,
        "schedule_sequence": entry["sequence"],
        "status": status,
        "invalid_reasons": invalid_reasons,
        "skill_activated": activated if condition_id == "S1" else False,
        "hidden_acceptance": bool(score["hidden_acceptance"]),
        "candidate_tests_pass": bool(score["candidate_tests_pass"]),
        "reference_compatible_tests": bool(score["reference_compatible_tests"]),
        "invalid_property": bool(score["invalid_property"]),
        "flaky": bool(score["flaky"]),
        "edge_test_added": bool(score["edge_test_added"]),
        "critical_failure": bool(score["critical_failure"]),
        "accepted": bool(score["accepted"]),
        "usage": {**usage, "generated_tokens": generated, "wall_time_ms": result.duration_ms},
        "event_count": event_count,
        "private_refs": {
            "invocation_sha256": sha256_path(invocation_path),
            "events_sha256": sha256_path(events_path),
            "candidate_tree_sha256": tree_sha256(run_output / "workspace"),
            "score_sha256": sha256_path(evaluation_output / "workspace" / "score.json"),
        },
    }
    observation_path.write_text(
        json.dumps(observation, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return observation


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase", required=True, choices=["sacrificial", "screening", "confirmation"]
    )
    parser.add_argument("--pack-root", required=True, type=Path)
    parser.add_argument("--raw-root", required=True, type=Path)
    parser.add_argument("--auth-file", required=True, type=Path)
    parser.add_argument("--skill-root", required=True, type=Path)
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--selection", type=Path)
    parser.add_argument("--repeat-limit", type=int, default=1)
    args = parser.parse_args()

    pack_root = args.pack_root.resolve()
    raw_root = args.raw_root.resolve()
    raw_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    pack = read_pack(pack_root)
    tasks = task_map(pack_root, pack)
    bundle: dict[str, object] | None = None
    freeze_hash: str | None = None
    if args.phase != "sacrificial":
        if args.bundle is None:
            raise SandboxError("scored phases require a public freeze bundle")
        bundle = load_json_object(args.bundle.resolve())
        issues = validate_freeze_bundle(bundle)
        if issues:
            raise SandboxError(f"freeze bundle has {len(issues)} issue(s)")
        verify_private_pack(bundle, args.phase, pack_root)
        freeze_hash = sha256_path(args.bundle.resolve())
        if sha256_path(Path(__file__).resolve()) != bundle["runner_code_sha256"]:
            raise SandboxError("runner code no longer matches the frozen hash")
        if sha256_path(Path(pbt_pilot.__file__).resolve()) != bundle["decision_code_sha256"]:
            raise SandboxError("decision code no longer matches the frozen hash")
        if pbt_pilot.execution_code_sha256() != bundle["execution_code_sha256"]:
            raise SandboxError("execution dependencies no longer match the frozen hash")
        prompt_hash = hashlib.sha256(STUDY_PROMPT.encode("utf-8")).hexdigest()
        if prompt_hash != bundle["prompt_sha256"]:
            raise SandboxError("study prompt no longer matches the frozen hash")
        if args.phase == "confirmation" and (
            args.selection is None
            or not pbt_confirmation_unlocked(args.bundle.resolve(), args.selection.resolve())
        ):
            raise SandboxError("confirmation is locked by the frozen selection rule")
        treatment = next(
            (
                condition
                for condition in bundle["conditions"]
                if condition.get("condition_id") == "S1"
            ),
            None,
        )
        if treatment is None:
            raise SandboxError("freeze bundle lacks the S1 treatment")
        if tree_sha256(args.skill_root.resolve()) != treatment["intervention_sha256"]:
            raise SandboxError("intervention tree does not match the frozen treatment")

    timeout = int(bundle["budget"]["per_run_timeout_seconds"]) if bundle else 900
    token_budget = int(bundle["budget"]["max_generated_tokens"]) if bundle else 30000
    schedule = schedule_for(args.phase, bundle, tasks, args.repeat_limit)
    for entry in schedule:
        task_id = str(entry["task_id"])
        if task_id not in tasks:
            raise SandboxError(f"scheduled task is absent from private pack: {task_id}")
        observation = run_cell(
            entry,
            tasks[task_id],
            pack_root,
            raw_root,
            args.auth_file.resolve(),
            args.skill_root.resolve(),
            timeout,
            token_budget,
        )
        print(
            f"cell complete: task={task_id} condition={entry['condition_id']} "
            f"repeat={entry['repeat_index']} status={observation['status']}"
        )
    observations_path = write_observations(raw_root, args.phase, freeze_hash)
    print(f"observations ready: {len(schedule)} scheduled cell(s) {observations_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
