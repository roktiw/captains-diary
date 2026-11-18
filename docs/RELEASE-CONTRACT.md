# Captain's Diary — GitLab DEV → GitHub PROD release contract

**Decision, 2026-11-18.** `roktiw/captains-diary` in **private GitLab** is the only development source of truth. Public `roktiw/captains-diary` on **GitHub** is the production *distribution* endpoint, not a working source mirror. Do not paste proprietary files, secrets, logs, user workspaces, or private CI artifacts into GitHub.

## Exact release boundary

```text
GitLab main (protected)
  → testsuite, native macOS ARM64 package/smoke, native Linux x64 package/smoke
  → download:apps (checked ZIPs + manifest + SHA256SUMS)
  → optional: Linux Windows-x64 cross-package → Windows guest handoff
              → real Windows VM interactive packaged GUI smoke, same commit + ZIP
  → explicit protected/manual publish:github promotion
  → GitHub draft prerelease → immutable uploaded binaries + evidence
  → publish only after hashes / exact asset set verified
  → GitHub Actions release:published read-only verifier
```

The GitHub release tag is a **distribution record**, not the original application source commit: `diary-v<package-version>-alpha.<first-8-to-12-hex-of-GitLab-SHA>`. The exact **40-hex GitLab commit** and private GitLab pipeline URL are recorded in `manifest.json`. Never treat the GitHub tag's commit as evidence for the application's source.

## Supported package artifacts

| Target | Public prerelease payload | Required runtime gate | Stable release requirement |
| --- | --- | --- | --- |
| macOS ARM64 | `CaptainsDiary-macOS-arm64.zip` | Packaged GUI E2E on native Apple Silicon, signature verification on final ZIP | Developer ID signing, notarization/stapling, friendly DMG or PKG |
| Linux x64 | `CaptainsDiary-Linux-x64.zip` | Packaged GUI E2E on native Linux under Xvfb | Installer packaging (e.g. AppImage and/or DEB), installation checks |
| Windows x64 | `CaptainsDiary-Windows-x64.zip` | Real Windows VM interactive GUI E2E for the same ZIP SHA and GitLab commit | Authenticode signing, verified Windows installer (MSI or MSIX) |

**Current status is pre-alpha.** macOS ZIPs can be ad-hoc signed; these are **not** Gatekeeper-ready. Windows cross-builds on Linux do **not** satisfy the Windows runtime gate. Do not promote Windows on the basis of PE signatures or ZIP structure alone.

## Release asset allowlist

Always required:

- `CaptainsDiary-macOS-arm64.zip`
- `CaptainsDiary-Linux-x64.zip`
- `SHA256SUMS` — checksum record for each released ZIP and macOS installer, exactly once
- `manifest.json` — version, exact GitLab SHA, native macOS/Linux receipts, macOS final-ZIP signature evidence
- `HOW-TO-TEST.md`
- `install-macos-alpha.sh`

When (and only when) Windows has passed its native gate on the identical source commit and binary SHA:

- `CaptainsDiary-Windows-x64.zip`
- `windows-attestation.json` with **sanitized**, minimal `schema`, `status`, `nativeGui`, `platform`, `provenance`, `commit`, `sha256` fields. The source Windows `windows-vm-result.json` stays private.

The public Python verifier rejects unknown files, changed checksums, mismatched platform/source receipts, and claims of Windows GUI validation without a matching attestation. The GitLab publisher performs equivalent checks **before** public release; the GitHub workflow runs again on `release:published`, which is a post-publication audit, not a substitute for promotion gating.

## Required operator controls

1. Keep GitLab `main` protected, reconcile active editor merge requests and secure local-write P0 findings. Require one successful `main` pipeline for the **same** 40-character SHA and preserve its evidence.
2. Create a **fine-grained GitHub token** scoped exclusively to `roktiw/captains-diary`, with **Contents: Read and Write**. Store as protected, masked GitLab `GITHUB_RELEASE_TOKEN`. Do not use a token for `roktiw/roktiw.github.io`, a broad classic token, or a personal PAT stored in a file. Rotate on exposure.
3. `publish:github` must be a **manual** job on protected `main` with explicit `CAPTAINS_DIARY_GITHUB_PUBLISH=1`. Confirm the exact GitLab commit, license/provenance, P0 acceptance, manifest, app behavior and released version before running.
4. Windows inclusion must additionally require `CAPTAINS_DIARY_RELEASE_WINDOWS=1` and `CAPTAINS_DIARY_WINDOWS_VM_E2E=1`, with successful matching `test:windows-vm` job and receipt. Missing guest/failed test = **HOLD**; do not silently label the cross-built ZIP validated.
5. Only create a GitHub **draft** first. Upload an exact allowlist and compare remote SHA256 asset digests. If uploads fail, leave the release draft and fail. Publish a prerelease only after complete verification. Never replace an already published asset under the same tag.
6. Review the GitHub Actions read-only release verifier result. If it fails, unpublish/quarantine the release and investigate before directing users to it. GitHub branch rules/release permissions require separate repository configuration.

## Acceptance checklist

- [ ] GitHub public policy PR reviewed and merged.
- [ ] GitLab publisher MR reviewed, merged and all release-policy unit tests green.
- [ ] GitHub target-scoped token configured protected + masked on GitLab.
- [ ] GitLab P0 durability/HTTP security and manual dogfooding acceptance documented for exact SHA.
- [ ] Successful native macOS and Linux package+GUI E2E jobs for the exact source SHA.
- [ ] Successful native Windows VM GUI smoke and matching sanitized receipt (required for Windows promotion).
- [ ] Manual promotion produces a fully populated prerelease with verified SHA256, **not** a release with missing assets.
- [ ] GitHub post-publish integrity workflow green.
- [ ] For stable (non-alpha): trusted signing/notarization and actual installers on all advertised systems.

No token, Windows VM guest, Apple Developer ID certificate or code-signing secrets belong in this repository.
