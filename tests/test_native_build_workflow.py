"""Guard the public build workflow's source and artifact boundaries."""
from pathlib import Path
import re
import unittest

WORKFLOW = (
    Path(__file__).resolve().parents[1]
    / ".github/workflows/native-desktop-build.yml"
)


class NativeBuildWorkflowPolicy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_private_source_job_is_manual_only_and_least_permissions(self):
        self.assertRegex(self.text, r"(?m)^  workflow_dispatch:")
        self.assertRegex(self.text, r"(?m)^  push:")
        self.assertIn('      - ".github/workflows/native-desktop-build.yml"', self.text)
        self.assertIn("if: github.event_name == 'workflow_dispatch'", self.text)
        self.assertNotRegex(self.text, r"(?m)^  (?:pull_request|schedule|repository_dispatch):")
        self.assertRegex(self.text, r"(?m)^permissions:\n  contents: read")

    def test_secretless_probe_compiles_on_all_three_platforms(self):
        self.assertIn("runner-probe:", self.text)
        self.assertIn('bun build "$src" --compile --outfile "$exe"', self.text)
        self.assertIn("NATIVE_PROBE_OK", self.text)
        self.assertIn("needs: runner-probe", self.text)

    def test_forge_packaging_probe_is_synthetic_and_public_safe(self):
        self.assertIn("Package synthetic Electron Forge ZIP natively", self.text)
        self.assertIn('"electron": "41.1.1"', self.text)
        self.assertIn('"@electron-forge/cli": "7.11.1"', self.text)
        self.assertIn('"@electron-forge/maker-zip": "7.11.1"', self.text)
        self.assertIn("./node_modules/.bin/electron-forge make", self.text)
        self.assertIn("FORGE_PROBE_PASS", self.text)
        self.assertIn("captainsDiaryBuilt: false", self.text)
        self.assertIn("synthetic: true", self.text)

    def test_source_is_private_gitlab_main_at_exact_sha(self):
        self.assertIn("https://gitlab.com/roktiw/captains-diary.git", self.text)
        self.assertIn("DIARY_GITLAB_READ_USER", self.text)
        self.assertIn("DIARY_GITLAB_READ_TOKEN", self.text)
        self.assertIn("git clone --depth 1 --single-branch --branch main", self.text)
        self.assertIn('if [[ "$actual" != "$SOURCE_SHA" ]]; then', self.text)
        self.assertIn("GIT_CONFIG_VALUE_0", self.text)

    def test_all_native_platforms(self):
        for platform, runner in (
            ("macos-arm64", "macos-15"),
            ("linux-x64", "ubuntu-24.04"),
            ("windows-x64", "windows-2025"),
        ):
            self.assertIn(f"platform: {platform}, runner: {runner}", self.text)
        self.assertIn("smoke-electron.mjs", self.text)
        self.assertIn("verify-macos-package.mjs", self.text)

    def test_public_artifacts_are_only_sanitized_receipts(self):
        self.assertIn("path: source/github-build-receipt.json", self.text)
        self.assertEqual(self.text.count("actions/upload-artifact@"), 1)
        self.assertNotRegex(self.text, r"(?m)^\s+path:.*(?:out/|\.zip|node_modules|source/\*\*)")
        self.assertNotIn("gh release create", self.text)
        self.assertNotIn("gh release upload", self.text)
        self.assertNotIn("permissions:\n  contents: write", self.text)


if __name__ == "__main__":
    unittest.main()
