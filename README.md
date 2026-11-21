# Captain's Diary — Desktop Releases

This is the **public production distribution repository** for Captain's Diary, a local-first Markdown and Living Specification IDE.

- **Development and source of truth:** private [GitLab `roktiw/captains-diary`](https://gitlab.com/roktiw/captains-diary) (merge requests, tests and native platform builds).
- **Public downloads:** [GitHub Releases](https://github.com/roktiw/captains-diary/releases) (only explicitly promoted, verified build artifacts).
- **This repository is not the development source mirror.** A release tag in this repository identifies a distribution record; the *exact GitLab source commit* and pipeline URL are recorded in each release manifest.

## Desktop targets

| Platform | Initial artifact | Current release gate |
| --- | --- | --- |
| macOS Apple Silicon (arm64) | `CaptainsDiary-macOS-arm64.zip` | Native packaged GUI smoke; currently ad-hoc signed, not Apple-notarized |
| Linux x64 | `CaptainsDiary-Linux-x64.zip` | Native packaged GUI smoke under Xvfb |
| Windows x64 | `CaptainsDiary-Windows-x64.zip` | **HOLD** until a real Windows VM completes packaged GUI tests |

Portable ZIPs are the *initial packaging format*, **not** DMG/MSI/AppImage installers. Stable end-user releases will require additional signing, notarization and installer work. Windows cross-compilation on Linux alone does not count as a Windows test.

## GitHub-hosted builds (manual, fail-closed)

GitHub Actions can build and natively smoke-test the protected **private GitLab**
source on macOS ARM64, Linux x64, and Windows x64 without mirroring source
into this public repository. It requires a project-scoped GitLab read-only
deploy token stored in GitHub Actions secrets and an exact GitLab main SHA.
The workflow publishes **sanitized JSON receipts only**, never unreviewed
Electron ZIPs. Read the [setup and runbook](docs/GITHUB-NATIVE-BUILD.md), then
[run the native build](https://github.com/roktiw/captains-diary/actions/workflows/native-desktop-build.yml).


## Download safely

1. Open [Releases](https://github.com/roktiw/captains-diary/releases) and select a published release. Until the first approved promotion there are no downloads.
2. Download your OS ZIP and the matching `SHA256SUMS` and `manifest.json`.
3. Verify checksums before extracting:
   - macOS / Linux: `shasum -a 256 -c SHA256SUMS` or `sha256sum -c SHA256SUMS` (verify only the downloaded entries).
   - Windows PowerShell: `(Get-FileHash .\\CaptainsDiary-Windows-x64.zip -Algorithm SHA256).Hash`, then compare to `SHA256SUMS`.
4. Test prereleases on a **copy** of your documents. Keep backups. Do not disable OS security globally.

A checksum proves integrity relative to the release manifest; it is not independent publisher authentication.

## Release policy

Production promotion is **manual and fail-closed**. GitLab builds, tests, and verifies packages; GitHub receives only approved assets and evidence. A GitHub release is initially created as a draft, populated, and published only after verification. Windows is never advertised as tested without a native Windows result for the exact GitLab commit and ZIP SHA256.

See [release contract](docs/RELEASE-CONTRACT.md) and the GitHub release-verification workflow. The project remains pre-alpha until the documented durability/security acceptance gates are closed.

**Security note:** Do not submit personal documents, application data, credentials or private GitLab job logs to this public repository.
