from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from ael.result_core import ResultSurfaceError, SourceLedger, load_json_object


class ResultCoreTests(unittest.TestCase):
    def test_source_ledger_records_every_resolved_reference_once(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as raw_root:
            root = Path(raw_root)
            owner = root / "profile.json"
            target = root / "evidence.json"
            owner.write_text("{}\n", encoding="utf-8")
            target.write_text('{"ok": true}\n', encoding="utf-8")
            digest = hashlib.sha256(target.read_bytes()).hexdigest()
            ledger = SourceLedger(root)

            projected = ledger.projected_ref(
                owner,
                {"uri": "evidence.json", "sha256": digest},
                "evidence",
            )

            self.assertEqual({"uri": "evidence.json", "sha256": digest}, projected)
            self.assertEqual({"evidence.json": digest}, ledger.snapshot())

    def test_source_ledger_detects_mid_projection_source_change(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as raw_root:
            root = Path(raw_root)
            target = root / "evidence.json"
            target.write_text('{"version": 1}\n', encoding="utf-8")
            ledger = SourceLedger(root)
            ledger.add(target)
            target.write_text('{"version": 2}\n', encoding="utf-8")

            with self.assertRaisesRegex(ResultSurfaceError, "changed during materialization"):
                ledger.add(target)

    def test_source_ledger_accounts_for_a_complete_regular_tree(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as raw_root:
            root = Path(raw_root)
            bundle = root / "bundle"
            nested = bundle / "nested"
            nested.mkdir(parents=True)
            (bundle / "a.json").write_text("{}\n", encoding="utf-8")
            (nested / "b.txt").write_text("evidence\n", encoding="utf-8")
            ledger = SourceLedger(root)

            self.assertEqual(2, ledger.add_tree(bundle, "bundle"))
            self.assertEqual(
                {"bundle/a.json", "bundle/nested/b.txt"},
                set(ledger.snapshot()),
            )

    def test_strict_json_boundary_rejects_duplicate_and_overflow_numbers(self) -> None:
        for payload in ('{"x": 1, "x": 2}\n', '{"x": 1e400}\n'):
            with (
                self.subTest(payload=payload),
                tempfile.TemporaryDirectory(dir="/private/tmp") as raw_root,
            ):
                path = Path(raw_root) / "input.json"
                path.write_text(payload, encoding="utf-8")
                with self.assertRaises(ResultSurfaceError):
                    load_json_object(path)


if __name__ == "__main__":
    unittest.main()
