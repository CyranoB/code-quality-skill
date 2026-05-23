"""Unit tests for security_scan.secrets — baseline parsing, path stripping."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from security_scan.secrets import _parse, run_detect_secrets

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class ParseSecretsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = (FIXTURES / "detect_secrets_baseline.json").read_text()
        self.project_root = Path("/abs/project")

    def test_flattens_results_map_to_finding_list(self) -> None:
        findings = _parse(self.payload, self.project_root)
        # Fixture: 2 in config.py + 1 in tests/fixtures/sample.env = 3
        self.assertEqual(len(findings), 3)

    def test_all_findings_marked_blocker(self) -> None:
        for f in _parse(self.payload, self.project_root):
            self.assertEqual(f["severity"], "BLK")

    def test_strips_project_root_prefix(self) -> None:
        findings = _parse(self.payload, self.project_root)
        files = {f["file"] for f in findings}
        # Absolute /abs/project/src/config.py -> src/config.py
        self.assertIn("src/config.py", files)
        # Path NOT starting under project_root stays as-is — but our fixture
        # has only paths under /abs/project so all should be stripped.
        for path in files:
            self.assertFalse(path.startswith("/abs/project"))

    def test_keeps_path_when_outside_project_root(self) -> None:
        payload = json.dumps({
            "results": {
                "/elsewhere/file.py": [
                    {"type": "X", "line_number": 1, "hashed_secret": "h", "is_verified": False}
                ]
            }
        })
        findings = _parse(payload, Path("/abs/project"))
        self.assertEqual(findings[0]["file"], "/elsewhere/file.py")

    def test_preserves_type_line_and_hash(self) -> None:
        findings = _parse(self.payload, self.project_root)
        aws = next(f for f in findings if f["type"] == "AWS Access Key")
        self.assertEqual(aws["line"], 5)
        self.assertEqual(aws["hashed_secret"], "abc123hash")
        self.assertFalse(aws["is_verified"])

    def test_returns_empty_on_invalid_json(self) -> None:
        self.assertEqual(_parse("not json", self.project_root), [])

    def test_returns_empty_when_no_results_key(self) -> None:
        self.assertEqual(_parse(json.dumps({}), self.project_root), [])


class RunDetectSecretsSkipsTest(unittest.TestCase):
    def test_skips_when_uvx_missing(self) -> None:
        import security_scan.secrets as ss
        original = ss.shutil.which
        ss.shutil.which = lambda x: None
        try:
            result = run_detect_secrets(Path("/tmp"))
            self.assertEqual(result["status"], "skipped")
            self.assertIn("uvx", str(result["reason"]))
        finally:
            ss.shutil.which = original


if __name__ == "__main__":
    unittest.main()
