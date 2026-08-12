#!/usr/bin/env python3
"""Import sanitized Council Generation 1 held-out evidence into AEL records."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

EXPECTED_PACKAGE_COMPOSITE = "dd1716d04484c62b0348f8b329d2967da840582462c662c53650d0c4e3656656"
EXPECTED_PROVENANCE_SHA256 = "3d0712562c3db115cfabe15e02c43940e9fd626b6ee862cf630fbc31141db6ed"
STUDY_ID = "kizz:ael:study:council-generation-1-heldout"
TASK_PACK_ID = "engineering-council-generation-1-heldout"

STRATA = {
    "E1": "routine-local",
    "E4": "consequential-domain-policy",
    "E7": "consequential-performance",
}


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def package_composite(source_root: Path) -> tuple[int, str]:
    rows: list[bytes] = []
    paths = sorted(
        (
            path
            for path in source_root.rglob("*")
            if path.is_file() and path.name != "package-freeze.md"
        ),
        key=lambda path: "./" + path.relative_to(source_root).as_posix(),
    )
    for path in paths:
        relative = "./" + path.relative_to(source_root).as_posix()
        rows.append(f"{sha256_path(path)}  {relative}\n".encode())
    return len(paths), hashlib.sha256(b"".join(rows)).hexdigest()


def source_ref(uri: str, sha256: str, visibility: str = "private") -> dict[str, Any]:
    return {
        "uri": uri,
        "sha256": sha256,
        "revision": "2026-08-11",
        "visibility": visibility,
    }


def build_run_record(cell_path: Path, cell: dict[str, Any], study_sha256: str) -> dict[str, Any]:
    cell_id = cell["cell_id"]
    case_id = cell["case_id"]
    runtime = cell["runtime"]
    usage = cell["usage"]
    issues = list(cell.get("integrity_issues", []))
    stderr_count = int(cell.get("stderr_error_count", 0))
    if stderr_count:
        issues.append(
            f"runner reported {stderr_count} stderr error(s); source cell remained capture-valid"
        )
    events = cell.get("agent_events", [])
    output_sha = cell["hashes"]["final_output_sha256"]
    return {
        "schema_version": "ael.run-record/0.1",
        "object_type": "run_record",
        "run_id": f"kizz:ael:run:council-generation-1:{cell_id}",
        "study_ref": {
            "study_id": STUDY_ID,
            "revision": 1,
            "uri": "../study-manifest.json",
            "sha256": study_sha256,
            "visibility": "public",
        },
        "condition_id": cell["condition"],
        "task": {
            "task_pack_id": TASK_PACK_ID,
            "task_id": case_id,
            "stratum": STRATA[case_id],
            "role": "holdout",
        },
        "repeat_index": 1,
        "status": cell["status"],
        "runtime": {
            "harness": {
                "name": "codex-cli",
                "version": runtime["cli"].removeprefix("codex-cli "),
            },
            "model": {
                "provider": "OpenAI",
                "model_id": runtime["model"],
                "effort": runtime["contestant_reasoning_effort"],
                "immutable_revision_exposed": False,
            },
            "sandbox": runtime["target_sandbox"],
            "environment": {
                "ephemeral": bool(runtime["ephemeral"]),
                "identity_available": False,
            },
        },
        "usage": {
            "input_tokens": usage["input_tokens"],
            "cached_input_tokens": usage["cached_input_tokens"],
            "output_tokens": usage["output_tokens"],
            "reasoning_output_tokens": usage["reasoning_output_tokens"],
            "wall_time_ms": cell["wall_time_ms"],
        },
        "outputs": [
            source_ref(
                f"lifeos:labs:experiment:engineering-council-evaluation:2026-08-11:heldout:{cell_id}:final-output",
                output_sha,
            )
        ],
        "effects": [],
        "event_summary": {
            "captured": True,
            "event_count": len(events),
            "authenticated_actor_ids": [],
            "limitations": [
                "The retained event stream did not expose authenticated subagent receiver IDs."
            ],
        },
        "integrity_issues": issues,
        "source_refs": [
            source_ref(
                f"lifeos:labs:experiment:engineering-council-evaluation:2026-08-11:heldout:{cell_id}:capture",
                sha256_path(cell_path),
            )
        ],
    }


def build_measurements(
    source_root: Path,
    run_records: dict[str, dict[str, Any]],
    study_sha256: str,
) -> dict[str, Any]:
    measurements: list[dict[str, Any]] = []
    score_by_condition: dict[str, list[float]] = {key: [] for key in ["C0", "C1", "C2", "C3"]}
    judgment_refs: list[dict[str, Any]] = []

    for case_id in STRATA:
        judgment_path = source_root / "results" / "heldout" / "judgments" / f"{case_id}.json"
        judgment = load_json(judgment_path)
        judgment_ref = source_ref(
            f"lifeos:labs:experiment:engineering-council-evaluation:2026-08-11:heldout:{case_id}:judgment",
            sha256_path(judgment_path),
        )
        judgment_refs.append(judgment_ref)
        for evaluation in judgment["judgment"]["evaluations"]:
            condition = judgment["opaque_mapping"][evaluation["label"]]
            run_id = f"kizz:ael:run:council-generation-1:{case_id}-{condition}"
            score = float(evaluation["weighted_score"])
            score_by_condition[condition].append(score)
            measurements.append(
                {
                    "measurement_id": f"score:{case_id}:{condition}",
                    "kind": "subjective",
                    "metric": "blinded_weighted_decision_score",
                    "value": score,
                    "unit": "score_0_to_4",
                    "direction": "higher_better",
                    "run_ids": [run_id],
                    "condition_id": condition,
                    "task_id": case_id,
                    "stratum": STRATA[case_id],
                    "evaluator": {
                        "evaluator_id": "isolated-codex-judge",
                        "kind": "model",
                        "blinded": True,
                    },
                    "evidence_refs": [judgment_ref],
                }
            )
            measurements.append(
                {
                    "measurement_id": f"critical-anchor-misses:{case_id}:{condition}",
                    "kind": "subjective",
                    "metric": "critical_anchor_misses",
                    "value": len(evaluation["critical_failures"]),
                    "unit": "count",
                    "direction": "lower_better",
                    "run_ids": [run_id],
                    "condition_id": condition,
                    "task_id": case_id,
                    "stratum": STRATA[case_id],
                    "evaluator": {
                        "evaluator_id": "isolated-codex-judge",
                        "kind": "model",
                        "blinded": True,
                    },
                    "evidence_refs": [judgment_ref],
                }
            )

    for run_id, record in sorted(run_records.items()):
        usage = record["usage"]
        measurements.append(
            {
                "measurement_id": "generated-work:" + run_id.rsplit(":", 1)[-1],
                "kind": "cost",
                "metric": "generated_work_tokens",
                "value": usage["output_tokens"] + usage["reasoning_output_tokens"],
                "unit": "tokens",
                "direction": "lower_better",
                "run_ids": [run_id],
                "condition_id": record["condition_id"],
                "task_id": record["task"]["task_id"],
                "stratum": record["task"]["stratum"],
                "evidence_refs": record["source_refs"],
            }
        )

    audit_path = source_root / "results" / "heldout" / "parent-audit.md"
    audit_ref = source_ref(
        "lifeos:labs:experiment:engineering-council-evaluation:2026-08-11:heldout:parent-audit",
        sha256_path(audit_path),
    )
    for condition, values in score_by_condition.items():
        measurements.append(
            {
                "measurement_id": f"heldout-mean-score:{condition}",
                "kind": "aggregate",
                "metric": "heldout_mean_blinded_weighted_decision_score",
                "value": round(sum(values) / len(values), 2),
                "unit": "score_0_to_4",
                "direction": "higher_better",
                "run_ids": [
                    f"kizz:ael:run:council-generation-1:{case_id}-{condition}" for case_id in STRATA
                ],
                "condition_id": condition,
                "evidence_refs": judgment_refs + [audit_ref],
            }
        )

    candidate_ids = [f"kizz:ael:run:council-generation-1:{case_id}-C3" for case_id in ["E4", "E7"]]
    baseline_ids = [f"kizz:ael:run:council-generation-1:{case_id}-C2" for case_id in ["E4", "E7"]]
    candidate_work = sum(
        run_records[run_id]["usage"]["output_tokens"]
        + run_records[run_id]["usage"]["reasoning_output_tokens"]
        for run_id in candidate_ids
    )
    baseline_work = sum(
        run_records[run_id]["usage"]["output_tokens"]
        + run_records[run_id]["usage"]["reasoning_output_tokens"]
        for run_id in baseline_ids
    )
    measurements.extend(
        [
            {
                "measurement_id": "consequential-generated-work:C3",
                "kind": "aggregate",
                "metric": "consequential_generated_work_tokens",
                "value": candidate_work,
                "unit": "tokens",
                "direction": "lower_better",
                "run_ids": candidate_ids,
                "condition_id": "C3",
                "stratum": "consequential",
                "evidence_refs": [audit_ref],
            },
            {
                "measurement_id": "consequential-generated-work:C2",
                "kind": "aggregate",
                "metric": "consequential_generated_work_tokens",
                "value": baseline_work,
                "unit": "tokens",
                "direction": "lower_better",
                "run_ids": baseline_ids,
                "condition_id": "C2",
                "stratum": "consequential",
                "evidence_refs": [audit_ref],
            },
            {
                "measurement_id": "consequential-generated-work-reduction:C3-vs-C2",
                "kind": "aggregate",
                "metric": "relative_generated_work_reduction",
                "value": round((baseline_work - candidate_work) / baseline_work, 4),
                "unit": "proportion",
                "direction": "higher_better",
                "run_ids": candidate_ids + baseline_ids,
                "stratum": "consequential",
                "evidence_refs": [audit_ref],
            },
            {
                "measurement_id": "routine-direct-routing:C3",
                "kind": "process",
                "metric": "correctly_declined_council",
                "value": True,
                "unit": "boolean",
                "direction": "target",
                "run_ids": ["kizz:ael:run:council-generation-1:E1-C3"],
                "condition_id": "C3",
                "task_id": "E1",
                "stratum": STRATA["E1"],
                "evidence_refs": [audit_ref],
            },
            {
                "measurement_id": "historical-profile-fork-error:E4-C2",
                "kind": "process",
                "metric": "named_profile_fork_error_observed",
                "value": True,
                "unit": "boolean",
                "direction": "lower_better",
                "run_ids": ["kizz:ael:run:council-generation-1:E4-C2"],
                "condition_id": "C2",
                "task_id": "E4",
                "stratum": STRATA["E4"],
                "evidence_refs": [audit_ref],
            },
            {
                "measurement_id": "candidate-profile-id-omission:E7-C3",
                "kind": "process",
                "metric": "required_profile_identity_omitted",
                "value": True,
                "unit": "boolean",
                "direction": "lower_better",
                "run_ids": ["kizz:ael:run:council-generation-1:E7-C3"],
                "condition_id": "C3",
                "task_id": "E7",
                "stratum": STRATA["E7"],
                "evidence_refs": [audit_ref],
            },
        ]
    )

    run_summary_path = source_root / "results" / "heldout" / "run-summary.json"
    result_path = source_root / "result.md"
    return {
        "schema_version": "ael.measurement-set/0.1",
        "object_type": "measurement_set",
        "measurement_set_id": "kizz:ael:measurements:council-generation-1-heldout",
        "study_ref": {
            "study_id": STUDY_ID,
            "revision": 1,
            "uri": "study-manifest.json",
            "sha256": study_sha256,
            "visibility": "public",
        },
        "measurements": measurements,
        "critical_failures": [],
        "limitations": [
            "One stochastic sample per case and condition does not estimate run variance.",
            "The blinded judge used a correlated variant of the same model family as contestants.",
            "The task pack used synthetic engineering briefs rather than observed production decisions.",
            "Total input compute was not equalized; generated-work tokens do not establish universal cost reduction.",
            "No downstream implementation, rework, production, or user outcome was measured.",
            "Subagent receiver identities were not authenticated by the retained CLI event stream.",
        ],
        "source_refs": [
            source_ref(
                "lifeos:labs:experiment:engineering-council-evaluation:2026-08-11:heldout:run-summary",
                sha256_path(run_summary_path),
            ),
            audit_ref,
            source_ref(
                "lifeos:labs:experiment:engineering-council-evaluation:2026-08-11:integrated-result",
                sha256_path(result_path),
            ),
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--council-provenance", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_root = args.source_root.resolve()
    output_root = args.output_root.resolve()
    provenance = args.council_provenance.resolve()
    if sha256_path(provenance) != EXPECTED_PROVENANCE_SHA256:
        raise SystemExit("Council provenance receipt does not match the pinned Generation 1 source")
    count, composite = package_composite(source_root)
    if count != 114 or composite != EXPECTED_PACKAGE_COMPOSITE:
        raise SystemExit(f"Council source package drift: files={count}, composite={composite}")
    study_path = output_root / "study-manifest.json"
    if not study_path.is_file():
        raise SystemExit(f"missing AEL study manifest: {study_path}")
    study_sha256 = sha256_path(study_path)

    run_records: dict[str, dict[str, Any]] = {}
    runs_root = output_root / "runs"
    for cell_path in sorted((source_root / "results" / "heldout" / "cells").glob("*.json")):
        cell = load_json(cell_path)
        if cell["case_id"] not in STRATA:
            continue
        record = build_run_record(cell_path, cell, study_sha256)
        run_records[record["run_id"]] = record
        write_json(runs_root / f"{cell['cell_id']}.json", record)
    if len(run_records) != 12:
        raise SystemExit(f"expected 12 held-out run records, generated {len(run_records)}")
    measurements = build_measurements(source_root, run_records, study_sha256)
    write_json(output_root / "measurement-set.json", measurements)
    print(f"imported {len(run_records)} sanitized run records; source composite {composite}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
