from __future__ import annotations

import hashlib
import json
import re
import shlex
from pathlib import Path
from typing import Any

from ael.sandbox import SandboxError

ACTIVATION_SCHEMA_VERSION = "ael.codex-skill-activation/0.1"
MAX_EVENT_BYTES = 64 * 1024 * 1024
MAX_EVENT_LINES = 100_000
_SKILL_NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,127}$")
_READERS = {"cat", "head", "sed", "tail"}
_REJECTED_SHELL_CONTROLS = {";", "&", "|", "||", "<", ">", ">>"}


def _command_retrieves_skill(command: str, skill_path_suffix: str) -> bool:
    try:
        outer = shlex.split(command)
    except ValueError:
        return False
    if not outer:
        return False
    executable = Path(outer[0]).name
    if executable in {"bash", "sh", "zsh"}:
        try:
            command_index = outer.index("-lc") + 1
            inner = outer[command_index]
        except (ValueError, IndexError):
            return False
        lexer = shlex.shlex(inner, posix=True, punctuation_chars=";&|<>")
        lexer.whitespace_split = True
        try:
            tokens = list(lexer)
        except ValueError:
            return False
    else:
        tokens = outer
    if not tokens:
        return False
    segments: list[list[str]] = [[]]
    for token in tokens:
        if token == "&&":
            if not segments[-1]:
                return False
            segments.append([])
        else:
            segments[-1].append(token)
    if not segments[-1]:
        return False
    return any(
        Path(segment[0]).name in _READERS
        and not any(token in _REJECTED_SHELL_CONTROLS for token in segment)
        and any(token.endswith(skill_path_suffix) for token in segment[1:])
        for segment in segments
    )


def audit_skill_activation(events_path: Path, skill_name: str) -> dict[str, Any]:
    if _SKILL_NAME.fullmatch(skill_name) is None:
        raise SandboxError("skill name must use normalized lowercase letters, digits, and hyphens")
    events_path = events_path.absolute()
    if not events_path.is_file() or events_path.is_symlink():
        raise SandboxError("Codex event input must be a regular, non-symlink file")
    events_path = events_path.resolve()
    if events_path.stat().st_size > MAX_EVENT_BYTES:
        raise SandboxError(f"Codex event input exceeds {MAX_EVENT_BYTES} bytes")

    skill_path_suffix = f"/home/.codex/skills/{skill_name}/SKILL.md"
    matches: list[dict[str, str]] = []
    event_count = 0
    try:
        with events_path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if line_number > MAX_EVENT_LINES:
                    raise SandboxError(f"Codex event input exceeds {MAX_EVENT_LINES} lines")
                if not line.strip():
                    continue
                event_count += 1
                try:
                    event = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise SandboxError(
                        f"invalid Codex JSON event at line {line_number}: {exc}"
                    ) from exc
                if not isinstance(event, dict):
                    raise SandboxError(f"Codex event at line {line_number} must be an object")
                item = event.get("item")
                if (
                    event.get("type") != "item.completed"
                    or not isinstance(item, dict)
                    or item.get("type") != "command_execution"
                    or item.get("status") != "completed"
                    or item.get("exit_code") != 0
                ):
                    continue
                command = item.get("command")
                if not isinstance(command, str) or not _command_retrieves_skill(
                    command, skill_path_suffix
                ):
                    continue
                output = item.get("aggregated_output")
                if not isinstance(output, str) or not output.strip():
                    continue
                item_id = item.get("id")
                matches.append(
                    {
                        "item_id": item_id if isinstance(item_id, str) else "",
                        "command_sha256": hashlib.sha256(command.encode("utf-8")).hexdigest(),
                        "output_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest(),
                    }
                )
    except (OSError, UnicodeError) as exc:
        raise SandboxError(f"Codex event input is unreadable: {exc}") from exc

    return {
        "schema_version": ACTIVATION_SCHEMA_VERSION,
        "skill_name": skill_name,
        "activated": bool(matches),
        "evidence_semantics": "a completed successful allowlisted read command retrieved non-empty exact-path SKILL.md content into the Codex turn",
        "event_count": event_count,
        "matched_commands": matches,
    }
