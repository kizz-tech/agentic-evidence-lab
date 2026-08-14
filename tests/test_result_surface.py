from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from ael.result_surface import (
    ResultSurfaceError,
    build_result_surface,
    load_public_profile,
    materialize_result_surface,
    validate_public_profile,
)

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "studies" / "public-results.json"
EXAMPLE = ROOT / "examples" / "council-generation-1"
QUALITY_EXAMPLE = ROOT / "studies" / "quality-preflight" / "examples" / "pass"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _root_relative(path: Path, root: Path) -> str:
    return os.path.relpath(path, root)


class ResultSurfaceTests(unittest.TestCase):
    def _temporary_directory(self) -> tempfile.TemporaryDirectory[str]:
        # macOS exposes /tmp as a symlink.  The projection intentionally
        # rejects symlinked parents, so place fixture roots under the physical
        # temporary directory when it is available.
        directory = "/private/tmp" if Path("/private/tmp").is_dir() else None
        return tempfile.TemporaryDirectory(dir=directory)

    def _profile_tree(self, temporary: str) -> tuple[Path, dict[str, object], Path]:
        root = Path(temporary)
        (root / "pyproject.toml").write_text(
            "[project]\nname='result-surface-test'\n", encoding="utf-8"
        )
        example = root / "examples" / "council-generation-1"
        shutil.copytree(EXAMPLE, example)
        receipt = example / "evidence-receipt.json"
        profile: dict[str, object] = {
            "schema_version": "ael.public-results/0.5",
            "as_of": "2026-08-12",
            "projection_policy": "ael.publication-projection/0.5",
            "studies": [
                {
                    "card_id": "council-generation-1",
                    "title": "Council Generation 1",
                    "receipt_ref": {
                        "uri": _root_relative(receipt, root),
                        "sha256": _sha256(receipt),
                    },
                    "claim_ids": ["AEL-CG1-01", "AEL-CG1-05"],
                    "decision_claim_ids": ["AEL-CG1-01"],
                    "verification": {
                        "kind": "evidence_graph",
                        "command": ["uv run ael validate examples/council-generation-1"],
                        "boundary": "Validates the published Contract v0 graph only.",
                    },
                    "materials": [],
                    "history": {
                        "admission": "not_declared_historical",
                        "action": "not_declared_historical",
                        "outcome_follow_up": "not_declared_historical",
                        "freshness": "unassessed",
                    },
                    "quality": {"assessment": "not_assessed_historical"},
                    "catalog_state": "listed",
                    "maintainer_rerun": {
                        "status": "not_assessed",
                        "boundary": "No maintainer rerun package is asserted.",
                    },
                }
            ],
        }
        profile_path = root / "studies" / "public-results.json"
        profile_path.parent.mkdir(parents=True)
        profile_path.write_text(json.dumps(profile, indent=2), encoding="utf-8")
        return profile_path, profile, receipt

    def test_current_four_card_projection_is_deterministic(self) -> None:
        first = build_result_surface(PROFILE)
        second = build_result_surface(PROFILE)
        self.assertEqual(first, second)
        self.assertEqual(
            {
                "RESULTS.md",
                "docs/results/index.json",
                "docs/results/council-generation-1.md",
                "docs/results/focused-change-verification-calibration.md",
                "docs/results/property-based-testing-v2.md",
                "docs/results/systematic-debugging-real-shadow-v1.md",
            },
            set(first),
        )
        index = json.loads(first["docs/results/index.json"])
        profile_entries = {
            entry["card_id"]: entry for entry in load_public_profile(PROFILE)["studies"]
        }
        self.assertEqual("ael.public-results/0.5", index["schema_version"])
        self.assertEqual(
            [
                "council-generation-1",
                "focused-change-verification-calibration",
                "property-based-testing-v2",
                "systematic-debugging-real-shadow-v1",
            ],
            [card["card_id"] for card in index["studies"]],
        )
        self.assertIn("Catalog state", first["docs/results/council-generation-1.md"])
        council_markdown = first["docs/results/council-generation-1.md"]
        self.assertLess(
            council_markdown.index("## Decision"),
            council_markdown.index("## Decision-governing claims"),
        )
        self.assertLess(
            council_markdown.index("## Decision-governing claims"),
            council_markdown.index("## Technical evidence"),
        )
        self.assertIn("## Additional selected claims", council_markdown)
        self.assertIn("Evidence references:", council_markdown)
        self.assertIn("`heldout-mean-score:C1`", council_markdown)
        self.assertNotIn("- Evidence level:", council_markdown)
        self.assertIn("Receipt evidence state: `controlled_effect_observed`", council_markdown)
        self.assertIn("`planned_reliability_coverage`", council_markdown)
        self.assertNotIn("| Evidence |", first["RESULTS.md"])
        self.assertIn("1 valid run / retained cell", first["RESULTS.md"])
        self.assertIn("1 contradicted", first["RESULTS.md"])
        self.assertNotIn("single_valid_observation_per_retained_cell", first["RESULTS.md"])
        self.assertNotIn(
            "Reproducibility: `rerunnable`",
            first["docs/results/council-generation-1.md"],
        )
        self.assertIn("not_declared_historical", first["docs/results/property-based-testing-v2.md"])
        self.assertIn("not_assessed_historical", first["docs/results/property-based-testing-v2.md"])
        for card in index["studies"]:
            self.assertEqual("not_assessed_historical", card["quality"]["status"])
            self.assertEqual(
                {"not_assessed_historical"}, set(card["quality"]["quality_axes"].values())
            )
            self.assertEqual(
                "single_valid_observation_per_retained_cell",
                card["runs"]["repeat_evidence"]["status"],
            )
            self.assertEqual("not_reported", card["measurements"]["uncertainty"]["status"])
            sources = card["source_hashes"]
            self.assertEqual(card["receipt"]["sha256"], sources[card["receipt"]["uri"]])
            if "report" in card:
                self.assertEqual(card["report"]["sha256"], sources[card["report"]["uri"]])
            for material in card["materials"]:
                if material["availability"] == "public":
                    self.assertEqual(material["ref"]["sha256"], sources[material["ref"]["uri"]])
            for claim in card["claims"]:
                for binding in claim["evidence_bindings"]:
                    if binding["binding"] == "public_sidecar":
                        self.assertEqual(binding["sha256"], sources[binding["uri"]])
            verification = profile_entries[card["card_id"]]["verification"]
            if verification["kind"] == "frozen_public_bundle":
                freeze_ref = verification["freeze_ref"]
                self.assertEqual(freeze_ref["sha256"], sources[freeze_ref["uri"]])
        focused = next(
            card
            for card in index["studies"]
            if card["card_id"] == "focused-change-verification-calibration"
        )
        totals = {
            (summary["metric"], summary["condition_id"]): summary["total"]
            for summary in focused["measurements"]["selected_summaries"]
            if "total" in summary
        }
        self.assertEqual(20256, totals[("generated_work_tokens", "S0")])
        self.assertEqual(21944, totals[("generated_work_tokens", "S1")])
        self.assertEqual(331689, totals[("wall_time", "S0")])
        self.assertEqual(378385, totals[("wall_time", "S1")])
        pbt = next(
            card for card in index["studies"] if card["card_id"] == "property-based-testing-v2"
        )
        self.assertIn(
            "studies/agent-skills-season-1/results/property-based-testing-v2/decision.json",
            pbt["source_hashes"],
        )
        self.assertIn(
            "studies/agent-skills-season-1/results/property-based-testing-v2/freeze-ref.json",
            pbt["source_hashes"],
        )
        real_shadow = next(
            card
            for card in index["studies"]
            if card["card_id"] == "systematic-debugging-real-shadow-v1"
        )
        self.assertEqual("admitted", real_shadow["history"]["admission"])
        self.assertEqual("verified", real_shadow["history"]["action"])
        self.assertEqual("scheduled:not_due", real_shadow["history"]["outcome_follow_up"])
        self.assertEqual("within_declared_window", real_shadow["history"]["freshness"])
        self.assertEqual("reject_exact_version", real_shadow["lifecycle"]["adoption_disposition"])
        self.assertEqual("listed", real_shadow["catalog_state"])
        self.assertEqual("rerunnable", real_shadow["receipt_reproducibility"])
        self.assertEqual(
            "decision_recomputable",
            real_shadow["reproduction"]["public_graph_verification"]["status"],
        )
        self.assertEqual(
            "maintainer_only_new_observation",
            real_shadow["reproduction"]["study_rerun"]["status"],
        )
        self.assertEqual(
            "none_linked",
            real_shadow["reproduction"]["independent_replication"]["status"],
        )
        self.assertIn(
            "projection repair",
            " ".join(real_shadow["limitations"]),
        )
        self.assertIn(
            "studies/agent-skills-season-1/results/systematic-debugging-real-shadow-v1/effect-decision.json",
            real_shadow["source_hashes"],
        )
        real_shadow_markdown = first["docs/results/systematic-debugging-real-shadow-v1.md"]
        self.assertLess(
            real_shadow_markdown.index("## Decision"),
            real_shadow_markdown.index("Audit status: `passed`."),
        )

    def test_profile_unknown_keys_and_historical_values_fail_closed(self) -> None:
        profile = load_public_profile(PROFILE)
        unknown = copy.deepcopy(profile)
        unknown["unexpected"] = True
        with self.assertRaisesRegex(ResultSurfaceError, "unknown key"):
            validate_public_profile(unknown)

        invalid_history = copy.deepcopy(profile)
        invalid_history["studies"][0]["history"]["action"] = "completed"  # type: ignore[index]
        with self.assertRaisesRegex(
            ResultSurfaceError, "derived_from_lifecycle|not_declared_historical"
        ):
            validate_public_profile(invalid_history)

        invalid_catalog = copy.deepcopy(profile)
        invalid_catalog["studies"][0]["catalog_state"] = "published"  # type: ignore[index]
        with self.assertRaisesRegex(ResultSurfaceError, "catalog_state"):
            validate_public_profile(invalid_catalog)

        invalid_rerun = copy.deepcopy(profile)
        invalid_rerun["studies"][0]["maintainer_rerun"]["status"] = "public"  # type: ignore[index]
        with self.assertRaisesRegex(ResultSurfaceError, "maintainer_rerun.status"):
            validate_public_profile(invalid_rerun)

        missing_rerun = copy.deepcopy(profile)
        del missing_rerun["studies"][0]["maintainer_rerun"]  # type: ignore[index]
        with self.assertRaisesRegex(ResultSurfaceError, "missing required key"):
            validate_public_profile(missing_rerun)

        missing_quality = copy.deepcopy(profile)
        del missing_quality["studies"][0]["quality"]  # type: ignore[index]
        with self.assertRaisesRegex(ResultSurfaceError, "missing required key"):
            validate_public_profile(missing_quality)

        malformed_quality = copy.deepcopy(profile)
        malformed_quality["studies"][0]["quality"] = {  # type: ignore[index]
            "assessment": "profiled"
        }
        with self.assertRaisesRegex(ResultSurfaceError, "profile_ref"):
            validate_public_profile(malformed_quality)

    def test_duplicate_cards_and_claims_are_rejected(self) -> None:
        profile = load_public_profile(PROFILE)
        duplicate_cards = copy.deepcopy(profile)
        duplicate_cards["studies"].append(copy.deepcopy(duplicate_cards["studies"][0]))  # type: ignore[index]
        with self.assertRaisesRegex(ResultSurfaceError, "duplicate card_id"):
            validate_public_profile(duplicate_cards)

        duplicate_claims = copy.deepcopy(profile)
        duplicate_claims["studies"][0]["claim_ids"] = ["AEL-CG1-01", "AEL-CG1-01"]  # type: ignore[index]
        with self.assertRaisesRegex(ResultSurfaceError, "unique claim"):
            validate_public_profile(duplicate_claims)

        unrelated_decision_claim = copy.deepcopy(profile)
        unrelated_decision_claim["studies"][0]["decision_claim_ids"] = ["not-selected"]  # type: ignore[index]
        with self.assertRaisesRegex(ResultSurfaceError, "must be a subset"):
            validate_public_profile(unrelated_decision_claim)

    def test_bad_receipt_hash_is_rejected(self) -> None:
        with self._temporary_directory() as temporary:
            profile_path, profile, _receipt = self._profile_tree(temporary)
            profile["studies"][0]["receipt_ref"]["sha256"] = "0" * 64  # type: ignore[index]
            profile_path.write_text(json.dumps(profile), encoding="utf-8")
            with self.assertRaisesRegex(ResultSurfaceError, "sha256 does not match"):
                build_result_surface(profile_path, Path(temporary))

    def test_selected_claim_references_are_classified_and_path_safe(self) -> None:
        with self._temporary_directory() as temporary:
            profile_path, profile, receipt = self._profile_tree(temporary)
            receipt_data = json.loads(receipt.read_text(encoding="utf-8"))
            claim = next(
                item
                for item in receipt_data["evaluated_claims"]
                if item["claim_id"] == "AEL-CG1-05"
            )
            claim["evidence_refs"] = [
                "logical-observation-id",
                "candidate-profile-id-omission:E7-C3",
            ]
            receipt.write_text(json.dumps(receipt_data), encoding="utf-8")
            profile["studies"][0]["receipt_ref"]["sha256"] = _sha256(receipt)  # type: ignore[index]
            profile["studies"][0]["claim_ids"] = ["AEL-CG1-05"]  # type: ignore[index]
            profile["studies"][0]["decision_claim_ids"] = ["AEL-CG1-05"]  # type: ignore[index]
            profile_path.write_text(json.dumps(profile), encoding="utf-8")
            outputs = build_result_surface(profile_path, Path(temporary))
            index = json.loads(outputs["docs/results/index.json"])
            binding = index["studies"][0]["claims"][0]["evidence_bindings"][0]
            self.assertEqual("opaque_receipt_reference", binding["binding"])

        with self._temporary_directory() as temporary:
            profile_path, profile, receipt = self._profile_tree(temporary)
            receipt_data = json.loads(receipt.read_text(encoding="utf-8"))
            claim = next(
                item
                for item in receipt_data["evaluated_claims"]
                if item["claim_id"] == "AEL-CG1-05"
            )
            claim["evidence_refs"] = ["../outside.json"]
            receipt.write_text(json.dumps(receipt_data), encoding="utf-8")
            profile["studies"][0]["receipt_ref"]["sha256"] = _sha256(receipt)  # type: ignore[index]
            profile["studies"][0]["claim_ids"] = ["AEL-CG1-05"]  # type: ignore[index]
            profile["studies"][0]["decision_claim_ids"] = ["AEL-CG1-05"]  # type: ignore[index]
            profile_path.write_text(json.dumps(profile), encoding="utf-8")
            with self.assertRaisesRegex(ResultSurfaceError, "contains traversal"):
                build_result_surface(profile_path, Path(temporary))

        with self._temporary_directory() as temporary:
            profile_path, profile, receipt = self._profile_tree(temporary)
            sidecar = receipt.parent / "linked-sidecar.json"
            sidecar.symlink_to(receipt)
            receipt_data = json.loads(receipt.read_text(encoding="utf-8"))
            claim = next(
                item
                for item in receipt_data["evaluated_claims"]
                if item["claim_id"] == "AEL-CG1-05"
            )
            claim["evidence_refs"] = [sidecar.name]
            receipt.write_text(json.dumps(receipt_data), encoding="utf-8")
            profile["studies"][0]["receipt_ref"]["sha256"] = _sha256(receipt)  # type: ignore[index]
            profile["studies"][0]["claim_ids"] = ["AEL-CG1-05"]  # type: ignore[index]
            profile["studies"][0]["decision_claim_ids"] = ["AEL-CG1-05"]  # type: ignore[index]
            profile_path.write_text(json.dumps(profile), encoding="utf-8")
            with self.assertRaisesRegex(ResultSurfaceError, "must not use symlinks"):
                build_result_surface(profile_path, Path(temporary))

    def test_overflow_json_number_is_rejected(self) -> None:
        with self._temporary_directory() as temporary:
            profile_path, _profile, _receipt = self._profile_tree(temporary)
            profile_path.write_text('{"overflow": 1e400}', encoding="utf-8")
            with self.assertRaisesRegex(ResultSurfaceError, "non-finite JSON number"):
                load_public_profile(profile_path)

    def test_claim_support_is_explicit_not_ordinal(self) -> None:
        with self._temporary_directory() as temporary:
            profile_path, profile, receipt = self._profile_tree(temporary)
            receipt_data = json.loads(receipt.read_text(encoding="utf-8"))
            receipt_data["evaluated_claims"][0]["claim_level"] = "outcome"
            receipt.write_text(json.dumps(receipt_data), encoding="utf-8")
            profile["studies"][0]["receipt_ref"]["sha256"] = _sha256(receipt)  # type: ignore[index]
            profile["studies"][0]["claim_ids"] = ["AEL-CG1-01"]  # type: ignore[index]
            profile_path.write_text(json.dumps(profile), encoding="utf-8")
            with self.assertRaisesRegex(ResultSurfaceError, "requires its own support predicate"):
                build_result_surface(profile_path, Path(temporary))

        with self._temporary_directory() as temporary:
            profile_path, profile, receipt = self._profile_tree(temporary)
            receipt_data = json.loads(receipt.read_text(encoding="utf-8"))
            receipt_data["evidence_level"] = "externally_decision_changing"
            receipt_data["evaluated_claims"][0]["claim_level"] = "transfer"
            receipt.write_text(json.dumps(receipt_data), encoding="utf-8")
            profile["studies"][0]["receipt_ref"]["sha256"] = _sha256(receipt)  # type: ignore[index]
            profile["studies"][0]["claim_ids"] = ["AEL-CG1-01"]  # type: ignore[index]
            profile_path.write_text(json.dumps(profile), encoding="utf-8")
            with self.assertRaisesRegex(ResultSurfaceError, "requires its own support predicate"):
                build_result_surface(profile_path, Path(temporary))

        with self._temporary_directory() as temporary:
            profile_path, profile, receipt = self._profile_tree(temporary)
            receipt_data = json.loads(receipt.read_text(encoding="utf-8"))
            receipt_data["evidence_level"] = "paid_repeated_use"
            receipt_data["evaluated_claims"][0]["claim_level"] = "outcome"
            receipt.write_text(json.dumps(receipt_data), encoding="utf-8")
            profile["studies"][0]["receipt_ref"]["sha256"] = _sha256(receipt)  # type: ignore[index]
            profile["studies"][0]["claim_ids"] = ["AEL-CG1-01"]  # type: ignore[index]
            profile_path.write_text(json.dumps(profile), encoding="utf-8")
            with self.assertRaisesRegex(ResultSurfaceError, "requires its own support predicate"):
                build_result_surface(profile_path, Path(temporary))

        with self._temporary_directory() as temporary:
            profile_path, profile, receipt = self._profile_tree(temporary)
            receipt_data = json.loads(receipt.read_text(encoding="utf-8"))
            receipt_data["evidence_level"] = "downstream_outcome_observed"
            receipt_data["evaluated_claims"][0]["claim_level"] = "factor_causal"
            receipt.write_text(json.dumps(receipt_data), encoding="utf-8")
            profile["studies"][0]["receipt_ref"]["sha256"] = _sha256(receipt)  # type: ignore[index]
            profile["studies"][0]["claim_ids"] = ["AEL-CG1-01"]  # type: ignore[index]
            profile_path.write_text(json.dumps(profile), encoding="utf-8")
            with self.assertRaisesRegex(ResultSurfaceError, "requires its own support predicate"):
                build_result_surface(profile_path, Path(temporary))

        with self._temporary_directory() as temporary:
            profile_path, profile, receipt = self._profile_tree(temporary)
            receipt_data = json.loads(receipt.read_text(encoding="utf-8"))
            receipt_data["evidence_level"] = "downstream_outcome_observed"
            receipt_data["evaluated_claims"][0]["claim_level"] = "outcome"
            receipt_data["evaluated_claims"][0]["evidence_refs"] = ["outcome-test"]
            measurement_path = receipt.parent / receipt_data["measurement_set_ref"]["uri"]
            measurement_data = json.loads(measurement_path.read_text(encoding="utf-8"))
            outcome_measurement = copy.deepcopy(measurement_data["measurements"][0])
            outcome_measurement["measurement_id"] = "outcome-test"
            outcome_measurement["kind"] = "outcome"
            measurement_data["measurements"].append(outcome_measurement)
            measurement_path.write_text(json.dumps(measurement_data), encoding="utf-8")
            receipt_data["measurement_set_ref"]["sha256"] = _sha256(measurement_path)
            receipt.write_text(json.dumps(receipt_data), encoding="utf-8")
            profile["studies"][0]["receipt_ref"]["sha256"] = _sha256(receipt)  # type: ignore[index]
            profile["studies"][0]["claim_ids"] = ["AEL-CG1-01"]  # type: ignore[index]
            profile_path.write_text(json.dumps(profile), encoding="utf-8")
            outputs = build_result_surface(profile_path, Path(temporary))
            self.assertIn("Claim class: `outcome`", outputs["docs/results/council-generation-1.md"])

        with self._temporary_directory() as temporary:
            profile_path, profile, receipt = self._profile_tree(temporary)
            receipt_data = json.loads(receipt.read_text(encoding="utf-8"))
            receipt_data["evidence_level"] = "transferred"
            receipt_data["evaluated_claims"][0]["claim_level"] = "transfer"
            receipt.write_text(json.dumps(receipt_data), encoding="utf-8")
            profile["studies"][0]["receipt_ref"]["sha256"] = _sha256(receipt)  # type: ignore[index]
            profile["studies"][0]["claim_ids"] = ["AEL-CG1-01"]  # type: ignore[index]
            profile_path.write_text(json.dumps(profile), encoding="utf-8")
            with self.assertRaisesRegex(ResultSurfaceError, "bound to a transfer task pack"):
                build_result_surface(profile_path, Path(temporary))

        with self._temporary_directory() as temporary:
            profile_path, profile, receipt = self._profile_tree(temporary)
            receipt_data = json.loads(receipt.read_text(encoding="utf-8"))
            receipt_data["evidence_level"] = "independently_outcome_verified"
            receipt_data["evaluated_claims"][0]["claim_level"] = "outcome"
            receipt.write_text(json.dumps(receipt_data), encoding="utf-8")
            profile["studies"][0]["receipt_ref"]["sha256"] = _sha256(receipt)  # type: ignore[index]
            profile["studies"][0]["claim_ids"] = ["AEL-CG1-01"]  # type: ignore[index]
            profile_path.write_text(json.dumps(profile), encoding="utf-8")
            with self.assertRaisesRegex(ResultSurfaceError, "independence is maintainer_evaluated"):
                build_result_surface(profile_path, Path(temporary))

        with self._temporary_directory() as temporary:
            profile_path, profile, receipt = self._profile_tree(temporary)
            receipt_data = json.loads(receipt.read_text(encoding="utf-8"))
            additional_claim = next(
                claim
                for claim in receipt_data["evaluated_claims"]
                if claim["claim_id"] == "AEL-CG1-05"
            )
            additional_claim["claim_level"] = "factor_causal"
            receipt.write_text(json.dumps(receipt_data), encoding="utf-8")
            profile["studies"][0]["receipt_ref"]["sha256"] = _sha256(receipt)  # type: ignore[index]
            profile_path.write_text(json.dumps(profile), encoding="utf-8")
            with self.assertRaisesRegex(ResultSurfaceError, "must be an artifact or workflow"):
                build_result_surface(profile_path, Path(temporary))

    def test_profiled_quality_is_hash_bound_and_study_bound(self) -> None:
        with self._temporary_directory() as temporary:
            profile_path, profile, receipt = self._profile_tree(temporary)
            root = Path(temporary)
            example = root / "examples" / "council-generation-1"
            manifest = example / "study-manifest.json"
            manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
            manifest_data["status"] = "frozen"
            manifest.write_text(json.dumps(manifest_data, indent=2) + "\n", encoding="utf-8")
            manifest_digest = _sha256(manifest)

            receipt_data = json.loads(receipt.read_text(encoding="utf-8"))
            receipt_data["study_ref"]["sha256"] = manifest_digest
            for run_ref in receipt_data["run_record_refs"]:
                run_path = example / run_ref["uri"]
                run = json.loads(run_path.read_text(encoding="utf-8"))
                run["study_ref"]["sha256"] = manifest_digest
                run_path.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
                run_ref["sha256"] = _sha256(run_path)
            measurement_path = example / receipt_data["measurement_set_ref"]["uri"]
            measurement = json.loads(measurement_path.read_text(encoding="utf-8"))
            measurement["study_ref"]["sha256"] = manifest_digest
            measurement_path.write_text(json.dumps(measurement, indent=2) + "\n", encoding="utf-8")
            receipt_data["measurement_set_ref"]["sha256"] = _sha256(measurement_path)
            receipt.write_text(json.dumps(receipt_data, indent=2) + "\n", encoding="utf-8")
            profile["studies"][0]["receipt_ref"]["sha256"] = _sha256(receipt)  # type: ignore[index]

            for filename in ("task-provenance.md", "task-audit.md", "evaluator-calibration.md"):
                shutil.copy2(QUALITY_EXAMPLE / filename, example / filename)
            quality = json.loads((QUALITY_EXAMPLE / "quality-profile.json").read_text())
            quality["profile_id"] = "kizz:ael:quality-profile:council-test:1"
            quality["study_ref"] = {
                "study_id": manifest_data["study_id"],
                "revision": manifest_data["revision"],
                "uri": "study-manifest.json",
                "sha256": manifest_digest,
            }
            quality_path = example / "quality-profile.json"
            quality_path.write_text(json.dumps(quality, indent=2) + "\n", encoding="utf-8")
            profile["studies"][0]["quality"] = {  # type: ignore[index]
                "assessment": "profiled",
                "profile_ref": {
                    "uri": _root_relative(quality_path, root),
                    "sha256": _sha256(quality_path),
                },
            }
            profile["as_of"] = "2026-08-14"
            profile_path.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")

            outputs = build_result_surface(profile_path, root)
            index = json.loads(outputs["docs/results/index.json"])
            projected = index["studies"][0]["quality"]
            self.assertEqual("conformant_with_warnings", projected["status"])
            self.assertEqual("controlled_pilot", projected["quality_axes"]["design_class"])
            self.assertEqual(
                _root_relative(quality_path, root),
                projected["profile"]["uri"],
            )
            self.assertIn(_root_relative(quality_path, root), index["studies"][0]["source_hashes"])

    def test_traversal_symlink_and_special_file_references_fail(self) -> None:
        with self._temporary_directory() as temporary:
            profile_path, profile, receipt = self._profile_tree(temporary)
            profile["studies"][0]["receipt_ref"]["uri"] = "../outside.json"  # type: ignore[index]
            profile_path.write_text(json.dumps(profile), encoding="utf-8")
            with self.assertRaisesRegex(ResultSurfaceError, "escapes repository root"):
                build_result_surface(profile_path, Path(temporary))

        with self._temporary_directory() as temporary:
            profile_path, profile, receipt = self._profile_tree(temporary)
            linked = Path(temporary) / "linked-receipt.json"
            linked.symlink_to(receipt)
            profile["studies"][0]["receipt_ref"] = {
                "uri": "linked-receipt.json",
                "sha256": _sha256(receipt),
            }
            profile_path.write_text(json.dumps(profile), encoding="utf-8")
            with self.assertRaisesRegex(ResultSurfaceError, "symlink"):
                build_result_surface(profile_path, Path(temporary))

        with self._temporary_directory() as temporary:
            profile_path, profile, _receipt = self._profile_tree(temporary)
            directory = Path(temporary) / "directory"
            directory.mkdir()
            profile["studies"][0]["receipt_ref"] = {"uri": "directory", "sha256": "0" * 64}  # type: ignore[index]
            profile_path.write_text(json.dumps(profile), encoding="utf-8")
            with self.assertRaisesRegex(ResultSurfaceError, "regular file"):
                build_result_surface(profile_path, Path(temporary))

    def test_material_rules_are_typed_and_nonpublic_material_is_not_dereferenced(self) -> None:
        profile = load_public_profile(PROFILE)
        public_without_ref = copy.deepcopy(profile)
        public_without_ref["studies"][0]["materials"] = [{"label": "x", "availability": "public"}]  # type: ignore[index]
        with self.assertRaisesRegex(ResultSurfaceError, "requires ref"):
            validate_public_profile(public_without_ref)

        nonpublic_with_ref = copy.deepcopy(profile)
        nonpublic_with_ref["studies"][0]["materials"] = [  # type: ignore[index]
            {
                "label": "private",
                "availability": "withheld",
                "ref": {"uri": "../../secret", "sha256": "0" * 64},
                "reason": "private",
                "reproduction_impact": "not replayable",
            }
        ]
        with self.assertRaisesRegex(ResultSurfaceError, "must not include ref"):
            validate_public_profile(nonpublic_with_ref)

        with self._temporary_directory() as temporary:
            profile_path, profile, _receipt = self._profile_tree(temporary)
            profile["studies"][0]["materials"] = [  # type: ignore[index]
                {
                    "label": "withheld task bytes",
                    "availability": "withheld",
                    "reason": "retained outside the repository",
                    "reproduction_impact": "exact tasks cannot be rerun",
                }
            ]
            profile_path.write_text(json.dumps(profile), encoding="utf-8")
            outputs = build_result_surface(profile_path, Path(temporary))
            self.assertIn("withheld task bytes", outputs["docs/results/council-generation-1.md"])

    def test_materialize_and_check_are_safe_and_deterministic(self) -> None:
        with self._temporary_directory() as temporary:
            profile_path, _profile, _receipt = self._profile_tree(temporary)
            root = Path(temporary)
            materialized = materialize_result_surface(profile_path, root)
            self.assertEqual("materialized", materialized["status"])
            checked = materialize_result_surface(profile_path, root, check=True)
            self.assertEqual("checked", checked["status"])
            self.assertFalse(checked["materialized"])
            self.assertEqual(materialized["outputs"], checked["outputs"])
            self.assertEqual(
                materialized["outputs"]["RESULTS.md"],
                _sha256(root / "RESULTS.md"),
            )
            self.assertEqual(0o644, (root / "RESULTS.md").stat().st_mode & 0o777)

            stale = root / "docs" / "results" / "stale-card.md"
            stale.write_text("old projection\n", encoding="utf-8")
            with self.assertRaisesRegex(ResultSurfaceError, "stale output"):
                materialize_result_surface(profile_path, root, check=True)


if __name__ == "__main__":
    unittest.main()
