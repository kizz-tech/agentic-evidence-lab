from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ael.prospective_study import load_json_object, sha256_path
from ael.sandbox import SandboxError
from ael.validation import validate

ROOT = Path(__file__).resolve().parents[1]
SEASON_ROOT = ROOT / "studies" / "agent-skills-season-1"
CONCEPT_PATH = SEASON_ROOT / "concept.json"
MANIFEST_PATH = SEASON_ROOT / "manifests" / "systematic-debugging-real-shadow.study-manifest.json"
REPAIR_SCHEMA_VERSION = "ael.projection-deviation/0.1-pilot"
EXPECTED_INVALID_VALUE = "partially_rerunnable"
REPAIRED_VALUE = "rerunnable"
EXPECTED_FAILURE = (
    "materialized Contract v0 bundle is invalid: evidence-receipt.json at "
    "reproducibility: 'partially_rerunnable' is not one of the Contract v0 enum values"
)


def write_json(path: Path, document: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(document, indent=2, sort_keys=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _require_hash(document: Mapping[str, Any], path: list[str], expected: str) -> None:
    value: Any = document
    for key in path:
        if not isinstance(value, Mapping) or key not in value:
            raise SandboxError(f"projection repair is missing {'.'.join(path)}")
        value = value[key]
    if value != expected:
        raise SandboxError(
            f"projection repair expected {'.'.join(path)}={expected}, observed {value}"
        )


def repair_projection(result_root: Path, freeze_path: Path, repaired_at: str) -> dict[str, Any]:
    result_root = result_root.absolute()
    freeze_path = freeze_path.resolve()
    if result_root.is_symlink() or not result_root.is_dir():
        raise SandboxError("result root is missing or unsafe")

    receipt_path = result_root / "evidence-receipt.json"
    adoption_path = result_root / "adoption-decision.pilot.json"
    routing_path = result_root / "routing-policy.pilot.json"
    action_path = result_root / "action-record.pilot.json"
    follow_up_path = result_root / "outcome-follow-up.pilot.json"
    freeze_ref_path = result_root / "freeze-ref.json"
    effect_path = result_root / "effect-decision.json"
    deviation_path = result_root / "projection-deviation.pilot.json"
    if deviation_path.exists():
        raise SandboxError("projection repair is single-use; deviation record already exists")

    receipt = load_json_object(receipt_path)
    adoption = load_json_object(adoption_path)
    routing = load_json_object(routing_path)
    action = load_json_object(action_path)
    follow_up = load_json_object(follow_up_path)
    freeze_ref = load_json_object(freeze_ref_path)
    freeze = load_json_object(freeze_path)

    if receipt.get("reproducibility") != EXPECTED_INVALID_VALUE:
        raise SandboxError("projection repair only accepts the known invalid reproducibility value")
    if receipt.get("decision", {}).get("disposition") != "reject":
        raise SandboxError("projection repair refuses to alter a non-reject receipt")
    effect_sha = sha256_path(effect_path)
    _require_hash(freeze_ref, ["effect_decision_sha256"], effect_sha)
    _require_hash(adoption, ["effect_decision_ref", "sha256"], effect_sha)

    original_receipt_sha = sha256_path(receipt_path)
    receipt["reproducibility"] = REPAIRED_VALUE
    receipt.setdefault("limitations", []).append(
        "The frozen materializer emitted a non-Contract reproducibility enum after scored work; "
        "a transparent post-run projection repair mapped only that value to `rerunnable`, "
        "recomputed dependent hashes, and did not change observations or the effect decision."
    )
    write_json(receipt_path, receipt)

    adoption["evidence_receipt_ref"]["sha256"] = sha256_path(receipt_path)
    write_json(adoption_path, adoption)
    adoption_sha = sha256_path(adoption_path)

    routing["adoption_decision_ref"]["sha256"] = adoption_sha
    write_json(routing_path, routing)
    action["adoption_decision_ref"]["sha256"] = adoption_sha
    action["owner_system_ref"]["sha256"] = sha256_path(routing_path)
    write_json(action_path, action)
    action_sha = sha256_path(action_path)

    follow_up["action_ref"]["sha256"] = action_sha
    write_json(follow_up_path, follow_up)

    deviation = {
        "schema_version": REPAIR_SCHEMA_VERSION,
        "deviation_id": "kizz:ael:projection-deviation:systematic-debugging-real-shadow-v1:1",
        "detected_stage": "post-run Contract v0 validation",
        "detected_failure": EXPECTED_FAILURE,
        "repaired_at": repaired_at,
        "preregistration_sha": freeze_ref["preregistration_sha"],
        "frozen_materializer_sha256": freeze["code_hashes"]["materializer"],
        "repair_tool_sha256": sha256_path(Path(__file__).resolve()),
        "original_receipt_sha256": original_receipt_sha,
        "repaired_receipt_sha256": sha256_path(receipt_path),
        "effect_decision_sha256": effect_sha,
        "allowed_change": {
            "path": "evidence-receipt.json.reproducibility",
            "before": EXPECTED_INVALID_VALUE,
            "after": REPAIRED_VALUE,
        },
        "dependent_hashes_recomputed": [
            "adoption-decision.pilot.json",
            "routing-policy.pilot.json",
            "action-record.pilot.json",
            "outcome-follow-up.pilot.json",
            "freeze-ref.json",
        ],
        "decision_impact": "none; observations and effect-decision.json remained byte-identical",
        "claim_boundary": (
            "This repairs a public projection contract violation. It is not a preregistered "
            "analysis change and does not strengthen the empirical claim."
        ),
    }
    write_json(deviation_path, deviation)

    freeze_ref["receipt_sha256"] = sha256_path(receipt_path)
    freeze_ref["adoption_decision_sha256"] = adoption_sha
    freeze_ref["action_record_sha256"] = action_sha
    freeze_ref["projection_deviation_sha256"] = sha256_path(deviation_path)
    write_json(freeze_ref_path, freeze_ref)

    contract_paths = [
        CONCEPT_PATH,
        MANIFEST_PATH,
        *sorted((result_root / "runs").glob("*.json")),
        result_root / "measurement-set.json",
        receipt_path,
    ]
    documents, issues = validate(contract_paths)
    if issues:
        raise SandboxError(f"repaired Contract v0 bundle is invalid: {issues[0]}")
    return {
        "status": "repaired",
        "contract_documents": len(documents),
        "receipt_sha256": sha256_path(receipt_path),
        "effect_decision_sha256": effect_sha,
        "deviation_sha256": sha256_path(deviation_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Repair the one admitted post-run projection defect without changing evidence."
    )
    parser.add_argument("--result", required=True, type=Path)
    parser.add_argument("--freeze", required=True, type=Path)
    parser.add_argument("--repaired-at", required=True)
    args = parser.parse_args()
    print(json.dumps(repair_projection(args.result, args.freeze, args.repaired_at), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
