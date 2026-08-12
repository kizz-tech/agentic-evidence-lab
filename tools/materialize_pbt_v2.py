from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

import ael.pbt_pilot as pbt_pilot
from ael import __version__
from ael.pbt_pilot import decide_pbt_stage
from ael.sandbox import SandboxError
from ael.study_freeze import load_json_object, validate_freeze_bundle
from ael.validation import sha256_path

ROOT = Path(__file__).resolve().parents[1]
SEASON_ROOT = ROOT / "studies" / "agent-skills-season-1"
CONCEPT_PATH = SEASON_ROOT / "concept.json"
MANIFEST_PATH = SEASON_ROOT / "manifests" / "property-based-testing-v2.study-manifest.json"
STUDY_ID = "kizz:ael:study:agent-skills-season-1:property-based-testing"
CONCEPT_ID = "kizz:ael:concept:public-agent-skill-effectiveness"
REVISION = "property-based-testing-v2-pilot-1"
RUNNER_IMAGE_ID = "f5ebad21373b16799a4bb0189d917856280cca8394c25967c95d612b6b61ac08"
GIT_SHA = re.compile(r"^[a-f0-9]{40}$")


def write_json(path: Path, document: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def private_ref(uri: str, digest: str) -> dict[str, object]:
    return {"uri": uri, "sha256": digest, "revision": REVISION, "visibility": "private"}


def study_ref(uri: str) -> dict[str, object]:
    return {
        "study_id": STUDY_ID,
        "revision": 2,
        "uri": uri,
        "sha256": sha256_path(MANIFEST_PATH),
        "visibility": "public",
    }


def run_id(observation: dict[str, object]) -> str:
    return (
        "kizz:ael:run:agent-skills-season-1:property-based-testing-v2:"
        f"{observation['task_id']}:{observation['condition_id']}:"
        f"R{int(observation['repeat_index']):02d}"
    )


def build_run(observation: dict[str, object], phase: str) -> dict[str, object]:
    private_prefix = f"urn:kizz:ael:private-run:pbt-v2:{observation['observation_id']}"
    refs = observation["private_refs"]
    record: dict[str, object] = {
        "schema_version": "ael.run-record/0.1",
        "object_type": "run_record",
        "run_id": run_id(observation),
        "study_ref": study_ref("../../../manifests/property-based-testing-v2.study-manifest.json"),
        "condition_id": observation["condition_id"],
        "task": {
            "task_pack_id": f"property-based-testing-v2-{phase}",
            "task_id": observation["task_id"],
            "stratum": observation["stratum"],
            "role": "holdout" if phase == "confirmation" else "screening",
        },
        "repeat_index": observation["repeat_index"],
        "status": observation["status"],
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
                "digest": RUNNER_IMAGE_ID,
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
                "Raw tasks, events, candidates, and evaluator outputs remain private and are represented by hashes.",
                "Encrypted provider traffic was not inspected.",
            ],
        },
        "integrity_issues": [
            "The maintainer-approved reusable ChatGPT credential was readable by the Codex process; only frozen maintainer-controlled inputs were used."
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
    observation: dict[str, object],
    metric: str,
    value: object,
    kind: str,
    direction: str,
    evidence: str,
    unit: str = "boolean",
) -> dict[str, object]:
    private_prefix = f"urn:kizz:ael:private-run:pbt-v2:{observation['observation_id']}"
    return {
        "measurement_id": (
            f"{metric}:{observation['task_id']}:{observation['condition_id']}:"
            f"R{int(observation['repeat_index']):02d}"
        ),
        "kind": kind,
        "metric": metric,
        "value": value,
        "unit": unit,
        "direction": direction,
        "run_ids": [run_id(observation)],
        "condition_id": observation["condition_id"],
        "task_id": observation["task_id"],
        "stratum": observation["stratum"],
        "evaluator": {
            "evaluator_id": "ael-pbt-v2-deterministic-hidden-evaluator",
            "kind": "deterministic",
            "blinded": True,
        },
        "evidence_refs": [
            private_ref(
                private_prefix + f":{evidence}",
                observation["private_refs"][f"{evidence}_sha256"],
            )
        ],
    }


def verified_decision(
    freeze_path: Path, observations_path: Path, decision_path: Path, stage: str
) -> dict[str, object]:
    recorded = load_json_object(decision_path)
    recomputed = decide_pbt_stage(freeze_path, observations_path, stage)
    if recorded != recomputed:
        raise SandboxError(f"{stage} decision does not match frozen-rule recomputation")
    return recorded


def decision_summary(decision: dict[str, object]) -> tuple[str, str, str]:
    outcome = decision["outcome"]
    if outcome == "confirmed_S1":
        return (
            "adopt",
            "S1 met the frozen hidden-acceptance rule in screening and untouched confirmation on this pilot surface.",
            "supported",
        )
    if str(outcome).startswith("reject_all") or outcome == "not_confirmed":
        return (
            "reject",
            "S1 did not meet the frozen selection or confirmation rule on this pilot surface.",
            "contradicted",
        )
    return (
        "inconclusive",
        f"The frozen pilot terminated as {outcome}; no adoption decision is supported.",
        "unresolved",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--screening-observations", required=True, type=Path)
    parser.add_argument("--screening-decision", required=True, type=Path)
    parser.add_argument("--continuation-observations", type=Path)
    parser.add_argument("--continuation-decision", type=Path)
    parser.add_argument("--confirmation-observations", type=Path)
    parser.add_argument("--confirmation-decision", type=Path)
    parser.add_argument("--freeze", required=True, type=Path)
    parser.add_argument("--preregistration-sha", required=True)
    parser.add_argument("--generated-at", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    freeze_path = args.freeze.resolve()
    freeze = load_json_object(freeze_path)
    issues = validate_freeze_bundle(freeze)
    if issues:
        raise SandboxError(f"freeze bundle has {len(issues)} issue(s)")
    if sha256_path(Path(__file__).resolve()) != freeze["analysis_code_sha256"]:
        raise SandboxError("materializer code no longer matches the frozen hash")
    if sha256_path(Path(pbt_pilot.__file__).resolve()) != freeze["decision_code_sha256"]:
        raise SandboxError("decision code no longer matches the frozen hash")
    if pbt_pilot.execution_code_sha256() != freeze["execution_code_sha256"]:
        raise SandboxError("execution dependencies no longer match the frozen hash")
    if not GIT_SHA.fullmatch(args.preregistration_sha):
        raise SandboxError("preregistration SHA must be 40 lowercase hexadecimal characters")
    if bool(args.continuation_observations) != bool(args.continuation_decision):
        raise SandboxError("continuation observations and decision must be supplied together")
    if bool(args.confirmation_observations) != bool(args.confirmation_decision):
        raise SandboxError("confirmation observations and decision must be supplied together")

    screening_path = args.screening_observations.resolve()
    screening = load_json_object(screening_path)
    screening_recorded = load_json_object(args.screening_decision.resolve())
    screening_stage = screening_recorded.get("stage")
    if screening_stage not in {"continuation", "selection"}:
        raise SandboxError("screening decision must be a continuation or selection record")
    screening_decision = verified_decision(
        freeze_path, screening_path, args.screening_decision.resolve(), screening_stage
    )
    continuation_decision: dict[str, object] | None = None
    if args.continuation_observations and args.continuation_decision:
        continuation_decision = verified_decision(
            freeze_path,
            args.continuation_observations.resolve(),
            args.continuation_decision.resolve(),
            "continuation",
        )
        if continuation_decision["outcome"] != "continue":
            raise SandboxError("a continued screening chain requires outcome continue")
    if screening_stage == "selection" and continuation_decision is None:
        raise SandboxError("selection evidence requires its frozen continuation decision")
    if screening_stage == "continuation" and screening_decision["outcome"] == "continue":
        raise SandboxError("a continue outcome is not a terminal screening decision")

    observation_groups = [("screening", screening["observations"])]
    confirmation_decision: dict[str, object] | None = None
    if args.confirmation_observations and args.confirmation_decision:
        confirmation_path = args.confirmation_observations.resolve()
        confirmation = load_json_object(confirmation_path)
        observation_groups.append(("confirmation", confirmation["observations"]))
        confirmation_decision = verified_decision(
            freeze_path,
            confirmation_path,
            args.confirmation_decision.resolve(),
            "confirmation",
        )
        if screening_decision["outcome"] != "select_S1":
            raise SandboxError("confirmation requires a successful screening selection")
    elif screening_decision["outcome"] == "select_S1":
        raise SandboxError("a selected treatment requires confirmation before materialization")
    terminal_decision = confirmation_decision or screening_decision

    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise SandboxError("materializer output must be empty")
    output.mkdir(parents=True, exist_ok=True)
    all_observations: list[tuple[str, dict[str, object]]] = []
    run_refs: list[dict[str, object]] = []
    for phase, observations in observation_groups:
        for observation in observations:
            record = build_run(observation, phase)
            filename = (
                f"{observation['task_id']}-{observation['condition_id']}-"
                f"R{int(observation['repeat_index']):02d}.json"
            )
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
            all_observations.append((phase, observation))

    measurements: list[dict[str, object]] = []
    metric_specs = [
        ("hidden_acceptance", "outcome", "higher_better", "score", "boolean"),
        ("candidate_tests_pass", "deterministic", "higher_better", "score", "boolean"),
        ("reference_compatible_tests", "deterministic", "higher_better", "score", "boolean"),
        ("invalid_property", "outcome", "lower_better", "score", "boolean"),
        ("flaky", "outcome", "lower_better", "score", "boolean"),
        ("edge_test_added", "process", "descriptive", "score", "boolean"),
        ("critical_failure", "outcome", "lower_better", "score", "boolean"),
        ("accepted", "deterministic", "higher_better", "score", "boolean"),
        ("skill_activated", "process", "target", "events", "boolean"),
    ]
    for _phase, observation in all_observations:
        for metric, kind, direction, evidence, unit in metric_specs:
            if observation["status"] != "valid" and kind in {"deterministic", "outcome"}:
                continue
            measurements.append(
                measurement(
                    observation, metric, observation[metric], kind, direction, evidence, unit
                )
            )
        for metric, unit in (("generated_tokens", "tokens"), ("wall_time_ms", "milliseconds")):
            measurements.append(
                measurement(
                    observation,
                    metric,
                    observation["usage"][metric],
                    "cost",
                    "lower_better",
                    "events",
                    unit,
                )
            )

    terminal_decision_path = (
        args.confirmation_decision.resolve()
        if args.confirmation_decision
        else args.screening_decision.resolve()
    )
    measurement_set = {
        "schema_version": "ael.measurement-set/0.1",
        "object_type": "measurement_set",
        "measurement_set_id": "kizz:ael:measurements:agent-skills-season-1:pbt-v2",
        "study_ref": study_ref("../../manifests/property-based-testing-v2.study-manifest.json"),
        "measurements": measurements,
        "critical_failures": [
            {
                "failure_id": "treatment-invalid-or-flaky-property",
                "severity": "critical",
                "observed": any(
                    item["status"] == "valid"
                    and item["condition_id"] == "S1"
                    and item["critical_failure"]
                    for _phase, item in all_observations
                ),
                "description": "A treatment cell added a property incompatible with the reference repair or produced seed-dependent test outcomes.",
                "run_ids": [
                    run_id(item)
                    for _phase, item in all_observations
                    if item["status"] == "valid"
                    and item["condition_id"] == "S1"
                    and item["critical_failure"]
                ],
                "evidence_refs": [
                    private_ref(
                        "urn:kizz:ael:private-decision:pbt-v2",
                        sha256_path(terminal_decision_path),
                    )
                ],
            }
        ],
        "limitations": [
            "The pilot covers two exact defect families and is not representative of software work in general.",
            "Private task and evaluator content is withheld; public artifacts expose opaque hashes only.",
        ],
        "source_refs": [
            private_ref(
                "urn:kizz:ael:private-observations:pbt-v2:screening",
                sha256_path(screening_path),
            ),
            private_ref(
                "urn:kizz:ael:private-decision:pbt-v2", sha256_path(terminal_decision_path)
            ),
        ],
    }
    if args.confirmation_observations:
        measurement_set["source_refs"].append(
            private_ref(
                "urn:kizz:ael:private-observations:pbt-v2:confirmation",
                sha256_path(args.confirmation_observations.resolve()),
            )
        )
    measurement_path = output / "measurement-set.json"
    write_json(measurement_path, measurement_set)

    if args.continuation_decision:
        shutil.copyfile(args.continuation_decision.resolve(), output / "continuation-decision.json")
    shutil.copyfile(args.screening_decision.resolve(), output / "screening-decision.json")
    if args.confirmation_decision:
        shutil.copyfile(args.confirmation_decision.resolve(), output / "confirmation-decision.json")
    shutil.copyfile(terminal_decision_path, output / "decision.json")
    disposition, summary, claim_status = decision_summary(terminal_decision)
    counts = terminal_decision["counts"]
    receipt = {
        "schema_version": "ael.evidence-receipt/0.1",
        "object_type": "evidence_receipt",
        "receipt_id": "kizz:ael:receipt:agent-skills-season-1:pbt-v2",
        "generated_at": args.generated_at,
        "concept_ref": {
            "concept_id": CONCEPT_ID,
            "revision": 1,
            "uri": "../../concept.json",
            "sha256": sha256_path(CONCEPT_PATH),
            "visibility": "public",
        },
        "study_ref": study_ref("../../manifests/property-based-testing-v2.study-manifest.json"),
        "run_record_refs": run_refs,
        "measurement_set_ref": {
            "measurement_set_id": measurement_set["measurement_set_id"],
            "uri": "measurement-set.json",
            "sha256": sha256_path(measurement_path),
            "visibility": "public",
        },
        "evidence_level": "controlled_effect_observed",
        "reproducibility": "rerunnable",
        "independence": {
            "label": "maintainer_evaluated",
            "role_overlaps": [
                "Kizz authored the tasks, operated the runner, evaluated deterministic outcomes, and owns the decision."
            ],
            "disclosure": "This is a preregistered maintainer pilot, not independent verification.",
        },
        "decision": {
            "disposition": disposition,
            "summary": summary,
            "scope": [
                "the exact frozen PBT v2 serialization and normalization tasks",
                "Codex CLI 0.146.0 with gpt-5.6-sol at xhigh effort",
                f"preregistration commit {args.preregistration_sha}",
            ],
            "reversal_trigger": "Re-evaluate after any intervention, task, evaluator, runtime, model, prompt, budget, or provider-behavior change.",
        },
        "evaluated_claims": [
            {
                "claim_id": "AEL-PBT-V2-01",
                "statement": "S1 changed hidden-edge acceptance enough to satisfy the frozen terminal rule on the exact pilot cells.",
                "status": claim_status,
                "claim_level": "factor_causal",
                "scope": ["exact matched serialization and normalization pilot cells"],
                "evidence_refs": [
                    f"hidden_acceptance:{item['task_id']}:{item['condition_id']}:R{int(item['repeat_index']):02d}"
                    for _phase, item in all_observations
                    if item["status"] == "valid"
                ],
                "falsifier": "A retained cell, frozen-rule recomputation, or untouched confirmation result contradicts the published counts or outcome.",
            },
            {
                "claim_id": "AEL-PBT-V2-02",
                "statement": "The public decision is bound to a preregistered freeze and private pack composites that preceded scored calls.",
                "status": "supported",
                "claim_level": "workflow",
                "scope": ["freeze and result artifacts in this repository"],
                "evidence_refs": ["screening-decision.json", "decision.json"],
                "falsifier": "Git history or retained private evidence shows a scored call preceding the freeze or a pack hash mismatch.",
            },
        ],
        "unsupported_inferences": [
            "Property-based-testing skills work in general.",
            "The skill independently caused defect discovery or prevention rather than a final hidden-acceptance difference.",
            "The result transfers to other defect families, tasks, models, CLIs, repositories, or production systems.",
            "The maintainer-evaluated result is independent verification.",
            "A token or latency difference from this small pilot is a stable cost effect.",
        ],
        "limitations": [
            f"The terminal decision used {counts['complete_pairs']} matched pairs and has wide task-sampling uncertainty.",
            "Tasks, raw events, candidates, and deterministic evaluator outputs remain private and are represented by opaque hashes.",
            "Kizz authored, operated, and evaluated this pilot; no independent replication exists.",
            "The provider exposed a model identifier but not an immutable model revision.",
            "The reusable ChatGPT credential was process-readable; persisted output was exact-value scanned, but encrypted provider traffic was not inspected.",
        ],
        "invalidation_triggers": [
            "A pack hash, freeze hash, preregistration SHA, observation hash, or published count fails verification",
            "A scored call is shown to predate preregistration",
            "A task, evaluator, prompt, source, model, effort, image, budget, or decision rule changed after freeze",
            "Public language promotes this bounded pilot into a general skill or model claim",
        ],
        "state": {
            "experiment": f"PBT v2 terminal outcome: {terminal_decision['outcome']}",
            "artifact": "frozen private task composites represented by hashes; sanitized evidence materialized",
            "repository": "result package prepared in the local release candidate",
            "publication": "prepared, not published",
            "deployment": "not deployed",
            "outcome": "hidden-edge acceptance observed on exact pilot cells; downstream production outcome unmeasured",
        },
        "publication_state": "public_ready",
        "generator": {"name": "agentic-evidence-lab", "version": __version__},
    }
    write_json(output / "evidence-receipt.json", receipt)
    write_json(
        output / "freeze-ref.json",
        {
            "freeze_id": freeze["freeze_id"],
            "freeze_sha256": sha256_path(freeze_path),
            "preregistration_sha": args.preregistration_sha,
            "screening_pack_sha256": freeze["private_packs"]["screening"]["sha256"],
            "confirmation_pack_sha256": freeze["private_packs"]["confirmation"]["sha256"],
            "screening_decision_sha256": sha256_path(args.screening_decision.resolve()),
            "confirmation_decision_sha256": sha256_path(args.confirmation_decision.resolve())
            if args.confirmation_decision
            else None,
        },
    )
    print(
        json.dumps(
            {
                "runs": len(all_observations),
                "measurements": len(measurements),
                "outcome": terminal_decision["outcome"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
