from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

FIXTURE = Path("/fixture")
WORKSPACE = Path("/workspace/repo")
HOME = Path("/workspace/home")
OUTPUT = Path("/output")
AUTH_SOURCE = Path("/run/ael-secrets/codex-auth.json")
SKILL_SOURCE = Path("/intervention")


def main() -> int:
    if not FIXTURE.is_dir() or not OUTPUT.is_dir():
        print("runner requires /fixture and /output mounts", file=sys.stderr)
        return 125
    if not sys.argv[1:]:
        print("runner requires a command", file=sys.stderr)
        return 125
    if any(OUTPUT.iterdir()):
        print("runner requires an empty /output directory", file=sys.stderr)
        return 125

    HOME.mkdir(parents=True, exist_ok=False)
    if AUTH_SOURCE.is_file():
        codex_home = HOME / ".codex"
        codex_home.mkdir(mode=0o700)
        auth_target = codex_home / "auth.json"
        shutil.copyfile(AUTH_SOURCE, auth_target)
        auth_target.chmod(0o600)
    if SKILL_SOURCE.is_dir():
        skill_name = os.environ.get("AEL_SKILL_NAME", "intervention")
        if not skill_name or "/" in skill_name or skill_name in {".", ".."}:
            print("invalid AEL_SKILL_NAME", file=sys.stderr)
            return 125
        skills_root = HOME / ".codex" / "skills"
        skills_root.mkdir(parents=True, exist_ok=True)
        shutil.copytree(SKILL_SOURCE, skills_root / skill_name, symlinks=True)
    shutil.copytree(FIXTURE, WORKSPACE, symlinks=True)
    started = time.monotonic()
    with (OUTPUT / "stdout.log").open("wb") as stdout, (OUTPUT / "stderr.log").open("wb") as stderr:
        completed = subprocess.run(
            sys.argv[1:], cwd=WORKSPACE, stdout=stdout, stderr=stderr, check=False
        )
    duration_ms = round((time.monotonic() - started) * 1000)
    shutil.copytree(WORKSPACE, OUTPUT / "workspace", symlinks=True)
    (OUTPUT / "container-result.json").write_text(
        json.dumps(
            {
                "schema_version": "ael.container-result/0.1",
                "exit_code": completed.returncode,
                "duration_ms": duration_ms,
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
