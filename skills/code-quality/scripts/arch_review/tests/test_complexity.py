"""Unit tests for complexity.py."""
from __future__ import annotations

import json
import unittest

from arch_review.complexity import _parse_ruff_c901, _parse_eslint_complexity


class ParseRuffC901Test(unittest.TestCase):
    def test_extracts_complexity_from_message(self) -> None:
        payload = json.dumps([
            {
                "code": "C901",
                "message": "`process_order` is too complex (18 > 10)",
                "location": {"row": 23, "column": 5},
                "filename": "src/orders.py",
            }
        ])
        findings = _parse_ruff_c901(payload)
        self.assertEqual(len(findings), 1)
        f = findings[0]
        self.assertEqual(f["file"], "src/orders.py")
        self.assertEqual(f["line"], 23)
        self.assertEqual(f["function"], "process_order")
        self.assertEqual(f["complexity"], 18)
        self.assertEqual(f["threshold"], 10)


class ParseEslintComplexityTest(unittest.TestCase):
    def test_extracts_complexity_from_messages(self) -> None:
        payload = json.dumps([
            {
                "filePath": "/abs/src/auth.ts",
                "messages": [
                    {
                        "ruleId": "complexity",
                        "message": "Function 'validateToken' has a complexity of 15. Maximum allowed is 10.",
                        "line": 45,
                        "column": 1,
                    }
                ],
            }
        ])
        findings = _parse_eslint_complexity(payload)
        self.assertEqual(len(findings), 1)
        f = findings[0]
        self.assertEqual(f["file"], "/abs/src/auth.ts")
        self.assertEqual(f["line"], 45)
        self.assertEqual(f["function"], "validateToken")
        self.assertEqual(f["complexity"], 15)
        self.assertEqual(f["threshold"], 10)

    def test_ignores_non_complexity_messages(self) -> None:
        payload = json.dumps([
            {
                "filePath": "/abs/src/auth.ts",
                "messages": [
                    {"ruleId": "no-unused-vars", "message": "x is unused", "line": 1, "column": 1}
                ],
            }
        ])
        findings = _parse_eslint_complexity(payload)
        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
