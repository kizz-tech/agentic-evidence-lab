from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from completion_integrity_activation_support import load_json, sha256_path, write_json_atomic

from ael.completion_integrity_activation import (
    decide_activation,
    decision_id_from_study_id,
    decision_measurements,
    validate_observations,
)
from ael.sandbox import SandboxError

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STUDY_ROOT = ROOT / "studies" / "completion-integrity" / "activation-v1"
DEFAULT_RESULT_ROOT = DEFAULT_STUDY_ROOT / "results"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SandboxError(f"activation materializer failed: {message}")


def _ref(uri: str, sha256: str, visibility: str = "public") -> dict[str, str]:
    return {"uri": uri, "sha256": sha256, "visibility": visibility}


def _study_ref(
    manifest_sha256: str, *, uri: str, study_id: str, study_revision: int
) -> dict[str, object]:
    return {
        "uri": uri,
        "sha256": manifest_sha256,
        "visibility": "public",
        "study_id": study_id,
        "revision": study_revision,
    }


def _identity_prefix(study_id: str, object_type: str, study_revision: int) -> str:
    prefix = "kizz:ael:study:"
    _require(study_id.startswith(prefix), "study identity is not canonical")
    activation = study_id.removeprefix(prefix)
    if study_revision == 1 and activation == "completion-integrity-activation-v1":
        # Activation v1 was materialized before the generic revision-aware
        # implementation existed. Preserve its public IDs byte-for-byte.
        return f"kizz:ael:{object_type}:completion-integrity:activation-v1"
    return f"kizz:ael:{object_type}:{activation}:revision:{study_revision}"


def _measurement_prefix(study_revision: int) -> str:
    return "ci11" if study_revision == 1 else f"ci11-r{study_revision}"


def _run_id(cell_id: str, *, run_prefix: str) -> str:
    return f"{run_prefix}:{cell_id}"


def _private_output_refs(cell: Mapping[str, Any], role: str, cell_id: str) -> list[dict[str, str]]:
    private_refs = cell.get("private_refs")
    if not isinstance(private_refs, Mapping):
        return []
    key = "candidate_tree_sha256" if role == "executor" else "submission_sha256"
    digest = private_refs.get(key)
    if not isinstance(digest, str):
        return []
    label = "candidate" if role == "executor" else "reporter-submission"
    return [_ref(f"urn:kizz:ael:private:{label}:{cell_id}", digest, "hidden")]


def _run_record(
    *,
    entry: Mapping[str, Any],
    cell: Mapping[str, Any] | None,
    manifest_sha256: str,
    freeze_sha256: str,
    freeze: Mapping[str, Any],
    study_root: Path,
    study_id: str,
    study_revision: int,
    run_prefix: str,
) -> dict[str, Any]:
    cell_id = str(entry["cell_id"])
    role = str(entry["role"])
    status = str(cell.get("status")) if cell else "unrun"
    if status not in {"valid", "invalid"}:
        status = "unrun"
    usage = cell.get("usage") if cell else None
    if not isinstance(usage, Mapping):
        usage = {}
    context_sha = (
        cell.get("evidence_tree_sha256")
        if role == "reporter" and cell
        else cell.get("artifact_sha256")
        if cell
        else None
    )
    if not isinstance(context_sha, str) or len(context_sha) != 64:
        context_sha = "0" * 64
    prompt_name = "executor.txt" if role == "executor" else f"reporter-{entry['condition_id']}.txt"
    prompt_sha = sha256_path(study_root / "prompts" / prompt_name)
    image_id = (
        str(freeze["runtime"]["executor_image_id"])
        if role == "executor"
        else str(freeze["runtime"]["reporter_image_id"])
    )
    issues = list(cell.get("issues", [])) if cell else ["cell was not submitted"]
    source_refs = [_ref("../../freeze.json", freeze_sha256)]
    if cell:
        private_refs = cell.get("private_refs")
        if isinstance(private_refs, Mapping) and isinstance(private_refs.get("events_sha256"), str):
            source_refs.append(
                _ref(
                    f"urn:kizz:ael:private:codex-events:{cell_id}",
                    str(private_refs["events_sha256"]),
                    "hidden",
                )
            )
    return {
        "schema_version": "ael.run-record/0.1",
        "object_type": "run_record",
        "run_id": _run_id(cell_id, run_prefix=run_prefix),
        "study_ref": _study_ref(
            manifest_sha256,
            uri="../../study-manifest.json",
            study_id=study_id,
            study_revision=study_revision,
        ),
        "condition_id": str(entry["condition_id"] or "E0"),
        "task": {
            "task_pack_id": "completion-integrity-v2-activation",
            "task_id": str(entry["task_id"]),
            "stratum": "python-cli" if entry["task_id"] == "CI2-PY-01" else "typescript-config",
            "role": "calibration",
        },
        "repeat_index": 1,
        "status": status,
        **({"invalid_reason": "; ".join(issues)} if status == "invalid" else {}),
        "runtime": {
            "harness": {"name": "codex-cli", "version": "0.146.0"},
            "model": {
                "provider": "OpenAI",
                "model_id": str(freeze["runtime"]["model"]),
                "effort": str(freeze["runtime"]["reasoning_effort"]),
                "immutable_revision_exposed": False,
            },
            "sandbox": (
                "docker-ephemeral-writable-candidate-openai-proxy"
                if role == "executor"
                else "docker-read-only-evidence-openai-proxy"
            ),
            "environment": {
                "ephemeral": True,
                "identity_available": True,
                "digest": image_id.removeprefix("sha256:"),
            },
            "tool_policy_sha256": prompt_sha,
            "context_sha256": context_sha,
        },
        "usage": {
            "input_tokens": int(usage.get("input_tokens", 0)),
            "cached_input_tokens": int(usage.get("cached_input_tokens", 0)),
            "output_tokens": int(usage.get("output_tokens", 0)),
            "reasoning_output_tokens": int(usage.get("reasoning_output_tokens", 0)),
            "wall_time_ms": int(usage.get("wall_time_ms", 0)),
        },
        "outputs": _private_output_refs(cell or {}, role, cell_id),
        "effects": [
            {
                "effect_type": (
                    "candidate_workspace_change" if role == "executor" else "terminal_claim_report"
                ),
                "target": f"urn:kizz:ael:private:{role}:{cell_id}",
                "outcome": "observed" if status == "valid" else "unknown",
                "evidence_refs": source_refs,
            }
        ],
        "event_summary": {
            "captured": bool(cell),
            "event_count": int(cell.get("event_count", 0)) if cell else 0,
            "authenticated_actor_ids": [],
            "limitations": [
                "Raw Codex events are retained privately; this record exposes hashes and counts only."
            ],
        },
        "integrity_issues": issues,
        "source_refs": source_refs,
    }


def _measurement(
    *,
    measurement_id: str,
    metric: str,
    value: object,
    unit: str,
    run_ids: Sequence[str],
    evidence_ref: Mapping[str, str],
    kind: str = "deterministic",
    direction: str = "descriptive",
    condition_id: str | None = None,
    task_id: str | None = None,
    evaluator_id: str,
) -> dict[str, Any]:
    return {
        "measurement_id": measurement_id,
        "kind": kind,
        "metric": metric,
        "value": value,
        "unit": unit,
        "direction": direction,
        "run_ids": list(run_ids),
        **({"condition_id": condition_id} if condition_id else {}),
        **({"task_id": task_id} if task_id else {}),
        "evaluator": {
            "evaluator_id": evaluator_id,
            "kind": "deterministic",
            "blinded": False,
        },
        "evidence_refs": [dict(evidence_ref)],
    }


def _measurement_set(
    *,
    observations: Mapping[str, Any],
    decision: Mapping[str, Any],
    freeze: Mapping[str, Any],
    run_paths: Mapping[str, Path],
    observations_sha256: str,
    manifest_sha256: str,
    study_root: Path,
    study_id: str,
    study_revision: int,
    run_prefix: str,
    measurement_set_id: str,
    measurement_prefix: str,
) -> dict[str, Any]:
    observation_ref = _ref("observations.json", observations_sha256)
    evaluator_id = f"ael.completion-integrity.activation-v{study_revision}"
    all_run_ids = [
        _run_id(str(entry["cell_id"]), run_prefix=run_prefix) for entry in freeze["schedule"]
    ]
    executor_run_ids = [run_id for run_id in all_run_ids if run_id.endswith("-E0")]
    reporter_run_ids = [run_id for run_id in all_run_ids if not run_id.endswith("-E0")]
    metric_runs = {
        "task_roots": all_run_ids,
        "observable_chain_complete": executor_run_ids,
        "executor_claim_agreement": executor_run_ids,
        "B0_claim_agreement": [run_id for run_id in reporter_run_ids if run_id.endswith("-B0")],
        "T1_claim_agreement": [run_id for run_id in reporter_run_ids if run_id.endswith("-T1")],
        "artifact_or_evaluator_exposure": reporter_run_ids,
    }
    measurements = [
        _measurement(
            measurement_id=f"{measurement_prefix}:{metric}",
            metric=metric,
            value=value,
            unit="count",
            run_ids=metric_runs[metric],
            evidence_ref=observation_ref,
            kind="aggregate",
            condition_id=metric[:2] if metric.startswith(("B0", "T1")) else None,
            evaluator_id=evaluator_id,
        )
        for metric, value in decision_measurements(decision)
    ]
    cells_by_id: dict[str, Mapping[str, Any]] = {}
    for task in observations["tasks"]:
        task_id = str(task["task_id"])
        cells_by_id[f"{task_id}-E0"] = {
            "claim_agreement": task["executor_claim_agreement"],
            "capture_state": task["capture_state"],
        }
        for reporter in task["reporters"]:
            cells_by_id[f"{task_id}-{reporter['condition_id']}"] = reporter
    for cell_id, path in sorted(run_paths.items()):
        run = load_json(path)
        evidence_ref = _ref(f"runs/{path.name}", sha256_path(path))
        run_id = str(run["run_id"])
        measurements.extend(
            [
                _measurement(
                    measurement_id=f"{measurement_prefix}:{cell_id}:wall-time-ms",
                    metric="wall_time",
                    value=run["usage"]["wall_time_ms"],
                    unit="ms",
                    run_ids=[run_id],
                    evidence_ref=evidence_ref,
                    kind="cost",
                    task_id=str(run["task"]["task_id"]),
                    evaluator_id=evaluator_id,
                ),
                _measurement(
                    measurement_id=f"{measurement_prefix}:{cell_id}:generated-tokens",
                    metric="generated_work_tokens",
                    value=run["usage"]["output_tokens"] + run["usage"]["reasoning_output_tokens"],
                    unit="tokens",
                    run_ids=[run_id],
                    evidence_ref=evidence_ref,
                    kind="cost",
                    task_id=str(run["task"]["task_id"]),
                    evaluator_id=evaluator_id,
                ),
            ]
        )
        cell = cells_by_id[cell_id]
        if cell_id.endswith("-E0"):
            measurements.append(
                _measurement(
                    measurement_id=f"{measurement_prefix}:{cell_id}:capture-state",
                    metric="observable_chain_state",
                    value=cell["capture_state"],
                    unit="state",
                    run_ids=[run_id],
                    evidence_ref=observation_ref,
                    kind="process",
                    task_id=str(run["task"]["task_id"]),
                    evaluator_id=evaluator_id,
                )
            )
        else:
            measurements.append(
                _measurement(
                    measurement_id=f"{measurement_prefix}:{cell_id}:tool-events",
                    metric="reporter_tool_event_count",
                    value=cell["tool_event_count"],
                    unit="events",
                    run_ids=[run_id],
                    evidence_ref=observation_ref,
                    kind="process",
                    condition_id=str(run["condition_id"]),
                    task_id=str(run["task"]["task_id"]),
                    evaluator_id=evaluator_id,
                )
            )
    return {
        "schema_version": "ael.measurement-set/0.1",
        "object_type": "measurement_set",
        "measurement_set_id": measurement_set_id,
        "study_ref": _study_ref(
            manifest_sha256,
            uri="../study-manifest.json",
            study_id=study_id,
            study_revision=study_revision,
        ),
        "measurements": measurements,
        "critical_failures": [
            {
                "failure_id": f"{measurement_prefix}:protocol-integrity-failure",
                "severity": "critical",
                "observed": decision["status"] == "protocol_invalid",
                "description": "The six-cell activation schedule did not finish under every frozen integrity boundary.",
                "run_ids": all_run_ids,
                "evidence_refs": [observation_ref],
            }
        ],
        "limitations": [
            "Two maintainer-authored sacrificial roots support activation diagnostics only, not a population estimate.",
            "Raw tasks, evaluator bytes, candidate workspaces, and Codex events are withheld.",
            "The hosted model exposed no immutable provider revision and the historical calls are not replayable.",
            "B0/T1 counts are descriptive; no effect, reliability, transfer, model-only, production, or independent-reproduction claim is supported.",
        ],
        "source_refs": [
            observation_ref,
            _ref("../freeze.json", sha256_path(study_root / "freeze.json")),
        ],
    }


def _receipt(
    *,
    generated_at: str,
    decision: Mapping[str, Any],
    manifest_sha256: str,
    run_paths: Mapping[str, Path],
    measurement_path: Path,
    study_root: Path,
    study_id: str,
    study_revision: int,
    run_prefix: str,
    measurement_set_id: str,
    receipt_id: str,
    claim_prefix: str,
    measurement_prefix: str,
) -> dict[str, Any]:
    counts = decision["condition_counts"]
    disposition_map = {
        "adopt_adapter_for_alpha12_pilot": "narrow",
        "reject_structured_reporter_prompt": "reject",
        "revise_activation_adapter": "inconclusive",
        "revise_capture_mapping": "inconclusive",
        "revise_reporter_protocol": "inconclusive",
    }
    completed_protocol = decision["status"] == "complete"
    claim_level = "workflow" if completed_protocol else "artifact"
    decision_statement = str(decision["reason"])
    count_statement = (
        "On the exact two roots, B0 produced "
        f"{counts['B0']['claim_agreement']} observed agreements across "
        f"{counts['B0']['valid']} valid calls; T1 produced "
        f"{counts['T1']['claim_agreement']} observed agreements across "
        f"{counts['T1']['valid']} valid calls. Unrun or invalid calls are not "
        "counted as disagreements; these are descriptive counts, not an effect estimate."
    )
    if not completed_protocol:
        decision_statement = f"The published activation bundle records: {decision_statement}"
        count_statement = f"The published normalized record states: {count_statement}"

    return {
        "schema_version": "ael.evidence-receipt/0.1",
        "object_type": "evidence_receipt",
        "receipt_id": receipt_id,
        "generated_at": generated_at,
        "concept_ref": {
            "uri": "../../concept.json",
            "sha256": sha256_path(study_root.parent / "concept.json"),
            "visibility": "public",
            "concept_id": "kizz:ael:concept:completion-integrity",
            "revision": 1,
        },
        "study_ref": _study_ref(
            manifest_sha256,
            uri="../study-manifest.json",
            study_id=study_id,
            study_revision=study_revision,
        ),
        "run_record_refs": [
            {
                "uri": f"runs/{path.name}",
                "sha256": sha256_path(path),
                "visibility": "public",
                "run_id": _run_id(cell_id, run_prefix=run_prefix),
            }
            for cell_id, path in sorted(run_paths.items())
        ],
        "measurement_set_ref": {
            "uri": "measurement-set.json",
            "sha256": sha256_path(measurement_path),
            "visibility": "public",
            "measurement_set_id": measurement_set_id,
        },
        "evidence_level": "runtime_conformant" if completed_protocol else "structurally_valid",
        "reproducibility": "not_rerunnable",
        "independence": {
            "label": "maintainer_evaluated",
            "role_overlaps": [
                "Kizz authored the method, sacrificial tasks, deterministic evaluators, adapters, analysis, and owner decision."
            ],
            "disclosure": "No independent task selection, evaluation, provider execution, or replication exists.",
        },
        "decision": {
            "disposition": disposition_map[str(decision["disposition"])],
            "summary": str(decision["reason"]),
            "scope": [
                "the versioned Completion Integrity activation adapter",
                "two qualified sacrificial Python and TypeScript roots",
                "the pinned Codex CLI 0.146.0 / gpt-5.6-sol xhigh stack",
            ],
            "reversal_trigger": "A recomputation mismatch, frozen-binding failure, hidden protocol breach, or larger preregistered pilot contradicts this bounded decision.",
        },
        "evaluated_claims": [
            {
                "claim_id": f"{claim_prefix}-01",
                "statement": decision_statement,
                "status": "bounded",
                "claim_level": claim_level,
                "scope": [
                    "exact two-root activation schedule",
                    "versioned owner capture and reporter adapters",
                ],
                "evidence_refs": [
                    f"{measurement_prefix}:observable_chain_complete",
                    f"{measurement_prefix}:artifact_or_evaluator_exposure",
                ],
                "falsifier": "A frozen recomputation produces a different disposition or any retained raw boundary check contradicts the normalized observation.",
            },
            {
                "claim_id": f"{claim_prefix}-02",
                "statement": count_statement,
                "status": "bounded",
                "claim_level": claim_level,
                "scope": ["B0 and T1 reporter calls over identical sealed task-level evidence"],
                "evidence_refs": [
                    f"{measurement_prefix}:B0_claim_agreement",
                    f"{measurement_prefix}:T1_claim_agreement",
                ],
                "falsifier": "The public observations or terminal-claim assessments recompute to different condition counts.",
            },
        ],
        "unsupported_inferences": [
            "The structured reporter caused a change in claim accuracy.",
            "Either reporter is reliable on a broader task population.",
            "The result identifies intrinsic gpt-5.6-sol or Codex quality.",
            "The workflow transfers to another model, harness, repository, organization, or production environment.",
            "The result is independently reproduced or externally outcome-verified.",
        ],
        "limitations": [
            "The frozen design contains only two sacrificial roots and schedules each reporter condition once per root; protocol-invalid execution can leave cells unrun.",
            "Task, evaluator, candidate, event, authentication, and personal-path bytes remain private.",
            "Maintainer authorship and evaluation overlap; provider state is not immutable or replayable.",
            "The reporter retained a built-in command tool inside a read-only evidence boundary; it was not tool-free.",
        ],
        "invalidation_triggers": [
            "Any public graph hash, frozen decision count, preregistration ordering, or protected private hash fails verification.",
            "Any reporter received task artifact, evaluator, executor workspace, intervention, or mutable evidence access.",
            "A hidden raw event, evaluator repeat, or no-retry journal contradicts the public normalized record.",
        ],
        "state": {
            "experiment": (
                "completed_under_frozen_protocol"
                if decision["status"] == "complete"
                else "terminated_protocol_invalid"
            ),
            "artifact": "public_bounded_result_materialized",
            "repository": "prepared_uncommitted",
            "publication": "prepared_not_published",
            "deployment": "not_applicable",
            "outcome": (
                "bounded_activation_observed"
                if decision["status"] == "complete"
                else "not_observed"
            ),
        },
        "publication_state": "public_ready",
        "generator": {"name": "ael-completion-integrity-activation-materializer", "version": "0.1"},
    }


def materialize(
    *,
    freeze_path: Path,
    raw_root: Path,
    result_root: Path,
    preregistration_sha: str,
    generated_at: str,
) -> dict[str, Any]:
    freeze = load_json(freeze_path)
    study_root = freeze_path.absolute().parent
    study_id = str(freeze["study_id"])
    study_revision = int(freeze["study_revision"])
    run_prefix = _identity_prefix(study_id, "run", study_revision)
    measurement_set_id = _identity_prefix(study_id, "measurements", study_revision)
    receipt_id = _identity_prefix(study_id, "receipt", study_revision)
    claim_prefix = "AEL-CI11" if study_revision == 1 else f"AEL-CI11-R{study_revision}"
    measurement_prefix = _measurement_prefix(study_revision)
    observations = validate_observations(load_json(raw_root / "observations.json"))
    decision = decide_activation(
        observations,
        decision_id=decision_id_from_study_id(study_id),
    )
    _require(
        load_json(raw_root / "decision.json") == decision, "private decision recomputation differs"
    )
    _require(
        observations["freeze_sha256"] == sha256_path(freeze_path),
        "observations refer to different freeze bytes",
    )
    _require(
        observations["preregistration_sha"] == preregistration_sha,
        "observations refer to a different preregistration commit",
    )
    if result_root.exists() and any(result_root.iterdir()):
        raise SandboxError("activation result root must be new or empty")
    (result_root / "runs").mkdir(parents=True, exist_ok=True)
    manifest_sha256 = sha256_path(study_root / "study-manifest.json")
    cells = {
        path.stem: load_json(path)
        for path in sorted((raw_root / "cells").glob("*.json"))
        if path.is_file() and not path.is_symlink()
    }
    run_paths: dict[str, Path] = {}
    for entry in freeze["schedule"]:
        cell_id = str(entry["cell_id"])
        path = result_root / "runs" / f"{cell_id}.json"
        write_json_atomic(
            path,
            _run_record(
                entry=entry,
                cell=cells.get(cell_id),
                manifest_sha256=manifest_sha256,
                freeze_sha256=sha256_path(freeze_path),
                freeze=freeze,
                study_root=study_root,
                study_id=study_id,
                study_revision=study_revision,
                run_prefix=run_prefix,
            ),
        )
        run_paths[cell_id] = path
    observations_path = result_root / "observations.json"
    write_json_atomic(observations_path, observations)
    decision_path = result_root / "decision.json"
    write_json_atomic(decision_path, decision)
    write_json_atomic(
        result_root / "freeze-ref.json",
        {
            "schema_version": "ael.completion-integrity-activation-freeze-ref/0.1-pilot",
            "freeze_id": freeze["freeze_id"],
            "freeze_sha256": sha256_path(freeze_path),
            "preregistration_sha": preregistration_sha,
            "observations_sha256": sha256_path(observations_path),
            "decision_sha256": sha256_path(decision_path),
            "private_pack_sha256": freeze["private_pack"]["supply_artifact_sha256"],
            "qualification_sha256": freeze["qualification"]["receipt_sha256"],
        },
    )
    measurement_path = result_root / "measurement-set.json"
    write_json_atomic(
        measurement_path,
        _measurement_set(
            observations=observations,
            decision=decision,
            freeze=freeze,
            run_paths=run_paths,
            observations_sha256=sha256_path(observations_path),
            manifest_sha256=manifest_sha256,
            study_root=study_root,
            study_id=study_id,
            study_revision=study_revision,
            run_prefix=run_prefix,
            measurement_set_id=measurement_set_id,
            measurement_prefix=measurement_prefix,
        ),
    )
    receipt_path = result_root / "evidence-receipt.json"
    write_json_atomic(
        receipt_path,
        _receipt(
            generated_at=generated_at,
            decision=decision,
            manifest_sha256=manifest_sha256,
            run_paths=run_paths,
            measurement_path=measurement_path,
            study_root=study_root,
            study_id=study_id,
            study_revision=study_revision,
            run_prefix=run_prefix,
            measurement_set_id=measurement_set_id,
            receipt_id=receipt_id,
            claim_prefix=claim_prefix,
            measurement_prefix=measurement_prefix,
        ),
    )
    return {
        "decision": decision,
        "runs": len(run_paths),
        "measurements": len(load_json(measurement_path)["measurements"]),
        "receipt_sha256": sha256_path(receipt_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize a public activation result")
    parser.add_argument("--freeze", type=Path, default=DEFAULT_STUDY_ROOT / "freeze.json")
    parser.add_argument("--raw-root", required=True, type=Path)
    parser.add_argument("--result-root", type=Path, default=DEFAULT_RESULT_ROOT)
    parser.add_argument("--preregistration-sha", required=True)
    parser.add_argument("--generated-at", required=True)
    args = parser.parse_args()
    try:
        result = materialize(
            freeze_path=args.freeze.absolute(),
            raw_root=args.raw_root.absolute(),
            result_root=args.result_root.absolute(),
            preregistration_sha=args.preregistration_sha,
            generated_at=args.generated_at,
        )
    except SandboxError as exc:
        print(f"activation materializer failed: {exc}")
        return 1
    print(
        "activation materializer pass: "
        f"runs={result['runs']} measurements={result['measurements']} "
        f"disposition={result['decision']['disposition']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
