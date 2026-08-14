from __future__ import annotations

import copy
import json
import re
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from ael.calibration import render_report, simulate
from ael.render import render_receipt
from ael.validation import SCHEMA_FILES, Document, _relative_target, _schema, sha256_path, validate

ROOT = Path(__file__).resolve().parents[1]
COUNCIL_EXAMPLE = ROOT / "examples" / "council-generation-1"
CODEX_CALIBRATION = ROOT / "examples" / "coding-skill" / "calibration-v1"


class ContractValidationTests(unittest.TestCase):
    def test_all_schemas_are_valid_draft_2020_12(self) -> None:
        for object_type in SCHEMA_FILES:
            with self.subTest(object_type=object_type):
                Draft202012Validator.check_schema(_schema(object_type))

    def test_council_generation_one_vertical_slice_validates(self) -> None:
        documents, issues = validate([COUNCIL_EXAMPLE])
        self.assertEqual([], [str(issue) for issue in issues])
        counts: dict[str, int] = {}
        for document in documents:
            counts[document.object_type] = counts.get(document.object_type, 0) + 1
        self.assertEqual(
            {
                "concept": 1,
                "study_manifest": 1,
                "run_record": 12,
                "measurement_set": 1,
                "evidence_receipt": 1,
            },
            counts,
        )

    def test_all_cross_type_examples_validate(self) -> None:
        documents, issues = validate([ROOT / "examples"])
        self.assertEqual([], [str(issue) for issue in issues])
        self.assertEqual(30, len(documents))

    def test_council_generation_two_draft_validates(self) -> None:
        path = ROOT / "studies" / "council-generation-2" / "study-manifest.draft.json"
        documents, issues = validate([path])
        self.assertEqual([], [str(issue) for issue in issues])
        self.assertEqual("draft", documents[0].data["status"])

    def test_receipt_render_is_deterministic(self) -> None:
        receipt = json.loads(
            (COUNCIL_EXAMPLE / "evidence-receipt.json").read_text(encoding="utf-8")
        )
        expected = (COUNCIL_EXAMPLE / "evidence-receipt.md").read_text(encoding="utf-8")
        self.assertEqual(expected, render_receipt(receipt))

        calibration = json.loads(
            (CODEX_CALIBRATION / "evidence-receipt.json").read_text(encoding="utf-8")
        )
        calibration_expected = (CODEX_CALIBRATION / "evidence-receipt.md").read_text(
            encoding="utf-8"
        )
        self.assertEqual(calibration_expected, render_receipt(calibration))
        self.assertIn("Receipt evidence state:", calibration_expected)
        self.assertIn("Claim class:", calibration_expected)
        self.assertNotIn("Evidence level:", calibration_expected)
        self.assertNotIn("Claim level:", calibration_expected)

    def test_receipt_content_hashes_resolve(self) -> None:
        receipt = json.loads(
            (COUNCIL_EXAMPLE / "evidence-receipt.json").read_text(encoding="utf-8")
        )
        refs = [
            receipt["concept_ref"],
            receipt["study_ref"],
            receipt["measurement_set_ref"],
            *receipt["run_record_refs"],
        ]
        for reference in refs:
            with self.subTest(uri=reference["uri"]):
                target = COUNCIL_EXAMPLE / reference["uri"]
                self.assertTrue(target.is_file())
                self.assertEqual(reference["sha256"], sha256_path(target))

        calibration = json.loads(
            (CODEX_CALIBRATION / "evidence-receipt.json").read_text(encoding="utf-8")
        )
        calibration_refs = [
            calibration["concept_ref"],
            calibration["study_ref"],
            calibration["measurement_set_ref"],
            *calibration["run_record_refs"],
        ]
        for reference in calibration_refs:
            with self.subTest(uri=reference["uri"]):
                target = CODEX_CALIBRATION / reference["uri"]
                self.assertTrue(target.is_file())
                self.assertEqual(reference["sha256"], sha256_path(target))

    def test_personal_absolute_path_is_rejected(self) -> None:
        concept = json.loads((COUNCIL_EXAMPLE / "concept.json").read_text(encoding="utf-8"))
        concept["idea"] = "/" + "Users/example/private/project"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "concept.json"
            path.write_text(json.dumps(concept), encoding="utf-8")
            _, issues = validate([path])
        self.assertTrue(
            any("personal absolute filesystem paths" in issue.message for issue in issues)
        )

    def test_local_reference_cannot_escape_validation_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "public"
            root.mkdir()
            path = root / "receipt.json"
            path.write_text("{}\n", encoding="utf-8")
            document = Document(path=path, root=root, data={})
            target, issues = _relative_target(document, {"uri": "../private.json"}, "ref")
        self.assertIsNone(target)
        self.assertTrue(any("escapes validation root" in issue.message for issue in issues))

    def test_local_reference_cannot_use_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target_file = root / "target.json"
            target_file.write_text("{}\n", encoding="utf-8")
            linked = root / "linked.json"
            linked.symlink_to(target_file)
            document = Document(path=root / "receipt.json", root=root, data={})
            target, issues = _relative_target(document, {"uri": "linked.json"}, "ref")
        self.assertIsNone(target)
        self.assertTrue(any("must not use symlinks" in issue.message for issue in issues))

    def test_duplicate_json_members_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "duplicate.json"
            path.write_text(
                '{"object_type":"concept","object_type":"run_record"}\n',
                encoding="utf-8",
            )
            _, issues = validate([path])
        self.assertTrue(any("duplicate object member" in issue.message for issue in issues))

    def test_distinct_study_revisions_can_validate_together(self) -> None:
        study = json.loads((COUNCIL_EXAMPLE / "study-manifest.json").read_text(encoding="utf-8"))
        study["status"] = "draft"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            revision_one = root / "study-v1.json"
            revision_two = root / "study-v2.json"
            revision_one.write_text(json.dumps(study), encoding="utf-8")
            study["revision"] = 2
            revision_two.write_text(json.dumps(study), encoding="utf-8")
            documents, issues = validate([revision_one, revision_two])
        self.assertEqual([], [str(issue) for issue in issues])
        self.assertEqual([1, 2], sorted(document.data["revision"] for document in documents))

    def test_duplicate_study_revision_is_rejected(self) -> None:
        study = json.loads((COUNCIL_EXAMPLE / "study-manifest.json").read_text(encoding="utf-8"))
        study["status"] = "draft"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "study-a.json").write_text(json.dumps(study), encoding="utf-8")
            (root / "study-b.json").write_text(json.dumps(study), encoding="utf-8")
            _, issues = validate([root])
        self.assertTrue(any("duplicates" in issue.message for issue in issues))

    def test_run_reference_resolves_exact_study_revision(self) -> None:
        study = json.loads((COUNCIL_EXAMPLE / "study-manifest.json").read_text(encoding="utf-8"))
        run = json.loads((COUNCIL_EXAMPLE / "runs" / "E1-C0.json").read_text(encoding="utf-8"))
        study["status"] = "draft"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            revision_one = root / "study-v1.json"
            revision_two = root / "study-v2.json"
            revision_one.write_text(json.dumps(study), encoding="utf-8")
            study["revision"] = 2
            revision_two.write_text(json.dumps(study), encoding="utf-8")
            run["study_ref"]["revision"] = 2
            run["study_ref"]["uri"] = "study-v1.json"
            run["study_ref"]["sha256"] = sha256_path(revision_one)
            run_path = root / "run.json"
            run_path.write_text(json.dumps(run), encoding="utf-8")
            _, issues = validate([root])
        self.assertTrue(
            any(
                "referenced study revision hash does not match" in issue.message for issue in issues
            )
        )

    def test_nonfinite_json_numbers_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "nonfinite.json"
            path.write_text('{"object_type":"concept","revision":NaN}\n', encoding="utf-8")
            _, issues = validate([path])
        self.assertTrue(any("non-finite JSON number" in issue.message for issue in issues))

    def test_independent_receipt_with_role_overlap_is_rejected(self) -> None:
        receipt = json.loads(
            (COUNCIL_EXAMPLE / "evidence-receipt.json").read_text(encoding="utf-8")
        )
        receipt["independence"]["label"] = "independently_verified"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "receipt.json"
            path.write_text(json.dumps(receipt), encoding="utf-8")
            _, issues = validate([path])
        self.assertTrue(any("cannot declare role overlap" in issue.message for issue in issues))

    def test_operational_stack_cannot_promote_to_model_only_claim(self) -> None:
        study = json.loads((COUNCIL_EXAMPLE / "study-manifest.json").read_text(encoding="utf-8"))
        receipt = json.loads(
            (COUNCIL_EXAMPLE / "evidence-receipt.json").read_text(encoding="utf-8")
        )
        study["comparison_mode"] = "operational_stack"
        receipt["evaluated_claims"][0]["claim_level"] = "model_only"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            study_path = root / "study.json"
            study_path.write_text(json.dumps(study), encoding="utf-8")
            receipt["study_ref"]["uri"] = "study.json"
            receipt["study_ref"]["sha256"] = sha256_path(study_path)
            receipt_path = root / "receipt.json"
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            _, issues = validate([study_path, receipt_path])
        self.assertTrue(any("cannot support model-only" in issue.message for issue in issues))

    def test_evaluative_measurement_cannot_use_invalid_run(self) -> None:
        run = json.loads((COUNCIL_EXAMPLE / "runs" / "E1-C0.json").read_text(encoding="utf-8"))
        measurements = json.loads(
            (COUNCIL_EXAMPLE / "measurement-set.json").read_text(encoding="utf-8")
        )
        run["status"] = "invalid"
        run["invalid_reason"] = "synthetic test"
        measurements["measurements"] = [
            copy.deepcopy(
                next(item for item in measurements["measurements"] if item["kind"] == "subjective")
            )
        ]
        measurements["measurements"][0]["run_ids"] = [run["run_id"]]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_path = root / "run.json"
            measurement_path = root / "measurements.json"
            run_path.write_text(json.dumps(run), encoding="utf-8")
            measurement_path.write_text(json.dumps(measurements), encoding="utf-8")
            _, issues = validate([run_path, measurement_path])
        self.assertTrue(
            any(
                "evaluative measurement references non-valid run" in issue.message
                for issue in issues
            )
        )

    def test_calibration_simulation_is_seed_deterministic(self) -> None:
        config = json.loads(
            (
                ROOT
                / "studies"
                / "council-generation-2"
                / "calibration"
                / "calibration-config.json"
            ).read_text(encoding="utf-8")
        )
        config["iterations"] = 12
        config["screening"]["task_counts"] = [3]
        config["confirmation"]["task_counts"] = [4]
        config["confirmation"]["absolute_effects"] = [0.0, 0.15]
        config["confirmation"]["bootstrap_samples"] = 20
        self.assertEqual(simulate(copy.deepcopy(config)), simulate(copy.deepcopy(config)))

    def test_committed_calibration_artifacts_reproduce(self) -> None:
        root = ROOT / "studies" / "council-generation-2" / "calibration"
        config = json.loads((root / "calibration-config.json").read_text(encoding="utf-8"))
        expected_result = json.loads((root / "calibration-result.json").read_text(encoding="utf-8"))
        result = simulate(config)
        self.assertEqual(expected_result, result)
        self.assertEqual(
            (root / "calibration-report.md").read_text(encoding="utf-8"), render_report(result)
        )

    def test_public_tree_has_no_personal_absolute_paths(self) -> None:
        ignored_parts = {".git", ".venv", "__pycache__"}
        for path in ROOT.rglob("*"):
            if not path.is_file() or ignored_parts.intersection(path.parts):
                continue
            if (ROOT / "reviews" / "private") in path.parents:
                continue
            if (ROOT / "artifacts" / "private") in path.parents:
                continue
            # Public artifacts must not expose personal paths. Python source is
            # excluded because the validator and this test intentionally
            # contain the literal pattern they detect.
            if path.suffix not in {".md", ".json", ".toml"} and path.name not in {
                "uv.lock",
                ".gitignore",
            }:
                continue
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertNotIn("/" + "Users/", path.read_text(encoding="utf-8"))

    def test_relative_markdown_links_resolve(self) -> None:
        ignored_parts = {".git", ".venv", "__pycache__"}
        link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
        failures: list[str] = []
        for path in ROOT.rglob("*.md"):
            if (
                ignored_parts.intersection(path.parts)
                or (ROOT / "reviews" / "private") in path.parents
            ):
                continue
            if (ROOT / "artifacts" / "private") in path.parents:
                continue
            for target in link_pattern.findall(path.read_text(encoding="utf-8")):
                if target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                clean = target.split("#", 1)[0]
                if clean and not (path.parent / clean).resolve().exists():
                    failures.append(f"{path.relative_to(ROOT)} -> {target}")
        self.assertEqual([], failures)


if __name__ == "__main__":
    unittest.main()
