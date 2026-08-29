from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ael.contract_graph import validate
from ael.pbt_pilot import paired_counts
from ael.sandbox import SandboxError
from ael.study_freeze import (
    DECISION_SCHEMA_VERSION,
    validate_freeze_bundle,
    verify_private_pack,
)
from ael.validation import MAX_JSON_BYTES, sha256_path

AUDIT_SCHEMA_VERSION = "ael.study-audit/0.1"
_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_GIT_SHA = re.compile(r"^[a-f0-9]{40}$")
_STAGES = {"continuation", "selection", "confirmation"}
_DECISION_ADAPTERS = {"pbt-v2"}
_COUNT_KEYS = {
    "valid_observations",
    "invalid_observations",
    "complete_pairs",
    "favorable_pairs",
    "unfavorable_pairs",
    "tied_pairs",
    "baseline_hidden_failures",
    "treatment_hidden_failures",
    "activation_failures",
    "treatment_critical_failures",
}


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate object member: {key}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise ValueError(f"non-finite JSON number: {value}")


def _load_object(path: Path) -> dict[str, Any]:
    path = path.absolute()
    if not path.is_file() or path.is_symlink():
        raise SandboxError(f"study audit requires a regular, non-symlink file: {path}")
    path = path.resolve()
    if path.stat().st_size > MAX_JSON_BYTES:
        raise SandboxError(f"study audit JSON exceeds {MAX_JSON_BYTES} bytes: {path}")
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_strict_object,
            parse_constant=_reject_nonfinite,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise SandboxError(f"study audit JSON is unreadable: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SandboxError(f"study audit JSON must contain an object: {path}")
    return value


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SandboxError(f"study audit failed: {message}")


def _reference_path(owner: Path, reference: object, repository_root: Path) -> Path:
    _require(isinstance(reference, dict), f"reference in {owner.name} must be an object")
    uri = reference.get("uri")
    _require(isinstance(uri, str) and uri, f"reference in {owner.name} requires a URI")
    parsed = urlparse(uri)
    _require(not parsed.scheme and not uri.startswith("/"), "public audit reference must be local")
    candidate = owner.parent / parsed.path
    _require(not candidate.is_symlink(), f"reference from {owner.name} must not use a symlink")
    target = candidate.resolve()
    _require(
        target.is_relative_to(repository_root),
        f"reference from {owner.name} escapes the repository root",
    )
    _require(target.is_file(), f"reference from {owner.name} does not resolve to a file")
    expected = reference.get("sha256")
    _require(
        isinstance(expected, str) and _SHA256.fullmatch(expected) is not None,
        "reference hash is invalid",
    )
    _require(sha256_path(target) == expected, f"reference hash does not match {target.name}")
    return target


def _repository_root(path: Path) -> Path:
    for candidate in (path, *path.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate.resolve()
    raise SandboxError("study audit could not locate a repository root with pyproject.toml")


def _expected_cells(bundle: dict[str, Any], stage: str) -> set[tuple[str, str, int]]:
    phase = "confirmation" if stage == "confirmation" else "screening"
    entries = bundle["schedule"][phase]
    if stage == "continuation":
        repeat_limit = bundle["budget"]["initial_repeats"]
        entries = [entry for entry in entries if entry["repeat_index"] <= repeat_limit]
    return {(entry["task_id"], entry["condition_id"], entry["repeat_index"]) for entry in entries}


def _run_observations(
    run_paths: list[Path],
    measurement_set: dict[str, Any],
    bundle: dict[str, Any],
    stage: str,
    decision_adapter: str | None,
) -> tuple[list[dict[str, Any]], int]:
    metrics: dict[tuple[str, str], Any] = {}
    measurements = measurement_set.get("measurements")
    _require(isinstance(measurements, list), "measurement set has no measurements")
    for measurement in measurements:
        _require(isinstance(measurement, dict), "measurement entry must be an object")
        run_ids = measurement.get("run_ids")
        metric = measurement.get("metric")
        if metric not in {"hidden_acceptance", "skill_activated", "critical_failure"}:
            continue
        _require(
            isinstance(run_ids, list) and len(run_ids) == 1 and isinstance(run_ids[0], str),
            f"{metric} must refer to exactly one run",
        )
        key = (run_ids[0], metric)
        _require(key not in metrics, f"duplicate {metric} measurement for {run_ids[0]}")
        value = measurement.get("value")
        _require(isinstance(value, bool), f"{metric} must be boolean")
        metrics[key] = value

    observations: list[dict[str, Any]] = []
    observed_cells: set[tuple[str, str, int]] = set()
    run_ids: set[str] = set()
    phase = "confirmation" if stage == "confirmation" else "screening"
    for path in run_paths:
        run = _load_object(path)
        run_id = run.get("run_id")
        task = run.get("task")
        condition_id = run.get("condition_id")
        repeat_index = run.get("repeat_index")
        _require(isinstance(run_id, str) and run_id, f"{path.name} has no run ID")
        _require(run_id not in run_ids, f"duplicate run ID {run_id}")
        _require(isinstance(task, dict), f"{path.name} has no task object")
        task_id = task.get("task_id")
        _require(isinstance(task_id, str), f"{path.name} has no task ID")
        _require(task.get("role") == phase, f"{path.name} does not belong to the {phase} phase")
        _require(isinstance(condition_id, str), f"{path.name} has no condition ID")
        _require(
            isinstance(repeat_index, int) and not isinstance(repeat_index, bool),
            f"{path.name} has no repeat index",
        )
        cell = (task_id, condition_id, repeat_index)
        _require(cell not in observed_cells, f"duplicate scheduled cell {cell}")
        observation: dict[str, Any] = {
            "task_id": task_id,
            "condition_id": condition_id,
            "repeat_index": repeat_index,
            "status": run.get("status"),
        }
        if decision_adapter == "pbt-v2" and run.get("status") == "valid":
            for metric in ("hidden_acceptance", "skill_activated", "critical_failure"):
                _require((run_id, metric) in metrics, f"run {run_id} lacks {metric}")
                observation[metric] = metrics[(run_id, metric)]
        observations.append(observation)
        observed_cells.add(cell)
        run_ids.add(run_id)

    _require(
        observed_cells == _expected_cells(bundle, stage),
        "run records do not cover the terminal frozen schedule",
    )
    used_metric_keys = {
        (run_id, metric)
        for run_id in run_ids
        for metric in ("hidden_acceptance", "skill_activated", "critical_failure")
    }
    _require(
        not (set(metrics) - used_metric_keys),
        "decision metrics refer to a run outside the terminal schedule",
    )
    return observations, len(measurements)


def _pbt_outcome(counts: dict[str, int], rule: dict[str, Any], stage: str) -> str:
    if counts["invalid_observations"] != 0:
        return "stopped_integrity_failure"
    if counts["activation_failures"] != 0:
        return "stopped_activation_failure"
    if counts["baseline_hidden_failures"] == 0:
        return "stopped_baseline_ceiling"
    if counts["treatment_critical_failures"] != 0:
        return "not_confirmed" if stage == "confirmation" else "reject_all_critical_failure"
    threshold_met = (
        counts["favorable_pairs"] >= rule["minimum_favorable_pairs"]
        and counts["unfavorable_pairs"] <= rule["maximum_unfavorable_pairs"]
    )
    if threshold_met:
        return {
            "continuation": "continue",
            "selection": "select_S1",
            "confirmation": "confirmed_S1",
        }[stage]
    return "not_confirmed" if stage == "confirmation" else "reject_all"


def _validate_decision(
    decision: dict[str, Any],
    bundle: dict[str, Any],
    freeze_path: Path,
    decision_adapter: str | None,
) -> str:
    _require(
        decision.get("schema_version") == DECISION_SCHEMA_VERSION,
        "decision schema version is invalid",
    )
    stage = decision.get("stage")
    _require(stage in _STAGES, "decision stage is invalid")
    _require(
        decision.get("decision_id") == f"{bundle['freeze_id']}:{stage}",
        "decision ID is not freeze-bound",
    )
    _require(
        decision.get("study_id") == bundle["study_id"], "decision study ID differs from freeze"
    )
    _require(
        decision.get("study_revision") == bundle["study_revision"],
        "decision revision differs from freeze",
    )
    freeze_ref = decision.get("freeze_ref")
    _require(isinstance(freeze_ref, dict), "decision freeze reference is missing")
    _require(freeze_ref.get("freeze_id") == bundle["freeze_id"], "decision freeze ID differs")
    _require(freeze_ref.get("sha256") == sha256_path(freeze_path), "decision freeze hash differs")
    _require(decision.get("rule") == bundle[f"{stage}_rule"], "decision rule differs from freeze")
    _require(
        isinstance(decision.get("observations_sha256"), str)
        and _SHA256.fullmatch(decision["observations_sha256"]) is not None,
        "decision observations hash is invalid",
    )
    counts = decision.get("counts")
    _require(isinstance(counts, dict), "decision counts are missing")
    _require(
        all(
            isinstance(value, int) and not isinstance(value, bool) and value >= 0
            for value in counts.values()
        ),
        "decision counts must be non-negative integers",
    )
    _require(
        isinstance(decision.get("outcome"), str) and decision["outcome"],
        "decision outcome is missing",
    )
    _require(
        isinstance(decision.get("confirmation_unlocked"), bool),
        "confirmation unlock state must be boolean",
    )
    if decision_adapter == "pbt-v2":
        _require(
            set(counts) == _COUNT_KEYS,
            "PBT v2 decision counts do not use the complete expected key set",
        )
        expected_outcome = _pbt_outcome(counts, bundle[f"{stage}_rule"], str(stage))
        _require(
            decision["outcome"] == expected_outcome,
            "PBT v2 outcome does not follow public counts and the frozen rule",
        )
        expected_unlock = stage == "selection" and expected_outcome == "select_S1"
        _require(
            decision.get("confirmation_unlocked") is expected_unlock,
            "PBT v2 confirmation unlock state contradicts terminal decision",
        )
    return str(stage)


def _verify_git_preregistration(
    repository_root: Path, freeze_path: Path, result_root: Path, preregistration_sha: str
) -> dict[str, Any]:
    _require(
        _GIT_SHA.fullmatch(preregistration_sha) is not None,
        "preregistration SHA must be 40 lowercase hex",
    )
    try:
        freeze_relative = freeze_path.relative_to(repository_root).as_posix()
        decision_relative = (result_root / "decision.json").relative_to(repository_root).as_posix()
    except ValueError as exc:
        raise SandboxError("study audit paths are outside the Git root") from exc

    def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
        try:
            return subprocess.run(
                ["git", "-C", str(repository_root), *args],
                check=check,
                capture_output=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise SandboxError(f"Git preregistration proof failed: {' '.join(args)}") from exc

    git("cat-file", "-e", f"{preregistration_sha}^{{commit}}")
    git("merge-base", "--is-ancestor", preregistration_sha, "HEAD")
    current_head = git("rev-parse", "HEAD").stdout.decode("utf-8").strip()
    _require(current_head != preregistration_sha, "preregistration commit is still current HEAD")
    frozen_payload = git("show", f"{preregistration_sha}:{freeze_relative}").stdout
    _require(
        hashlib.sha256(frozen_payload).hexdigest() == sha256_path(freeze_path),
        "preregistration commit contains different freeze bytes",
    )
    result_at_freeze = git(
        "cat-file", "-e", f"{preregistration_sha}:{decision_relative}", check=False
    )
    _require(
        result_at_freeze.returncode != 0,
        "terminal decision already existed at preregistration commit",
    )
    committed_decision = git("show", f"HEAD:{decision_relative}").stdout
    _require(
        hashlib.sha256(committed_decision).hexdigest()
        == sha256_path(result_root / "decision.json"),
        "current HEAD does not contain the exact audited terminal decision",
    )
    tags = git("tag", "--points-at", preregistration_sha).stdout.decode("utf-8").splitlines()
    return {
        "sha": preregistration_sha,
        "git_verified": True,
        "freeze_bytes_verified": True,
        "terminal_decision_absent_at_freeze": True,
        "terminal_decision_committed_after_freeze": True,
        "tags": sorted(tag for tag in tags if tag),
    }


def audit_study_bundle(
    freeze_path: Path,
    result_root: Path,
    *,
    screening_root: Path | None = None,
    confirmation_root: Path | None = None,
    git_root: Path | None = None,
    require_git_proof: bool = False,
    decision_adapter: str | None = None,
) -> dict[str, Any]:
    _require(
        decision_adapter is None or decision_adapter in _DECISION_ADAPTERS,
        f"decision adapter must be one of {sorted(_DECISION_ADAPTERS)}",
    )
    freeze_path = freeze_path.absolute()
    result_root = result_root.absolute()
    _require(not freeze_path.is_symlink(), "freeze path must not be a symlink")
    _require(
        result_root.is_dir() and not result_root.is_symlink(),
        "result root must be a non-symlink directory",
    )
    freeze_path = freeze_path.resolve()
    result_root = result_root.resolve()
    repository_root = _repository_root(result_root)
    bundle = _load_object(freeze_path)
    freeze_issues = validate_freeze_bundle(bundle)
    if freeze_issues:
        raise SandboxError(
            f"study audit failed: freeze has {len(freeze_issues)} issue(s): {freeze_issues[0]}"
        )

    required_paths = {
        "decision": result_root / "decision.json",
        "freeze_ref": result_root / "freeze-ref.json",
        "receipt": result_root / "evidence-receipt.json",
        "measurements": result_root / "measurement-set.json",
    }
    for label, path in required_paths.items():
        _require(
            path.is_file() and not path.is_symlink(), f"required {label} file is missing or unsafe"
        )
    runs_root = result_root / "runs"
    _require(
        runs_root.is_dir() and not runs_root.is_symlink(), "runs directory is missing or unsafe"
    )
    run_paths = sorted(runs_root.glob("*.json"))
    _require(
        run_paths and all(path.is_file() and not path.is_symlink() for path in run_paths),
        "runs must contain regular JSON files",
    )

    decision = _load_object(required_paths["decision"])
    stage = _validate_decision(decision, bundle, freeze_path, decision_adapter)
    terminal_name = (
        "confirmation-decision.json" if stage == "confirmation" else "screening-decision.json"
    )
    terminal_path = result_root / terminal_name
    _require(
        terminal_path.is_file() and not terminal_path.is_symlink(),
        f"{terminal_name} is missing or unsafe",
    )
    _require(
        terminal_path.read_bytes() == required_paths["decision"].read_bytes(),
        "decision.json is not an exact terminal-decision alias",
    )

    freeze_ref = _load_object(required_paths["freeze_ref"])
    _require(
        freeze_ref.get("freeze_id") == bundle["freeze_id"], "freeze-ref ID differs from freeze"
    )
    _require(
        freeze_ref.get("freeze_sha256") == sha256_path(freeze_path),
        "freeze-ref hash differs from freeze",
    )
    _require(
        freeze_ref.get("screening_pack_sha256") == bundle["private_packs"]["screening"]["sha256"],
        "screening private-pack hash differs from freeze",
    )
    _require(
        freeze_ref.get("confirmation_pack_sha256")
        == bundle["private_packs"]["confirmation"]["sha256"],
        "confirmation private-pack hash differs from freeze",
    )
    screening_decision = result_root / "screening-decision.json"
    confirmation_decision = result_root / "confirmation-decision.json"
    expected_screening_hash = (
        sha256_path(screening_decision) if screening_decision.is_file() else None
    )
    expected_confirmation_hash = (
        sha256_path(confirmation_decision) if confirmation_decision.is_file() else None
    )
    _require(
        freeze_ref.get("screening_decision_sha256") == expected_screening_hash,
        "screening-decision hash differs from freeze-ref",
    )
    _require(
        freeze_ref.get("confirmation_decision_sha256") == expected_confirmation_hash,
        "confirmation-decision hash differs from freeze-ref",
    )

    receipt = _load_object(required_paths["receipt"])
    measurement_set = _load_object(required_paths["measurements"])
    concept_path = _reference_path(
        required_paths["receipt"], receipt.get("concept_ref"), repository_root
    )
    manifest_path = _reference_path(
        required_paths["receipt"], receipt.get("study_ref"), repository_root
    )
    _reference_path(required_paths["receipt"], receipt.get("measurement_set_ref"), repository_root)
    contract_paths = [
        concept_path,
        manifest_path,
        required_paths["receipt"],
        required_paths["measurements"],
        *run_paths,
    ]
    documents, validation_issues = validate(contract_paths)
    if validation_issues:
        raise SandboxError(
            f"study audit failed: Contract v0 has {len(validation_issues)} issue(s): {validation_issues[0]}"
        )
    _require(
        receipt.get("study_ref", {}).get("study_id") == bundle["study_id"],
        "receipt study ID differs from freeze",
    )
    _require(
        receipt.get("study_ref", {}).get("revision") == bundle["study_revision"],
        "receipt revision differs from freeze",
    )

    observations, measurement_count = _run_observations(
        run_paths, measurement_set, bundle, stage, decision_adapter
    )
    counts_recomputed = False
    if decision_adapter == "pbt-v2":
        recomputed_counts = paired_counts(observations)
        _require(
            recomputed_counts == decision["counts"],
            "public run and measurement records do not reproduce PBT v2 decision counts",
        )
        counts_recomputed = True

    receipt_run_refs = receipt.get("run_record_refs")
    _require(isinstance(receipt_run_refs, list), "receipt run references are missing")
    receipt_run_ids = {
        reference.get("run_id") for reference in receipt_run_refs if isinstance(reference, dict)
    }
    loaded_run_ids = {_load_object(path)["run_id"] for path in run_paths}
    _require(
        receipt_run_ids == loaded_run_ids and len(receipt_run_refs) == len(run_paths),
        "receipt run references do not exactly cover published runs",
    )

    private_packs_verified: list[str] = []
    if screening_root is not None:
        verify_private_pack(bundle, "screening", screening_root)
        private_packs_verified.append("screening")
    if confirmation_root is not None:
        verify_private_pack(bundle, "confirmation", confirmation_root)
        private_packs_verified.append("confirmation")

    preregistration_sha = freeze_ref.get("preregistration_sha")
    _require(isinstance(preregistration_sha, str), "freeze-ref preregistration SHA is missing")
    preregistration: dict[str, Any] = {
        "sha": preregistration_sha,
        "git_verified": False,
        "freeze_bytes_verified": False,
        "terminal_decision_absent_at_freeze": False,
        "terminal_decision_committed_after_freeze": False,
        "tags": [],
    }
    selected_git_root = git_root.resolve() if git_root is not None else repository_root
    git_available = (selected_git_root / ".git").exists()
    if git_available:
        preregistration = _verify_git_preregistration(
            selected_git_root, freeze_path, result_root, preregistration_sha
        )
    elif require_git_proof:
        raise SandboxError(
            "study audit failed: Git preregistration proof was required but no Git root exists"
        )

    limitations = [
        "The decision observation payload was not supplied in this public bundle; the audit verifies its published hash and, with a decision adapter, recomputes counts from public records rather than its hidden bytes.",
        "Structural and lineage checks do not establish external validity, independent replication, or production impact.",
    ]
    unverified_packs = sorted({"screening", "confirmation"} - set(private_packs_verified))
    if unverified_packs:
        limitations.insert(
            0,
            "Private task-pack bytes were not supplied for "
            + ", ".join(unverified_packs)
            + "; only their frozen digests were checked.",
        )
    if decision_adapter is None:
        limitations.insert(
            0,
            "No study-specific decision adapter was selected; decision structure and lineage were checked, but aggregate counts and outcome were not recomputed.",
        )

    return {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "audit_id": f"{bundle['freeze_id']}:public-bundle",
        "status": "passed",
        "study": {"study_id": bundle["study_id"], "revision": bundle["study_revision"]},
        "freeze": {
            "freeze_id": bundle["freeze_id"],
            "sha256": sha256_path(freeze_path),
            "private_packs_verified": private_packs_verified,
        },
        "decision": {
            "stage": stage,
            "outcome": decision["outcome"],
            "counts": decision["counts"],
            "adapter": decision_adapter,
            "public_counts_recomputed": counts_recomputed,
        },
        "evidence": {
            "contract_documents": len(documents),
            "run_records": len(run_paths),
            "measurements": measurement_count,
            "terminal_decision_sha256": sha256_path(required_paths["decision"]),
        },
        "preregistration": preregistration,
        "limitations": limitations,
    }
