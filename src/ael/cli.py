from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ael import __version__
from ael.calibration import run_calibration
from ael.codex_runner import (
    DEFAULT_CODEX_MODEL,
    DEFAULT_CODEX_TIMEOUT_SECONDS,
    DEFAULT_REASONING_EFFORT,
    run_codex_task,
)
from ael.render import render_receipt
from ael.sandbox import (
    DEFAULT_CODEX_IMAGE,
    DEFAULT_EGRESS_IMAGE,
    DEFAULT_IMAGE,
    NETWORK_POLICIES,
    SandboxError,
    build_image,
    docker_doctor,
    run_container,
)
from ael.taskpack import check_adaptation_pack, evaluate_candidate
from ael.validation import sha256_path, validate


def _validate(args: argparse.Namespace) -> int:
    documents, issues = validate(Path(path) for path in args.paths)
    if issues:
        for issue in issues:
            print(issue, file=sys.stderr)
        print(f"validation failed: {len(issues)} issue(s)", file=sys.stderr)
        return 1
    counts: dict[str, int] = {}
    for document in documents:
        counts[document.object_type] = counts.get(document.object_type, 0) + 1
    summary = ", ".join(f"{key}={counts[key]}" for key in sorted(counts))
    print(f"validation passed: {len(documents)} document(s); {summary}")
    return 0


def _hash(args: argparse.Namespace) -> int:
    for raw_path in args.paths:
        path = Path(raw_path).resolve()
        if not path.is_file():
            print(f"not a file: {path}", file=sys.stderr)
            return 1
        print(f"{sha256_path(path)}  {path}")
    return 0


def _render(args: argparse.Namespace) -> int:
    input_path = Path(args.receipt).resolve()
    try:
        receipt = json.loads(input_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"cannot read receipt: {exc}", file=sys.stderr)
        return 1
    _, issues = validate([input_path])
    schema_issues = [issue for issue in issues if "was not loaded" not in issue.message]
    if schema_issues:
        for issue in schema_issues:
            print(issue, file=sys.stderr)
        return 1
    rendered = render_receipt(receipt)
    if args.output:
        output_path = Path(args.output).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
        print(f"rendered {output_path}")
    else:
        print(rendered, end="")
    return 0


def _calibrate(args: argparse.Namespace) -> int:
    result = run_calibration(
        Path(args.config).resolve(),
        Path(args.output).resolve(),
        Path(args.report).resolve() if args.report else None,
    )
    print(
        f"calibration complete: {result['simulation_id']}; "
        f"iterations={result['iterations']}; assumptions={result['assumption_state']}"
    )
    return 0


def _sandbox_doctor(_args: argparse.Namespace) -> int:
    try:
        versions = docker_doctor()
    except SandboxError as exc:
        print(f"sandbox unavailable: {exc}", file=sys.stderr)
        return 1
    print(
        "sandbox available: "
        f"docker client={versions['client_version']} server={versions['server_version']}"
    )
    return 0


def _sandbox_build(args: argparse.Namespace) -> int:
    try:
        image_id = build_image(Path(args.context), args.tag)
    except SandboxError as exc:
        print(f"sandbox build failed: {exc}", file=sys.stderr)
        return 1
    print(f"sandbox image ready: {args.tag} {image_id}")
    return 0


def _sandbox_run(args: argparse.Namespace) -> int:
    command = list(args.container_command)
    if command and command[0] == "--":
        command = command[1:]
    try:
        result = run_container(
            Path(args.fixture),
            Path(args.output),
            command,
            image=args.image,
            timeout_seconds=args.timeout_seconds,
            cpus=args.cpus,
            memory=args.memory,
            pids_limit=args.pids_limit,
            workspace_size=args.workspace_size,
            tmp_size=args.tmp_size,
            network_policy=args.network_policy,
            proxy_image=args.proxy_image,
        )
    except SandboxError as exc:
        print(f"sandbox run failed: {exc}", file=sys.stderr)
        return 1
    print(
        f"sandbox run complete: exit={result.exit_code} duration_ms={result.duration_ms} "
        f"image={result.image_id} fixture={result.fixture_sha256} output={result.output}"
    )
    return result.exit_code


def _sandbox_codex(args: argparse.Namespace) -> int:
    if not args.trusted_input_only:
        print(
            "Codex sandbox run refused: hosted runs expose a reusable credential to the "
            "agent process. Re-run only for maintainer-controlled fixtures and interventions "
            "with --trusted-input-only.",
            file=sys.stderr,
        )
        return 2
    try:
        result = run_codex_task(
            Path(args.fixture),
            Path(args.output),
            Path(args.auth_file),
            intervention=Path(args.skill) if args.skill else None,
            skill_name=args.skill_name if args.skill else None,
            model=args.model,
            reasoning_effort=args.reasoning_effort,
            image=args.image,
            proxy_image=args.proxy_image,
            timeout_seconds=args.timeout_seconds,
        )
    except SandboxError as exc:
        print(f"Codex sandbox run failed: {exc}", file=sys.stderr)
        return 1
    print(
        f"Codex sandbox run complete: exit={result.exit_code} duration_ms={result.duration_ms} "
        f"image={result.image_id} fixture={result.fixture_sha256} output={result.output}"
    )
    return result.exit_code


def _taskpack_check(args: argparse.Namespace) -> int:
    try:
        result = check_adaptation_pack(Path(args.root), Path(args.output), image=args.image)
    except SandboxError as exc:
        print(f"task-pack check failed: {exc}", file=sys.stderr)
        return 1
    print(
        f"task-pack check complete: tasks={result['task_count']} healthy={result['healthy']} "
        f"output={Path(args.output).resolve()}"
    )
    return 0 if result["healthy"] else 1


def _taskpack_evaluate(args: argparse.Namespace) -> int:
    try:
        result = evaluate_candidate(
            Path(args.task_root),
            Path(args.workspace),
            Path(args.output),
            image=args.image,
        )
    except SandboxError as exc:
        print(f"candidate evaluation failed: {exc}", file=sys.stderr)
        return 1
    print(
        f"candidate evaluation complete: task={result['task_id']} accepted={result['accepted']} "
        f"visible={result['visible_exit_code']} acceptance={result['acceptance_exit_code']}"
    )
    return 0 if result["accepted"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ael", description="Agentic Evidence Lab contract tools")
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="validate AEL JSON documents")
    validate_parser.add_argument("paths", nargs="+", help="JSON file or directory")
    validate_parser.set_defaults(handler=_validate)

    hash_parser = subparsers.add_parser("hash", help="print SHA-256 for files")
    hash_parser.add_argument("paths", nargs="+")
    hash_parser.set_defaults(handler=_hash)

    render_parser = subparsers.add_parser(
        "render", aliases=["receipt"], help="render a validated receipt as Markdown"
    )
    render_parser.add_argument("receipt", help="evidence receipt JSON")
    render_parser.add_argument("--output", help="output Markdown path")
    render_parser.set_defaults(handler=_render)

    calibrate_parser = subparsers.add_parser(
        "calibrate", help="simulate study-design operating characteristics"
    )
    calibrate_parser.add_argument("config", help="calibration configuration JSON")
    calibrate_parser.add_argument("--output", required=True, help="simulation result JSON")
    calibrate_parser.add_argument("--report", help="optional Markdown report")
    calibrate_parser.set_defaults(handler=_calibrate)

    sandbox_parser = subparsers.add_parser(
        "sandbox", help="build and run the isolated Docker adapter"
    )
    sandbox_subparsers = sandbox_parser.add_subparsers(dest="sandbox_command", required=True)

    doctor_parser = sandbox_subparsers.add_parser(
        "doctor", help="check Docker client and engine availability"
    )
    doctor_parser.set_defaults(handler=_sandbox_doctor)

    sandbox_build_parser = sandbox_subparsers.add_parser(
        "build", help="build the pinned offline runner image"
    )
    sandbox_build_parser.add_argument(
        "--context", default="docker/runner", help="Docker build context"
    )
    sandbox_build_parser.add_argument("--tag", default=DEFAULT_IMAGE, help="runner image tag")
    sandbox_build_parser.set_defaults(handler=_sandbox_build)

    run_parser = sandbox_subparsers.add_parser(
        "run", help="run one command against a read-only fixture"
    )
    run_parser.add_argument(
        "--fixture", required=True, help="task fixture directory mounted read-only"
    )
    run_parser.add_argument("--output", required=True, help="new or empty private output directory")
    run_parser.add_argument("--image", default=DEFAULT_IMAGE, help="runner image")
    run_parser.add_argument("--timeout-seconds", type=int, default=900)
    run_parser.add_argument("--cpus", default="2")
    run_parser.add_argument("--memory", default="2g")
    run_parser.add_argument("--pids-limit", type=int, default=256)
    run_parser.add_argument("--workspace-size", default="1g")
    run_parser.add_argument("--tmp-size", default="256m")
    run_parser.add_argument("--network-policy", choices=NETWORK_POLICIES, default="none")
    run_parser.add_argument("--proxy-image", default=DEFAULT_EGRESS_IMAGE)
    run_parser.add_argument("container_command", nargs=argparse.REMAINDER, help="command after --")
    run_parser.set_defaults(handler=_sandbox_run)

    codex_parser = sandbox_subparsers.add_parser(
        "codex",
        help="run a pinned Codex CLI task through the controlled OpenAI egress proxy",
    )
    codex_parser.add_argument("--fixture", required=True, help="task fixture directory")
    codex_parser.add_argument(
        "--output", required=True, help="new or empty private output directory"
    )
    codex_parser.add_argument(
        "--auth-file", required=True, help="Codex auth.json mounted read-only"
    )
    codex_parser.add_argument(
        "--trusted-input-only",
        action="store_true",
        help="acknowledge that the fixture and intervention are maintainer-controlled",
    )
    codex_parser.add_argument("--skill", help="optional installable skill directory")
    codex_parser.add_argument("--skill-name", default="focused-change-verification")
    codex_parser.add_argument("--model", default=DEFAULT_CODEX_MODEL)
    codex_parser.add_argument("--reasoning-effort", default=DEFAULT_REASONING_EFFORT)
    codex_parser.add_argument("--image", default=DEFAULT_CODEX_IMAGE)
    codex_parser.add_argument("--proxy-image", default=DEFAULT_EGRESS_IMAGE)
    codex_parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_CODEX_TIMEOUT_SECONDS)
    codex_parser.set_defaults(handler=_sandbox_codex)

    taskpack_parser = subparsers.add_parser(
        "taskpack", help="validate executable task-pack behavior"
    )
    taskpack_subparsers = taskpack_parser.add_subparsers(dest="taskpack_command", required=True)
    taskpack_check_parser = taskpack_subparsers.add_parser(
        "check-adaptation",
        help="require visible tests to pass and pristine acceptance tests to fail",
    )
    taskpack_check_parser.add_argument("root", help="adaptation task-pack root")
    taskpack_check_parser.add_argument(
        "--output", required=True, help="new or empty private output directory"
    )
    taskpack_check_parser.add_argument("--image", default=DEFAULT_IMAGE)
    taskpack_check_parser.set_defaults(handler=_taskpack_check)
    taskpack_evaluate_parser = taskpack_subparsers.add_parser(
        "evaluate",
        help="run visible and held-out acceptance checks against an exported candidate workspace",
    )
    taskpack_evaluate_parser.add_argument("--task-root", required=True)
    taskpack_evaluate_parser.add_argument("--workspace", required=True)
    taskpack_evaluate_parser.add_argument("--output", required=True)
    taskpack_evaluate_parser.add_argument("--image", default=DEFAULT_IMAGE)
    taskpack_evaluate_parser.set_defaults(handler=_taskpack_evaluate)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
