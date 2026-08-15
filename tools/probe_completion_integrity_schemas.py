from __future__ import annotations

import argparse
import shutil
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from completion_integrity_activation_support import (
    canonical_sha256,
    load_json,
    parse_codex_events,
    sha256_path,
    write_json_atomic,
)
from jsonschema import Draft202012Validator

from ael.codex_activation_runner import (
    DEFAULT_MODEL,
    DEFAULT_REASONING_EFFORT,
    run_activation_executor,
)
from ael.codex_reporter import run_codex_reporter
from ael.sandbox import SandboxError

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STUDY_ROOT = ROOT / "studies" / "completion-integrity" / "activation-v2"
PROBE_SCHEMA = "ael.completion-integrity-schema-capability/0.1-pilot"
OBSERVED_UNSUPPORTED_KEYWORDS = {"uniqueItems"}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SandboxError(f"schema capability probe failed: {message}")


def _private_root(raw_root: Path) -> Path:
    raw_root = raw_root.absolute()
    _require(not raw_root.is_symlink(), "raw root must not be a symlink")
    _require(
        not raw_root.resolve(strict=False).is_relative_to(ROOT.resolve()),
        "raw root must remain outside Git",
    )
    _require(
        not raw_root.exists() or not any(raw_root.iterdir()),
        "raw root must be new or empty; never retry in place",
    )
    raw_root.mkdir(parents=True, mode=0o700, exist_ok=True)
    return raw_root


def _walk_schema(value: object, *, location: str = "$") -> None:
    if isinstance(value, Mapping):
        forbidden = OBSERVED_UNSUPPORTED_KEYWORDS.intersection(value)
        _require(not forbidden, f"{location} uses unsupported keywords: {sorted(forbidden)}")
        for key, child in value.items():
            _walk_schema(child, location=f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk_schema(child, location=f"{location}[{index}]")


def _validate_output(schema: Mapping[str, Any], output: Mapping[str, Any], *, role: str) -> None:
    issues = sorted(
        Draft202012Validator(schema).iter_errors(output), key=lambda issue: list(issue.path)
    )
    _require(
        not issues,
        f"{role} output violates exact local schema: {issues[0].message if issues else ''}",
    )


def _call_receipt(
    *,
    role: str,
    schema_path: Path,
    output_path: Path,
    invocation_path: Path,
    expected_output: Mapping[str, Any],
) -> dict[str, object]:
    invocation = load_json(invocation_path)
    events = parse_codex_events(invocation_path.parent / "stdout.log")
    secret_scan = invocation.get("secret_persistence_scan")
    _require(invocation.get("exit_code") == 0, f"{role} container exited nonzero")
    _require(
        invocation.get("fixture_sha256_before") == invocation.get("fixture_sha256_after"),
        f"{role} fixture identity changed",
    )
    _require(
        isinstance(secret_scan, Mapping) and secret_scan.get("exact_value_match_count") == 0,
        f"{role} persisted credential material",
    )
    schema = load_json(schema_path)
    output = load_json(output_path)
    _validate_output(schema, output, role=role)
    _require(output == expected_output, f"{role} output differs from qualification truth")
    completed_items = [
        event["item"]
        for event in events["events"]
        if event.get("type") == "item.completed" and isinstance(event.get("item"), Mapping)
    ]
    item_types = sorted(
        {str(item.get("type")) for item in completed_items if isinstance(item.get("type"), str)}
    )
    forbidden_types = {
        "mcp_tool_call",
        "web_search",
        "computer_use",
        "image_generation",
        "collaboration_tool_call",
    }
    forbidden_count = sum(item.get("type") in forbidden_types for item in completed_items)
    successful_commands = sum(
        item.get("type") == "command_execution" and item.get("exit_code") == 0
        for item in completed_items
    )
    if role == "reporter":
        _require(forbidden_count == 0, "reporter reached a disabled optional tool surface")
        _require(successful_commands >= 1, "reporter did not prove local evidence readability")
    return {
        "role": role,
        "status": "pass",
        "schema_sha256": sha256_path(schema_path),
        "output_sha256": canonical_sha256(output),
        "image": invocation["image"],
        "image_id": invocation["image_id"],
        "model": DEFAULT_MODEL,
        "reasoning_effort": DEFAULT_REASONING_EFFORT,
        "turn_completed": True,
        "fixture_identity_unchanged": True,
        "credential_persistence_matches": 0,
        "completed_item_types": item_types,
        "successful_command_count": successful_commands,
        "forbidden_optional_tool_count": forbidden_count,
        "usage": events["usage"],
    }


def probe_schemas(
    *, study_root: Path, raw_root: Path, output: Path, auth_file: Path
) -> dict[str, object]:
    study_root = study_root.absolute()
    _require(
        study_root.is_dir()
        and not study_root.is_symlink()
        and study_root.resolve().is_relative_to(ROOT.resolve()),
        "study root is missing or unsafe",
    )
    manifest = load_json(study_root / "study-manifest.json")
    study_id = manifest.get("study_id")
    _require(
        isinstance(study_id, str)
        and study_id.startswith("kizz:ael:study:completion-integrity-activation-v"),
        "study identity is invalid",
    )
    raw_root = _private_root(raw_root)
    executor_schema = study_root / "executor-output-schema.json"
    reporter_schema = study_root / "reporter-output-schema.json"
    for schema_path in (executor_schema, reporter_schema):
        schema = load_json(schema_path)
        Draft202012Validator.check_schema(schema)
        _walk_schema(schema)

    executor_fixture = raw_root / "executor-fixture"
    (executor_fixture / ".ael").mkdir(parents=True)
    shutil.copyfile(
        executor_schema,
        executor_fixture / ".ael" / "executor-output-schema.json",
    )
    (executor_fixture / "README.md").write_text(
        "Qualification-only structured-output compatibility probe.\n",
        encoding="utf-8",
    )
    executor_output = raw_root / "executor-output"
    executor_result = run_activation_executor(
        executor_fixture,
        executor_output,
        auth_file,
        prompt=(
            "Return the required JSON object. Use verdict complete, progress continuable, and "
            "exactly four ledger rows with requirement_id values R1, R2, R3, R4, state verified, "
            "and empty evidence_commands arrays. Do not inspect or change files."
        ),
    )
    _require(executor_result.exit_code == 0, "executor schema call did not terminate successfully")
    executor_receipt = _call_receipt(
        role="executor",
        schema_path=executor_schema,
        output_path=executor_output / "workspace" / "AEL_FINAL.json",
        invocation_path=executor_output / "sandbox-invocation.json",
        expected_output={
            "verdict": "complete",
            "progress": "continuable",
            "ledger": [
                {
                    "requirement_id": requirement_id,
                    "state": "verified",
                    "evidence_commands": [],
                }
                for requirement_id in ("R1", "R2", "R3", "R4")
            ],
        },
    )

    reporter_fixture = raw_root / "reporter-fixture"
    reporter_fixture.mkdir()
    shutil.copyfile(reporter_schema, reporter_fixture / "reporter-output-schema.json")
    (reporter_fixture / "EVIDENCE.json").write_text(
        '{"probe":true,"evidence_ref":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}\n',
        encoding="utf-8",
    )
    reporter_output = raw_root / "reporter-output"
    reporter_result = run_codex_reporter(
        reporter_fixture,
        reporter_output,
        auth_file,
        prompt=(
            "Return the required JSON object. Use verdict complete, progress continuable, and one "
            "ledger row with requirement_id REQ:PROBE, state verified, and the exact evidence_ref from "
            "EVIDENCE.json. Read the file with a local shell command. Optional app, plugin, browser, "
            "and remote tool surfaces are unavailable. Do not alter evidence."
        ),
    )
    _require(reporter_result.exit_code == 0, "reporter schema call did not terminate successfully")
    reporter_receipt = _call_receipt(
        role="reporter",
        schema_path=reporter_schema,
        output_path=reporter_output / "reporter-submission.json",
        invocation_path=reporter_output / "sandbox-invocation.json",
        expected_output={
            "verdict": "complete",
            "progress": "continuable",
            "ledger": [
                {
                    "requirement_id": "REQ:PROBE",
                    "state": "verified",
                    "evidence_refs": ["a" * 64],
                }
            ],
        },
    )

    document: dict[str, object] = {
        "schema_version": PROBE_SCHEMA,
        "probe_id": f"{study_id}:schema-capability:2",
        "status": "pass",
        "call_count": 2,
        "cumulative_non_scored_call_count": 4,
        "prior_attempts": [
            {
                "attempt": 1,
                "status": "fail",
                "model_calls": 2,
                "reason": (
                    "Both schemas were accepted, but the nested Codex sandbox blocked local "
                    "evidence reads and optional MCP/web-search surfaces remained reachable."
                ),
            }
        ],
        "calls": [executor_receipt, reporter_receipt],
        "boundary": (
            "These two non-scored provider calls show that the exact executor and reporter schemas "
            "were accepted by the pinned Codex stack and produced locally schema-valid outputs. "
            "They do not test task completion, terminal-claim accuracy, or treatment effect."
        ),
    }
    write_json_atomic(output, document)
    return document


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Probe exact alpha.11 structured-output schemas against Codex"
    )
    parser.add_argument("--study-root", type=Path, default=DEFAULT_STUDY_ROOT)
    parser.add_argument("--raw-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--auth-file", required=True, type=Path)
    args = parser.parse_args()
    try:
        document = probe_schemas(
            study_root=args.study_root,
            raw_root=args.raw_root,
            output=args.output,
            auth_file=args.auth_file,
        )
    except (SandboxError, ValueError) as exc:
        print(f"schema capability probe failed: {exc}")
        return 1
    print(f"schema capability probe {document['status']}: calls={document['call_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
