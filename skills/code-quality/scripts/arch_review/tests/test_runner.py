"""Integration test for runner.py against a small synthetic project."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from arch_review.runner import run_audit


def write(root: Path, rel: str, content: str = "") -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)


class RunAuditPythonTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()
        # Synthetic project with a layering violation and one cycle.
        write(self.root, "src/myapp/__init__.py")
        write(self.root, "src/myapp/domain/__init__.py")
        write(self.root, "src/myapp/domain/order.py", "from myapp.db import session\n")
        write(self.root, "src/myapp/db/__init__.py")
        write(self.root, "src/myapp/db/session.py", "")
        # Planted cycle: a ↔ b
        write(self.root, "src/myapp/a.py", "from myapp import b\n")
        write(self.root, "src/myapp/b.py", "from myapp import a\n")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_audit_returns_expected_shape(self) -> None:
        result = run_audit(
            project_root=self.root,
            language="python",
            framework="none",
            options={"skip_section": ["dead_code", "complex_functions"]},
        )
        self.assertIn("summary", result)
        self.assertIn("sections", result)
        self.assertEqual(result["summary"]["language"], "python")

    def test_finds_cycle(self) -> None:
        result = run_audit(
            project_root=self.root,
            language="python",
            framework="none",
            options={"skip_section": ["dead_code", "complex_functions"]},
        )
        cycles = result["sections"]["cycles"]
        self.assertEqual(cycles["status"], "found")
        self.assertGreaterEqual(len(cycles["findings"]), 1)

    def test_finds_layering_violation(self) -> None:
        result = run_audit(
            project_root=self.root,
            language="python",
            framework="none",
            options={"skip_section": ["dead_code", "complex_functions"]},
        )
        layering = result["sections"]["layering"]
        self.assertEqual(layering["status"], "found")
        kinds = [(v["importer_layer"], v["imported_layer"]) for v in layering["findings"]]
        self.assertIn(("domain", "infrastructure"), kinds)

    def test_result_is_json_serializable(self) -> None:
        result = run_audit(
            project_root=self.root,
            language="python",
            framework="none",
            options={"skip_section": ["dead_code", "complex_functions"]},
        )
        json.dumps(result)

    def test_monorepo_warning_when_workspaces_present(self) -> None:
        (self.root / "package.json").write_text(json.dumps({"workspaces": ["packages/*"]}))
        result = run_audit(
            project_root=self.root,
            language="python",
            framework="none",
            options={"skip_section": ["dead_code", "complex_functions"]},
        )
        self.assertTrue(any("monorepo detected" in w for w in result["summary"]["warnings"]))


if __name__ == "__main__":
    unittest.main()
