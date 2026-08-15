"""Fail-closed checks for Python wheel and source-distribution archives.

The repository release-tree checker operates on checked-out files.  This
module applies the same privacy checks to the bytes that will actually be
distributed, without importing the repository checker (which is deliberately
not part of the installed package).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import sys
import tarfile
import tomllib
import zipfile
from collections.abc import Iterable, Sequence
from email import policy
from email.parser import BytesParser
from pathlib import Path, PurePosixPath

# Keep these small literals aligned with tools/release_check.py.  They are
# duplicated here so the verifier remains usable from a clean installation.
FORBIDDEN_PARTS = {
    ".env",
    ".venv",
    "artifacts/private",
    "reviews/private",
    "__pycache__",
    "dist",
}
SECRET_PATTERNS = {
    "OpenAI-style API key": re.compile(rb"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "GitHub token": re.compile(rb"\b(?:gh[opsu]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    "private key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "AWS-style access key": re.compile(rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "signed URL query": re.compile(
        rb"(?i)(?:X-Amz-Signature|X-Goog-Signature|Signature)=[A-Fa-f0-9%]{16,}"
    ),
}
PRIVATE_EVIDENCE_CANARY_PREFIX = b"AEL-HIDDEN-" + b"CANARY:"
PERSONAL_PATH_PATTERNS = (
    # Require a path-boundary before the leading slash so /workspace/home/...,
    # a common container path, is not mistaken for a host user's home.
    re.compile(rb"(?<![A-Za-z0-9_.-])/(?:Users|home)/[^./\s][^/\s]*/"),
    re.compile(rb"[A-Za-z]:\\Users\\[^\s]+\\"),
)
WORKSPACE_MARKER = b"codex" + b"-work1"
EXPECTED_PROJECT_NAME = "agentic-evidence-lab"
EXPECTED_DISTRIBUTION_NAME = "agentic_evidence_lab"
EXPECTED_PROJECTION_POLICY = "ael.publication-projection/0.6"

WHEEL_REQUIRED_SUFFIXES = ("ael/__init__.py",)
WHEEL_REQUIRED_DIST_INFO = ("METADATA", "WHEEL", "RECORD")
SDIST_REQUIRED_SUFFIXES = (
    "pyproject.toml",
    "README.md",
    "LICENSE",
    "src/ael/__init__.py",
)


def _display_path(path: Path) -> str:
    """Use the caller's path spelling in diagnostics without resolving it."""

    return str(path)


def _normalise_member_name(name: str) -> tuple[str | None, str | None]:
    """Return a safe POSIX spelling and an error for unsafe archive names."""

    if not name:
        return None, "empty member name"
    if "\x00" in name:
        return None, "member name contains NUL"
    # Backslashes are interpreted as separators by common Windows extractors.
    # Reject them instead of trying to assign platform-specific semantics.
    if "\\" in name:
        return None, "member name contains a backslash"
    if name.startswith("/") or PurePosixPath(name).is_absolute():
        return None, "absolute member name"
    if re.match(r"^[A-Za-z]:($|/)", name):
        return None, "drive-qualified member name"

    is_directory = name.endswith("/")
    parts = name.split("/")
    if is_directory:
        parts.pop()
    if not parts or any(part in {"", ".", ".."} for part in parts):
        if any(part == ".." for part in parts):
            return None, "traversal member name"
        return None, "non-canonical member name"
    if ".." in parts:
        return None, "traversal member name"
    return "/".join(parts), None


def _forbidden_member_reason(name: str) -> str | None:
    parts = tuple(name.split("/"))
    for forbidden in FORBIDDEN_PARTS:
        needle = tuple(forbidden.split("/"))
        width = len(needle)
        if any(parts[index : index + width] == needle for index in range(len(parts) - width + 1)):
            return forbidden
    return None


def _payload_failures(member: str, payload: bytes) -> list[str]:
    failures: list[str] = []
    if (
        any(pattern.search(payload) for pattern in PERSONAL_PATH_PATTERNS)
        or WORKSPACE_MARKER in payload
    ):
        failures.append(f"personal absolute path or workspace marker: {member}")
    if PRIVATE_EVIDENCE_CANARY_PREFIX in payload:
        failures.append(f"private evidence canary leaked into archive: {member}")
    for label, pattern in SECRET_PATTERNS.items():
        if pattern.search(payload):
            failures.append(f"{label} shaped value: {member}")
    return failures


def _member_failures(archive: Path, name: str) -> tuple[str | None, list[str]]:
    normalised, name_error = _normalise_member_name(name)
    if name_error:
        return None, [f"{_display_path(archive)}: {name_error}: {name!r}"]
    assert normalised is not None
    forbidden = _forbidden_member_reason(normalised)
    if forbidden is not None:
        return None, [
            f"{_display_path(archive)}: forbidden private/generated member "
            f"({forbidden}): {normalised}"
        ]
    return normalised, []


def _zip_mode(info: zipfile.ZipInfo) -> int:
    return (info.external_attr >> 16) & 0xFFFF


def _read_zip(path: Path) -> tuple[dict[str, bytes], list[str]]:
    regular: dict[str, bytes] = {}
    failures: list[str] = []
    seen: set[str] = set()
    try:
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                name, name_failures = _member_failures(path, info.filename)
                failures.extend(name_failures)
                if name is None:
                    continue
                if name in seen:
                    failures.append(f"{_display_path(path)}: duplicate member: {name}")
                seen.add(name)

                mode = _zip_mode(info)
                member_type = stat.S_IFMT(mode)
                is_directory = info.is_dir() or info.filename.endswith("/")
                if member_type == stat.S_IFLNK:
                    failures.append(f"{_display_path(path)}: symlink member: {name}")
                    continue
                if member_type not in (0, stat.S_IFREG, stat.S_IFDIR):
                    failures.append(f"{_display_path(path)}: special member: {name}")
                    continue
                if is_directory:
                    if member_type not in (0, stat.S_IFDIR):
                        failures.append(f"{_display_path(path)}: special member: {name}")
                    continue
                if member_type == stat.S_IFDIR:
                    failures.append(f"{_display_path(path)}: directory marked as file: {name}")
                    continue
                try:
                    payload = archive.read(info)
                except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
                    failures.append(f"{_display_path(path)}: cannot read member {name}: {exc}")
                    continue
                failures.extend(_payload_failures(name, payload))
                regular[name] = payload
    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
        failures.append(f"{_display_path(path)}: cannot read wheel archive: {exc}")
    return regular, failures


def _read_tar(path: Path) -> tuple[dict[str, bytes], list[str]]:
    regular: dict[str, bytes] = {}
    failures: list[str] = []
    seen: set[str] = set()
    try:
        with tarfile.open(path, mode="r:*") as archive:
            for info in archive.getmembers():
                name, name_failures = _member_failures(path, info.name)
                failures.extend(name_failures)
                if name is None:
                    continue
                if name in seen:
                    failures.append(f"{_display_path(path)}: duplicate member: {name}")
                seen.add(name)
                if info.issym() or info.islnk():
                    failures.append(f"{_display_path(path)}: symlink/hardlink member: {name}")
                    continue
                if info.isdir():
                    continue
                if not info.isreg():
                    failures.append(f"{_display_path(path)}: special member: {name}")
                    continue
                extracted = archive.extractfile(info)
                if extracted is None:
                    failures.append(f"{_display_path(path)}: cannot read member {name}")
                    continue
                try:
                    payload = extracted.read()
                finally:
                    extracted.close()
                failures.extend(_payload_failures(name, payload))
                regular[name] = payload
    except (OSError, tarfile.TarError) as exc:
        failures.append(f"{_display_path(path)}: cannot read source archive: {exc}")
    return regular, failures


def _has_suffix(files: Iterable[str], suffix: str) -> bool:
    return any(name == suffix or name.endswith("/" + suffix) for name in files)


def _matching_suffixes(files: Iterable[str], suffix: str) -> list[str]:
    return sorted(name for name in files if name == suffix or name.endswith("/" + suffix))


def _wheel_dist_info(files: Iterable[str]) -> list[str]:
    return sorted(
        name for name in files if name.endswith(".dist-info/METADATA") and name.count("/") >= 1
    )


def _wheel_identity(
    path: Path, files: dict[str, bytes], failures: list[str]
) -> tuple[str, str] | None:
    metadata_paths = _wheel_dist_info(files)
    if len(metadata_paths) != 1:
        failures.append(
            f"{_display_path(path)}: expected one *.dist-info/METADATA member, found {len(metadata_paths)}"
        )
        return None
    metadata_path = metadata_paths[0]
    try:
        message = BytesParser(policy=policy.compat32).parsebytes(files[metadata_path])
    except (TypeError, ValueError) as exc:
        failures.append(f"{_display_path(path)}: invalid wheel METADATA: {exc}")
        return None
    name = message.get("Name")
    version = message.get("Version")
    if not name or not name.strip() or not version or not version.strip():
        failures.append(f"{_display_path(path)}: wheel METADATA has no Name or Version field")
        return None
    return name.strip(), version.strip()


def _check_wheel(
    path: Path, files: dict[str, bytes], expected_version: str, failures: list[str]
) -> None:
    for suffix in WHEEL_REQUIRED_SUFFIXES:
        if not _has_suffix(files, suffix):
            failures.append(f"{_display_path(path)}: missing required wheel file: {suffix}")

    metadata_paths = _wheel_dist_info(files)
    if metadata_paths:
        dist_info_root = metadata_paths[0].rsplit("/", 1)[0]
        for filename in WHEEL_REQUIRED_DIST_INFO:
            required = f"{dist_info_root}/{filename}"
            if required not in files:
                failures.append(f"{_display_path(path)}: missing required wheel file: {required}")
    identity = _wheel_identity(path, files, failures)
    if identity is None:
        return
    name, version = identity
    if name != EXPECTED_PROJECT_NAME:
        failures.append(
            f"{_display_path(path)}: wheel METADATA name {name!r} does not match "
            f"expected {EXPECTED_PROJECT_NAME!r}"
        )
    if version != expected_version:
        failures.append(
            f"{_display_path(path)}: wheel METADATA version {version!r} does not match "
            f"expected {expected_version!r}"
        )


def _sdist_identity(
    path: Path, files: dict[str, bytes], failures: list[str]
) -> tuple[str, str] | None:
    pyproject_paths = _matching_suffixes(files, "pyproject.toml")
    if len(pyproject_paths) != 1:
        failures.append(
            f"{_display_path(path)}: expected one pyproject.toml member, found {len(pyproject_paths)}"
        )
        return None
    pyproject_path = pyproject_paths[0]
    try:
        document = tomllib.loads(files[pyproject_path].decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        failures.append(f"{_display_path(path)}: invalid pyproject.toml: {exc}")
        return None
    project = document.get("project")
    name = project.get("name") if isinstance(project, dict) else None
    version = project.get("version") if isinstance(project, dict) else None
    if (
        not isinstance(name, str)
        or not name.strip()
        or not isinstance(version, str)
        or not version.strip()
    ):
        failures.append(f"{_display_path(path)}: pyproject.toml has no static project.name/version")
        return None
    return name.strip(), version.strip()


def _check_sdist(
    path: Path, files: dict[str, bytes], expected_version: str, failures: list[str]
) -> None:
    for suffix in SDIST_REQUIRED_SUFFIXES:
        if not _has_suffix(files, suffix):
            failures.append(f"{_display_path(path)}: missing required sdist file: {suffix}")
    identity = _sdist_identity(path, files, failures)
    if identity is None:
        return
    name, version = identity
    if name != EXPECTED_PROJECT_NAME:
        failures.append(
            f"{_display_path(path)}: sdist project name {name!r} does not match "
            f"expected {EXPECTED_PROJECT_NAME!r}"
        )
    if version != expected_version:
        failures.append(
            f"{_display_path(path)}: sdist pyproject version {version!r} does not match "
            f"expected {expected_version!r}"
        )


def _read_archive(path: Path) -> tuple[dict[str, bytes], list[str], str]:
    lowered = path.name.lower()
    if lowered.endswith(".whl"):
        files, failures = _read_zip(path)
        return files, failures, "wheel"
    if lowered.endswith(".tar.gz") or lowered.endswith(".tgz") or ".tar." in lowered:
        files, failures = _read_tar(path)
        return files, failures, "sdist"
    return {}, [f"{_display_path(path)}: unsupported archive type"], "unknown"


def _filename_failure(path: Path, archive_kind: str, expected_version: str) -> str | None:
    if archive_kind == "wheel":
        parts = path.name.split("-")
        if len(parts) < 5 or parts[0] != EXPECTED_DISTRIBUTION_NAME or parts[1] != expected_version:
            return (
                f"{_display_path(path)}: wheel filename identity does not match "
                f"expected {EXPECTED_DISTRIBUTION_NAME}-{expected_version}-*.whl"
            )
    elif archive_kind == "sdist" and not (
        path.name == f"{EXPECTED_DISTRIBUTION_NAME}-{expected_version}.tar.gz"
        or path.name == f"{EXPECTED_DISTRIBUTION_NAME}-{expected_version}.tgz"
    ):
        return (
            f"{_display_path(path)}: sdist filename identity does not match "
            f"expected {EXPECTED_DISTRIBUTION_NAME}-{expected_version}.tar.gz"
        )
    return None


def verify_archives(paths: Sequence[str | Path], expected_version: str) -> list[str]:
    """Validate supplied wheel/sdist archives and return deterministic failures."""

    failures: list[str] = []
    if not expected_version or not expected_version.strip():
        return ["expected version must not be empty"]
    archives = [Path(path) for path in paths]
    if not archives:
        return ["no release archives supplied"]
    seen_names: set[str] = set()
    for path in archives:
        if path.name in seen_names:
            failures.append(f"duplicate archive filename: {path.name}")
        seen_names.add(path.name)
    for path in sorted(archives, key=lambda item: (item.name, str(item))):
        if not path.is_file() or path.is_symlink():
            failures.append(f"{_display_path(path)}: archive path is not a regular file")
            continue
        files, archive_failures, archive_kind = _read_archive(path)
        failures.extend(archive_failures)
        filename_failure = _filename_failure(path, archive_kind, expected_version.strip())
        if filename_failure is not None:
            failures.append(filename_failure)
        if archive_kind == "wheel":
            _check_wheel(path, files, expected_version.strip(), failures)
        elif archive_kind == "sdist":
            _check_sdist(path, files, expected_version.strip(), failures)
    return sorted(set(failures))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _archive_records(archives: Sequence[str | Path]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for path in sorted((Path(item) for item in archives), key=lambda item: item.name):
        records.append(
            {
                "filename": path.name,
                "sha256": _sha256(path),
                "size_bytes": path.stat().st_size,
            }
        )
    return records


def _release_tag(version: str) -> str:
    alpha = re.fullmatch(r"([0-9]+\.[0-9]+\.[0-9]+)a([0-9]+)", version)
    if alpha is not None:
        return f"v{alpha.group(1)}-alpha.{alpha.group(2)}"
    return f"v{version}"


def write_release_metadata(
    archives: Sequence[str | Path],
    output_dir: str | Path,
    *,
    tag: str,
    commit: str,
    version: str,
    projection_policy: str,
) -> None:
    """Write deterministic checksum and release-manifest files for archives."""

    if not version.strip():
        raise ValueError("version must not be empty")
    expected_tag = _release_tag(version.strip())
    if tag != expected_tag:
        raise ValueError(f"tag must be {expected_tag} for version {version}")
    if not re.fullmatch(r"[0-9a-fA-F]{40}", commit):
        raise ValueError("commit must be a full 40-character hexadecimal SHA")
    if projection_policy != EXPECTED_PROJECTION_POLICY:
        raise ValueError(f"projection policy must be {EXPECTED_PROJECTION_POLICY}")
    paths = [Path(item) for item in archives]
    records = _archive_records(paths)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    checksums = "".join(f"{record['sha256']}  {record['filename']}\n" for record in records)
    (output / "SHA256SUMS").write_text(checksums, encoding="utf-8")
    manifest = {
        "format": "ael.release-manifest/0.1",
        "tag": tag,
        "commit": commit.lower(),
        "version": version,
        "projection_policy": projection_policy,
        "artifacts": records,
    }
    (output / "release-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-version", required=True)
    parser.add_argument("--tag")
    parser.add_argument("--commit", help="full 40-character Git SHA")
    parser.add_argument("--projection-policy")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("archives", nargs="+", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    failures = verify_archives(args.archives, args.expected_version)
    if failures:
        for failure in failures:
            print(f"release artifact check failed: {failure}", file=sys.stderr)
        return 1

    if args.output_dir is not None:
        missing = [
            option
            for option, value in (
                ("--tag", args.tag),
                ("--commit", args.commit),
                ("--projection-policy", args.projection_policy),
            )
            if value is None
        ]
        if missing:
            print(
                "release artifact check failed: --output-dir requires " + ", ".join(missing),
                file=sys.stderr,
            )
            return 2
        try:
            write_release_metadata(
                args.archives,
                args.output_dir,
                tag=args.tag,
                commit=args.commit,
                version=args.expected_version,
                projection_policy=args.projection_policy,
            )
        except (OSError, ValueError) as exc:
            print(f"release artifact check failed: cannot write metadata: {exc}", file=sys.stderr)
            return 1

    print(
        f"release artifact check passed: {len(args.archives)} archive(s); version={args.expected_version}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
