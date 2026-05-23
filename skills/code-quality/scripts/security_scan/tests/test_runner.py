"""Integration-style tests for security_scan.runner — skip, error propagation,
default exclude regex shape, glob-to-regex helper."""
from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from security_scan import runner


class GlobToLooseRegexTest(unittest.TestCase):
    def test_suffix_glob(self) -> None:
        self.assertEqual(runner._glob_to_loose_regex("*.min.js"), r"\.min\.js$")

    def test_path_segment_glob(self) -> None:
        # Escapes dot, anchors at slash boundaries.
        self.assertEqual(runner._glob_to_loose_regex("vendor"), r"(^|/)vendor(/|$)")

    def test_empty_string_returns_empty(self) -> None:
        self.assertEqual(runner._glob_to_loose_regex(""), "")


class DefaultExcludeRegexTest(unittest.TestCase):
    def test_matches_common_paths(self) -> None:
        import re
        pat = re.compile(runner.DEFAULT_EXCLUDE_REGEX)
        for path in [
            "node_modules/foo.js",
            "src/vendor/bundle.min.js",
            "src/sourcemap.map",
            "package-lock.json",
            "tests/.pytest_cache/foo",
            ".git/HEAD",
            "subdir/__pycache__/x.pyc",
        ]:
            self.assertTrue(pat.search(path), f"expected to match: {path}")

    def test_does_not_match_normal_paths(self) -> None:
        import re
        pat = re.compile(runner.DEFAULT_EXCLUDE_REGEX)
        for path in ["src/app.py", "lib/utils.ts", "README.md", "Makefile"]:
            self.assertFalse(pat.search(path), f"should not match: {path}")


class RunScanSkipSectionTest(unittest.TestCase):
    def test_skipping_semgrep_only_runs_secrets(self) -> None:
        with mock.patch.object(runner.semgrep_mod, "run_semgrep") as mock_semgrep, \
             mock.patch.object(runner.secrets_mod, "run_detect_secrets") as mock_secrets:
            mock_secrets.return_value = {"status": "ok", "severity": None, "findings": []}
            result = runner.run_scan(Path("/tmp"), options={"skip_section": ["semgrep"]})
            mock_semgrep.assert_not_called()
            mock_secrets.assert_called_once()
            self.assertIn("semgrep", result["summary"]["sections_skipped"])

    def test_skipping_secrets_only_runs_semgrep(self) -> None:
        with mock.patch.object(runner.semgrep_mod, "run_semgrep") as mock_semgrep, \
             mock.patch.object(runner.secrets_mod, "run_detect_secrets") as mock_secrets:
            mock_semgrep.return_value = {"status": "ok", "severity": None, "findings": []}
            result = runner.run_scan(Path("/tmp"), options={"skip_section": ["secrets"]})
            mock_secrets.assert_not_called()
            mock_semgrep.assert_called_once()
            self.assertIn("secrets", result["summary"]["sections_skipped"])


class RunScanErrorPropagationTest(unittest.TestCase):
    def test_sub_tool_exception_becomes_error_section(self) -> None:
        def boom(*_a, **_k):
            raise RuntimeError("disk full")

        with mock.patch.object(runner.semgrep_mod, "run_semgrep", side_effect=boom), \
             mock.patch.object(runner.secrets_mod, "run_detect_secrets") as mock_secrets:
            mock_secrets.return_value = {"status": "ok", "severity": None, "findings": []}
            result = runner.run_scan(Path("/tmp"))
            self.assertEqual(result["sections"]["semgrep"]["status"], "error")
            self.assertIn("disk full", result["sections"]["semgrep"]["reason"])
            self.assertIn("semgrep", result["summary"]["sections_errored"])

    def test_skipped_sub_tool_recorded_in_summary(self) -> None:
        with mock.patch.object(runner.semgrep_mod, "run_semgrep") as mock_semgrep, \
             mock.patch.object(runner.secrets_mod, "run_detect_secrets") as mock_secrets:
            mock_semgrep.return_value = {"status": "skipped", "reason": "uvx missing"}
            mock_secrets.return_value = {"status": "ok", "severity": None, "findings": []}
            result = runner.run_scan(Path("/tmp"))
            self.assertIn("semgrep", result["summary"]["sections_skipped"])


class RunScanExtraExcludesTest(unittest.TestCase):
    def test_user_excludes_append_to_defaults_for_semgrep(self) -> None:
        captured = {}

        def stub_semgrep(root, config, excludes, timeout, max_findings):
            captured["excludes"] = list(excludes)
            return {"status": "ok", "severity": None, "findings": []}

        with mock.patch.object(runner.semgrep_mod, "run_semgrep", side_effect=stub_semgrep), \
             mock.patch.object(runner.secrets_mod, "run_detect_secrets") as mock_secrets:
            mock_secrets.return_value = {"status": "ok", "severity": None, "findings": []}
            runner.run_scan(Path("/tmp"), options={"exclude": ["custom_dir"]})
            self.assertIn("custom_dir", captured["excludes"])
            # Defaults are still present.
            self.assertIn("node_modules", captured["excludes"])


if __name__ == "__main__":
    unittest.main()
