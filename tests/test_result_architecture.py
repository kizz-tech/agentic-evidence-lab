from __future__ import annotations

import ast
import importlib
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


def _imported_modules(module: str) -> set[str]:
    """Return canonical module paths named by static imports in *module*.

    This deliberately records imports rather than maintaining a positive list
    of innocuous stdlib modules.  CEP's purity boundary is a deny-list: a new
    dependency is acceptable unless it crosses one of the explicit authority
    boundaries below.
    """

    tree = ast.parse((PACKAGE / f"{module}.py").read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                imports.add("." * node.level + (node.module or ""))
                continue
            if node.module:
                # ``from ael import coevolution`` is a dependency on the
                # submodule, not on the package facade.
                if node.module == "ael":
                    imports.update(f"ael.{alias.name}" for alias in node.names)
                else:
                    imports.add(node.module)
    return imports


def _assert_no_import_prefixes(
    testcase: unittest.TestCase,
    module: str,
    forbidden_prefixes: set[str],
) -> None:
    imports = _imported_modules(module)
    forbidden = {
        imported
        for imported in imports
        if any(
            imported == prefix or imported.startswith(f"{prefix}.") for prefix in forbidden_prefixes
        )
    }
    testcase.assertEqual(
        set(),
        forbidden,
        f"{module} crosses a prohibited architecture boundary: {sorted(forbidden)}",
    )


# A negative boundary is intentionally broader than the currently observed
# imports.  It blocks ambient I/O, orchestration, and nondeterministic sources
# without constraining harmless implementation details such as collections or
# typing.
_AMBIENT_IO_AND_NONDETERMINISM = {
    "asyncio",
    "concurrent",
    "datetime",
    "email",
    "fileinput",
    "ftplib",
    "glob",
    "http",
    "importlib",
    "io",
    "logging",
    "multiprocessing",
    "ntpath",
    "os",
    "pathlib",
    "pickle",
    "platform",
    "poplib",
    "posixpath",
    "random",
    "requests",
    "secrets",
    "shutil",
    "signal",
    "smtplib",
    "socket",
    "ssl",
    "subprocess",
    "tempfile",
    "time",
    "urllib",
    "uuid",
    "webbrowser",
    "xmlrpc",
}


class ResultArchitectureTests(unittest.TestCase):
    def test_method_policy_remains_pure(self) -> None:
        self.assertEqual(set(), _ael_imports("method_policy"))

    def test_completion_integrity_engagement_policy_remains_pure(self) -> None:
        self.assertEqual(set(), _ael_imports("completion_integrity_engagement"))

    def test_completion_integrity_terminal_claim_policy_remains_pure(self) -> None:
        self.assertEqual(set(), _ael_imports("completion_integrity_claim"))

    def test_completion_integrity_task_supply_policy_remains_pure(self) -> None:
        self.assertEqual(set(), _ael_imports("completion_integrity_task_supply"))

    def test_decision_utility_policy_remains_pure(self) -> None:
        self.assertEqual(set(), _ael_imports("decision_utility"))
        _assert_no_import_prefixes(
            self,
            "decision_utility",
            _AMBIENT_IO_AND_NONDETERMINISM,
        )

    def test_publication_dependencies_point_toward_narrow_boundaries(self) -> None:
        self.assertEqual(
            {"ael.sandbox", "ael.validation"},
            _ael_imports("result_core"),
        )
        self.assertEqual({"ael"}, _ael_imports("result_constants"))
        self.assertEqual({"ael.result_constants"}, _ael_imports("result_rendering"))
        self.assertEqual(
            {
                "ael.completion_integrity_activation_audit",
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

    def test_coevolution_kernel_is_pure_and_deterministic(self) -> None:
        self.assertEqual(set(), _ael_imports("coevolution"))
        _assert_no_import_prefixes(
            self,
            "coevolution",
            _AMBIENT_IO_AND_NONDETERMINISM
            | {
                "runner",
                "provider",
                "sandbox",
            },
        )

    def test_coevolution_simulator_isolation(self) -> None:
        imports = _imported_modules("coevolution_simulator")
        self.assertEqual(
            {"ael.coevolution"},
            {imported for imported in imports if imported.startswith("ael")},
        )
        _assert_no_import_prefixes(
            self,
            "coevolution_simulator",
            _AMBIENT_IO_AND_NONDETERMINISM
            | {
                "runner",
                "provider",
                "sandbox",
            },
        )

    def test_coevolution_bundle_cannot_reach_execution_or_result_surface(self) -> None:
        imports = _imported_modules("coevolution_bundle")
        self.assertEqual(
            {"ael.coevolution"},
            {imported for imported in imports if imported.startswith("ael")},
        )
        _assert_no_import_prefixes(
            self,
            "coevolution_bundle",
            {
                "http",
                "ftplib",
                "poplib",
                "requests",
                "smtplib",
                "socket",
                "ssl",
                "urllib",
                "webbrowser",
                "xmlrpc",
                "runner",
                "provider",
                "sandbox",
                "result_surface",
                "ael.runner",
                "ael.provider",
                "ael.sandbox",
                "ael.result_surface",
            },
        )

    def test_coevolution_python_modules_publish_no_supported_api(self) -> None:
        for module_name in (
            "ael.coevolution",
            "ael.coevolution_bundle",
            "ael.coevolution_simulator",
            "ael.decision_utility",
        ):
            with self.subTest(module=module_name):
                module = importlib.import_module(module_name)
                self.assertEqual((), module.__all__)

    def test_contract_graph_only_adapts_the_frozen_contract_validator(self) -> None:
        imports = _imported_modules("contract_graph")
        self.assertEqual(
            {"ael.validation"},
            {imported for imported in imports if imported.startswith("ael")},
        )


if __name__ == "__main__":
    unittest.main()
