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
            "schema_version": "ael.public-results/0.1",
            "as_of": "2026-08-12",
            "projection_policy": "ael.publication-projection/0.1",
            "studies": [
                {
                    "card_id": "council-generation-1",
                    "title": "Council Generation 1",
                    "receipt_ref": {
                        "uri": _root_relative(receipt, root),
                        "sha256": _sha256(receipt),
                    },
                    "claim_ids": ["AEL-CG1-01", "AEL-CG1-05"],
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
                    "publication": "published",
                }
            ],
        }
        profile_path = root / "studies" / "public-results.json"
        profile_path.parent.mkdir(parents=True)
        profile_path.write_text(json.dumps(profile, indent=2), encoding="utf-8")
        return profile_path, profile, receipt

    def test_current_three_card_projection_is_deterministic(self) -> None:
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
            },
            set(first),
        )
        index = json.loads(first["docs/results/index.json"])
        self.assertEqual("ael.public-results/0.1", index["schema_version"])
        self.assertEqual(
            [
                "council-generation-1",
                "focused-change-verification-calibration",
                "property-based-testing-v2",
            ],
            [card["card_id"] for card in index["studies"]],
        )
        self.assertIn("Current publication", first["docs/results/council-generation-1.md"])
        self.assertIn("not_declared_historical", first["docs/results/property-based-testing-v2.md"])
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

    def test_profile_unknown_keys_and_historical_values_fail_closed(self) -> None:
        profile = load_public_profile(PROFILE)
        unknown = copy.deepcopy(profile)
        unknown["unexpected"] = True
        with self.assertRaisesRegex(ResultSurfaceError, "unknown key"):
            validate_public_profile(unknown)

        invalid_history = copy.deepcopy(profile)
        invalid_history["studies"][0]["history"]["action"] = "completed"  # type: ignore[index]
        with self.assertRaisesRegex(ResultSurfaceError, "not_declared_historical"):
            validate_public_profile(invalid_history)

        invalid_publication = copy.deepcopy(profile)
        invalid_publication["studies"][0]["publication"] = "public_ready"  # type: ignore[index]
        with self.assertRaisesRegex(ResultSurfaceError, "publication"):
            validate_public_profile(invalid_publication)

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

    def test_bad_receipt_hash_is_rejected(self) -> None:
        with self._temporary_directory() as temporary:
            profile_path, profile, _receipt = self._profile_tree(temporary)
            profile["studies"][0]["receipt_ref"]["sha256"] = "0" * 64  # type: ignore[index]
            profile_path.write_text(json.dumps(profile), encoding="utf-8")
            with self.assertRaisesRegex(ResultSurfaceError, "sha256 does not match"):
                build_result_surface(profile_path, Path(temporary))

    def test_overflow_json_number_is_rejected(self) -> None:
        with self._temporary_directory() as temporary:
            profile_path, _profile, _receipt = self._profile_tree(temporary)
            profile_path.write_text('{"overflow": 1e400}', encoding="utf-8")
            with self.assertRaisesRegex(ResultSurfaceError, "non-finite JSON number"):
                load_public_profile(profile_path)

    def test_claim_ceiling_is_derived_from_receipt(self) -> None:
        with self._temporary_directory() as temporary:
            profile_path, profile, receipt = self._profile_tree(temporary)
            receipt_data = json.loads(receipt.read_text(encoding="utf-8"))
            receipt_data["evaluated_claims"][0]["claim_level"] = "outcome"
            receipt.write_text(json.dumps(receipt_data), encoding="utf-8")
            profile["studies"][0]["receipt_ref"]["sha256"] = _sha256(receipt)  # type: ignore[index]
            profile["studies"][0]["claim_ids"] = ["AEL-CG1-01"]  # type: ignore[index]
            profile_path.write_text(json.dumps(profile), encoding="utf-8")
            with self.assertRaisesRegex(ResultSurfaceError, "exceeds evidence ceiling"):
                build_result_surface(profile_path, Path(temporary))

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
