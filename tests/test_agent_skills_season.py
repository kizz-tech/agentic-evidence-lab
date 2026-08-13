from __future__ import annotations

import json
import tomllib
import unittest
from pathlib import Path

from ael.sandbox import tree_sha256
from ael.taskpack import _tasks
from ael.validation import sha256_path, validate

ROOT = Path(__file__).resolve().parents[1]
SEASON_ROOT = ROOT / "studies" / "agent-skills-season-1"


class AgentSkillsSeasonOneTests(unittest.TestCase):
    def test_season_has_ten_bounded_studies(self) -> None:
        season = tomllib.loads((SEASON_ROOT / "season.toml").read_text(encoding="utf-8"))
        studies = season["studies"]
        self.assertEqual(list(range(1, 11)), [item["ordinal"] for item in studies])
        self.assertEqual(10, len({item["study_id"] for item in studies}))
        self.assertEqual(3, sum(bool(item["first_wave"]) for item in studies))
        for item in studies:
            with self.subTest(study=item["study_id"]):
                self.assertTrue((SEASON_ROOT / item["protocol"]).is_file())
                self.assertTrue(
                    (
                        SEASON_ROOT / "manifests" / f"{item['study_id']}.study-manifest.json"
                    ).is_file()
                )

    def test_all_season_manifests_validate(self) -> None:
        documents, issues = validate([SEASON_ROOT / "concept.json", SEASON_ROOT / "manifests"])
        self.assertEqual([], [str(issue) for issue in issues])
        self.assertEqual(13, len(documents))

    def test_manifest_hashes_bind_protocol_source_lock_and_calibration_pack(self) -> None:
        for path in sorted((SEASON_ROOT / "manifests").glob("*.json")):
            manifest = json.loads(path.read_text(encoding="utf-8"))
            references = [
                manifest["concept_ref"],
                manifest["analysis_plan"],
                manifest["source_refs"][0],
                manifest["task_packs"][0]["artifact_ref"],
            ]
            for reference in references:
                with self.subTest(manifest=path.name, uri=reference["uri"]):
                    target = (path.parent / reference["uri"]).resolve()
                    self.assertTrue(target.is_file())
                    self.assertEqual(reference["sha256"], sha256_path(target))

    def test_calibration_pack_has_one_hash_bound_task_per_study(self) -> None:
        pack_root = SEASON_ROOT / "task-pack" / "calibration-v1"
        manifest = tomllib.loads((pack_root / "task-pack.toml").read_text(encoding="utf-8"))
        tasks = _tasks(pack_root)
        season = tomllib.loads((SEASON_ROOT / "season.toml").read_text(encoding="utf-8"))
        self.assertEqual(10, manifest["task_count"])
        self.assertEqual(manifest["tasks_tree_sha256"], tree_sha256(pack_root / "tasks"))
        self.assertEqual(
            sorted(item["study_id"] for item in season["studies"]),
            [task_id for task_id, _fixture, _evaluator in tasks],
        )
        entries = {item["task_id"]: item for item in manifest["tasks"]}
        for task_id, fixture, evaluator in tasks:
            with self.subTest(task=task_id):
                self.assertEqual(entries[task_id]["fixture_tree_sha256"], tree_sha256(fixture))
                self.assertEqual(entries[task_id]["evaluator_tree_sha256"], tree_sha256(evaluator))

    def test_committed_calibration_health_matches_frozen_fixtures(self) -> None:
        health = json.loads(
            (SEASON_ROOT / "calibration" / "task-pack-health.json").read_text(encoding="utf-8")
        )
        self.assertTrue(health["healthy"])
        self.assertEqual(10, health["task_count"])
        self.assertTrue(all(item["visible_exit_code"] == 0 for item in health["tasks"]))
        self.assertTrue(all(item["pristine_acceptance_exit_code"] != 0 for item in health["tasks"]))
        pack_root = SEASON_ROOT / "task-pack" / "calibration-v1"
        for item in health["tasks"]:
            with self.subTest(task=item["task_id"]):
                fixture = pack_root / "tasks" / item["task_id"] / "fixture"
                self.assertEqual(item["fixture_sha256"], tree_sha256(fixture))

    def test_reviewed_third_party_sources_are_maintainer_controlled_only(self) -> None:
        lock = tomllib.loads((SEASON_ROOT / "sources.lock.toml").read_text(encoding="utf-8"))
        self.assertEqual(12, len(lock["sources"]))
        self.assertTrue(
            all(
                item["hosted_model_execution"] == "maintainer_controlled_only"
                for item in lock["sources"]
            )
        )
        self.assertTrue(
            all(item["source_state"] == "verified_snapshot" for item in lock["sources"])
        )

    def test_activation_calibration_evidence_validates(self) -> None:
        calibration = SEASON_ROOT / "calibration" / "runtime-v1"
        documents, issues = validate(
            [SEASON_ROOT / "concept.json", SEASON_ROOT / "manifests", calibration]
        )
        self.assertEqual([], [str(issue) for issue in issues])
        counts: dict[str, int] = {}
        for document in documents:
            counts[document.object_type] = counts.get(document.object_type, 0) + 1
        self.assertEqual(
            {
                "concept": 1,
                "study_manifest": 12,
                "run_record": 22,
                "measurement_set": 10,
                "evidence_receipt": 10,
            },
            counts,
        )


if __name__ == "__main__":
    unittest.main()
