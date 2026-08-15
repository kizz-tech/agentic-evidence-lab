from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

EVIDENCE = Path("/fixture")
HOME = Path("/workspace/home")
OUTPUT = Path("/output")
AUTH_SOURCE = Path("/run/ael-secrets/codex-auth.json")


def tree_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise RuntimeError(f"sealed evidence contains a symlink: {relative}")
        if path.is_dir():
            digest.update(f"D\0{relative}\n".encode())
        elif path.is_file():
            digest.update(f"F\0{relative}\0".encode())
            digest.update(path.read_bytes())
            digest.update(b"\n")
        else:
            raise RuntimeError(f"sealed evidence contains a special member: {relative}")
    return digest.hexdigest()


def probe_boundary() -> int:
    os.chdir(EVIDENCE)
    evidence_before = tree_sha256(EVIDENCE)
    write_blocked = False
    try:
        (EVIDENCE / ".ael-probe-write").write_text("forbidden\n", encoding="utf-8")
    except OSError:
        write_blocked = True
    forbidden_paths = {
        path: Path(path).exists()
        for path in ("/workspace/repo", "/evaluator", "/artifact", "/intervention")
    }
    output_probe = OUTPUT / ".ael-output-probe"
    output_probe.write_text("ok\n", encoding="utf-8")
    output_writable = output_probe.read_text(encoding="utf-8") == "ok\n"
    output_probe.unlink()
    evidence_after = tree_sha256(EVIDENCE)
    document = {
        "schema_version": "ael.codex-reporter-boundary-probe/0.1",
        "cwd": str(Path.cwd()),
        "evidence_readable": (EVIDENCE / "probe-input.txt").read_text(encoding="utf-8")
        == "sealed evidence\n",
        "evidence_write_blocked": write_blocked,
        "evidence_sha256_before": evidence_before,
        "evidence_sha256_after": evidence_after,
        "forbidden_paths_present": forbidden_paths,
        "output_writable": output_writable,
        "auth_mounted": AUTH_SOURCE.exists(),
    }
    (OUTPUT / "boundary-probe.json").write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return (
        0
        if all(
            (
                document["cwd"] == "/fixture",
                document["evidence_readable"],
                document["evidence_write_blocked"],
                evidence_before == evidence_after,
                not any(forbidden_paths.values()),
                document["output_writable"],
                not document["auth_mounted"],
            )
        )
        else 125
    )


def main() -> int:
    if not EVIDENCE.is_dir() or not OUTPUT.is_dir():
        print("reporter requires /fixture and /output mounts", file=sys.stderr)
        return 125
    if not sys.argv[1:]:
        print("reporter requires a command", file=sys.stderr)
        return 125
    if any(OUTPUT.iterdir()):
        print("reporter requires an empty /output directory", file=sys.stderr)
        return 125
    if sys.argv[1:] == ["--ael-probe"]:
        return probe_boundary()
    evidence_before = tree_sha256(EVIDENCE)
    HOME.mkdir(parents=True, exist_ok=False)
    if not AUTH_SOURCE.is_file():
        print("reporter requires explicit Codex authentication", file=sys.stderr)
        return 125
    codex_home = HOME / ".codex"
    codex_home.mkdir(mode=0o700)
    auth_target = codex_home / "auth.json"
    shutil.copyfile(AUTH_SOURCE, auth_target)
    auth_target.chmod(0o600)

    started = time.monotonic()
    with (OUTPUT / "stdout.log").open("wb") as stdout, (OUTPUT / "stderr.log").open("wb") as stderr:
        completed = subprocess.run(
            sys.argv[1:],
            cwd=EVIDENCE,
            stdout=stdout,
            stderr=stderr,
            check=False,
        )
    duration_ms = round((time.monotonic() - started) * 1000)
    evidence_after = tree_sha256(EVIDENCE)
    home_members = sorted(
        path.relative_to(HOME).as_posix()
        for path in HOME.rglob("*")
        if path.relative_to(HOME).as_posix() != ".codex/auth.json"
    )
    (OUTPUT / "container-result.json").write_text(
        json.dumps(
            {
                "schema_version": "ael.codex-reporter-container/0.1",
                "exit_code": completed.returncode,
                "duration_ms": duration_ms,
                "evidence_sha256_before": evidence_before,
                "evidence_sha256_after": evidence_after,
                "cwd": "/fixture",
                "task_artifact_mounted": False,
                "evaluator_mounted": False,
                "executor_workspace_mounted": False,
                "home_non_auth_member_count": len(home_members),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
