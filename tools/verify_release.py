#!/usr/bin/env python3
"""Fail-closed verifier for public Captain's Diary GitHub release assets.

Run locally or in GitHub Actions; stdlib only, no access to private GitLab needed.
The GitLab publisher MUST perform these checks before making a draft public.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

MAC = "CaptainsDiary-macOS-arm64.zip"
LINUX = "CaptainsDiary-Linux-x64.zip"
WINDOWS = "CaptainsDiary-Windows-x64.zip"
INSTALLER = "install-macos-alpha.sh"
BASE_ASSETS = {MAC, LINUX, INSTALLER, "SHA256SUMS", "manifest.json", "HOW-TO-TEST.md"}
WINDOWS_ASSETS = {WINDOWS, "windows-attestation.json"}
TAG_PATTERN = re.compile(r"diary-v(?P<version>\d+\.\d+\.\d+)-alpha\.(?P<sha>[0-9a-f]{8,12})")
SUM_PATTERN = re.compile(r"([0-9a-f]{64})  ([A-Za-z0-9][A-Za-z0-9._-]*)")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read_json(location: Path) -> dict:
    document = json.loads(location.read_text(encoding="utf-8"))
    require(isinstance(document, dict), f"{location.name}: expected JSON object")
    return document


def digest(location: Path) -> str:
    h = hashlib.sha256()
    with location.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def checksums(location: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in location.read_text(encoding="utf-8").splitlines():
        match = SUM_PATTERN.fullmatch(line)
        require(match is not None, "Malformed SHA256SUMS record")
        sha, filename = match.groups()
        require(filename not in entries, f"Duplicate SHA256SUMS record: {filename}")
        entries[filename] = sha
    return entries


def verify_release(directory: Path, tag: str) -> dict:
    match = TAG_PATTERN.fullmatch(tag)
    require(match is not None, "Only immutable diary-vX.Y.Z-alpha.SHA tags are supported")
    require(directory.is_dir(), f"Release assets directory not found: {directory}")

    names = {file.name for file in directory.iterdir() if file.is_file()}
    require(all(not file.is_symlink() for file in directory.iterdir()), "Symlink in release assets")
    has_windows = bool(names & WINDOWS_ASSETS)
    expected_assets = BASE_ASSETS | (WINDOWS_ASSETS if has_windows else set())
    require(names == expected_assets, f"Unexpected/missing release assets: {sorted(names ^ expected_assets)}")

    manifest = read_json(directory / "manifest.json")
    require(manifest.get("schema") == "captains.diary.desktop-preview/v1", "Unsupported manifest schema")
    require(manifest.get("version") == match.group("version"), "Tag version and manifest version differ")
    source = manifest.get("commit")
    require(isinstance(source, str) and re.fullmatch(r"[0-9a-f]{40}", source),
            "Source must be an exact 40-character GitLab commit")
    require(source.startswith(match.group("sha")), "Tag and GitLab source commit differ")
    runtime = manifest.get("platformRuntimeCoverage")
    require(isinstance(runtime, dict) and runtime.get("macos") == "native-e2e"
            and runtime.get("linux") == "native-e2e", "Missing native macOS/Linux runtime evidence")
    signing = manifest.get("macosSigning")
    require(isinstance(signing, dict) and signing.get("verified") is True
            and signing.get("downloadedZipSignatureVerified") is True,
            "macOS distributable signing integrity not verified")
    require(signing.get("mode") in {"ad-hoc", "developer-id-notarized"}, "Unknown macOS signing mode")
    require(manifest.get("signed") is (signing.get("gatekeeperReady") is True),
            "macOS Gatekeeper state mismatch")

    packages = manifest.get("packages")
    require(isinstance(packages, list) and len(packages) == 2, "Expected two native package receipts")
    by_platform = {item.get("platform"): item for item in packages if isinstance(item, dict)}
    require(set(by_platform) == {"macos", "linux"}, "Platform receipts missing or duplicated")
    require(by_platform["macos"].get("file") == MAC and by_platform["linux"].get("file") == LINUX,
            "Unexpected package filenames")

    installer = manifest.get("installer")
    require(isinstance(installer, dict) and installer.get("file") == INSTALLER,
            "Missing installer receipt")

    sums = checksums(directory / "SHA256SUMS")
    names_to_hash = {MAC, LINUX, INSTALLER} | ({WINDOWS} if has_windows else set())
    require(set(sums) == names_to_hash, "Unexpected/missing SHA256SUMS entries")
    for name in names_to_hash:
        require(sums[name] == digest(directory / name), f"SHA256 mismatch: {name}")
    for platform in ("macos", "linux"):
        item = by_platform[platform]
        name = item["file"]
        require(item.get("sha256") == sums[name], f"Manifest hash mismatch: {name}")
        require(item.get("bytes") == (directory / name).stat().st_size,
                f"Manifest byte count mismatch: {name}")
    require(installer.get("sha256") == sums[INSTALLER], "Installer hash mismatch")

    if has_windows:
        attestation = read_json(directory / "windows-attestation.json")
        require(attestation.get("schema") == "captains.diary.windows-native-public/v1",
                "Unexpected public Windows attestation schema")
        require(attestation.get("status") == "PASS" and attestation.get("nativeGui") is True
                and attestation.get("platform") == "windows-x64"
                and attestation.get("provenance") == "kvm-windows-guest",
                "Windows native packaged GUI evidence is missing")
        require(attestation.get("commit") == source, "Windows source SHA differs")
        require(attestation.get("sha256") == sums[WINDOWS], "Windows native tested ZIP hash differs")
        require((directory / WINDOWS).stat().st_size > 0, "Windows package is empty")

    return {"status": "PASS", "tag": tag, "sourceCommit": source,
            "platforms": ["macos-arm64", "linux-x64"] + (["windows-x64"] if has_windows else []),
            "macosNotarized": signing.get("gatekeeperReady") is True}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", type=Path, required=True)
    parser.add_argument("--tag", required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(verify_release(args.dir, args.tag), sort_keys=True))
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        parser.exit(1, f"Release verification FAIL: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
