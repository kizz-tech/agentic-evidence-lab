from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from ael.sandbox import tree_sha256
from ael.validation import sha256_path

ROOT = Path(__file__).resolve().parents[1]
SEASON_ROOT = ROOT / "studies" / "agent-skills-season-1"
RUNNER_IMAGE_ID = "sha256:f5ebad21373b16799a4bb0189d917856280cca8394c25967c95d612b6b61ac08"
PROXY_IMAGE_ID = "sha256:69a5e44397a2e752507076cf12b30b7609c47711bd6d3f342c612dba7d968e35"
CONCEPT_ID = "kizz:ael:concept:public-agent-skill-effectiveness"
CALIBRATION_REVISION = "runtime-v1-calibration-1"


@dataclass(frozen=True)
class Cell:
    condition_id: str
    skill_name: str | None = None


@dataclass(frozen=True)
class Study:
    study_id: str
    cells: tuple[Cell, ...]
    raw_directory: str | None = None


STUDIES = (
    Study(
        "truthful-completion",
        (Cell("B0"), Cell("S1", "verification-before-completion")),
        "truthful-completion-r2",
    ),
    Study(
        "debugging-tournament",
        (Cell("B0"), Cell("S1", "systematic-debugging"), Cell("S2", "ce-debug")),
    ),
    Study("test-driven-development", (Cell("B0"), Cell("S1", "test-driven-development"))),
    Study("property-based-testing", (Cell("B0"), Cell("S1", "property-based-testing"))),
    Study("differential-security-review", (Cell("B0"), Cell("S1", "differential-review"))),
    Study("review-team-topology", (Cell("B0"), Cell("S1", "ce-code-review"))),
    Study("mcp-server-construction", (Cell("B0"), Cell("S1", "mcp-builder"))),
    Study("webapp-testing", (Cell("B0"), Cell("S1", "webapp-testing"))),
    Study(
        "frontend-design",
        (Cell("B0"), Cell("S1", "frontend-design")),
        "frontend-design-r3",
    ),
    Study(
        "recursive-skill-improvement",
        (Cell("B0"), Cell("S1", "skill-creator"), Cell("S2", "skill-improver")),
    ),
)


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, document: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def private_ref(uri: str, path: Path) -> dict[str, object]:
    return {
        "uri": uri,
        "sha256": sha256_path(path),
        "revision": CALIBRATION_REVISION,
        "visibility": "private",
    }


def parse_events(path: Path, skill_name: str | None) -> tuple[dict[str, int], int, bool]:
    usage = {
        "input_tokens": 0,
        "cached_input_tokens": 0,
        "output_tokens": 0,
        "reasoning_output_tokens": 0,
    }
    event_count = 0
    skill_activated = False
    activation_marker = None
    if skill_name:
        activation_marker = f"home/.codex/skills/{skill_name}/SKILL.md"
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event_count += 1
        event = json.loads(line)
        if event.get("type") == "turn.completed":
            usage.update(event.get("usage", {}))
        if activation_marker and activation_marker in line:
            skill_activated = True
    return usage, event_count, skill_activated


def build_run(
    raw_root: Path,
    study: Study,
    cell: Cell,
    study_hash: str,
) -> tuple[dict[str, object], dict[str, object]]:
    raw_study = raw_root / (study.raw_directory or study.study_id)
    raw = raw_study / f"{cell.condition_id}-01"
    evaluation_suffix = "-evaluation-r4" if study.study_id == "frontend-design" else "-evaluation"
    evaluation_root = raw_study / f"{cell.condition_id}-01{evaluation_suffix}"
    invocation_path = raw / "sandbox-invocation.json"
    events_path = raw / "stdout.log"
    evaluation_path = evaluation_root / "candidate-evaluation.json"
    final_path = raw / "workspace" / "AEL_FINAL.md"
    invocation = read_json(invocation_path)
    evaluation = read_json(evaluation_path)
    usage, event_count, skill_activated = parse_events(events_path, cell.skill_name)

    expected_intervention = cell.skill_name is not None
    integrity_issues = [
        "The maintainer-approved reusable ChatGPT credential was readable by the Codex process; only pinned, reviewed intervention snapshots and maintainer-controlled fixtures were used."
    ]
    invalid_reasons: list[str] = []
    if invocation["image_id"] != RUNNER_IMAGE_ID or invocation["proxy_image_id"] != PROXY_IMAGE_ID:
        invalid_reasons.append("unexpected runtime image identity")
    if invocation["fixture_sha256_before"] != invocation["fixture_sha256_after"]:
        invalid_reasons.append("canonical fixture identity changed")
    if invocation["intervention_injected"] is not expected_intervention:
        invalid_reasons.append("intervention injection did not match the condition")
    scan = invocation.get("secret_persistence_scan")
    if scan and scan["exact_value_match_count"] != 0:
        invalid_reasons.append("credential material was detected in persisted output")
    if invalid_reasons:
        status = "invalid"
    elif invocation["exit_code"] != 0:
        status = "invalid"
        invalid_reasons.append("Codex runner did not reach a normal terminal state")
    elif not evaluation["accepted"]:
        status = "failed"
    else:
        status = "valid"

    run_id = f"kizz:ael:run:agent-skills-season-1:{study.study_id}:{cell.condition_id}:01"
    private_prefix = (
        f"urn:kizz:ael:private-run:agent-skills-season-1:{study.study_id}:{cell.condition_id}:01"
    )
    source_refs = [
        private_ref(private_prefix + ":events", events_path),
        private_ref(private_prefix + ":invocation", invocation_path),
        private_ref(private_prefix + ":evaluation", evaluation_path),
    ]
    outputs: list[dict[str, object]] = []
    if final_path.is_file():
        outputs.append(private_ref(private_prefix + ":final", final_path))
    workspace_path = raw / "workspace"
    if workspace_path.is_dir():
        outputs.append(
            {
                "uri": private_prefix + ":candidate",
                "sha256": tree_sha256(workspace_path),
                "revision": CALIBRATION_REVISION,
                "visibility": "private",
            }
        )
    record: dict[str, object] = {
        "schema_version": "ael.run-record/0.1",
        "object_type": "run_record",
        "run_id": run_id,
        "study_ref": {
            "study_id": f"kizz:ael:study:agent-skills-season-1:{study.study_id}",
            "revision": 1,
            "uri": f"../../../../manifests/{study.study_id}.study-manifest.json",
            "sha256": study_hash,
            "visibility": "public",
        },
        "condition_id": cell.condition_id,
        "task": {
            "task_pack_id": "agent-skills-season-1-calibration-v1",
            "task_id": study.study_id,
            "stratum": study.study_id,
            "role": "calibration",
        },
        "repeat_index": 1,
        "status": status,
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
        "outputs": outputs,
        "effects": [],
        "event_summary": {
            "captured": True,
            "event_count": event_count,
            "authenticated_actor_ids": [],
            "limitations": [
                "The provider did not expose an immutable model revision.",
                "Raw Codex events remain private and are represented here by content hashes.",
                "Encrypted provider traffic was not inspected.",
            ],
        },
        "integrity_issues": integrity_issues,
        "source_refs": source_refs,
    }
    if status == "invalid":
        record["invalid_reason"] = "; ".join(invalid_reasons)
    summary = {
        "run_id": run_id,
        "condition_id": cell.condition_id,
        "accepted": bool(evaluation["accepted"]),
        "visible_passed": evaluation["visible_exit_code"] == 0,
        "skill_expected": expected_intervention,
        "skill_activated": skill_activated,
        "status": status,
        "usage": record["usage"],
        "evaluation_ref": source_refs[2],
        "events_ref": source_refs[0],
    }
    return record, summary


def measurement(
    measurement_id: str,
    kind: str,
    metric: str,
    value: int | bool,
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
        "task_id": summary["condition_id"],
        "stratum": "activation-calibration",
        "evaluator": {
            "evaluator_id": "ael-deterministic-taskpack-evaluator",
            "kind": "deterministic",
            "blinded": True,
        },
        "evidence_refs": [summary[evidence_key]],
    }


def build_study(
    raw_root: Path,
    output_root: Path,
    study: Study,
    generated_at: str,
    concept_hash: str,
) -> list[dict[str, object]]:
    output = output_root / study.study_id
    runs_dir = output / "runs"
    manifest_path = SEASON_ROOT / "manifests" / f"{study.study_id}.study-manifest.json"
    manifest_hash = sha256_path(manifest_path)
    summaries: list[dict[str, object]] = []
    run_refs: list[dict[str, object]] = []
    for cell in study.cells:
        record, summary = build_run(raw_root, study, cell, manifest_hash)
        filename = f"{cell.condition_id}-01.json"
        run_path = runs_dir / filename
        write_json(run_path, record)
        summaries.append(summary)
        run_refs.append(
            {
                "run_id": record["run_id"],
                "uri": f"runs/{filename}",
                "sha256": sha256_path(run_path),
                "visibility": "public",
            }
        )

    measurements: list[dict[str, object]] = []
    for summary in summaries:
        condition = str(summary["condition_id"])
        measurements.extend(
            [
                measurement(
                    f"acceptance:{condition}",
                    "deterministic",
                    "calibration_task_accepted",
                    bool(summary["accepted"]),
                    "boolean",
                    "higher_better",
                    summary,
                    "evaluation_ref",
                ),
                measurement(
                    f"visible-tests:{condition}",
                    "deterministic",
                    "visible_tests_passed",
                    bool(summary["visible_passed"]),
                    "boolean",
                    "higher_better",
                    summary,
                    "evaluation_ref",
                ),
                measurement(
                    f"generated-work:{condition}",
                    "cost",
                    "generated_work_tokens",
                    int(summary["usage"]["output_tokens"])
                    + int(summary["usage"]["reasoning_output_tokens"]),
                    "tokens",
                    "lower_better",
                    summary,
                    "events_ref",
                ),
                measurement(
                    f"wall-time:{condition}",
                    "cost",
                    "wall_time",
                    int(summary["usage"]["wall_time_ms"]),
                    "milliseconds",
                    "lower_better",
                    summary,
                    "events_ref",
                ),
            ]
        )
        if summary["skill_expected"]:
            measurements.append(
                measurement(
                    f"skill-activation:{condition}",
                    "process",
                    "skill_activated",
                    bool(summary["skill_activated"]),
                    "boolean",
                    "target",
                    summary,
                    "events_ref",
                )
            )

    raw_study = raw_root / (study.raw_directory or study.study_id)
    fixture_mutation = any(item["status"] == "invalid" for item in summaries)
    all_accepted = all(item["accepted"] for item in summaries)
    all_treatments_activated = all(
        item["skill_activated"] for item in summaries if item["skill_expected"]
    )
    limitations = [
        "One non-randomized public calibration repeat was run per listed condition; this is not an effect estimate.",
        "The public mechanics task is intentionally small and may prescribe behavior that masks treatment differences.",
        "Kizz selected the sources, authored the task, operated the runner, and evaluated the result.",
        "The provider exposes a model identifier but not an immutable model revision.",
        "Realized token usage and wall time were recorded but not forced to equality.",
        "The maintainer-approved reusable ChatGPT credential was process-readable; persisted outputs were exact-value scanned, but encrypted provider traffic was not inspected.",
        "No effectiveness, transfer, production, downstream rework, or user outcome was measured.",
    ]
    measurement_set: dict[str, object] = {
        "schema_version": "ael.measurement-set/0.1",
        "object_type": "measurement_set",
        "measurement_set_id": f"kizz:ael:measurements:agent-skills-season-1:{study.study_id}:activation-v1",
        "study_ref": {
            "study_id": f"kizz:ael:study:agent-skills-season-1:{study.study_id}",
            "revision": 1,
            "uri": f"../../../manifests/{study.study_id}.study-manifest.json",
            "sha256": manifest_hash,
            "visibility": "public",
        },
        "measurements": measurements,
        "critical_failures": [
            {
                "failure_id": "canonical-fixture-or-runtime-integrity-failure",
                "severity": "critical",
                "observed": fixture_mutation,
                "description": "No canonical fixture, runtime-image, intervention-injection, or persisted-secret integrity failure was observed."
                if not fixture_mutation
                else "At least one calibration cell was invalidated by an integrity check.",
                "run_ids": [item["run_id"] for item in summaries],
                "evidence_refs": [item["events_ref"] for item in summaries],
            }
        ],
        "limitations": limitations,
        "source_refs": [
            {
                "uri": f"urn:kizz:ael:private-run-set:agent-skills-season-1:{study.study_id}:activation-v1",
                "sha256": tree_sha256(raw_study),
                "revision": CALIBRATION_REVISION,
                "visibility": "private",
            }
        ],
    }
    measurement_path = output / "measurement-set.json"
    write_json(measurement_path, measurement_set)

    activation_status = "supported" if all_treatments_activated else "contradicted"
    decision_disposition = "narrow" if all_accepted and all_treatments_activated else "inconclusive"
    decision_summary = (
        "The pinned condition is execution-compatible with the current Codex Docker adapter and may proceed to discriminating screening; this calibration does not establish effectiveness."
        if decision_disposition == "narrow"
        else "At least one condition failed activation or deterministic calibration acceptance; resolve compatibility before effectiveness screening."
    )
    receipt: dict[str, object] = {
        "schema_version": "ael.evidence-receipt/0.1",
        "object_type": "evidence_receipt",
        "receipt_id": f"kizz:ael:receipt:agent-skills-season-1:{study.study_id}:activation-v1",
        "generated_at": generated_at,
        "concept_ref": {
            "concept_id": CONCEPT_ID,
            "revision": 1,
            "uri": "../../../concept.json",
            "sha256": concept_hash,
            "visibility": "public",
        },
        "study_ref": {
            "study_id": f"kizz:ael:study:agent-skills-season-1:{study.study_id}",
            "revision": 1,
            "uri": f"../../../manifests/{study.study_id}.study-manifest.json",
            "sha256": manifest_hash,
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
                "Kizz owns source selection, task pack, execution, evaluation, and continuation decision."
            ],
            "disclosure": "This is maintainer activation calibration, not independent certification or a confirmatory skill-effect study.",
        },
        "decision": {
            "disposition": decision_disposition,
            "summary": decision_summary,
            "scope": [
                "Codex CLI 0.146.0 with gpt-5.6-sol at xhigh effort",
                "the exact pinned runner and proxy image identities in the run records",
                "one public maintainer-authored mechanics task",
                "one non-randomized repeat per listed condition",
            ],
            "reversal_trigger": "Re-evaluate after any source, task, runner, model, effort, evaluator, or credential-boundary change, or if a repeated screening study contradicts this compatibility result.",
        },
        "evaluated_claims": [
            {
                "claim_id": f"AEL-S1-{study.study_id.upper()}-CAL-01",
                "statement": "The listed conditions reached a normal Codex terminal state and were evaluated against the public mechanics task.",
                "status": "supported"
                if all(item["status"] != "invalid" for item in summaries)
                else "contradicted",
                "claim_level": "workflow",
                "scope": ["listed activation-v1 cells", "maintainer-controlled fixture"],
                "evidence_refs": [f"acceptance:{item['condition_id']}" for item in summaries],
                "falsifier": "A retained invocation or evaluation shows an invalid runtime, changed fixture, or missing terminal evaluation.",
            },
            {
                "claim_id": f"AEL-S1-{study.study_id.upper()}-CAL-02",
                "statement": "Every treatment skill was installed and explicitly read during its assigned treatment cell.",
                "status": activation_status,
                "claim_level": "artifact",
                "scope": ["listed treatment cells", "retained private Codex event streams"],
                "evidence_refs": [
                    f"skill-activation:{item['condition_id']}"
                    for item in summaries
                    if item["skill_expected"]
                ],
                "falsifier": "A retained treatment event stream lacks the exact installed SKILL.md read.",
            },
            {
                "claim_id": f"AEL-S1-{study.study_id.upper()}-CAL-03",
                "statement": "This single public calibration task does not identify a skill-effect difference or support a leaderboard position.",
                "status": "bounded",
                "claim_level": "workflow",
                "scope": ["single public calibration repeat"],
                "evidence_refs": [f"acceptance:{item['condition_id']}" for item in summaries],
                "falsifier": "A frozen repeated screening or holdout study measures the prespecified primary estimand with uncertainty and critical-failure gates.",
            },
        ],
        "unsupported_inferences": [
            "The treatment skill improves correctness, quality, security, design quality, or cost-effectiveness.",
            "A treatment that used fewer tokens or less wall time is superior.",
            "The result transfers to real repositories, other tasks, models, or agent runtimes.",
            "Codex is superior to Claude Code, Cursor, another CLI, or a raw model API.",
            "The current runner is safe for arbitrary unreviewed third-party submissions.",
        ],
        "limitations": limitations,
        "invalidation_triggers": [
            "A change to a pinned source, task, Codex version, model, effort, image, proxy policy, prompt, or evaluator",
            "Evidence that credential material entered persisted artifacts or an unauthorized network path",
            "A repeated screening or real-shadow study contradicts the activation observation",
            "A public claim presents this calibration as effectiveness evidence or a leaderboard result",
        ],
        "state": {
            "experiment": "activation calibration completed; effectiveness screening not run",
            "artifact": "source-locked public intervention snapshot and calibration task locally validated",
            "repository": "generated evidence present in the local release candidate",
            "publication": "prepared, not published",
            "deployment": "not deployed",
            "outcome": "not observed",
        },
        "publication_state": "public_ready",
        "generator": {"name": "agentic-evidence-lab", "version": "0.1.0a2"},
    }
    receipt_path = output / "evidence-receipt.json"
    write_json(receipt_path, receipt)
    return summaries


def write_summary(output_root: Path, all_summaries: list[dict[str, object]]) -> None:
    lines = [
        "# Agent Skills Season 1 — activation calibration",
        "",
        "This table reports one public mechanics run per listed condition. It is a runtime and activation matrix, not an effectiveness leaderboard.",
        "",
        "| Study | Condition | Accepted | Skill read | Generated tokens | Wall time |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for item in all_summaries:
        usage = item["usage"]
        generated = int(usage["output_tokens"]) + int(usage["reasoning_output_tokens"])
        activated = (
            "n/a" if not item["skill_expected"] else ("yes" if item["skill_activated"] else "no")
        )
        lines.append(
            f"| {item['study_id']} | {item['condition_id']} | {'yes' if item['accepted'] else 'no'} | {activated} | {generated} | {int(usage['wall_time_ms']) / 1000:.1f}s |"
        )
    lines.extend(
        [
            "",
            "## Decision boundary",
            "",
            "A treatment advances only as an execution-compatible candidate. Ranking requires a frozen discriminating screening pack, repeated matched cells, prespecified primary endpoints and critical-failure gates, followed by untouched holdout confirmation.",
            "",
            "Truthful-completion revision 1 and frontend-design revision 2 are retained separately because activation exposed task/evaluator contract defects. The corrected truthful revision 2 candidates and frontend revision 3 candidates, evaluated under the format-only revision 4 contract, are represented above.",
        ]
    )
    (output_root / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--generated-at", required=True)
    args = parser.parse_args()
    raw_root = args.raw_root.resolve()
    output_root = args.output.resolve()
    concept_hash = sha256_path(SEASON_ROOT / "concept.json")
    all_summaries: list[dict[str, object]] = []
    for study in STUDIES:
        summaries = build_study(raw_root, output_root, study, args.generated_at, concept_hash)
        for summary in summaries:
            summary["study_id"] = study.study_id
        all_summaries.extend(summaries)
    write_summary(output_root, all_summaries)
    print(json.dumps({"studies": len(STUDIES), "runs": len(all_summaries)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
