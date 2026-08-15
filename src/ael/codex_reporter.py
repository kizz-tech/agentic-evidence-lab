"""Narrow Codex CLI adapter for reporter-only Completion Integrity sessions."""

from __future__ import annotations

from pathlib import Path

from ael.sandbox import (
    DEFAULT_EGRESS_IMAGE,
    SandboxError,
    SandboxResult,
    run_container,
)

DEFAULT_REPORTER_IMAGE = "kizz/ael-codex-reporter:0.146.0"
DEFAULT_MODEL = "gpt-5.6-sol"
DEFAULT_REASONING_EFFORT = "xhigh"
DEFAULT_TIMEOUT_SECONDS = 900


def reporter_command(model: str, reasoning_effort: str, *, prompt: str) -> list[str]:
    """Build the frozen non-resumable reporter command.

    The CLI still has its built-in command tool.  The capability boundary is
    therefore evidence-only and non-mutating, not tool-free: the process starts
    in the read-only evidence mount, has no task/evaluator/executor workspace,
    requests the Codex read-only sandbox, and emits one schema-bound final file.
    """

    if not model.strip():
        raise SandboxError("Codex reporter model is required")
    if reasoning_effort not in {"low", "medium", "high", "xhigh", "max", "ultra"}:
        raise SandboxError(f"unsupported reporter reasoning effort: {reasoning_effort}")
    if not prompt.strip():
        raise SandboxError("Codex reporter prompt is required")
    return [
        "codex",
        "exec",
        "--json",
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "--strict-config",
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        "--model",
        model,
        "--config",
        f'model_reasoning_effort="{reasoning_effort}"',
        "--config",
        'service_tier="default"',
        "--config",
        'approval_policy="never"',
        "--color",
        "never",
        "--output-schema",
        "/fixture/reporter-output-schema.json",
        "--output-last-message",
        "/output/reporter-submission.json",
        prompt,
    ]


def run_codex_reporter(
    evidence: Path,
    output: Path,
    auth_file: Path,
    *,
    prompt: str,
    model: str = DEFAULT_MODEL,
    reasoning_effort: str = DEFAULT_REASONING_EFFORT,
    image: str = DEFAULT_REPORTER_IMAGE,
    proxy_image: str = DEFAULT_EGRESS_IMAGE,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> SandboxResult:
    return run_container(
        evidence,
        output,
        reporter_command(model, reasoning_effort, prompt=prompt),
        image=image,
        proxy_image=proxy_image,
        timeout_seconds=timeout_seconds,
        network_policy="openai-proxy",
        auth_file=auth_file,
        cpus="1",
        memory="1g",
        pids_limit=128,
        workspace_size="512m",
        tmp_size="128m",
    )
