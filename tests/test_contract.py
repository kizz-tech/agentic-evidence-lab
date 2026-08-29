from __future__ import annotations

import copy
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from ael.calibration import render_report, simulate
from ael.contract_graph import validate
from ael.render import render_receipt
from ael.validation import SCHEMA_FILES, Document, _relative_target, _schema, sha256_path

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

    def test_terminal_study_requires_loaded_concept_reference(self) -> None:
        study = json.loads((COUNCIL_EXAMPLE / "study-manifest.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "study.json"
            path.write_text(json.dumps(study), encoding="utf-8")
            _, issues = validate([path])
        self.assertTrue(any(issue.message == "concept was not loaded" for issue in issues))

    def test_receipt_requires_loaded_concept_reference(self) -> None:
        receipt = json.loads(
            (COUNCIL_EXAMPLE / "evidence-receipt.json").read_text(encoding="utf-8")
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "receipt.json"
            path.write_text(json.dumps(receipt), encoding="utf-8")
            _, issues = validate([path])
        self.assertTrue(any(issue.message == "concept was not loaded" for issue in issues))

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

    def test_measurement_run_reference_must_resolve(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "graph"
            shutil.copytree(COUNCIL_EXAMPLE, root)
            measurement_path = root / "measurement-set.json"
            measurements = json.loads(measurement_path.read_text(encoding="utf-8"))
            measurements["measurements"][0]["run_ids"] = ["ghost-run"]
            measurement_path.write_text(json.dumps(measurements), encoding="utf-8")
            _, issues = validate([root / "study-manifest.json", root / "runs", measurement_path])
        self.assertTrue(
            any(
                issue.location == "measurements.0.run_ids"
                and issue.message == "run record was not loaded"
                for issue in issues
            )
        )

    def test_measurement_run_reference_must_match_study(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "graph"
            shutil.copytree(COUNCIL_EXAMPLE, root)
            study_path = root / "study-manifest.json"
            other_study_path = root / "study-other.json"
            other_study = json.loads(study_path.read_text(encoding="utf-8"))
            other_study["status"] = "draft"
            other_study["study_id"] = "kizz:ael:study:other"
            other_study_path.write_text(json.dumps(other_study), encoding="utf-8")

            run_path = root / "runs" / "E1-C0.json"
            run = json.loads(run_path.read_text(encoding="utf-8"))
            run["study_ref"].update(
                {
                    "study_id": other_study["study_id"],
                    "uri": "../study-other.json",
                    "sha256": sha256_path(other_study_path),
                }
            )
            run_path.write_text(json.dumps(run), encoding="utf-8")
            _, issues = validate(
                [study_path, other_study_path, root / "runs", root / "measurement-set.json"]
            )
        self.assertTrue(
            any(
                issue.location == "measurements.4.run_ids"
                and "does not match measurement set study reference" in issue.message
                for issue in issues
            )
        )

    def test_receipt_run_reference_must_match_study(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "graph"
            shutil.copytree(COUNCIL_EXAMPLE, root)
            study_path = root / "study-manifest.json"
            other_study_path = root / "study-other.json"
            other_study = json.loads(study_path.read_text(encoding="utf-8"))
            other_study["status"] = "draft"
            other_study["study_id"] = "kizz:ael:study:other"
            other_study_path.write_text(json.dumps(other_study), encoding="utf-8")

            run_path = root / "runs" / "E1-C0.json"
            run = json.loads(run_path.read_text(encoding="utf-8"))
            run["study_ref"].update(
                {
                    "study_id": other_study["study_id"],
                    "uri": "../study-other.json",
                    "sha256": sha256_path(other_study_path),
                }
            )
            run_path.write_text(json.dumps(run), encoding="utf-8")

            receipt_path = root / "evidence-receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            next(
                reference
                for reference in receipt["run_record_refs"]
                if reference["run_id"] == run["run_id"]
            )["sha256"] = sha256_path(run_path)
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            _, issues = validate([root])
        self.assertTrue(
            any(
                issue.location == "run_record_refs.0.run_id"
                and "does not match receipt study reference" in issue.message
                for issue in issues
            )
        )

    def test_receipt_measurement_set_reference_must_match_study(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "graph"
            shutil.copytree(COUNCIL_EXAMPLE, root)
            study_path = root / "study-manifest.json"
            other_study_path = root / "study-other.json"
            other_study = json.loads(study_path.read_text(encoding="utf-8"))
            other_study["status"] = "draft"
            other_study["study_id"] = "kizz:ael:study:other"
            other_study_path.write_text(json.dumps(other_study), encoding="utf-8")

            measurement_path = root / "measurement-set.json"
            measurements = json.loads(measurement_path.read_text(encoding="utf-8"))
            measurements["study_ref"].update(
                {
                    "study_id": other_study["study_id"],
                    "uri": "study-other.json",
                    "sha256": sha256_path(other_study_path),
                }
            )
            measurement_path.write_text(json.dumps(measurements), encoding="utf-8")

            receipt_path = root / "evidence-receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["measurement_set_ref"]["sha256"] = sha256_path(measurement_path)
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            _, issues = validate([root])
        self.assertTrue(
            any(
                issue.location == "measurement_set_ref"
                and "does not match receipt study reference" in issue.message
                for issue in issues
            )
        )

    def test_receipt_run_reference_uri_must_match_declared_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "graph"
            shutil.copytree(COUNCIL_EXAMPLE, root)
            receipt_path = root / "evidence-receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            swapped_path = root / "runs" / "E1-C1.json"
            receipt["run_record_refs"][0].update(
                {"uri": "runs/E1-C1.json", "sha256": sha256_path(swapped_path)}
            )
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            _, issues = validate([root])
        self.assertTrue(
            any(
                issue.location == "run_record_refs.0.run_id"
                and "reference target identity does not match declared identity" in issue.message
                for issue in issues
            )
        )

    def test_receipt_measurement_set_reference_uri_must_match_declared_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "graph"
            shutil.copytree(COUNCIL_EXAMPLE, root)
            original_path = root / "measurement-set.json"
            swapped_path = root / "measurement-set-other.json"
            swapped = json.loads(original_path.read_text(encoding="utf-8"))
            swapped["measurement_set_id"] = "kizz:ael:measurements:other"
            swapped_path.write_text(json.dumps(swapped), encoding="utf-8")

            receipt_path = root / "evidence-receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["measurement_set_ref"].update(
                {"uri": "measurement-set-other.json", "sha256": sha256_path(swapped_path)}
            )
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            _, issues = validate([root])
        self.assertTrue(
            any(
                issue.location == "measurement_set_ref.measurement_set_id"
                and "reference target identity does not match declared identity" in issue.message
                for issue in issues
            )
        )

    def test_receipt_concept_reference_uri_must_match_declared_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "graph"
            shutil.copytree(COUNCIL_EXAMPLE, root)
            original_path = root / "concept.json"
            swapped_path = root / "concept-other.json"
            swapped = json.loads(original_path.read_text(encoding="utf-8"))
            swapped["concept_id"] = "kizz:ael:concept:other"
            swapped_path.write_text(json.dumps(swapped), encoding="utf-8")

            receipt_path = root / "evidence-receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["concept_ref"].update(
                {"uri": "concept-other.json", "sha256": sha256_path(swapped_path)}
            )
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            _, issues = validate([root])
        self.assertTrue(
            any(
                issue.location == "concept_ref.concept_id"
                and "reference target identity does not match declared identity" in issue.message
                for issue in issues
            )
        )

    def test_study_concept_reference_uri_must_match_declared_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "graph"
            shutil.copytree(COUNCIL_EXAMPLE, root)
            concept_path = root / "concept.json"
            swapped_path = root / "concept-other.json"
            swapped = json.loads(concept_path.read_text(encoding="utf-8"))
            swapped["concept_id"] = "kizz:ael:concept:other"
            swapped_path.write_text(json.dumps(swapped), encoding="utf-8")

            study_path = root / "study-manifest.json"
            study = json.loads(study_path.read_text(encoding="utf-8"))
            study["concept_ref"].update(
                {"uri": "concept-other.json", "sha256": sha256_path(swapped_path)}
            )
            study_path.write_text(json.dumps(study), encoding="utf-8")

            receipt_path = root / "evidence-receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["study_ref"]["sha256"] = sha256_path(study_path)
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            _, issues = validate([root])
        self.assertTrue(
            any(
                issue.location == "concept_ref.concept_id"
                and "reference target identity does not match declared identity" in issue.message
                for issue in issues
            )
        )

    def test_concept_reference_uri_must_match_declared_revision(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "graph"
            shutil.copytree(COUNCIL_EXAMPLE, root)
            concept_path = root / "concept.json"
            revision_path = root / "concept-revision-2.json"
            revision = json.loads(concept_path.read_text(encoding="utf-8"))
            revision["revision"] = 2
            revision_path.write_text(json.dumps(revision), encoding="utf-8")

            receipt_path = root / "evidence-receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["concept_ref"].update(
                {"uri": "concept-revision-2.json", "sha256": sha256_path(revision_path)}
            )
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            _, issues = validate([root])
        self.assertTrue(
            any(
                issue.location == "concept_ref.revision"
                and "reference target revision does not match declared revision" in issue.message
                for issue in issues
            )
        )

    def test_study_concept_reference_uri_must_match_declared_revision(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "graph"
            shutil.copytree(COUNCIL_EXAMPLE, root)
            concept_path = root / "concept.json"
            revision_path = root / "concept-revision-2.json"
            revision = json.loads(concept_path.read_text(encoding="utf-8"))
            revision["revision"] = 2
            revision_path.write_text(json.dumps(revision), encoding="utf-8")

            study_path = root / "study-manifest.json"
            study = json.loads(study_path.read_text(encoding="utf-8"))
            study["concept_ref"].update(
                {"uri": "concept-revision-2.json", "sha256": sha256_path(revision_path)}
            )
            study_path.write_text(json.dumps(study), encoding="utf-8")

            receipt_path = root / "evidence-receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["study_ref"]["sha256"] = sha256_path(study_path)
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            _, issues = validate([root])
        self.assertTrue(
            any(
                issue.location == "concept_ref.revision"
                and "reference target revision does not match declared revision" in issue.message
                for issue in issues
            )
        )

    def test_typed_study_references_must_match_loaded_study(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "graph"
            shutil.copytree(COUNCIL_EXAMPLE, root)
            study_path = root / "study-manifest.json"
            other_study_path = root / "study-other.json"
            other_study = json.loads(study_path.read_text(encoding="utf-8"))
            other_study["status"] = "draft"
            other_study["study_id"] = "kizz:ael:study:other"
            other_study_path.write_text(json.dumps(other_study), encoding="utf-8")
            other_sha = sha256_path(other_study_path)

            run_path = root / "runs" / "E1-C0.json"
            run = json.loads(run_path.read_text(encoding="utf-8"))
            run["study_ref"].update({"uri": "../study-other.json", "sha256": other_sha})
            run_path.write_text(json.dumps(run), encoding="utf-8")

            measurement_path = root / "measurement-set.json"
            measurements = json.loads(measurement_path.read_text(encoding="utf-8"))
            measurements["study_ref"].update({"uri": "study-other.json", "sha256": other_sha})
            measurement_path.write_text(json.dumps(measurements), encoding="utf-8")

            receipt_path = root / "evidence-receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["study_ref"].update({"uri": "study-other.json", "sha256": other_sha})
            next(
                reference
                for reference in receipt["run_record_refs"]
                if reference["run_id"] == run["run_id"]
            )["sha256"] = sha256_path(run_path)
            receipt["measurement_set_ref"]["sha256"] = sha256_path(measurement_path)
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            _, issues = validate([root])
        locations = {
            ("E1-C0.json", "study_ref.study_id"),
            ("measurement-set.json", "study_ref.study_id"),
            ("evidence-receipt.json", "study_ref.study_id"),
        }
        self.assertTrue(
            all(
                any(
                    issue.path.name == name
                    and issue.location == location
                    and "reference target identity does not match declared identity"
                    in issue.message
                    for issue in issues
                )
                for name, location in locations
            )
        )

    def test_critical_failure_run_reference_must_resolve(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "graph"
            shutil.copytree(COUNCIL_EXAMPLE, root)
            measurement_path = root / "measurement-set.json"
            measurements = json.loads(measurement_path.read_text(encoding="utf-8"))
            measurements["critical_failures"] = [
                {
                    "failure_id": "synthetic-missing-run",
                    "severity": "low",
                    "observed": True,
                    "description": "synthetic test",
                    "run_ids": ["ghost-run"],
                    "evidence_refs": [
                        {
                            "uri": "lifeos:labs:synthetic-test",
                            "sha256": "0" * 64,
                            "visibility": "private",
                        }
                    ],
                }
            ]
            measurement_path.write_text(json.dumps(measurements), encoding="utf-8")
            _, issues = validate([root / "study-manifest.json", root / "runs", measurement_path])
        self.assertTrue(
            any(
                issue.location == "critical_failures.0.run_ids"
                and issue.message == "run record was not loaded"
                for issue in issues
            )
        )

    def test_malformed_measurement_run_id_does_not_crash_graph_closure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "graph"
            shutil.copytree(COUNCIL_EXAMPLE, root)
            measurement_path = root / "measurement-set.json"
            measurements = json.loads(measurement_path.read_text(encoding="utf-8"))
            measurements["measurements"][0]["run_ids"] = [{"x": 1}]
            measurement_path.write_text(json.dumps(measurements), encoding="utf-8")
            _, issues = validate([root])
        self.assertTrue(
            any(
                issue.location == "measurements.0.run_ids.0"
                and "is not of type 'string'" in issue.message
                for issue in issues
            )
        )

    def test_receipt_critical_failure_run_reference_must_resolve(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "graph"
            shutil.copytree(COUNCIL_EXAMPLE, root)
            measurement_path = root / "measurement-set.json"
            measurements = json.loads(measurement_path.read_text(encoding="utf-8"))
            measurements["critical_failures"] = [
                {
                    "failure_id": "synthetic-missing-run",
                    "severity": "low",
                    "observed": True,
                    "description": "synthetic test",
                    "run_ids": ["ghost-run"],
                    "evidence_refs": [
                        {
                            "uri": "lifeos:labs:synthetic-test",
                            "sha256": "0" * 64,
                            "visibility": "private",
                        }
                    ],
                }
            ]
            measurement_path.write_text(json.dumps(measurements), encoding="utf-8")
            _, issues = validate([root])
        self.assertTrue(
            any(
                issue.path.name == "evidence-receipt.json"
                and issue.location == "measurement_set_ref.critical_failures.0.run_ids"
                and issue.message == "run record was not loaded"
                for issue in issues
            )
        )

    def test_malformed_critical_failure_run_id_does_not_crash_graph_closure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "graph"
            shutil.copytree(COUNCIL_EXAMPLE, root)
            measurement_path = root / "measurement-set.json"
            measurements = json.loads(measurement_path.read_text(encoding="utf-8"))
            measurements["critical_failures"] = [
                {
                    "failure_id": "synthetic-malformed-run",
                    "severity": "low",
                    "observed": True,
                    "description": "synthetic test",
                    "run_ids": [{"x": 1}],
                    "evidence_refs": [
                        {
                            "uri": "lifeos:labs:synthetic-test",
                            "sha256": "0" * 64,
                            "visibility": "private",
                        }
                    ],
                }
            ]
            measurement_path.write_text(json.dumps(measurements), encoding="utf-8")
            _, issues = validate([root])
        self.assertTrue(
            any(
                issue.location == "critical_failures.0.run_ids.0"
                and "is not of type 'string'" in issue.message
                for issue in issues
            )
        )

    def test_malformed_run_id_containers_do_not_crash_graph_closure(self) -> None:
        mutations = [
            ("measurement", 7, "measurements.0.run_ids"),
            ("measurement", {"x": 1}, "measurements.0.run_ids"),
            ("critical", 7, "critical_failures.0.run_ids"),
            ("critical", {"x": 1}, "critical_failures.0.run_ids"),
        ]
        for kind, malformed, location in mutations:
            with self.subTest(kind=kind, malformed=malformed):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary) / "graph"
                    shutil.copytree(COUNCIL_EXAMPLE, root)
                    measurement_path = root / "measurement-set.json"
                    measurements = json.loads(measurement_path.read_text(encoding="utf-8"))
                    if kind == "measurement":
                        measurements["measurements"][0]["run_ids"] = malformed
                    else:
                        measurements["critical_failures"] = [
                            {
                                "failure_id": "synthetic-malformed-run",
                                "severity": "low",
                                "observed": True,
                                "description": "synthetic test",
                                "run_ids": malformed,
                                "evidence_refs": [
                                    {
                                        "uri": "lifeos:labs:synthetic-test",
                                        "sha256": "0" * 64,
                                        "visibility": "private",
                                    }
                                ],
                            }
                        ]
                    measurement_path.write_text(json.dumps(measurements), encoding="utf-8")
                    _, issues = validate([root])
                self.assertTrue(any(issue.location == location for issue in issues))

    def test_critical_failure_run_reference_must_match_receipt_study(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "graph"
            shutil.copytree(COUNCIL_EXAMPLE, root)
            study_path = root / "study-manifest.json"
            other_study_path = root / "study-other.json"
            other_study = json.loads(study_path.read_text(encoding="utf-8"))
            other_study["status"] = "draft"
            other_study["study_id"] = "kizz:ael:study:other"
            other_study_path.write_text(json.dumps(other_study), encoding="utf-8")

            run_path = root / "runs" / "E1-C0.json"
            run = json.loads(run_path.read_text(encoding="utf-8"))
            run["study_ref"].update(
                {
                    "study_id": other_study["study_id"],
                    "uri": "../study-other.json",
                    "sha256": sha256_path(other_study_path),
                }
            )
            run_path.write_text(json.dumps(run), encoding="utf-8")

            measurement_path = root / "measurement-set.json"
            measurements = json.loads(measurement_path.read_text(encoding="utf-8"))
            measurements["critical_failures"] = [
                {
                    "failure_id": "synthetic-cross-study-run",
                    "severity": "low",
                    "observed": True,
                    "description": "synthetic test",
                    "run_ids": [run["run_id"]],
                    "evidence_refs": [
                        {
                            "uri": "lifeos:labs:synthetic-test",
                            "sha256": "0" * 64,
                            "visibility": "private",
                        }
                    ],
                }
            ]
            measurement_path.write_text(json.dumps(measurements), encoding="utf-8")

            receipt_path = root / "evidence-receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            next(
                reference
                for reference in receipt["run_record_refs"]
                if reference["run_id"] == run["run_id"]
            )["sha256"] = sha256_path(run_path)
            receipt["measurement_set_ref"]["sha256"] = sha256_path(measurement_path)
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            _, issues = validate([root])
        self.assertTrue(
            any(
                issue.location == "measurement_set_ref.critical_failures.0.run_ids"
                and "does not match receipt study reference" in issue.message
                for issue in issues
            )
        )

    def test_receipt_run_references_cover_measurement_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "graph"
            shutil.copytree(COUNCIL_EXAMPLE, root)
            receipt_path = root / "evidence-receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["run_record_refs"] = receipt["run_record_refs"][1:]
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            _, issues = validate([root])
        self.assertTrue(
            any(
                issue.location == "run_record_refs"
                and "not included in receipt run_record_refs" in issue.message
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
