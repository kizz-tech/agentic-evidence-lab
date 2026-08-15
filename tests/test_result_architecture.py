from __future__ import annotations

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src/ael"


def _ael_imports(module: str) -> set[str]:
    tree = ast.parse((PACKAGE / f"{module}.py").read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names if alias.name.startswith("ael"))
        elif isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("ael"):
            imports.add(node.module)
    return imports


class ResultArchitectureTests(unittest.TestCase):
    def test_method_policy_remains_pure(self) -> None:
        self.assertEqual(set(), _ael_imports("method_policy"))

    def test_completion_integrity_engagement_policy_remains_pure(self) -> None:
        self.assertEqual(set(), _ael_imports("completion_integrity_engagement"))

    def test_completion_integrity_terminal_claim_policy_remains_pure(self) -> None:
        self.assertEqual(set(), _ael_imports("completion_integrity_claim"))

    def test_completion_integrity_task_supply_policy_remains_pure(self) -> None:
        self.assertEqual(set(), _ael_imports("completion_integrity_task_supply"))

    def test_publication_dependencies_point_toward_narrow_boundaries(self) -> None:
        self.assertEqual(
            {"ael.sandbox", "ael.validation"},
            _ael_imports("result_core"),
        )
        self.assertEqual({"ael"}, _ael_imports("result_constants"))
        self.assertEqual({"ael.result_constants"}, _ael_imports("result_rendering"))
        self.assertEqual(
            {
                "ael.completion_integrity_audit",
                "ael.debugging_shadow_audit",
                "ael.sandbox",
                "ael.study_audit",
            },
            _ael_imports("result_verification"),
        )

    def test_low_level_publication_modules_do_not_depend_on_orchestrator(self) -> None:
        for module in (
            "method_policy",
            "result_constants",
            "result_core",
            "result_rendering",
            "result_verification",
        ):
            with self.subTest(module=module):
                self.assertNotIn("ael.result_surface", _ael_imports(module))


if __name__ == "__main__":
    unittest.main()
