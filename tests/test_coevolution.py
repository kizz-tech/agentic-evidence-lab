from __future__ import annotations

import copy
import hashlib
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError

from ael.coevolution import (
    PROTOCOL_SCHEMA_VERSION,
    CoevolutionError,
    _derive_anchor_decision_agreement,
    _derive_bridge_panel_gate,
    append_bundle,
    append_rescore,
    bundle_hash,
    canonical_hash,
    canonical_json_bytes,
    classify_replay,
    create_bundle,
    create_record,
    derive_arm_primary_endpoints,
    derive_contrast_diagnostics,
    derive_operating_metrics,
    evaluate_bridge,
    project_bundle,
    reduce_promotion,
    validate_bundle,
    validate_protocol,
)

H = "a" * 64


def _rechain_mutated_bundle(bundle: dict[str, object], mutate: object) -> dict[str, object]:
    """Recompute addressed record hashes after a test-only payload mutation."""

    result = copy.deepcopy(bundle)
    records = result["records"]
    assert isinstance(records, list)
    assert callable(mutate)
    mutate(records)
    current_hashes: dict[str, str] = {}
    # Promotion records bind the predecessor transition by hash rather than by
    # a record-id/ref pair.  A payload mutation changes every subsequent
    # addressed hash, so retain the old->new mapping while rebuilding the chain
    # and rewrite those predecessor bindings before hashing each transition.
    replaced_hashes: dict[str, str] = {}

    def refresh(value: object) -> None:
        if isinstance(value, dict):
            for key, child in list(value.items()):
                if (
                    key == "predecessor_transition_hash"
                    and isinstance(child, str)
                    and child in replaced_hashes
                ):
                    value[key] = replaced_hashes[child]
                    continue
                if (
                    isinstance(key, str)
                    and key.endswith("_ref")
                    and isinstance(child, str)
                    and f"{key[:-4]}_hash" in value
                    and child in current_hashes
                ):
                    value[f"{key[:-4]}_hash"] = current_hashes[child]
                refresh(child)
        elif isinstance(value, list):
            for child in value:
                refresh(child)

    previous: str | None = None
    for record in records:
        assert isinstance(record, dict)
        old_record_hash = record["record_hash"]
        refresh(record["payload"])
        for dependency in record["dependency_refs"]:
            if dependency["record_id"] in current_hashes:
                dependency["record_hash"] = current_hashes[dependency["record_id"]]
        record["previous_record_hash"] = previous
        record["record_hash"] = canonical_hash(
            {key: value for key, value in record.items() if key != "record_hash"},
            domain="ael-cep-record",
        )
        replaced_hashes[old_record_hash] = record["record_hash"]
        current_hashes[record["record_id"]] = record["record_hash"]
        previous = record["record_hash"]
    result["bundle_hash"] = bundle_hash(
        {key: value for key, value in result.items() if key != "bundle_hash"}
    )
    return result


class CoevolutionFixtures:
    @staticmethod
    def protocol() -> dict[str, object]:
        algorithms = {
            key: {"ref": key, "hash": H}
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
        partitions = {}
        partition_names = ("development", "screening", "bridge", "confirmation", "historical")
        partition_roots = {
            name: f"{index + 1:x}" * 64 for index, name in enumerate(partition_names)
        }
        for name in partition_names:
            partitions[name] = {
                "partition_id": name,
                "purpose": "declared",
                "feedback": "none"
                if name in {"bridge", "confirmation", "historical"}
                else "aggregate",
                "sealed": name in {"bridge", "confirmation", "historical"},
                "single_use": name == "confirmation",
                "eligible_for_promotion": name == "confirmation",
                "exposure_budget": 1,
                "task_root_hash": partition_roots[name],
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
        principals = {
            name: {"principal_id": name, "custody": f"custody:{name}", "independence": "separate"}
            for name in ("evidence", "confirmation", "anchor", "adjudication", "promotion")
        }
        contrast = {
            "contrast_id": "builder-effect",
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
            "budgets": {"total_system": 1, "feedback": 1, "exposure": 1, "confirmation": 1},
        }
        return {
            "schema_version": PROTOCOL_SCHEMA_VERSION,
            "protocol_id": "protocol:test",
            "epoch": {
                "epoch_id": "epoch:test",
                "state": "frozen",
                "constitution_ref": "constitution:test",
                "constitution_hash": H,
            },
            "principals": principals,
            "intake": intake,
            "partitions": partitions,
            "arms": arms,
            "contrasts": [contrast],
            "algorithms": algorithms,
            "budgets": {"total_system": 1, "feedback": 1, "exposure": 1, "confirmation": 1},
            "feedback_exposure": {
                name: "declared"
                for name in ("development", "screening", "bridge", "confirmation", "total")
            },
            "missingness": {
                "policy": "declared",
                "bounds": "declared",
                "critical_failure_rule": "declared",
            },
            "stopping": {
                "algorithm_ref": "stopping",
                "algorithm_hash": H,
                "rule": "declared",
                "max_looks": 1,
                "missing_data": "declared",
            },
            "bridge": {
                "global_shift_tolerance": 0.1,
                "interaction_tolerance": 0.1,
                "decision_agreement_min": 0.8,
                "construct_required": True,
                "reliability_required": True,
                "anchor_required": True,
                "strata": [
                    {
                        "stratum": name,
                        "weight": 0.2,
                        "task_root_hash": hashlib.sha256(
                            f"test-stratum:{name}".encode()
                        ).hexdigest(),
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
                "retention_policy": "retain",
                "required_surfaces": ["output", "trace"],
                "deterministic_code_policy": "separate",
            },
            "independence": {
                "protected_dimensions": ["organization", "model_family"],
                "ceiling": "declared",
            },
            "promotion": {
                "initial_state": "registered",
                "transition_table": {
                    "registered": ["development_eligible"],
                    "development_eligible": ["revoke", "screening_pass", "screening_reject"],
                    "screening_pass": ["bridge_eligible", "new_measurement_epoch", "revoke"],
                    "screening_reject": [],
                    "bridge_eligible": ["confirmation_eligible", "new_measurement_epoch", "revoke"],
                    "new_measurement_epoch": [],
                    "confirmation_eligible": ["promote", "narrow", "abstain", "reject", "revoke"],
                    "promote": ["monitor", "expire", "revoke"],
                    "narrow": ["monitor", "expire", "revoke"],
                    "abstain": ["monitor", "expire", "revoke"],
                    "reject": ["monitor", "expire", "revoke"],
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
                "config_version": "sim:0.2",
                "seed": 7,
                "scenarios": [
                    {"name": "null", "tasks": 1, "replicates": 1},
                    {"name": "improvement", "tasks": 1, "replicates": 1},
                    {"name": "exploitation", "tasks": 1, "replicates": 1},
                ],
            },
        }

    @staticmethod
    def builder() -> dict[str, object]:
        return {
            "release_id": "B0",
            "release_kind": "builder",
            "revision": "b0",
            "artifact_hash": H,
            "custody": "builder-custody",
            "allowed_evidence_surface": ["output", "trace"],
        }

    @staticmethod
    def evaluator(evaluator_id: str = "E0") -> dict[str, object]:
        return {
            "release_id": evaluator_id,
            "release_kind": "evaluator",
            "revision": evaluator_id.lower(),
            "artifact_hash": H,
            "implementation": "impl",
            "prompt_or_rubric": "rubric",
            "model": "model",
            "parser_or_aggregation": "aggregate",
            "tools_or_environment": "none",
            "calibration_lineage": "calibration",
            "known_error_envelope": "bounded",
            "custody": "evaluator-custody",
            "allowed_evidence_surface": ["output", "trace"],
        }

    @staticmethod
    def method() -> dict[str, object]:
        return {
            "method_id": "M0",
            "revision": "m0",
            "artifact_hash": H,
            "construct": "construct",
            "oracle": "oracle",
            "parser": "parser",
            "aggregation": "aggregation",
            "validity": "validity",
            "reliability": "reliability",
            "custody": "method-custody",
        }

    @classmethod
    def records(cls) -> list[dict[str, object]]:
        b = create_record(
            record_id="B0",
            record_type="builder_release",
            epoch_id="epoch:test",
            sequence=0,
            previous_record_hash=None,
            payload=cls.builder(),
        )
        e = create_record(
            record_id="E0",
            record_type="evaluator_release",
            epoch_id="epoch:test",
            sequence=1,
            previous_record_hash=b["record_hash"],
            payload=cls.evaluator(),
        )
        m = create_record(
            record_id="M0",
            record_type="measurement_method",
            epoch_id="epoch:test",
            sequence=2,
            previous_record_hash=e["record_hash"],
            payload=cls.method(),
        )
        evidence_payload = {
            "evidence_id": "V0",
            "subject_ref": "S",
            "builder_release_ref": "B0",
            "builder_release_hash": b["record_hash"],
            "task_partition": "screening",
            "task_ref": "task:test",
            "task_hash": CoevolutionFixtures.protocol()["partitions"]["screening"][
                "task_root_hash"
            ],
            "environment_ref": "environment:test",
            "environment_hash": H,
            "runner_ref": "runner:test",
            "runner_hash": H,
            "exposure_state_ref": "exposure:test",
            "exposure_state_hash": H,
            "partition": "screening",
            "surface_refs": ["output", "trace"],
            "artifact_hash": H,
            "status": "retained",
        }
        v = create_record(
            record_id="V0",
            record_type="subject_execution_evidence",
            epoch_id="epoch:test",
            sequence=3,
            previous_record_hash=m["record_hash"],
            payload=evidence_payload,
            dependency_refs={"B0": b["record_hash"]},
        )
        binding_payload = {
            "binding_id": "X0",
            "builder_release_ref": "B0",
            "builder_release_hash": b["record_hash"],
            "evaluator_release_ref": "E0",
            "evaluator_release_hash": e["record_hash"],
            "method_ref": "M0",
            "method_hash": m["record_hash"],
            "evidence_ref": "V0",
            "evidence_hash": v["record_hash"],
            "task_partition": "screening",
            "task_ref": "task:test",
            "task_hash": "2" * 64,
            "exposure_policy": "aggregate",
            "analysis_ref": "analysis",
            "analysis_hash": H,
            "environment_ref": "environment:test",
            "environment_hash": H,
            "runner_ref": "runner:test",
            "runner_hash": H,
            "promotion_policy_ref": "promotion",
            "promotion_policy_hash": H,
            "exposure_state_ref": "exposure:test",
            "exposure_state_hash": H,
            "allowed_evidence_surface": ["output", "trace"],
        }
        x = create_record(
            record_id="X0",
            record_type="evaluation_binding",
            epoch_id="epoch:test",
            sequence=4,
            previous_record_hash=v["record_hash"],
            payload=binding_payload,
            dependency_refs={
                "B0": b["record_hash"],
                "E0": e["record_hash"],
                "M0": m["record_hash"],
                "V0": v["record_hash"],
            },
        )
        score_payload = {
            "score_run_id": "Q0",
            "binding_ref": "X0",
            "binding_hash": x["record_hash"],
            "evidence_ref": "V0",
            "evidence_hash": v["record_hash"],
            "evaluator_release_ref": "E0",
            "evaluator_release_hash": e["record_hash"],
            "builder_release_ref": "B0",
            "builder_release_hash": b["record_hash"],
            "method_ref": "M0",
            "method_hash": m["record_hash"],
            "score": 0.5,
            "score_status": "observed",
            "scoring_actor": "adjudication",
            "partition": "screening",
            "surface_refs": ["output", "trace"],
            "score_key": "S",
        }
        q = create_record(
            record_id="Q0",
            record_type="score_run",
            epoch_id="epoch:test",
            sequence=5,
            previous_record_hash=x["record_hash"],
            payload=score_payload,
            dependency_refs={
                "X0": x["record_hash"],
                "V0": v["record_hash"],
                "E0": e["record_hash"],
            },
        )
        return [b, e, m, v, x, q]

    @classmethod
    def bundle(cls) -> dict[str, object]:
        return create_bundle(cls.protocol(), bundle_id="bundle:0", records=cls.records())


class CoevolutionTests(unittest.TestCase):
    def test_schema_members_are_unique_and_independence_authority_is_required(self) -> None:
        for name in ("protocol.schema.json", "bundle.schema.json"):
            seen_duplicates: list[str] = []

            def no_duplicates(
                pairs: list[tuple[str, object]], duplicate_sink: list[str] = seen_duplicates
            ) -> dict[str, object]:
                result: dict[str, object] = {}
                for key, value in pairs:
                    if key in result:
                        duplicate_sink.append(key)
                    result[key] = value
                return result

            json.loads(
                (Path(__file__).parents[1] / "src/ael/coevolution_schemas" / name).read_text(),
                object_pairs_hook=no_duplicates,
            )
            self.assertEqual(seen_duplicates, [], name)
        with self.assertRaisesRegex(CoevolutionError, "missing_field"):
            create_record(
                record_id="I0",
                record_type="independence_assessment",
                epoch_id="epoch:test",
                sequence=0,
                previous_record_hash=None,
                payload={
                    "assessment_id": "I0",
                    "claim_ref": "candidate",
                    "dimensions": {"organization": "separate"},
                    "overall": "pass",
                    "evidence_refs": [],
                },
            )

    def test_effect_attempt_is_typed_blocked_fact(self) -> None:
        bundle = CoevolutionFixtures.bundle()
        effect = create_record(
            record_id="FX0",
            record_type="effect_attempt",
            epoch_id="epoch:test",
            sequence=6,
            previous_record_hash=bundle["records"][-1]["record_hash"],
            payload={
                "effect_attempt_id": "FX0",
                "candidate_ref": "B0",
                "candidate_hash": bundle["records"][0]["record_hash"],
                "evidence_ref": "V0",
                "evidence_hash": bundle["records"][3]["record_hash"],
                "binding_ref": "X0",
                "binding_hash": bundle["records"][4]["record_hash"],
                "partition": "screening",
                "observation_authority": "evidence",
                "effect_request_hash": H,
                "idempotency_key_hash": H,
                "disposition": "blocked",
                "postcondition_status": "not_dispatched",
                "reason_code": "stage0_forbidden",
            },
            dependency_refs={
                "B0": bundle["records"][0]["record_hash"],
                "V0": bundle["records"][3]["record_hash"],
                "X0": bundle["records"][4]["record_hash"],
            },
        )
        with self.assertRaisesRegex(CoevolutionError, "effect_orphan"):
            append_bundle(bundle, [effect], bundle_id="bundle:effect")
        invalid = copy.deepcopy(effect)
        invalid["payload"]["disposition"] = "accepted"
        invalid["record_hash"] = canonical_hash(
            {key: value for key, value in invalid.items() if key != "record_hash"},
            domain="ael-cep-record",
        )
        with self.assertRaisesRegex(CoevolutionError, "effect_postcondition"):
            create_record(
                record_id="FX1",
                record_type="effect_attempt",
                epoch_id="epoch:test",
                sequence=6,
                previous_record_hash=bundle["records"][-1]["record_hash"],
                payload=invalid["payload"],
                dependency_refs=invalid["dependency_refs"],
            )
        accepted_payload = dict(effect["payload"])
        accepted_payload.update(
            {
                "effect_attempt_id": "FX2",
                "disposition": "accepted",
                "postcondition_status": "confirmed_applied",
                "receipt_ref": "Q0",
                "receipt_hash": bundle["records"][5]["record_hash"],
            }
        )
        with self.assertRaisesRegex(CoevolutionError, "effect_forbidden"):
            create_record(
                record_id="FX2",
                record_type="effect_attempt",
                epoch_id="epoch:test",
                sequence=6,
                previous_record_hash=bundle["records"][-1]["record_hash"],
                payload=accepted_payload,
                dependency_refs={
                    "B0": bundle["records"][0]["record_hash"],
                    "V0": bundle["records"][3]["record_hash"],
                    "X0": bundle["records"][4]["record_hash"],
                    "Q0": bundle["records"][5]["record_hash"],
                },
            )
        for disposition, postcondition in (
            ("quarantined", "ambiguous"),
            ("blocked", "confirmed_not_applied"),
        ):
            future = dict(effect["payload"])
            future.update(
                {
                    "effect_attempt_id": f"FX-{disposition}",
                    "disposition": disposition,
                    "postcondition_status": postcondition,
                }
            )
            with self.assertRaisesRegex(CoevolutionError, "effect_forbidden"):
                create_record(
                    record_id=f"FX-{disposition}",
                    record_type="effect_attempt",
                    epoch_id="epoch:test",
                    sequence=6,
                    previous_record_hash=bundle["records"][-1]["record_hash"],
                    payload=future,
                    dependency_refs=effect["dependency_refs"],
                )
        receipt_payload = dict(effect["payload"])
        receipt_payload.update(
            {
                "effect_attempt_id": "FX-receipt",
                "receipt_ref": "Q0",
                "receipt_hash": bundle["records"][5]["record_hash"],
            }
        )
        with self.assertRaisesRegex(CoevolutionError, "effect_forbidden"):
            create_record(
                record_id="FX-receipt",
                record_type="effect_attempt",
                epoch_id="epoch:test",
                sequence=6,
                previous_record_hash=bundle["records"][-1]["record_hash"],
                payload=receipt_payload,
                dependency_refs=[
                    *effect["dependency_refs"],
                    {"record_id": "Q0", "record_hash": bundle["records"][5]["record_hash"]},
                ],
            )

    def test_schemas_are_draft_2020_12_and_fixture_validates(self) -> None:
        for name in ("protocol.schema.json", "bundle.schema.json"):
            schema = json.loads(
                (Path(__file__).parents[1] / "src/ael/coevolution_schemas" / name).read_text()
            )
            Draft202012Validator.check_schema(schema)
        protocol = validate_protocol(CoevolutionFixtures.protocol())
        schema = json.loads(
            (
                Path(__file__).parents[1] / "src/ael/coevolution_schemas/protocol.schema.json"
            ).read_text()
        )
        Draft202012Validator(schema).validate(protocol)
        bundle = CoevolutionFixtures.bundle()
        schema = json.loads(
            (
                Path(__file__).parents[1] / "src/ael/coevolution_schemas/bundle.schema.json"
            ).read_text()
        )
        Draft202012Validator(schema).validate(bundle)
        builder_payload = CoevolutionFixtures.builder() | {"model": "must-not-be-builder-data"}
        with self.assertRaises(CoevolutionError):
            create_record(
                record_id="B1",
                record_type="builder_release",
                epoch_id="epoch:test",
                sequence=0,
                previous_record_hash=None,
                payload=builder_payload,
            )
        bad_record = copy.deepcopy(bundle["records"][0])
        bad_record["payload"]["model"] = "irrelevant"
        bad_record["record_hash"] = canonical_hash(
            {key: value for key, value in bad_record.items() if key != "record_hash"},
            domain="ael-cep-record",
        )
        invalid_bundle = copy.deepcopy(bundle)
        invalid_bundle["records"][0] = bad_record
        invalid_bundle["bundle_hash"] = bundle_hash(
            {key: value for key, value in invalid_bundle.items() if key != "bundle_hash"}
        )
        with self.assertRaises(ValidationError):
            Draft202012Validator(schema).validate(invalid_bundle)
        panel_names = ("good", "bad", "exploit", "semantic_mutant", "near_threshold")
        panel_strata = []
        for name in panel_names:
            panel = {"stratum": name, "weight": 0.2}
            for prefix in ("old_evidence", "new_evidence"):
                panel[f"{prefix}_ref"] = f"{prefix}:{name}"
                panel[f"{prefix}_hash"] = H
            for cell in ("b0e0", "b0e1", "b1e0", "b1e1"):
                panel[f"{cell}_score_ref"] = f"{cell}:{name}"
                panel[f"{cell}_score_hash"] = H
            for anchor in ("b0_anchor", "b1_anchor"):
                panel[f"{anchor}_ref"] = f"{anchor}:{name}"
                panel[f"{anchor}_hash"] = H
            panel_strata.append(panel)
        panel_payload = {
            "bridge_id": "bridge:panel",
            "old_builder_ref": "B0",
            "old_builder_hash": H,
            "new_builder_ref": "B1",
            "new_builder_hash": H,
            "old_evaluator_ref": "E0",
            "old_evaluator_hash": H,
            "new_evaluator_ref": "E1",
            "new_evaluator_hash": H,
            "old_evidence_ref": "evidence:old",
            "old_evidence_hash": H,
            "new_evidence_ref": "evidence:new",
            "new_evidence_hash": H,
            "old_builder_old_evaluator_score_ref": "b0e0:good",
            "old_builder_old_evaluator_score_hash": H,
            "old_builder_new_evaluator_score_ref": "b0e1:good",
            "old_builder_new_evaluator_score_hash": H,
            "new_builder_old_evaluator_score_ref": "b1e0:good",
            "new_builder_old_evaluator_score_hash": H,
            "new_builder_new_evaluator_score_ref": "b1e1:good",
            "new_builder_new_evaluator_score_hash": H,
            "anchor_release_ref": "A0",
            "anchor_release_hash": H,
            "decision_threshold": 0.5,
            "global_shift_interval": [0.0, 0.0],
            "interaction_interval": [0.0, 0.0],
            "decision_agreement": 1.0,
            "anchor_agreement": 1.0,
            "construct_evidence": "synthetic_pass",
            "reliability_evidence": "synthetic_pass",
            "strata": panel_strata,
            "outcome": "bridge_comparable",
        }
        panel_record = create_record(
            record_id="bridge:panel",
            record_type="bridge_observation",
            epoch_id="epoch:test",
            sequence=6,
            previous_record_hash=bundle["records"][-1]["record_hash"],
            payload=panel_payload,
        )
        schema_bundle = copy.deepcopy(bundle)
        schema_bundle["records"].append(panel_record)
        schema_bundle["bundle_hash"] = bundle_hash(
            {key: value for key, value in schema_bundle.items() if key != "bundle_hash"}
        )
        Draft202012Validator(schema).validate(schema_bundle)

    def test_canonical_hash_is_deterministic_and_rejects_nonfinite(self) -> None:
        self.assertEqual(
            canonical_json_bytes({"b": 2, "a": 1}), canonical_json_bytes({"a": 1, "b": 2})
        )
        self.assertEqual(canonical_hash({"x": 1}), canonical_hash({"x": 1}))
        with self.assertRaisesRegex(CoevolutionError, "nonfinite"):
            canonical_hash({"x": float("nan")})
        with self.assertRaisesRegex(CoevolutionError, "unsupported_type"):
            canonical_hash({"x": object()})

    def test_protocol_intake_arms_contrast_and_unknown_field_fail_closed(self) -> None:
        protocol = CoevolutionFixtures.protocol()
        self.assertEqual(validate_protocol(protocol)["arms"]["A5"]["challenger"], "present")
        incomplete = copy.deepcopy(protocol)
        del incomplete["intake"]["sampling_cutoff"]
        with self.assertRaisesRegex(CoevolutionError, "incomplete_intake"):
            validate_protocol(incomplete)
        wrong_arm = copy.deepcopy(protocol)
        wrong_arm["arms"]["A4"]["anchor"] = "absent"
        with self.assertRaisesRegex(CoevolutionError, "arm_definition"):
            validate_protocol(wrong_arm)
        wrong_budget = copy.deepcopy(protocol)
        wrong_budget["contrasts"][0]["budgets"]["feedback"] = 2
        with self.assertRaisesRegex(CoevolutionError, "contrast_budget_mismatch"):
            validate_protocol(wrong_budget)
        package = copy.deepcopy(protocol)
        package["contrasts"][0].update(
            {
                "arm_a": "A3",
                "arm_b": "A4",
                "estimand_kind": "policy_package",
                "treatment": {
                    "dimension": "policy_package",
                    "arm_a_level": "A3",
                    "arm_b_level": "A4",
                },
            }
        )
        self.assertEqual(
            validate_protocol(package)["contrasts"][0]["estimand_kind"], "policy_package"
        )
        component_claim = copy.deepcopy(package)
        component_claim["contrasts"][0]["estimand_kind"] = "component"
        with self.assertRaisesRegex(CoevolutionError, "contrast_treatment"):
            validate_protocol(component_claim)
        unknown = copy.deepcopy(protocol)
        unknown["intake"]["new_field"] = "x"
        with self.assertRaisesRegex(CoevolutionError, "unknown_field"):
            validate_protocol(unknown)
        duplicate_custody = copy.deepcopy(protocol)
        duplicate_custody["principals"]["anchor"]["custody"] = duplicate_custody["principals"][
            "evidence"
        ]["custody"]
        with self.assertRaisesRegex(CoevolutionError, "principal_custody"):
            validate_protocol(duplicate_custody)
        duplicate_stratum_root = copy.deepcopy(protocol)
        duplicate_stratum_root["bridge"]["strata"][1]["task_root_hash"] = duplicate_stratum_root[
            "bridge"
        ]["strata"][0]["task_root_hash"]
        with self.assertRaisesRegex(CoevolutionError, "strata_policy"):
            validate_protocol(duplicate_stratum_root)

    def test_valid_chain_and_tamper_gap_fork_dangling_duplicate(self) -> None:
        bundle = CoevolutionFixtures.bundle()
        self.assertEqual(validate_bundle(bundle)["bundle_hash"], bundle["bundle_hash"])
        tampered = copy.deepcopy(bundle)
        tampered["records"][2]["payload"]["revision"] = "tamper"
        with self.assertRaisesRegex(CoevolutionError, "hash_mismatch"):
            validate_bundle(tampered)
        gap = copy.deepcopy(bundle)
        gap["records"][2]["sequence"] = 9
        with self.assertRaisesRegex(CoevolutionError, "hash_mismatch|sequence_gap"):
            validate_bundle(gap)
        fork = copy.deepcopy(bundle)
        fork["records"][2]["previous_record_hash"] = H
        fork["records"][2]["record_hash"] = canonical_hash(
            {key: value for key, value in fork["records"][2].items() if key != "record_hash"},
            domain="ael-cep-record",
        )
        fork["bundle_hash"] = bundle_hash(
            {key: value for key, value in fork.items() if key != "bundle_hash"}
        )
        with self.assertRaisesRegex(CoevolutionError, "chain_fork"):
            validate_bundle(fork)
        dangling = copy.deepcopy(bundle)
        dangling["records"][5]["dependency_refs"].append({"record_id": "future", "record_hash": H})
        dangling["records"][5]["record_hash"] = canonical_hash(
            {key: value for key, value in dangling["records"][5].items() if key != "record_hash"},
            domain="ael-cep-record",
        )
        dangling["bundle_hash"] = bundle_hash(
            {key: value for key, value in dangling.items() if key != "bundle_hash"}
        )
        with self.assertRaisesRegex(CoevolutionError, "dangling_dependency"):
            validate_bundle(dangling)
        duplicate = copy.deepcopy(bundle)
        duplicate["records"][1]["record_id"] = "B0"
        with self.assertRaisesRegex(CoevolutionError, "identity_mismatch|duplicate_id"):
            validate_bundle(duplicate)

    def test_successor_preserves_prefix_and_old_score(self) -> None:
        bundle = CoevolutionFixtures.bundle()
        successor = append_bundle(bundle, [], bundle_id="bundle:1")
        self.assertEqual(successor["records"], bundle["records"])
        with self.assertRaisesRegex(CoevolutionError, "predecessor_required"):
            validate_bundle(successor)
        self.assertEqual(
            project_bundle(successor, predecessor=bundle)["record_count"], len(successor["records"])
        )
        gen2 = append_bundle(successor, [], bundle_id="bundle:2", predecessor_chain=(bundle,))
        self.assertEqual(
            validate_bundle(gen2, predecessor_chain=(bundle, successor))["bundle_hash"],
            gen2["bundle_hash"],
        )
        with self.assertRaisesRegex(CoevolutionError, "predecessor_chain_required"):
            validate_bundle(gen2, predecessor=successor)
        altered = copy.deepcopy(successor)
        altered["records"][0]["payload"]["revision"] = "changed"
        altered["records"][0]["record_hash"] = canonical_hash(
            {key: value for key, value in altered["records"][0].items() if key != "record_hash"},
            domain="ael-cep-record",
        )
        altered["bundle_hash"] = bundle_hash(
            {key: value for key, value in altered.items() if key != "bundle_hash"}
        )
        with self.assertRaisesRegex(CoevolutionError, "predecessor_prefix|chain_fork"):
            validate_bundle(altered, predecessor=bundle)
        evaluator = CoevolutionFixtures.evaluator("E1")
        score = {
            "score_run_id": "Q1",
            "evidence_ref": "V0",
            "evidence_hash": bundle["records"][3]["record_hash"],
            "builder_release_ref": "B0",
            "builder_release_hash": bundle["records"][0]["record_hash"],
            "method_ref": "M0",
            "method_hash": bundle["records"][2]["record_hash"],
            "partition": "screening",
            "score": 0.6,
            "score_key": "S",
            "surface_refs": ["output", "trace"],
        }
        rescored = append_rescore(
            bundle,
            evaluator,
            score,
            actor="adjudication",
            retained_surfaces=["output", "trace"],
        )
        self.assertEqual(rescored["records"][5]["record_id"], "Q0")
        self.assertEqual(rescored["records"][-1]["record_id"], "Q1")
        self.assertEqual(rescored["records"][5], bundle["records"][5])

    def test_replay_classes_and_rescore_fail_closed(self) -> None:
        args = {"retained_surfaces": ["output"], "required_surfaces": ["output"]}
        self.assertEqual(classify_replay(**args), "rescorable")
        self.assertEqual(
            classify_replay(**args, deterministic_code=True), "deterministic_replayable"
        )
        self.assertEqual(classify_replay(**args, unavailable=True), "historical_only")
        self.assertEqual(classify_replay(**args, changes=["model"]), "rerun_required")
        with self.assertRaisesRegex(CoevolutionError, "self_certification|custody_unknown"):
            append_rescore(
                CoevolutionFixtures.bundle(),
                CoevolutionFixtures.evaluator("E1"),
                {"score_run_id": "Q1"},
                actor="evaluator-custody",
            )
        with self.assertRaisesRegex(CoevolutionError, "missing_surface"):
            append_rescore(
                CoevolutionFixtures.bundle(),
                CoevolutionFixtures.evaluator("E1"),
                {"score_run_id": "Q1"},
                actor="other",
            )

    def test_replay_distinguishes_evaluator_model_from_subject_model(self) -> None:
        args = {"retained_surfaces": ["output"], "required_surfaces": ["output"]}
        old = {
            "implementation": "eval-v1",
            "prompt_or_rubric": "rubric-v1",
            "model": "judge-v1",
            "parser_or_aggregation": "parser-v1",
        }
        evaluator_model = dict(old, model="judge-v2")
        self.assertEqual(
            classify_replay(**args, old_evaluator=old, new_evaluator=evaluator_model),
            "rescorable",
        )
        self.assertEqual(classify_replay(**args, changes=["model"]), "rerun_required")
        self.assertEqual(classify_replay(**args, changes=["subject_model"]), "rerun_required")

    def test_score_run_missingness_and_decision_range_are_closed(self) -> None:
        score = copy.deepcopy(CoevolutionFixtures.records()[5]["payload"])
        score_dependencies = {
            item["record_id"]: item["record_hash"]
            for item in CoevolutionFixtures.records()[5]["dependency_refs"]
        }
        with self.assertRaisesRegex(CoevolutionError, "score_range"):
            create_record(
                record_id="Q-range-high",
                record_type="score_run",
                epoch_id="epoch:test",
                sequence=5,
                previous_record_hash=CoevolutionFixtures.records()[4]["record_hash"],
                payload={**score, "score": 100.0},
                dependency_refs=score_dependencies,
            )
        with self.assertRaisesRegex(CoevolutionError, "score_range"):
            create_record(
                record_id="Q-range-low",
                record_type="score_run",
                epoch_id="epoch:test",
                sequence=5,
                previous_record_hash=CoevolutionFixtures.records()[4]["record_hash"],
                payload={**score, "score": -1.0},
                dependency_refs=score_dependencies,
            )
        with self.assertRaisesRegex(CoevolutionError, "score_range"):
            create_record(
                record_id="Q-observed-null",
                record_type="score_run",
                epoch_id="epoch:test",
                sequence=5,
                previous_record_hash=CoevolutionFixtures.records()[4]["record_hash"],
                payload={**score, "score": None},
                dependency_refs=score_dependencies,
            )
        missing = create_record(
            record_id="Q-missing",
            record_type="score_run",
            epoch_id="epoch:test",
            sequence=5,
            previous_record_hash=CoevolutionFixtures.records()[4]["record_hash"],
            payload={**score, "score": None, "score_status": "missing"},
            dependency_refs=score_dependencies,
        )
        self.assertIsNone(missing["payload"]["score"])
        schema = json.loads(
            (
                Path(__file__).parents[1] / "src/ael/coevolution_schemas/bundle.schema.json"
            ).read_text()
        )
        schema_validator = Draft202012Validator(schema)
        self.assertEqual([], list(schema_validator.descend(missing, schema["$defs"]["record"])))
        bad_schema_record = copy.deepcopy(missing)
        bad_schema_record["payload"]["score_status"] = "observed"
        bad_schema_record["payload"]["score"] = None
        self.assertNotEqual(
            [], list(schema_validator.descend(bad_schema_record, schema["$defs"]["record"]))
        )

    def test_bridge_failure_has_a_prospective_new_epoch_transition(self) -> None:
        transition = {
            "transition_id": "P:bridge-failed",
            "candidate_ref": "B1",
            "candidate_hash": H,
            "from_state": "bridge_eligible",
            "to_state": "new_measurement_epoch",
            "predecessor_transition_hash": H,
            "actor": "adjudication",
            "approval_actor": "promotion",
            "independence": {"organization": "overlap", "model_family": "unknown"},
            "confirmation_status": "not_opened",
            "bridge_status": "new_epoch_not_comparable",
            "critical_failure": True,
            "effect_attempt": False,
            "revoked_ancestry": False,
            "reason": "bridge-failed",
            "evidence_refs": [],
        }
        reduced = reduce_promotion(
            {"state": "bridge_eligible", "transition_hash": H},
            transition,
            evidence={
                "bridge_status": "new_epoch_not_comparable",
                "critical_failure": True,
                "independence": transition["independence"],
            },
            protocol=CoevolutionFixtures.protocol(),
        )
        self.assertEqual(reduced["state"], "new_measurement_epoch")
        with self.assertRaisesRegex(CoevolutionError, "bridge_outcome"):
            reduce_promotion(
                {"state": "bridge_eligible", "transition_hash": H},
                {**transition, "bridge_status": "bridge_comparable"},
                evidence={"bridge_status": "bridge_comparable"},
                protocol=CoevolutionFixtures.protocol(),
            )

    def test_bridge_outcomes(self) -> None:
        observation = {
            "global_shift_interval": [-0.01, 0.01],
            "interaction_interval": [-0.02, 0.02],
            "decision_agreement": 0.95,
            "construct_evidence": "synthetic_pass",
            "reliability_evidence": "synthetic_pass",
            "strata": [
                {"stratum": name, "weight": 0.2, "pass": True}
                for name in ("good", "bad", "exploit", "semantic_mutant", "near_threshold")
            ],
            "anchor_agreement": 1.0,
        }
        self.assertEqual(
            evaluate_bridge(
                observation, tolerances={"global_shift": 0.1, "interaction": 0.1, "agreement": 0.8}
            )["outcome"],
            "bridge_comparable",
        )
        uncertain = dict(observation, decision_agreement=0.5)
        self.assertEqual(
            evaluate_bridge(
                uncertain, tolerances={"global_shift": 0.1, "interaction": 0.1, "agreement": 0.8}
            )["outcome"],
            "linked_with_uncertainty",
        )
        failed = dict(observation, interaction_interval=[-0.5, 0.5])
        self.assertEqual(
            evaluate_bridge(
                failed, tolerances={"global_shift": 0.1, "interaction": 0.1, "agreement": 0.8}
            )["outcome"],
            "new_epoch_not_comparable",
        )

    def test_bridge_anchor_values_and_per_stratum_gate_are_authoritative(self) -> None:
        scores = {cell: {"score": 0.9} for cell in ("b0e0", "b0e1", "b1e0", "b1e1")}
        anchors = {
            "b0_anchor": {"value": 0.1, "status": "observed", "critical_failure": False},
            "b1_anchor": {"value": 0.1, "status": "observed", "critical_failure": False},
        }
        derived = _derive_anchor_decision_agreement(scores, anchors, 0.5, "bridge.bad")
        self.assertEqual(derived, 0.0)
        # Matching status labels cannot override contradictory observed values.
        anchors["b0_anchor"]["status"] = "pass"
        anchors["b1_anchor"]["status"] = "pass"
        self.assertEqual(_derive_anchor_decision_agreement(scores, anchors, 0.5, "bridge.bad"), 0.0)
        self.assertNotEqual(1.0, derived)

        panel = {"strata": []}
        by_id: dict[str, dict[str, object]] = {}
        for name, values in {
            "good": (0.7, 0.9, 0.7, 0.9),
            "bad": (0.9, 0.7, 0.9, 0.7),
            "exploit": (0.8, 0.8, 0.8, 0.8),
            "semantic_mutant": (0.8, 0.8, 0.8, 0.8),
            "near_threshold": (0.8, 0.8, 0.8, 0.8),
        }.items():
            stratum: dict[str, object] = {"stratum": name, "weight": 0.2}
            for cell, value in zip(("b0e0", "b0e1", "b1e0", "b1e1"), values, strict=True):
                ref = f"score:{name}:{cell}"
                stratum[f"{cell}_score_ref"] = ref
                by_id[ref] = {"record_type": "score_run", "payload": {"score": value}}
            for anchor in ("b0_anchor", "b1_anchor"):
                ref = f"anchor:{name}:{anchor}"
                stratum[f"{anchor}_ref"] = ref
                by_id[ref] = {
                    "record_type": "anchor_observation",
                    "payload": {"value": 0.8},
                }
            panel["strata"].append(stratum)
        panel_metrics = _derive_bridge_panel_gate(
            panel,
            by_id,
            threshold=0.64,
            global_tolerance=0.05,
            interaction_tolerance=0.05,
            agreement_min=0.9,
            path="bridge.panel",
        )
        # Equal/opposite shifts cancel in the weighted summary, but the
        # per-stratum hard gate still rejects the bridge.
        self.assertAlmostEqual(panel_metrics["global"], 0.0)
        self.assertFalse(panel_metrics["strata_gate"])
        observation = {
            "global_shift_interval": [0.0, 0.0],
            "interaction_interval": [0.0, 0.0],
            "decision_agreement": 1.0,
            "anchor_agreement": 1.0,
            "construct_evidence": "synthetic_pass",
            "reliability_evidence": "synthetic_pass",
            "strata": [
                {"stratum": name, "weight": 0.2, "b0e0_score_ref": "present"}
                for name in ("good", "bad", "exploit", "semantic_mutant", "near_threshold")
            ],
        }
        self.assertEqual(
            evaluate_bridge(
                observation,
                tolerances={"global_shift": 0.05, "interaction": 0.05, "agreement": 0.9},
                per_stratum_gate=panel_metrics["strata_gate"],
            )["outcome"],
            "new_epoch_not_comparable",
        )

    def test_confirmation_anchor_taint_is_order_independent(self) -> None:
        transition = {
            "from_state": "confirmation_eligible",
            "to_state": "promote",
            "predecessor_transition_hash": "0" * 64,
            "actor": "adjudication",
            "approval_actor": "promotion",
            "evidence_refs": [],
        }
        evidence_variants = (
            {
                "confirmation_status": "single_use",
                "tainted_confirmation": True,
                "anchor_status": "observed",
            },
            {
                "anchor_status": "observed",
                "tainted_confirmation": True,
                "confirmation_status": "single_use",
            },
        )
        for evidence in evidence_variants:
            evidence["independence"] = {"organization": "separate", "model_family": "separate"}
            evidence["bridge_status"] = "bridge_comparable"
            with self.assertRaisesRegex(CoevolutionError, "confirmation_reuse"):
                reduce_promotion(
                    {"state": "confirmation_eligible", "transition_hash": "0" * 64},
                    transition,
                    evidence=evidence,
                    protocol=CoevolutionFixtures.protocol(),
                )

    def test_unconsumed_confirmation_anchor_fails_in_both_evidence_orders(self) -> None:
        """A valid-looking anchor cannot overwrite an unconsumed pack."""

        from ael.coevolution_simulator import default_protocol, simulate

        protocol = default_protocol(seed=17, scenarios=["useful"])
        bundle = simulate(protocol)
        for reverse in (False, True):

            def mutate(records: list[dict[str, object]], reverse: bool = reverse) -> None:
                for record in records:
                    if (
                        record["record_type"] == "confirmation_consumption"
                        and record["record_id"] == "consumption:A5:confirmation:v1"
                    ):
                        record["payload"]["consumed"] = False
                    if reverse and record["record_id"] == "promotion:A5:4:promote":
                        record["payload"]["evidence_refs"] = list(
                            reversed(record["payload"]["evidence_refs"])
                        )

            mutated = _rechain_mutated_bundle(bundle, mutate)
            with self.assertRaisesRegex(CoevolutionError, "confirmation_policy"):
                validate_bundle(mutated, protocol=protocol)

    def test_confirmation_task_root_is_globally_single_use_across_candidates(self) -> None:
        from ael.coevolution_simulator import default_protocol, simulate

        protocol = default_protocol(seed=17, scenarios=["useful"])
        bundle = simulate(protocol)
        source_evidence = next(
            record
            for record in bundle["records"]
            if record["record_type"] == "subject_execution_evidence"
            and record["payload"].get("partition") == "confirmation"
        )
        alternate_candidate = next(
            record
            for record in bundle["records"]
            if record["record_type"] == "builder_release"
            and record["record_id"] != source_evidence["payload"]["builder_release_ref"]
        )
        sequence = bundle["records"][-1]["sequence"] + 1
        reused_evidence_id = "evidence:confirmation:alternate-root"
        reused_evidence = create_record(
            record_id=reused_evidence_id,
            record_type="subject_execution_evidence",
            epoch_id=bundle["records"][0]["epoch_id"],
            sequence=sequence,
            previous_record_hash=bundle["records"][-1]["record_hash"],
            payload={
                **source_evidence["payload"],
                "evidence_id": reused_evidence_id,
                "subject_ref": "subject:confirmation:alternate-root",
                "builder_release_ref": alternate_candidate["record_id"],
                "builder_release_hash": alternate_candidate["record_hash"],
            },
            dependency_refs={alternate_candidate["record_id"]: alternate_candidate["record_hash"]},
        )
        reused_consumption_id = "consumption:confirmation:alternate-root"
        reused_consumption = create_record(
            record_id=reused_consumption_id,
            record_type="confirmation_consumption",
            epoch_id=bundle["records"][0]["epoch_id"],
            sequence=sequence + 1,
            previous_record_hash=reused_evidence["record_hash"],
            payload={
                "consumption_id": reused_consumption_id,
                "partition": "confirmation",
                "confirmation_ref": reused_evidence_id,
                "confirmation_hash": reused_evidence["record_hash"],
                "candidate_ref": alternate_candidate["record_id"],
                "candidate_hash": alternate_candidate["record_hash"],
                "authority": protocol["principals"]["confirmation"]["principal_id"],
                "consumed": True,
            },
            dependency_refs={
                reused_evidence_id: reused_evidence["record_hash"],
                alternate_candidate["record_id"]: alternate_candidate["record_hash"],
            },
        )
        with self.assertRaisesRegex(CoevolutionError, "confirmation_reuse"):
            append_bundle(
                bundle,
                [reused_evidence, reused_consumption],
                bundle_id="bundle:confirmation-root-reuse",
                protocol=protocol,
            )

    def test_confirmation_exposure_alias_is_single_use_by_task_hash(self) -> None:
        """An exposure through a binding alias taints the same sealed pack."""

        from ael.coevolution_simulator import default_protocol, simulate

        protocol = default_protocol(seed=17, scenarios=["useful"])
        full = simulate(protocol)
        final_promote = next(
            record
            for record in full["records"]
            if record["record_type"] == "promotion_transition"
            and record["payload"].get("to_state") == "promote"
        )
        prefix_records = full["records"][: final_promote["sequence"]]
        prefix = create_bundle(
            protocol,
            bundle_id="bundle:confirmation-exposure-alias-prefix",
            records=prefix_records,
        )
        binding = next(
            record
            for record in prefix["records"]
            if record["record_id"] == "binding:A5:confirmation:v1"
        )
        sequence = prefix["records"][-1]["sequence"] + 1
        exposure = create_record(
            record_id="exposure:A5:confirmation:alias",
            record_type="exposure_event",
            epoch_id=prefix["records"][0]["epoch_id"],
            sequence=sequence,
            previous_record_hash=prefix["records"][-1]["record_hash"],
            payload={
                "exposure_id": "exposure:A5:confirmation:alias",
                "target_ref": binding["record_id"],
                "target_hash": binding["record_hash"],
                "partition": "confirmation",
                "exposure_kind": "post-consumption-alias",
                "amount": 1,
            },
            dependency_refs={binding["record_id"]: binding["record_hash"]},
        )
        promote_payload = copy.deepcopy(final_promote["payload"])
        promote_payload["transition_id"] = "promotion:A5:4:promote-after-alias-exposure"
        promote_payload["evidence_refs"] = [
            *promote_payload["evidence_refs"],
            exposure["record_id"],
        ]
        promote_dependencies = {
            item["record_id"]: item["record_hash"] for item in final_promote["dependency_refs"]
        }
        promote_dependencies[exposure["record_id"]] = exposure["record_hash"]
        promote = create_record(
            record_id=promote_payload["transition_id"],
            record_type="promotion_transition",
            epoch_id=prefix["records"][0]["epoch_id"],
            sequence=sequence + 1,
            previous_record_hash=exposure["record_hash"],
            payload=promote_payload,
            dependency_refs=promote_dependencies,
        )
        with self.assertRaisesRegex(CoevolutionError, "promotion_claim|promotion_stage_blocker"):
            append_bundle(
                prefix,
                [exposure, promote],
                bundle_id="bundle:confirmation-exposure-alias",
                protocol=protocol,
            )

    def test_confirmation_evidence_is_historical_only_for_rescore(self) -> None:
        from ael.coevolution_simulator import default_protocol, simulate

        protocol = default_protocol(seed=17, scenarios=["useful"])
        bundle = simulate(protocol)
        evaluator_record = next(
            record
            for record in bundle["records"]
            if record["record_type"] == "evaluator_release"
            and record["record_id"] == "evaluator:A5:v1"
        )
        confirmation_score = next(
            record
            for record in bundle["records"]
            if record["record_type"] == "score_run"
            and record["payload"].get("partition") == "confirmation"
        )
        evaluator_payload = copy.deepcopy(evaluator_record["payload"])
        evaluator_payload["release_id"] = "evaluator:A5:confirmation-rescore"
        score_payload = copy.deepcopy(confirmation_score["payload"])
        score_payload["score_run_id"] = "score:A5:confirmation:rescore"
        with self.assertRaisesRegex(CoevolutionError, "historical_only"):
            append_rescore(
                bundle,
                evaluator_payload,
                score_payload,
                actor=protocol["principals"]["adjudication"]["principal_id"],
                retained_surfaces=score_payload["surface_refs"],
                required_surfaces=score_payload["surface_refs"],
                protocol=protocol,
            )

    def test_score_run_cannot_carry_confirmation_consumption_ref(self) -> None:
        score = next(
            record
            for record in CoevolutionFixtures.records()
            if record["record_type"] == "score_run"
        )
        payload = copy.deepcopy(score["payload"])
        payload["score_run_id"] = "Q-confirmation-ref"
        payload["confirmation_consumption_ref"] = "consumption:confirmation:v1"
        with self.assertRaisesRegex(CoevolutionError, "unknown_field"):
            create_record(
                record_id="Q-confirmation-ref",
                record_type="score_run",
                epoch_id="epoch:test",
                sequence=5,
                previous_record_hash=CoevolutionFixtures.records()[-2]["record_hash"],
                payload=payload,
                dependency_refs={
                    "X0": CoevolutionFixtures.records()[4]["record_hash"],
                    "V0": CoevolutionFixtures.records()[3]["record_hash"],
                    "E0": CoevolutionFixtures.records()[1]["record_hash"],
                },
            )

    def test_bridge_and_comparability_substitution_cannot_promote_another_candidate(self) -> None:
        from ael.coevolution_simulator import default_protocol, simulate

        protocol = default_protocol(seed=17, scenarios=["useful", "forbidden_effect"])
        bundle = simulate(protocol)
        forbidden = next(
            record
            for record in bundle["records"]
            if record["record_type"] == "builder_release"
            and record["record_id"] == "builder:A5:forbidden:v1"
        )
        promoted_id = "promotion:A5:4:promote"

        def mutate_promotion(records: list[dict[str, object]]) -> None:
            target = next(record for record in records if record["record_id"] == promoted_id)
            target["payload"]["candidate_ref"] = forbidden["record_id"]
            target["payload"]["candidate_hash"] = forbidden["record_hash"]

        substituted = _rechain_mutated_bundle(bundle, mutate_promotion)
        with self.assertRaisesRegex(
            CoevolutionError, "missing_dependency_edge|promotion_evidence|promotion_candidate"
        ):
            validate_bundle(substituted, protocol=protocol)

        bridge = next(
            record for record in bundle["records"] if record["record_type"] == "bridge_observation"
        )

        def mutate_bridge(records: list[dict[str, object]]) -> None:
            target = next(
                record for record in records if record["record_id"] == bridge["record_id"]
            )
            target["payload"]["new_builder_ref"] = forbidden["record_id"]
            target["payload"]["new_builder_hash"] = forbidden["record_hash"]

        substituted_bridge = _rechain_mutated_bundle(bundle, mutate_bridge)
        with self.assertRaisesRegex(
            CoevolutionError, "bridge_order|bridge_identity|bridge_insufficient|dangling_dependency"
        ):
            validate_bundle(substituted_bridge, protocol=protocol)

        duplicate_payload = copy.deepcopy(bridge["payload"])
        duplicate_payload["bridge_id"] = "bridge:A5:evaluator:duplicate"
        duplicate = create_record(
            record_id=duplicate_payload["bridge_id"],
            record_type="bridge_observation",
            epoch_id=bundle["records"][0]["epoch_id"],
            sequence=bundle["records"][-1]["sequence"] + 1,
            previous_record_hash=bundle["records"][-1]["record_hash"],
            payload=duplicate_payload,
            dependency_refs=bridge["dependency_refs"],
        )
        with self.assertRaisesRegex(CoevolutionError, "bridge_reuse"):
            append_bundle(
                bundle,
                [duplicate],
                bundle_id="bundle:bridge-root-reuse",
                protocol=protocol,
            )

    def test_bridge_facts_require_prior_candidate_bridge_eligible(self) -> None:
        from ael.coevolution_simulator import default_protocol, simulate

        protocol = default_protocol(seed=17, scenarios=["useful"])
        bundle = simulate(protocol)

        def remove_bridge_eligibility(records: list[dict[str, object]]) -> None:
            target = next(
                record
                for record in records
                if record["record_type"] == "promotion_transition"
                and record["payload"].get("to_state") == "bridge_eligible"
            )
            target["payload"]["to_state"] = "new_measurement_epoch"

        invalid = _rechain_mutated_bundle(bundle, remove_bridge_eligibility)
        with self.assertRaisesRegex(CoevolutionError, "bridge_order"):
            validate_bundle(invalid, protocol=protocol)

    def test_independence_custody_requires_roles_and_allows_generation_reuse(self) -> None:
        from ael.coevolution_simulator import default_protocol, simulate

        protocol = default_protocol(seed=17, scenarios=["useful"])
        bundle = simulate(protocol)
        assessment_id = "independence:A5:promotion:v1"

        # The simulator's frozen protected dimensions already include custody;
        # retaining its complete assessment is the positive baseline.  The
        # same role may legitimately reuse custody across generations.
        with_custody = copy.deepcopy(bundle)
        self.assertEqual(
            validate_bundle(with_custody, protocol=protocol)["bundle_hash"],
            with_custody["bundle_hash"],
        )

        def remove_roles(records: list[dict[str, object]]) -> None:
            target = next(record for record in records if record["record_id"] == assessment_id)
            target["payload"]["evidence_refs"] = [
                item for item in target["payload"]["evidence_refs"] if "anchor-observation" in item
            ]
            target["dependency_refs"] = [
                item
                for item in target["dependency_refs"]
                if "anchor-observation" in item["record_id"]
            ]

        missing_roles = _rechain_mutated_bundle(with_custody, remove_roles)
        missing_roles["protocol_hash"] = bundle["protocol_hash"]
        missing_roles["bundle_hash"] = bundle_hash(
            {key: value for key, value in missing_roles.items() if key != "bundle_hash"}
        )
        with self.assertRaisesRegex(CoevolutionError, "independence_custody"):
            validate_bundle(missing_roles, protocol=protocol)

        def overlap_roles(records: list[dict[str, object]]) -> None:
            target = next(
                record
                for record in records
                if record["record_type"] == "evaluator_release"
                and record["record_id"] == "evaluator:A5:v1"
            )
            target["payload"]["custody"] = "synthetic:builder:custody"

        overlapping = _rechain_mutated_bundle(with_custody, overlap_roles)
        overlapping["protocol_hash"] = bundle["protocol_hash"]
        overlapping["bundle_hash"] = bundle_hash(
            {key: value for key, value in overlapping.items() if key != "bundle_hash"}
        )
        with self.assertRaisesRegex(CoevolutionError, "independence_custody"):
            validate_bundle(overlapping, protocol=protocol)

    def test_promotion_transitions_and_blockers(self) -> None:
        independent = {"organization": "separate", "model_family": "separate"}
        first = reduce_promotion(
            "registered",
            {
                "from_state": "registered",
                "to_state": "development_eligible",
                "predecessor_transition_hash": "0" * 64,
                "actor": "builder",
                "approval_actor": "promotion",
            },
            evidence={"independence": independent},
        )
        self.assertEqual(first["state"], "development_eligible")
        with self.assertRaisesRegex(CoevolutionError, "illegal_transition"):
            reduce_promotion(
                first,
                {
                    "from_state": "development_eligible",
                    "to_state": "promote",
                    "predecessor_transition_hash": first["transition_hash"],
                    "actor": "builder",
                    "approval_actor": "promotion",
                },
                evidence={"independence": independent},
            )
        with self.assertRaisesRegex(CoevolutionError, "self_approval"):
            reduce_promotion(
                "registered",
                {
                    "from_state": "registered",
                    "to_state": "development_eligible",
                    "predecessor_transition_hash": "0" * 64,
                    "actor": "same",
                    "approval_actor": "same",
                },
                evidence={"independence": independent},
            )
        with self.assertRaisesRegex(CoevolutionError, "independence_ceiling"):
            reduce_promotion(
                "registered",
                {
                    "from_state": "registered",
                    "to_state": "development_eligible",
                    "predecessor_transition_hash": "0" * 64,
                    "actor": "builder",
                    "approval_actor": "promotion",
                },
                evidence={"independence": {"organization": "unknown"}},
            )
        with self.assertRaisesRegex(CoevolutionError, "effect_quarantine"):
            reduce_promotion(
                "registered",
                {
                    "from_state": "registered",
                    "to_state": "development_eligible",
                    "predecessor_transition_hash": "0" * 64,
                    "actor": "builder",
                    "approval_actor": "promotion",
                },
                evidence={"independence": independent, "effect_attempt": True},
            )
        with self.assertRaisesRegex(CoevolutionError, "approval_authority"):
            reduce_promotion(
                "registered",
                {
                    "from_state": "registered",
                    "to_state": "development_eligible",
                    "predecessor_transition_hash": "0" * 64,
                    "actor": "builder",
                    "approval_actor": "wrong",
                },
                evidence={"independence": {"organization": "separate", "model_family": "separate"}},
                protocol=CoevolutionFixtures.protocol(),
            )

    def test_promotion_projection_is_candidate_keyed_for_interleaved_candidates(self) -> None:
        # Keep the predecessor free of pre-decision screening facts so each
        # interleaved candidate starts its own prospective state machine at
        # registered; stage closure still scans the complete available prefix.
        bundle = create_bundle(
            CoevolutionFixtures.protocol(),
            bundle_id="bundle:interleaved-base",
            records=CoevolutionFixtures.records()[:3],
        )
        candidate = create_record(
            record_id="B1",
            record_type="builder_release",
            epoch_id="epoch:test",
            sequence=3,
            previous_record_hash=bundle["records"][-1]["record_hash"],
            payload={**CoevolutionFixtures.builder(), "release_id": "B1", "revision": "b1"},
        )
        independent = {"organization": "separate", "model_family": "separate"}

        def transition(
            record_id: str,
            sequence: int,
            previous_hash: str,
            candidate_ref: str,
            candidate_hash: str,
            from_state: str,
            to_state: str,
            predecessor_hash: str,
            predecessor_ref: str | None = None,
        ) -> dict[str, object]:
            payload = {
                "transition_id": record_id,
                "candidate_ref": candidate_ref,
                "candidate_hash": candidate_hash,
                "from_state": from_state,
                "to_state": to_state,
                "predecessor_transition_hash": predecessor_hash,
                "actor": "builder",
                "approval_actor": "promotion",
                "independence": independent,
                "confirmation_status": "not_opened",
                "bridge_status": "not_opened",
                "critical_failure": False,
                "effect_attempt": False,
                "revoked_ancestry": False,
                "reason": "interleaved",
                "evidence_refs": [],
            }
            dependencies: dict[str, str] = {candidate_ref: candidate_hash}
            if predecessor_ref is not None:
                payload["predecessor_transition_ref"] = predecessor_ref
                dependencies[predecessor_ref] = predecessor_hash
            return create_record(
                record_id=record_id,
                record_type="promotion_transition",
                epoch_id="epoch:test",
                sequence=sequence,
                previous_record_hash=previous_hash,
                payload=payload,
                dependency_refs=dependencies,
            )

        b0_dev = transition(
            "P:B0:dev",
            4,
            candidate["record_hash"],
            "B0",
            bundle["records"][0]["record_hash"],
            "registered",
            "development_eligible",
            "0" * 64,
        )
        b1_dev = transition(
            "P:B1:dev",
            5,
            b0_dev["record_hash"],
            "B1",
            candidate["record_hash"],
            "registered",
            "development_eligible",
            "0" * 64,
        )
        b0_reject = transition(
            "P:B0:reject",
            6,
            b1_dev["record_hash"],
            "B0",
            bundle["records"][0]["record_hash"],
            "development_eligible",
            "screening_reject",
            b0_dev["record_hash"],
            "P:B0:dev",
        )
        interleaved = append_bundle(
            bundle,
            [candidate, b0_dev, b1_dev, b0_reject],
            bundle_id="bundle:interleaved",
            protocol=CoevolutionFixtures.protocol(),
        )
        projection = project_bundle(interleaved, predecessor=bundle)
        self.assertEqual(projection["promotion_states"]["B0"]["state"], "screening_reject")
        self.assertEqual(projection["promotion_states"]["B1"]["state"], "development_eligible")
        self.assertIsNone(projection["promotion_state"])
        self.assertIsNone(projection["promotion"])

    def test_tombstone_transitive_projection_does_not_mutate(self) -> None:
        bundle = CoevolutionFixtures.bundle()
        before = copy.deepcopy(bundle)
        tombstone = create_record(
            record_id="T0",
            record_type="deletion_tombstone",
            epoch_id="epoch:test",
            sequence=6,
            previous_record_hash=bundle["records"][-1]["record_hash"],
            payload={
                "tombstone_id": "T0",
                "targets": ["B0"],
                "authority": "evidence",
                "reason": "revoked",
                "descendant_policy": "revoke-or-unscorable-all-dependants",
                "deleted_surfaces": ["output"],
            },
            dependency_refs={"B0": bundle["records"][0]["record_hash"]},
        )
        tombstoned = append_bundle(bundle, [tombstone], bundle_id="bundle:tombstone")
        projection = project_bundle(tombstoned, predecessor=bundle)
        self.assertIn("B0", projection["revoked_record_ids"])
        self.assertIn("Q0", projection["revoked_record_ids"])
        self.assertEqual(bundle, before)

    def test_post_promotion_tombstone_has_one_authorized_revoke_path(self) -> None:
        from ael.coevolution_simulator import default_protocol, simulate

        protocol = default_protocol(seed=17, scenarios=["useful"])
        bundle = simulate(protocol)
        promoted = next(
            record
            for record in reversed(bundle["records"])
            if record["record_type"] == "promotion_transition"
            and record["payload"]["to_state"] == "promote"
        )
        candidate_ref = promoted["payload"]["candidate_ref"]
        candidate = next(
            record for record in bundle["records"] if record["record_id"] == candidate_ref
        )
        sequence = bundle["records"][-1]["sequence"] + 1
        tombstone = create_record(
            record_id="tombstone:promoted-candidate",
            record_type="deletion_tombstone",
            epoch_id=bundle["records"][0]["epoch_id"],
            sequence=sequence,
            previous_record_hash=bundle["records"][-1]["record_hash"],
            payload={
                "tombstone_id": "tombstone:promoted-candidate",
                "targets": [candidate_ref],
                "authority": protocol["principals"]["evidence"]["principal_id"],
                "reason": "post-promotion-revocation",
                "descendant_policy": "revoke-or-unscorable-all-dependants",
                "deleted_surfaces": ["subject-output"],
            },
            dependency_refs={candidate_ref: candidate["record_hash"]},
        )
        revoke_id = "promotion:A5:post-tombstone-revoke"
        revoke = create_record(
            record_id=revoke_id,
            record_type="promotion_transition",
            epoch_id=bundle["records"][0]["epoch_id"],
            sequence=sequence + 1,
            previous_record_hash=tombstone["record_hash"],
            payload={
                "transition_id": revoke_id,
                "candidate_ref": candidate_ref,
                "candidate_hash": candidate["record_hash"],
                "from_state": "promote",
                "to_state": "revoke",
                "predecessor_transition_ref": promoted["record_id"],
                "predecessor_transition_hash": promoted["record_hash"],
                "actor": protocol["principals"]["adjudication"]["principal_id"],
                "approval_actor": protocol["principals"]["promotion"]["principal_id"],
                "independence": promoted["payload"]["independence"],
                "confirmation_status": promoted["payload"]["confirmation_status"],
                "bridge_status": promoted["payload"]["bridge_status"],
                "critical_failure": False,
                "effect_attempt": False,
                "revoked_ancestry": False,
                "reason": "tombstone-containment",
                "evidence_refs": [tombstone["record_id"]],
            },
            dependency_refs={
                candidate_ref: candidate["record_hash"],
                promoted["record_id"]: promoted["record_hash"],
                tombstone["record_id"]: tombstone["record_hash"],
            },
        )
        successor = append_bundle(
            bundle,
            [tombstone, revoke],
            bundle_id="bundle:post-promotion-revoke",
            protocol=protocol,
        )
        projection = project_bundle(successor, protocol=protocol, predecessor=bundle)
        state = projection["promotion_states"][candidate_ref]
        self.assertEqual(state["state"], "revoke")
        self.assertFalse(state["revoke_required"])
        self.assertTrue(state["promotion_quarantined"])
        self.assertNotIn(revoke_id, projection["revoked_record_ids"])

    def test_tombstone_revoke_is_legal_from_each_preterminal_stage(self) -> None:
        """A tombstone must leave every preterminal state with a safe closure."""

        from ael.coevolution_simulator import default_protocol, simulate

        protocol = default_protocol(seed=17, scenarios=["useful"])
        full_bundle = simulate(protocol)
        for stage in (
            "development_eligible",
            "screening_pass",
            "bridge_eligible",
            "confirmation_eligible",
        ):
            with self.subTest(stage=stage):
                stage_transition = next(
                    record
                    for record in full_bundle["records"]
                    if record["record_type"] == "promotion_transition"
                    and record["payload"]["to_state"] == stage
                )
                prefix = create_bundle(
                    protocol,
                    bundle_id=f"bundle:prefix:{stage}",
                    records=full_bundle["records"][: stage_transition["sequence"] + 1],
                )
                candidate_ref = stage_transition["payload"]["candidate_ref"]
                candidate = next(
                    record for record in prefix["records"] if record["record_id"] == candidate_ref
                )
                sequence = prefix["records"][-1]["sequence"] + 1
                tombstone_id = f"tombstone:{stage}"
                tombstone = create_record(
                    record_id=tombstone_id,
                    record_type="deletion_tombstone",
                    epoch_id=prefix["records"][0]["epoch_id"],
                    sequence=sequence,
                    previous_record_hash=prefix["records"][-1]["record_hash"],
                    payload={
                        "tombstone_id": tombstone_id,
                        "targets": [candidate_ref],
                        "authority": protocol["principals"]["evidence"]["principal_id"],
                        "reason": "preterminal-tombstone",
                        "descendant_policy": "revoke-or-unscorable-all-dependants",
                        "deleted_surfaces": ["subject-output"],
                    },
                    dependency_refs={candidate_ref: candidate["record_hash"]},
                )
                revoke_id = f"promotion:{stage}:tombstone-revoke"
                stage_payload = stage_transition["payload"]
                revoke_payload = {
                    "transition_id": revoke_id,
                    "candidate_ref": candidate_ref,
                    "candidate_hash": candidate["record_hash"],
                    "from_state": stage,
                    "to_state": "revoke",
                    "predecessor_transition_ref": stage_transition["record_id"],
                    "predecessor_transition_hash": stage_transition["record_hash"],
                    "actor": protocol["principals"]["adjudication"]["principal_id"],
                    "approval_actor": protocol["principals"]["promotion"]["principal_id"],
                    "independence": stage_payload["independence"],
                    "confirmation_status": stage_payload["confirmation_status"],
                    "bridge_status": stage_payload["bridge_status"],
                    "critical_failure": False,
                    "effect_attempt": False,
                    "revoked_ancestry": False,
                    "reason": "tombstone-containment",
                    "evidence_refs": [tombstone_id],
                }
                revoke = create_record(
                    record_id=revoke_id,
                    record_type="promotion_transition",
                    epoch_id=prefix["records"][0]["epoch_id"],
                    sequence=sequence + 1,
                    previous_record_hash=tombstone["record_hash"],
                    payload=revoke_payload,
                    dependency_refs={
                        candidate_ref: candidate["record_hash"],
                        stage_transition["record_id"]: stage_transition["record_hash"],
                        tombstone_id: tombstone["record_hash"],
                    },
                )
                successor = append_bundle(
                    prefix,
                    [tombstone, revoke],
                    bundle_id=f"bundle:{stage}:tombstone-revoke",
                    protocol=protocol,
                )
                projection = project_bundle(successor, protocol=protocol, predecessor=prefix)
                state = projection["promotion_states"][candidate_ref]
                self.assertEqual(state["state"], "revoke")
                self.assertTrue(state["promotion_quarantined"])
                self.assertFalse(state["revoke_required"])

    def test_early_stage_revoke_without_tombstone_is_rejected(self) -> None:
        from ael.coevolution_simulator import default_protocol, simulate

        protocol = default_protocol(seed=17, scenarios=["useful"])
        bundle = simulate(protocol)
        stage_transition = next(
            record
            for record in bundle["records"]
            if record["record_type"] == "promotion_transition"
            and record["payload"]["to_state"] == "development_eligible"
        )
        candidate_ref = stage_transition["payload"]["candidate_ref"]
        candidate = next(
            record for record in bundle["records"] if record["record_id"] == candidate_ref
        )
        sequence = bundle["records"][-1]["sequence"] + 1
        payload = {
            **{
                key: stage_transition["payload"][key]
                for key in (
                    "candidate_ref",
                    "candidate_hash",
                    "independence",
                    "confirmation_status",
                    "bridge_status",
                )
            },
            "transition_id": "promotion:development_eligible:bare-revoke",
            "from_state": "development_eligible",
            "to_state": "revoke",
            "predecessor_transition_ref": stage_transition["record_id"],
            "predecessor_transition_hash": stage_transition["record_hash"],
            "actor": protocol["principals"]["adjudication"]["principal_id"],
            "approval_actor": protocol["principals"]["promotion"]["principal_id"],
            "critical_failure": False,
            "effect_attempt": False,
            "revoked_ancestry": False,
            "reason": "bare-early-revoke",
            "evidence_refs": [],
        }
        revoke = create_record(
            record_id=payload["transition_id"],
            record_type="promotion_transition",
            epoch_id=bundle["records"][0]["epoch_id"],
            sequence=sequence,
            previous_record_hash=bundle["records"][-1]["record_hash"],
            payload=payload,
            dependency_refs={
                candidate_ref: candidate["record_hash"],
                stage_transition["record_id"]: stage_transition["record_hash"],
            },
        )
        with self.assertRaisesRegex(CoevolutionError, "revocation_evidence"):
            append_bundle(
                bundle,
                [revoke],
                bundle_id="bundle:bare-early-revoke",
                protocol=protocol,
            )

    def test_early_stage_revoke_rejects_unrelated_tombstone(self) -> None:
        from ael.coevolution_simulator import default_protocol, simulate

        protocol = default_protocol(seed=17, scenarios=["useful"])
        bundle = simulate(protocol)
        stage_transition = next(
            record
            for record in bundle["records"]
            if record["record_type"] == "promotion_transition"
            and record["payload"]["to_state"] == "development_eligible"
        )
        candidate_ref = stage_transition["payload"]["candidate_ref"]
        candidate = next(
            record for record in bundle["records"] if record["record_id"] == candidate_ref
        )
        unrelated = next(
            record for record in bundle["records"] if record["record_type"] == "measurement_method"
        )
        sequence = bundle["records"][-1]["sequence"] + 1
        tombstone_id = "tombstone:unrelated"
        tombstone = create_record(
            record_id=tombstone_id,
            record_type="deletion_tombstone",
            epoch_id=bundle["records"][0]["epoch_id"],
            sequence=sequence,
            previous_record_hash=bundle["records"][-1]["record_hash"],
            payload={
                "tombstone_id": tombstone_id,
                "targets": [unrelated["record_id"]],
                "authority": protocol["principals"]["evidence"]["principal_id"],
                "reason": "unrelated-target",
                "descendant_policy": "revoke-or-unscorable-all-dependants",
                "deleted_surfaces": ["method"],
            },
            dependency_refs={unrelated["record_id"]: unrelated["record_hash"]},
        )
        payload = {
            **{
                key: stage_transition["payload"][key]
                for key in (
                    "candidate_ref",
                    "candidate_hash",
                    "independence",
                    "confirmation_status",
                    "bridge_status",
                )
            },
            "transition_id": "promotion:development_eligible:unrelated-revoke",
            "from_state": "development_eligible",
            "to_state": "revoke",
            "predecessor_transition_ref": stage_transition["record_id"],
            "predecessor_transition_hash": stage_transition["record_hash"],
            "actor": protocol["principals"]["adjudication"]["principal_id"],
            "approval_actor": protocol["principals"]["promotion"]["principal_id"],
            "critical_failure": False,
            "effect_attempt": False,
            "revoked_ancestry": False,
            "reason": "unrelated-tombstone-revoke",
            "evidence_refs": [tombstone_id],
        }
        revoke = create_record(
            record_id=payload["transition_id"],
            record_type="promotion_transition",
            epoch_id=bundle["records"][0]["epoch_id"],
            sequence=sequence + 1,
            previous_record_hash=tombstone["record_hash"],
            payload=payload,
            dependency_refs={
                candidate_ref: candidate["record_hash"],
                stage_transition["record_id"]: stage_transition["record_hash"],
                tombstone_id: tombstone["record_hash"],
            },
        )
        with self.assertRaisesRegex(CoevolutionError, "revocation_evidence"):
            append_bundle(
                bundle,
                [tombstone, revoke],
                bundle_id="bundle:unrelated-tombstone-revoke",
                protocol=protocol,
            )

    def test_operating_summary_is_closed_and_schema_bound(self) -> None:
        counts = {
            "disposition": {
                "eligible": 4,
                "quarantined": 1,
                "revoked": 0,
                "unscorable": 1,
                "invalid": 0,
                "missing": 0,
            },
            "promotion": {"useful": 1, "null": 1, "harmful": 0, "adversarial": 0},
            "candidate_opportunities": {"useful": 1, "null": 1, "harmful": 0, "adversarial": 0},
            "exploit": {"candidates": 1, "accepted": 0},
            "critical_failures": 0,
            "bridge": {
                "attempted": 2,
                "passed": 1,
                "failed": 1,
                "unknown": 0,
                "later_reversal": 0,
            },
            "tainted": 1,
            "revocation": {"declared_descendants": 2, "complete_descendants": 2},
            "optional_stopping": {"events": 0, "eligible_replicates": 0},
        }
        trajectory = create_record(
            record_id="trajectory:A0:null",
            record_type="trajectory_summary",
            epoch_id="epoch:test",
            sequence=0,
            previous_record_hash=None,
            payload={
                "summary_id": "trajectory:A0:null",
                "arm": "A0",
                "scenario_ref": "scenario:null",
                "counts": counts,
                "primary_endpoint": {"sum_ppm": 500_000, "observed_count": 1},
                "budget": {"target": 1, "actual": 1, "delta": 0},
            },
            dependency_refs={},
        )
        seal = create_record(
            record_id="contrast-summary:stage0",
            record_type="contrast_summary",
            epoch_id="epoch:test",
            sequence=1,
            previous_record_hash=trajectory["record_hash"],
            payload={
                "summary_id": "contrast-summary:stage0",
                "aggregation_version": "ael-cep-stage0-contrast-summary/v1",
                "contrasts": [
                    {
                        "contrast_id": "builder-effect",
                        "status": "causal_eligible",
                        "reason": None,
                        "endpoint_delta_ppm": 0,
                    }
                ],
            },
            dependency_refs={trajectory["record_id"]: trajectory["record_hash"]},
        )
        with open(
            Path(__file__).parents[1] / "src/ael/coevolution_schemas/bundle.schema.json"
        ) as fh:
            schema = json.load(fh)
        validator = Draft202012Validator(schema)
        self.assertEqual([], list(validator.descend(trajectory, schema["$defs"]["record"])))
        self.assertEqual([], list(validator.descend(seal, schema["$defs"]["record"])))
        metrics = derive_operating_metrics(trajectory["payload"])
        self.assertEqual(
            metrics["false_promotion_share"], {"count": 1, "denominator": 2, "rate": 0.5}
        )
        self.assertEqual(metrics["exploit_acceptance"], {"count": 0, "denominator": 1, "rate": 0.0})
        self.assertEqual(metrics["missingness"], {"count": 0, "denominator": 6, "rate": 0.0})

    def test_operating_summary_rejects_arbitrary_metrics_and_count_invariants(self) -> None:
        counts = {
            "disposition": {
                "eligible": 1,
                "quarantined": 0,
                "revoked": 0,
                "unscorable": 0,
                "invalid": 0,
                "missing": 0,
            },
            "promotion": {"useful": 0, "null": 0, "harmful": 0, "adversarial": 0},
            "candidate_opportunities": {"useful": 0, "null": 0, "harmful": 0, "adversarial": 0},
            "exploit": {"candidates": 0, "accepted": 0},
            "critical_failures": 0,
            "bridge": {"attempted": 0, "passed": 0, "failed": 0, "unknown": 0, "later_reversal": 0},
            "tainted": 0,
            "revocation": {"declared_descendants": 0, "complete_descendants": 0},
            "optional_stopping": {"events": 0, "eligible_replicates": 0},
        }
        bad = copy.deepcopy(counts)
        bad["bridge"]["attempted"] = 1
        with self.assertRaisesRegex(CoevolutionError, "unknown_field|summary_counts"):
            create_record(
                record_id="trajectory:A0:null",
                record_type="trajectory_summary",
                epoch_id="epoch:test",
                sequence=0,
                previous_record_hash=None,
                payload={
                    "summary_id": "trajectory:A0:null",
                    "arm": "A0",
                    "scenario_ref": "scenario:null",
                    "counts": bad,
                    "primary_endpoint": {"sum_ppm": 0, "observed_count": 0},
                    "budget": {"target": 1, "actual": 1, "delta": 0},
                    "metrics": {"forged": 1},
                },
                dependency_refs={},
            )

    def test_structured_scenarios_endpoints_and_contrast_diagnostics(self) -> None:
        protocol = CoevolutionFixtures.protocol()
        bad_protocol = copy.deepcopy(protocol)
        bad_protocol["simulation"]["scenarios"][0] = "legacy-string"
        with self.assertRaisesRegex(CoevolutionError, "simulation_scenarios"):
            validate_protocol(bad_protocol)

        def row(arm: str, scenario_ref: str, sum_ppm: int) -> dict[str, object]:
            return {
                "summary_id": f"trajectory:{arm}:{scenario_ref}",
                "arm": arm,
                "scenario_ref": scenario_ref,
                "counts": {
                    "disposition": {
                        "eligible": 1,
                        "quarantined": 0,
                        "revoked": 0,
                        "unscorable": 0,
                        "invalid": 0,
                        "missing": 0,
                    },
                    "promotion": {"useful": 1, "null": 0, "harmful": 0, "adversarial": 0},
                    "candidate_opportunities": {
                        "useful": 1,
                        "null": 0,
                        "harmful": 0,
                        "adversarial": 0,
                    },
                    "exploit": {"candidates": 0, "accepted": 0},
                    "critical_failures": 0,
                    "bridge": {
                        "attempted": 0,
                        "passed": 0,
                        "failed": 0,
                        "unknown": 0,
                        "later_reversal": 0,
                    },
                    "tainted": 0,
                    "revocation": {"declared_descendants": 0, "complete_descendants": 0},
                    "optional_stopping": {"events": 0, "eligible_replicates": 0},
                },
                "primary_endpoint": {"sum_ppm": sum_ppm, "observed_count": 1},
                "budget": {"target": 1, "actual": 1, "delta": 0},
            }

        rows = [
            row(arm, scenario_ref, 500_000 if arm == "A0" else 600_000)
            for arm in protocol["arms"]
            for scenario_ref in ("scenario:null", "scenario:improvement", "scenario:exploitation")
        ]
        endpoints = derive_arm_primary_endpoints(protocol, rows)
        self.assertEqual(
            endpoints["A0"], {"sum_ppm": 1_500_000, "observed_count": 3, "mean_ppm": 500_000}
        )
        diagnostics = derive_contrast_diagnostics(protocol, rows)
        self.assertEqual(
            diagnostics,
            [
                {
                    "contrast_id": "builder-effect",
                    "status": "causal_eligible",
                    "reason": None,
                    "endpoint_delta_ppm": -100_000,
                }
            ],
        )
        # A row-level missing endpoint is not repaired by the arm aggregate:
        # each frozen arm×scenario row must observe exactly the scenario task
        # count before the contrast can be causal.
        partial_rows = copy.deepcopy(rows)
        partial_rows[0]["primary_endpoint"] = {"sum_ppm": 0, "observed_count": 0}
        partial_diagnostics = derive_contrast_diagnostics(protocol, partial_rows)
        self.assertEqual(
            partial_diagnostics,
            [
                {
                    "contrast_id": "builder-effect",
                    "status": "not_estimable",
                    "reason": "missing_endpoint",
                    "endpoint_delta_ppm": None,
                }
            ],
        )
        missingness_protocol = copy.deepcopy(protocol)
        missingness_protocol["simulation"]["scenarios"][0]["name"] = "missingness"
        missingness_rows = copy.deepcopy(rows)
        for row_value in missingness_rows:
            if row_value["scenario_ref"] == "scenario:null":
                row_value["scenario_ref"] = "scenario:missingness"
        missingness_diagnostics = derive_contrast_diagnostics(
            missingness_protocol, missingness_rows
        )
        self.assertEqual(missingness_diagnostics[0]["status"], "causal_eligible")
        missingness_rows[0]["primary_endpoint"] = {"sum_ppm": 0, "observed_count": 0}
        missingness_diagnostics = derive_contrast_diagnostics(
            missingness_protocol, missingness_rows
        )
        self.assertEqual(missingness_diagnostics[0]["reason"], "missing_endpoint")
        self.assertIsNone(missingness_diagnostics[0]["endpoint_delta_ppm"])
        multi_protocol = copy.deepcopy(protocol)
        multi_protocol["simulation"]["scenarios"][0]["replicates"] = 3
        multi_rows = copy.deepcopy(rows)
        for row_value in multi_rows:
            if row_value["scenario_ref"] != "scenario:null":
                continue
            row_value["counts"]["disposition"]["eligible"] = 3
            row_value["counts"]["candidate_opportunities"] = {
                "useful": 1,
                "null": 2,
                "harmful": 0,
                "adversarial": 0,
            }
            row_value["primary_endpoint"] = {"sum_ppm": 1_500_000, "observed_count": 3}
        multi_diagnostics = derive_contrast_diagnostics(multi_protocol, multi_rows)
        self.assertEqual(multi_diagnostics[0]["status"], "causal_eligible")
        multi_rows[0]["primary_endpoint"] = {"sum_ppm": 1_000_000, "observed_count": 2}
        multi_diagnostics = derive_contrast_diagnostics(multi_protocol, multi_rows)
        self.assertEqual(multi_diagnostics[0]["reason"], "missing_endpoint")
        self.assertIsNone(multi_diagnostics[0]["endpoint_delta_ppm"])
        rows[1]["budget"] = {"target": 1, "actual": 2, "delta": 1}
        diagnostics = derive_contrast_diagnostics(protocol, rows)
        self.assertEqual(diagnostics[0]["status"], "diagnostic_only")
        self.assertEqual(diagnostics[0]["reason"], "actual_cost_mismatch")
        rows[1]["budget"] = {"target": 1, "actual": 1, "delta": 0}
        rows[0]["counts"]["candidate_opportunities"]["useful"] = 0
        with self.assertRaisesRegex(CoevolutionError, "summary_counts"):
            derive_contrast_diagnostics(protocol, rows)
        rows[0]["counts"]["candidate_opportunities"]["useful"] = 1
        rows[0]["counts"]["promotion"]["useful"] = 2
        with self.assertRaisesRegex(CoevolutionError, "summary_counts"):
            derive_contrast_diagnostics(protocol, rows)

    def test_primary_endpoint_bounds_and_zero_observation(self) -> None:
        counts = {
            "disposition": {
                "eligible": 0,
                "quarantined": 0,
                "revoked": 0,
                "unscorable": 0,
                "invalid": 0,
                "missing": 0,
            },
            "promotion": {"useful": 0, "null": 0, "harmful": 0, "adversarial": 0},
            "candidate_opportunities": {"useful": 0, "null": 0, "harmful": 0, "adversarial": 0},
            "exploit": {"candidates": 0, "accepted": 0},
            "critical_failures": 0,
            "bridge": {"attempted": 0, "passed": 0, "failed": 0, "unknown": 0, "later_reversal": 0},
            "tainted": 0,
            "revocation": {"declared_descendants": 0, "complete_descendants": 0},
            "optional_stopping": {"events": 0, "eligible_replicates": 0},
        }
        base = {
            "summary_id": "trajectory:A0:null",
            "arm": "A0",
            "scenario_ref": "scenario:null",
            "counts": counts,
            "budget": {"target": 1, "actual": 1, "delta": 0},
        }
        with self.assertRaisesRegex(CoevolutionError, "summary_endpoint"):
            create_record(
                record_id="trajectory:A0:null",
                record_type="trajectory_summary",
                epoch_id="epoch:test",
                sequence=0,
                previous_record_hash=None,
                payload={**base, "primary_endpoint": {"sum_ppm": 1, "observed_count": 0}},
                dependency_refs={},
            )
        record = create_record(
            record_id="trajectory:A0:null",
            record_type="trajectory_summary",
            epoch_id="epoch:test",
            sequence=0,
            previous_record_hash=None,
            payload={**base, "primary_endpoint": {"sum_ppm": 0, "observed_count": 0}},
            dependency_refs={},
        )
        self.assertEqual(record["payload"]["primary_endpoint"], {"sum_ppm": 0, "observed_count": 0})
        bad = copy.deepcopy(counts)
        bad["tainted"] = True
        with self.assertRaisesRegex(CoevolutionError, "summary_counts"):
            create_record(
                record_id="trajectory:A0:null",
                record_type="trajectory_summary",
                epoch_id="epoch:test",
                sequence=0,
                previous_record_hash=None,
                payload={
                    "summary_id": "trajectory:A0:null",
                    "arm": "A0",
                    "scenario_ref": "scenario:null",
                    "counts": bad,
                    "primary_endpoint": {"sum_ppm": 0, "observed_count": 0},
                    "budget": {"target": 1, "actual": 1, "delta": 0},
                },
                dependency_refs={},
            )

    def test_contrast_seal_is_recomputed_and_revocation_clears_projection(self) -> None:
        from ael.coevolution_simulator import default_protocol, simulate

        protocol = default_protocol(seed=17, scenarios=["useful"])
        bundle = simulate(protocol)
        forged = copy.deepcopy(bundle)
        seal = next(
            record for record in forged["records"] if record["record_type"] == "contrast_summary"
        )
        seal["payload"]["contrasts"][0]["endpoint_delta_ppm"] += 1
        forged = _rechain_mutated_bundle(forged, lambda _records: None)
        with self.assertRaisesRegex(CoevolutionError, "summary_contrasts"):
            validate_bundle(forged, protocol=protocol)

        sequence = bundle["records"][-1]["sequence"] + 1
        seal = bundle["records"][-1]
        tombstone = create_record(
            record_id="tombstone:contrast-summary",
            record_type="deletion_tombstone",
            epoch_id=bundle["records"][0]["epoch_id"],
            sequence=sequence,
            previous_record_hash=seal["record_hash"],
            payload={
                "tombstone_id": "tombstone:contrast-summary",
                "targets": [seal["record_id"]],
                "authority": protocol["principals"]["evidence"]["principal_id"],
                "reason": "seal-revoked",
                "descendant_policy": "revoke-or-unscorable-all-dependants",
                "deleted_surfaces": ["summary"],
            },
            dependency_refs={seal["record_id"]: seal["record_hash"]},
        )
        revoked = append_bundle(
            bundle,
            [tombstone],
            bundle_id="bundle:contrast-summary-revoked",
            protocol=protocol,
        )
        projection = project_bundle(revoked, protocol=protocol, predecessor=bundle)
        self.assertNotIn(tombstone["record_id"], projection["revoked_record_ids"])
        self.assertIn(seal["record_id"], projection["revoked_record_ids"])
        self.assertEqual(projection["operating_metrics"], {})
        self.assertEqual(projection["primary_endpoints"], {})
        self.assertEqual(projection["contrast_diagnostics"], [])


if __name__ == "__main__":
    unittest.main()
