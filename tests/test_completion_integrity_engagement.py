from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from ael.completion_integrity_engagement import (
    canonical_ledger_sha256,
    diagnose_cells,
    diagnose_policy_enactment,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "studies/completion-integrity/diagnostics/process-v1"
METHOD_PLAN_PATH = EXAMPLE / "method-plan.pilot.json"
OBSERVATIONS_PATH = EXAMPLE / "fixtures/normalized-cells.json"
EXPECTED_PATH = EXAMPLE / "fixtures/expected-diagnostics.json"

SPEC = importlib.util.spec_from_file_location(
    "check_completion_integrity_engagement",
    ROOT / "tools/check_completion_integrity_engagement.py",
)
assert SPEC is not None and SPEC.loader is not None
ADAPTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ADAPTER)


def _load(path: Path):  # type: ignore[no-untyped-def]
    return json.loads(path.read_text(encoding="utf-8"))


class CompletionIntegrityEngagementTests(unittest.TestCase):
    def setUp(self) -> None:
        self.method = _load(METHOD_PLAN_PATH)
        self.observations = _load(OBSERVATIONS_PATH)
        self.policy_bytes = (EXAMPLE / "policy-fixture.txt").read_bytes()

    def test_known_states_are_non_compensating_and_deterministic(self) -> None:
        first = diagnose_cells(self.method, self.observations, self.policy_bytes)
        self.assertEqual(
            first,
            diagnose_cells(self.method, self.observations, self.policy_bytes),
        )
        self.assertEqual("complete", first["status"])
        self.assertEqual(
            {
                "observable_chain_complete": 2,
                "observable_chain_incomplete": 2,
                "not_assessable": 1,
                "invalid": 0,
            },
            first["state_counts"],
        )

    def test_repair_loop_is_valid_and_complete(self) -> None:
        result = diagnose_policy_enactment(self.method, self.observations[0], self.policy_bytes)
        self.assertEqual("observable_chain_complete", result["state"])
        self.assertEqual("observed", result["stage_vector"]["change"])
        self.assertEqual(1, result["counts"]["successful_preterminal_checks"])

    def test_blocker_requires_evidence_and_terminal_semantics(self) -> None:
        supported = diagnose_policy_enactment(self.method, self.observations[1], self.policy_bytes)
        self.assertEqual("observable_chain_complete", supported["state"])
        self.assertEqual(1, supported["counts"]["supported_blockers"])

        missing = copy.deepcopy(self.observations[1])
        missing["ledger_entries"][0]["evidence_event_ids"] = []
        missing["ledger_sha256"] = canonical_ledger_sha256(missing["ledger_entries"])
        result = diagnose_policy_enactment(self.method, missing, self.policy_bytes)
        self.assertEqual("observable_chain_incomplete", result["state"])
        self.assertEqual("unsatisfied", result["facets"]["checks_evidenced"])

        false_blocked = diagnose_policy_enactment(
            self.method, self.observations[2], self.policy_bytes
        )
        self.assertEqual("observable_chain_incomplete", false_blocked["state"])
        self.assertEqual("unsatisfied", false_blocked["facets"]["terminal_reconciled"])

    def test_zero_events_cannot_complete_the_chain(self) -> None:
        result = diagnose_policy_enactment(self.method, self.observations[3], self.policy_bytes)
        self.assertEqual("observable_chain_incomplete", result["state"])
        self.assertEqual("unsatisfied", result["facets"]["checks_evidenced"])
        self.assertEqual("unsatisfied", result["facets"]["terminal_reconciled"])

    def test_reconciliation_and_verification_must_follow_the_final_change(self) -> None:
        stale_verification = copy.deepcopy(self.observations[0])
        stale_verification["ledger_entries"][0]["evidence_event_ids"] = ["RL-3"]
        stale_verification["ledger_sha256"] = canonical_ledger_sha256(
            stale_verification["ledger_entries"]
        )
        result = diagnose_policy_enactment(self.method, stale_verification, self.policy_bytes)
        self.assertEqual("observable_chain_incomplete", result["state"])
        self.assertEqual("unsatisfied", result["facets"]["checks_evidenced"])

        early_reconciliation = copy.deepcopy(self.observations[0])
        early_reconciliation["events"][3]["stage"] = "reconcile"
        early_reconciliation["events"][4]["stage"] = "change"
        early_reconciliation["events"][5]["stage"] = "verify"
        early_reconciliation["events"][5]["outcome"] = "success"
        for entry in early_reconciliation["ledger_entries"]:
            entry["evidence_event_ids"] = ["RL-6"]
        early_reconciliation["ledger_sha256"] = canonical_ledger_sha256(
            early_reconciliation["ledger_entries"]
        )
        result = diagnose_policy_enactment(self.method, early_reconciliation, self.policy_bytes)
        self.assertEqual("observable_chain_incomplete", result["state"])
        self.assertEqual("unsatisfied", result["facets"]["terminal_reconciled"])

    def test_inspection_is_not_blocker_evidence(self) -> None:
        weak_blocker = copy.deepcopy(self.observations[1])
        weak_blocker["ledger_entries"][0]["evidence_event_ids"] = ["BL-1"]
        weak_blocker["ledger_sha256"] = canonical_ledger_sha256(weak_blocker["ledger_entries"])
        result = diagnose_policy_enactment(self.method, weak_blocker, self.policy_bytes)
        self.assertEqual("observable_chain_incomplete", result["state"])
        self.assertEqual("unsatisfied", result["facets"]["checks_evidenced"])

    def test_bundle_rejects_empty_and_duplicate_cell_sets(self) -> None:
        empty = diagnose_cells(self.method, [], self.policy_bytes)
        self.assertEqual("blocked", empty["status"])
        self.assertIn("CI10-R001", {item["code"] for item in empty["issues"]})

        duplicate = diagnose_cells(
            self.method,
            [self.observations[0], self.observations[0]],
            self.policy_bytes,
        )
        self.assertEqual("blocked", duplicate["status"])
        self.assertIn("CI10-R002", {item["code"] for item in duplicate["issues"]})

    def test_alpha9_is_not_retroactively_classified(self) -> None:
        historical = diagnose_policy_enactment(
            self.method, self.observations[-1], self.policy_bytes
        )
        self.assertEqual("not_assessable", historical["state"])
        self.assertTrue(all(value == "not_assessable" for value in historical["facets"].values()))
        self.assertIn("alpha.9", historical["boundary"])

    def test_hash_and_reference_failures_are_invalid(self) -> None:
        byte_mismatch = diagnose_policy_enactment(
            self.method,
            self.observations[0],
            b"different policy bytes",
        )
        self.assertEqual("invalid", byte_mismatch["state"])
        self.assertIn("CI10-E029", {item["code"] for item in byte_mismatch["issues"]})

        policy_mismatch = copy.deepcopy(self.observations[0])
        policy_mismatch["policy_sha256"] = "b" * 64
        result = diagnose_policy_enactment(self.method, policy_mismatch, self.policy_bytes)
        self.assertEqual("invalid", result["state"])
        self.assertIn("CI10-E015", {item["code"] for item in result["issues"]})

        ledger_mismatch = copy.deepcopy(self.observations[0])
        ledger_mismatch["ledger_entries"][0]["status"] = "unmet"
        result = diagnose_policy_enactment(self.method, ledger_mismatch, self.policy_bytes)
        self.assertEqual("invalid", result["state"])
        self.assertIn("CI10-E022", {item["code"] for item in result["issues"]})

        unknown_event = copy.deepcopy(self.observations[0])
        unknown_event["ledger_entries"][0]["evidence_event_ids"] = ["UNKNOWN"]
        unknown_event["ledger_sha256"] = canonical_ledger_sha256(unknown_event["ledger_entries"])
        result = diagnose_policy_enactment(self.method, unknown_event, self.policy_bytes)
        self.assertEqual("invalid", result["state"])
        self.assertIn("CI10-E025", {item["code"] for item in result["issues"]})

    def test_policy_fixture_and_golden_bundle_are_bound(self) -> None:
        bundle = ADAPTER.check_bundle(
            METHOD_PLAN_PATH,
            OBSERVATIONS_PATH,
            diagnostics_json=EXPECTED_PATH,
            check=True,
        )
        self.assertEqual(
            self.method["policy_ref"]["sha256"],
            bundle["input_hashes"]["policy_fixture_sha256"],
        )
        self.assertEqual("complete", bundle["report"]["status"])
        self.assertEqual(_load(EXPECTED_PATH), bundle)

    def test_adapter_rejects_unsafe_or_non_strict_inputs(self) -> None:
        temporary_root = "/private/tmp" if Path("/private/tmp").is_dir() else None
        with tempfile.TemporaryDirectory(dir=temporary_root) as temporary:
            root = Path(temporary)
            path = root / "duplicate.json"
            path.write_text('{"a": 1, "a": 2}', encoding="utf-8")
            with self.assertRaisesRegex(ADAPTER.EngagementAdapterError, "duplicate"):
                ADAPTER.load_json(path, "fixture")
            path.write_text('{"a": 1e400}', encoding="utf-8")
            with self.assertRaisesRegex(ADAPTER.EngagementAdapterError, "non-finite"):
                ADAPTER.load_json(path, "fixture")

            method = copy.deepcopy(self.method)
            method["policy_ref"]["uri"] = "../policy.txt"
            with self.assertRaisesRegex(ADAPTER.EngagementAdapterError, "safe relative"):
                ADAPTER._policy_file(root / "method.json", method)

    def test_family_policy_has_no_ael_dependency(self) -> None:
        source = (ROOT / "src/ael/completion_integrity_engagement.py").read_text(encoding="utf-8")
        self.assertNotIn("from ael", source)
        self.assertNotIn("import ael", source)


if __name__ == "__main__":
    unittest.main()
