"""Unit tests for dead_code.py.

The subprocess functions (run_knip, run_vulture) are exercised by smoke tests.
Here we only test the parsers against synthetic CLI outputs.
"""
from __future__ import annotations

import json
import unittest

from arch_review.dead_code import _parse_knip_json, _parse_vulture_text


class ParseKnipJsonTest(unittest.TestCase):
    def test_returns_empty_on_clean_output(self) -> None:
        payload = json.dumps({"files": [], "exports": {}})
        findings = _parse_knip_json(payload)
        self.assertEqual(findings, [])

    def test_collects_unused_files(self) -> None:
        payload = json.dumps({
            "files": ["src/unused.ts", "src/dead.ts"],
            "exports": {},
        })
        findings = _parse_knip_json(payload)
        kinds = sorted(f["kind"] for f in findings)
        self.assertEqual(kinds, ["unused_file", "unused_file"])

    def test_collects_unused_exports(self) -> None:
        payload = json.dumps({
            "files": [],
            "exports": {
                "src/a.ts": [
                    {"name": "foo", "line": 10},
                    {"name": "bar", "line": 12},
                ],
            },
        })
        findings = _parse_knip_json(payload)
        self.assertEqual(len(findings), 2)
        self.assertTrue(all(f["kind"] == "unused_export" for f in findings))


class ParseVultureTextTest(unittest.TestCase):
    def test_parses_finding(self) -> None:
        text = "src/myapp/orphan.py:42: unused function 'foo' (90% confidence)\n"
        findings = _parse_vulture_text(text)
        self.assertEqual(len(findings), 1)
        f = findings[0]
        self.assertEqual(f["file"], "src/myapp/orphan.py")
        self.assertEqual(f["line"], 42)
        self.assertEqual(f["confidence"], 90)

    def test_ignores_empty_lines(self) -> None:
        text = "\n\n"
        self.assertEqual(_parse_vulture_text(text), [])


if __name__ == "__main__":
    unittest.main()
