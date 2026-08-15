"""Fail-closed public audit for a versioned Completion Integrity activation."""

from __future__ import annotations

import hashlib
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ael.completion_integrity_activation import (
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


def _git(root: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(["git", *arguments], cwd=root, capture_output=True, check=False)
    if check and result.returncode != 0:
        _fail(f"git {' '.join(arguments)} failed")
    return result


def _verify_git(
    *, repository_root: Path, freeze_path: Path, result_root: Path, preregistration_sha: str
) -> dict[str, Any]:
    _git(repository_root, "cat-file", "-e", f"{preregistration_sha}^{{commit}}")
    _git(repository_root, "merge-base", "--is-ancestor", preregistration_sha, "HEAD")
    freeze_relative = freeze_path.relative_to(repository_root).as_posix()
    frozen_bytes = _git(repository_root, "show", f"{preregistration_sha}:{freeze_relative}").stdout
    if hashlib.sha256(frozen_bytes).hexdigest() != sha256_path(freeze_path):
        _fail("preregistration commit contains different freeze bytes")
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
    prefix = "ci11" if study_revision == 1 else f"ci11-r{study_revision}"
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
    repository_root = (git_root or Path(__file__).resolve().parents[2]).resolve()
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
    claim_prefix = "AEL-CI11" if revision == 1 else f"AEL-CI11-R{revision}"
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
        },
        "preregistration": preregistration,
    }
