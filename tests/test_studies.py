from __future__ import annotations

import json
import tomllib
import unittest
from pathlib import Path

from ael.sandbox import tree_sha256
from ael.taskpack import _tasks
from ael.validation import sha256_path

ROOT = Path(__file__).resolve().parents[1]
STUDY_ROOT = ROOT / "studies" / "focused-change-verification"


class FocusedChangeVerificationStudyTests(unittest.TestCase):
    def test_frozen_skill_manifest_matches_files(self) -> None:
        manifest_path = STUDY_ROOT / "artifact.toml"
        manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
        artifact_root = STUDY_ROOT / "artifacts" / "focused-change-verification"
        self.assertEqual(manifest["tree_sha256"], tree_sha256(artifact_root))
        for item in manifest["files"]:
            with self.subTest(path=item["path"]):
                self.assertEqual(item["sha256"], sha256_path(STUDY_ROOT / item["path"]))

    def test_adaptation_pack_manifest_matches_three_tasks(self) -> None:
        pack_root = STUDY_ROOT / "task-pack" / "adaptation-v1"
        manifest = tomllib.loads((pack_root / "task-pack.toml").read_text(encoding="utf-8"))
        self.assertEqual(manifest["tasks_tree_sha256"], tree_sha256(pack_root / "tasks"))
        self.assertEqual(
            ["cross-contract", "local-unit", "migration"],
            [task_id for task_id, _fixture, _evaluator in _tasks(pack_root)],
        )

    def test_study_references_frozen_skill_pack_and_analysis(self) -> None:
        study_path = ROOT / "examples" / "coding-skill" / "study-manifest.json"
        study = json.loads(study_path.read_text(encoding="utf-8"))
        references = [
            study["conditions"][1]["intervention_ref"],
            study["task_packs"][0]["artifact_ref"],
            study["analysis_plan"],
        ]
        for reference in references:
            with self.subTest(uri=reference["uri"]):
                target = (study_path.parent / reference["uri"]).resolve()
                self.assertTrue(target.is_file())
                self.assertEqual(reference["sha256"], sha256_path(target))


if __name__ == "__main__":
    unittest.main()
