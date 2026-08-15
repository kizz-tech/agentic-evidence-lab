"""Named audit-adapter registry shared by the CLI and public projection.

Study-family audit semantics remain explicit and closed by default.  Adding a
new adapter is one registry change with one focused test; callers no longer
duplicate family dispatch or silently drift on supported names.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from ael.completion_integrity_audit import audit_completion_integrity_bundle
from ael.debugging_shadow_audit import audit_debugging_shadow_bundle
from ael.sandbox import SandboxError
from ael.study_audit import audit_study_bundle


@dataclass(frozen=True)
class AuditRequest:
    freeze_path: Path
    result_root: Path
    screening_root: Path | None = None
    confirmation_root: Path | None = None
    git_root: Path | None = None
    require_git_proof: bool = False


AuditRunner = Callable[[AuditRequest], dict[str, Any]]


def _pbt_v2(request: AuditRequest) -> dict[str, Any]:
    return audit_study_bundle(
        request.freeze_path,
        request.result_root,
        screening_root=request.screening_root,
        confirmation_root=request.confirmation_root,
        git_root=request.git_root,
        require_git_proof=request.require_git_proof,
        decision_adapter="pbt-v2",
    )


def _systematic_debugging_real_shadow(request: AuditRequest) -> dict[str, Any]:
    if request.screening_root or request.confirmation_root:
        raise SandboxError(
            "the real-shadow adapter verifies opaque private-pack hashes; "
            "legacy screening/confirmation roots are unsupported"
        )
    return audit_debugging_shadow_bundle(
        request.freeze_path,
        request.result_root,
        git_root=request.git_root,
        require_git_proof=request.require_git_proof,
    )


def _completion_integrity_prompt_policy(request: AuditRequest) -> dict[str, Any]:
    if request.screening_root or request.confirmation_root:
        raise SandboxError(
            "the Completion Integrity adapter verifies opaque private-pack hashes; "
            "legacy screening/confirmation roots are unsupported"
        )
    return audit_completion_integrity_bundle(
        request.freeze_path,
        request.result_root,
        git_root=request.git_root,
        require_git_proof=request.require_git_proof,
    )


AUDIT_ADAPTERS: Mapping[str, AuditRunner] = MappingProxyType(
    {
        "completion-integrity-prompt-policy-v1": _completion_integrity_prompt_policy,
        "pbt-v2": _pbt_v2,
        "systematic-debugging-real-shadow-v1": _systematic_debugging_real_shadow,
    }
)


def audit_adapter_names() -> tuple[str, ...]:
    return tuple(sorted(AUDIT_ADAPTERS))


def audit_bundle(adapter: str | None, request: AuditRequest) -> dict[str, Any]:
    """Run one explicit adapter, or the generic Contract audit when omitted."""

    if adapter is None:
        return audit_study_bundle(
            request.freeze_path,
            request.result_root,
            screening_root=request.screening_root,
            confirmation_root=request.confirmation_root,
            git_root=request.git_root,
            require_git_proof=request.require_git_proof,
            decision_adapter=None,
        )
    runner = AUDIT_ADAPTERS.get(adapter)
    if runner is None:
        raise SandboxError(f"unknown study audit adapter: {adapter}")
    return runner(request)


def public_audit_projection(adapter: str, request: AuditRequest) -> dict[str, Any]:
    """Project stable audit facts while keeping Git proof a build-only gate."""

    summary = audit_bundle(adapter, request)
    # Study-local adapters may expose richer terminal result semantics than the
    # generic Contract audit.  Add the small stable rendering surface without
    # discarding that family-owned detail.
    if "status" not in summary:
        result = summary.get("result")
        if not isinstance(result, Mapping):
            raise SandboxError("study audit lacks a stable public result summary")
        run_count = result.get("run_count")
        measurement_count = result.get("measurement_count")
        if not isinstance(run_count, int) or not isinstance(measurement_count, int):
            raise SandboxError("study audit lacks public evidence counts")
        summary["status"] = "passed"
        summary["evidence"] = {
            "contract_documents": run_count + 4,
            "run_records": run_count,
            "measurements": measurement_count,
        }
    preregistration = summary.get("preregistration")
    if isinstance(preregistration, dict):
        preregistration.pop("git_verified", None)
        preregistration["boundary"] = (
            "Git proof is an optional fail-closed build gate and is not projected as evidence; "
            "when required, it establishes repository artifact ordering only."
        )
    return summary
