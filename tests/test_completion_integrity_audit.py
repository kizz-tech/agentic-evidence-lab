from __future__ import annotations

import copy
import unittest

from ael.completion_integrity import decide_effect
from ael.completion_integrity_audit import _reconstruct_observations
from ael.sandbox import SandboxError
from tests.test_completion_integrity import freeze, observations


def public_projection(frozen, private_observations):
    runs = []
    measurements = []
    for row in private_observations["observations"]:
        run_id = f"kizz:ael:run:completion-integrity:{row['cell_id']}"
        runs.append({"run_id": run_id, "status": "valid"})
        derived = {
            "declaration_state": "claimed_complete",
            "accepted_final_state": row["evaluator"]["accepted"],
            "regression": row["evaluator"]["regression"],
            "critical_failure": row["evaluator"]["critical_failure"],
        }
        for metric, value in derived.items():
            measurements.append(
                {
                    "measurement_id": f"{metric}:{row['cell_id']}",
                    "metric": metric,
                    "value": value,
                    "run_ids": [run_id],
                }
            )
    return runs, {"measurements": measurements}


class CompletionIntegrityAuditTests(unittest.TestCase):
    def test_public_measurements_recompute_the_same_effect(self) -> None:
        frozen = freeze()
        private = observations(frozen)
        runs, measurement_set = public_projection(frozen, private)

        reconstructed = _reconstruct_observations(frozen, runs, measurement_set)

        self.assertEqual(decide_effect(frozen, private), decide_effect(frozen, reconstructed))

    def test_duplicate_public_decision_measurement_fails_closed(self) -> None:
        frozen = freeze()
        private = observations(frozen)
        runs, measurement_set = public_projection(frozen, private)
        measurement_set["measurements"].append(copy.deepcopy(measurement_set["measurements"][0]))

        with self.assertRaisesRegex(SandboxError, "duplicate public measurement"):
            _reconstruct_observations(frozen, runs, measurement_set)


if __name__ == "__main__":
    unittest.main()
