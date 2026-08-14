"""Fail-closed public audit for the Completion Integrity prompt-policy study."""

from __future__ import annotations

import datetime as dt
import re
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ael.completion_integrity import (
    FREEZE_SCHEMA_VERSION,
    decide_effect,
    text_sha256,
    validate_digest,
)
from ael.prospective_study import load_json_object, sha256_path
from ael.sandbox import SandboxError, tree_sha256
from ael.validation import validate

AUDIT_SCHEMA_VERSION = "ael.completion-integrity-audit/0.1-pilot"
AUDIT_PATH = Path(__file__).resolve()
_GIT_SHA = re.compile(r"^[a-f0-9]{40}$")
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
    raise SandboxError(f"completion-integrity audit failed: {message}")


def _utc_timestamp(value: object, label: str) -> dt.datetime:
    if not isinstance(value, str):
        _fail(f"{label} must be an RFC 3339 UTC timestamp")
    try:
        parsed = dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        _fail(f"{label} must be an RFC 3339 UTC timestamp")
    return parsed.replace(tzinfo=dt.UTC)


def _git(root: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(["git", *arguments], cwd=root, check=False, capture_output=True)
    if check and result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        _fail(f"git {' '.join(arguments)} failed: {detail}")
    return result


def _repository_root(freeze_path: Path, explicit: Path | None) -> Path:
    if explicit is not None:
        root = explicit.resolve()
    else:
        for candidate in (freeze_path.parent, *freeze_path.parents):
            if (candidate / "pyproject.toml").is_file():
                root = candidate.resolve()
                break
        else:
            _fail("could not locate repository root")
    if not (root / "pyproject.toml").is_file():
        _fail("repository root lacks pyproject.toml")
    if not freeze_path.resolve().is_relative_to(root):
        _fail("freeze is outside the repository")
    return root


def _repo_ref(reference: object, root: Path, label: str) -> Path:
    if not isinstance(reference, Mapping):
        _fail(f"{label} must be an object")
    uri = reference.get("uri")
    digest = reference.get("sha256")
    if not isinstance(uri, str) or not uri or uri.startswith("/") or "\\" in uri:
        _fail(f"{label} has an unsafe repository URI")
    try:
        validate_digest(digest, f"{label}.sha256")
    except ValueError as exc:
        _fail(str(exc))
    path = (root / uri).resolve()
    if not path.is_relative_to(root) or path.is_symlink() or not path.is_file():
        _fail(f"{label} is missing, unsafe, or outside the repository")
    if sha256_path(path) != digest:
        _fail(f"{label} hash mismatch")
    return path


def _repo_prompt_ref(reference: object, root: Path, label: str) -> Path:
    if not isinstance(reference, Mapping):
        _fail(f"{label} must be an object")
    uri = reference.get("uri")
    digest = reference.get("sha256")
    if not isinstance(uri, str) or not uri or uri.startswith("/") or "\\" in uri:
        _fail(f"{label} has an unsafe repository URI")
    try:
        validate_digest(digest, f"{label}.sha256")
    except ValueError as exc:
        _fail(str(exc))
    path = (root / uri).resolve()
    if not path.is_relative_to(root) or path.is_symlink() or not path.is_file():
        _fail(f"{label} is missing, unsafe, or outside the repository")
    try:
        value = path.read_text(encoding="utf-8").rstrip("\n")
    except (OSError, UnicodeError) as exc:
        _fail(f"{label} is unreadable: {exc}")
    if text_sha256(value) != digest:
        _fail(f"{label} normalized text hash mismatch")
    return path


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


def _verify_freeze(freeze_path: Path, freeze: Mapping[str, Any], root: Path) -> dict[str, Path]:
    if freeze.get("schema_version") != FREEZE_SCHEMA_VERSION:
        _fail("freeze has an unsupported schema version")
    if freeze.get("freeze_revision") != 3:
        _fail("freeze is not the post-architecture-audit revision")
    if freeze.get("scored_calls_executed") != 0:
        _fail("freeze does not declare zero scored calls")
    schedule = freeze.get("schedule")
    if (
        not isinstance(schedule, list)
        or len(schedule) != 52
        or len({row.get("cell_id") for row in schedule if isinstance(row, Mapping)}) != 52
    ):
        _fail("freeze does not contain 52 unique scheduled cells")
    if freeze.get("budget", {}).get("max_scored_calls") != 52:
        _fail("freeze call budget differs from the schedule")
    if freeze.get("budget", {}).get("outcome_retries") != 0:
        _fail("freeze permits outcome retries")
    if freeze.get("execution_policy", {}).get("submitted_or_ambiguous_retry") != "forbidden":
        _fail("freeze does not forbid submitted or ambiguous retries")

    code_paths = {
        "policy": root / "src" / "ael" / "completion_integrity.py",
        "runner": root / "tools" / "run_completion_integrity.py",
        "support": root / "tools" / "completion_integrity_support.py",
        "codex_runner": root / "src" / "ael" / "codex_runner.py",
        "sandbox": root / "src" / "ael" / "sandbox.py",
        "prospective_study": root / "src" / "ael" / "prospective_study.py",
        "materializer": root / "tools" / "materialize_completion_integrity.py",
        "audit": AUDIT_PATH,
        "validation": root / "src" / "ael" / "validation.py",
    }
    expected_code_keys = {*code_paths, "contract_schemas"}
    if set(freeze.get("code_hashes", {})) != expected_code_keys:
        _fail("freeze code-hash set is incomplete or unknown")
    for key, path in code_paths.items():
        if path.is_symlink() or not path.is_file():
            _fail(f"freeze-bound code is missing or unsafe: {key}")
        if freeze["code_hashes"][key] != sha256_path(path):
            _fail(f"freeze-bound code hash drifted: {key}")
    if freeze["code_hashes"]["contract_schemas"] != tree_sha256(root / "src" / "ael" / "schemas"):
        _fail("freeze-bound Contract schema tree drifted")

    refs = freeze.get("refs")
    required_refs = {
        "study_manifest",
        "quality_profile",
        "preflight",
        "gate",
        "headroom",
        "admission",
    }
    if not isinstance(refs, Mapping) or set(refs) != required_refs:
        _fail("freeze reference set is incomplete or unknown")
    paths = {key: _repo_ref(refs[key], root, f"freeze.refs.{key}") for key in required_refs}
    prompt_paths = {
        key: _repo_prompt_ref(freeze["prompts"][key], root, f"freeze.prompts.{key}")
        for key in ("common", "policy")
    }

    manifest = load_json_object(paths["study_manifest"])
    if (
        manifest.get("study_id") != freeze.get("study_id")
        or manifest.get("revision") != freeze.get("study_revision")
        or manifest.get("status") != "frozen"
    ):
        _fail("study manifest identity or state differs from the freeze")
    profile = load_json_object(paths["quality_profile"])
    if profile.get("study_ref", {}).get("sha256") != sha256_path(paths["study_manifest"]):
        _fail("quality profile does not bind the study manifest")
    preflight = load_json_object(paths["preflight"])
    if (
        preflight.get("status") not in {"conformant", "conformant_with_warnings"}
        or preflight.get("profile_sha256") != sha256_path(paths["quality_profile"])
        or preflight.get("study", {}).get("manifest_sha256") != sha256_path(paths["study_manifest"])
    ):
        _fail("Study Quality preflight is not conformant")
    gate = load_json_object(paths["gate"])
    headroom = load_json_object(paths["headroom"])
    admission = load_json_object(paths["admission"])
    pack_sha = freeze.get("private_pack", {}).get("sha256")
    if (
        gate.get("status") != "pass"
        or gate.get("private_pack_ref", {}).get("sha256") != pack_sha
        or gate.get("task_count") != 8
    ):
        _fail("no-call discrimination gate does not bind the frozen task pack")
    if (
        headroom.get("status") != "pass"
        or headroom.get("private_pack_sha256") != pack_sha
        or int(headroom.get("false_completion_count", 0)) < 1
        or any(
            headroom.get("runtime", {}).get(key) != freeze.get("runtime", {}).get(key)
            for key in ("harness", "harness_version", "model", "reasoning_effort")
        )
    ):
        _fail("baseline headroom does not bind the frozen task pack")
    admission_refs = {
        "study_manifest_ref": "study_manifest",
        "quality_profile_ref": "quality_profile",
        "preflight_ref": "preflight",
        "gate_ref": "gate",
        "headroom_ref": "headroom",
    }
    expected_actions = {
        "enable_default": "record_exact_policy_as_default_for_admitted_internal_scope",
        "route_selectively": "record_exact_policy_for_named_eligible_mechanisms_only",
        "reject_exact_policy": "record_exact_policy_rejection",
        "retest_design": "record_no_adoption_and_require_new_revision",
    }
    action_rows = admission.get("owner_action_policy", {}).get("rules", [])
    action_map = {
        row.get("effect_disposition"): row.get("owner_action")
        for row in action_rows
        if isinstance(row, Mapping)
    }
    if (
        admission.get("schema_version") != "ael.completion-integrity-admission/0.1-pilot"
        or admission.get("status") != "admitted"
        or admission.get("scored_calls_executed") != 0
        or admission.get("max_scored_calls") != 52
        or admission.get("outcome_retries") != 0
        or admission.get("private_pack", {}).get("sha256") != pack_sha
        or admission.get("private_pack", {}).get("revision")
        != freeze.get("private_pack", {}).get("revision")
        or any(
            admission.get(admission_key, {}).get("sha256") != sha256_path(paths[path_key])
            for admission_key, path_key in admission_refs.items()
        )
        or admission.get("candidate", {}).get("baseline_prompt_ref", {}).get("sha256")
        != sha256_path(prompt_paths["common"])
        or admission.get("candidate", {}).get("policy_prompt_ref", {}).get("sha256")
        != sha256_path(prompt_paths["policy"])
        or any(
            admission.get("runtime", {}).get(key) != freeze.get("runtime", {}).get(key)
            for key in ("harness", "harness_version", "model", "reasoning_effort")
        )
        or action_map != expected_actions
    ):
        _fail("owner admission is malformed or does not bind pre-run evidence")
    frozen_at = _utc_timestamp(freeze.get("frozen_at"), "freeze.frozen_at")
    admitted_at = _utc_timestamp(admission.get("admitted_at"), "admission.admitted_at")
    expires_at = _utc_timestamp(admission.get("expires_at"), "admission.expires_at")
    if frozen_at < admitted_at or frozen_at > expires_at:
        _fail("freeze timestamp falls outside the owner-admission window")
    return paths


def _measurement_map(
    measurement_set: Mapping[str, Any], run_ids: set[str]
) -> dict[tuple[str, str], object]:
    selected: dict[tuple[str, str], object] = {}
    for measurement in measurement_set.get("measurements", []):
        if not isinstance(measurement, Mapping):
            _fail("measurement set contains a non-object")
        metric = measurement.get("metric")
        ids = measurement.get("run_ids")
        if metric == "false_completion_risk_reduction":
            continue
        if not isinstance(metric, str) or not isinstance(ids, list) or len(ids) != 1:
            continue
        run_id = ids[0]
        if run_id not in run_ids:
            _fail("measurement references an unknown public run")
        key = (str(run_id), metric)
        if key in selected:
            _fail(f"duplicate public measurement: {run_id}/{metric}")
        selected[key] = measurement.get("value")
    return selected


def _reconstruct_observations(
    freeze: Mapping[str, Any], runs: list[Mapping[str, Any]], measurement_set: Mapping[str, Any]
) -> dict[str, Any]:
    by_id = {str(run.get("run_id")): run for run in runs}
    if len(by_id) != len(runs):
        _fail("duplicate public run ID")
    measurements = _measurement_map(measurement_set, set(by_id))
    marker_for_state = {
        "claimed_complete": ["complete"],
        "claimed_incomplete": ["incomplete"],
        "claimed_blocked": ["blocked"],
        "indeterminate": [],
    }
    observations: list[dict[str, Any]] = []
    for entry in freeze["schedule"]:
        run_id = f"kizz:ael:run:completion-integrity:{entry['cell_id']}"
        run = by_id.get(run_id)
        if run is None:
            _fail(f"missing public run for {entry['cell_id']}")
        expected_status = (
            "valid"
            if run.get("status") == "valid"
            else "operational_invalid"
            if run.get("status") == "invalid"
            else "missing"
        )
        declaration = measurements.get((run_id, "declaration_state"))
        if expected_status == "valid" and declaration not in marker_for_state:
            _fail(f"run {run_id} lacks a valid declaration-state measurement")
        accepted = measurements.get((run_id, "accepted_final_state"))
        regression = measurements.get((run_id, "regression"))
        critical = measurements.get((run_id, "critical_failure"))
        if expected_status == "valid" and not all(
            isinstance(value, bool) for value in (accepted, regression, critical)
        ):
            _fail(f"run {run_id} lacks deterministic outcome measurements")
        observation: dict[str, Any] = {
            **entry,
            "status": expected_status,
            "declaration_markers": marker_for_state.get(str(declaration), []),
            "evaluator": (
                {
                    "operational_valid": True,
                    "accepted": accepted,
                    "regression": regression,
                    "critical_failure": critical,
                    "omitted_requirement_ids": [],
                }
                if expected_status == "valid"
                else None
            ),
        }
        observations.append(observation)
    return {
        "schema_version": "ael.completion-integrity-observations/0.1-pilot",
        "observations": observations,
    }


def _verify_result(
    freeze_path: Path,
    freeze: Mapping[str, Any],
    result_root: Path,
    paths: Mapping[str, Path],
    root: Path,
) -> dict[str, Any]:
    required = {
        "measurement-set.json",
        "evidence-receipt.json",
        "effect-decision.json",
        "adoption-decision.pilot.json",
        "freeze-ref.json",
    }
    actual_root_files = {path.name for path in result_root.iterdir() if path.is_file()}
    if not required.issubset(actual_root_files):
        _fail(f"public result lacks required files: {sorted(required - actual_root_files)}")
    run_paths = sorted((result_root / "runs").glob("*.json"))
    if len(run_paths) != 52:
        _fail("public run count differs from the 52-cell freeze")
    manifest_path = paths["study_manifest"]
    manifest = load_json_object(manifest_path)
    concept_path = (manifest_path.parent / str(manifest["concept_ref"]["uri"])).resolve()
    measurement_path = result_root / "measurement-set.json"
    receipt_path = result_root / "evidence-receipt.json"
    documents, issues = validate(
        [concept_path, manifest_path, *run_paths, measurement_path, receipt_path]
    )
    if issues:
        _fail(f"Contract v0 graph is invalid: {issues[0]}")
    if len(documents) != 56:
        _fail("Contract v0 graph has an unexpected document count")
    runs = [load_json_object(path) for path in run_paths]
    measurement_set = load_json_object(measurement_path)
    reconstructed = _reconstruct_observations(freeze, runs, measurement_set)
    recomputed = decide_effect(freeze, reconstructed)
    effect_path = result_root / "effect-decision.json"
    recorded_effect = load_json_object(effect_path)
    if {key: recorded_effect.get(key) for key in recomputed} != recomputed:
        _fail("public effect decision differs from independent recomputation")
    aggregate = [
        row
        for row in measurement_set["measurements"]
        if row.get("measurement_id") == "false_completion_risk_reduction:core"
    ]
    expected_reduction = (
        recomputed.get("primary", {}).get("reduction") if recomputed.get("primary") else None
    )
    if len(aggregate) != 1 or aggregate[0].get("value") != expected_reduction:
        _fail("aggregate public effect measurement differs from recomputation")

    receipt = load_json_object(receipt_path)
    adoption_path = result_root / "adoption-decision.pilot.json"
    adoption = load_json_object(adoption_path)
    disposition_map = {
        "enable_default": "adopt",
        "route_selectively": "narrow",
        "reject_exact_policy": "reject",
        "retest_design": "inconclusive",
    }
    if receipt.get("decision", {}).get("disposition") != disposition_map[recomputed["disposition"]]:
        _fail("receipt disposition differs from the frozen study disposition")
    if (
        adoption.get("study_disposition") != recomputed["disposition"]
        or adoption.get("public_disposition") != disposition_map[recomputed["disposition"]]
        or adoption.get("effect_ref", {}).get("sha256") != sha256_path(effect_path)
        or adoption.get("evidence_receipt_ref", {}).get("sha256") != sha256_path(receipt_path)
    ):
        _fail("adoption decision differs from the effect or receipt")
    bindings = load_json_object(result_root / "freeze-ref.json")
    expected_bindings = {
        "freeze_sha256": sha256_path(freeze_path),
        "effect_decision_sha256": sha256_path(effect_path),
        "measurement_set_sha256": sha256_path(measurement_path),
        "evidence_receipt_sha256": sha256_path(receipt_path),
        "adoption_decision_sha256": sha256_path(adoption_path),
    }
    for key, value in expected_bindings.items():
        if bindings.get(key) != value:
            _fail(f"result binding mismatch: {key}")
    return {
        "effect_result": recomputed["effect_result"],
        "disposition": recomputed["disposition"],
        "eligible_mechanisms": recomputed["eligible_mechanisms"],
        "run_count": len(run_paths),
        "measurement_count": len(measurement_set["measurements"]),
        "preregistration_sha": bindings.get("preregistration_sha"),
    }


def _verify_git(
    root: Path,
    preregistration_sha: object,
    freeze_path: Path,
    paths: Mapping[str, Path],
    freeze: Mapping[str, Any],
    result_root: Path,
) -> dict[str, Any]:
    if not isinstance(preregistration_sha, str) or _GIT_SHA.fullmatch(preregistration_sha) is None:
        _fail("preregistration SHA is malformed")
    _git(root, "cat-file", "-e", f"{preregistration_sha}^{{commit}}")
    if _git(
        root, "merge-base", "--is-ancestor", preregistration_sha, "HEAD", check=False
    ).returncode:
        _fail("preregistration commit is not an ancestor of HEAD")
    prereg_paths = [freeze_path, *paths.values()]
    for key in ("common", "policy"):
        prereg_paths.append(_repo_prompt_ref(freeze["prompts"][key], root, f"freeze.prompts.{key}"))
    for path in prereg_paths:
        relative = path.resolve().relative_to(root).as_posix()
        historical = _git(root, "show", f"{preregistration_sha}:{relative}")
        if historical.stdout != path.read_bytes():
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
        "boundary": "Git proves repository artifact ordering, not private hosted-call chronology.",
    }


def audit_completion_integrity_bundle(
    freeze_path: Path,
    result_root: Path,
    *,
    git_root: Path | None = None,
    require_git_proof: bool = False,
) -> dict[str, Any]:
    freeze_path = freeze_path.resolve()
    root = _repository_root(freeze_path, git_root)
    result_root = result_root.resolve()
    if not result_root.is_relative_to(root) or result_root.is_symlink() or not result_root.is_dir():
        _fail("result root is missing, unsafe, or outside the repository")
    _verify_public_boundary(result_root)
    freeze = load_json_object(freeze_path)
    paths = _verify_freeze(freeze_path, freeze, root)
    result = _verify_result(freeze_path, freeze, result_root, paths, root)
    preregistration = {
        "git_verified": False,
        "preregistration_sha": result["preregistration_sha"],
        "boundary": "Git proof was not required for this audit invocation.",
    }
    if require_git_proof:
        preregistration = _verify_git(
            root,
            result["preregistration_sha"],
            freeze_path,
            paths,
            freeze,
            result_root,
        )
    return {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "study": {
            "study_id": freeze["study_id"],
            "revision": freeze["study_revision"],
            "private_pack_revision": freeze["private_pack"]["revision"],
        },
        "result": result,
        "quality": {
            "gate": "pass",
            "headroom": "pass",
            "preflight": load_json_object(paths["preflight"])["status"],
            "independence": "maintainer_evaluated",
        },
        "preregistration": preregistration,
    }
