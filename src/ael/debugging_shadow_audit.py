"""Fail-closed public audit for the systematic-debugging real-shadow pilot."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ael.prospective_study import (
    load_json_object,
    sha256_path,
    validate_admission,
    validate_freeze,
)
from ael.sandbox import SandboxError
from ael.systematic_debugging_shadow import match_owner_policy, paired_counts
from ael.validation import validate

AUDIT_SCHEMA_VERSION = "ael.debugging-shadow-audit/0.1-pilot"
REPAIR_SCHEMA_VERSION = "ael.projection-deviation/0.1-pilot"
REPAIR_TOOL = "tools/repair_systematic_debugging_shadow_projection.py"
_SHA = re.compile(r"^[a-f0-9]{40}$")
_FORBIDDEN_PUBLIC_MARKERS = (
    "/" + "Users" + "/",
    "/" + "home" + "/",
    "\\" + "Users" + "\\",
    ".codex" + "-work1",
    "AEL-HIDDEN-" + "CANARY:",
    "BEGIN OPENSSH PRIVATE KEY",
    "BEGIN RSA PRIVATE KEY",
)


def _fail(message: str) -> None:
    raise SandboxError(f"debugging-shadow audit failed: {message}")


def _git(root: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=False,
        capture_output=True,
    )
    if check and result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        _fail(f"git {' '.join(arguments)} failed: {detail}")
    return result


def _resolved_ref(owner: Path, reference: Mapping[str, Any], root: Path, label: str) -> Path:
    uri = reference.get("uri")
    digest = reference.get("sha256")
    if not isinstance(uri, str) or not uri or uri.startswith("/") or "\\" in uri:
        _fail(f"{label} has an unsafe URI")
    candidate = owner.parent / uri
    if candidate.is_symlink():
        _fail(f"{label} must not use a symlink")
    path = candidate.resolve()
    if not path.is_relative_to(root) or not path.is_file():
        _fail(f"{label} escapes the repository or is missing")
    if digest != sha256_path(path):
        _fail(f"{label} hash mismatch")
    return path


def _public_effect(
    freeze: Mapping[str, Any], runs: list[Mapping[str, Any]], measurement_set: Mapping[str, Any]
) -> dict[str, Any]:
    statuses: dict[tuple[str, str], str] = {}
    for run in runs:
        task = run.get("task")
        if not isinstance(task, Mapping):
            _fail("run is missing task identity")
        key = (str(task.get("task_id")), str(run.get("condition_id")))
        if key in statuses:
            _fail("duplicate public run cell")
        statuses[key] = str(run.get("status"))

    selected: dict[tuple[str, str], dict[str, Any]] = {
        key: {
            "task_id": key[0],
            "condition_id": key[1],
            "repeat_index": 1,
            "status": status,
            "stratum": freeze["private_pack"]["strata"].get(key[0]),
        }
        for key, status in statuses.items()
    }
    required_metrics = {"accepted", "critical_failure", "skill_activated"}
    seen: set[tuple[str, str, str]] = set()
    for measurement in measurement_set.get("measurements", []):
        if not isinstance(measurement, Mapping):
            _fail("measurement set contains a non-object")
        metric = measurement.get("metric")
        if metric not in required_metrics:
            continue
        key = (str(measurement.get("task_id")), str(measurement.get("condition_id")))
        target = selected.get(key)
        if target is None:
            _fail("measurement references an unknown public run cell")
        identity = (key[0], key[1], str(metric))
        if identity in seen:
            _fail("duplicate public decision measurement")
        seen.add(identity)
        value = measurement.get("value")
        if not isinstance(value, bool):
            _fail("public decision measurement must be boolean")
        target[str(metric)] = value
    expected_metrics = {
        (task, condition, metric)
        for task in freeze["private_pack"]["task_ids"]
        for condition in ("B0", "S1")
        for metric in required_metrics
    }
    if seen != expected_metrics:
        _fail("public measurements do not cover every frozen decision cell")

    observations = [selected[key] for key in sorted(selected)]
    counts, classifications, favorable_by_stratum = paired_counts(
        observations, freeze["private_pack"]["strata"]
    )
    rule = freeze["decision_rule"]
    eligible = sorted(
        stratum
        for stratum, count in favorable_by_stratum.items()
        if count >= rule["route_requires_favorable_tasks_per_stratum"]
    )
    if counts["invalid_observations"]:
        outcome = "invalid_manual_review"
        eligible = []
    elif counts["activation_failures"]:
        outcome = "treatment_activation_failure"
        eligible = []
    elif counts["treatment_critical_failures"]:
        outcome = "treatment_critical_failure"
        eligible = []
    elif counts["unfavorable_pairs"] >= rule["reject_at_unfavorable_pairs"]:
        outcome = "treatment_harm_signal"
        eligible = []
    elif eligible and counts["unfavorable_pairs"] <= rule["maximum_unfavorable_for_route"]:
        outcome = "bounded_favorable_signal"
    else:
        outcome = "mixed_or_no_headroom"
        eligible = []
    return {
        "counts": counts,
        "pair_classifications": classifications,
        "favorable_by_stratum": favorable_by_stratum,
        "eligible_strata": eligible,
        "effect_outcome": outcome,
    }


def _verify_projection_repair(
    result_root: Path, freeze: Mapping[str, Any], repository_root: Path
) -> dict[str, Any]:
    deviation = load_json_object(result_root / "projection-deviation.pilot.json")
    if deviation.get("schema_version") != REPAIR_SCHEMA_VERSION:
        _fail("projection deviation has the wrong schema version")
    allowed = deviation.get("allowed_change")
    if allowed != {
        "path": "evidence-receipt.json.reproducibility",
        "before": "partially_rerunnable",
        "after": "rerunnable",
    }:
        _fail("projection deviation exceeds the admitted one-field repair")
    if deviation.get("frozen_materializer_sha256") != freeze["code_hashes"]["materializer"]:
        _fail("projection deviation does not bind the frozen materializer")
    repair_tool = repository_root / REPAIR_TOOL
    if repair_tool.is_symlink() or not repair_tool.is_file():
        _fail("projection repair tool is missing or unsafe in the repository")
    if deviation.get("repair_tool_sha256") != sha256_path(repair_tool):
        _fail("projection repair tool hash mismatch")
    receipt_path = result_root / "evidence-receipt.json"
    receipt = load_json_object(receipt_path)
    if receipt.get("reproducibility") != "rerunnable":
        _fail("repaired receipt does not use the Contract v0 reproducibility enum")
    limitations = receipt.get("limitations")
    if not isinstance(limitations, list) or not limitations:
        _fail("repaired receipt lacks the projection-repair disclosure")
    disclosure = limitations[-1]
    if not isinstance(disclosure, str) or "post-run projection repair" not in disclosure:
        _fail("repaired receipt does not disclose the post-run repair")

    reconstructed = dict(receipt)
    reconstructed["reproducibility"] = "partially_rerunnable"
    reconstructed["limitations"] = limitations[:-1]
    original_bytes = (
        json.dumps(reconstructed, indent=2, sort_keys=False, allow_nan=False) + "\n"
    ).encode("utf-8")
    original_sha = hashlib.sha256(original_bytes).hexdigest()
    if original_sha != deviation.get("original_receipt_sha256"):
        _fail("original invalid receipt cannot be reconstructed from the repair record")
    if deviation.get("repaired_receipt_sha256") != sha256_path(receipt_path):
        _fail("projection deviation repaired receipt hash mismatch")
    return deviation


def _verify_lifecycle(
    result_root: Path,
    admission: Mapping[str, Any],
    effect: Mapping[str, Any],
) -> dict[str, str]:
    receipt_path = result_root / "evidence-receipt.json"
    adoption_path = result_root / "adoption-decision.pilot.json"
    adoption = load_json_object(adoption_path)
    routing_path = result_root / "routing-policy.pilot.json"
    routing = load_json_object(routing_path)
    action_path = result_root / "action-record.pilot.json"
    action = load_json_object(action_path)
    follow_up_path = result_root / "outcome-follow-up.pilot.json"
    follow_up = load_json_object(follow_up_path)
    freeze_ref = load_json_object(result_root / "freeze-ref.json")

    expected_rule, resolution = match_owner_policy(admission, effect)
    if expected_rule is None or resolution != "applied_policy":
        _fail("effect outcome did not resolve to an admitted owner action")
    if adoption.get("matched_rule_id") != expected_rule["rule_id"]:
        _fail("adoption decision did not apply the matched frozen owner rule")
    if adoption.get("disposition") != expected_rule["disposition"]:
        _fail("adoption disposition differs from the frozen owner rule")
    if adoption.get("evidence_receipt_ref", {}).get("sha256") != sha256_path(receipt_path):
        _fail("adoption decision receipt hash mismatch")
    adoption_sha = sha256_path(adoption_path)
    if routing.get("adoption_decision_ref", {}).get("sha256") != adoption_sha:
        _fail("routing policy adoption hash mismatch")
    if routing.get("mode") != adoption.get("disposition") or routing.get("global_installation"):
        _fail("routing policy exceeds the owner adoption decision")
    if action.get("adoption_decision_ref", {}).get("sha256") != adoption_sha:
        _fail("action record adoption hash mismatch")
    if action.get("owner_system_ref", {}).get("sha256") != sha256_path(routing_path):
        _fail("action record routing-policy hash mismatch")
    if action.get("action_kind") != expected_rule["action_kind"]:
        _fail("action record kind differs from the frozen owner rule")
    if action.get("state") != "verified":
        _fail("owner action is not verified")
    if follow_up.get("action_ref", {}).get("sha256") != sha256_path(action_path):
        _fail("follow-up action hash mismatch")
    if follow_up.get("status") != "scheduled" or follow_up.get("conclusion") != "not_due":
        _fail("follow-up record overclaims an observed downstream outcome")

    expected_hashes = {
        "receipt_sha256": sha256_path(receipt_path),
        "adoption_decision_sha256": adoption_sha,
        "action_record_sha256": sha256_path(action_path),
        "projection_deviation_sha256": sha256_path(result_root / "projection-deviation.pilot.json"),
    }
    for key, expected in expected_hashes.items():
        if freeze_ref.get(key) != expected:
            _fail(f"freeze-ref {key} mismatch")
    return {
        "admission": str(admission.get("status")),
        "adoption": str(adoption.get("disposition")),
        "action": str(action.get("state")),
        "follow_up": str(follow_up.get("status")),
    }


def _verify_public_boundary(result_root: Path) -> None:
    for path in sorted(result_root.rglob("*")):
        if path.is_symlink() or (path.exists() and not path.is_file() and not path.is_dir()):
            _fail(f"public result contains an unsafe filesystem member: {path}")
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeError:
            _fail(f"public result contains a non-text artifact: {path}")
        for marker in _FORBIDDEN_PUBLIC_MARKERS:
            if marker in text:
                _fail(f"public result contains forbidden private marker {marker!r}: {path}")


def _verify_git(
    root: Path,
    preregistration_sha: str,
    freeze_path: Path,
    admission_path: Path,
    manifest_path: Path,
    source_lock_path: Path,
    result_root: Path,
) -> dict[str, Any]:
    if _SHA.fullmatch(preregistration_sha) is None:
        _fail("preregistration SHA is malformed")
    _git(root, "cat-file", "-e", f"{preregistration_sha}^{{commit}}")
    if _git(
        root, "merge-base", "--is-ancestor", preregistration_sha, "HEAD", check=False
    ).returncode:
        _fail("preregistration commit is not an ancestor of HEAD")
    for path in (freeze_path, admission_path, manifest_path, source_lock_path):
        relative = path.resolve().relative_to(root).as_posix()
        historical = _git(root, "show", f"{preregistration_sha}:{relative}").stdout
        if historical != path.read_bytes():
            _fail(f"current {relative} differs from preregistration bytes")
    result_relative = result_root.resolve().relative_to(root).as_posix()
    if (
        _git(
            root, "cat-file", "-e", f"{preregistration_sha}:{result_relative}", check=False
        ).returncode
        == 0
    ):
        _fail("public result existed in the preregistration commit")
    for path in sorted(result_root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.resolve().relative_to(root).as_posix()
        historical = _git(root, "show", f"HEAD:{relative}", check=False)
        if historical.returncode != 0 or historical.stdout != path.read_bytes():
            _fail(f"public result is not committed exactly at HEAD: {relative}")
    return {
        "git_verified": True,
        "preregistration_sha": preregistration_sha,
        "boundary": "Git proves repository artifact ordering, not private model-call time.",
    }


def audit_debugging_shadow_bundle(
    freeze_path: Path,
    result_root: Path,
    *,
    git_root: Path | None = None,
    require_git_proof: bool = False,
) -> dict[str, Any]:
    freeze_path = freeze_path.resolve()
    result_root = result_root.resolve()
    if git_root is not None:
        root = git_root.resolve()
    else:
        for candidate in (freeze_path.parent, *freeze_path.parents):
            if (candidate / "pyproject.toml").is_file():
                root = candidate.resolve()
                break
        else:
            _fail("could not locate repository root from the supplied freeze")
    if not result_root.is_relative_to(root) or result_root.is_symlink() or not result_root.is_dir():
        _fail("result root is missing, unsafe, or outside the repository")
    freeze = load_json_object(freeze_path)
    freeze_issues = validate_freeze(freeze)
    if freeze_issues:
        _fail(f"freeze has {len(freeze_issues)} issue(s): {freeze_issues[0]}")
    admission_path = _resolved_ref(freeze_path, freeze["admission_ref"], root, "admission_ref")
    manifest_path = _resolved_ref(
        freeze_path, freeze["study_manifest_ref"], root, "study_manifest_ref"
    )
    source_lock_path = _resolved_ref(
        freeze_path, freeze["source_lock_ref"], root, "source_lock_ref"
    )
    admission = load_json_object(admission_path)
    admission_issues = validate_admission(admission)
    if admission_issues:
        _fail(f"admission has {len(admission_issues)} issue(s): {admission_issues[0]}")

    receipt_path = result_root / "evidence-receipt.json"
    measurement_path = result_root / "measurement-set.json"
    run_paths = sorted((result_root / "runs").glob("*.json"))
    contract_paths = [
        root / "studies" / "agent-skills-season-1" / "concept.json",
        manifest_path,
        *run_paths,
        measurement_path,
        receipt_path,
    ]
    documents, issues = validate(contract_paths)
    if issues:
        _fail(f"Contract v0 graph is invalid: {issues[0]}")
    if len(run_paths) != len(freeze["schedule"]):
        _fail("public run count differs from the frozen schedule")
    runs = [load_json_object(path) for path in run_paths]
    measurement_set = load_json_object(measurement_path)
    public_effect = _public_effect(freeze, runs, measurement_set)
    effect_path = result_root / "effect-decision.json"
    effect = load_json_object(effect_path)
    for key in (
        "counts",
        "pair_classifications",
        "favorable_by_stratum",
        "eligible_strata",
        "effect_outcome",
    ):
        if effect.get(key) != public_effect[key]:
            _fail(f"public effect decision differs from reconstructed {key}")
    if effect.get("freeze_ref", {}).get("sha256") != sha256_path(freeze_path):
        _fail("effect decision freeze hash mismatch")
    freeze_ref = load_json_object(result_root / "freeze-ref.json")
    if freeze_ref.get("effect_decision_sha256") != sha256_path(effect_path):
        _fail("freeze-ref effect decision hash mismatch")
    source_refs = measurement_set.get("source_refs")
    if not isinstance(source_refs, list) or not any(
        ref.get("sha256") == effect.get("observations_sha256")
        for ref in source_refs
        if isinstance(ref, Mapping)
    ):
        _fail("measurement set does not bind the private observations hash")

    deviation = _verify_projection_repair(result_root, freeze, root)
    lifecycle = _verify_lifecycle(result_root, admission, effect)
    _verify_public_boundary(result_root)
    preregistration_sha = str(freeze_ref.get("preregistration_sha", ""))
    preregistration = {
        "git_verified": False,
        "preregistration_sha": preregistration_sha,
        "boundary": "Git proof was not required for this invocation.",
    }
    if require_git_proof:
        preregistration = _verify_git(
            root,
            preregistration_sha,
            freeze_path,
            admission_path,
            manifest_path,
            source_lock_path,
            result_root,
        )
    return {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "status": "passed",
        "study": {"study_id": freeze["study_id"], "revision": freeze["study_revision"]},
        "decision": {
            "stage": "terminal",
            "outcome": effect["effect_outcome"],
            "claim_ceiling": effect["claim_ceiling"],
        },
        "evidence": {
            "contract_documents": len(documents),
            "run_records": len(run_paths),
            "measurements": len(measurement_set["measurements"]),
            "public_recomputation": True,
            "private_observations_sha256": effect["observations_sha256"],
        },
        "lifecycle": lifecycle,
        "projection_deviation": {
            "status": "disclosed_and_verified",
            "deviation_id": deviation["deviation_id"],
            "decision_impact": deviation["decision_impact"],
        },
        "preregistration": preregistration,
    }
