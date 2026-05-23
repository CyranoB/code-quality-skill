"""Unit tests for the dual-metric (cyclomatic + cognitive) path in complexity.py."""
from __future__ import annotations

import json
import unittest

from arch_review.complexity import (
    COGNITIVE_CRITICAL_MIN,
    COGNITIVE_MAJOR_MIN,
    MERGE_LINE_TOLERANCE,
    _merge_dual,
    _parse_eslint_cognitive,
    _parse_flake8_cognitive,
    severity_for,
)


class ParseFlake8CognitiveTest(unittest.TestCase):
    def test_extracts_findings_from_text_output(self) -> None:
        payload = "\n".join([
            "src/orders.py:23:1: CCR001 Cognitive complexity is too high (28 > 15)",
            "src/auth.py:45:5: CCR001 Cognitive complexity is too high (18 > 15)",
        ])
        findings = _parse_flake8_cognitive(payload)
        self.assertEqual(len(findings), 2)
        self.assertEqual(findings[0]["file"], "src/orders.py")
        self.assertEqual(findings[0]["line"], 23)
        self.assertEqual(findings[0]["cognitive"], 28)
        self.assertEqual(findings[0]["cognitive_threshold"], 15)
        self.assertEqual(findings[0]["function"], "")  # flake8 message lacks it

    def test_ignores_unrelated_lines(self) -> None:
        payload = "\n".join([
            "src/foo.py:1:1: E501 line too long",
            "Some random log line",
            "",
        ])
        self.assertEqual(_parse_flake8_cognitive(payload), [])

    def test_handles_paths_with_spaces_and_colons_safely(self) -> None:
        # The regex anchors on `: CCR001 ...` so paths without that suffix don't match.
        payload = "/abs/with space/file.py:10:1: CCR001 Cognitive complexity is too high (20 > 15)"
        findings = _parse_flake8_cognitive(payload)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["cognitive"], 20)


class ParseEslintCognitiveTest(unittest.TestCase):
    def test_extracts_finding_from_sonarjs_rule(self) -> None:
        payload = json.dumps([
            {
                "filePath": "/abs/src/orders.ts",
                "messages": [
                    {
                        "ruleId": "sonarjs/cognitive-complexity",
                        "message": "Refactor this function to reduce its Cognitive Complexity from 25 to the 15 allowed.",
                        "line": 12,
                        "column": 1,
                    }
                ],
            }
        ])
        findings = _parse_eslint_cognitive(payload)
        self.assertEqual(len(findings), 1)
        f = findings[0]
        self.assertEqual(f["file"], "/abs/src/orders.ts")
        self.assertEqual(f["line"], 12)
        self.assertEqual(f["cognitive"], 25)
        self.assertEqual(f["cognitive_threshold"], 15)
        self.assertEqual(f["function"], "")

    def test_ignores_other_sonarjs_rules(self) -> None:
        payload = json.dumps([
            {
                "filePath": "/abs/src/foo.ts",
                "messages": [
                    {"ruleId": "sonarjs/no-duplicate-string", "message": "x", "line": 1, "column": 1}
                ],
            }
        ])
        self.assertEqual(_parse_eslint_cognitive(payload), [])


class MergeDualTest(unittest.TestCase):
    def test_merges_findings_at_same_line(self) -> None:
        cyclomatic = [
            {"file": "/abs/a.py", "line": 10, "function": "foo", "complexity": 12, "threshold": 10},
        ]
        cognitive = [
            {"file": "/abs/a.py", "line": 10, "function": "", "cognitive": 18, "cognitive_threshold": 15},
        ]
        merged = _merge_dual(cyclomatic, cognitive)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["function"], "foo")  # name preserved from cyclomatic
        self.assertEqual(merged[0]["complexity"], 12)
        self.assertEqual(merged[0]["cognitive"], 18)

    def test_merges_within_line_tolerance(self) -> None:
        # Tools sometimes report on the decorator line vs the def line.
        cyclomatic = [
            {"file": "/abs/a.py", "line": 10, "function": "foo", "complexity": 12, "threshold": 10},
        ]
        cognitive = [
            {"file": "/abs/a.py", "line": 10 + MERGE_LINE_TOLERANCE, "function": "", "cognitive": 18, "cognitive_threshold": 15},
        ]
        merged = _merge_dual(cyclomatic, cognitive)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["cognitive"], 18)

    def test_keeps_findings_apart_when_outside_tolerance(self) -> None:
        cyclomatic = [
            {"file": "/abs/a.py", "line": 10, "function": "foo", "complexity": 12, "threshold": 10},
        ]
        cognitive = [
            {"file": "/abs/a.py", "line": 100, "function": "", "cognitive": 18, "cognitive_threshold": 15},
        ]
        merged = _merge_dual(cyclomatic, cognitive)
        self.assertEqual(len(merged), 2)

    def test_includes_cognitive_only_findings(self) -> None:
        cyclomatic: list = []
        cognitive = [
            {"file": "/abs/a.py", "line": 10, "function": "", "cognitive": 18, "cognitive_threshold": 15},
        ]
        merged = _merge_dual(cyclomatic, cognitive)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["cognitive"], 18)
        self.assertNotIn("complexity", merged[0])

    def test_segregates_findings_by_file(self) -> None:
        cyclomatic = [
            {"file": "/abs/a.py", "line": 10, "function": "foo", "complexity": 12, "threshold": 10},
        ]
        cognitive = [
            {"file": "/abs/b.py", "line": 10, "function": "", "cognitive": 18, "cognitive_threshold": 15},
        ]
        merged = _merge_dual(cyclomatic, cognitive)
        self.assertEqual(len(merged), 2)


class SeverityForTest(unittest.TestCase):
    def test_cognitive_critical_min_is_critical(self) -> None:
        self.assertEqual(severity_for({"cognitive": COGNITIVE_CRITICAL_MIN}), "CRITICAL")
        self.assertEqual(severity_for({"cognitive": COGNITIVE_CRITICAL_MIN + 50}), "CRITICAL")

    def test_cognitive_major_band(self) -> None:
        self.assertEqual(severity_for({"cognitive": COGNITIVE_MAJOR_MIN}), "MAJOR")
        self.assertEqual(severity_for({"cognitive": COGNITIVE_CRITICAL_MIN - 1}), "MAJOR")

    def test_cognitive_below_threshold(self) -> None:
        # Tools usually filter these out, but the function should still classify cleanly.
        self.assertEqual(severity_for({"cognitive": COGNITIVE_MAJOR_MIN - 1}), "")

    def test_cyclomatic_only_is_major(self) -> None:
        self.assertEqual(severity_for({"complexity": 15, "threshold": 10}), "MAJOR")

    def test_cognitive_dominates_cyclomatic(self) -> None:
        # If both are present, cognitive drives severity.
        finding = {"complexity": 12, "threshold": 10, "cognitive": COGNITIVE_CRITICAL_MIN + 1}
        self.assertEqual(severity_for(finding), "CRITICAL")


if __name__ == "__main__":
    unittest.main()
