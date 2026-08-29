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
from collections.abc import Sequence
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
# Archive members are untrusted input.  Keep the extraction surface below the
# repository's public-file ceiling while permitting ordinary source releases.
MAX_ARCHIVE_MEMBERS = 10_000
MAX_ARCHIVE_MEMBER_BYTES = 2 * 1024 * 1024
MAX_ARCHIVE_TOTAL_BYTES = 32 * 1024 * 1024
_READ_CHUNK_BYTES = 64 * 1024

# AEL-CEP is a package-level feature, not an optional development fixture.
# These are archive-relative paths, deliberately not suffixes: an attacker
# must not be able to satisfy the contract with ``decoy/ael/...`` members.
WHEEL_REQUIRED_FILES = (
    "ael/__init__.py",
    "ael/contract_graph.py",
    "ael/coevolution.py",
    "ael/coevolution_bundle.py",
    "ael/coevolution_simulator.py",
    "ael/coevolution_schemas/protocol.schema.json",
    "ael/coevolution_schemas/bundle.schema.json",
)
WHEEL_REQUIRED_DIST_INFO = ("METADATA", "WHEEL", "RECORD")
SDIST_REQUIRED_FILES = (
    "pyproject.toml",
    "README.md",
    "LICENSE",
    "src/ael/__init__.py",
    "src/ael/contract_graph.py",
    "src/ael/coevolution.py",
    "src/ael/coevolution_bundle.py",
    "src/ael/coevolution_simulator.py",
    "src/ael/coevolution_schemas/protocol.schema.json",
    "src/ael/coevolution_schemas/bundle.schema.json",
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


def _bounded_read(stream: object, limit: int) -> tuple[bytes | None, str | None]:
    """Read an archive member without allocating more than ``limit`` bytes."""

    chunks: list[bytes] = []
    actual_size = 0
    try:
        while True:
            chunk = stream.read(_READ_CHUNK_BYTES)  # type: ignore[attr-defined]
            if not chunk:
                break
            actual_size += len(chunk)
            if actual_size > limit:
                return None, f"actual uncompressed member exceeds {limit} bytes"
            chunks.append(chunk)
    except (EOFError, OSError, RuntimeError, tarfile.TarError, zipfile.BadZipFile) as exc:
        return None, f"cannot read bounded member data: {exc}"
    return b"".join(chunks), None


def _declared_size_failure(path: Path, name: str, size: int, total: int) -> tuple[int, str | None]:
    if size < 0:
        return total, f"{_display_path(path)}: negative declared member size: {name}"
    if size > MAX_ARCHIVE_MEMBER_BYTES:
        return (
            total,
            f"{_display_path(path)}: declared member exceeds {MAX_ARCHIVE_MEMBER_BYTES} bytes: {name}",
        )
    next_total = total + size
    if next_total > MAX_ARCHIVE_TOTAL_BYTES:
        return (
            total,
            f"{_display_path(path)}: declared uncompressed archive total exceeds "
            f"{MAX_ARCHIVE_TOTAL_BYTES} bytes",
        )
    return next_total, None


def _read_zip(path: Path) -> tuple[dict[str, bytes], list[str]]:
    regular: dict[str, bytes] = {}
    failures: list[str] = []
    seen: set[str] = set()
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_ARCHIVE_MEMBERS:
                return regular, [
                    f"{_display_path(path)}: archive member count exceeds {MAX_ARCHIVE_MEMBERS}"
                ]
            declared_total = 0
            actual_total = 0
            for info in infos:
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
                    if info.file_size != 0:
                        failures.append(
                            f"{_display_path(path)}: directory has nonzero declared size: {name}"
                        )
                    continue
                if member_type == stat.S_IFDIR:
                    failures.append(f"{_display_path(path)}: directory marked as file: {name}")
                    continue
                declared_total, size_failure = _declared_size_failure(
                    path, name, info.file_size, declared_total
                )
                if size_failure is not None:
                    failures.append(size_failure)
                    continue
                try:
                    with archive.open(info) as stream:
                        payload, read_failure = _bounded_read(
                            stream,
                            min(MAX_ARCHIVE_MEMBER_BYTES, MAX_ARCHIVE_TOTAL_BYTES - actual_total),
                        )
                except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
                    failures.append(f"{_display_path(path)}: cannot read member {name}: {exc}")
                    continue
                if read_failure is not None:
                    failures.append(f"{_display_path(path)}: {read_failure}: {name}")
                    continue
                assert payload is not None
                if len(payload) != info.file_size:
                    failures.append(
                        f"{_display_path(path)}: declared/actual size mismatch for member {name}"
                    )
                    continue
                actual_total += len(payload)
                if actual_total > MAX_ARCHIVE_TOTAL_BYTES:
                    failures.append(
                        f"{_display_path(path)}: actual uncompressed archive total exceeds "
                        f"{MAX_ARCHIVE_TOTAL_BYTES} bytes"
                    )
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
            declared_total = 0
            actual_total = 0
            member_count = 0
            for info in archive:
                member_count += 1
                if member_count > MAX_ARCHIVE_MEMBERS:
                    failures.append(
                        f"{_display_path(path)}: archive member count exceeds {MAX_ARCHIVE_MEMBERS}"
                    )
                    break
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
                    if info.size != 0:
                        failures.append(
                            f"{_display_path(path)}: directory has nonzero declared size: {name}"
                        )
                    continue
                if not info.isreg():
                    failures.append(f"{_display_path(path)}: special member: {name}")
                    continue
                declared_total, size_failure = _declared_size_failure(
                    path, name, info.size, declared_total
                )
                if size_failure is not None:
                    failures.append(size_failure)
                    continue
                extracted = archive.extractfile(info)
                if extracted is None:
                    failures.append(f"{_display_path(path)}: cannot read member {name}")
                    continue
                try:
                    payload, read_failure = _bounded_read(
                        extracted,
                        min(MAX_ARCHIVE_MEMBER_BYTES, MAX_ARCHIVE_TOTAL_BYTES - actual_total),
                    )
                finally:
                    extracted.close()
                if read_failure is not None:
                    failures.append(f"{_display_path(path)}: {read_failure}: {name}")
                    continue
                assert payload is not None
                if len(payload) != info.size:
                    failures.append(
                        f"{_display_path(path)}: declared/actual size mismatch for member {name}"
                    )
                    continue
                actual_total += len(payload)
                if actual_total > MAX_ARCHIVE_TOTAL_BYTES:
                    failures.append(
                        f"{_display_path(path)}: actual uncompressed archive total exceeds "
                        f"{MAX_ARCHIVE_TOTAL_BYTES} bytes"
                    )
                    continue
                failures.extend(_payload_failures(name, payload))
                regular[name] = payload
    except (OSError, tarfile.TarError) as exc:
        failures.append(f"{_display_path(path)}: cannot read source archive: {exc}")
    return regular, failures


def _wheel_dist_info(files: dict[str, bytes]) -> list[str]:
    return sorted(
        name for name in files if name.endswith(".dist-info/METADATA") and name.count("/") >= 1
    )


def _wheel_dist_info_root(expected_version: str) -> str:
    return f"{EXPECTED_DISTRIBUTION_NAME}-{expected_version}.dist-info"


def _wheel_identity(
    path: Path, files: dict[str, bytes], expected_version: str, failures: list[str]
) -> tuple[str, str] | None:
    metadata_paths = _wheel_dist_info(files)
    expected_metadata = f"{_wheel_dist_info_root(expected_version)}/METADATA"
    if metadata_paths != [expected_metadata]:
        failures.append(
            f"{_display_path(path)}: expected exactly one canonical wheel METADATA member "
            f"{expected_metadata}, found {metadata_paths}"
        )
        return None
    try:
        message = BytesParser(policy=policy.compat32).parsebytes(files[expected_metadata])
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
    for required in WHEEL_REQUIRED_FILES:
        if required not in files:
            failures.append(f"{_display_path(path)}: missing required wheel file: {required}")

    dist_info_root = _wheel_dist_info_root(expected_version)
    for filename in WHEEL_REQUIRED_DIST_INFO:
        required = f"{dist_info_root}/{filename}"
        if required not in files:
            failures.append(f"{_display_path(path)}: missing required wheel file: {required}")
    identity = _wheel_identity(path, files, expected_version, failures)
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


def _sdist_root(
    path: Path, files: dict[str, bytes], expected_version: str, failures: list[str]
) -> str | None:
    expected_root = f"{EXPECTED_DISTRIBUTION_NAME}-{expected_version}"
    roots = sorted({name.split("/", 1)[0] for name in files})
    if roots != [expected_root]:
        failures.append(
            f"{_display_path(path)}: expected exactly one canonical sdist root "
            f"{expected_root}, found {roots}"
        )
        return None
    return expected_root


def _sdist_identity(
    path: Path, files: dict[str, bytes], root: str, failures: list[str]
) -> tuple[str, str] | None:
    pyproject_path = f"{root}/pyproject.toml"
    if pyproject_path not in files:
        failures.append(f"{_display_path(path)}: missing required sdist file: pyproject.toml")
        return None
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
    root = _sdist_root(path, files, expected_version, failures)
    if root is None:
        return
    for required_suffix in SDIST_REQUIRED_FILES:
        required = f"{root}/{required_suffix}"
        if required not in files:
            failures.append(
                f"{_display_path(path)}: missing required sdist file: {required_suffix}"
            )
    identity = _sdist_identity(path, files, root, failures)
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
