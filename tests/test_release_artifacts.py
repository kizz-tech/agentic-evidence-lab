from __future__ import annotations

import hashlib
import io
import json
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from ael.result_surface import PUBLICATION_PROJECTION_POLICY
from tools import verify_release_artifacts as release_artifacts
from tools.verify_release_artifacts import (
    EXPECTED_PROJECTION_POLICY,
    main,
    verify_archives,
    write_release_metadata,
)

VERSION = "0.1.0a9"


def _wheel(path: Path, *, payload: bytes = b"", extra: dict[str, bytes] | None = None) -> None:
    files = {
        "ael/__init__.py": b'__version__ = "0.1.0a9"\n',
        "ael/contract_graph.py": b"# graph validator\n",
        "ael/coevolution.py": b"# protocol kernel\n",
        "ael/coevolution_bundle.py": b"# file adapter\n",
        "ael/coevolution_simulator.py": b"# no-effect simulator\n",
        "ael/coevolution_schemas/protocol.schema.json": b"{}\n",
        "ael/coevolution_schemas/bundle.schema.json": b"{}\n",
        "agentic_evidence_lab-0.1.0a9.dist-info/METADATA": (
            b"Metadata-Version: 2.3\nName: agentic-evidence-lab\nVersion: 0.1.0a9\n"
        ),
        "agentic_evidence_lab-0.1.0a9.dist-info/WHEEL": b"Wheel-Version: 1.0\n",
        "agentic_evidence_lab-0.1.0a9.dist-info/RECORD": b"",
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
    root = "agentic_evidence_lab-0.1.0a9"
    files = {
        "pyproject.toml": b'[project]\nname = "agentic-evidence-lab"\nversion = "0.1.0a9"\n',
        "README.md": b"Public README\n",
        "LICENSE": b"Apache-2.0\n",
        "src/ael/__init__.py": b'__version__ = "0.1.0a9"\n',
        "src/ael/contract_graph.py": b"# graph validator\n",
        "src/ael/coevolution.py": b"# protocol kernel\n",
        "src/ael/coevolution_bundle.py": b"# file adapter\n",
        "src/ael/coevolution_simulator.py": b"# no-effect simulator\n",
        "src/ael/coevolution_schemas/protocol.schema.json": b"{}\n",
        "src/ael/coevolution_schemas/bundle.schema.json": b"{}\n",
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
            wheel = root / "agentic_evidence_lab-0.1.0a9-py3-none-any.whl"
            sdist = root / "agentic_evidence_lab-0.1.0a9.tar.gz"
            _wheel(wheel)
            _sdist(sdist)
            self.assertEqual([], verify_archives([sdist, wheel], VERSION))

            output = root / "metadata"
            write_release_metadata(
                [sdist, wheel],
                output,
                tag="v0.1.0-alpha.9",
                commit="A" * 40,
                version=VERSION,
                projection_policy="ael.publication-projection/0.6",
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
            wheel = root / "agentic_evidence_lab-0.1.0a9-py3-none-any.whl"
            _wheel(wheel)
            for tag, policy, message in (
                (
                    "v0.1.0-alpha.6",
                    "ael.publication-projection/0.6",
                    "tag must be v0.1.0-alpha.9",
                ),
                (
                    "v0.1.0-alpha.9",
                    "ael.publication-projection/0.3",
                    "projection policy must be ael.publication-projection/0.6",
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
                extra={"agentic_evidence_lab-0.1.0a9/.env": b"private"},
            )
            failures = verify_archives([archive], VERSION)
            self.assertTrue(any("forbidden private/generated member" in item for item in failures))
            self.assertTrue(any("personal absolute path" in item for item in failures))
            self.assertTrue(any("OpenAI-style API key" in item for item in failures))
            self.assertTrue(any("AWS-style access key" in item for item in failures))
            self.assertTrue(any("signed URL query" in item for item in failures))

    def test_container_home_path_is_not_treated_as_personal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "agentic_evidence_lab-0.1.0a9-py3-none-any.whl"
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
                info = tarfile.TarInfo("agentic_evidence_lab-0.1.0a9/src/ael/link")
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
                        payload = payload.replace(b"Version: 0.1.0a9", b"Version: 0.1.0a4")
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

    def test_ael_cep_modules_and_schema_resources_are_required(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wheel = root / "agentic_evidence_lab-0.1.0a9-py3-none-any.whl"
            _wheel(wheel)
            removed = root / "without-protocol-schema.whl"
            with zipfile.ZipFile(wheel) as source, zipfile.ZipFile(removed, "w") as target:
                for info in source.infolist():
                    if info.filename.endswith("coevolution_schemas/protocol.schema.json"):
                        continue
                    target.writestr(info, source.read(info))
            failures = verify_archives([removed], VERSION)
            self.assertTrue(
                any(
                    "missing required wheel file: ael/coevolution_schemas/protocol.schema.json"
                    in item
                    for item in failures
                )
            )

            sdist = root / "agentic_evidence_lab-0.1.0a9.tar.gz"
            _sdist(sdist)
            without_module = root / "without-bundle-module.tar.gz"
            with (
                tarfile.open(sdist, "r:gz") as source,
                tarfile.open(without_module, "w:gz") as target,
            ):
                for member in source.getmembers():
                    if member.name.endswith("src/ael/coevolution_bundle.py"):
                        continue
                    if member.isfile():
                        payload = source.extractfile(member)
                        assert payload is not None
                        with payload:
                            target.addfile(member, payload)
                    else:
                        target.addfile(member)
            failures = verify_archives([without_module], VERSION)
            self.assertTrue(
                any(
                    "missing required sdist file: src/ael/coevolution_bundle.py" in item
                    for item in failures
                )
            )

    def test_decoy_suffixes_cannot_satisfy_canonical_archive_contract(self) -> None:
        """A matching suffix under an attacker-controlled prefix is not evidence."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wheel = root / "agentic_evidence_lab-0.1.0a9-py3-none-any.whl"
            _wheel(wheel)
            forged_wheel = root / "forged-wheel.whl"
            with zipfile.ZipFile(wheel) as source, zipfile.ZipFile(forged_wheel, "w") as target:
                for info in source.infolist():
                    if info.filename == "ael/coevolution_bundle.py":
                        continue
                    target.writestr(info, source.read(info))
                target.writestr("decoy/ael/coevolution_bundle.py", b"# decoy\n")
            failures = verify_archives([forged_wheel], VERSION)
            self.assertTrue(
                any(
                    "missing required wheel file: ael/coevolution_bundle.py" in item
                    for item in failures
                )
            )

            sdist = root / "agentic_evidence_lab-0.1.0a9.tar.gz"
            _sdist(sdist)
            forged_sdist = root / "forged-sdist.tar.gz"
            with (
                tarfile.open(sdist, "r:gz") as source,
                tarfile.open(forged_sdist, "w:gz") as target,
            ):
                for member in source.getmembers():
                    if member.name.endswith("src/ael/coevolution_bundle.py"):
                        continue
                    if member.isfile():
                        payload = source.extractfile(member)
                        assert payload is not None
                        with payload:
                            target.addfile(member, payload)
                    else:
                        target.addfile(member)
                payload = b"# decoy\n"
                info = tarfile.TarInfo("decoy/src/ael/coevolution_bundle.py")
                info.size = len(payload)
                target.addfile(info, io.BytesIO(payload))
            failures = verify_archives([forged_sdist], VERSION)
            self.assertTrue(
                any("expected exactly one canonical sdist root" in item for item in failures)
            )

    def test_archive_expansion_limits_fail_closed_for_zip_and_tar(self) -> None:
        """Small fixtures exercise declared bytes, total bytes, and member caps."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wheel = root / "agentic_evidence_lab-0.1.0a9-py3-none-any.whl"
            sdist = root / "agentic_evidence_lab-0.1.0a9.tar.gz"
            _wheel(wheel, payload=b"12345")
            _sdist(sdist, payload=b"12345")

            with patch.object(release_artifacts, "MAX_ARCHIVE_MEMBER_BYTES", 4):
                for archive in (wheel, sdist):
                    with self.subTest(archive=archive.name, limit="member"):
                        failures = verify_archives([archive], VERSION)
                        self.assertTrue(
                            any("declared member exceeds 4 bytes" in item for item in failures)
                        )

            with patch.object(release_artifacts, "MAX_ARCHIVE_TOTAL_BYTES", 4):
                for archive in (wheel, sdist):
                    with self.subTest(archive=archive.name, limit="total"):
                        failures = verify_archives([archive], VERSION)
                        self.assertTrue(
                            any(
                                "declared uncompressed archive total exceeds 4 bytes" in item
                                for item in failures
                            )
                        )

            with patch.object(release_artifacts, "MAX_ARCHIVE_MEMBERS", 2):
                for archive in (wheel, sdist):
                    with self.subTest(archive=archive.name, limit="members"):
                        failures = verify_archives([archive], VERSION)
                        self.assertTrue(
                            any("archive member count exceeds 2" in item for item in failures)
                        )

    def test_cli_requires_metadata_options_when_output_requested(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "agentic_evidence_lab-0.1.0a9-py3-none-any.whl"
            _wheel(archive)
            result = main(["--expected-version", VERSION, "--output-dir", directory, str(archive)])
            self.assertEqual(2, result)


if __name__ == "__main__":
    unittest.main()
