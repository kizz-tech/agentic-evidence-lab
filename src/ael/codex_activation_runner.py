"""Versioned Codex executor adapter for Completion Integrity activation v1.

This module is separate from :mod:`ael.codex_runner` so the historical alpha.9
runner bytes and freeze binding remain unchanged.
"""

from __future__ import annotations

from pathlib import Path

from ael.sandbox import (
    DEFAULT_CODEX_IMAGE,
    DEFAULT_EGRESS_IMAGE,
    SandboxError,
    SandboxResult,
    run_container,
)

DEFAULT_MODEL = "gpt-5.6-sol"
DEFAULT_REASONING_EFFORT = "xhigh"
DEFAULT_TIMEOUT_SECONDS = 1800


def activation_executor_command(model: str, reasoning_effort: str, *, prompt: str) -> list[str]:
    if not model.strip():
        raise SandboxError("Codex activation model is required")
    if reasoning_effort not in {"low", "medium", "high", "xhigh", "max", "ultra"}:
        raise SandboxError(f"unsupported activation reasoning effort: {reasoning_effort}")
    if not prompt.strip():
        raise SandboxError("Codex activation prompt is required")
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
        "--output-schema",
        "/fixture/.ael/executor-output-schema.json",
        "--output-last-message",
        "/workspace/repo/AEL_FINAL.json",
        prompt,
    ]


def run_activation_executor(
    fixture: Path,
    output: Path,
    auth_file: Path,
    *,
    prompt: str,
    model: str = DEFAULT_MODEL,
    reasoning_effort: str = DEFAULT_REASONING_EFFORT,
    image: str = DEFAULT_CODEX_IMAGE,
    proxy_image: str = DEFAULT_EGRESS_IMAGE,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> SandboxResult:
    return run_container(
        fixture,
        output,
        activation_executor_command(model, reasoning_effort, prompt=prompt),
        image=image,
        proxy_image=proxy_image,
        timeout_seconds=timeout_seconds,
        network_policy="openai-proxy",
        auth_file=auth_file,
    )
