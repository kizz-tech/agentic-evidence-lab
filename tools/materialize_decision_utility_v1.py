from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from ael.decision_utility import (
    build_schedule,
    build_views,
    canonical_sha256,
    validate_case_pack,
    validate_protocol,
)
from ael.prospective_study import load_json_object
from ael.sandbox import SandboxError

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "studies/decision-utility-v1"
PROTOCOL = STUDY / "calibration/protocol.json"
CASES = STUDY / "calibration/cases.json"
PARTICIPANTS = STUDY / "calibration/participants.json"
READINESS = STUDY / "readiness.json"
OUTPUT = STUDY / "calibration/output.json"
REPORT = STUDY / "calibration/report.md"


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    ).encode("utf-8")


def _write(path: Path, payload: bytes, *, check: bool) -> None:
    if check:
        try:
            current = path.read_bytes()
        except OSError as exc:
            raise SandboxError(f"checked output is unavailable: {path}: {exc}") from exc
        if current != payload:
            raise SandboxError(f"checked output is stale: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _readiness(value: dict[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version",
        "study_id",
        "revision",
        "state",
        "human_pilot_admitted",
        "human_responses",
        "model_proxy_is_human_evidence",
        "blockers",
        "next_gate",
    }
    if set(value) != required:
        raise SandboxError("decision-utility readiness has missing or unknown keys")
    if value["schema_version"] != "ael.decision-utility-readiness/0.1-development":
        raise SandboxError("decision-utility readiness schema version is unsupported")
    if value["state"] != "instrument_qualification_only":
        raise SandboxError("decision-utility readiness must remain instrument_qualification_only")
    if value["human_pilot_admitted"] is not False or value["human_responses"] != 0:
        raise SandboxError("decision-utility calibration cannot claim a human pilot or responses")
    if value["model_proxy_is_human_evidence"] is not False:
        raise SandboxError("model proxy must not be represented as human evidence")
    blockers = value["blockers"]
    if (
        not isinstance(blockers, list)
        or len(blockers) < 4
        or not all(isinstance(item, str) and item.strip() for item in blockers)
    ):
        raise SandboxError("decision-utility readiness must retain all material blockers")
    if not isinstance(value["next_gate"], str) or not value["next_gate"].strip():
        raise SandboxError("decision-utility readiness next_gate is missing")
    return value


def _report(output: dict[str, Any]) -> str:
    schedule = output["schedule"]
    readiness = output["readiness"]
    lines = [
        "# Decision Utility v1 calibration",
        "",
        f"- State: `{readiness['state']}`",
        f"- Human pilot admitted: `{str(readiness['human_pilot_admitted']).lower()}`",
        f"- Human responses: `{readiness['human_responses']}`",
        f"- Calibration cases: `{output['case_count']}`",
        f"- Evidence-equivalent views: `{output['view_count']}`",
        f"- Synthetic schedule participants: `{schedule['participant_count']}`",
        f"- Synthetic schedule cells: `{len(schedule['cells'])}`",
        "",
        "## Blocking evidence",
        "",
    ]
    lines.extend(f"- {item}" for item in readiness["blockers"])
    lines.extend(
        [
            "",
            "## Claim ceiling",
            "",
            "This package proves deterministic instrument structure only. It contains no human outcome and cannot establish comprehension, decision utility, adoption, or downstream effect. Model readers are not human evidence.",
            "",
        ]
    )
    return "\n".join(lines)


def materialize(*, check: bool) -> dict[str, Any]:
    protocol = validate_protocol(load_json_object(PROTOCOL))
    cases = validate_case_pack(protocol, load_json_object(CASES))
    participants = load_json_object(PARTICIPANTS)
    if set(participants) != {"participant_ids"} or not isinstance(
        participants["participant_ids"], list
    ):
        raise SandboxError("decision-utility participants must contain one participant_ids array")
    readiness = _readiness(load_json_object(READINESS))
    views = build_views(protocol, cases)
    schedule = build_schedule(protocol, cases, participants["participant_ids"])
    output = {
        "schema_version": "ael.decision-utility-calibration/0.1-development",
        "protocol_id": protocol["protocol_id"],
        "protocol_revision": protocol["revision"],
        "protocol_sha256": canonical_sha256(protocol),
        "case_pack_id": cases["pack_id"],
        "case_pack_revision": cases["revision"],
        "case_pack_sha256": canonical_sha256(cases),
        "case_count": len(cases["cases"]),
        "view_count": len(views),
        "views": views,
        "schedule": schedule,
        "readiness": readiness,
    }
    _write(OUTPUT, _json_bytes(output), check=check)
    _write(REPORT, _report(output).encode("utf-8"), check=check)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Materialize or check the Decision Utility v1 synthetic calibration."
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        output = materialize(check=args.check)
    except (SandboxError, ValueError) as exc:
        parser.error(str(exc))
    verb = "checked" if args.check else "materialized"
    print(
        f"decision-utility calibration {verb}: cases={output['case_count']} "
        f"views={output['view_count']} cells={len(output['schedule']['cells'])} "
        "human_responses=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
