"""Unit tests for graph.py."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from arch_review.graph import build_python_graph


def write_file(root: Path, relpath: str, content: str) -> None:
    full = root / relpath
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content)


class BuildPythonGraphTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_resolves_simple_absolute_imports(self) -> None:
        write_file(self.root, "src/myapp/__init__.py", "")
        write_file(self.root, "src/myapp/a.py", "from myapp import b\n")
        write_file(self.root, "src/myapp/b.py", "")
        graph = build_python_graph(self.root, exclude_tests=True)

        a = str(self.root / "src/myapp/a.py")
        b = str(self.root / "src/myapp/b.py")
        self.assertIn(a, graph)
        self.assertIn(b, graph[a])

    def test_resolves_relative_imports(self) -> None:
        write_file(self.root, "src/myapp/__init__.py", "")
        write_file(self.root, "src/myapp/a.py", "from . import b\n")
        write_file(self.root, "src/myapp/b.py", "")
        graph = build_python_graph(self.root, exclude_tests=True)

        a = str(self.root / "src/myapp/a.py")
        b = str(self.root / "src/myapp/b.py")
        self.assertIn(b, graph[a])

    def test_ignores_third_party_imports(self) -> None:
        write_file(self.root, "src/myapp/__init__.py", "")
        write_file(self.root, "src/myapp/a.py", "import os\nimport requests\n")
        graph = build_python_graph(self.root, exclude_tests=True)

        a = str(self.root / "src/myapp/a.py")
        # External imports must not appear as edges
        self.assertEqual(graph[a], [])

    def test_excludes_test_files_by_default(self) -> None:
        write_file(self.root, "src/myapp/__init__.py", "")
        write_file(self.root, "src/myapp/a.py", "")
        write_file(self.root, "tests/test_a.py", "from myapp import a\n")
        graph = build_python_graph(self.root, exclude_tests=True)

        test_path = str(self.root / "tests/test_a.py")
        self.assertNotIn(test_path, graph)

    def test_include_tests_flag(self) -> None:
        write_file(self.root, "src/myapp/__init__.py", "")
        write_file(self.root, "src/myapp/a.py", "")
        write_file(self.root, "tests/test_a.py", "from myapp import a\n")
        graph = build_python_graph(self.root, exclude_tests=False)

        test_path = str(self.root / "tests/test_a.py")
        self.assertIn(test_path, graph)

    def test_skips_syntactically_broken_file(self) -> None:
        write_file(self.root, "src/myapp/__init__.py", "")
        write_file(self.root, "src/myapp/broken.py", "from\n")  # SyntaxError
        write_file(self.root, "src/myapp/ok.py", "")
        graph = build_python_graph(self.root, exclude_tests=True)

        ok = str(self.root / "src/myapp/ok.py")
        self.assertIn(ok, graph)
        # Broken file is skipped silently — verify build did not crash.


if __name__ == "__main__":
    unittest.main()
