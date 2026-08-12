#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ael.sandbox import tree_sha256
from ael.validation import sha256_path

TASKS = {
    "local-unit": "local-unit-change",
    "cross-contract": "cross-module-contract-change",
    "migration": "migration-backed-change",
}
CONDITIONS = ("S0", "S1")
RUNNER_IMAGE_ID = "sha256:37252639215efd84e0b777118dee587de9912828923b80847bbc2654b4847a76"
PROXY_IMAGE_ID = "sha256:6a27ca246703c1318b6a9bb4de156c1167ba7a15b06a390a02a23efcc1bcf0df"
STUDY_ID = "kizz:ael:study:focused-change-verification-skill"
CONCEPT_ID = "kizz:ael:example:focused-change-verification-skill"


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, document: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def private_ref(uri: str, path: Path) -> dict[str, object]:
    return {
        "uri": uri,
        "sha256": sha256_path(path),
        "revision": "runtime-v2-calibration-1",
        "visibility": "private",
    }


def parse_usage(events_path: Path) -> tuple[dict[str, int], int, bool]:
    usage: dict[str, int] | None = None
    event_count = 0
    skill_activated = False
    for line in events_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event_count += 1
        event = json.loads(line)
        if event.get("type") == "turn.completed":
            usage = event.get("usage")
        if "home/.codex/skills/focused-change-verification/SKILL.md" in line:
            skill_activated = True
    if usage is None:
        raise RuntimeError(f"missing turn usage: {events_path}")
    return usage, event_count, skill_activated


def run_record(
    raw_root: Path,
    study_sha256: str,
    task_id: str,
    stratum: str,
    condition_id: str,
) -> tuple[dict[str, object], dict[str, object]]:
    run_name = f"{task_id}-{condition_id}-01"
    raw = raw_root / task_id / f"{condition_id}-01"
    evaluation_root = raw_root / task_id / f"{condition_id}-01-evaluation"
    invocation_path = raw / "sandbox-invocation.json"
    events_path = raw / "stdout.log"
    final_path = raw / "workspace" / "AEL_FINAL.md"
    evaluation_path = evaluation_root / "candidate-evaluation.json"
    invocation = read_json(invocation_path)
    evaluation = read_json(evaluation_path)
    usage, event_count, skill_activated = parse_usage(events_path)

    if invocation["image_id"] != RUNNER_IMAGE_ID or invocation["proxy_image_id"] != PROXY_IMAGE_ID:
        raise RuntimeError(f"unexpected runtime image in {run_name}")
    if invocation["fixture_sha256_before"] != invocation["fixture_sha256_after"]:
        raise RuntimeError(f"fixture identity changed in {run_name}")
    if invocation["exit_code"] != 0 or not evaluation["accepted"]:
        raise RuntimeError(f"run is not an accepted calibration cell: {run_name}")
    expected_intervention = condition_id == "S1"
    if invocation["intervention_injected"] is not expected_intervention:
        raise RuntimeError(f"intervention mismatch in {run_name}")
    if skill_activated is not expected_intervention:
        raise RuntimeError(f"skill activation mismatch in {run_name}")
    scan = invocation.get("secret_persistence_scan")
    scan_state = "automatic output scan passed"
    if scan is None:
        scan_state = "post-run exact-value scan required outside this record"
    elif scan["exact_value_match_count"] != 0:
        raise RuntimeError(f"credential persistence detected in {run_name}")

    run_id = f"kizz:ael:run:focused-change-verification-calibration:{run_name}"
    output_uri = f"urn:kizz:ael:private-run:{run_name}:final"
    candidate_uri = f"urn:kizz:ael:private-run:{run_name}:candidate"
    source_prefix = f"urn:kizz:ael:private-run:{run_name}"
    record: dict[str, object] = {
        "schema_version": "ael.run-record/0.1",
        "object_type": "run_record",
        "run_id": run_id,
        "study_ref": {
            "study_id": STUDY_ID,
            "revision": 1,
            "uri": "../../study-manifest.json",
            "sha256": study_sha256,
            "visibility": "public",
        },
        "condition_id": condition_id,
        "task": {
            "task_pack_id": "focused-change-verification-adaptation-v1",
            "task_id": task_id,
            "stratum": stratum,
            "role": "calibration",
        },
        "repeat_index": 1,
        "status": "valid",
        "runtime": {
            "harness": {"name": "codex-cli", "version": "0.146.0"},
            "model": {
                "provider": "OpenAI",
                "model_id": "gpt-5.6-sol",
                "effort": "xhigh",
                "immutable_revision_exposed": False,
            },
            "sandbox": "restricted outer Docker; Codex inner sandbox disabled",
            "environment": {
                "ephemeral": True,
                "identity_available": True,
                "digest": RUNNER_IMAGE_ID.removeprefix("sha256:"),
            },
            "context_sha256": invocation["fixture_sha256_before"],
        },
        "usage": {
            "input_tokens": usage["input_tokens"],
            "cached_input_tokens": usage["cached_input_tokens"],
            "output_tokens": usage["output_tokens"],
            "reasoning_output_tokens": usage["reasoning_output_tokens"],
            "wall_time_ms": invocation["duration_ms"],
        },
        "outputs": [
            {
                "uri": output_uri,
                "sha256": sha256_path(final_path),
                "revision": "runtime-v2-calibration-1",
                "visibility": "private",
            },
            {
                "uri": candidate_uri,
                "sha256": tree_sha256(raw / "workspace"),
                "revision": "runtime-v2-calibration-1",
                "visibility": "private",
            },
        ],
        "effects": [],
        "event_summary": {
            "captured": True,
            "event_count": event_count,
            "authenticated_actor_ids": [],
            "limitations": [
                "The provider did not expose an immutable model revision.",
                "Raw Codex events remain private and are represented here by content hashes.",
                scan_state + ".",
            ],
        },
        "integrity_issues": [
            "The reusable ChatGPT credential was readable by the Codex process and generated shell commands; only maintainer-controlled fixtures and intervention content were used."
        ],
        "source_refs": [
            private_ref(source_prefix + ":events", events_path),
            private_ref(source_prefix + ":invocation", invocation_path),
            private_ref(source_prefix + ":evaluation", evaluation_path),
        ],
    }
    summary = {
        "run_id": run_id,
        "condition_id": condition_id,
        "task_id": task_id,
        "stratum": stratum,
        "accepted": True,
        "visible_passed": evaluation["visible_exit_code"] == 0,
        "skill_activated": skill_activated,
        "usage": record["usage"],
        "evaluation_ref": private_ref(source_prefix + ":evaluation", evaluation_path),
        "events_ref": private_ref(source_prefix + ":events", events_path),
    }
    return record, summary


def measurement(
    measurement_id: str,
    kind: str,
    metric: str,
    value: int | float | bool,
    unit: str,
    direction: str,
    summary: dict[str, object],
    evidence_key: str,
) -> dict[str, object]:
    return {
        "measurement_id": measurement_id,
        "kind": kind,
        "metric": metric,
        "value": value,
        "unit": unit,
        "direction": direction,
        "run_ids": [summary["run_id"]],
        "condition_id": summary["condition_id"],
        "task_id": summary["task_id"],
        "stratum": summary["stratum"],
        "evaluator": {
            "evaluator_id": "ael-deterministic-evaluator",
            "kind": "deterministic",
            "blinded": True,
        },
        "evidence_refs": [summary[evidence_key]],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--generated-at", required=True)
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    raw_root = args.raw_root.resolve()
    output = args.output.resolve()
    study_path = repo_root / "examples" / "coding-skill" / "study-manifest.json"
    concept_path = repo_root / "examples" / "coding-skill" / "concept.json"
    study_sha256 = sha256_path(study_path)
    concept_sha256 = sha256_path(concept_path)
    output.mkdir(parents=True, exist_ok=True)
    runs_dir = output / "runs"
    runs_dir.mkdir(exist_ok=True)

    summaries: list[dict[str, object]] = []
    run_refs: list[dict[str, object]] = []
    for task_id, stratum in TASKS.items():
        for condition_id in CONDITIONS:
            record, summary = run_record(raw_root, study_sha256, task_id, stratum, condition_id)
            filename = f"{task_id}-{condition_id}-01.json"
            record_path = runs_dir / filename
            write_json(record_path, record)
            summaries.append(summary)
            run_refs.append(
                {
                    "run_id": record["run_id"],
                    "uri": f"runs/{filename}",
                    "sha256": sha256_path(record_path),
                    "visibility": "public",
                }
            )

    measurements: list[dict[str, object]] = []
    for summary in summaries:
        suffix = f"{summary['task_id']}:{summary['condition_id']}"
        measurements.extend(
            [
                measurement(
                    f"acceptance:{suffix}",
                    "deterministic",
                    "held_out_acceptance_passed",
                    summary["accepted"],
                    "boolean",
                    "higher_better",
                    summary,
                    "evaluation_ref",
                ),
                measurement(
                    f"visible-tests:{suffix}",
                    "deterministic",
                    "visible_tests_passed",
                    summary["visible_passed"],
                    "boolean",
                    "higher_better",
                    summary,
                    "evaluation_ref",
                ),
                measurement(
                    f"generated-work:{suffix}",
                    "cost",
                    "generated_work_tokens",
                    summary["usage"]["output_tokens"] + summary["usage"]["reasoning_output_tokens"],
                    "tokens",
                    "lower_better",
                    summary,
                    "events_ref",
                ),
                measurement(
                    f"wall-time:{suffix}",
                    "cost",
                    "wall_time",
                    summary["usage"]["wall_time_ms"],
                    "milliseconds",
                    "lower_better",
                    summary,
                    "events_ref",
                ),
            ]
        )
        if summary["condition_id"] == "S1":
            measurements.append(
                measurement(
                    f"skill-activation:{suffix}",
                    "process",
                    "skill_activated",
                    summary["skill_activated"],
                    "boolean",
                    "target",
                    summary,
                    "events_ref",
                )
            )

    totals: dict[str, dict[str, int]] = {}
    for condition_id in CONDITIONS:
        selected = [item for item in summaries if item["condition_id"] == condition_id]
        totals[condition_id] = {
            "accepted": sum(int(item["accepted"]) for item in selected),
            "generated_work_tokens": sum(
                item["usage"]["output_tokens"] + item["usage"]["reasoning_output_tokens"]
                for item in selected
            ),
            "wall_time_ms": sum(item["usage"]["wall_time_ms"] for item in selected),
        }
        measurements.extend(
            [
                {
                    "measurement_id": f"acceptance-total:{condition_id}",
                    "kind": "aggregate",
                    "metric": "accepted_tasks",
                    "value": totals[condition_id]["accepted"],
                    "unit": "tasks",
                    "direction": "higher_better",
                    "run_ids": [item["run_id"] for item in selected],
                    "condition_id": condition_id,
                    "evidence_refs": [item["evaluation_ref"] for item in selected],
                },
                {
                    "measurement_id": f"generated-work-total:{condition_id}",
                    "kind": "aggregate",
                    "metric": "generated_work_tokens",
                    "value": totals[condition_id]["generated_work_tokens"],
                    "unit": "tokens",
                    "direction": "lower_better",
                    "run_ids": [item["run_id"] for item in selected],
                    "condition_id": condition_id,
                    "evidence_refs": [item["events_ref"] for item in selected],
                },
                {
                    "measurement_id": f"wall-time-total:{condition_id}",
                    "kind": "aggregate",
                    "metric": "wall_time",
                    "value": totals[condition_id]["wall_time_ms"],
                    "unit": "milliseconds",
                    "direction": "lower_better",
                    "run_ids": [item["run_id"] for item in selected],
                    "condition_id": condition_id,
                    "evidence_refs": [item["events_ref"] for item in selected],
                },
            ]
        )

    measurement_set: dict[str, object] = {
        "schema_version": "ael.measurement-set/0.1",
        "object_type": "measurement_set",
        "measurement_set_id": "kizz:ael:measurements:focused-change-verification-calibration-v1",
        "study_ref": {
            "study_id": STUDY_ID,
            "revision": 1,
            "uri": "../study-manifest.json",
            "sha256": study_sha256,
            "visibility": "public",
        },
        "measurements": measurements,
        "critical_failures": [
            {
                "failure_id": "canonical-fixture-mutation",
                "severity": "critical",
                "observed": False,
                "description": "No canonical fixture hash changed during any of the six stable calibration cells.",
                "run_ids": [item["run_id"] for item in summaries],
                "evidence_refs": [item["events_ref"] for item in summaries],
            },
            {
                "failure_id": "deterministic-acceptance-regression",
                "severity": "high",
                "observed": False,
                "description": "All three baseline and all three treatment candidates passed their separate acceptance evaluator.",
                "run_ids": [item["run_id"] for item in summaries],
                "evidence_refs": [item["evaluation_ref"] for item in summaries],
            },
        ],
        "limitations": [
            "One non-randomized calibration repeat was run per task and condition; this is not an effect estimate.",
            "The public task prompts explicitly request much of the verification behavior contributed by the skill, creating a ceiling and treatment-contamination risk.",
            "Kizz owns the skill, tasks, runner, deterministic evaluator, and decision.",
            "The provider exposes a model identifier but not an immutable model revision.",
            "Generated-work and wall-time budgets were matched by configuration but not forced to equal realized usage.",
            "The reusable ChatGPT credential was process-readable; persisted outputs were scanned, but encrypted provider traffic was not inspected.",
            "No downstream rework, production behavior, user outcome, or third-party replication was measured.",
        ],
        "source_refs": [
            {
                "uri": "urn:kizz:ael:private-run-set:focused-change-verification-calibration-v1",
                "sha256": tree_sha256(raw_root),
                "revision": "runtime-v2-calibration-1",
                "visibility": "private",
            }
        ],
    }
    measurement_path = output / "measurement-set.json"
    write_json(measurement_path, measurement_set)

    receipt: dict[str, object] = {
        "schema_version": "ael.evidence-receipt/0.1",
        "object_type": "evidence_receipt",
        "receipt_id": "kizz:ael:receipt:focused-change-verification-calibration-v1",
        "generated_at": args.generated_at,
        "concept_ref": {
            "concept_id": CONCEPT_ID,
            "revision": 1,
            "uri": "../concept.json",
            "sha256": concept_sha256,
            "visibility": "public",
        },
        "study_ref": {
            "study_id": STUDY_ID,
            "revision": 1,
            "uri": "../study-manifest.json",
            "sha256": study_sha256,
            "visibility": "public",
        },
        "run_record_refs": run_refs,
        "measurement_set_ref": {
            "measurement_set_id": measurement_set["measurement_set_id"],
            "uri": "measurement-set.json",
            "sha256": sha256_path(measurement_path),
            "visibility": "public",
        },
        "evidence_level": "runtime_conformant",
        "reproducibility": "rerunnable",
        "independence": {
            "label": "maintainer_evaluated",
            "role_overlaps": [
                "Kizz owns the intervention, task pack, runner, evaluator, analysis, and continuation decision."
            ],
            "disclosure": "This is maintainer calibration evidence, not independent certification or a confirmatory skill-effect study.",
        },
        "decision": {
            "disposition": "narrow",
            "summary": "Keep the Codex runner and current pack as an operational smoke surface, but do not spend the planned 18-cell budget on this ceiling-limited pack; design tasks that do not restate the skill before estimating an effect.",
            "scope": [
                "Codex CLI 0.146.0 with gpt-5.6-sol at xhigh effort",
                "the exact pinned runtime and proxy image IDs in the six run records",
                "three public maintainer-authored calibration tasks",
                "one non-randomized repeat per condition and task",
            ],
            "reversal_trigger": "Reconsider after a frozen discriminating pack, preregistered behavioral rubric, randomized order, repeated cells, and a safer credential boundary are available.",
        },
        "evaluated_claims": [
            {
                "claim_id": "AEL-FCV-CAL-01",
                "statement": "The controlled-egress Docker adapter executed six stable Codex cells without changing any canonical fixture and captured enough telemetry for deterministic post-run evaluation.",
                "status": "supported",
                "claim_level": "workflow",
                "scope": ["six runtime-v2 calibration cells", "maintainer-controlled fixtures"],
                "evidence_refs": [
                    "canonical-fixture-mutation",
                    "acceptance-total:S0",
                    "acceptance-total:S1",
                ],
                "falsifier": "A byte-equivalent rerun mutates a fixture, cannot export a candidate, or cannot bind telemetry to the evaluated workspace.",
            },
            {
                "claim_id": "AEL-FCV-CAL-02",
                "statement": "The frozen skill was installed and explicitly read in all three treatment cells and in no baseline cell.",
                "status": "supported",
                "claim_level": "artifact",
                "scope": ["S1 treatment cells", "retained private Codex event streams"],
                "evidence_refs": [
                    "skill-activation:local-unit:S1",
                    "skill-activation:cross-contract:S1",
                    "skill-activation:migration:S1",
                ],
                "falsifier": "A retained treatment trace lacks the exact skill read or a baseline trace loads it.",
            },
            {
                "claim_id": "AEL-FCV-CAL-03",
                "statement": "No deterministic implementation-acceptance difference was observed: baseline and treatment each passed three of three tasks.",
                "status": "bounded",
                "claim_level": "workflow",
                "scope": [
                    "one calibration repeat",
                    "three public tasks",
                    "deterministic acceptance only",
                ],
                "evidence_refs": ["acceptance-total:S0", "acceptance-total:S1"],
                "falsifier": "Repeated matched runs on a discriminating pack produce a stable acceptance or critical-omission difference.",
            },
            {
                "claim_id": "AEL-FCV-CAL-04",
                "statement": "The current public prompts are too explicit to isolate the skill's verification-routing contribution and should remain smoke tests rather than become the first confirmatory pack.",
                "status": "bounded",
                "claim_level": "workflow",
                "scope": ["current task wording", "observed 6-of-6 acceptance ceiling"],
                "evidence_refs": ["acceptance-total:S0", "acceptance-total:S1"],
                "falsifier": "A preregistered repeated study on the unchanged pack exhibits reliable non-ceiling discrimination on the primary behavioral estimand.",
            },
            {
                "claim_id": "AEL-FCV-CAL-05",
                "statement": "Treatment finals more consistently separated local validation from commit, push, deployment, and outcome state, but this observation was not scored by a preregistered rubric.",
                "status": "unresolved",
                "claim_level": "workflow",
                "scope": ["six final responses", "post-hoc qualitative observation"],
                "evidence_refs": ["generated-work-total:S0", "generated-work-total:S1"],
                "falsifier": "A blinded preregistered state-reporting rubric finds no stable paired difference or favors baseline.",
            },
        ],
        "unsupported_inferences": [
            "The skill improves implementation correctness or code quality.",
            "The skill is cost-effective or faster.",
            "The skill transfers to real repositories or other models and agent runtimes.",
            "Codex or gpt-5.6-sol is superior to Claude Code, Cursor, another CLI, or another model.",
            "The current credential boundary is safe for untrusted third-party tasks or skills.",
            "Three acceptance passes per condition establish equivalence.",
        ],
        "limitations": measurement_set["limitations"],
        "invalidation_triggers": [
            "A change to the frozen skill, task pack, prompt, Codex version, model/effort, runner image, proxy policy, or evaluator",
            "New evidence that credential content entered persisted artifacts or unauthorized traffic",
            "A repeated or real-shadow study contradicting the calibration observations",
            "A public claim that omits the maintainer-evaluated and calibration-only scope",
        ],
        "state": {
            "experiment": "six-cell runner calibration completed; planned 18-cell adaptation study not run",
            "artifact": "frozen skill and public task pack locally validated",
            "repository": "included in the v0.1.0-alpha.1 release candidate",
            "publication": "prepared for public alpha release",
            "deployment": "not deployed",
            "outcome": "not observed",
        },
        "publication_state": "public_ready",
        "generator": {"name": "agentic-evidence-lab", "version": "0.1.0a1"},
    }
    receipt_path = output / "evidence-receipt.json"
    write_json(receipt_path, receipt)
    print(
        json.dumps(
            {
                "runs": len(summaries),
                "totals": totals,
                "measurement_set_sha256": sha256_path(measurement_path),
                "receipt_sha256": sha256_path(receipt_path),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
