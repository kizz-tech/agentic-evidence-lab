from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from pathlib import Path

from ael import __version__
from ael.result_surface import ResultSurfaceError, materialize_result_surface
from ael.sandbox import SandboxError
from ael.study_quality import materialize_preflight

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = {
    ".gitattributes",
    ".github/CODEOWNERS",
    ".github/workflows/ci.yml",
    ".gitignore",
    "AGENTS.md",
    "CHANGELOG.md",
    "CITATION.cff",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "GOVERNANCE.md",
    "LICENSE",
    "NOTICE",
    "README.md",
    "ROADMAP.md",
    "RESULTS.md",
    "SECURITY.md",
    "SUPPORT.md",
    "docs/release-notes/v0.1.0-alpha.7.md",
    "docs/results/index.json",
    "docs/study-quality-preflight.md",
    "pyproject.toml",
    "studies/public-results.json",
    "studies/quality-preflight/examples/pass/preflight.json",
    "studies/quality-preflight/examples/pass/preflight.md",
    "studies/quality-preflight/examples/pass/quality-profile.json",
    "uv.lock",
}
ALLOWED_TOP_LEVEL = {
    ".gitattributes",
    ".github",
    ".gitignore",
    "AGENTS.md",
    "CHANGELOG.md",
    "CITATION.cff",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "GOVERNANCE.md",
    "LICENSE",
    "NOTICE",
    "README.md",
    "ROADMAP.md",
    "RESULTS.md",
    "SECURITY.md",
    "SUPPORT.md",
    "docker",
    "docs",
    "examples",
    "pyproject.toml",
    "reports",
    "src",
    "studies",
    "tests",
    "tools",
    "uv.lock",
}
FORBIDDEN_PARTS = {
    ".env",
    ".venv",
    "artifacts/private",
    "reviews/private",
    "__pycache__",
    "dist",
}
SECRET_PATTERNS = {
    "OpenAI-style API key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "GitHub token": re.compile(r"\b(?:gh[opsu]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "AWS-style access key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "signed URL query": re.compile(
        r"(?i)(?:X-Amz-Signature|X-Goog-Signature|Signature)=[A-Fa-f0-9%]{16,}"
    ),
}
PERSONAL_PATH_PATTERNS = (
    re.compile(r"(?<![A-Za-z0-9_.-])/(?:Users|home)/[^./\s][^/\s]*/"),
    re.compile(r"[A-Za-z]:\\Users\\[^\s]+\\"),
)
MAX_PUBLIC_FILE_BYTES = 2 * 1024 * 1024
PRIVATE_EVIDENCE_CANARY_PREFIX = "AEL-HIDDEN-" + "CANARY:"


def public_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [ROOT / item.decode("utf-8") for item in result.stdout.split(b"\0") if item]


def payload_failures(relative: str, payload: str) -> list[str]:
    failures: list[str] = []
    workspace_marker = "codex" + "-work1"
    if (
        any(pattern.search(payload) for pattern in PERSONAL_PATH_PATTERNS)
        or workspace_marker in payload
    ):
        failures.append(f"personal absolute path or workspace marker: {relative}")
    if PRIVATE_EVIDENCE_CANARY_PREFIX in payload:
        failures.append(f"private evidence canary leaked into public tree: {relative}")
    for label, pattern in SECRET_PATTERNS.items():
        if pattern.search(payload):
            failures.append(f"{label} shaped value: {relative}")
    return failures


def main() -> int:
    failures: list[str] = []
    files = public_files()
    relative_files = {path.relative_to(ROOT).as_posix() for path in files}

    for required in sorted(REQUIRED_FILES - relative_files):
        failures.append(f"missing required release file: {required}")

    for relative in sorted(relative_files):
        top = relative.split("/", 1)[0]
        if top not in ALLOWED_TOP_LEVEL:
            failures.append(f"outside positive release allowlist: {relative}")
        if any(relative == part or relative.startswith(part + "/") for part in FORBIDDEN_PARTS):
            failures.append(f"private or generated path is public: {relative}")

    for path in files:
        relative = path.relative_to(ROOT).as_posix()
        if path.is_symlink():
            failures.append(f"public tree contains a symlink: {relative}")
            continue
        if not path.is_file():
            failures.append(f"public tree contains a non-regular entry: {relative}")
            continue
        if path.stat().st_size > MAX_PUBLIC_FILE_BYTES:
            failures.append(f"public file exceeds {MAX_PUBLIC_FILE_BYTES} bytes: {relative}")
            continue
        try:
            payload = path.read_text(encoding="utf-8")
        except OSError as exc:
            failures.append(f"cannot read public file {relative}: {exc}")
            continue
        except UnicodeDecodeError:
            failures.append(f"public release file is not UTF-8 text: {relative}")
            continue
        failures.extend(payload_failures(relative, payload))

    expected_version = "0.1.0a7"
    expected_release = "0.1.0-alpha.7"
    if __version__ != expected_version:
        failures.append(f"package version is {__version__}, expected {expected_version}")
    try:
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
        project_version = project["version"]
    except (OSError, UnicodeError, tomllib.TOMLDecodeError, KeyError, TypeError) as exc:
        failures.append(f"cannot read pyproject project.version: {exc}")
    else:
        if project_version != expected_version:
            failures.append(
                f"pyproject project.version is {project_version}, expected {expected_version}"
            )
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    if f'version: "{expected_release}"' not in citation:
        failures.append(f"CITATION.cff release version is not {expected_release}")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if f"## [{expected_release}]" not in changelog:
        failures.append(f"CHANGELOG.md has no {expected_release} release section")

    try:
        materialize_preflight(
            ROOT / "studies/quality-preflight/examples/pass/quality-profile.json",
            json_output=ROOT / "studies/quality-preflight/examples/pass/preflight.json",
            markdown_output=ROOT / "studies/quality-preflight/examples/pass/preflight.md",
            check=True,
            repository_root=ROOT,
        )
    except SandboxError as exc:
        failures.append(f"study quality preflight example is stale or invalid: {exc}")

    try:
        materialize_result_surface(
            ROOT / "studies/public-results.json",
            repository_root=ROOT,
            check=True,
        )
    except ResultSurfaceError as exc:
        failures.append(f"generated result projection is stale or invalid: {exc}")
    frozen_check = subprocess.run(
        [sys.executable, str(ROOT / "tools/check_frozen_artifacts.py")],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if frozen_check.returncode:
        detail = frozen_check.stderr.strip() or frozen_check.stdout.strip()
        failures.append(f"frozen evidence check failed: {detail}")

    if failures:
        for failure in failures:
            print(f"release check failed: {failure}", file=sys.stderr)
        return 1
    print(f"release check passed: {len(files)} public file(s); version={__version__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
