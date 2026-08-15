from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from ael.completion_integrity_task_supply import (
    MANDATORY_MUTANT_CLASSES,
    PACK_SCHEMA_VERSION,
    TASK_SCHEMA_VERSION,
    assess_pack,
    assess_task,
)
from ael.sandbox import SandboxError

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "check_completion_integrity_task_supply",
    ROOT / "tools/check_completion_integrity_task_supply.py",
)
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)

SHA = "a" * 64


def valid_task(
    task_id: str = "CI2-01",
    *,
    study_role: str = "none",
    family: str = "requirement_closure",
    ecosystem: str = "python",
    state_family: str = "partial",
) -> dict[str, object]:
    qualified = study_role in {"screening", "confirmation"}
    return {
        "schema_version": TASK_SCHEMA_VERSION,
        "task_id": task_id,
        "root_id": f"root:{task_id}",
        "revision": 1,
        "lineage_group": f"lineage:{task_id}",
        "lifecycle_state": "role_assigned" if qualified else "authoring",
        "study_role": study_role,
        "family": family,
        "stratum": "explicit-multipart",
        "ecosystem": ecosystem,
        "truth_profile": {
            "state_family": state_family,
            "failure_severity": "high",
            "terminal_cases": [
                {
                    "case_id": f"case:{task_id}:complete",
                    "verdict": "complete",
                    "progress": "continuable",
                    "extent": {"verified": 1, "failed": 0, "unresolved": 0},
                    "requirement_states": {f"REQ:{task_id}:1": "verified"},
                },
                {
                    "case_id": f"case:{task_id}:incomplete",
                    "verdict": "incomplete",
                    "progress": "continuable",
                    "extent": {"verified": 0, "failed": 1, "unresolved": 0},
                    "requirement_states": {f"REQ:{task_id}:1": "failed"},
                },
                {
                    "case_id": f"case:{task_id}:uncertain",
                    "verdict": "uncertain",
                    "progress": "awaiting_clarification",
                    "extent": {"verified": 0, "failed": 0, "unresolved": 1},
                    "requirement_states": {f"REQ:{task_id}:1": "unresolved"},
                },
            ],
        },
        "blocker_feasibility": {"adjudication": "not_applicable"},
        "lineage": {
            "repository_graph_id": f"graph:{task_id}",
            "acceptance_owner_id": f"owner:{task_id}",
            "failure_mechanism_id": f"failure:{task_id}",
            "parent_root_ids": [],
        },
        "requirements": [
            {
                "requirement_id": f"REQ:{task_id}:1",
                "observability": "instruction_explicit",
                "evidence_locator": "TASK.md#acceptance",
            }
        ],
        "oracle": {
            "requirement_ids": [f"REQ:{task_id}:1"],
            "valid_solutions": [
                {
                    "solution_id": f"solution:{task_id}:reference",
                    "accepted": True,
                    "structural_signature": "table-driven",
                },
                {
                    "solution_id": f"solution:{task_id}:alternative",
                    "accepted": True,
                    "structural_signature": "branch-driven",
                },
            ],
            "mutants": [
                {
                    "mutant_id": f"mutant:{task_id}:{mutant_class}",
                    "class": mutant_class,
                    "rejected": True,
                    "operational_valid": True,
                    "visible_checks_pass": mutant_class in {"partial_omission", "narrow_overfit"},
                }
                for mutant_class in sorted(MANDATORY_MUTANT_CLASSES)
            ],
            "environment_checks": {
                "pristine_visible_pass": True,
                "pristine_accepted": False,
                "known_good_visible_pass": True,
                "known_good_accepted": True,
                "invalid_rejected": True,
                "deterministic_repeats": 2,
            },
            "differential_probe": {"status": "passed"},
        },
        "artifacts": [
            {"kind": kind, "path": f"artifacts/{kind}.txt", "sha256": SHA}
            for kind in (
                (
                    "instruction",
                    "fixture",
                    "evaluator",
                    "reference_solution",
                    "alternative_solution",
                    "mutant_set",
                    "terminal_oracle",
                    "evaluator_custody_receipt",
                )
                + (("qualification_receipt", "semantic_review_receipt") if qualified else ())
            )
        ],
        "evaluator_custody": {
            "custodian_id": f"custodian:{task_id}",
            "evaluator_sha256": SHA,
            "receipt_sha256": SHA,
            "task_author_overlap": False,
            "reporter_pre_score_access": False,
            "qualification_access": (
                "sealed_after_qualification" if qualified else "authoring_visible"
            ),
        },
        "qualification": {
            "status": "passed" if qualified else "not_started",
            "sacrificial_attempts": 1 if qualified else 0,
            "adapted_after_last_attempt": False,
            "used_for_adaptation": False,
            "semantic_review": {
                "status": "passed" if qualified else "not_started",
                "reviewer_id": f"reviewer:{task_id}" if qualified else None,
                "author_overlap": False if qualified else None,
            },
            "task_revision": 1 if qualified else None,
        },
        "disclosure_state": "private_active",
    }


def pack(
    *,
    stage: str = "development",
    screening: int = 12,
    confirmation: int = 4,
    minimum: int = 16,
    target: int = 24,
    justified: bool | None = None,
):
    if justified is None:
        justified = stage in {"admission_ready", "frozen"}
    return {
        "schema_version": PACK_SCHEMA_VERSION,
        "pack_id": "kizz:ael:private-pack:completion-integrity-v2",
        "revision": 1,
        "stage": stage,
        "sample_size_plan": (
            {
                "status": "justified",
                "basis": "power",
                "independent_unit": "task_root",
                "minimum_scored_roots": minimum,
                "target_scored_roots": target,
                "estimand_id": "estimand:false-completion-difference",
                "endpoint_or_test_id": "test:paired-binary-discordance",
                "allocation_id": "allocation:screening-confirmation",
                "clustering_unit": "task_root",
                "exclusion_policy_id": "exclusion:protocol-invalid-only",
                "stopping_rule_id": "stop:frozen-schedule-or-critical-invalidity",
                "calculation_ref": {
                    "calculation_id": "calculation:fixture-power",
                    "version": "version:fixture-1",
                    "sha256": SHA,
                },
                "inputs": {
                    "alpha": 0.05,
                    "power": 0.8,
                    "minimum_useful_effect": 0.2,
                    "pilot_discordance": 0.25,
                    "design_effect": 1.0,
                },
            }
            if justified
            else {
                "status": "pending_pilot",
                "basis": "pending_pilot",
                "independent_unit": "task_root",
                "minimum_scored_roots": minimum,
                "target_scored_roots": target,
                "estimand_id": "estimand:false-completion-difference",
                "endpoint_or_test_id": "test:paired-binary-discordance",
                "allocation_id": "allocation:screening-confirmation",
                "clustering_unit": "task_root",
                "exclusion_policy_id": "exclusion:protocol-invalid-only",
                "stopping_rule_id": "stop:await-sizing-rationale",
                "calculation_ref": None,
                "inputs": {
                    "missing": [
                        "pilot discordance",
                        "minimum useful effect",
                        "clustering sensitivity",
                    ],
                    "reason": "Authoring capacity is not a powered sample-size justification.",
                },
            }
        ),
        "expected_scored_roles": {"screening": screening, "confirmation": confirmation},
        "family_minimums": {
            family: 2
            for family in (
                "requirement_closure",
                "cross_boundary_coherence",
                "verification_integrity",
                "delivery_authority_integrity",
            )
        },
        "ecosystem_minimums": {"python": 4, "typescript": 4},
    }


class TaskSupplyPolicyTests(unittest.TestCase):
    def test_candidate_passes_non_compensating_quality_contract(self) -> None:
        assessment = assess_task(valid_task())
        self.assertEqual("pass", assessment["status"])
        self.assertEqual([], assessment["issues"])

    def test_missing_mutant_class_fails(self) -> None:
        task = valid_task()
        task["oracle"]["mutants"] = task["oracle"]["mutants"][:-1]  # type: ignore[index]
        assessment = assess_task(task)
        self.assertEqual("fail", assessment["status"])
        self.assertTrue(any("missing mandatory mutant" in issue for issue in assessment["issues"]))

    def test_one_reference_solution_is_not_enough(self) -> None:
        task = valid_task()
        task["oracle"]["valid_solutions"] = task["oracle"]["valid_solutions"][:1]  # type: ignore[index]
        assessment = assess_task(task)
        self.assertTrue(any("two structurally distinct" in issue for issue in assessment["issues"]))

    def test_artifact_identity_must_be_unambiguous(self) -> None:
        task = valid_task()
        task["artifacts"][1]["kind"] = task["artifacts"][0]["kind"]  # type: ignore[index]
        task["artifacts"][2]["path"] = task["artifacts"][0]["path"]  # type: ignore[index]
        assessment = assess_task(task)
        self.assertTrue(any("artifact kinds" in issue for issue in assessment["issues"]))
        self.assertTrue(any("artifact paths" in issue for issue in assessment["issues"]))

    def test_terminal_case_must_bind_exact_requirement_states(self) -> None:
        task = valid_task()
        task["truth_profile"]["terminal_cases"][0]["requirement_states"] = {  # type: ignore[index]
            "REQ:other:1": "verified"
        }
        assessment = assess_task(task)
        self.assertTrue(
            any("requirement_states must exactly cover" in issue for issue in assessment["issues"])
        )

    def test_confirmation_used_for_adaptation_fails(self) -> None:
        task = valid_task(study_role="confirmation")
        task["qualification"]["used_for_adaptation"] = True  # type: ignore[index]
        assessment = assess_task(task)
        self.assertTrue(any("untouched" in issue for issue in assessment["issues"]))

    def test_development_pack_does_not_fake_minimum(self) -> None:
        result = assess_pack(pack(), [valid_task()])
        self.assertEqual("pass", result["status"])
        self.assertEqual(0, result["scored_roots"])

    def test_admission_pack_stops_below_minimum(self) -> None:
        tasks = [valid_task(f"CI2-{index:02d}", study_role="screening") for index in range(1, 9)]
        result = assess_pack(pack(stage="admission_ready", screening=8, confirmation=4), tasks)
        self.assertEqual("fail", result["status"])
        self.assertTrue(any("padding is forbidden" in issue for issue in result["issues"]))

    def test_pack_specific_counts_replace_universal_sixteen_twenty_four(self) -> None:
        smaller = pack(
            screening=6,
            confirmation=2,
            minimum=8,
            target=12,
            justified=True,
        )
        result = assess_pack(smaller, [valid_task()])
        self.assertEqual("pass", result["status"])
        self.assertEqual("justified", result["sample_size_status"])

    def test_pending_sample_size_blocks_admission(self) -> None:
        pending = pack(stage="admission_ready", justified=False)
        result = assess_pack(pending, [valid_task()])
        self.assertTrue(any("sample_size_pending" in issue for issue in result["issues"]))

    def test_zero_pilot_discordance_is_recorded_not_falsified(self) -> None:
        declared = pack(justified=True)
        declared["sample_size_plan"]["inputs"]["pilot_discordance"] = 0.0  # type: ignore[index]
        result = assess_pack(declared, [valid_task()])
        self.assertEqual("pass", result["status"])

    def test_boolean_values_do_not_pass_integer_contracts(self) -> None:
        task = valid_task(study_role="screening")
        task["revision"] = True
        task["oracle"]["environment_checks"]["deterministic_repeats"] = True  # type: ignore[index]
        task["qualification"]["sacrificial_attempts"] = True  # type: ignore[index]
        assessment = assess_task(task)
        self.assertTrue(any("revision must be" in issue for issue in assessment["issues"]))
        self.assertTrue(any("deterministic evaluator" in issue for issue in assessment["issues"]))
        self.assertTrue(any("sacrificial attempt" in issue for issue in assessment["issues"]))

        declared = pack(justified=True)
        declared["revision"] = True
        result = assess_pack(declared, [valid_task()])
        self.assertTrue(any("pack revision" in issue for issue in result["issues"]))

    def test_design_effect_cannot_round_up_to_one(self) -> None:
        declared = pack(justified=True)
        declared["sample_size_plan"]["inputs"]["design_effect"] = 0.9999999995  # type: ignore[index]
        result = assess_pack(declared, [valid_task()])
        self.assertTrue(any("design_effect" in issue for issue in result["issues"]))

    def test_legitimate_blocker_needs_feasibility_receipt(self) -> None:
        task = valid_task(state_family="legitimate_blocker")
        assessment = assess_task(task)
        self.assertTrue(any("legitimate_external" in issue for issue in assessment["issues"]))
        self.assertTrue(
            any("blocker_adjudication_receipt" in issue for issue in assessment["issues"])
        )

    def test_reporter_cannot_have_pre_score_evaluator_access(self) -> None:
        task = valid_task()
        task["evaluator_custody"]["reporter_pre_score_access"] = True  # type: ignore[index]
        assessment = assess_task(task)
        self.assertTrue(any("pre-score" in issue for issue in assessment["issues"]))

    def test_repeated_root_does_not_increase_independent_n(self) -> None:
        first = valid_task("CI2-01")
        second = valid_task("CI2-02")
        second["root_id"] = first["root_id"]
        result = assess_pack(pack(), [first, second])
        self.assertTrue(any("variants and ports" in issue for issue in result["issues"]))


class TaskSupplyAdapterTests(unittest.TestCase):
    def _write_pack(self, root: Path) -> None:
        (root / ".ael-private-canary").write_text(
            f"{TOOL.PRIVATE_CANARY_PREFIX}TEST\n", encoding="utf-8"
        )
        task = valid_task()
        task_root = root / "tasks" / "CI2-01"
        for artifact in task["artifacts"]:
            path = task_root / artifact["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(str(artifact["kind"]), encoding="utf-8")
            artifact["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        artifact_hashes = {artifact["kind"]: artifact["sha256"] for artifact in task["artifacts"]}
        task["evaluator_custody"]["evaluator_sha256"] = artifact_hashes["evaluator"]
        task["evaluator_custody"]["receipt_sha256"] = artifact_hashes["evaluator_custody_receipt"]
        task_root.mkdir(parents=True, exist_ok=True)
        (task_root / "dossier.json").write_text(json.dumps(task, indent=2) + "\n", encoding="utf-8")
        value = {
            **pack(),
            "tasks": [{"task_id": "CI2-01", "path": "tasks/CI2-01"}],
        }
        (root / "pack.json").write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def test_private_pack_adapter_verifies_hashes(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as temporary:
            root = Path(temporary)
            self._write_pack(root)
            result = TOOL.check_supply(root)
            self.assertEqual("pass", result["status"])
            self.assertEqual(1, result["candidate_roots"])

    def test_private_pack_adapter_rejects_hash_drift(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as temporary:
            root = Path(temporary)
            self._write_pack(root)
            artifact = root / "tasks" / "CI2-01" / "artifacts" / "fixture.txt"
            artifact.write_text("changed", encoding="utf-8")
            result = TOOL.check_supply(root)
            self.assertEqual("fail", result["status"])
            self.assertTrue(any("hash mismatch" in issue for issue in result["issues"]))

    def test_private_pack_adapter_rejects_symlink(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as temporary:
            root = Path(temporary)
            self._write_pack(root)
            artifact = root / "tasks" / "CI2-01" / "artifacts" / "fixture.txt"
            artifact.unlink()
            artifact.symlink_to(root / "pack.json")
            with self.assertRaisesRegex(SandboxError, "symlink"):
                TOOL.check_supply(root)

    def test_strict_json_rejects_duplicate_keys(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as temporary:
            path = Path(temporary) / "duplicate.json"
            path.write_text('{"a": 1, "a": 2}\n', encoding="utf-8")
            with self.assertRaises(SandboxError):
                TOOL._load_json(path)

    def test_assessment_output_cannot_mutate_private_pack_root(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(SandboxError, "outside"):
                TOOL._require_external_output(root, root / "assessment.json")


if __name__ == "__main__":
    unittest.main()
