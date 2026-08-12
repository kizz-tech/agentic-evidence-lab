from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ael.pbt_pilot import decide_pbt_stage, pbt_confirmation_unlocked
from ael.study_freeze import (
    FREEZE_SCHEMA_VERSION,
    OBSERVATIONS_SCHEMA_VERSION,
    deterministic_schedule,
    validate_freeze_bundle,
)
from ael.validation import sha256_path


def bundle() -> dict[str, object]:
    conditions = [
        {"condition_id": "B0", "role": "baseline", "intervention_sha256": None},
        {"condition_id": "S1", "role": "treatment", "intervention_sha256": "a" * 64},
    ]
    return {
        "schema_version": FREEZE_SCHEMA_VERSION,
        "freeze_id": "kizz:ael:freeze:test:2",
        "study_id": "kizz:ael:study:test",
        "study_revision": 2,
        "frozen_at": "2026-08-12T00:00:00Z",
        "scored_calls_executed": 0,
        "analysis_code_sha256": "b" * 64,
        "decision_code_sha256": "3" * 64,
        "execution_code_sha256": "4" * 64,
        "runner_code_sha256": "2" * 64,
        "prompt_sha256": "c" * 64,
        "conditions": conditions,
        "private_packs": {
            "screening": {
                "uri": "urn:kizz:ael:private-pack:test:screening",
                "sha256": "d" * 64,
                "task_ids": ["S-01"],
            },
            "confirmation": {
                "uri": "urn:kizz:ael:private-pack:test:confirmation",
                "sha256": "e" * 64,
                "task_ids": ["C-01"],
            },
        },
        "primary_endpoint": "unsupported completion claim per matched run",
        "critical_failure_gates": ["no fabricated external evidence"],
        "invalid_run_policy": "retain and exclude only enumerated integrity failures",
        "retry_policy": "retry only a prespecified infrastructure failure",
        "runtime": {
            "harness": "codex-cli",
            "harness_version": "0.146.0",
            "model": "gpt-test",
            "reasoning_effort": "xhigh",
            "runner_image_id": "sha256:" + "f" * 64,
            "proxy_image_id": "sha256:" + "1" * 64,
        },
        "budget": {
            "initial_repeats": 1,
            "max_repeats": 1,
            "max_scored_runs": 4,
            "per_run_timeout_seconds": 900,
            "max_generated_tokens": 10000,
        },
        "schedule": {
            "algorithm": "sha256-keyed-order-v1",
            "seed": "public-seed",
            "screening": deterministic_schedule(["S-01"], ["B0", "S1"], 1, "s"),
            "confirmation": deterministic_schedule(["C-01"], ["B0", "S1"], 1, "c"),
        },
        "continuation_rule": {
            "minimum_favorable_pairs": 1,
            "maximum_unfavorable_pairs": 0,
            "require_zero_treatment_critical_failures": True,
        },
        "selection_rule": {
            "minimum_favorable_pairs": 1,
            "maximum_unfavorable_pairs": 0,
            "require_zero_treatment_critical_failures": True,
        },
        "confirmation_rule": {
            "minimum_favorable_pairs": 1,
            "maximum_unfavorable_pairs": 0,
            "require_zero_treatment_critical_failures": True,
        },
        "roles": {
            "task_author": "maintainer",
            "operator": "maintainer",
            "evaluator": "deterministic evaluator",
            "decision_owner": "maintainer",
        },
    }


class StudyFreezeTests(unittest.TestCase):
    def test_valid_bundle_passes(self) -> None:
        self.assertEqual([], [str(issue) for issue in validate_freeze_bundle(bundle())])

    def test_schedule_must_cover_all_frozen_cells(self) -> None:
        data = bundle()
        data["schedule"]["screening"] = data["schedule"]["screening"][:1]
        issues = validate_freeze_bundle(data)
        self.assertTrue(any("cover every frozen" in issue.message for issue in issues))

    def test_nonzero_scored_calls_cannot_freeze(self) -> None:
        data = bundle()
        data["scored_calls_executed"] = 1
        issues = validate_freeze_bundle(data)
        self.assertTrue(any(issue.location == "scored_calls_executed" for issue in issues))

    def test_selection_and_unlock_are_hash_bound(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle_path = root / "freeze.json"
            observations_path = root / "observations.json"
            selection_path = root / "selection.json"
            bundle_path.write_text(json.dumps(bundle()), encoding="utf-8")
            observations = {
                "schema_version": OBSERVATIONS_SCHEMA_VERSION,
                "phase": "screening",
                "freeze_sha256": sha256_path(bundle_path),
                "observations": [
                    {
                        "task_id": "S-01",
                        "condition_id": "B0",
                        "repeat_index": 1,
                        "schedule_sequence": next(
                            entry["sequence"]
                            for entry in bundle()["schedule"]["screening"]
                            if entry["condition_id"] == "B0"
                        ),
                        "status": "valid",
                        "skill_activated": False,
                        "hidden_acceptance": False,
                        "critical_failure": False,
                    },
                    {
                        "task_id": "S-01",
                        "condition_id": "S1",
                        "repeat_index": 1,
                        "schedule_sequence": next(
                            entry["sequence"]
                            for entry in bundle()["schedule"]["screening"]
                            if entry["condition_id"] == "S1"
                        ),
                        "status": "valid",
                        "skill_activated": True,
                        "hidden_acceptance": True,
                        "critical_failure": False,
                    },
                ],
            }
            observations_path.write_text(json.dumps(observations), encoding="utf-8")
            selection = decide_pbt_stage(bundle_path, observations_path, "selection")
            selection_path.write_text(json.dumps(selection), encoding="utf-8")
            self.assertEqual("select_S1", selection["outcome"])
            self.assertTrue(pbt_confirmation_unlocked(bundle_path, selection_path))
            selection["freeze_ref"]["sha256"] = "0" * 64
            selection_path.write_text(json.dumps(selection), encoding="utf-8")
            self.assertFalse(pbt_confirmation_unlocked(bundle_path, selection_path))

    def test_selection_requires_the_full_frozen_schedule(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle_path = root / "freeze.json"
            observations_path = root / "observations.json"
            data = bundle()
            bundle_path.write_text(json.dumps(data), encoding="utf-8")
            one_entry = data["schedule"]["screening"][0]
            observations_path.write_text(
                json.dumps(
                    {
                        "schema_version": OBSERVATIONS_SCHEMA_VERSION,
                        "phase": "screening",
                        "freeze_sha256": sha256_path(bundle_path),
                        "observations": [
                            {
                                "task_id": one_entry["task_id"],
                                "condition_id": one_entry["condition_id"],
                                "repeat_index": one_entry["repeat_index"],
                                "schedule_sequence": one_entry["sequence"],
                                "status": "valid",
                                "skill_activated": one_entry["condition_id"] == "S1",
                                "hidden_acceptance": False,
                                "critical_failure": False,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(Exception, "exact frozen schedule"):
                decide_pbt_stage(bundle_path, observations_path, "selection")

    def test_forged_selection_counts_do_not_unlock_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle_path = root / "freeze.json"
            selection_path = root / "selection.json"
            data = bundle()
            bundle_path.write_text(json.dumps(data), encoding="utf-8")
            selection_path.write_text(
                json.dumps(
                    {
                        "schema_version": "ael.study-decision/0.1",
                        "decision_id": f"{data['freeze_id']}:selection",
                        "stage": "selection",
                        "study_id": data["study_id"],
                        "study_revision": data["study_revision"],
                        "freeze_ref": {
                            "sha256": sha256_path(bundle_path),
                            "freeze_id": data["freeze_id"],
                        },
                        "observations_sha256": "f" * 64,
                        "counts": {
                            "invalid_observations": 0,
                            "activation_failures": 0,
                            "treatment_critical_failures": 0,
                            "baseline_hidden_failures": 0,
                            "complete_pairs": 1,
                            "favorable_pairs": 1,
                            "unfavorable_pairs": 0,
                        },
                        "rule": data["selection_rule"],
                        "outcome": "select_S1",
                        "confirmation_unlocked": True,
                    }
                ),
                encoding="utf-8",
            )
            self.assertFalse(pbt_confirmation_unlocked(bundle_path, selection_path))


if __name__ == "__main__":
    unittest.main()
