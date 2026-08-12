from __future__ import annotations

from pathlib import Path

from ael.sandbox import (
    DEFAULT_CODEX_IMAGE,
    DEFAULT_EGRESS_IMAGE,
    SandboxError,
    SandboxResult,
    run_container,
)

DEFAULT_CODEX_MODEL = "gpt-5.6-sol"
DEFAULT_REASONING_EFFORT = "xhigh"
DEFAULT_CODEX_TIMEOUT_SECONDS = 1800


DEFAULT_TASK_PROMPT = (
    "Implement the task described in TASK.md in this workspace. Work autonomously: inspect the "
    "relevant owner code, make the focused change, and run the checks needed to support your "
    "claims. Do not access external services. In the final response, report the intended effect, "
    "changed files, exact checks and results, limitations, and the precise completion state."
)


def codex_command(
    model: str, reasoning_effort: str, *, prompt: str = DEFAULT_TASK_PROMPT
) -> list[str]:
    if not model.strip():
        raise SandboxError("Codex model is required")
    if reasoning_effort not in {"low", "medium", "high", "xhigh", "max", "ultra"}:
        raise SandboxError(f"unsupported reasoning effort: {reasoning_effort}")
    if not prompt.strip():
        raise SandboxError("Codex task prompt is required")
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
        "danger-full-access",
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
        "--output-last-message",
        "/workspace/repo/AEL_FINAL.md",
        prompt,
    ]


def run_codex_task(
    fixture: Path,
    output: Path,
    auth_file: Path,
    *,
    intervention: Path | None = None,
    skill_name: str | None = None,
    model: str = DEFAULT_CODEX_MODEL,
    reasoning_effort: str = DEFAULT_REASONING_EFFORT,
    image: str = DEFAULT_CODEX_IMAGE,
    proxy_image: str = DEFAULT_EGRESS_IMAGE,
    timeout_seconds: int = DEFAULT_CODEX_TIMEOUT_SECONDS,
    prompt: str = DEFAULT_TASK_PROMPT,
) -> SandboxResult:
    return run_container(
        fixture,
        output,
        codex_command(model, reasoning_effort, prompt=prompt),
        image=image,
        proxy_image=proxy_image,
        timeout_seconds=timeout_seconds,
        network_policy="openai-proxy",
        auth_file=auth_file,
        intervention=intervention,
        skill_name=skill_name,
    )
