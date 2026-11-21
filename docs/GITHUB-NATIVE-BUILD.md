# GitHub-hosted native builds — Captain's Diary

**Status: build-only pilot; no automatic release and no source-code mirror.**

The canonical development repository remains **private GitLab** `roktiw/captains-diary`.
The public GitHub `roktiw/captains-diary` repository contains release policy and
a manual workflow that **clones the private GitLab source into an ephemeral
GitHub-hosted runner**. It never commits source into this public GitHub repository.

## One-time repository setup

At GitHub → `roktiw/captains-diary` → **Settings → Secrets and variables →
Actions**, create these **repository secrets**:

| Secret | Value | Permissions |
| --- | --- | --- |
| `DIARY_GITLAB_READ_USER` | Username of a GitLab *project deploy token* | No extra permission |
| `DIARY_GITLAB_READ_TOKEN` | Its secret token value | **read_repository only** for private `roktiw/captains-diary` |

Do **not** use an owner-wide GitLab PAT, a write token, an interactive personal
password, a secret in workflow YAML, or a reusable token from another project.
Never share token values in PRs or logs. Restrict who can edit workflows on this
public repository and enable branch protection / required reviews. The credential
is scoped to a single clone step; subsequent `bun install` and application scripts
do not receive it.

## Run one exact build

1. In **GitLab**, identify the full 40-hex **HEAD of protected `main`** after CI
   has completed. Do not copy a SHA from a pending MR branch.
2. In **GitHub** → Actions → [Native desktop build (private GitLab source)](https://github.com/roktiw/captains-diary/actions/workflows/native-desktop-build.yml)
   → **Run workflow** → supply `source_sha`.
3. The workflow checks that the private GitLab `main` tip equals the supplied
   SHA. If `main` advances between selecting and cloning, the job fails closed:
   choose a new SHA or trigger immediately after the green pipeline.
4. Three independent jobs use:
   - `macos-15`: Apple Silicon ARM64, Forge ZIP, signature check,
     install checksum test, packaged Electron GUI + native preferences smoke.
   - `ubuntu-24.04`: Linux x64, Forge ZIP, Xvfb packaged GUI + native preferences.
   - `windows-2025`: Windows x64, native Forge ZIP and packaged GUI smoke
     (may fail if GitHub's hosted session cannot run interactive GUI).
5. Successful jobs upload a **small sanitized JSON receipt**:
   exact GitLab SHA, OS/architecture, ZIP basename, byte count, SHA256,
   native smoke result. They do **not** upload the ZIP itself.

Each job uses Node 24, Bun 1.3.10 and `bun install --frozen-lockfile`.
Third-party GitHub Actions are pinned to full commit SHA. No unpublished binaries
or user Markdown files are copied to this public distribution repository.

## Release isolation

This workflow **does not** create a GitHub Release, publish binary artifacts,
merge a GitLab MR, alter version numbers, or enable automatic updates.

Reason: the current Electron Forge ZIP contains bundled application/source
resources. A public GitHub Actions artifact can expose that content. Binary
publication must remain behind the existing [release contract](RELEASE-CONTRACT.md):
exact-source receipts, reviewer-approved source/content scope, macOS Developer ID
signing + notarization for stable releases, Windows native GUI and signing
before advertising it as production-ready, and a draft → verify → publish gate.
The GitLab [release MR !129](https://gitlab.com/roktiw/captains-diary/-/merge_requests/129)
covers the existing manual publisher and must not be silently bypassed.

## Expected blockers and troubleshooting

- **Missing GitLab secrets:** clone step fails before accessing private source.
- **SHA mismatch:** GitLab `main` moved. The workflow intentionally refuses it.
- **macOS signature/GUI failure:** retain logs; do not publish or disable Gatekeeper.
- **Windows native GUI failure:** Windows stays HOLD; a successful crossbuild
  cannot substitute for a native interactive smoke.
- **No ZIP download in GitHub Actions:** intentional. Only sanitized receipts
  are public. Use approved protected release promotion for packages.
- **Auto-update:** separate feature, not enabled by this workflow.
