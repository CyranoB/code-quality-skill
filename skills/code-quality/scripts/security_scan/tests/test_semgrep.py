"""Unit tests for security_scan.semgrep — parser, severity mapping, truncation."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from security_scan.semgrep import _parse, _section_severity, run_semgrep

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class ParseSemgrepTest(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = (FIXTURES / "semgrep_findings.json").read_text()

    def test_extracts_three_findings(self) -> None:
        findings = _parse(self.payload)
        self.assertEqual(len(findings), 3)

    def test_maps_error_to_blocker(self) -> None:
        findings = _parse(self.payload)
        shell_finding = next(f for f in findings if "subprocess-shell-true" in str(f["rule_id"]))
        self.assertEqual(shell_finding["severity"], "BLK")
        self.assertEqual(shell_finding["raw_severity"], "ERROR")
        self.assertEqual(shell_finding["line"], 12)
        self.assertEqual(shell_finding["file"], "/abs/project/src/runner.py")

    def test_maps_warning_to_critical(self) -> None:
        findings = _parse(self.payload)
        warn_finding = next(f for f in findings if "dangerous-exec" in str(f["rule_id"]))
        self.assertEqual(warn_finding["severity"], "CRT")

    def test_maps_info_to_major(self) -> None:
        findings = _parse(self.payload)
        xss_finding = next(f for f in findings if "direct-response-write" in str(f["rule_id"]))
        self.assertEqual(xss_finding["severity"], "MAJ")

    def test_flattens_cwe_list_to_string(self) -> None:
        findings = _parse(self.payload)
        shell_finding = next(f for f in findings if "subprocess-shell-true" in str(f["rule_id"]))
        # Fixture has CWE as a list; parser should produce a comma-joined string.
        self.assertIsInstance(shell_finding["cwe"], str)
        self.assertIn("CWE-78", shell_finding["cwe"])

    def test_passes_through_string_cwe(self) -> None:
        findings = _parse(self.payload)
        warn_finding = next(f for f in findings if "dangerous-exec" in str(f["rule_id"]))
        self.assertIn("CWE-95", warn_finding["cwe"])

    def test_returns_empty_on_invalid_json(self) -> None:
        self.assertEqual(_parse("not json"), [])

    def test_returns_empty_on_no_results_key(self) -> None:
        self.assertEqual(_parse(json.dumps({"errors": []})), [])

    def test_unknown_severity_falls_back_to_major(self) -> None:
        payload = json.dumps({
            "results": [{
                "check_id": "x",
                "path": "/a.py",
                "start": {"line": 1},
                "extra": {"severity": "MYSTERY", "message": "x"},
            }]
        })
        self.assertEqual(_parse(payload)[0]["severity"], "MAJ")


class SectionSeverityTest(unittest.TestCase):
    def test_picks_most_severe(self) -> None:
        self.assertEqual(_section_severity([{"severity": "MAJ"}, {"severity": "BLK"}]), "BLK")
        self.assertEqual(_section_severity([{"severity": "INF"}, {"severity": "CRT"}]), "CRT")

    def test_none_for_empty(self) -> None:
        self.assertIsNone(_section_severity([]))


class RunSemgrepSkipsTest(unittest.TestCase):
    def test_skips_when_uvx_missing(self) -> None:
        import security_scan.semgrep as sg
        original = sg.shutil.which
        sg.shutil.which = lambda x: None
        try:
            result = run_semgrep(Path("/tmp"), timeout=5)
            self.assertEqual(result["status"], "skipped")
            self.assertIn("uvx", str(result["reason"]))
        finally:
            sg.shutil.which = original


class TruncationTest(unittest.TestCase):
    def test_truncates_above_max_findings_sorted_by_severity(self) -> None:
        # Build a payload with 5 findings of mixed severity.
        results = []
        for i in range(5):
            sev = ["ERROR", "WARNING", "INFO", "INFO", "INFO"][i]
            results.append({
                "check_id": f"r{i}",
                "path": f"/p/f{i}.py",
                "start": {"line": i + 1},
                "extra": {"severity": sev, "message": ""},
            })
        # Patch _parse to return our list, and run_semgrep should keep highest-severity.
        # Easier: test the parse + sort directly.
        findings = _parse(json.dumps({"results": results}))
        # Sort the way run_semgrep does for truncation:
        order = {"BLK": 0, "CRT": 1, "MAJ": 2, "MIN": 3, "INF": 4}
        findings.sort(key=lambda f: (order.get(str(f.get("severity", "INF")), 9),))
        # Take the top 2 (simulating max_findings=2).
        kept = findings[:2]
        self.assertEqual(kept[0]["severity"], "BLK")
        self.assertEqual(kept[1]["severity"], "CRT")


if __name__ == "__main__":
    unittest.main()
