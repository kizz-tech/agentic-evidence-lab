from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from ael.completion_integrity_activation import (
    ACTIVATION_SCHEMA_VERSION,
    decide_activation,
    decision_id_from_study_id,
)
from ael.validation import validate
from tools.completion_integrity_activation_support import (
    load_json,
    sha256_path,
    write_json_atomic,
)

ROOT = Path(__file__).resolve().parents[1]
STUDIES_ROOT = ROOT / "studies" / "completion-integrity"
V1_ROOT = STUDIES_ROOT / "activation-v1"
V2_ROOT = STUDIES_ROOT / "activation-v2"


def _cell(entry: dict[str, object]) -> dict[str, object]:
    role = str(entry["role"])
    common: dict[str, object] = {
        "schema_version": "ael.completion-integrity-activation-cell/0.1-pilot",
        **entry,
        "attempt_id": "a" * 32,
        "status": "valid",
        "issues": [],
        "usage": {
            "input_tokens": 100,
            "cached_input_tokens": 25,
            "output_tokens": 10,
            "reasoning_output_tokens": 5,
            "wall_time_ms": 1000,
        },
        "event_count": 3,
        "private_refs": {"events_sha256": "1" * 64},
    }
    if role == "executor":
        return {
            **common,
            "artifact_sha256": "2" * 64,
            "evidence_bundle_sha256": "3" * 64,
            "evidence_tree_sha256": "4" * 64,
            "truth_sha256": "5" * 64,
            "capture_state": "observable_chain_complete",
            "executor_claim_agreement": True,
            "private_refs": {
                "events_sha256": "1" * 64,
                "candidate_tree_sha256": "2" * 64,
            },
        }
    return {
        **common,
        "tool_event_count": 1,
        "claim_agreement": True,
        "workspace_unchanged": True,
        "evidence_hash_match": True,
        "artifact_or_evaluator_exposed": False,
        "evidence_tree_sha256": "4" * 64,
        "private_refs": {
            "events_sha256": "1" * 64,
            "submission_sha256": "6" * 64,
        },
    }


def _observations(
    freeze: dict[str, object], preregistration_sha: str, *, study_root: Path
) -> dict[str, object]:
    return {
        "schema_version": ACTIVATION_SCHEMA_VERSION,
        "freeze_sha256": sha256_path(study_root / "freeze.json"),
        "preregistration_sha": preregistration_sha,
        "task_pack_sha256": freeze["private_pack"]["supply_artifact_sha256"],  # type: ignore[index]
        "qualification_sha256": freeze["qualification"]["receipt_sha256"],  # type: ignore[index]
        "schedule_complete": True,
        "protocol_issues": [],
        "tasks": [
            {
                "task_id": task_id,
                "ecosystem": ecosystem,
                "executor_status": "valid",
                "executor_claim_agreement": True,
                "capture_state": "observable_chain_complete",
                "evidence_packet_sha256": "3" * 64,
                "truth_sha256": "5" * 64,
                "artifact_sha256": "2" * 64,
                "reporters": [
                    {
                        "condition_id": condition,
                        "status": "valid",
                        "claim_agreement": True,
                        "workspace_unchanged": True,
                        "evidence_hash_match": True,
                        "artifact_or_evaluator_exposed": False,
                        "tool_event_count": 1,
                    }
                    for condition in ("B0", "T1")
                ],
            }
            for task_id, ecosystem in (
                ("CI2-PY-01", "python"),
                ("CI2-TS-01", "typescript"),
            )
        ],
    }


class CompletionIntegrityActivationMaterializerTests(unittest.TestCase):
    def test_materialized_contract_graph_resolves_every_local_reference(self) -> None:
        for study_root in (V1_ROOT, V2_ROOT):
            with self.subTest(study=study_root.name):
                self._assert_materialized_graph(study_root)

    def _assert_materialized_graph(self, study_root: Path) -> None:
        freeze = load_json(study_root / "freeze.json")
        preregistration_sha = "b" * 40
        temporary_parent = Path("/private/tmp") if Path("/private/tmp").is_dir() else None
        with tempfile.TemporaryDirectory(
            prefix="ael-ci11-materializer-", dir=temporary_parent
        ) as raw:
            temporary = Path(raw)
            raw_root = temporary / "raw"
            (raw_root / "cells").mkdir(parents=True)
            observations = _observations(
                freeze,
                preregistration_sha,
                study_root=study_root,
            )
            write_json_atomic(raw_root / "observations.json", observations)
            write_json_atomic(
                raw_root / "decision.json",
                decide_activation(
                    observations,
                    decision_id=decision_id_from_study_id(str(freeze["study_id"])),
                ),
            )
            for entry in freeze["schedule"]:
                write_json_atomic(
                    raw_root / "cells" / f"{entry['cell_id']}.json",  # type: ignore[index]
                    _cell(entry),  # type: ignore[arg-type]
                )

            repository = temporary / "repository"
            activation_root = repository / "studies" / "completion-integrity" / study_root.name
            activation_root.parent.mkdir(parents=True)
            (repository / "pyproject.toml").write_text(
                "[project]\nname='fixture'\n", encoding="utf-8"
            )
            shutil.copyfile(
                STUDIES_ROOT / "concept.json",
                repository / "studies" / "completion-integrity" / "concept.json",
            )
            shutil.copytree(study_root, activation_root)
            result_root = activation_root / "results"
            if result_root.exists():
                shutil.rmtree(result_root)
            completed = subprocess.run(
                [
                    "uv",
                    "run",
                    "python",
                    "tools/materialize_completion_integrity_activation.py",
                    "--freeze",
                    str(study_root / "freeze.json"),
                    "--raw-root",
                    str(raw_root),
                    "--result-root",
                    str(result_root),
                    "--preregistration-sha",
                    preregistration_sha,
                    "--generated-at",
                    "2026-08-15T00:00:00Z",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)

            documents, issues = validate(
                [
                    repository / "studies" / "completion-integrity" / "concept.json",
                    activation_root / "study-manifest.json",
                    *(result_root / "runs").glob("*.json"),
                    result_root / "measurement-set.json",
                    result_root / "evidence-receipt.json",
                ]
            )
            self.assertEqual([], issues)
            self.assertEqual(10, len(documents))

            receipt = load_json(result_root / "evidence-receipt.json")
            revision = int(freeze["study_revision"])
            expected_claim = "AEL-CI11-01" if revision == 1 else f"AEL-CI11-R{revision}-01"
            self.assertEqual(expected_claim, receipt["evaluated_claims"][0]["claim_id"])
            measurement = load_json(result_root / "measurement-set.json")
            prefix = "ci11" if revision == 1 else f"ci11-r{revision}"
            self.assertIn(
                f"{prefix}:observable_chain_complete",
                {row["measurement_id"] for row in measurement["measurements"]},
            )

    def test_protocol_invalid_receipt_does_not_treat_unrun_as_disagreement(self) -> None:
        receipt = load_json(V1_ROOT / "results" / "evidence-receipt.json")
        statement = receipt["evaluated_claims"][1]["statement"]
        self.assertIn("0 observed agreements across 0 valid calls", statement)
        self.assertNotIn("0/2", statement)


if __name__ == "__main__":
    unittest.main()
