from __future__ import annotations

import argparse
from pathlib import Path

from completion_integrity_activation_support import load_json, write_json_atomic

from ael.codex_reporter import DEFAULT_REPORTER_IMAGE
from ael.sandbox import SandboxError, run_container, tree_sha256

PROBE_SCHEMA = "ael.completion-integrity-reporter-capability/0.1-pilot"


def probe_reporter(raw_root: Path, output: Path, *, image: str) -> dict[str, object]:
    raw_root = raw_root.absolute()
    output = output.absolute()
    if raw_root.is_symlink() or (raw_root.exists() and any(raw_root.iterdir())):
        raise SandboxError("reporter probe raw root must be new, empty, and non-symlink")
    raw_root.mkdir(parents=True, mode=0o700, exist_ok=True)
    fixture = raw_root / "fixture"
    fixture.mkdir(mode=0o700)
    (fixture / "probe-input.txt").write_text("sealed evidence\n", encoding="utf-8")
    host_evidence_sha256 = tree_sha256(fixture)
    run_output = raw_root / "output"
    result = run_container(
        fixture,
        run_output,
        ["--ael-probe"],
        image=image,
        network_policy="none",
        timeout_seconds=60,
        cpus="1",
        memory="512m",
        pids_limit=64,
        workspace_size="128m",
        tmp_size="64m",
    )
    raw = load_json(run_output / "boundary-probe.json")
    forbidden = raw.get("forbidden_paths_present")
    passed = (
        result.exit_code == 0
        and raw.get("cwd") == "/fixture"
        and raw.get("evidence_readable") is True
        and raw.get("evidence_write_blocked") is True
        and raw.get("evidence_sha256_before") == host_evidence_sha256
        and raw.get("evidence_sha256_before") == raw.get("evidence_sha256_after")
        and isinstance(forbidden, dict)
        and not any(forbidden.values())
        and raw.get("output_writable") is True
        and raw.get("auth_mounted") is False
    )
    document: dict[str, object] = {
        "schema_version": PROBE_SCHEMA,
        "probe_id": "kizz:ael:completion-integrity:activation-v1:reporter-boundary",
        "status": "pass" if passed else "fail",
        "image": image,
        "image_id": result.image_id,
        "assertions": {
            "starts_in_read_only_evidence": raw.get("cwd") == "/fixture"
            and raw.get("evidence_readable") is True
            and raw.get("evidence_write_blocked") is True,
            "evidence_identity_unchanged": raw.get("evidence_sha256_before")
            == raw.get("evidence_sha256_after"),
            "host_and_container_tree_hash_match": raw.get("evidence_sha256_before")
            == host_evidence_sha256,
            "task_artifact_evaluator_and_intervention_absent": isinstance(forbidden, dict)
            and not any(forbidden.values()),
            "output_only_persistence_surface": raw.get("output_writable") is True,
            "credential_absent_during_offline_probe": raw.get("auth_mounted") is False,
        },
        "boundary": (
            "This proves the Docker mount and write boundary for the probed image. It does not "
            "show that Codex is tool-free or establish claim accuracy."
        ),
    }
    write_json_atomic(output, document)
    if not passed:
        raise SandboxError("reporter capability probe failed")
    return document


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe the alpha.11 reporter capability boundary")
    parser.add_argument("--raw-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--image", default=DEFAULT_REPORTER_IMAGE)
    args = parser.parse_args()
    try:
        document = probe_reporter(args.raw_root, args.output, image=args.image)
    except SandboxError as exc:
        print(f"reporter capability probe failed: {exc}")
        return 1
    print(f"reporter capability probe {document['status']}: {document['image_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
