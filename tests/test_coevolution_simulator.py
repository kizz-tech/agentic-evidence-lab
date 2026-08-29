from __future__ import annotations

import ast
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ael import coevolution as core
from ael.coevolution_bundle import load_bundle, load_protocol, materialize_bundle
from ael.coevolution_simulator import (
    ARM_ORDER,
    RNG_ALGORITHM,
    SCENARIO_CATALOG,
    SplitMix64,
    _aggregate_arm_scenario,
    _bridge_anchor_truth,
    _bridge_cell_scores,
    default_protocol,
    derive_stream_seed,
    simulate,
    simulate_scenario,
)


class CoevolutionSimulatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.protocol = default_protocol(seed=17)

    def test_protocol_has_six_arms_and_catalog(self) -> None:
        frozen = core.freeze_protocol(self.protocol)
        self.assertEqual(tuple(frozen["arms"]), ARM_ORDER)
        scenarios = frozen["simulation"]["scenarios"]
        self.assertEqual(tuple(item["name"] for item in scenarios), SCENARIO_CATALOG)
        self.assertTrue(all(set(item) == {"name", "tasks", "replicates"} for item in scenarios))
        self.assertEqual(len(frozen["contrasts"]), 15)
        self.assertTrue(any(item["estimand_kind"] == "component" for item in frozen["contrasts"]))
        self.assertTrue(
            any(item["estimand_kind"] == "policy_package" for item in frozen["contrasts"])
        )

    def test_default_protocol_closes_scenarios_and_preserves_custom_bounds(self) -> None:
        protocol = default_protocol(
            seed=17,
            scenarios=["null", {"name": "useful", "tasks": 4, "replicates": 2}],
        )
        self.assertEqual(
            protocol["simulation"]["scenarios"],
            [
                {"name": "null", "tasks": 16, "replicates": 3},
                {"name": "useful", "tasks": 4, "replicates": 2},
            ],
        )
        self.assertTrue(
            all(
                set(item) == {"name", "tasks", "replicates"}
                for item in protocol["simulation"]["scenarios"]
            )
        )

    def test_identical_input_is_byte_deterministic(self) -> None:
        first = simulate(copy.deepcopy(self.protocol))
        second = simulate(copy.deepcopy(self.protocol))
        first_bytes = core.canonical_json_bytes(first, domain="test-bundle")
        self.assertEqual(first_bytes, core.canonical_json_bytes(second, domain="test-bundle"))
        self.assertEqual(first["bundle_hash"], second["bundle_hash"])

    def test_seed_change_changes_bundle(self) -> None:
        first = simulate(self.protocol)
        changed = default_protocol(seed=18)
        second = simulate(changed)
        self.assertNotEqual(first["bundle_hash"], second["bundle_hash"])

    def test_arm_mapping_order_does_not_change_stream_or_bundle(self) -> None:
        reordered = copy.deepcopy(self.protocol)
        reordered["arms"] = {arm: reordered["arms"][arm] for arm in reversed(ARM_ORDER)}
        first = simulate(self.protocol)
        second = simulate(reordered)
        self.assertEqual(first["bundle_hash"], second["bundle_hash"])
        self.assertEqual(
            derive_stream_seed(17, "null", 0, "A0", "task:0", "anchor_truth"),
            derive_stream_seed(17, "null", 0, "A0", "task:0", "anchor_truth"),
        )

    def test_stream_derivation_is_independent_of_unrelated_arm(self) -> None:
        baseline = derive_stream_seed(17, "null", 0, "A0", "task:0", "candidate")
        # Adding a named stream for an unrelated arm does not consume A0's stream.
        _ = derive_stream_seed(17, "null", 0, "A5", "task:0", "candidate")
        self.assertEqual(baseline, derive_stream_seed(17, "null", 0, "A0", "task:0", "candidate"))

    def test_bridge_truth_is_independent_of_evaluator_cells(self) -> None:
        threshold = 0.64
        truth = _bridge_anchor_truth(17, "baseline", "near_threshold", threshold)
        cells_a = _bridge_cell_scores(
            truth,
            decision_threshold=threshold,
            rng=SplitMix64(
                derive_stream_seed(17, "baseline", 0, "A5", "bridge-cells-a", "evaluator")
            ),
        )
        cells_b = _bridge_cell_scores(
            truth,
            decision_threshold=threshold,
            rng=SplitMix64(
                derive_stream_seed(17, "baseline", 0, "A5", "bridge-cells-b", "evaluator")
            ),
        )
        self.assertNotEqual(cells_a, cells_b)
        self.assertEqual(truth, _bridge_anchor_truth(17, "baseline", "near_threshold", threshold))
        self.assertNotEqual(cells_a["b0e1"], truth[0])
        self.assertNotEqual(cells_a["b1e1"], truth[1])
        self.assertNotEqual(
            truth[0] >= threshold,
            truth[1] >= threshold,
            "near-threshold frozen truth should exercise both decisions",
        )

    def test_bundle_contains_representative_ledger_and_count_identities(self) -> None:
        bundle = simulate(self.protocol)
        record_types = {record["record_type"] for record in bundle["records"]}
        self.assertTrue(
            {
                "builder_release",
                "evaluator_release",
                "challenger_release",
                "anchor_release",
                "measurement_method",
                "evaluation_binding",
                "subject_execution_evidence",
                "score_run",
                "anchor_observation",
                "exposure_event",
                "bridge_observation",
                "comparability_decision",
                "independence_assessment",
                "promotion_transition",
                "trajectory_summary",
                "contrast_summary",
                "deletion_tombstone",
            }.issubset(record_types)
        )
        summary = next(
            record for record in bundle["records"] if record["record_type"] == "contrast_summary"
        )
        self.assertEqual(
            summary["payload"]["aggregation_version"], core.CONTRAST_SUMMARY_AGGREGATION_VERSION
        )
        self.assertEqual(len(summary["dependency_refs"]), len(ARM_ORDER) * len(SCENARIO_CATALOG))
        trajectories = {
            (record["payload"]["arm"], record["payload"]["scenario_ref"]): record
            for record in bundle["records"]
            if record["record_type"] == "trajectory_summary"
        }
        for arm in ARM_ORDER:
            for scenario in SCENARIO_CATALOG:
                trajectory = trajectories[(arm, f"scenario:{scenario}")]
                counts = trajectory["payload"]["counts"]
                disposition_total = sum(counts["disposition"].values())
                self.assertGreaterEqual(disposition_total, 0)
                self.assertLessEqual(
                    sum(counts["promotion"].values()), counts["disposition"]["eligible"]
                )
                self.assertEqual(
                    counts["bridge"]["attempted"],
                    counts["bridge"]["passed"]
                    + counts["bridge"]["failed"]
                    + counts["bridge"]["unknown"],
                )
                self.assertEqual(sum(counts["candidate_opportunities"].values()), 3)
                self.assertEqual(
                    set(counts["optional_stopping"]), {"events", "eligible_replicates"}
                )
                self.assertEqual(
                    set(trajectory["payload"]["primary_endpoint"]),
                    {"sum_ppm", "observed_count"},
                )

    def test_blind_spot_and_exploit_change_score_not_anchor(self) -> None:
        blind_a0 = simulate_scenario(self.protocol, "shared_blind_spot", "A0")
        blind_a2 = simulate_scenario(self.protocol, "shared_blind_spot", "A2")
        self.assertEqual(
            blind_a0["metrics"]["anchor_utility_mean"], blind_a2["metrics"]["anchor_utility_mean"]
        )
        self.assertNotEqual(
            blind_a0["metrics"]["evaluator_score_mean"], blind_a2["metrics"]["evaluator_score_mean"]
        )
        exploit_a0 = simulate_scenario(self.protocol, "evaluator_exploit", "A0")
        exploit_a2 = simulate_scenario(self.protocol, "evaluator_exploit", "A2")
        self.assertEqual(
            exploit_a0["metrics"]["anchor_utility_mean"],
            exploit_a2["metrics"]["anchor_utility_mean"],
        )
        self.assertGreater(
            exploit_a2["metrics"]["evaluator_score_mean"],
            exploit_a0["metrics"]["evaluator_score_mean"],
        )

    def test_truth_family_keeps_proxy_only_scenarios_arm_blinded(self) -> None:
        baseline = simulate_scenario(self.protocol, "null", "A0")
        for scenario in ("shared_blind_spot", "evaluator_exploit", "feedback_leakage"):
            observed = simulate_scenario(self.protocol, scenario, "A0")
            self.assertEqual(
                baseline["metrics"]["anchor_utility_mean"],
                observed["metrics"]["anchor_utility_mean"],
            )
        useful_a0 = simulate_scenario(self.protocol, "useful", "A0")
        useful_a1 = simulate_scenario(self.protocol, "useful", "A1")
        self.assertGreater(
            useful_a1["metrics"]["anchor_utility_mean"],
            useful_a0["metrics"]["anchor_utility_mean"],
        )

    def test_leakage_taints_without_changing_arm_blinded_anchor(self) -> None:
        a0 = simulate_scenario(self.protocol, "feedback_leakage", "A0")
        a1 = simulate_scenario(self.protocol, "feedback_leakage", "A1")
        self.assertGreater(a0["metrics"]["tainted"], 0)
        self.assertEqual(a0["metrics"]["anchor_utility_mean"], a1["metrics"]["anchor_utility_mean"])

    def test_challenger_coverage_is_monotonic_in_paired_fixture(self) -> None:
        a4 = simulate_scenario(self.protocol, "evaluator_exploit", "A4")
        a5 = simulate_scenario(self.protocol, "evaluator_exploit", "A5")
        detected_a4 = sum(int(item["detected_exploit"]) for item in a4["observations"])
        detected_a5 = sum(int(item["detected_exploit"]) for item in a5["observations"])
        self.assertGreaterEqual(detected_a5, detected_a4)

    def test_optional_stopping_is_diagnostic(self) -> None:
        result = simulate_scenario(self.protocol, "optional_stopping", "A5")
        self.assertFalse(result["metrics"]["diagnostic"]["causal_comparison_eligible"])
        self.assertGreater(result["metrics"]["optional_stopping"], 0)
        self.assertLess(result["metrics"]["attempted"], 16)

    def test_optional_stopping_rate_uses_replicate_denominator_and_cost_is_honest(self) -> None:
        protocol = default_protocol(seed=17, scenarios=["optional_stopping"])
        bundle = simulate(protocol)
        summary = next(
            record for record in bundle["records"] if record["record_type"] == "contrast_summary"
        )
        self.assertEqual(
            summary["payload"]["aggregation_version"], core.CONTRAST_SUMMARY_AGGREGATION_VERSION
        )
        trajectory = next(
            record
            for record in bundle["records"]
            if record["record_type"] == "trajectory_summary" and record["payload"]["arm"] == "A0"
        )
        self.assertEqual(trajectory["payload"]["budget"]["delta"], -42.0)
        self.assertFalse(
            trajectory["payload"]["budget"]["actual"] == trajectory["payload"]["budget"]["target"]
        )
        self.assertEqual(
            _aggregate_arm_scenario(core.freeze_protocol(protocol), "optional_stopping", "A0")[
                "optional_stopping_rate"
            ],
            {"count": 3, "denominator": 3, "rate": 1.0},
        )
        self.assertEqual(
            trajectory["payload"]["counts"]["optional_stopping"],
            {"events": 3, "eligible_replicates": 3},
        )

    def test_prebridge_rejections_do_not_materialize_bridge_panel(self) -> None:
        for scenario in (
            "null",
            "feedback_leakage",
            "optional_stopping",
            "poisoning",
            "forbidden_effect",
        ):
            with self.subTest(scenario=scenario):
                bundle = simulate(default_protocol(seed=17, scenarios=[scenario]))
                self.assertFalse(
                    any(
                        record["record_type"] == "bridge_observation"
                        for record in bundle["records"]
                    )
                )
                self.assertFalse(
                    any(
                        record["payload"].get("partition") == "bridge"
                        for record in bundle["records"]
                    )
                )
                self.assertFalse(
                    any(
                        record["record_type"] == "exposure_event"
                        and record["payload"].get("partition") == "bridge"
                        for record in bundle["records"]
                    )
                )
                trajectory = next(
                    record
                    for record in bundle["records"]
                    if record["record_type"] == "trajectory_summary"
                    and record["payload"]["arm"] == "A5"
                    and record["payload"]["scenario_ref"] == f"scenario:{scenario}"
                )
                self.assertEqual(
                    trajectory["payload"]["counts"]["bridge"],
                    {"attempted": 0, "passed": 0, "failed": 0, "unknown": 0, "later_reversal": 0},
                )

    def test_frozen_threshold_controls_promotion_and_bridge(self) -> None:
        protocol = default_protocol(seed=1, scenarios=["null"])
        protocol["decision_rule"]["threshold"] = 0.5
        bundle = simulate(protocol)
        bridge = next(
            record for record in bundle["records"] if record["record_type"] == "bridge_observation"
        )
        self.assertEqual(bridge["payload"]["decision_threshold"], 0.5)
        transitions = [
            record["payload"]["to_state"]
            for record in bundle["records"]
            if record["record_type"] == "promotion_transition"
            and record["payload"]["candidate_ref"] == "builder:A5:v2"
        ]
        self.assertIn("promote", transitions)

    def test_simulate_scenario_rejects_out_of_range_replicates(self) -> None:
        protocol = default_protocol(seed=17, scenarios=[{"name": "null", "replicates": 1}])
        for replicate in (-1, 1, 999, True):
            with self.subTest(replicate=replicate), self.assertRaises(ValueError):
                simulate_scenario(protocol, "null", "A0", replicate=replicate)

    def test_raw_promotions_have_their_replicate_level_gates(self) -> None:
        for scenario in SCENARIO_CATALOG:
            for arm in ARM_ORDER:
                with self.subTest(scenario=scenario, arm=arm):
                    metrics = simulate_scenario(self.protocol, scenario, arm)["metrics"]
                    if metrics["promoted"] <= 0:
                        continue
                    self.assertGreater(metrics["disposition"]["eligible"], 0)
                    self.assertEqual(metrics["tainted"], 0)
                    self.assertEqual(metrics["critical_failures"], 0)
                    self.assertEqual(metrics["forbidden_effect_attempted"], 0)
                    self.assertEqual(metrics["optional_stopping"], 0)

    def test_missingness_stress_keeps_endpoints_but_blocks_contrasts(self) -> None:
        protocol = default_protocol(seed=17)
        bundle = simulate(protocol)
        trajectories = [
            record["payload"]
            for record in bundle["records"]
            if record["record_type"] == "trajectory_summary"
        ]
        missing_rows = [
            row for row in trajectories if row["scenario_ref"] == "scenario:missingness"
        ]
        self.assertEqual(len(missing_rows), len(ARM_ORDER))
        for row in missing_rows:
            self.assertLess(row["primary_endpoint"]["observed_count"], 16 * 3)
            self.assertIsInstance(row["primary_endpoint"]["sum_ppm"], int)
        seal = next(
            record for record in bundle["records"] if record["record_type"] == "contrast_summary"
        )
        self.assertEqual(
            {item["status"] for item in seal["payload"]["contrasts"]}, {"not_estimable"}
        )
        self.assertEqual(
            {item["reason"] for item in seal["payload"]["contrasts"]}, {"missing_endpoint"}
        )
        self.assertTrue(
            all(item["endpoint_delta_ppm"] is None for item in seal["payload"]["contrasts"])
        )

    def test_closed_opportunities_endpoint_and_kernel_estimands(self) -> None:
        protocol = default_protocol(seed=17, scenarios=["useful"])
        bundle = simulate(protocol)
        rows = [
            record["payload"]
            for record in bundle["records"]
            if record["record_type"] == "trajectory_summary"
        ]
        for row in rows:
            counts = row["counts"]
            self.assertEqual(sum(counts["candidate_opportunities"].values()), 3)
            self.assertEqual(
                row["primary_endpoint"]["sum_ppm"],
                _aggregate_arm_scenario(
                    core.freeze_protocol(protocol),
                    row["scenario_ref"].removeprefix("scenario:"),
                    row["arm"],
                )["anchor_utility_sum"],
            )
            self.assertEqual(
                row["primary_endpoint"]["observed_count"],
                _aggregate_arm_scenario(
                    core.freeze_protocol(protocol),
                    row["scenario_ref"].removeprefix("scenario:"),
                    row["arm"],
                )["anchor_observations"],
            )
        kernel = core.derive_operating_metrics(rows)
        self.assertEqual(kernel["false_promotion_share"]["count"], 0)
        self.assertEqual(kernel["false_promotion_share"]["denominator"], 18)
        self.assertEqual(kernel["false_promotion_share"]["rate"], 0.0)
        self.assertEqual(kernel["invalid_candidate_promotion_rate"]["count"], 0)
        self.assertEqual(kernel["invalid_candidate_promotion_rate"]["denominator"], 0)
        self.assertIsNone(kernel["invalid_candidate_promotion_rate"]["rate"])
        self.assertNotEqual(
            (
                kernel["false_promotion_share"]["count"],
                kernel["false_promotion_share"]["denominator"],
            ),
            (
                kernel["invalid_candidate_promotion_rate"]["count"],
                kernel["invalid_candidate_promotion_rate"]["denominator"],
            ),
        )
        seal = next(
            record for record in bundle["records"] if record["record_type"] == "contrast_summary"
        )
        self.assertEqual(
            seal["payload"]["aggregation_version"], core.CONTRAST_SUMMARY_AGGREGATION_VERSION
        )
        self.assertEqual(
            seal["payload"]["contrasts"], core.derive_contrast_diagnostics(protocol, rows)
        )

    def test_bridge_has_actual_e0_e1_scores_on_same_retained_evidence(self) -> None:
        bundle = simulate(default_protocol(seed=17, scenarios=["useful"]))
        records = {record["record_id"]: record for record in bundle["records"]}
        bridge = next(
            record for record in bundle["records"] if record["record_type"] == "bridge_observation"
        )
        dependencies = {item["record_id"] for item in bridge["dependency_refs"]}
        payload = bridge["payload"]
        self.assertEqual(payload["old_builder_ref"], "builder:A5:v1")
        self.assertEqual(payload["new_builder_ref"], "builder:A5:v2")
        self.assertEqual(payload["old_evaluator_ref"], "evaluator:A5:v1")
        self.assertEqual(payload["new_evaluator_ref"], "evaluator:A5:v2")
        self.assertIn("builder:A5:v1", dependencies)
        self.assertIn("builder:A5:v2", dependencies)
        self.assertIn("evaluator:A5:v1", dependencies)
        self.assertIn("evaluator:A5:v2", dependencies)
        expected_strata = {"good", "bad", "exploit", "semantic_mutant", "near_threshold"}
        self.assertEqual({item["stratum"] for item in payload["strata"]}, expected_strata)
        self.assertEqual(sum(item["weight"] for item in payload["strata"]), 1.0)
        frozen_strata = {item["stratum"]: item for item in self.protocol["bridge"]["strata"]}
        self.assertEqual(
            len({item["task_root_hash"] for item in frozen_strata.values()}),
            len(expected_strata),
        )
        observed_task_roots: set[str] = set()
        score_ids: set[str] = set()
        for item in payload["strata"]:
            self.assertEqual(
                {key for key in item if key.endswith("_score_ref")},
                {"b0e0_score_ref", "b0e1_score_ref", "b1e0_score_ref", "b1e1_score_ref"},
            )
            self.assertEqual(
                {key for key in item if key.endswith("_anchor_ref")},
                {"b0_anchor_ref", "b1_anchor_ref"},
            )
            old_evidence = records[item["old_evidence_ref"]]
            new_evidence = records[item["new_evidence_ref"]]
            bridge_exposure = records[f"exposure:A5:bridge:{item['stratum']}"]
            self.assertIn(bridge_exposure["record_id"], dependencies)
            self.assertEqual(bridge_exposure["payload"]["target_ref"], item["b1e1_score_ref"])
            expected_task_root = frozen_strata[item["stratum"]]["task_root_hash"]
            self.assertEqual(old_evidence["payload"]["task_hash"], expected_task_root)
            self.assertEqual(new_evidence["payload"]["task_hash"], expected_task_root)
            self.assertEqual(
                old_evidence["payload"]["task_ref"],
                f"task-pack:bridge:{item['stratum']}:stage0",
            )
            observed_task_roots.add(old_evidence["payload"]["task_hash"])
            for field in (
                "task_ref",
                "task_hash",
                "environment_ref",
                "environment_hash",
                "runner_ref",
                "runner_hash",
                "exposure_state_ref",
                "exposure_state_hash",
            ):
                self.assertEqual(old_evidence["payload"][field], new_evidence["payload"][field])
            expected_axes = {
                "b0e0": ("builder:A5:v1", "evaluator:A5:v1", item["old_evidence_ref"]),
                "b0e1": ("builder:A5:v1", "evaluator:A5:v2", item["old_evidence_ref"]),
                "b1e0": ("builder:A5:v2", "evaluator:A5:v1", item["new_evidence_ref"]),
                "b1e1": ("builder:A5:v2", "evaluator:A5:v2", item["new_evidence_ref"]),
            }
            for cell, (builder_ref, evaluator_ref, evidence_ref) in expected_axes.items():
                score = records[item[f"{cell}_score_ref"]]
                score_ids.add(score["record_id"])
                self.assertIn(score["record_id"], dependencies)
                self.assertEqual(score["payload"]["builder_release_ref"], builder_ref)
                self.assertEqual(score["payload"]["evaluator_release_ref"], evaluator_ref)
                self.assertEqual(score["payload"]["evidence_ref"], evidence_ref)
                self.assertEqual(score["payload"]["partition"], "bridge")
            for anchor_key, builder_ref in (
                ("b0_anchor", "builder:A5:v1"),
                ("b1_anchor", "builder:A5:v2"),
            ):
                anchor_record = records[item[f"{anchor_key}_ref"]]
                self.assertIn(anchor_record["record_id"], dependencies)
                self.assertEqual(anchor_record["payload"]["candidate_ref"], builder_ref)
                self.assertEqual(anchor_record["payload"]["partition"], "bridge")
                self.assertNotIn("confirmation_consumption_ref", anchor_record["payload"])
            b0_anchor = records[item["b0_anchor_ref"]]["payload"]
            b1_anchor = records[item["b1_anchor_ref"]]["payload"]
            self.assertNotEqual(b0_anchor["value"], b1_anchor["value"])
            threshold = payload["decision_threshold"]
            anchor_agreement = 0.25 * sum(
                (
                    float(
                        (records[item["b0e0_score_ref"]]["payload"]["score"] >= threshold)
                        == (b0_anchor["value"] >= threshold)
                    ),
                    float(
                        (records[item["b0e1_score_ref"]]["payload"]["score"] >= threshold)
                        == (b0_anchor["value"] >= threshold)
                    ),
                    float(
                        (records[item["b1e0_score_ref"]]["payload"]["score"] >= threshold)
                        == (b1_anchor["value"] >= threshold)
                    ),
                    float(
                        (records[item["b1e1_score_ref"]]["payload"]["score"] >= threshold)
                        == (b1_anchor["value"] >= threshold)
                    ),
                )
            )
            self.assertEqual(anchor_agreement, 1.0)
        self.assertEqual(len(score_ids), 20)
        self.assertNotIn("score:A5:confirmation:anchor", records)
        self.assertEqual(payload["global_shift_interval"][0], payload["global_shift_interval"][1])
        self.assertEqual(payload["interaction_interval"][0], payload["interaction_interval"][1])
        self.assertEqual(payload["outcome"], "bridge_comparable")
        self.assertEqual(len(observed_task_roots), len(expected_strata))

    def test_bridge_anchor_decision_contradiction_cannot_claim_comparable(self) -> None:
        bundle = simulate(default_protocol(seed=17, scenarios=["useful"]))
        bridge = next(
            record for record in bundle["records"] if record["record_type"] == "bridge_observation"
        )
        contradicted = copy.deepcopy(bridge["payload"])
        contradicted["anchor_agreement"] = 0.0
        result = core.evaluate_bridge(
            contradicted,
            tolerances={"global_shift": 0.05, "interaction": 0.05, "agreement": 0.90},
            expected_strata=default_protocol(seed=17, scenarios=["useful"])["bridge"]["strata"],
        )
        self.assertNotEqual(result["outcome"], "bridge_comparable")

    def test_bridge_cell_mutation_does_not_change_anchor_truth_or_record_hashes(self) -> None:
        protocol = default_protocol(seed=17, scenarios=["useful"])
        baseline = simulate(protocol)
        baseline_records = {record["record_id"]: record for record in baseline["records"]}

        def shifted_cells(
            truth_values: tuple[float, float], *, decision_threshold: float, rng: SplitMix64
        ) -> dict[str, float]:
            original = _bridge_cell_scores(
                truth_values, decision_threshold=decision_threshold, rng=rng
            )
            # A uniform bounded shift changes evaluator scores while retaining
            # every frozen threshold decision and bridge tolerance.
            return {cell: round(value + 0.001, 6) for cell, value in original.items()}

        with patch("ael.coevolution_simulator._bridge_cell_scores", side_effect=shifted_cells):
            changed = simulate(protocol)
        changed_records = {record["record_id"]: record for record in changed["records"]}
        anchor_ids = {
            record["record_id"]
            for record in baseline["records"]
            if record["record_type"] == "anchor_observation"
            and record["payload"]["partition"] == "bridge"
        }
        self.assertTrue(anchor_ids)
        for anchor_id in anchor_ids:
            self.assertEqual(
                baseline_records[anchor_id]["record_hash"],
                changed_records[anchor_id]["record_hash"],
            )
            self.assertEqual(
                baseline_records[anchor_id]["payload"]["value"],
                changed_records[anchor_id]["payload"]["value"],
            )
        self.assertNotEqual(baseline["bundle_hash"], changed["bundle_hash"])

    def test_bridge_raw_tolerances_determine_outcome(self) -> None:
        normal = simulate(default_protocol(seed=17, scenarios=["useful"]))
        normal_bridge = next(
            record for record in normal["records"] if record["record_type"] == "bridge_observation"
        )
        self.assertEqual(normal_bridge["payload"]["outcome"], "bridge_comparable")
        strict = default_protocol(seed=17, scenarios=["useful"])
        strict["bridge"]["global_shift_tolerance"] = 0.0
        strict["bridge"]["interaction_tolerance"] = 0.0
        strict_bundle = simulate(strict)
        strict_bridge = next(
            record
            for record in strict_bundle["records"]
            if record["record_type"] == "bridge_observation"
        )
        self.assertEqual(strict_bridge["payload"]["outcome"], "new_epoch_not_comparable")

    def test_bridge_reason_is_preconfirmation_and_ordered_before_confirmation(self) -> None:
        bundle = simulate(default_protocol(seed=17, scenarios=["useful"]))
        records = bundle["records"]
        bridge = next(record for record in records if record["record_type"] == "bridge_observation")
        decision = next(
            record for record in records if record["record_type"] == "comparability_decision"
        )
        confirmation = next(
            record
            for record in records
            if record["record_type"] == "promotion_transition"
            and record["payload"]["to_state"] == "confirmation_eligible"
        )
        reason = decision["payload"]["reason"].casefold()
        self.assertNotIn("confirmation", reason)
        self.assertLess(bridge["sequence"], decision["sequence"])
        self.assertLess(decision["sequence"], confirmation["sequence"])

    def test_shared_blind_spot_failed_bridge_opens_new_measurement_epoch(self) -> None:
        bundle = simulate(default_protocol(seed=17, scenarios=["shared_blind_spot"]))
        transitions = [
            record
            for record in bundle["records"]
            if record["record_type"] == "promotion_transition"
            and record["payload"]["candidate_ref"] == "builder:A5:v2"
        ]
        bridge = next(
            record for record in bundle["records"] if record["record_type"] == "bridge_observation"
        )
        self.assertEqual(bridge["payload"]["outcome"], "new_epoch_not_comparable")
        self.assertEqual(
            [record["payload"]["to_state"] for record in transitions],
            [
                "development_eligible",
                "screening_pass",
                "bridge_eligible",
                "new_measurement_epoch",
            ],
        )
        self.assertFalse(
            any(record["payload"]["to_state"] == "confirmation_eligible" for record in transitions)
        )
        terminal = transitions[-1]
        self.assertLess(bridge["sequence"], terminal["sequence"])
        self.assertIn(bridge["record_id"], terminal["payload"]["evidence_refs"])
        trajectory = next(
            record
            for record in bundle["records"]
            if record["record_type"] == "trajectory_summary"
            and record["payload"]["arm"] == "A5"
            and record["payload"]["scenario_ref"] == "scenario:shared_blind_spot"
        )
        self.assertGreater(trajectory["payload"]["counts"]["bridge"]["failed"], 0)
        self.assertEqual(trajectory["payload"]["counts"]["bridge"]["passed"], 0)

    def test_evidence_commitment_and_projection_expose_taint(self) -> None:
        useful = simulate(default_protocol(seed=17, scenarios=["useful"]))
        leakage_protocol = default_protocol(seed=17, scenarios=["feedback_leakage"])
        leakage = simulate(leakage_protocol)
        useful_evidence = next(
            record
            for record in useful["records"]
            if record["record_type"] == "subject_execution_evidence"
            and record["payload"]["partition"] == "screening"
            and record["payload"]["builder_release_ref"] == "builder:A5:v1"
        )
        leakage_evidence = next(
            record
            for record in leakage["records"]
            if record["record_type"] == "subject_execution_evidence"
            and record["payload"]["partition"] == "screening"
            and record["payload"]["builder_release_ref"] == "builder:A5:v1"
        )
        self.assertNotEqual(
            useful_evidence["payload"]["artifact_hash"],
            leakage_evidence["payload"]["artifact_hash"],
        )
        leakage_exposure = next(
            record for record in leakage["records"] if record["record_type"] == "exposure_event"
        )
        self.assertTrue(leakage_exposure["payload"]["tainted"])
        projection = core.project_bundle(leakage, protocol=leakage_protocol)
        self.assertIn(leakage_exposure["record_id"], projection["tainted_record_ids"])

    def test_forbidden_effect_has_only_blocked_not_dispatched_ledger_facts(self) -> None:
        protocol = default_protocol(seed=17, scenarios=["forbidden_effect"])
        bundle = simulate(protocol)
        effects = [
            record for record in bundle["records"] if record["record_type"] == "effect_attempt"
        ]
        self.assertEqual(len(effects), 3)  # A5 representative x three deterministic replicates
        self.assertTrue(all(item["payload"]["disposition"] == "blocked" for item in effects))
        self.assertTrue(
            all(item["payload"]["postcondition_status"] == "not_dispatched" for item in effects)
        )
        self.assertTrue(all("receipt_ref" not in item["payload"] for item in effects))
        self.assertEqual(
            {item["payload"]["candidate_ref"] for item in effects},
            {"builder:A5:forbidden:v1"},
        )
        reject = next(
            record
            for record in bundle["records"]
            if record["record_type"] == "promotion_transition"
            and record["payload"]["to_state"] == "screening_reject"
        )
        self.assertLess(max(item["sequence"] for item in effects), reject["sequence"])
        self.assertTrue(
            {item["record_id"] for item in effects}.issubset(
                set(reject["payload"]["evidence_refs"])
            )
        )
        summary = next(
            record for record in bundle["records"] if record["record_type"] == "contrast_summary"
        )
        self.assertEqual(
            summary["payload"]["aggregation_version"], core.CONTRAST_SUMMARY_AGGREGATION_VERSION
        )
        # The closed core summary intentionally carries only trajectory count
        # inputs; the representative ledger still proves blocked/no-dispatch
        # effects, while bulk counts are retained in the simulator's rich
        # internal metrics rather than free-form summary payloads.
        self.assertEqual(len(effects), 3)
        self.assertFalse(
            any(
                record["payload"].get("to_state") == "promote"
                for record in bundle["records"]
                if record["record_type"] == "promotion_transition"
            )
        )

    def test_promotions_follow_selected_observed_scenario(self) -> None:
        useful = simulate(default_protocol(seed=17, scenarios=["useful"]))
        self.assertTrue(
            any(
                record["payload"]["to_state"] == "promote"
                for record in useful["records"]
                if record["record_type"] == "promotion_transition"
            )
        )
        for scenario in ("null", "evaluator_exploit", "poisoning", "forbidden_effect"):
            bundle = simulate(default_protocol(seed=17, scenarios=[scenario]))
            self.assertFalse(
                any(
                    record["payload"]["to_state"] == "promote"
                    for record in bundle["records"]
                    if record["record_type"] == "promotion_transition"
                ),
                scenario,
            )

    def test_confirmation_is_single_use_and_only_final_promote_consumes_it(self) -> None:
        bundle = simulate(default_protocol(seed=17, scenarios=["useful"]))
        records = {record["record_id"]: record for record in bundle["records"]}
        eligible = next(
            record
            for record in bundle["records"]
            if record["record_type"] == "promotion_transition"
            and record["payload"]["to_state"] == "confirmation_eligible"
        )
        promote = next(
            record
            for record in bundle["records"]
            if record["record_type"] == "promotion_transition"
            and record["payload"]["to_state"] == "promote"
        )
        eligible_evidence = [
            records[record_id] for record_id in eligible["payload"]["evidence_refs"]
        ]
        self.assertFalse(
            any(
                record["record_type"] in {"confirmation_consumption", "anchor_observation"}
                or (
                    record["record_type"] == "subject_execution_evidence"
                    and record["payload"]["partition"] == "confirmation"
                )
                for record in eligible_evidence
            )
        )
        final_evidence = [records[record_id] for record_id in promote["payload"]["evidence_refs"]]
        confirmations = [
            record
            for record in final_evidence
            if record["record_type"] == "confirmation_consumption"
        ]
        anchors = [
            record
            for record in final_evidence
            if record["record_type"] == "anchor_observation"
            and record["payload"]["partition"] == "confirmation"
        ]
        packs = [
            record
            for record in final_evidence
            if record["record_type"] == "subject_execution_evidence"
            and record["payload"]["partition"] == "confirmation"
        ]
        self.assertEqual(len(confirmations), 1)
        self.assertEqual(len(anchors), 1)
        self.assertEqual(len(packs), 1)
        self.assertEqual(
            anchors[0]["payload"]["confirmation_consumption_ref"], confirmations[0]["record_id"]
        )
        self.assertEqual(confirmations[0]["payload"]["candidate_ref"], "builder:A5:v2")
        self.assertEqual(anchors[0]["payload"]["candidate_ref"], "builder:A5:v2")
        self.assertLess(eligible["sequence"], packs[0]["sequence"])
        self.assertLess(packs[0]["sequence"], promote["sequence"])
        self.assertEqual(promote["payload"]["confirmation_status"], "single_use")

    def test_confirmation_sample_is_partition_separated_from_screening(self) -> None:
        frozen = core.freeze_protocol(default_protocol(seed=17, scenarios=["useful"]))
        screening = _aggregate_arm_scenario(frozen, "useful", "A5", partition="screening")
        confirmation = _aggregate_arm_scenario(frozen, "useful", "A5", partition="confirmation")
        self.assertNotEqual(screening["anchor_utility_mean"], confirmation["anchor_utility_mean"])
        self.assertNotEqual(screening["evaluator_score_mean"], confirmation["evaluator_score_mean"])
        bundle = simulate(default_protocol(seed=17, scenarios=["useful"]))
        evidence = next(
            record
            for record in bundle["records"]
            if record["record_type"] == "subject_execution_evidence"
            and record["record_id"] == "evidence:A5:confirmation:pack"
        )
        screening_evidence = next(
            record
            for record in bundle["records"]
            if record["record_type"] == "subject_execution_evidence"
            and record["record_id"] == "evidence:A5:screening:sample"
        )
        anchor = next(
            record
            for record in bundle["records"]
            if record["record_type"] == "anchor_observation"
            and record["record_id"] == "anchor-observation:A5:confirmation:v1"
        )
        self.assertEqual(evidence["payload"]["task_partition"], "confirmation")
        self.assertNotEqual(
            evidence["payload"]["artifact_hash"], screening_evidence["payload"]["artifact_hash"]
        )
        self.assertEqual(anchor["payload"]["value"], confirmation["anchor_utility_mean"])

    def test_bridge_b1_candidate_has_its_own_screening_lineage(self) -> None:
        bundle = simulate(default_protocol(seed=17, scenarios=["useful"]))
        records = {record["record_id"]: record for record in bundle["records"]}
        candidate = records["builder:A5:v2"]
        b0_screening = records["evidence:A5:screening:sample"]
        b1_screening = records["evidence:A5:screening:candidate-v2"]
        b1_binding = records["binding:A5:screening:candidate-v2"]
        b1_score = records["score:A5:screening:candidate-v2"]
        b1_exposure = records["exposure:A5:screening:v1"]
        self.assertEqual(candidate["payload"]["parent_release_ref"], "builder:A5:v1")
        self.assertNotEqual(
            b1_screening["payload"]["artifact_hash"], b0_screening["payload"]["artifact_hash"]
        )
        self.assertEqual(b1_screening["payload"]["builder_release_ref"], candidate["record_id"])
        self.assertEqual(b1_binding["payload"]["builder_release_ref"], candidate["record_id"])
        self.assertEqual(b1_score["payload"]["builder_release_ref"], candidate["record_id"])
        b1_refs = {
            b1_screening["record_id"],
            b1_binding["record_id"],
            b1_score["record_id"],
            b1_exposure["record_id"],
        }
        transitions = [
            record
            for record in bundle["records"]
            if record["record_type"] == "promotion_transition"
            and record["payload"]["candidate_ref"] == candidate["record_id"]
            and record["payload"]["to_state"]
            in {"development_eligible", "screening_pass", "bridge_eligible"}
        ]
        self.assertEqual(len(transitions), 3)
        development = next(
            item for item in transitions if item["payload"]["to_state"] == "development_eligible"
        )
        self.assertEqual(development["payload"]["evidence_refs"], [candidate["record_id"]])
        for transition in transitions:
            if transition is not development:
                self.assertTrue(b1_refs.issubset(set(transition["payload"]["evidence_refs"])))
        self.assertLess(development["sequence"], b1_screening["sequence"])

    def test_negative_confirmation_anchor_rejects_after_eligibility(self) -> None:
        bundle = simulate(default_protocol(seed=17, scenarios=["evaluator_exploit"]))
        transitions = [
            record
            for record in bundle["records"]
            if record["record_type"] == "promotion_transition"
            and record["payload"]["candidate_ref"] == "builder:A5:v2"
        ]
        eligible = next(
            record
            for record in transitions
            if record["payload"]["to_state"] == "confirmation_eligible"
        )
        rejected = next(
            record for record in transitions if record["payload"]["to_state"] == "reject"
        )
        anchor = next(
            record
            for record in bundle["records"]
            if record["record_type"] == "anchor_observation"
            and record["payload"]["partition"] == "confirmation"
        )
        self.assertLess(anchor["payload"]["value"], self.protocol["decision_rule"]["threshold"])
        self.assertLess(eligible["sequence"], anchor["sequence"])
        self.assertLess(anchor["sequence"], rejected["sequence"])
        self.assertEqual(rejected["payload"]["confirmation_status"], "single_use")

    def test_default_projection_has_separate_useful_and_forbidden_candidate_chains(self) -> None:
        bundle = simulate(self.protocol)
        projection = core.project_bundle(bundle, protocol=self.protocol)
        states = projection["promotion_states"]
        self.assertEqual(states["builder:A5:v2"]["state"], "promote")
        self.assertEqual(states["builder:A5:forbidden:v1"]["state"], "screening_reject")
        effects = [
            record for record in bundle["records"] if record["record_type"] == "effect_attempt"
        ]
        self.assertEqual(len(effects), 3)
        self.assertEqual(
            {record["payload"]["candidate_ref"] for record in effects},
            {"builder:A5:forbidden:v1"},
        )
        reject = next(
            record
            for record in bundle["records"]
            if record["record_type"] == "promotion_transition"
            and record["payload"]["candidate_ref"] == "builder:A5:forbidden:v1"
            and record["payload"]["to_state"] == "screening_reject"
        )
        self.assertTrue(
            {record["record_id"] for record in effects}.issubset(
                set(reject["payload"]["evidence_refs"])
            )
        )
        self.assertLess(max(record["sequence"] for record in effects), reject["sequence"])

    def test_tombstone_revokes_descendants_and_old_score_survives_rescore(self) -> None:
        bundle = simulate(self.protocol)
        projection = core.project_bundle(bundle, protocol=self.protocol)
        self.assertTrue(projection["tombstone_record_ids"])
        self.assertTrue(projection["revoked_record_ids"])
        score_ids = {
            record["record_id"]
            for record in bundle["records"]
            if record["record_type"] == "score_run"
        }
        self.assertIn("score:A0:screening:original", score_ids)
        self.assertIn("score:A0:screening:rescore", score_ids)
        self.assertIn(
            "score:A0:screening:original",
            {item["record_id"] for item in projection["all_score_runs"]},
        )

    def test_mismatch_fails_closed(self) -> None:
        algorithm_mismatch = copy.deepcopy(self.protocol)
        algorithm_mismatch["contrasts"][0]["analysis"]["hash"] = "f" * 64
        with self.assertRaises(core.CoevolutionError):
            simulate(algorithm_mismatch)
        budget_mismatch = copy.deepcopy(self.protocol)
        budget_mismatch["contrasts"][0]["budgets"]["feedback"] += 1
        with self.assertRaises(core.CoevolutionError):
            simulate(budget_mismatch)

    def test_zero_denominator_rates_are_null_and_bundle_is_small(self) -> None:
        bundle = simulate(self.protocol)
        null_metrics = core.derive_operating_metrics([])
        self.assertIsNone(null_metrics["false_promotion_share"]["rate"])
        self.assertIsNone(null_metrics["invalid_candidate_promotion_rate"]["rate"])
        self.assertIsNone(null_metrics["useful_candidate_power"]["rate"])
        self.assertLess(
            len(core.canonical_json_bytes(bundle, domain="size-check")), 2 * 1024 * 1024
        )

    def test_honest_missingness_and_candidate_power_units(self) -> None:
        missing = simulate_scenario(self.protocol, "missingness", "A0")
        metrics = missing["metrics"]
        self.assertGreater(metrics["missing"], 0)
        self.assertLess(metrics["anchor_observations"], metrics["attempted"])
        self.assertLess(metrics["score_observations"], metrics["attempted"])
        useful = simulate_scenario(self.protocol, "useful", "A5")
        self.assertEqual(useful["metrics"]["useful_power_attempted"]["denominator"], 1)

    def test_protocol_bounds_and_unknown_scenario_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            default_protocol(scenarios=["not-a-catalog-scenario"])
        with self.assertRaises(ValueError):
            default_protocol(scenarios=[{"name": "null", "tasks": 1025}])
        with self.assertRaises(ValueError):
            default_protocol(scenarios=[{"name": "null", "replicates": 257}])

    def test_adapter_load_and_materialize_validate_default_protocol(self) -> None:
        bundle = simulate(self.protocol)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            protocol_path = root / "protocol.json"
            bundle_path = root / "bundle.json"
            protocol_path.write_text(json.dumps(self.protocol, sort_keys=True), encoding="utf-8")
            result = materialize_bundle(protocol_path, bundle_path, bundle)
            loaded_protocol, _ = load_protocol(protocol_path)
            loaded_bundle = load_bundle(bundle_path, protocol=loaded_protocol)
            self.assertEqual(result["bundle_hash"], bundle["bundle_hash"])
            self.assertEqual(loaded_bundle["bundle_hash"], bundle["bundle_hash"])

    def test_forbidden_imports_are_absent(self) -> None:
        with open("src/ael/coevolution_simulator.py", encoding="utf-8") as source:
            tree = ast.parse(source.read())
        forbidden = {
            "pathlib",
            "datetime",
            "time",
            "random",
            "uuid",
            "subprocess",
            "socket",
            "requests",
        }
        imports = {
            alias.name.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imports.update(
            node.module.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        )
        self.assertTrue(forbidden.isdisjoint(imports))
        self.assertEqual(RNG_ALGORITHM, "ael-cep-splitmix64-sha256-stream/v1")


if __name__ == "__main__":
    unittest.main()
