from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import run_systematic_debugging_shadow as runner

import ael.systematic_debugging_shadow as debugging_shadow
from ael.prospective_study import (
    FREEZE_SCHEMA_VERSION,
    deterministic_schedule,
    load_json_object,
    sha256_path,
    validate_admission,
    validate_freeze,
)
from ael.sandbox import SandboxError, inspect_image, tree_sha256

ROOT = Path(__file__).resolve().parents[1]
RUNNER_IMAGE = "kizz/ael-codex-runner:0.146.0"
PROXY_IMAGE = "kizz/ael-egress-proxy:0.1.0-alpha.1"
EVALUATOR_IMAGE = "kizz/ael-runner:0.1.0-alpha.1"
TASK_IDS = ["D-S01", "D-S02", "D-S03", "D-S04"]
STRATA = {
    "D-S01": "cross-boundary-contract",
    "D-S02": "cross-boundary-contract",
    "D-S03": "state-order-lifecycle",
    "D-S04": "state-order-lifecycle",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--admission", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--source-lock", required=True, type=Path)
    parser.add_argument("--pack-root", required=True, type=Path)
    parser.add_argument("--skill-root", required=True, type=Path)
    parser.add_argument("--frozen-at", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    output = args.output.absolute()
    if output.exists():
        raise SandboxError(f"freeze output already exists: {output}")
    admission_path = args.admission.resolve()
    manifest_path = args.manifest.resolve()
    source_lock_path = args.source_lock.resolve()
    pack_root = args.pack_root.resolve()
    skill_root = args.skill_root.resolve()
    admission = load_json_object(admission_path)
    issues = validate_admission(admission)
    if issues:
        raise SandboxError(f"admission has {len(issues)} issue(s): {issues[0]}")
    pack = runner.read_pack(pack_root)
    tasks = runner.task_map(pack_root, pack)
    if set(tasks) != set(TASK_IDS):
        raise SandboxError("private pack does not contain the exact admitted task IDs")
    if {key: value["stratum"] for key, value in tasks.items()} != STRATA:
        raise SandboxError("private pack stratum mapping differs from the admitted design")
    freeze = {
        "schema_version": FREEZE_SCHEMA_VERSION,
        "freeze_id": "kizz:ael:freeze:systematic-debugging-real-shadow:1",
        "study_id": "kizz:ael:study:agent-skills-season-1:systematic-debugging-real-shadow",
        "study_revision": 1,
        "frozen_at": args.frozen_at,
        "scored_calls_executed": 0,
        "study_manifest_ref": {
            "study_id": admission["study_manifest_ref"]["study_id"],
            "uri": "../manifests/systematic-debugging-real-shadow.study-manifest.json",
            "sha256": sha256_path(manifest_path),
        },
        "admission_ref": {
            "admission_id": admission["admission_id"],
            "uri": "systematic-debugging-real-shadow.admission.pilot.json",
            "sha256": sha256_path(admission_path),
        },
        "source_lock_ref": {
            "source_id": admission["candidate"]["source_id"],
            "uri": "../sources.lock.toml",
            "sha256": sha256_path(source_lock_path),
        },
        "candidate": {
            "source_id": admission["candidate"]["source_id"],
            "revision": admission["candidate"]["revision"],
            "path": admission["candidate"]["path"],
            "tree_sha256": tree_sha256(skill_root),
        },
        "conditions": [
            {"condition_id": "B0", "role": "baseline", "intervention_sha256": None},
            {
                "condition_id": "S1",
                "role": "treatment",
                "intervention_sha256": tree_sha256(skill_root),
            },
        ],
        "private_pack": {
            "uri": "urn:kizz:ael:private-pack:systematic-debugging-real-shadow:v1:screening",
            "sha256": tree_sha256(pack_root),
            "task_ids": TASK_IDS,
            "strata": STRATA,
        },
        "code_hashes": {
            "runner": sha256_path(ROOT / "tools" / "run_systematic_debugging_shadow.py"),
            "decision": sha256_path(Path(debugging_shadow.__file__).resolve()),
            "materializer": sha256_path(
                ROOT / "tools" / "materialize_systematic_debugging_shadow.py"
            ),
            "execution": debugging_shadow.execution_code_sha256(),
        },
        "prompt_sha256": hashlib.sha256(runner.STUDY_PROMPT.encode("utf-8")).hexdigest(),
        "runtime": {
            "harness": "codex-cli",
            "harness_version": "0.146.0",
            "model": "gpt-5.6-sol",
            "reasoning_effort": "xhigh",
            "runner_image": RUNNER_IMAGE,
            "runner_image_id": inspect_image(RUNNER_IMAGE),
            "proxy_image": PROXY_IMAGE,
            "proxy_image_id": inspect_image(PROXY_IMAGE),
            "evaluator_image": EVALUATOR_IMAGE,
            "evaluator_image_id": inspect_image(EVALUATOR_IMAGE),
            "network_policy": "openai-proxy",
        },
        "budget": {
            "max_scored_calls": 8,
            "per_run_timeout_seconds": 900,
            "max_generated_tokens": 30000,
        },
        "schedule": deterministic_schedule(
            TASK_IDS, ["B0", "S1"], "systematic-debugging-real-shadow-v1-2026-08-13"
        ),
        "decision_rule": {
            "route_requires_favorable_tasks_per_stratum": 2,
            "maximum_unfavorable_for_route": 0,
            "reject_at_unfavorable_pairs": 2,
            "require_zero_treatment_critical_failures": True,
            "require_all_treatment_activations": True,
            "invalid_outcome": "invalid_manual_review",
        },
        "roles": admission["roles"],
    }
    freeze_issues = validate_freeze(freeze)
    if freeze_issues:
        raise SandboxError(
            f"generated freeze has {len(freeze_issues)} issue(s): {freeze_issues[0]}"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(freeze, indent=2, sort_keys=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(f"freeze prepared: {output} sha256={sha256_path(output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
