from __future__ import annotations

import ast
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from ael import coevolution as core
from ael import coevolution_bundle as adapter
from ael import validation
from ael.coevolution_bundle import (
    MAX_EDGES,
    MAX_FILE_BYTES,
    MAX_RECORDS,
    CoevolutionBundleError,
    append_rescore_files,
    check_bundle,
    load_bundle,
    load_protocol,
    materialize_bundle,
    render_bundle_report,
    write_json_atomic,
    write_text_atomic,
)

HASH = "a" * 64


def _protocol() -> dict[str, object]:
    partitions = {
        name: {
            "partition_id": name,
            "purpose": "synthetic purpose",
            "feedback": "bounded feedback",
            "sealed": name == "confirmation",
            "single_use": name == "confirmation",
            "eligible_for_promotion": name == "confirmation",
            "exposure_budget": 1,
            "task_root_hash": hashlib.sha256(f"task-root-{name}".encode()).hexdigest(),
        }
        for name in ("development", "screening", "bridge", "confirmation", "historical")
    }
    arms = {
        "A0": {
            "builder": "fixed",
            "evaluator": "fixed",
            "loop": "open",
            "custody": "shared",
            "challenger": "absent",
            "anchor": "absent",
        },
        "A1": {
            "builder": "evolving",
            "evaluator": "fixed",
            "loop": "open",
            "custody": "shared",
            "challenger": "absent",
            "anchor": "absent",
        },
        "A2": {
            "builder": "fixed",
            "evaluator": "evolving",
            "loop": "open",
            "custody": "shared",
            "challenger": "absent",
            "anchor": "absent",
        },
        "A3": {
            "builder": "evolving",
            "evaluator": "evolving",
            "loop": "naive_closed",
            "custody": "shared",
            "challenger": "absent",
            "anchor": "absent",
        },
        "A4": {
            "builder": "evolving",
            "evaluator": "evolving",
            "loop": "custody_separated",
            "custody": "separated",
            "challenger": "absent",
            "anchor": "protected",
        },
        "A5": {
            "builder": "evolving",
            "evaluator": "evolving",
            "loop": "challenger_anchor",
            "custody": "separated",
            "challenger": "present",
            "anchor": "protected",
        },
    }
    algorithms = {
        key: {"ref": key, "hash": HASH}
        for key in (
            "eligibility",
            "task_allocation",
            "proposal_admission",
            "selection_ranking",
            "stopping",
            "analysis",
            "promotion",
        )
    }
    budgets = {key: 1 for key in ("total_system", "feedback", "exposure", "confirmation")}
    contrasts = [
        {
            "contrast_id": "builder-contrast",
            "arm_a": "A0",
            "arm_b": "A1",
            "treatment": {
                "dimension": "builder",
                "arm_a_level": "fixed",
                "arm_b_level": "evolving",
            },
            "estimand_kind": "component",
            "eligibility": algorithms["eligibility"],
            "task_allocation": algorithms["task_allocation"],
            "proposal_admission": algorithms["proposal_admission"],
            "selection_ranking": algorithms["selection_ranking"],
            "stopping": algorithms["stopping"],
            "analysis": algorithms["analysis"],
            "promotion": algorithms["promotion"],
            "budgets": budgets,
        }
    ]
    intake = {
        key: "declared"
        for key in (
            "target_population",
            "use",
            "intake_owner",
            "sampling_custodian",
            "sampling_frame",
            "sampling_method",
            "sampling_window",
            "sampling_cutoff",
            "eligibility",
            "deduplication",
            "censoring_late_arrival",
            "oracle",
            "adjudication",
            "appeal",
            "utility",
            "harms",
            "weights",
            "margins",
            "arm_blinding",
            "allocation_proof",
            "exposure_policy",
        )
    }
    return {
        "schema_version": core.PROTOCOL_SCHEMA_VERSION,
        "protocol_id": "protocol-test",
        "epoch": {
            "epoch_id": "epoch-test",
            "state": "frozen",
            "constitution_ref": "constitution-test",
            "constitution_hash": HASH,
        },
        "principals": {
            key: {
                "principal_id": key,
                "custody": f"{key}-custody",
                "independence": "separate",
            }
            for key in ("evidence", "confirmation", "anchor", "adjudication", "promotion")
        },
        "intake": intake,
        "partitions": partitions,
        "arms": arms,
        "contrasts": contrasts,
        "algorithms": algorithms,
        "budgets": budgets,
        "feedback_exposure": {
            "development": "declared",
            "screening": "declared",
            "bridge": "declared",
            "confirmation": "declared",
            "total": "declared",
        },
        "missingness": {
            "policy": "declared",
            "bounds": "declared",
            "critical_failure_rule": "declared",
        },
        "stopping": {
            "algorithm_ref": "stopping",
            "algorithm_hash": HASH,
            "rule": "declared",
            "max_looks": 1,
            "missing_data": "declared",
        },
        "bridge": {
            "global_shift_tolerance": 0,
            "interaction_tolerance": 0,
            "decision_agreement_min": 1,
            "construct_required": True,
            "reliability_required": True,
            "anchor_required": True,
            "strata": [
                {
                    "stratum": name,
                    "weight": 0.2,
                    "task_root_hash": hashlib.sha256(f"stratum-root-{name}".encode()).hexdigest(),
                }
                for name in ("good", "bad", "exploit", "semantic_mutant", "near_threshold")
            ],
        },
        "decision_rule": {
            "threshold": 0.64,
            "operator": "gte",
            "value_range": [0.0, 1.0],
            "required_status": "observed",
            "outcome": "prospective_utility",
            "critical_failure": "block",
        },
        "replay": {
            "retention_policy": "declared",
            "required_surfaces": ["surface"],
            "deterministic_code_policy": "declared",
        },
        "independence": {"protected_dimensions": ["custody"], "ceiling": "declared"},
        "promotion": {
            "initial_state": "registered",
            "transition_table": {
                "registered": ["development_eligible"],
                "development_eligible": ["revoke", "screening_pass", "screening_reject"],
                "screening_pass": ["bridge_eligible", "new_measurement_epoch", "revoke"],
                "screening_reject": [],
                "bridge_eligible": ["confirmation_eligible", "new_measurement_epoch", "revoke"],
                "new_measurement_epoch": [],
                "confirmation_eligible": [
                    "abstain",
                    "narrow",
                    "promote",
                    "reject",
                    "revoke",
                ],
                "promote": ["expire", "monitor", "revoke"],
                "narrow": ["expire", "monitor", "revoke"],
                "abstain": ["expire", "monitor", "revoke"],
                "reject": ["expire", "monitor", "revoke"],
                "monitor": ["expire", "revoke"],
                "expire": [],
                "revoke": [],
            },
            "terminal_states": [
                "screening_reject",
                "new_measurement_epoch",
                "expire",
                "revoke",
            ],
        },
        "effect_policy": "forbidden",
        "simulation": {
            "config_version": "test",
            "seed": 0,
            "scenarios": [{"name": "null", "tasks": 1, "replicates": 1}],
        },
    }


def _evaluator(release_id: str, *, custody: str = "evaluator-custody") -> dict[str, object]:
    return {
        "release_id": release_id,
        "release_kind": "evaluator",
        "revision": "1",
        "artifact_hash": HASH,
        "implementation": "data-only",
        "prompt_or_rubric": "data-only",
        "model": "synthetic",
        "parser_or_aggregation": "data-only",
        "tools_or_environment": "data-only",
        "calibration_lineage": "synthetic",
        "known_error_envelope": "declared",
        "custody": custody,
        "allowed_evidence_surface": ["surface"],
    }


def _trajectory_counts(*, zero: bool = False) -> dict[str, object]:
    """Small valid count fixture for the dependency-bound contrast seal."""

    if zero:
        eligible = 1
        promotion = {key: 0 for key in ("useful", "null", "harmful", "adversarial")}
        candidate_opportunities = {"useful": 1, "null": 0, "harmful": 0, "adversarial": 0}
        exploit = {"candidates": 0, "accepted": 0}
        disposition = {
            "eligible": eligible,
            "quarantined": 0,
            "revoked": 0,
            "unscorable": 0,
            "invalid": 0,
            "missing": 0,
        }
    else:
        eligible = 1
        promotion = {"useful": 0, "null": 1, "harmful": 0, "adversarial": 0}
        candidate_opportunities = {"useful": 0, "null": 1, "harmful": 0, "adversarial": 0}
        exploit = {"candidates": 0, "accepted": 0}
        disposition = {
            "eligible": eligible,
            "quarantined": 0,
            "revoked": 0,
            "unscorable": 0,
            "invalid": 0,
            "missing": 0,
        }
    return {
        "disposition": disposition,
        "promotion": promotion,
        "candidate_opportunities": candidate_opportunities,
        "exploit": exploit,
        "critical_failures": 0,
        "bridge": {"attempted": 0, "passed": 0, "failed": 0, "unknown": 0, "later_reversal": 0},
        "tainted": 0,
        "revocation": {"declared_descendants": 0, "complete_descendants": 0},
        "optional_stopping": {"events": 0, "eligible_replicates": 0},
    }


class CoevolutionBundleAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory(prefix="ael-cep-adapter-")
        self.root = Path(self.directory.name)
        self.protocol = _protocol()
        self.protocol_path = self.root / "protocol.json"
        write_json_atomic(self.protocol_path, self.protocol)
        self.protocol, self.protocol_raw_sha256 = load_protocol(self.protocol_path)
        self.bundle = core.create_bundle(self.protocol, bundle_id="bundle-test")
        self.bundle_path = self.root / "bundle.json"
        materialize_bundle(self.protocol_path, self.bundle_path, self.bundle)

    def tearDown(self) -> None:
        self.directory.cleanup()

    def _sealed_bundle(self, bundle_id: str, *, zero: bool = False) -> dict[str, object]:
        records: list[dict[str, object]] = []
        previous_hash: str | None = None
        for sequence, arm in enumerate(self.protocol["arms"]):
            record = core.create_record(
                record_id=f"trajectory:{arm}:null",
                record_type="trajectory_summary",
                epoch_id=self.protocol["epoch"]["epoch_id"],
                sequence=sequence,
                previous_record_hash=previous_hash,
                payload={
                    "summary_id": f"trajectory:{arm}:null",
                    "arm": arm,
                    "scenario_ref": "scenario:null",
                    "counts": _trajectory_counts(zero=zero),
                    "primary_endpoint": {
                        "sum_ppm": 0 if zero else sequence * 100_000,
                        "observed_count": 0 if zero else 1,
                    },
                    "budget": {"target": 1, "actual": 1, "delta": 0},
                },
            )
            records.append(record)
            previous_hash = record["record_hash"]
        seal = core.create_record(
            record_id="contrast-summary:sealed",
            record_type="contrast_summary",
            epoch_id=self.protocol["epoch"]["epoch_id"],
            sequence=len(records),
            previous_record_hash=previous_hash,
            payload={
                "summary_id": "contrast-summary:sealed",
                "aggregation_version": core.CONTRAST_SUMMARY_AGGREGATION_VERSION,
                "contrasts": core.derive_contrast_diagnostics(
                    self.protocol, [record["payload"] for record in records]
                ),
            },
            dependency_refs={record["record_id"]: record["record_hash"] for record in records},
        )
        records.append(seal)
        return core.create_bundle(self.protocol, bundle_id=bundle_id, records=records)

    def test_protocol_schema_and_raw_hash_binding(self) -> None:
        self.assertEqual(
            hashlib.sha256(self.protocol_path.read_bytes()).hexdigest(), self.protocol_raw_sha256
        )
        self.assertEqual(self.protocol["protocol_id"], "protocol-test")
        self.assertEqual(
            load_bundle(self.bundle_path, protocol=self.protocol)["bundle_id"], "bundle-test"
        )

    def test_duplicate_nonfinite_unknown_and_unsafe_values_are_rejected(self) -> None:
        duplicate = self.root / "duplicate.json"
        duplicate.write_bytes(b'{"x": 1, "x": 2}')
        with self.assertRaisesRegex(CoevolutionBundleError, "duplicate_json_member"):
            load_protocol(duplicate)
        nonfinite = self.root / "nonfinite.json"
        nonfinite.write_bytes(b'{"x": NaN}')
        with self.assertRaisesRegex(CoevolutionBundleError, "nonfinite"):
            load_protocol(nonfinite)
        unknown = dict(self.protocol)
        unknown["unexpected"] = True
        unknown_path = self.root / "unknown.json"
        write_json_atomic(unknown_path, unknown)
        with self.assertRaisesRegex(CoevolutionBundleError, "unknown_field"):
            load_protocol(unknown_path)
        builder = core.create_record(
            record_id="unknown-builder",
            record_type="builder_release",
            epoch_id=self.protocol["epoch"]["epoch_id"],
            sequence=0,
            previous_record_hash=None,
            payload={
                "release_id": "unknown-builder",
                "release_kind": "builder",
                "revision": "1",
                "artifact_hash": HASH,
                "custody": "builder-custody",
                "allowed_evidence_surface": ["surface"],
            },
        )
        unknown_bundle = core.create_bundle(
            self.protocol, bundle_id="unknown-bundle", records=[builder]
        )
        unknown_bundle["records"][0]["payload"]["unexpected"] = True
        unknown_bundle_path = self.root / "unknown-bundle.json"
        write_json_atomic(unknown_bundle_path, unknown_bundle)
        with self.assertRaisesRegex(CoevolutionBundleError, "unknown_field"):
            load_bundle(unknown_bundle_path, protocol=self.protocol)
        unsafe = dict(self.protocol)
        unsafe["epoch"] = dict(self.protocol["epoch"])
        unsafe["epoch"]["constitution_ref"] = "file:///private/constitution"
        (self.root / "unsafe.json").write_text(json.dumps(unsafe), encoding="utf-8")
        with self.assertRaisesRegex(CoevolutionBundleError, "unsafe_reference"):
            load_protocol(self.root / "unsafe.json")
        unsafe_key = self.root / "unsafe-key.json"
        unsafe_key.write_bytes(b'{"file:///private/constitution": 1}')
        with self.assertRaisesRegex(CoevolutionBundleError, "unsafe_reference"):
            load_protocol(unsafe_key)

    def test_schema_error_selection_is_streaming_and_deterministic(self) -> None:
        errors = (
            SimpleNamespace(
                absolute_path=[index],
                validator="required",
                message=f"error {index}",
                context=(),
            )
            for index in reversed(range(100_000))
        )
        selected = adapter._select_schema_error(errors)
        self.assertIsNotNone(selected)
        self.assertEqual(selected.absolute_path, [0])

        malformed = dict(self.bundle)
        malformed["records"] = [{} for _ in range(2_000)]
        malformed_path = self.root / "many-malformed-records.json"
        write_json_atomic(malformed_path, malformed)
        with self.assertRaisesRegex(CoevolutionBundleError, "schema_violation"):
            load_bundle(malformed_path, protocol=self.protocol)

        too_many_records = dict(self.bundle)
        too_many_records["records"] = [{} for _ in range(MAX_RECORDS + 1)]
        too_many_records_path = self.root / "too-many-records.json"
        write_json_atomic(too_many_records_path, too_many_records)
        with self.assertRaisesRegex(CoevolutionBundleError, "record_limit"):
            load_bundle(too_many_records_path, protocol=self.protocol)

        too_many_edges = dict(self.bundle)
        too_many_edges["records"] = [
            {"dependency_refs": {str(index): HASH for index in range(MAX_EDGES + 1)}}
        ]
        too_many_edges_path = self.root / "too-many-edges.json"
        write_json_atomic(too_many_edges_path, too_many_edges)
        with self.assertRaisesRegex(CoevolutionBundleError, "edge_limit"):
            load_bundle(too_many_edges_path, protocol=self.protocol)

        huge_error = dict(self.protocol)
        huge_error["simulation"] = {
            "config_version": "test",
            "seed": "x" * 100_000,
            "scenarios": ["null"],
        }
        huge_error_path = self.root / "bounded-schema-error.json"
        write_json_atomic(huge_error_path, huge_error)
        with self.assertRaises(CoevolutionBundleError) as caught:
            load_protocol(huge_error_path)
        self.assertLess(len(str(caught.exception)), 2_000)

    def test_size_and_symlink_limits(self) -> None:
        oversized = self.root / "oversized.json"
        oversized.write_bytes(b" " * (2 * 1024 * 1024 + 1))
        with self.assertRaisesRegex(CoevolutionBundleError, "size_limit"):
            load_protocol(oversized)
        symlink = self.root / "protocol-link.json"
        try:
            symlink.symlink_to(self.protocol_path)
        except OSError as exc:  # pragma: no cover - platform without symlinks
            self.skipTest(str(exc))
        with self.assertRaisesRegex(CoevolutionBundleError, "unsafe_symlink"):
            load_protocol(symlink)

    def test_tamper_predecessor_and_check_mode_drift(self) -> None:
        tampered = dict(self.bundle)
        tampered["bundle_hash"] = "b" * 64
        tampered_path = self.root / "tampered.json"
        write_json_atomic(tampered_path, tampered)
        with self.assertRaisesRegex(CoevolutionBundleError, "hash_mismatch"):
            load_bundle(tampered_path, protocol=self.protocol)
        predecessor_path = self.root / "predecessor.json"
        materialize_bundle(self.protocol_path, predecessor_path, self.bundle)
        # An empty successor has no predecessor records and is therefore
        # rejected by the core prefix rule; use append_bundle for a valid one.
        successor = core.append_bundle(self.bundle, [], protocol=self.protocol)
        declared_path = self.root / "declared-predecessor.json"
        write_json_atomic(declared_path, successor)
        with self.assertRaisesRegex(CoevolutionBundleError, "predecessor_required"):
            load_bundle(declared_path, protocol=self.protocol)
        with self.assertRaisesRegex(CoevolutionBundleError, "predecessor_arguments"):
            load_bundle(
                declared_path,
                protocol=self.protocol,
                predecessor_path=predecessor_path,
                predecessor_paths=[predecessor_path],
            )
        omitted_output = self.root / "omitted-predecessor-output.json"
        with self.assertRaisesRegex(CoevolutionBundleError, "predecessor_required"):
            materialize_bundle(self.protocol_path, omitted_output, successor)
        self.assertFalse(omitted_output.exists())
        output = self.root / "successor.json"
        materialize_bundle(self.protocol_path, output, successor, predecessor_path=predecessor_path)
        self.assertEqual(
            load_bundle(output, protocol=self.protocol, predecessor_path=predecessor_path)[
                "bundle_id"
            ],
            successor["bundle_id"],
        )

        second_successor = core.append_bundle(
            successor,
            [],
            protocol=self.protocol,
            predecessor_chain=[self.bundle],
        )
        second_output = self.root / "successor-2.json"
        with self.assertRaisesRegex(CoevolutionBundleError, "predecessor_required"):
            materialize_bundle(
                self.protocol_path,
                second_output,
                second_successor,
                predecessor_path=output,
            )
        materialize_bundle(
            self.protocol_path,
            second_output,
            second_successor,
            predecessor_paths=[predecessor_path, output],
        )
        self.assertEqual(
            load_bundle(
                second_output,
                protocol=self.protocol,
                predecessor_paths=[predecessor_path, output],
            )["bundle_id"],
            second_successor["bundle_id"],
        )
        second_projection = check_bundle(
            self.protocol_path,
            second_output,
            predecessor_paths=[predecessor_path, output],
        )
        with self.assertRaisesRegex(CoevolutionBundleError, "predecessor_required"):
            render_bundle_report(self.protocol, second_successor, second_projection)
        self.assertIn(
            "synthetic / provisional / no-effect",
            render_bundle_report(
                self.protocol,
                second_successor,
                second_projection,
                predecessor_paths=[predecessor_path, output],
            ),
        )

        third_successor = core.append_bundle(
            second_successor,
            [],
            protocol=self.protocol,
            predecessor_chain=[self.bundle, successor],
        )
        third_output = self.root / "successor-3.json"
        with self.assertRaisesRegex(CoevolutionBundleError, "predecessor_required"):
            materialize_bundle(
                self.protocol_path,
                third_output,
                third_successor,
                predecessor_paths=[output, second_output],
            )
        with self.assertRaisesRegex(CoevolutionBundleError, "predecessor_required"):
            materialize_bundle(
                self.protocol_path,
                third_output,
                third_successor,
                predecessor_paths=[output, predecessor_path, second_output],
            )
        changed_ancestor = dict(self.bundle)
        changed_ancestor["bundle_hash"] = "b" * 64
        with self.assertRaises(core.CoevolutionError) as missing_grandparent:
            core.validate_bundle(
                third_successor,
                protocol=self.protocol,
                predecessor_chain=[successor, second_successor],
            )
        self.assertEqual(missing_grandparent.exception.reason, "predecessor_required")
        with self.assertRaises(core.CoevolutionError) as changed_grandparent:
            core.validate_bundle(
                third_successor,
                protocol=self.protocol,
                predecessor_chain=[changed_ancestor, successor, second_successor],
            )
        self.assertEqual(changed_grandparent.exception.reason, "hash_mismatch")
        changed_ancestor_path = self.root / "changed-ancestor.json"
        write_json_atomic(changed_ancestor_path, changed_ancestor)
        with self.assertRaisesRegex(CoevolutionBundleError, "hash_mismatch"):
            materialize_bundle(
                self.protocol_path,
                third_output,
                third_successor,
                predecessor_paths=[changed_ancestor_path, output, second_output],
            )
        materialize_bundle(
            self.protocol_path,
            third_output,
            third_successor,
            predecessor_paths=[predecessor_path, output, second_output],
        )
        self.assertEqual(
            load_bundle(
                third_output,
                protocol=self.protocol,
                predecessor_paths=[predecessor_path, output, second_output],
            )["bundle_id"],
            third_successor["bundle_id"],
        )
        write_json_atomic(output, {"drift": True})
        with self.assertRaisesRegex(CoevolutionBundleError, "output_drift"):
            materialize_bundle(
                self.protocol_path, output, successor, predecessor_path=predecessor_path, check=True
            )
        missing_output = self.root / "missing-parent" / "bundle.json"
        with self.assertRaisesRegex(CoevolutionBundleError, "output_parent"):
            materialize_bundle(
                self.protocol_path,
                missing_output,
                successor,
                predecessor_path=predecessor_path,
                check=True,
            )
        self.assertFalse(missing_output.parent.exists())

        with self.assertRaisesRegex(CoevolutionBundleError, "input_mutation"):
            materialize_bundle(self.protocol_path, self.protocol_path, self.bundle)

    def test_atomic_writes_and_report_are_deterministic(self) -> None:
        text_path = self.root / "report.md"
        write_text_atomic(text_path, "hello")
        self.assertEqual(text_path.read_bytes(), b"hello\n")
        with self.assertRaisesRegex(CoevolutionBundleError, "size_limit"):
            write_text_atomic(self.root / "too-large.md", "x" * (MAX_FILE_BYTES + 1))
        self.assertFalse((self.root / "too-large.md").exists())
        report = render_bundle_report(
            self.protocol, self.bundle, check_bundle(self.protocol_path, self.bundle_path)
        )
        self.assertEqual(
            report,
            render_bundle_report(
                self.protocol, self.bundle, check_bundle(self.protocol_path, self.bundle_path)
            ),
        )
        self.assertIn("synthetic / provisional / no-effect", report)
        self.assertIn("does not establish real-world", report)
        untrusted = render_bundle_report(
            self.protocol,
            self.bundle,
            {"false_promotion_share": 999, "taint": 999},
        )
        self.assertNotIn("999", untrusted)

        sealed_bundle = self._sealed_bundle("summary-bundle")
        sealed_projection = core.project_bundle(sealed_bundle, protocol=self.protocol)
        sealed_report = render_bundle_report(self.protocol, sealed_bundle, sealed_projection)
        self.assertIn("synthetic / provisional / no-effect", sealed_report)
        self.assertIn("does not establish real-world", sealed_report)
        self.assertIn(
            '- `false_promotion_share`: {"count":6,"denominator":6,"rate":1.0}',
            sealed_report,
        )
        self.assertIn(
            '- `invalid_candidate_promotion_rate`: {"count":6,"denominator":6,"rate":1.0}',
            sealed_report,
        )
        self.assertNotIn("`false_promotion`:", sealed_report)
        for definition in (
            "invalid promotions (null, harmful, or adversarial) / all candidate promotions",
            "invalid promotions (null, harmful, or adversarial) / invalid candidate opportunities",
            "useful promotions / useful candidate opportunities",
            "accepted exploits / exploit candidates",
            "critical failures / task disposition attempts",
            "later bridge reversals / passed bridge replicates",
            "tainted task disposition attempts / task disposition attempts",
            "missing task dispositions / task disposition attempts",
            "quarantined task dispositions / task disposition attempts",
            "optional-stopping events / eligible optional-stopping replicates",
            "complete descendants / declared descendants",
        ):
            self.assertIn(definition, sealed_report)
        self.assertIn(
            '- `A1`: {"mean_ppm":100000,"observed_count":1,"sum_ppm":100000}',
            sealed_report,
        )
        self.assertIn(
            '- {"contrast_id":"builder-contrast","endpoint_delta_ppm":-100000,"reason":null,"status":"causal_eligible"}',
            sealed_report,
        )

        # Caller projections are untrusted views: a forged metric cannot
        # replace the internally recomputed core projection.
        untrusted = render_bundle_report(
            self.protocol,
            sealed_bundle,
            {
                "operating_metrics": {"false_promotion_share": 999},
                "primary_endpoints": {"A0": {"sum_ppm": 1234567}},
                "contrast_diagnostics": [{"contrast_id": "forged", "status": "causal_eligible"}],
            },
        )
        self.assertNotIn("999", untrusted)
        self.assertNotIn("1234567", untrusted)
        self.assertNotIn("forged", untrusted)

        # Zero-denominator rates remain null/unknown rather than becoming a
        # fabricated zero.
        zero_bundle = self._sealed_bundle("zero-summary-bundle", zero=True)
        zero_report = render_bundle_report(
            self.protocol,
            zero_bundle,
            core.project_bundle(zero_bundle, protocol=self.protocol),
        )
        self.assertIn(
            '- `false_promotion_share`: {"count":0,"denominator":0,"rate":null}',
            zero_report,
        )
        self.assertIn(
            '- `A0`: {"mean_ppm":null,"observed_count":0,"sum_ppm":0}',
            zero_report,
        )
        self.assertIn('"endpoint_delta_ppm":null', zero_report)

        # The dependency-bound contrast seal rejects arbitrary caller-controlled
        # Arbitrary metric fields are rejected before rendering can occur.
        bad_seal = dict(sealed_bundle["records"][-1])
        bad_payload = dict(bad_seal["payload"])
        bad_payload["metrics"] = {"false_promotion": 999}
        bad_seal["payload"] = bad_payload
        bad_seal["record_hash"] = core.record_hash(bad_seal)
        bad_bundle = dict(sealed_bundle)
        bad_bundle["records"] = [*sealed_bundle["records"][:-1], bad_seal]
        bad_bundle["bundle_hash"] = core.bundle_hash(bad_bundle)
        with self.assertRaisesRegex(CoevolutionBundleError, "unknown_field"):
            render_bundle_report(self.protocol, bad_bundle, {})

        # A trajectory without its dependency-bound contrast seal is not a
        # report authority, and duplicate seals are rejected by core validation.
        lone = sealed_bundle["records"][0]
        lone_bundle = dict(sealed_bundle)
        lone_bundle["records"] = [lone]
        lone_bundle["bundle_hash"] = core.bundle_hash(lone_bundle)
        with self.assertRaisesRegex(CoevolutionBundleError, "summary_missing"):
            render_bundle_report(self.protocol, lone_bundle, {})

        duplicate_seal = core.create_record(
            record_id="contrast-summary:duplicate",
            record_type="contrast_summary",
            epoch_id=self.protocol["epoch"]["epoch_id"],
            sequence=len(sealed_bundle["records"]),
            previous_record_hash=sealed_bundle["records"][-1]["record_hash"],
            payload={
                "summary_id": "contrast-summary:duplicate",
                "aggregation_version": core.CONTRAST_SUMMARY_AGGREGATION_VERSION,
                "contrasts": sealed_bundle["records"][-1]["payload"]["contrasts"],
            },
            dependency_refs={
                record["record_id"]: record["record_hash"]
                for record in sealed_bundle["records"][:-1]
            },
        )
        duplicate_bundle = dict(sealed_bundle)
        duplicate_bundle["records"] = [*sealed_bundle["records"], duplicate_seal]
        duplicate_bundle["bundle_hash"] = core.bundle_hash(duplicate_bundle)
        with self.assertRaisesRegex(CoevolutionBundleError, "summary_duplicate"):
            render_bundle_report(self.protocol, duplicate_bundle, {})

        tombstone = core.create_record(
            record_id="tombstone:summary",
            record_type="deletion_tombstone",
            epoch_id=self.protocol["epoch"]["epoch_id"],
            sequence=len(sealed_bundle["records"]),
            previous_record_hash=sealed_bundle["records"][-1]["record_hash"],
            payload={
                "tombstone_id": "tombstone:summary",
                "targets": [sealed_bundle["records"][0]["record_id"]],
                "authority": self.protocol["principals"]["evidence"]["principal_id"],
                "reason": "summary revoked",
                "descendant_policy": "revoke-or-unscorable-all-dependants",
                "deleted_surfaces": ["surface"],
            },
            dependency_refs={
                sealed_bundle["records"][0]["record_id"]: sealed_bundle["records"][0]["record_hash"]
            },
        )
        revoked_bundle = core.create_bundle(
            self.protocol,
            bundle_id="revoked-summary-bundle",
            records=[*sealed_bundle["records"], tombstone],
        )
        revoked_report = render_bundle_report(
            self.protocol,
            revoked_bundle,
            core.project_bundle(revoked_bundle, protocol=self.protocol),
        )
        self.assertIn(
            "Current operating metrics: unavailable (summary absent, revoked, tainted, or unscorable)",
            revoked_report,
        )
        for metric in (
            "false_promotion_share",
            "invalid_candidate_promotion_rate",
            "useful_candidate_power",
            "exploit_acceptance",
            "critical_failure",
            "bridge_reversal",
            "taint",
            "missingness",
            "quarantine",
            "optional_stopping",
            "revocation_completeness",
        ):
            self.assertIn(f"- `{metric}`: unknown", revoked_report)
        self.assertIn("Primary endpoints: unavailable", revoked_report)
        self.assertIn("Contrast diagnostics: unavailable", revoked_report)

        # Report validation follows the complete predecessor chain; a
        # successor cannot resurrect an unavailable sealed summary.
        revoked_path = self.root / "revoked-summary.json"
        materialize_bundle(self.protocol_path, revoked_path, revoked_bundle)
        successor = core.append_bundle(revoked_bundle, [], protocol=self.protocol)
        successor_path = self.root / "revoked-summary-successor.json"
        materialize_bundle(
            self.protocol_path,
            successor_path,
            successor,
            predecessor_path=revoked_path,
        )
        successor_bundle = load_bundle(
            successor_path,
            protocol=self.protocol,
            predecessor_path=revoked_path,
        )
        successor_report = render_bundle_report(
            self.protocol,
            successor_bundle,
            check_bundle(
                self.protocol_path,
                successor_path,
                predecessor_path=revoked_path,
            ),
            predecessor_path=revoked_path,
        )
        self.assertIn(
            "Current operating metrics: unavailable (summary absent, revoked, tainted, or unscorable)",
            successor_report,
        )

    def test_rescore_successor_preserves_source_bytes_and_old_score(self) -> None:
        builder = core.create_record(
            record_id="builder-0",
            record_type="builder_release",
            epoch_id=self.protocol["epoch"]["epoch_id"],
            sequence=0,
            previous_record_hash=None,
            payload={
                "release_id": "builder-0",
                "release_kind": "builder",
                "revision": "1",
                "artifact_hash": HASH,
                "custody": "builder-custody",
                "allowed_evidence_surface": ["surface"],
            },
        )
        evaluator = core.create_record(
            record_id="evaluator-0",
            record_type="evaluator_release",
            epoch_id=self.protocol["epoch"]["epoch_id"],
            sequence=1,
            previous_record_hash=builder["record_hash"],
            payload=_evaluator("evaluator-0"),
        )
        method = core.create_record(
            record_id="method-0",
            record_type="measurement_method",
            epoch_id=self.protocol["epoch"]["epoch_id"],
            sequence=2,
            previous_record_hash=evaluator["record_hash"],
            payload={
                "method_id": "method-0",
                "revision": "1",
                "artifact_hash": HASH,
                "construct": "synthetic",
                "oracle": "synthetic",
                "parser": "synthetic",
                "aggregation": "synthetic",
                "validity": "declared",
                "reliability": "declared",
                "custody": "method-custody",
            },
        )
        evidence = core.create_record(
            record_id="evidence-0",
            record_type="subject_execution_evidence",
            epoch_id=self.protocol["epoch"]["epoch_id"],
            sequence=3,
            previous_record_hash=method["record_hash"],
            payload={
                "evidence_id": "evidence-0",
                "subject_ref": "subject-0",
                "builder_release_ref": "builder-0",
                "builder_release_hash": builder["record_hash"],
                "task_partition": "screening",
                "task_ref": "task:test",
                "task_hash": self.protocol["partitions"]["screening"]["task_root_hash"],
                "environment_ref": "environment:test",
                "environment_hash": HASH,
                "runner_ref": "runner:test",
                "runner_hash": HASH,
                "exposure_state_ref": "exposure:test",
                "exposure_state_hash": HASH,
                "partition": "screening",
                "surface_refs": ["surface"],
                "artifact_hash": HASH,
                "status": "observed",
            },
            dependency_refs={"builder-0": builder["record_hash"]},
        )
        binding = core.create_record(
            record_id="binding-old",
            record_type="evaluation_binding",
            epoch_id=self.protocol["epoch"]["epoch_id"],
            sequence=4,
            previous_record_hash=evidence["record_hash"],
            payload={
                "binding_id": "binding-old",
                "builder_release_ref": "builder-0",
                "builder_release_hash": builder["record_hash"],
                "evaluator_release_ref": "evaluator-0",
                "evaluator_release_hash": evaluator["record_hash"],
                "method_ref": "method-0",
                "method_hash": method["record_hash"],
                "evidence_ref": "evidence-0",
                "evidence_hash": evidence["record_hash"],
                "task_partition": "screening",
                "task_ref": "task:test",
                "task_hash": self.protocol["partitions"]["screening"]["task_root_hash"],
                "exposure_policy": "screening",
                "analysis_ref": "analysis",
                "analysis_hash": HASH,
                "environment_ref": "environment:test",
                "environment_hash": HASH,
                "runner_ref": "runner:test",
                "runner_hash": HASH,
                "promotion_policy_ref": "promotion",
                "promotion_policy_hash": HASH,
                "exposure_state_ref": "exposure:test",
                "exposure_state_hash": HASH,
                "allowed_evidence_surface": ["surface"],
            },
            dependency_refs={
                "builder-0": builder["record_hash"],
                "evaluator-0": evaluator["record_hash"],
                "method-0": method["record_hash"],
                "evidence-0": evidence["record_hash"],
            },
        )
        old_score = core.create_record(
            record_id="score-old",
            record_type="score_run",
            epoch_id=self.protocol["epoch"]["epoch_id"],
            sequence=5,
            previous_record_hash=binding["record_hash"],
            payload={
                "score_run_id": "score-old",
                "binding_ref": "binding-old",
                "binding_hash": binding["record_hash"],
                "evidence_ref": "evidence-0",
                "evidence_hash": evidence["record_hash"],
                "evaluator_release_ref": "evaluator-0",
                "evaluator_release_hash": evaluator["record_hash"],
                "builder_release_ref": "builder-0",
                "builder_release_hash": builder["record_hash"],
                "method_ref": "method-0",
                "method_hash": method["record_hash"],
                "score": 0.25,
                "score_status": "observed",
                "scoring_actor": "adjudication",
                "partition": "screening",
                "surface_refs": ["surface"],
            },
            dependency_refs={
                "binding-old": binding["record_hash"],
                "evidence-0": evidence["record_hash"],
                "evaluator-0": evaluator["record_hash"],
            },
        )
        self.bundle = core.create_bundle(
            self.protocol,
            bundle_id="bundle-test",
            records=[builder, evaluator, method, evidence, binding, old_score],
        )
        materialize_bundle(self.protocol_path, self.bundle_path, self.bundle)
        source_bytes = self.bundle_path.read_bytes()
        request_path = self.root / "request.json"
        write_json_atomic(
            request_path,
            {
                "evaluator_release": _evaluator("evaluator-1"),
                "score_payload": {
                    "score_run_id": "score-1",
                    "score": 0.5,
                    "builder_release_ref": "builder-0",
                    "builder_release_hash": builder["record_hash"],
                    "evidence_ref": "evidence-0",
                    "evidence_hash": evidence["record_hash"],
                    "method_ref": "method-0",
                    "method_hash": method["record_hash"],
                    "partition": "screening",
                },
                "actor": "adjudication",
                "retained_surfaces": ["surface"],
                "required_surfaces": ["surface"],
                "changes": ["evaluator"],
            },
        )
        output = self.root / "rescore.json"
        result = append_rescore_files(self.protocol_path, self.bundle_path, request_path, output)
        self.assertEqual(self.bundle_path.read_bytes(), source_bytes)
        successor = result["successor"]
        self.assertEqual(
            successor["records"][: len(self.bundle["records"])], self.bundle["records"]
        )
        self.assertEqual(len(successor["records"]), len(self.bundle["records"]) + 3)
        successor_source_bytes = output.read_bytes()
        second_request = self.root / "request-2.json"
        write_json_atomic(
            second_request,
            {
                "evaluator_release": _evaluator("evaluator-2"),
                "score_payload": {
                    "score_run_id": "score-2",
                    "score": 0.75,
                    "builder_release_ref": "builder-0",
                    "builder_release_hash": builder["record_hash"],
                    "evidence_ref": "evidence-0",
                    "evidence_hash": evidence["record_hash"],
                    "method_ref": "method-0",
                    "method_hash": method["record_hash"],
                    "partition": "screening",
                },
                "actor": "adjudication",
                "retained_surfaces": ["surface"],
                "required_surfaces": ["surface"],
                "changes": ["evaluator"],
            },
        )
        second_output = self.root / "rescore-2.json"
        with self.assertRaisesRegex(CoevolutionBundleError, "predecessor_required"):
            append_rescore_files(self.protocol_path, output, second_request, second_output)
        second_result = append_rescore_files(
            self.protocol_path,
            output,
            second_request,
            second_output,
            predecessor_path=self.bundle_path,
        )
        self.assertEqual(output.read_bytes(), successor_source_bytes)
        self.assertEqual(
            second_result["successor"]["records"][: len(successor["records"])],
            successor["records"],
        )
        third_request = self.root / "request-3.json"
        write_json_atomic(
            third_request,
            {
                "evaluator_release": _evaluator("evaluator-3"),
                "score_payload": {
                    "score_run_id": "score-3",
                    "score": 0.9,
                    "builder_release_ref": "builder-0",
                    "builder_release_hash": builder["record_hash"],
                    "evidence_ref": "evidence-0",
                    "evidence_hash": evidence["record_hash"],
                    "method_ref": "method-0",
                    "method_hash": method["record_hash"],
                    "partition": "screening",
                },
                "actor": "adjudication",
                "retained_surfaces": ["surface"],
                "required_surfaces": ["surface"],
                "changes": ["evaluator"],
            },
        )
        third_output = self.root / "rescore-3.json"
        third_result = append_rescore_files(
            self.protocol_path,
            second_output,
            third_request,
            third_output,
            predecessor_paths=[self.bundle_path, output],
        )
        self.assertEqual(
            third_result["successor"]["records"][: len(second_result["successor"]["records"])],
            second_result["successor"]["records"],
        )

    def test_invalid_request_and_tainted_or_self_custodied_rescore_fail_closed(self) -> None:
        invalid = self.root / "invalid-request.json"
        write_json_atomic(invalid, {"evaluator_release": _evaluator("evaluator-1"), "extra": True})
        with self.assertRaisesRegex(CoevolutionBundleError, "unknown_field"):
            append_rescore_files(
                self.protocol_path, self.bundle_path, invalid, self.root / "x.json"
            )
        self_custody = self.root / "self-request.json"
        write_json_atomic(
            self_custody,
            {
                "evaluator_release": _evaluator("evaluator-1", custody="adjudication"),
                "score_payload": {
                    "score_run_id": "score-1",
                    "score": 0.5,
                    "builder_release_ref": "builder-0",
                    "builder_release_hash": HASH,
                    "evidence_ref": "evidence-0",
                    "evidence_hash": HASH,
                    "method_ref": "method-0",
                    "method_hash": HASH,
                    "partition": "screening",
                },
                "actor": "adjudication",
                "retained_surfaces": ["surface"],
                "required_surfaces": ["surface"],
                "changes": ["evaluator"],
            },
        )
        with self.assertRaisesRegex(CoevolutionBundleError, "self_certification"):
            append_rescore_files(
                self.protocol_path, self.bundle_path, self_custody, self.root / "x.json"
            )

    def test_contract_registry_is_unchanged_and_adapter_imports_are_effect_free(self) -> None:
        self.assertEqual(len(validation.SCHEMA_FILES), 5)
        source = Path(__file__).parents[1] / "src" / "ael" / "coevolution_bundle.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        forbidden = {
            "subprocess",
            "socket",
            "requests",
            "random",
            "time",
            "ael.validation",
            "ael.result_surface",
        }
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        self.assertTrue(imported.isdisjoint(forbidden), imported & forbidden)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
