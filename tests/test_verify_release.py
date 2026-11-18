"""Offline negative and positive tests for the public GitHub release gate."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from sys import path as python_path

python_path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from verify_release import verify_release  # noqa: E402

COMMIT = "a" * 40
TAG = "diary-v0.1.0-alpha.aaaaaaaa"
MAC = "CaptainsDiary-macOS-arm64.zip"
LINUX = "CaptainsDiary-Linux-x64.zip"
WINDOWS = "CaptainsDiary-Windows-x64.zip"
INSTALLER = "install-macos-alpha.sh"


def sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


class ReleaseFixture:
    def __init__(self, root: Path, windows: bool = False):
        self.root = root
        files = {
            MAC: b"fake-macos-zip",
            LINUX: b"fake-linux-zip",
            INSTALLER: b"#!/bin/sh\n",
            "HOW-TO-TEST.md": b"Testing instructions\n",
        }
        if windows:
            files[WINDOWS] = b"fake-windows-zip"
        for name, content in files.items():
            (root / name).write_bytes(content)
        self.manifest = {
            "schema": "captains.diary.desktop-preview/v1",
            "version": "0.1.0",
            "commit": COMMIT,
            "platformRuntimeCoverage": {"macos": "native-e2e", "linux": "native-e2e"},
            "macosSigning": {
                "verified": True,
                "downloadedZipSignatureVerified": True,
                "mode": "ad-hoc",
                "gatekeeperReady": False,
            },
            "signed": False,
            "installer": {"file": INSTALLER, "sha256": sha(files[INSTALLER])},
            "packages": [
                {"platform": "macos", "file": MAC, "sha256": sha(files[MAC]), "bytes": len(files[MAC])},
                {"platform": "linux", "file": LINUX, "sha256": sha(files[LINUX]), "bytes": len(files[LINUX])},
            ],
        }
        self.save_manifest()
        self.write_sums()
        if windows:
            self.write_json("windows-attestation.json", {
                "schema": "captains.diary.windows-native-public/v1",
                "status": "PASS",
                "nativeGui": True,
                "platform": "windows-x64",
                "provenance": "kvm-windows-guest",
                "commit": COMMIT,
                "sha256": sha(files[WINDOWS]),
            })

    def write_json(self, filename: str, payload: dict) -> None:
        (self.root / filename).write_text(json.dumps(payload), encoding="utf-8")

    def save_manifest(self) -> None:
        self.write_json("manifest.json", self.manifest)

    def write_sums(self) -> None:
        files = [MAC, LINUX, INSTALLER]
        if (self.root / WINDOWS).exists():
            files.append(WINDOWS)
        (self.root / "SHA256SUMS").write_text("".join(
            f"{sha((self.root / name).read_bytes())}  {name}\n" for name in files
        ), encoding="utf-8")


class VerifyReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.fixture = ReleaseFixture(self.root)

    def test_mac_and_linux_native_alpha_pass(self):
        self.assertEqual(verify_release(self.root, TAG)["platforms"],
                         ["macos-arm64", "linux-x64"])

    def test_native_windows_pass_when_attested(self):
        self.fixture = ReleaseFixture(self.root, windows=True)
        self.assertEqual(len(verify_release(self.root, TAG)["platforms"]), 3)

    def test_unattested_windows_package_is_rejected(self):
        self.fixture = ReleaseFixture(self.root, windows=True)
        (self.root / "windows-attestation.json").unlink()
        with self.assertRaisesRegex(ValueError, "Unexpected/missing release assets"):
            verify_release(self.root, TAG)

    def test_fabricated_windows_native_pass_is_rejected(self):
        self.fixture = ReleaseFixture(self.root, windows=True)
        attestation_file = self.root / "windows-attestation.json"
        data = json.loads(attestation_file.read_text())
        data["nativeGui"] = False
        self.fixture.write_json(attestation_file.name, data)
        with self.assertRaisesRegex(ValueError, "Windows native packaged GUI evidence"):
            verify_release(self.root, TAG)

    def test_mismatched_windows_tested_binary_is_rejected(self):
        self.fixture = ReleaseFixture(self.root, windows=True)
        attestation_file = self.root / "windows-attestation.json"
        data = json.loads(attestation_file.read_text())
        data["sha256"] = "f" * 64
        self.fixture.write_json(attestation_file.name, data)
        with self.assertRaisesRegex(ValueError, "Windows native tested ZIP hash"):
            verify_release(self.root, TAG)

    def test_modified_zip_is_rejected(self):
        (self.root / MAC).write_bytes(b"modified after CI")
        with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
            verify_release(self.root, TAG)

    def test_source_sha_not_matching_tag_is_rejected(self):
        self.fixture.manifest["commit"] = "b" * 40
        self.fixture.save_manifest()
        with self.assertRaisesRegex(ValueError, "Tag and GitLab source commit differ"):
            verify_release(self.root, TAG)

    def test_missing_native_linux_gate_is_rejected(self):
        self.fixture.manifest["platformRuntimeCoverage"]["linux"] = "cross-build-only"
        self.fixture.save_manifest()
        with self.assertRaisesRegex(ValueError, "native macOS/Linux"):
            verify_release(self.root, TAG)

    def test_extra_asset_cannot_leak_private_logs(self):
        (self.root / "private-job-log.txt").write_text("do not publish")
        with self.assertRaisesRegex(ValueError, "Unexpected/missing release assets"):
            verify_release(self.root, TAG)

    def test_duplicate_checksum_line_is_rejected(self):
        sums = self.root / "SHA256SUMS"
        sums.write_text(sums.read_text() + sums.read_text().splitlines()[0] + "\n")
        with self.assertRaisesRegex(ValueError, "Duplicate SHA256SUMS"):
            verify_release(self.root, TAG)

    def test_macos_unverified_signature_is_rejected(self):
        self.fixture.manifest["macosSigning"]["verified"] = False
        self.fixture.save_manifest()
        with self.assertRaisesRegex(ValueError, "signing integrity"):
            verify_release(self.root, TAG)


if __name__ == "__main__":
    unittest.main()
