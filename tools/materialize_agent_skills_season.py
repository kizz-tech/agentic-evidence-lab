from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path

from ael.validation import sha256_path

ROOT = Path(__file__).resolve().parents[1]
SEASON_ROOT = ROOT / "studies" / "agent-skills-season-1"
MANIFEST_ROOT = SEASON_ROOT / "manifests"
CONCEPT_ID = "kizz:ael:concept:public-agent-skill-effectiveness"

QUESTIONS = {
    "truthful-completion": "Does the exact pinned verification-before-completion skill reduce unsupported completion claims relative to the same Codex stack without it?",
    "debugging-tournament": "Which frozen debugging intervention most often produces a root-cause-correct repair under the same task and total-system budget contract?",
    "test-driven-development": "Does the exact pinned test-driven-development skill increase observed test-first behavior and reduce hidden regressions relative to baseline and an equal-context placebo?",
    "property-based-testing": "Does the exact pinned property-based-testing skill discover and prevent seeded edge-case defects missed by the same stack without it?",
    "differential-security-review": "Does the exact pinned differential-review skill improve critical security-regression recall at a bounded false-positive count?",
    "review-team-topology": "At a matched total-system budget, does the frozen ce-code-review topology produce more actionable non-duplicate findings than one strong reviewer?",
    "mcp-server-construction": "Does the exact pinned mcp-builder skill improve protocol-conformant MCP task completion relative to the same coding stack without it?",
    "webapp-testing": "Does the exact pinned webapp-testing skill improve detection and reproducible explanation of user-visible web regressions?",
    "frontend-design": "Does the exact pinned frontend-design skill improve blinded preference while preserving accessibility and task success?",
    "recursive-skill-improvement": "Does a frozen skill-improvement workflow improve held-out target-skill performance without introducing new critical failures?",
}

INTERVENTION_CLASSES = {
    "review-team-topology": "topology",
    "recursive-skill-improvement": "workflow",
}

PLACEBO_STUDIES = {"test-driven-development", "frontend-design"}


def _condition_for_source(source: dict[str, object], index: int) -> dict[str, object]:
    repository = str(source["repository"])
    revision = str(source["revision"])
    path = str(source["path"])
    source_id = str(source["source_id"])
    compatibility_note = ""
    changed_factors = ["installed_skill_tree", "instruction_context"]
    if source_id.startswith("every-"):
        compatibility_note = (
            " The raw upstream tree activated in Codex calibration; upstream runtime assumptions "
            "may still limit behavior and any later compatibility bundle is a distinct intervention."
        )
    if source_id == "trailofbits-skill-improver":
        compatibility_note = (
            " The raw tree activated in calibration without its optional reviewer dependency; "
            "screening must either freeze that dependency or explicitly study the raw snapshot."
        )
    return {
        "condition_id": f"S{index}",
        "label": source_id,
        "role": "treatment",
        "intervention_class": "skill",
        "intervention_ref": {
            "uri": f"{repository}/tree/{revision}/{path}",
            "sha256": source["tree_sha256"],
            "revision": revision,
            "visibility": "public",
        },
        "changed_factors": changed_factors,
        "delta_from_baseline": (
            "Adds the exact source-locked upstream skill tree to the otherwise frozen base "
            f"condition.{compatibility_note}"
        ),
    }


def build_manifests() -> dict[Path, str]:
    season = tomllib.loads((SEASON_ROOT / "season.toml").read_text(encoding="utf-8"))
    lock = tomllib.loads((SEASON_ROOT / "sources.lock.toml").read_text(encoding="utf-8"))
    sources = {item["source_id"]: item for item in lock["sources"]}
    concept_hash = sha256_path(SEASON_ROOT / "concept.json")
    source_lock_hash = sha256_path(SEASON_ROOT / "sources.lock.toml")
    pack_manifest_path = SEASON_ROOT / "task-pack" / "calibration-v1" / "task-pack.toml"
    pack_manifest = tomllib.loads(pack_manifest_path.read_text(encoding="utf-8"))
    pack_hash = sha256_path(pack_manifest_path)
    rendered: dict[Path, str] = {}
    for item in season["studies"]:
        study_id = item["study_id"]
        protocol_path = SEASON_ROOT / item["protocol"]
        conditions: list[dict[str, object]] = [
            {
                "condition_id": "B0",
                "label": "Frozen strong Codex baseline",
                "role": "baseline",
                "intervention_class": INTERVENTION_CLASSES.get(study_id, "skill"),
                "intervention_ref": {
                    "uri": f"urn:kizz:ael:season1:baseline:{study_id}:unfrozen",
                    "visibility": "private",
                },
                "changed_factors": [],
                "delta_from_baseline": "Reference condition; exact runtime and context snapshot remain to be frozen after activation calibration.",
            }
        ]
        conditions.extend(
            _condition_for_source(sources[source_id], index)
            for index, source_id in enumerate(item["source_ids"], start=1)
        )
        if study_id in PLACEBO_STUDIES:
            conditions.append(
                {
                    "condition_id": "P1",
                    "label": "Equal-context inert procedural placebo",
                    "role": "control",
                    "intervention_class": "context_policy",
                    "intervention_ref": {
                        "uri": f"urn:kizz:ael:season1:placebo:{study_id}:unfrozen",
                        "visibility": "hidden",
                    },
                    "changed_factors": ["context_length", "neutral_procedural_context"],
                    "delta_from_baseline": "Adds a frozen neutral context bundle matched to treatment size without the hypothesized mechanism.",
                }
            )
        manifest = {
            "schema_version": "ael.study-manifest/0.1",
            "object_type": "study_manifest",
            "study_id": f"kizz:ael:study:agent-skills-season-1:{study_id}",
            "revision": 1,
            "status": "draft",
            "decision_question": QUESTIONS[study_id],
            "comparison_mode": "controlled_factor",
            "primary_estimand": {
                "name": item["primary_endpoint"],
                "description": f"Matched-condition difference in {item['primary_endpoint']}; critical failures, invalid runs, cost, and latency remain separate gates.",
                "unit_of_analysis": "task cluster",
                "aggregation": "Report task and stratum outcomes before a prespecified paired aggregate; numeric threshold and uncertainty method remain calibration-blocked.",
            },
            "concept_ref": {
                "concept_id": CONCEPT_ID,
                "revision": 1,
                "uri": "../concept.json",
                "sha256": concept_hash,
                "visibility": "public",
            },
            "conditions": conditions,
            "task_packs": [
                {
                    "task_pack_id": "agent-skills-season-1-calibration-v1",
                    "revision": pack_manifest["revision"],
                    "role": "calibration",
                    "strata": [study_id],
                    "artifact_ref": {
                        "uri": "../task-pack/calibration-v1/task-pack.toml",
                        "sha256": pack_hash,
                        "visibility": "public",
                    },
                    "contamination_notes": [
                        "Public mechanics task only; cannot enter a skill-effect estimate or hidden confirmation pack."
                    ],
                },
                {
                    "task_pack_id": f"{study_id}-screening",
                    "revision": 1,
                    "role": "screening",
                    "artifact_ref": {
                        "uri": f"urn:kizz:ael:season1:{study_id}:screening:unfrozen",
                        "visibility": "hidden",
                    },
                    "contamination_notes": [
                        "Must not prescribe the target behavior or reuse public calibration defects."
                    ],
                },
                {
                    "task_pack_id": f"{study_id}-confirmation",
                    "revision": 1,
                    "role": "holdout",
                    "artifact_ref": {
                        "uri": f"urn:kizz:ael:season1:{study_id}:confirmation:unfrozen",
                        "visibility": "hidden",
                    },
                    "contamination_notes": [
                        "No candidate author, adaptation run, or screening evaluator may access this pack before finalist freeze."
                    ],
                },
            ],
            "budget": {
                "status": "uncalibrated",
                "description": "Match total-system resources after activation calibration; no numeric execution cap is yet frozen.",
                "dimensions": [
                    {
                        "metric": "generated_work_tokens",
                        "unit": "tokens",
                        "scope": "whole condition per task",
                        "rule": "count every parent, subagent, integration, and retry call",
                        "source": "activation calibration required",
                    },
                    {
                        "metric": "wall_time",
                        "unit": "seconds",
                        "scope": "whole condition per task",
                        "rule": "record actual elapsed time and predeclare timeout",
                        "source": "activation calibration required",
                    },
                ],
            },
            "adaptation_boundary": {
                "candidate_freeze_required": True,
                "runner_up_substitution": "forbidden",
                "description": "Every compatibility adaptation is a separately named content-addressed intervention. Screening selects one frozen finalist or rejects all; holdout failure cannot promote a runner-up.",
            },
            "selection_rules": [
                "Require source-lock verification and observed intervention activation before effectiveness screening.",
                "Select or reject using only frozen screening rules; do not revise a candidate after seeing holdout evidence.",
                "Keep invalid, negative, and inconclusive cells in the evidence package.",
            ],
            "stop_rules": [
                "Run third-party content only as an exact source-locked, maintainer-reviewed snapshot in maintainer-controlled execution; arbitrary submissions remain blocked.",
                "Stop if task instructions prescribe the target behavior, evaluators cannot distinguish pristine inputs, or condition equality is not evidenced.",
                "Retry only operationally invalid byte-equivalent runs under a predeclared rule.",
                "Do not publish an effectiveness or leaderboard claim from the public calibration task.",
            ],
            "roles": [
                {
                    "role": "concept_owner",
                    "actor_id": "kizz-ael-maintainer",
                    "organization": "Kizz",
                    "independence_group": "maintainer",
                },
                {
                    "role": "artifact_author",
                    "actor_id": "external-source-authors-and-adaptation-owner-unassigned",
                    "independence_group": "mixed",
                },
                {
                    "role": "task_pack_owner",
                    "actor_id": "season-one-task-owner-unassigned",
                    "organization": "Kizz",
                    "independence_group": "maintainer",
                },
                {
                    "role": "runner_operator",
                    "actor_id": "season-one-runner-unassigned",
                    "organization": "Kizz",
                    "independence_group": "maintainer",
                },
                {
                    "role": "evaluator",
                    "actor_id": "season-one-evaluator-unassigned",
                    "independence_group": "maintainer-evaluation",
                },
                {
                    "role": "decision_owner",
                    "actor_id": "kizz-ael-maintainer",
                    "organization": "Kizz",
                    "independence_group": "maintainer",
                },
                {
                    "role": "receipt_signer",
                    "actor_id": "kizz-ael-maintainer",
                    "organization": "Kizz",
                    "independence_group": "maintainer",
                },
            ],
            "independence_claim": {
                "label": "maintainer_evaluated",
                "role_overlaps": [
                    "Kizz owns the experiment contract, task-pack process, execution, and final decision; external independent replication is not yet assigned."
                ],
            },
            "analysis_plan": {
                "uri": f"../{item['protocol']}",
                "sha256": sha256_path(protocol_path),
                "visibility": "public",
            },
            "source_refs": [
                {
                    "uri": "../sources.lock.toml",
                    "sha256": source_lock_hash,
                    "visibility": "public",
                }
            ],
        }
        path = MANIFEST_ROOT / f"{study_id}.study-manifest.json"
        rendered[path] = json.dumps(manifest, indent=2, sort_keys=False) + "\n"
    return rendered


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    expected = build_manifests()
    failures: list[str] = []
    for path, payload in expected.items():
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != payload:
                failures.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(payload, encoding="utf-8")
    if failures:
        for failure in failures:
            print(f"generated manifest is stale: {failure}", file=sys.stderr)
        return 1
    action = "verified" if args.check else "materialized"
    print(f"agent-skills season manifests {action}: {len(expected)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
