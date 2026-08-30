"""Fail-closed public audit for a versioned Completion Integrity activation."""

from __future__ import annotations

import hashlib
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ael.completion_integrity_activation import (
    activation_claim_prefix,
    activation_measurement_prefix,
    decide_activation,
    decision_id_from_study_id,
    decision_measurements,
    validate_observations,
)
from ael.sandbox import SandboxError
from ael.validation import sha256_path, validate

FREEZE_SCHEMA = "ael.completion-integrity-activation-freeze/0.1-pilot"
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
    raise SandboxError(f"completion-integrity activation audit failed: {message}")


def _load(path: Path) -> dict[str, Any]:
    from ael.prospective_study import load_json_object

    return load_json_object(path)


def _repository_root(freeze_path: Path, explicit_root: Path | None) -> Path:
    if explicit_root is not None:
        root = explicit_root.resolve()
    else:
        root = next(
            (
                candidate
                for candidate in (freeze_path.parent, *freeze_path.parents)
                if (candidate / "pyproject.toml").is_file()
                and (candidate / "src" / "ael" / "schemas").is_dir()
            ),
            None,
        )
        if root is None:
            _fail("repository root could not be derived from the freeze path")
        root = root.resolve()
    if not freeze_path.resolve().is_relative_to(root):
        _fail("freeze path is outside the repository root")
    return root


def _git(root: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(["git", *arguments], cwd=root, capture_output=True, check=False)
    if check and result.returncode != 0:
        _fail(f"git {' '.join(arguments)} failed")
    return result


def _verify_git(
    *,
    repository_root: Path,
    freeze_path: Path,
    result_root: Path,
    preregistration_sha: str,
    freeze: Mapping[str, Any],
) -> dict[str, Any]:
    _git(repository_root, "cat-file", "-e", f"{preregistration_sha}^{{commit}}")
    _git(repository_root, "merge-base", "--is-ancestor", preregistration_sha, "HEAD")
    freeze_relative = freeze_path.relative_to(repository_root).as_posix()
    frozen_bytes = _git(repository_root, "show", f"{preregistration_sha}:{freeze_relative}").stdout
    if hashlib.sha256(frozen_bytes).hexdigest() != sha256_path(freeze_path):
        _fail("preregistration commit contains different freeze bytes")
    code_refs = freeze.get("code_refs")
    if not isinstance(code_refs, Mapping) or not code_refs:
        _fail("freeze has no code reference map")
    for relative, expected in code_refs.items():
        if not isinstance(relative, str) or not isinstance(expected, str):
            _fail("freeze code reference is malformed")
        frozen_code = _git(repository_root, "show", f"{preregistration_sha}:{relative}").stdout
        if hashlib.sha256(frozen_code).hexdigest() != expected:
            _fail(f"preregistration code binding differs: {relative}")
    decision_relative = (result_root / "decision.json").relative_to(repository_root).as_posix()
    if (
        _git(
            repository_root,
            "cat-file",
            "-e",
            f"{preregistration_sha}:{decision_relative}",
            check=False,
        ).returncode
        == 0
    ):
        _fail("terminal decision existed at preregistration")
    for path in sorted(result_root.rglob("*")):
        if path.is_symlink() or (not path.is_file() and not path.is_dir()):
            _fail("result tree contains a symlink or special member")
        if not path.is_file():
            continue
        relative = path.relative_to(repository_root).as_posix()
        committed = _git(repository_root, "show", f"HEAD:{relative}").stdout
        if hashlib.sha256(committed).hexdigest() != sha256_path(path):
            _fail(f"HEAD contains different result bytes: {relative}")
    return {
        "sha": preregistration_sha,
        "git_verified": True,
        "freeze_bytes_verified": True,
        "terminal_result_absent_at_freeze": True,
        "terminal_result_committed_after_freeze": True,
    }


def _verify_freeze_refs(freeze: Mapping[str, Any], repository_root: Path) -> None:
    public_refs = freeze.get("public_refs")
    if not isinstance(public_refs, Mapping) or not public_refs:
        _fail("freeze has no public reference map")
    for relative, expected in public_refs.items():
        if not isinstance(relative, str) or relative.startswith("/") or "\\" in relative:
            _fail("freeze public ref is unsafe")
        path = repository_root / relative
        if path.is_symlink() or not path.is_file() or sha256_path(path) != expected:
            _fail(f"frozen public reference differs: {relative}")


def _verify_contract(
    *, repository_root: Path, freeze_path: Path, result_root: Path
) -> tuple[int, int, int]:
    run_paths = sorted((result_root / "runs").glob("*.json"))
    paths = [
        repository_root / "studies" / "completion-integrity" / "concept.json",
        freeze_path.parent / "study-manifest.json",
        *run_paths,
        result_root / "measurement-set.json",
        result_root / "evidence-receipt.json",
    ]
    documents, issues = validate(paths)
    if issues:
        _fail(f"Contract v0 graph has {len(issues)} issue(s): {issues[0]}")
    measurement = _load(result_root / "measurement-set.json")
    return len(documents), len(run_paths), len(measurement["measurements"])


def _verify_decision_measurements(
    decision: Mapping[str, Any],
    measurement_set: Mapping[str, Any],
    *,
    study_revision: int,
) -> None:
    prefix = activation_measurement_prefix(study_revision)
    expected = {f"{prefix}:{metric}": value for metric, value in decision_measurements(decision)}
    observed: dict[str, object] = {}
    for measurement in measurement_set.get("measurements", []):
        if not isinstance(measurement, Mapping):
            _fail("measurement set contains a malformed row")
        measurement_id = measurement.get("measurement_id")
        if measurement_id not in expected:
            continue
        if measurement_id in observed:
            _fail("decision measurement is duplicated")
        observed[str(measurement_id)] = measurement.get("value")
    if observed != expected:
        _fail("public decision measurements differ from deterministic decision")


def _verify_schedule_projection(
    freeze: Mapping[str, Any],
    observations: Mapping[str, Any],
    result_root: Path,
) -> None:
    schedule = freeze.get("schedule")
    if not isinstance(schedule, list):
        _fail("freeze schedule is malformed")
    expected_task_ids: list[str] = []
    for entry in schedule:
        if not isinstance(entry, Mapping):
            _fail("freeze schedule row is malformed")
        task_id = entry.get("task_id")
        if not isinstance(task_id, str):
            _fail("freeze schedule task identity is malformed")
        if task_id not in expected_task_ids:
            expected_task_ids.append(task_id)
    tasks = observations.get("tasks")
    if not isinstance(tasks, list) or [task.get("task_id") for task in tasks] != expected_task_ids:
        _fail("public observation tasks differ from the frozen schedule")
    observation_status: dict[str, str] = {}
    for task in tasks:
        if not isinstance(task, Mapping):
            _fail("public observation task is malformed")
        task_id = str(task["task_id"])
        observation_status[f"{task_id}-E0"] = str(task["executor_status"])
        reporters = task.get("reporters")
        if not isinstance(reporters, list):
            _fail("public observation reporters are malformed")
        for reporter in reporters:
            if not isinstance(reporter, Mapping):
                _fail("public observation reporter is malformed")
            observation_status[f"{task_id}-{reporter['condition_id']}"] = str(reporter["status"])
    for entry in schedule:
        cell_id = str(entry["cell_id"])
        run = _load(result_root / "runs" / f"{cell_id}.json")
        run_task = run.get("task")
        if not isinstance(run_task, Mapping) or run_task.get("task_id") != entry["task_id"]:
            _fail(f"public run task differs from schedule: {cell_id}")
        expected_condition = str(entry.get("condition_id") or "E0")
        if run.get("condition_id") != expected_condition:
            _fail(f"public run condition differs from schedule: {cell_id}")
        source_status = observation_status[cell_id]
        expected_status = (
            "valid"
            if source_status == "valid"
            else "invalid"
            if source_status in {"invalid", "ambiguous"}
            else "unrun"
        )
        if run.get("status") != expected_status:
            _fail(f"public run status differs from normalized observation: {cell_id}")
        if source_status == "ambiguous" and not any(
            "ambiguous" in str(issue).lower() for issue in run.get("integrity_issues", [])
        ):
            _fail(f"ambiguous attempt is not explicit in public run: {cell_id}")


def _scan_public(result_root: Path) -> None:
    for path in sorted(result_root.rglob("*")):
        if path.is_symlink():
            _fail("result tree contains a symlink")
        if not path.is_file():
            continue
        payload = path.read_text(encoding="utf-8", errors="replace")
        for marker in _FORBIDDEN_PUBLIC_MARKERS:
            if marker in payload:
                _fail(f"forbidden private marker found in {path.name}")


def _verify_normalization_deviation(
    *,
    freeze: Mapping[str, Any],
    freeze_path: Path,
    result_root: Path,
    repository_root: Path,
    preregistration_sha: str,
    require_git_proof: bool,
) -> dict[str, Any] | None:
    path = result_root / "normalization-deviation.json"
    if not path.exists():
        return None
    if path.is_symlink() or not path.is_file():
        _fail("normalization deviation is unsafe")
    deviation = _load(path)
    if deviation.get("study_id") != freeze.get("study_id") or deviation.get(
        "study_revision"
    ) != freeze.get("study_revision"):
        _fail("normalization deviation study binding differs")
    if deviation.get("preregistration_sha") != preregistration_sha:
        _fail("normalization deviation preregistration differs")
    if deviation.get("freeze_sha256") != sha256_path(freeze_path):
        _fail("normalization deviation freeze binding differs")
    frozen_refs = deviation.get("frozen_source_refs")
    code_refs = freeze.get("code_refs")
    if not isinstance(frozen_refs, Mapping) or not isinstance(code_refs, Mapping):
        _fail("normalization deviation source maps are malformed")
    if any(code_refs.get(relative) != digest for relative, digest in frozen_refs.items()):
        _fail("normalization deviation frozen source binding differs")
    published = deviation.get("published_result_refs")
    if not isinstance(published, Mapping) or not published:
        _fail("normalization deviation has no published result bindings")
    for relative, expected in published.items():
        if (
            not isinstance(relative, str)
            or "/" in relative
            or not isinstance(expected, str)
            or sha256_path(result_root / relative) != expected
        ):
            _fail(f"normalization deviation result binding differs: {relative}")
    normalization = deviation.get("normalization")
    if not isinstance(normalization, Mapping):
        _fail("normalization deviation operation is malformed")
    expected_zero = {
        "model_calls": 0,
        "evaluator_calls": 0,
        "retries": 0,
        "resumes": 0,
        "overwrites": 0,
        "terminal_cells_created": 0,
    }
    if any(normalization.get(key) != value for key, value in expected_zero.items()):
        _fail("normalization deviation introduced a forbidden operation")
    terminal_refs = deviation.get("terminal_projection_source_refs")
    if not isinstance(terminal_refs, Mapping) or not terminal_refs:
        _fail("normalization deviation terminal source map is malformed")
    commit = deviation.get("terminal_projection_commit")
    git_verified = False
    if require_git_proof:
        if not isinstance(commit, str) or len(commit) != 40:
            _fail("normalization deviation lacks its terminal projection commit")
        _git(repository_root, "cat-file", "-e", f"{commit}^{{commit}}")
        _git(repository_root, "merge-base", "--is-ancestor", commit, "HEAD")
        for relative, expected in terminal_refs.items():
            if not isinstance(relative, str) or not isinstance(expected, str):
                _fail("normalization deviation terminal source binding is malformed")
            payload = _git(repository_root, "show", f"{commit}:{relative}").stdout
            if hashlib.sha256(payload).hexdigest() != expected:
                _fail(f"terminal projection source binding differs: {relative}")
        git_verified = True
    elif commit is not None and (not isinstance(commit, str) or len(commit) != 40):
        _fail("normalization deviation terminal projection commit is malformed")
    return {
        "status": "disclosed_and_verified" if git_verified else "disclosed",
        "model_calls": normalization["model_calls"],
        "retries": normalization["retries"],
        "terminal_projection_commit": commit,
    }


def audit_completion_integrity_activation_bundle(
    freeze_path: Path,
    result_root: Path,
    *,
    git_root: Path | None = None,
    require_git_proof: bool = False,
) -> dict[str, Any]:
    freeze_path = freeze_path.absolute()
    result_root = result_root.absolute()
    if freeze_path.is_symlink() or not freeze_path.is_file():
        _fail("freeze path is missing or unsafe")
    if result_root.is_symlink() or not result_root.is_dir():
        _fail("result root is missing or unsafe")
    repository_root = _repository_root(freeze_path, git_root)
    freeze = _load(freeze_path)
    if freeze.get("schema_version") != FREEZE_SCHEMA:
        _fail("freeze schema version differs")
    try:
        decision_id = decision_id_from_study_id(freeze.get("study_id"))
    except ValueError as exc:
        _fail(str(exc))
    _verify_freeze_refs(freeze, repository_root)
    required = {
        "observations.json",
        "decision.json",
        "freeze-ref.json",
        "measurement-set.json",
        "evidence-receipt.json",
    }
    if not required.issubset({path.name for path in result_root.iterdir() if path.is_file()}):
        _fail("result root lacks a required public document")
    observations = validate_observations(_load(result_root / "observations.json"))
    decision = decide_activation(observations, decision_id=decision_id)
    if _load(result_root / "decision.json") != decision:
        _fail("terminal decision does not recompute from public observations")
    if observations["freeze_sha256"] != sha256_path(freeze_path):
        _fail("observations refer to different freeze bytes")
    freeze_ref = _load(result_root / "freeze-ref.json")
    expected_freeze_ref = {
        "schema_version": "ael.completion-integrity-activation-freeze-ref/0.1-pilot",
        "freeze_id": freeze["freeze_id"],
        "freeze_sha256": sha256_path(freeze_path),
        "preregistration_sha": observations["preregistration_sha"],
        "observations_sha256": sha256_path(result_root / "observations.json"),
        "decision_sha256": sha256_path(result_root / "decision.json"),
        "private_pack_sha256": freeze["private_pack"]["supply_artifact_sha256"],
        "qualification_sha256": freeze["qualification"]["receipt_sha256"],
    }
    if freeze_ref != expected_freeze_ref:
        _fail("freeze-ref does not bind the exact terminal public result")
    run_paths = sorted((result_root / "runs").glob("*.json"))
    if len(run_paths) != len(freeze["schedule"]):
        _fail("run count differs from frozen schedule")
    expected_cells = [str(entry["cell_id"]) for entry in freeze["schedule"]]
    if [path.stem for path in run_paths] != sorted(expected_cells):
        _fail("public run identities differ from frozen schedule")
    _verify_schedule_projection(freeze, observations, result_root)
    normalization_deviation = _verify_normalization_deviation(
        freeze=freeze,
        freeze_path=freeze_path,
        result_root=result_root,
        repository_root=repository_root,
        preregistration_sha=str(observations["preregistration_sha"]),
        require_git_proof=require_git_proof,
    )
    measurement_set = _load(result_root / "measurement-set.json")
    revision = freeze.get("study_revision")
    if not isinstance(revision, int) or revision < 1:
        _fail("freeze study revision is invalid")
    _verify_decision_measurements(
        decision,
        measurement_set,
        study_revision=revision,
    )
    receipt = _load(result_root / "evidence-receipt.json")
    claim_prefix = activation_claim_prefix(revision)
    if [claim.get("claim_id") for claim in receipt.get("evaluated_claims", [])] != [
        f"{claim_prefix}-01",
        f"{claim_prefix}-02",
    ]:
        _fail("receipt claim set differs from the bounded activation surface")
    unsupported = receipt.get("unsupported_inferences")
    if not isinstance(unsupported, list) or len(unsupported) < 5:
        _fail("receipt does not preserve the activation claim ceiling")
    documents, run_count, measurement_count = _verify_contract(
        repository_root=repository_root,
        freeze_path=freeze_path,
        result_root=result_root,
    )
    _scan_public(result_root)
    preregistration = {
        "sha": observations["preregistration_sha"],
        "git_verified": False,
        "boundary": "Without Git proof, this audit verifies the public graph and deterministic decision only.",
    }
    if require_git_proof:
        preregistration = _verify_git(
            repository_root=repository_root,
            freeze_path=freeze_path,
            result_root=result_root,
            preregistration_sha=str(observations["preregistration_sha"]),
            freeze=freeze,
        )
    return {
        "schema_version": "ael.completion-integrity-activation-audit/0.1-pilot",
        "status": "passed",
        "study": {"study_id": freeze["study_id"], "revision": freeze["study_revision"]},
        "result": {
            "status": decision["status"],
            "disposition": decision["disposition"],
            "counts": decision["counts"],
            "condition_counts": decision["condition_counts"],
            "claim_ceiling": decision["claim_ceiling"],
        },
        "evidence": {
            "contract_documents": documents,
            "run_records": run_count,
            "measurements": measurement_count,
            **(
                {"normalization_deviation": normalization_deviation}
                if normalization_deviation is not None
                else {}
            ),
        },
        "preregistration": preregistration,
    }
