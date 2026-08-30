from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ael.completion_integrity_activation_audit import (
    _repository_root,
    audit_completion_integrity_activation_bundle,
)
from ael.sandbox import SandboxError


class CompletionIntegrityActivationAuditRootTests(unittest.TestCase):
    def test_v3_post_freeze_normalization_deviation_is_explicit(self) -> None:
        root = Path(__file__).resolve().parents[1]
        summary = audit_completion_integrity_activation_bundle(
            root / "studies" / "completion-integrity" / "activation-v3" / "freeze.json",
            root / "studies" / "completion-integrity" / "activation-v3" / "results",
            git_root=root,
        )
        self.assertEqual("protocol_invalid", summary["result"]["status"])
        deviation = summary["evidence"]["normalization_deviation"]
        self.assertEqual("disclosed", deviation["status"])
        self.assertEqual(0, deviation["model_calls"])
        self.assertEqual(0, deviation["retries"])
        commit = deviation["terminal_projection_commit"]
        self.assertTrue(commit is None or isinstance(commit, str) and len(commit) == 40)

    def test_repository_root_is_derived_from_the_audited_freeze_not_module_location(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ael-activation-audit-root-") as raw:
            root = Path(raw) / "checkout"
            freeze = root / "studies" / "completion-integrity" / "activation-v2" / "freeze.json"
            freeze.parent.mkdir(parents=True)
            (root / "src" / "ael" / "schemas").mkdir(parents=True)
            (root / "pyproject.toml").write_text("[project]\nname='fixture'\n", encoding="utf-8")
            freeze.write_text("{}\n", encoding="utf-8")
            self.assertEqual(root.resolve(), _repository_root(freeze, None))

            outside = Path(raw) / "outside.json"
            outside.write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(SandboxError, "outside"):
                _repository_root(outside, root)


if __name__ == "__main__":
    unittest.main()
