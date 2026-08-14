from __future__ import annotations

import hashlib
import io
import json
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path

from ael.result_surface import PUBLICATION_PROJECTION_POLICY
from tools.verify_release_artifacts import (
    EXPECTED_PROJECTION_POLICY,
    main,
    verify_archives,
    write_release_metadata,
)

VERSION = "0.1.0a7"


def _wheel(path: Path, *, payload: bytes = b"", extra: dict[str, bytes] | None = None) -> None:
    files = {
        "ael/__init__.py": b'__version__ = "0.1.0a7"\n',
        "agentic_evidence_lab-0.1.0a7.dist-info/METADATA": (
            b"Metadata-Version: 2.3\nName: agentic-evidence-lab\nVersion: 0.1.0a7\n"
        ),
        "agentic_evidence_lab-0.1.0a7.dist-info/WHEEL": b"Wheel-Version: 1.0\n",
        "agentic_evidence_lab-0.1.0a7.dist-info/RECORD": b"",
    }
    if payload:
        files["ael/payload.txt"] = payload
    files.update(extra or {})
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, value in files.items():
            archive.writestr(name, value)


def _sdist(
    path: Path, *, payload: bytes = b"", extra: list[tuple[str, bytes]] | None = None
) -> None:
    root = "agentic_evidence_lab-0.1.0a7"
    files = {
        "pyproject.toml": b'[project]\nname = "agentic-evidence-lab"\nversion = "0.1.0a7"\n',
        "README.md": b"Public README\n",
        "LICENSE": b"Apache-2.0\n",
        "src/ael/__init__.py": b'__version__ = "0.1.0a7"\n',
    }
    if payload:
        files["src/ael/payload.txt"] = payload
    with tarfile.open(path, "w:gz") as archive:
        for name, value in files.items():
            info = tarfile.TarInfo(f"{root}/{name}")
            info.size = len(value)
            archive.addfile(info, io.BytesIO(value))
        for name, value in extra or []:
            info = tarfile.TarInfo(f"{root}/{name}")
            info.size = len(value)
            archive.addfile(info, io.BytesIO(value))


class ReleaseArtifactTests(unittest.TestCase):
    def test_release_projection_policy_matches_generator(self) -> None:
        self.assertEqual(PUBLICATION_PROJECTION_POLICY, EXPECTED_PROJECTION_POLICY)

    def test_safe_wheel_and_sdist_pass_and_metadata_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wheel = root / "agentic_evidence_lab-0.1.0a7-py3-none-any.whl"
            sdist = root / "agentic_evidence_lab-0.1.0a7.tar.gz"
            _wheel(wheel)
            _sdist(sdist)
            self.assertEqual([], verify_archives([sdist, wheel], VERSION))

            output = root / "metadata"
            write_release_metadata(
                [sdist, wheel],
                output,
                tag="v0.1.0-alpha.7",
                commit="A" * 40,
                version=VERSION,
                projection_policy="ael.publication-projection/0.4",
            )
            manifest = json.loads((output / "release-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual("ael.release-manifest/0.1", manifest["format"])
            self.assertEqual("a" * 40, manifest["commit"])
            self.assertEqual(
                sorted((sdist.name, wheel.name)),
                [item["filename"] for item in manifest["artifacts"]],
            )
            self.assertNotIn("created_at", manifest)
            checksums = (output / "SHA256SUMS").read_text(encoding="utf-8")
            self.assertEqual(
                checksums,
                "".join(
                    f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n"
                    for path in sorted((sdist, wheel), key=lambda item: item.name)
                ),
            )

    def test_release_metadata_rejects_tag_or_projection_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wheel = root / "agentic_evidence_lab-0.1.0a7-py3-none-any.whl"
            _wheel(wheel)
            for tag, policy, message in (
                (
                    "v0.1.0-alpha.6",
                    "ael.publication-projection/0.4",
                    "tag must be v0.1.0-alpha.7",
                ),
                (
                    "v0.1.0-alpha.7",
                    "ael.publication-projection/0.3",
                    "projection policy must be ael.publication-projection/0.4",
                ),
            ):
                with (
                    self.subTest(tag=tag, policy=policy),
                    self.assertRaisesRegex(ValueError, message),
                ):
                    write_release_metadata(
                        [wheel],
                        root / "metadata",
                        tag=tag,
                        commit="a" * 40,
                        version=VERSION,
                        projection_policy=policy,
                    )

    def test_payload_patterns_and_forbidden_members_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "bad.whl"
            _wheel(
                archive,
                payload=(
                    b"/Users/private codex" + b"-work1 sk-" + b"12345678901234567890 "
                    b"AKIA" + b"ABCDEFGHIJKLMNOP "
                    b"X-Amz-Sig" + b"nature=abcdef0123456789 "
                    b"/" + b"home/private/ C:\\Users" + b"\\private\\"
                ),
                extra={"agentic_evidence_lab-0.1.0a7/.env": b"private"},
            )
            failures = verify_archives([archive], VERSION)
            self.assertTrue(any("forbidden private/generated member" in item for item in failures))
            self.assertTrue(any("personal absolute path" in item for item in failures))
            self.assertTrue(any("OpenAI-style API key" in item for item in failures))
            self.assertTrue(any("AWS-style access key" in item for item in failures))
            self.assertTrue(any("signed URL query" in item for item in failures))

    def test_container_home_path_is_not_treated_as_personal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "agentic_evidence_lab-0.1.0a7-py3-none-any.whl"
            _wheel(archive, payload=b"/workspace/home/container/project.txt")
            self.assertEqual([], verify_archives([archive], VERSION))

    def test_archive_paths_and_special_entries_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            traversal = root / "traversal.whl"
            _wheel(traversal, extra={"../outside.txt": b"x"})
            self.assertTrue(
                any("traversal" in item for item in verify_archives([traversal], VERSION))
            )

            symlink = root / "symlink.tar.gz"
            source = root / "source.tar.gz"
            _sdist(source)
            with (
                tarfile.open(source, "r:gz") as source_archive,
                tarfile.open(symlink, "w:gz") as archive,
            ):
                for member in source_archive.getmembers():
                    if member.isfile():
                        archive.addfile(member, source_archive.extractfile(member))
                info = tarfile.TarInfo("agentic_evidence_lab-0.1.0a7/src/ael/link")
                info.type = tarfile.SYMTYPE
                info.linkname = "/Users" + "/private"
                archive.addfile(info)
            self.assertTrue(any("symlink" in item for item in verify_archives([symlink], VERSION)))

    def test_versions_and_required_files_are_checked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wheel = root / "mismatch.whl"
            _wheel(wheel)
            rewritten = root / "rewritten.whl"
            with zipfile.ZipFile(wheel) as source, zipfile.ZipFile(rewritten, "w") as target:
                for info in source.infolist():
                    payload = source.read(info)
                    if info.filename.endswith("METADATA"):
                        payload = payload.replace(b"Version: 0.1.0a7", b"Version: 0.1.0a4")
                    target.writestr(info, payload)
            failures = verify_archives([rewritten], VERSION)
            self.assertTrue(any("does not match expected" in item for item in failures))

            wrong_name = root / "agentic_evidence_lab-0.1.0a4-py3-none-any.whl"
            _wheel(wrong_name)
            self.assertTrue(
                any(
                    "wheel filename identity" in item
                    for item in verify_archives([wrong_name], VERSION)
                )
            )

            missing = root / "missing.tar.gz"
            _sdist(missing, extra=[("src/ael/LICENSE", b"wrong location")])
            with tarfile.open(missing, "r:gz") as archive:
                members = [
                    member
                    for member in archive.getmembers()
                    if not member.name.endswith("/LICENSE")
                ]
                payloads = {
                    member.name: archive.extractfile(member).read()
                    for member in members
                    if member.isfile()
                }
            replacement = root / "missing2.tar.gz"
            with tarfile.open(replacement, "w:gz") as archive:
                for name, payload in payloads.items():
                    info = tarfile.TarInfo(name)
                    info.size = len(payload)
                    archive.addfile(info, io.BytesIO(payload))
            self.assertTrue(
                any(
                    "missing required sdist file: LICENSE" in item
                    for item in verify_archives([replacement], VERSION)
                )
            )

    def test_cli_requires_metadata_options_when_output_requested(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "agentic_evidence_lab-0.1.0a7-py3-none-any.whl"
            _wheel(archive)
            result = main(["--expected-version", VERSION, "--output-dir", directory, str(archive)])
            self.assertEqual(2, result)


if __name__ == "__main__":
    unittest.main()
