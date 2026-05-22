"""Integration tests against committed fixtures."""
from __future__ import annotations

import unittest
from pathlib import Path

from arch_review.runner import run_audit

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"


class CleanPyFixtureTest(unittest.TestCase):
    def test_clean_py_has_no_violations_or_cycles(self) -> None:
        result = run_audit(
            project_root=FIXTURE_DIR / "clean-py",
            language="python",
            framework="none",
            options={"skip_section": ["dead_code", "complex_functions"]},
        )
        self.assertEqual(result["sections"]["cycles"]["status"], "ok")
        self.assertEqual(result["sections"]["layering"]["status"], "ok")


class ViolationsPyFixtureTest(unittest.TestCase):
    def test_violations_py_finds_cycle_and_layering(self) -> None:
        result = run_audit(
            project_root=FIXTURE_DIR / "violations-py",
            language="python",
            framework="none",
            options={"skip_section": ["dead_code", "complex_functions"]},
        )
        self.assertEqual(result["sections"]["cycles"]["status"], "found")
        self.assertEqual(result["sections"]["layering"]["status"], "found")
        kinds = [
            (v["importer_layer"], v["imported_layer"])
            for v in result["sections"]["layering"]["findings"]
        ]
        self.assertIn(("domain", "infrastructure"), kinds)

    def test_violations_py_finds_oversized_file(self) -> None:
        result = run_audit(
            project_root=FIXTURE_DIR / "violations-py",
            language="python",
            framework="none",
            options={"skip_section": ["dead_code", "complex_functions"]},
        )
        oversized = result["sections"]["oversized_files"]
        self.assertEqual(oversized["status"], "found")
        files = [f["file"] for f in oversized["findings"]]
        self.assertTrue(any("oversized.py" in f for f in files))


if __name__ == "__main__":
    unittest.main()
