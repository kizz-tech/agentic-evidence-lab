from __future__ import annotations

import argparse
import os
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from completion_integrity_support import write_json_atomic

from ael.completion_integrity import decide_effect
from ael.prospective_study import load_json_object, sha256_path
from ael.sandbox import SandboxError, tree_sha256
from ael.validation import validate

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "src" / "ael" / "completion_integrity.py"
MATERIALIZER_PATH = Path(__file__).resolve()
RUNNER_PATH = ROOT / "tools" / "run_completion_integrity.py"
AUDIT_PATH = ROOT / "src" / "ael" / "completion_integrity_audit.py"
SUPPORT_PATH = ROOT / "tools" / "completion_integrity_support.py"
CODEX_RUNNER_PATH = ROOT / "src" / "ael" / "codex_runner.py"
SANDBOX_PATH = ROOT / "src" / "ael" / "sandbox.py"
PROSPECTIVE_PATH = ROOT / "src" / "ael" / "prospective_study.py"
VALIDATION_PATH = ROOT / "src" / "ael" / "validation.py"
SCHEMAS_PATH = ROOT / "src" / "ael" / "schemas"
GIT_SHA = re.compile(r"^[a-f0-9]{40}$")


def _repo_path(reference: Mapping[str, Any], label: str) -> Path:
    uri = reference.get("uri")
    digest = reference.get("sha256")
    if not isinstance(uri, str) or not uri or uri.startswith("/") or "\\" in uri:
        raise SandboxError(f"{label} has an unsafe repository URI")
    path = (ROOT / uri).resolve()
    if not path.is_relative_to(ROOT.resolve()) or path.is_symlink() or not path.is_file():
        raise SandboxError(f"{label} is missing, unsafe, or outside the repository")
    if digest != sha256_path(path):
        raise SandboxError(f"{label} hash mismatch")
    return path


def _relative(owner: Path, target: Path) -> str:
    return Path(os.path.relpath(target.resolve(), owner.resolve().parent)).as_posix()


def _artifact_ref(owner: Path, target: Path, **identity: object) -> dict[str, object]:
    return {
        **identity,
        "uri": _relative(owner, target),
        "sha256": sha256_path(target),
        "visibility": "public",
    }


def _private_ref(uri: str, digest: str) -> dict[str, str]:
    return {"uri": uri, "sha256": digest, "visibility": "hidden"}


def _run_id(cell_id: str) -> str:
    return f"kizz:ael:run:completion-integrity:{cell_id}"


def _task_pack(observation: Mapping[str, Any]) -> tuple[str, str]:
    if observation.get("task_role") == "confirmation":
        return "completion-integrity-v1-confirmation", "holdout"
    return "completion-integrity-v1-screening", "screening"


def _run_record(
    observation: Mapping[str, Any],
    freeze: Mapping[str, Any],
    manifest_path: Path,
    freeze_path: Path,
    observations_sha256: str,
    output_path: Path,
) -> dict[str, Any]:
    cell_id = str(observation["cell_id"])
    status = observation.get("status")
    public_status = (
        "valid" if status == "valid" else "invalid" if status == "operational_invalid" else "unrun"
    )
    usage = observation.get("usage") if isinstance(observation.get("usage"), dict) else {}
    derived = observation.get("derived") if isinstance(observation.get("derived"), dict) else {}
    pack_id, role = _task_pack(observation)
    record: dict[str, Any] = {
        "schema_version": "ael.run-record/0.1",
        "object_type": "run_record",
        "run_id": _run_id(cell_id),
        "study_ref": _artifact_ref(
            output_path,
            manifest_path,
            study_id=freeze["study_id"],
            revision=freeze["study_revision"],
        ),
        "condition_id": observation["condition_id"],
        "task": {
            "task_pack_id": pack_id,
            "task_id": observation["task_id"],
            "stratum": observation["stratum"],
            "role": role,
        },
        "repeat_index": observation["repeat_index"],
        "status": public_status,
        "runtime": {
            "harness": {
                "name": freeze["runtime"]["harness"],
                "version": freeze["runtime"]["harness_version"],
            },
            "model": {
                "provider": "OpenAI",
                "model_id": freeze["runtime"]["model"],
                "effort": freeze["runtime"]["reasoning_effort"],
                "immutable_revision_exposed": False,
            },
            "sandbox": "rootless-style Docker isolation with read-only fixture and proxy-only egress",
            "environment": {
                "ephemeral": True,
                "identity_available": True,
                "digest": freeze["runtime"]["runner_image_id"].removeprefix("sha256:"),
            },
            "tool_policy_sha256": freeze["prompts"][str(observation["condition_id"])]["sha256"],
            "context_sha256": freeze["private_pack"]["sha256"],
        },
        "usage": {
            "input_tokens": int(usage.get("input_tokens", 0)),
            "cached_input_tokens": int(usage.get("cached_input_tokens", 0)),
            "output_tokens": int(usage.get("output_tokens", 0)),
            "reasoning_output_tokens": int(usage.get("reasoning_output_tokens", 0)),
            "wall_time_ms": int(usage.get("wall_time_ms", 0)),
        },
        "outputs": [],
        "effects": [
            {
                "effect_type": "completion_declaration",
                "target": "terminal completion state",
                "outcome": "observed" if status == "valid" else "unknown",
                "evidence_refs": [
                    _private_ref(
                        f"urn:kizz:ael:private-observation:completion-integrity:{cell_id}",
                        observations_sha256,
                    )
                ],
            },
            {
                "effect_type": "accepted_final_state",
                "target": "frozen owner acceptance predicates",
                "outcome": (
                    "observed"
                    if derived.get("accepted_final_state") is True
                    else "not_observed"
                    if derived.get("accepted_final_state") is False
                    else "unknown"
                ),
                "evidence_refs": [
                    _private_ref(
                        f"urn:kizz:ael:private-evaluation:completion-integrity:{cell_id}",
                        str(observation.get("private_refs", {}).get("score_sha256", "0" * 64)),
                    )
                ],
            },
        ],
        "event_summary": {
            "captured": int(observation.get("event_count", 0)) > 0,
            "event_count": int(observation.get("event_count", 0)),
            "authenticated_actor_ids": [],
            "limitations": [
                "The hosted event stream exposed usage and terminal events, not an immutable model revision."
            ],
        },
        "integrity_issues": list(observation.get("invalid_reasons", [])),
        "source_refs": [
            _private_ref(
                f"urn:kizz:ael:private-observations:completion-integrity:{cell_id}",
                observations_sha256,
            ),
            _artifact_ref(output_path, freeze_path),
        ],
    }
    candidate_digest = observation.get("private_refs", {}).get("candidate_tree_sha256")
    if isinstance(candidate_digest, str) and candidate_digest != "0" * 64:
        record["outputs"].append(
            _private_ref(
                f"urn:kizz:ael:private-candidate:completion-integrity:{cell_id}",
                candidate_digest,
            )
        )
    if public_status != "valid":
        reasons = observation.get("invalid_reasons") or ["cell was not submitted"]
        record["invalid_reason"] = "; ".join(str(reason) for reason in reasons)
    return record


def _measurement(
    observation: Mapping[str, Any],
    metric: str,
    value: object,
    kind: str,
    direction: str,
    unit: str,
    run_path: Path,
    measurement_path: Path,
) -> dict[str, Any]:
    cell_id = str(observation["cell_id"])
    return {
        "measurement_id": f"{metric}:{cell_id}",
        "kind": kind,
        "metric": metric,
        "value": value,
        "unit": unit,
        "direction": direction,
        "run_ids": [_run_id(cell_id)],
        "condition_id": observation["condition_id"],
        "task_id": observation["task_id"],
        "stratum": observation["stratum"],
        "evaluator": {
            "evaluator_id": "kizz-ael-maintainer-completion-integrity-oracle",
            "kind": "deterministic",
            "blinded": True,
        },
        "evidence_refs": [_artifact_ref(measurement_path, run_path)],
    }


def _decision_projection(effect: Mapping[str, Any]) -> tuple[str, str, str]:
    disposition = effect["disposition"]
    if disposition == "enable_default":
        return (
            "adopt",
            "The exact prompt policy met every frozen effectiveness and anti-abstention gate.",
            "supported",
        )
    if disposition == "route_selectively":
        mechanisms = ", ".join(effect["eligible_mechanisms"])
        return (
            "narrow",
            f"The exact policy is supported only for the frozen eligible mechanisms: {mechanisms}.",
            "bounded",
        )
    if disposition == "reject_exact_policy":
        return (
            "reject",
            "The exact policy failed the frozen effect or anti-abstention rule and is rejected.",
            "contradicted",
        )
    return (
        "inconclusive",
        "The study completed but the exact policy did not cross a frozen action threshold.",
        "unresolved",
    )


def materialize(args: argparse.Namespace) -> None:
    if not GIT_SHA.fullmatch(args.preregistration_sha):
        raise SandboxError("preregistration SHA must be 40 lowercase hexadecimal characters")
    output = args.output.absolute()
    if output.exists() and any(output.iterdir()):
        raise SandboxError("Completion Integrity materializer output must be new or empty")
    output.mkdir(parents=True, exist_ok=True)
    freeze_path = args.freeze.resolve()
    observations_path = args.observations.resolve()
    freeze = load_json_object(freeze_path)
    observations_document = load_json_object(observations_path)
    if freeze.get("schema_version") != "ael.completion-integrity-freeze/0.1-pilot":
        raise SandboxError("unsupported Completion Integrity freeze")
    observed_code = {
        "policy": sha256_path(POLICY_PATH),
        "runner": sha256_path(RUNNER_PATH),
        "support": sha256_path(SUPPORT_PATH),
        "codex_runner": sha256_path(CODEX_RUNNER_PATH),
        "sandbox": sha256_path(SANDBOX_PATH),
        "prospective_study": sha256_path(PROSPECTIVE_PATH),
        "materializer": sha256_path(MATERIALIZER_PATH),
        "audit": sha256_path(AUDIT_PATH),
        "validation": sha256_path(VALIDATION_PATH),
        "contract_schemas": tree_sha256(SCHEMAS_PATH),
    }
    if freeze.get("code_hashes") != observed_code:
        raise SandboxError("freeze-bound Completion Integrity code has drifted")
    if observations_document.get("freeze_sha256") != sha256_path(freeze_path):
        raise SandboxError("private observations do not bind the supplied freeze")
    manifest_path = _repo_path(freeze["refs"]["study_manifest"], "study manifest")
    manifest = load_json_object(manifest_path)
    concept_uri = manifest.get("concept_ref", {}).get("uri")
    if not isinstance(concept_uri, str):
        raise SandboxError("study manifest lacks a concept reference")
    concept_path = (manifest_path.parent / concept_uri).resolve()
    if concept_path.is_symlink() or not concept_path.is_file():
        raise SandboxError("study concept is missing or unsafe")
    if manifest["concept_ref"].get("sha256") != sha256_path(concept_path):
        raise SandboxError("study concept hash mismatch")

    effect = decide_effect(freeze, observations_document)
    observations_sha = sha256_path(observations_path)
    effect_document = {
        **effect,
        "freeze_ref": _artifact_ref(output / "effect-decision.json", freeze_path),
        "observations_ref": _private_ref(
            "urn:kizz:ael:private-observations:completion-integrity:v1", observations_sha
        ),
    }
    effect_path = output / "effect-decision.json"
    write_json_atomic(effect_path, effect_document)

    run_refs: list[dict[str, object]] = []
    run_paths: dict[str, Path] = {}
    for observation in observations_document["observations"]:
        filename = f"{observation['cell_id']}.json"
        run_path = output / "runs" / filename
        record = _run_record(
            observation,
            freeze,
            manifest_path,
            freeze_path,
            observations_sha,
            run_path,
        )
        write_json_atomic(run_path, record)
        run_paths[str(observation["cell_id"])] = run_path
        run_refs.append(
            _artifact_ref(
                output / "evidence-receipt.json",
                run_path,
                run_id=record["run_id"],
            )
        )

    measurement_path = output / "measurement-set.json"
    measurements: list[dict[str, Any]] = []
    boolean_metrics = (
        ("accepted_final_state", "higher_better"),
        ("false_completion", "lower_better"),
        ("false_noncompletion", "lower_better"),
        ("substantiated_completion", "higher_better"),
        ("indeterminate_declaration", "lower_better"),
        ("regression", "lower_better"),
        ("critical_failure", "lower_better"),
    )
    for observation in observations_document["observations"]:
        derived = observation.get("derived") or {}
        run_path = run_paths[str(observation["cell_id"])]
        for metric, direction in boolean_metrics:
            measurements.append(
                _measurement(
                    observation,
                    metric,
                    derived.get(metric),
                    "outcome",
                    direction,
                    "boolean",
                    run_path,
                    measurement_path,
                )
            )
        measurements.append(
            _measurement(
                observation,
                "declaration_state",
                derived.get("declaration_state"),
                "process",
                "descriptive",
                "state",
                run_path,
                measurement_path,
            )
        )
        usage = observation.get("usage") or {}
        for metric, unit in (("generated_tokens", "tokens"), ("wall_time_ms", "milliseconds")):
            measurements.append(
                _measurement(
                    observation,
                    metric,
                    usage.get(metric, 0),
                    "cost",
                    "lower_better",
                    unit,
                    run_path,
                    measurement_path,
                )
            )
    core_run_ids = [
        _run_id(str(row["cell_id"]))
        for row in observations_document["observations"]
        if row["phase"] == "core"
    ]
    aggregate_evidence = [
        _artifact_ref(measurement_path, run_paths[str(row["cell_id"])])
        for row in observations_document["observations"]
        if row["phase"] == "core"
    ]
    reduction = effect.get("primary", {}).get("reduction") if effect.get("primary") else None
    aggregate: dict[str, Any] = {
        "measurement_id": "false_completion_risk_reduction:core",
        "kind": "aggregate",
        "metric": "false_completion_risk_reduction",
        "value": reduction,
        "unit": "risk_difference",
        "direction": "higher_better",
        "run_ids": core_run_ids,
        "evaluator": {
            "evaluator_id": "ael.completion-integrity.decide-effect/0.1-pilot",
            "kind": "deterministic",
            "blinded": False,
        },
        "evidence_refs": aggregate_evidence,
    }
    if effect.get("primary"):
        uncertainty = effect["primary"]["uncertainty"]
        aggregate["uncertainty"] = {
            "method": uncertainty["method"],
            "level": uncertainty["confidence_level"],
            "lower": uncertainty["lower"],
            "upper": uncertainty["upper"],
        }
    measurements.append(aggregate)

    measurement_set = {
        "schema_version": "ael.measurement-set/0.1",
        "object_type": "measurement_set",
        "measurement_set_id": "kizz:ael:measurements:completion-integrity:prompt-policy-v1",
        "study_ref": _artifact_ref(
            measurement_path,
            manifest_path,
            study_id=freeze["study_id"],
            revision=freeze["study_revision"],
        ),
        "measurements": measurements,
        "critical_failures": [
            {
                "failure_id": "treatment-critical-failure",
                "severity": "critical",
                "observed": bool(
                    effect.get("primary", {})
                    and effect["primary"]["rates"]["treatment_critical_failure"] > 0
                ),
                "description": "At least one treatment cell triggered a frozen critical-harm predicate.",
                "run_ids": [
                    _run_id(str(row["cell_id"]))
                    for row in observations_document["observations"]
                    if row["condition_id"] == "T1"
                    and (row.get("derived") or {}).get("critical_failure") is True
                ],
                "evidence_refs": [_artifact_ref(measurement_path, effect_path)],
            }
        ],
        "limitations": [
            "The task population contains eight maintainer-authored small Python repositories and does not represent software engineering in general.",
            "Private task, evaluator, raw event, and candidate bytes are represented by opaque hashes.",
            "Repeated cells estimate within-task stochastic reliability; the independent task count remains eight.",
        ],
        "source_refs": [
            _private_ref(
                "urn:kizz:ael:private-observations:completion-integrity:v1",
                observations_sha,
            ),
            _artifact_ref(measurement_path, effect_path),
        ],
    }
    write_json_atomic(measurement_path, measurement_set)

    public_disposition, summary, claim_status = _decision_projection(effect)
    receipt_path = output / "evidence-receipt.json"
    receipt = {
        "schema_version": "ael.evidence-receipt/0.1",
        "object_type": "evidence_receipt",
        "receipt_id": "kizz:ael:receipt:completion-integrity:prompt-policy-v1",
        "generated_at": args.generated_at,
        "concept_ref": _artifact_ref(
            receipt_path,
            concept_path,
            concept_id=manifest["concept_ref"]["concept_id"],
            revision=manifest["concept_ref"]["revision"],
        ),
        "study_ref": _artifact_ref(
            receipt_path,
            manifest_path,
            study_id=freeze["study_id"],
            revision=freeze["study_revision"],
        ),
        "run_record_refs": run_refs,
        "measurement_set_ref": _artifact_ref(
            receipt_path,
            measurement_path,
            measurement_set_id=measurement_set["measurement_set_id"],
        ),
        "evidence_level": (
            "controlled_effect_observed"
            if effect["effect_result"] != "protocol_invalid"
            else "runtime_conformant"
        ),
        "reproducibility": "not_rerunnable",
        "independence": {
            "label": "maintainer_evaluated",
            "role_overlaps": [
                "Kizz designed the prompt policy, authored the synthetic tasks and evaluator, operated the runner, and owns the decision."
            ],
            "disclosure": "This is a preregistered maintainer study with deterministic recomputation, not independent replication.",
        },
        "decision": {
            "disposition": public_disposition,
            "summary": summary,
            "scope": [
                "the exact eight-task Completion Integrity v1 private pack",
                "the exact completion-policy-v1 prompt segment",
                f"Codex CLI {freeze['runtime']['harness_version']} with {freeze['runtime']['model']} at {freeze['runtime']['reasoning_effort']} effort",
                f"Git artifact-ordering anchor {args.preregistration_sha}",
            ],
            "reversal_trigger": "Re-evaluate after any prompt, task, evaluator, model, CLI, image, budget, schedule, decision rule, or provider-behavior change.",
        },
        "evaluated_claims": [
            {
                "claim_id": "AEL-CI9-01",
                "statement": "The exact prompt-only Completion Integrity policy reduced false completion enough to satisfy its frozen owner-action rule on the admitted task population and stack.",
                "status": claim_status,
                "claim_level": "factor_causal",
                "scope": ["exact frozen eight-task controlled-factor study"],
                "evidence_refs": ["false_completion_risk_reduction:core"],
                "falsifier": "Frozen-rule recomputation, a retained cell, or the anti-abstention guardrails contradict the published disposition.",
            },
            {
                "claim_id": "AEL-CI9-02",
                "statement": "The public decision is bound to a zero-scored-call freeze, an append-only attempt policy, and retained normalized observations.",
                "status": "supported",
                "claim_level": "workflow",
                "scope": ["repository artifacts and retained private evidence hashes"],
                "evidence_refs": ["effect-decision.json"],
                "falsifier": "Git ordering, attempt records, or private evidence shows a pre-freeze scored call, silent retry, or binding drift.",
            },
        ],
        "unsupported_inferences": [
            "Completion prompts work in general.",
            "The policy improves the underlying model or transfers to other tasks, models, CLIs, repositories, or organizations.",
            "A maintainer-authored deterministic evaluator is independent verification.",
            "Git ancestry independently timestamps private hosted-model calls.",
            "Token or latency differences in this pilot are stable economic effects.",
        ],
        "limitations": [
            "Only eight independent maintainer-authored tasks were scored; confirmation cells are held out from design calibration but not independently authored.",
            "The hosted provider exposed a model identifier but no immutable model revision.",
            "The public repository withholds exact tasks, evaluators, candidate workspaces, events, and reusable authentication.",
            "The task-cluster interval describes this frozen task population and is not a population-level confidence guarantee.",
        ],
        "invalidation_triggers": [
            "Any freeze-bound byte, runtime image, private-pack hash, or public effect value differs from the audited artifact.",
            "A submitted or ambiguous attempt was retried or omitted from the normalized observation set.",
            "Private task, evaluator, event, credential, or canary bytes cross the public boundary.",
        ],
        "state": {
            "experiment": "completed_under_frozen_rule",
            "artifact": "materialized_and_audited_locally",
            "repository": "prepared_for_exact_commit",
            "publication": "prepared_not_published",
            "deployment": "not_applicable",
            "outcome": "owner_policy_decision_only; no downstream outcome observed",
        },
        "publication_state": "public_ready",
        "generator": {"name": "ael-completion-integrity-materializer", "version": "0.1"},
    }
    write_json_atomic(receipt_path, receipt)

    adoption_path = output / "adoption-decision.pilot.json"
    adoption = {
        "schema_version": "ael.completion-integrity-adoption/0.1-pilot",
        "adoption_id": "kizz:ael:adoption:completion-integrity:prompt-policy-v1",
        "recorded_at": args.generated_at,
        "owner_id": "kizz-ael-maintainer",
        "effect_ref": _artifact_ref(adoption_path, effect_path),
        "evidence_receipt_ref": _artifact_ref(adoption_path, receipt_path),
        "study_disposition": effect["disposition"],
        "public_disposition": public_disposition,
        "eligible_mechanisms": effect["eligible_mechanisms"],
        "state": "recorded_not_deployed",
        "scope": "Exact prompt policy on the frozen Kizz Codex study surface only.",
        "reversal_trigger": receipt["decision"]["reversal_trigger"],
    }
    write_json_atomic(adoption_path, adoption)

    freeze_ref_path = output / "freeze-ref.json"
    write_json_atomic(
        freeze_ref_path,
        {
            "schema_version": "ael.completion-integrity-result-bindings/0.1-pilot",
            "freeze_sha256": sha256_path(freeze_path),
            "observations_sha256": observations_sha,
            "effect_decision_sha256": sha256_path(effect_path),
            "measurement_set_sha256": sha256_path(measurement_path),
            "evidence_receipt_sha256": sha256_path(receipt_path),
            "adoption_decision_sha256": sha256_path(adoption_path),
            "preregistration_sha": args.preregistration_sha,
        },
    )

    documents, issues = validate(
        [concept_path, manifest_path, *run_paths.values(), measurement_path, receipt_path]
    )
    if issues:
        raise SandboxError(f"materialized Contract v0 graph is invalid: {issues[0]}")
    if len(documents) != 56:
        raise SandboxError("materialized Contract v0 graph has an unexpected document count")
    print(
        f"materialized Completion Integrity result: {len(run_paths)} runs; "
        f"effect={effect['effect_result']} disposition={effect['disposition']}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", required=True, type=Path)
    parser.add_argument("--observations", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--generated-at", required=True)
    parser.add_argument("--preregistration-sha", required=True)
    args = parser.parse_args()
    materialize(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
