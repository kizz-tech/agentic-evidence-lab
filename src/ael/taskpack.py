from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from ael.sandbox import DEFAULT_IMAGE, SandboxError, run_container, tree_sha256


@dataclass(frozen=True)
class TaskHealth:
    task_id: str
    fixture_sha256: str
    visible_exit_code: int
    pristine_acceptance_exit_code: int
    healthy: bool


@dataclass(frozen=True)
class CandidateEvaluation:
    task_id: str
    candidate_sha256: str
    visible_exit_code: int
    acceptance_exit_code: int
    accepted: bool


def _tasks(root: Path) -> list[tuple[str, Path, Path]]:
    tasks_root = root.resolve() / "tasks"
    if not tasks_root.is_dir():
        raise SandboxError(f"missing task directory: {tasks_root}")
    found: list[tuple[str, Path, Path]] = []
    for task_root in sorted(path for path in tasks_root.iterdir() if path.is_dir()):
        fixture = task_root / "fixture"
        evaluator = task_root / "evaluator"
        if not (fixture / "TASK.md").is_file():
            raise SandboxError(f"task {task_root.name} is missing fixture/TASK.md")
        if not (evaluator / "test_acceptance.py").is_file():
            raise SandboxError(f"task {task_root.name} is missing evaluator/test_acceptance.py")
        found.append((task_root.name, fixture, evaluator))
    if not found:
        raise SandboxError(f"no tasks found in {tasks_root}")
    return found


def check_adaptation_pack(
    root: Path, output: Path, *, image: str = DEFAULT_IMAGE
) -> dict[str, object]:
    root = root.resolve()
    output = output.resolve()
    if output.exists():
        if not output.is_dir() or any(output.iterdir()):
            raise SandboxError(f"task-pack output must be a new or empty directory: {output}")
    else:
        output.mkdir(parents=True, mode=0o700)

    results: list[TaskHealth] = []
    for task_id, fixture, evaluator in _tasks(root):
        task_output = output / task_id
        task_output.mkdir()
        visible = run_container(
            fixture,
            task_output / "visible",
            ["python", "-m", "unittest", "discover", "-s", "tests", "-v"],
            image=image,
        )
        with tempfile.TemporaryDirectory(prefix=f"ael-{task_id}-", dir=output) as temporary:
            staging = Path(temporary)
            shutil.copytree(fixture, staging / "candidate", symlinks=True)
            shutil.copytree(evaluator, staging / "evaluator", symlinks=True)
            acceptance = run_container(
                staging,
                task_output / "pristine-acceptance",
                ["python", "evaluator/test_acceptance.py", "candidate"],
                image=image,
            )
        healthy = visible.exit_code == 0 and acceptance.exit_code != 0
        results.append(
            TaskHealth(
                task_id=task_id,
                fixture_sha256=tree_sha256(fixture),
                visible_exit_code=visible.exit_code,
                pristine_acceptance_exit_code=acceptance.exit_code,
                healthy=healthy,
            )
        )

    summary: dict[str, object] = {
        "schema_version": "ael.task-pack-health/0.1",
        "task_pack": root.name,
        "task_count": len(results),
        "healthy": all(item.healthy for item in results),
        "tasks": [asdict(item) for item in results],
    }
    (output / "task-pack-health.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def evaluate_candidate(
    task_root: Path,
    candidate: Path,
    output: Path,
    *,
    image: str = DEFAULT_IMAGE,
) -> dict[str, object]:
    task_root = task_root.resolve()
    candidate = candidate.resolve()
    output = output.resolve()
    evaluator = task_root / "evaluator"
    if not (task_root / "fixture" / "TASK.md").is_file():
        raise SandboxError(f"task root is invalid: {task_root}")
    if not (evaluator / "test_acceptance.py").is_file():
        raise SandboxError(f"task evaluator is missing: {evaluator}")
    if not candidate.is_dir():
        raise SandboxError(f"candidate workspace is missing: {candidate}")
    if output.exists():
        if not output.is_dir() or any(output.iterdir()):
            raise SandboxError(f"candidate output must be a new or empty directory: {output}")
    else:
        output.mkdir(parents=True, mode=0o700)

    visible = run_container(
        candidate,
        output / "visible",
        ["python", "-m", "unittest", "discover", "-s", "tests", "-v"],
        image=image,
    )
    with tempfile.TemporaryDirectory(
        prefix=f"ael-evaluate-{task_root.name}-", dir=output
    ) as temporary:
        staging = Path(temporary)
        shutil.copytree(candidate, staging / "candidate", symlinks=True)
        shutil.copytree(evaluator, staging / "evaluator", symlinks=True)
        acceptance = run_container(
            staging,
            output / "acceptance",
            ["python", "evaluator/test_acceptance.py", "candidate"],
            image=image,
        )

    evaluation = CandidateEvaluation(
        task_id=task_root.name,
        candidate_sha256=tree_sha256(candidate),
        visible_exit_code=visible.exit_code,
        acceptance_exit_code=acceptance.exit_code,
        accepted=visible.exit_code == 0 and acceptance.exit_code == 0,
    )
    summary: dict[str, object] = {
        "schema_version": "ael.candidate-evaluation/0.1",
        **asdict(evaluation),
    }
    (output / "candidate-evaluation.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary
