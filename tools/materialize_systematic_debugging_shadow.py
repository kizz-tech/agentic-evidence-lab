from __future__ import annotations

import argparse
import json
import re
import shutil
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import ael.systematic_debugging_shadow as debugging_shadow
from ael import __version__
from ael.prospective_study import (
    ACTION_RECORD_SCHEMA_VERSION,
    ADOPTION_DECISION_SCHEMA_VERSION,
    FOLLOW_UP_SCHEMA_VERSION,
    load_json_object,
    sha256_path,
    validate_admission,
    validate_freeze,
)
from ael.sandbox import SandboxError
from ael.validation import validate

ROOT = Path(__file__).resolve().parents[1]
SEASON_ROOT = ROOT / "studies" / "agent-skills-season-1"
CONCEPT_PATH = SEASON_ROOT / "concept.json"
MANIFEST_PATH = SEASON_ROOT / "manifests" / "systematic-debugging-real-shadow.study-manifest.json"
STUDY_ID = "kizz:ael:study:agent-skills-season-1:systematic-debugging-real-shadow"
CONCEPT_ID = "kizz:ael:concept:public-agent-skill-effectiveness"
REVISION = "systematic-debugging-real-shadow-v1"
GIT_SHA = re.compile(r"^[a-f0-9]{40}$")


def write_json(path: Path, document: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, indent=2, sort_keys=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def private_ref(uri: str, digest: str) -> dict[str, object]:
    return {"uri": uri, "sha256": digest, "revision": REVISION, "visibility": "private"}


def study_ref(uri: str) -> dict[str, object]:
    return {
        "study_id": STUDY_ID,
        "revision": 1,
        "uri": uri,
        "sha256": sha256_path(MANIFEST_PATH),
        "visibility": "public",
    }


def run_id(observation: Mapping[str, Any]) -> str:
    return (
        "kizz:ael:run:agent-skills-season-1:systematic-debugging-real-shadow:"
        f"{observation['task_id']}:{observation['condition_id']}:R01"
    )


def build_run(observation: Mapping[str, Any], freeze: Mapping[str, Any]) -> dict[str, object]:
    identifier = run_id(observation)
    private_prefix = f"urn:kizz:ael:private-run:debug-shadow:{observation['observation_id']}"
    refs = observation["private_refs"]
    record: dict[str, object] = {
        "schema_version": "ael.run-record/0.1",
        "object_type": "run_record",
        "run_id": identifier,
        "study_ref": study_ref(
            "../../../manifests/systematic-debugging-real-shadow.study-manifest.json"
        ),
        "condition_id": observation["condition_id"],
        "task": {
            "task_pack_id": "systematic-debugging-real-shadow-v1-screening",
            "task_id": observation["task_id"],
            "stratum": observation["stratum"],
            "role": "screening",
        },
        "repeat_index": 1,
        "status": observation["status"],
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
            "sandbox": "restricted outer Docker; Codex inner sandbox disabled",
            "environment": {
                "ephemeral": True,
                "identity_available": True,
                "digest": str(freeze["runtime"]["runner_image_id"]).removeprefix("sha256:"),
            },
            "context_sha256": refs["candidate_tree_sha256"],
        },
        "usage": {
            "input_tokens": observation["usage"]["input_tokens"],
            "cached_input_tokens": observation["usage"]["cached_input_tokens"],
            "output_tokens": observation["usage"]["output_tokens"],
            "reasoning_output_tokens": observation["usage"]["reasoning_output_tokens"],
            "wall_time_ms": observation["usage"]["wall_time_ms"],
        },
        "outputs": [private_ref(private_prefix + ":candidate", refs["candidate_tree_sha256"])],
        "effects": [],
        "event_summary": {
            "captured": True,
            "event_count": observation["event_count"],
            "authenticated_actor_ids": [],
            "limitations": [
                "The provider did not expose an immutable model revision.",
                "Raw task content, events, candidates, and evaluator outputs remain private.",
                "Operator-recorded timestamps are chronology metadata, not trusted timestamps.",
            ],
        },
        "integrity_issues": [
            "The owner accepted use of reusable local Codex authentication for this exact reviewed skill and sanitized private pack; persisted output was scanned, while encrypted provider traffic was not inspected."
        ],
        "source_refs": [
            private_ref(private_prefix + ":events", refs["events_sha256"]),
            private_ref(private_prefix + ":invocation", refs["invocation_sha256"]),
            private_ref(private_prefix + ":score", refs["score_sha256"]),
        ],
    }
    if observation["status"] == "invalid":
        record["invalid_reason"] = "; ".join(observation["invalid_reasons"])
    return record


def measurement(
    observation: Mapping[str, Any], metric: str, value: object, kind: str, direction: str
) -> dict[str, object]:
    evidence = (
        "events" if metric in {"skill_activated", "generated_tokens", "wall_time_ms"} else "score"
    )
    private_prefix = f"urn:kizz:ael:private-run:debug-shadow:{observation['observation_id']}"
    units = {
        "skill_activated": "boolean",
        "visible_tests_pass": "boolean",
        "hidden_acceptance": "boolean",
        "root_cause_invariant_pass": "boolean",
        "reference_compatible_tests": "boolean",
        "safe_change_scope": "boolean",
        "critical_failure": "boolean",
        "accepted": "boolean",
        "generated_tokens": "tokens",
        "wall_time_ms": "milliseconds",
    }
    return {
        "measurement_id": f"{metric}:{observation['task_id']}:{observation['condition_id']}:R01",
        "kind": kind,
        "metric": metric,
        "value": value,
        "unit": units[metric],
        "direction": direction,
        "run_ids": [run_id(observation)],
        "condition_id": observation["condition_id"],
        "task_id": observation["task_id"],
        "stratum": observation["stratum"],
        "evaluator": {
            "evaluator_id": "ael-debugging-shadow-v1-deterministic-evaluator",
            "kind": "deterministic",
            "blinded": True,
        },
        "evidence_refs": [
            private_ref(
                private_prefix + f":{evidence}", observation["private_refs"][f"{evidence}_sha256"]
            )
        ],
    }


def evidence_summary(effect: Mapping[str, Any]) -> tuple[str, str, str]:
    outcome = effect["effect_outcome"]
    if outcome == "bounded_favorable_signal":
        return (
            "narrow",
            "The treatment met the frozen two-of-two rule in at least one exact defect stratum with no unfavorable pair or treatment critical failure.",
            "supported",
        )
    if outcome in {
        "treatment_activation_failure",
        "treatment_critical_failure",
        "treatment_harm_signal",
    }:
        return (
            "reject",
            "The exact treatment did not satisfy the frozen safety or delivery rule on this pilot surface.",
            "contradicted",
        )
    return (
        "inconclusive",
        "The exact pilot produced mixed evidence or insufficient baseline headroom for selective routing.",
        "unresolved",
    )


def adoption_record(
    admission_path: Path,
    admission: Mapping[str, Any],
    effect_path: Path,
    effect: Mapping[str, Any],
    receipt_path: Path,
    resolved_at: str,
) -> tuple[dict[str, object], Mapping[str, Any] | None]:
    rule, resolution_status = debugging_shadow.match_owner_policy(admission, effect)
    disposition = rule["disposition"] if rule else admission["owner_action_policy"]["fallback"]
    scope = rule["scope"] if rule else "no automatic action; manual review required"
    if disposition == "route_selectively":
        scope = f"{scope}; eligible strata: {', '.join(effect['eligible_strata'])}"
    return (
        {
            "schema_version": ADOPTION_DECISION_SCHEMA_VERSION,
            "adoption_decision_id": f"{admission['case_id']}:adoption:1",
            "admission_ref": {
                "admission_id": admission["admission_id"],
                "sha256": sha256_path(admission_path),
            },
            "effect_decision_ref": {
                "effect_decision_id": effect["effect_decision_id"],
                "sha256": sha256_path(effect_path),
            },
            "evidence_receipt_ref": {
                "receipt_id": "kizz:ael:receipt:agent-skills-season-1:systematic-debugging-real-shadow-v1",
                "sha256": sha256_path(receipt_path),
            },
            "matched_rule_id": rule["rule_id"] if rule else None,
            "resolution_status": resolution_status,
            "disposition": disposition,
            "scope": scope,
            "resolved_at": resolved_at,
            "owner_id": admission["owner_action_policy"]["owner_id"],
            "candidate": admission["candidate"],
            "limitations": [
                "This is execution of a preregistered owner policy, not an automatically inferred universal product recommendation.",
                "Global installation was ineligible under the admitted policy.",
            ],
        },
        rule,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--observations", required=True, type=Path)
    parser.add_argument("--effect-decision", required=True, type=Path)
    parser.add_argument("--freeze", required=True, type=Path)
    parser.add_argument("--admission", required=True, type=Path)
    parser.add_argument("--preregistration-sha", required=True)
    parser.add_argument("--generated-at", required=True)
    parser.add_argument("--action-at", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    if not GIT_SHA.fullmatch(args.preregistration_sha):
        raise SandboxError("preregistration SHA must be 40 lowercase hexadecimal characters")
    output = args.output.absolute()
    if output.exists() and any(output.iterdir()):
        raise SandboxError("materializer output must be empty")
    output.mkdir(parents=True, exist_ok=True)
    freeze_path = args.freeze.resolve()
    admission_path = args.admission.resolve()
    observations_path = args.observations.resolve()
    effect_path = args.effect_decision.resolve()
    freeze = load_json_object(freeze_path)
    admission = load_json_object(admission_path)
    freeze_issues = validate_freeze(freeze)
    admission_issues = validate_admission(admission)
    if freeze_issues:
        raise SandboxError(f"freeze has {len(freeze_issues)} issue(s): {freeze_issues[0]}")
    if admission_issues:
        raise SandboxError(f"admission has {len(admission_issues)} issue(s): {admission_issues[0]}")
    if sha256_path(Path(__file__).resolve()) != freeze["code_hashes"]["materializer"]:
        raise SandboxError("materializer code no longer matches the freeze")
    if sha256_path(Path(debugging_shadow.__file__).resolve()) != freeze["code_hashes"]["decision"]:
        raise SandboxError("decision code no longer matches the freeze")
    if debugging_shadow.execution_code_sha256() != freeze["code_hashes"]["execution"]:
        raise SandboxError("execution code no longer matches the freeze")
    observations_document = load_json_object(observations_path)
    recorded_effect = load_json_object(effect_path)
    recomputed_effect = debugging_shadow.decide_effect(freeze_path, observations_path)
    if recorded_effect != recomputed_effect:
        raise SandboxError("effect decision does not match frozen-rule recomputation")
    observations = observations_document["observations"]

    run_refs: list[dict[str, object]] = []
    for observation in observations:
        record = build_run(observation, freeze)
        filename = f"{observation['task_id']}-{observation['condition_id']}-R01.json"
        path = output / "runs" / filename
        write_json(path, record)
        run_refs.append(
            {
                "run_id": record["run_id"],
                "uri": f"runs/{filename}",
                "sha256": sha256_path(path),
                "visibility": "public",
            }
        )

    metric_specs = [
        ("visible_tests_pass", "deterministic", "higher_better"),
        ("hidden_acceptance", "outcome", "higher_better"),
        ("root_cause_invariant_pass", "outcome", "higher_better"),
        ("reference_compatible_tests", "deterministic", "higher_better"),
        ("safe_change_scope", "deterministic", "higher_better"),
        ("critical_failure", "outcome", "lower_better"),
        ("accepted", "deterministic", "higher_better"),
        ("skill_activated", "process", "target"),
    ]
    measurements: list[dict[str, object]] = []
    for observation in observations:
        for metric, kind, direction in metric_specs:
            measurements.append(
                measurement(observation, metric, observation[metric], kind, direction)
            )
        for metric in ("generated_tokens", "wall_time_ms"):
            measurements.append(
                measurement(
                    observation, metric, observation["usage"][metric], "cost", "lower_better"
                )
            )
    measurement_set = {
        "schema_version": "ael.measurement-set/0.1",
        "object_type": "measurement_set",
        "measurement_set_id": "kizz:ael:measurements:agent-skills-season-1:systematic-debugging-real-shadow-v1",
        "study_ref": study_ref(
            "../../manifests/systematic-debugging-real-shadow.study-manifest.json"
        ),
        "measurements": measurements,
        "critical_failures": [
            {
                "failure_id": "treatment-critical-or-scope-failure",
                "severity": "critical",
                "observed": recorded_effect["counts"]["treatment_critical_failures"] > 0,
                "description": "A treatment cell violated deterministic reference compatibility or safe-change scope.",
                "run_ids": [
                    run_id(item)
                    for item in observations
                    if item["condition_id"] == "S1" and item["critical_failure"]
                ],
                "evidence_refs": [
                    private_ref(
                        "urn:kizz:ael:private-effect-decision:debug-shadow-v1",
                        sha256_path(effect_path),
                    )
                ],
            }
        ],
        "limitations": [
            "The pilot contains four maintainer-selected sanitized incidents and no untouched confirmation phase.",
            "Private task, evaluator, raw event, and candidate bytes are represented by opaque hashes.",
        ],
        "source_refs": [
            private_ref(
                "urn:kizz:ael:private-observations:debug-shadow-v1", sha256_path(observations_path)
            ),
            private_ref(
                "urn:kizz:ael:private-effect-decision:debug-shadow-v1", sha256_path(effect_path)
            ),
        ],
    }
    measurement_path = output / "measurement-set.json"
    write_json(measurement_path, measurement_set)

    disposition, summary, claim_status = evidence_summary(recorded_effect)
    receipt = {
        "schema_version": "ael.evidence-receipt/0.1",
        "object_type": "evidence_receipt",
        "receipt_id": "kizz:ael:receipt:agent-skills-season-1:systematic-debugging-real-shadow-v1",
        "generated_at": args.generated_at,
        "concept_ref": {
            "concept_id": CONCEPT_ID,
            "revision": 1,
            "uri": "../../concept.json",
            "sha256": sha256_path(CONCEPT_PATH),
            "visibility": "public",
        },
        "study_ref": study_ref(
            "../../manifests/systematic-debugging-real-shadow.study-manifest.json"
        ),
        "run_record_refs": run_refs,
        "measurement_set_ref": {
            "measurement_set_id": measurement_set["measurement_set_id"],
            "uri": "measurement-set.json",
            "sha256": sha256_path(measurement_path),
            "visibility": "public",
        },
        "evidence_level": "controlled_effect_observed",
        "reproducibility": "partially_rerunnable",
        "independence": {
            "label": "maintainer_evaluated",
            "role_overlaps": admission["role_overlaps"],
            "disclosure": "Kizz authored sanitized tasks, operated the runner, evaluated deterministic outcomes, and owns the action policy; no independent replication exists.",
        },
        "decision": {
            "disposition": disposition,
            "summary": summary,
            "scope": [
                "four exact sanitized debugging fixtures across two declared strata",
                "the exact Superpowers systematic-debugging source snapshot",
                "Codex CLI 0.146.0 with gpt-5.6-sol at xhigh effort",
                f"Git artifact-ordering anchor {args.preregistration_sha}",
            ],
            "reversal_trigger": "Re-evaluate after any task, evaluator, prompt, skill, model, CLI, image, budget, rule, or provider behavior change.",
        },
        "evaluated_claims": [
            {
                "claim_id": "AEL-DEBUG-SHADOW-01",
                "statement": "The exact skill changed root-cause-correct hidden acceptance enough to satisfy the frozen bounded routing rule on at least one admitted stratum.",
                "status": claim_status,
                "claim_level": "factor_causal",
                "scope": recorded_effect["eligible_strata"]
                or ["exact four-cell matched pilot surface"],
                "evidence_refs": [
                    f"hidden_acceptance:{item['task_id']}:{item['condition_id']}:R01"
                    for item in observations
                ],
                "falsifier": "Frozen-rule recomputation, a retained cell, or the operational follow-up contradicts the published classifications.",
            },
            {
                "claim_id": "AEL-DEBUG-SHADOW-02",
                "statement": "The recorded runner checked admission, manifest, source, pack, code, prompt, and image bindings before every recorded scored call.",
                "status": "supported",
                "claim_level": "workflow",
                "scope": ["recorded runner invocations and Git artifact ordering"],
                "evidence_refs": ["freeze-ref.json", "effect-decision.json"],
                "falsifier": "A binding differs, the freeze did not precede result artifacts, or private records show an unadmitted scored call.",
            },
        ],
        "unsupported_inferences": [
            "Systematic debugging skills work in general.",
            "This exact skill is superior across debugging tasks, models, CLIs, repositories, or teams.",
            "A four-task screening surface supports global installation or a public leaderboard rank.",
            "Git ancestry independently proves private model-call chronology.",
            "Maintainer evaluation is independent replication.",
            "Token or latency differences in eight calls are stable cost effects.",
        ],
        "limitations": [
            "Only four maintainer-selected sanitized incidents and one stochastic draw per condition were used.",
            "No untouched confirmation pack was run; the maximum owner action is reversible selective routing.",
            "Task sanitization may not preserve every causal property of the originating incidents.",
            "The provider exposed a model identifier but not an immutable model revision.",
            "Reusable local Codex authentication was process-readable under explicit owner acceptance; persisted outputs were exact-value scanned, while encrypted provider traffic was not inspected.",
            "Git proves repository artifact ordering, not absolute time of all private model calls.",
        ],
        "invalidation_triggers": [
            "Any admission, manifest, freeze, source, pack, code, prompt, image, observation, or decision hash fails",
            "A scored call is shown to predate admission or freeze",
            "A task/evaluator was tuned after observing a scored candidate",
            "Private material or authentication escaped its declared boundary",
            "Public wording exceeds the bounded screening-derived claim ceiling",
        ],
        "state": {
            "experiment": f"real-shadow effect outcome: {recorded_effect['effect_outcome']}",
            "artifact": "sanitized public Contract v0 projection; private materials represented by hashes",
            "repository": "result package prepared in the local branch",
            "publication": "prepared, not published",
            "deployment": "owner policy action recorded separately; no global installation",
            "outcome": "operational follow-up scheduled; downstream outcome not yet observed",
        },
        "publication_state": "public_ready",
        "generator": {"name": "agentic-evidence-lab", "version": __version__},
    }
    receipt_path = output / "evidence-receipt.json"
    write_json(receipt_path, receipt)
    shutil.copyfile(effect_path, output / "effect-decision.json")

    adoption, matched_rule = adoption_record(
        admission_path,
        admission,
        output / "effect-decision.json",
        recorded_effect,
        receipt_path,
        args.action_at,
    )
    adoption_path = output / "adoption-decision.pilot.json"
    write_json(adoption_path, adoption)
    routing_policy = {
        "schema_version": "ael.debugging-routing-policy/0.1-pilot",
        "policy_id": f"{admission['case_id']}:routing:1",
        "adoption_decision_ref": {
            "adoption_decision_id": adoption["adoption_decision_id"],
            "sha256": sha256_path(adoption_path),
        },
        "candidate": admission["candidate"],
        "mode": adoption["disposition"],
        "eligible_strata": recorded_effect["eligible_strata"],
        "scope": adoption["scope"],
        "default_enabled": False,
        "global_installation": False,
        "reversal_trigger": admission["follow_up_plan"]["reversal_trigger"],
    }
    routing_path = output / "routing-policy.pilot.json"
    write_json(routing_path, routing_policy)
    action = {
        "schema_version": ACTION_RECORD_SCHEMA_VERSION,
        "action_id": f"{admission['case_id']}:action:1",
        "adoption_decision_ref": {
            "adoption_decision_id": adoption["adoption_decision_id"],
            "sha256": sha256_path(adoption_path),
        },
        "action_kind": matched_rule["action_kind"] if matched_rule else "manual_review_required",
        "state": "verified" if matched_rule else "blocked",
        "target_scope": adoption["scope"],
        "actor_id": admission["roles"]["action_owner"],
        "acted_at": args.action_at,
        "owner_system_ref": {
            "uri": "routing-policy.pilot.json",
            "sha256": sha256_path(routing_path),
        },
        "limitations": [
            "This routing policy governs AEL/Kizz Codex process guidance only; it is not proof of automatic enforcement in every client.",
            "No skill was globally installed by this action.",
        ],
    }
    action_path = output / "action-record.pilot.json"
    write_json(action_path, action)
    follow_up = {
        "schema_version": FOLLOW_UP_SCHEMA_VERSION,
        "follow_up_id": f"{admission['case_id']}:follow-up:1",
        "action_ref": {"action_id": action["action_id"], "sha256": sha256_path(action_path)},
        "owner_id": admission["follow_up_plan"]["owner_id"],
        "status": "scheduled",
        "planned_due_at": admission["follow_up_plan"]["due_at"],
        "observation_window": admission["follow_up_plan"]["window"],
        "signals": admission["follow_up_plan"]["signals"],
        "conclusion": "not_due",
        "observations": [],
        "limitations": [
            "This record schedules a future owner observation; it is not downstream outcome evidence.",
            "If no eligible natural cases occur, the follow-up must report not_observed rather than infer no effect.",
        ],
        "reversal_trigger": admission["follow_up_plan"]["reversal_trigger"],
    }
    write_json(output / "outcome-follow-up.pilot.json", follow_up)
    write_json(
        output / "freeze-ref.json",
        {
            "freeze_id": freeze["freeze_id"],
            "freeze_sha256": sha256_path(freeze_path),
            "admission_sha256": sha256_path(admission_path),
            "manifest_sha256": sha256_path(MANIFEST_PATH),
            "private_pack_sha256": freeze["private_pack"]["sha256"],
            "preregistration_sha": args.preregistration_sha,
            "effect_decision_sha256": sha256_path(output / "effect-decision.json"),
            "receipt_sha256": sha256_path(receipt_path),
            "adoption_decision_sha256": sha256_path(adoption_path),
            "action_record_sha256": sha256_path(action_path),
        },
    )
    documents, validation_issues = validate(
        [
            CONCEPT_PATH,
            MANIFEST_PATH,
            *sorted((output / "runs").glob("*.json")),
            measurement_path,
            receipt_path,
        ]
    )
    if validation_issues:
        raise SandboxError(f"materialized Contract v0 bundle is invalid: {validation_issues[0]}")
    print(
        json.dumps(
            {
                "contract_documents": len(documents),
                "runs": len(observations),
                "measurements": len(measurements),
                "effect_outcome": recorded_effect["effect_outcome"],
                "owner_disposition": adoption["disposition"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
