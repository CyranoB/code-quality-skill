"""Unit tests for smells.py."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from arch_review.smells import count_loc, count_exports


class CountLocTest(unittest.TestCase):
    def test_counts_code_lines_only(self) -> None:
        content = (
            "# comment\n"
            "\n"
            "def f():\n"
            "    return 1\n"
            "\n"
            "# another comment\n"
        )
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(content)
            path = Path(f.name)
        try:
            self.assertEqual(count_loc(path), 2)
        finally:
            path.unlink()

    def test_counts_zero_for_all_blank(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write("\n\n   \n")
            path = Path(f.name)
        try:
            self.assertEqual(count_loc(path), 0)
        finally:
            path.unlink()

    def test_js_line_comments_ignored(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".ts", delete=False) as f:
            f.write("// comment\nconst x = 1;\n// another\nconst y = 2;\n")
            path = Path(f.name)
        try:
            self.assertEqual(count_loc(path), 2)
        finally:
            path.unlink()


class CountExportsTest(unittest.TestCase):
    def test_python_dunder_all(self) -> None:
        content = '__all__ = ["a", "b", "c"]\n'
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(content)
            path = Path(f.name)
        try:
            self.assertEqual(count_exports(path, "python"), 3)
        finally:
            path.unlink()

    def test_python_top_level_defs_when_no_all(self) -> None:
        content = (
            "def public_fn(): pass\n"
            "def _private(): pass\n"
            "class Public: pass\n"
            "class _Private: pass\n"
        )
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(content)
            path = Path(f.name)
        try:
            self.assertEqual(count_exports(path, "python"), 2)
        finally:
            path.unlink()

    def test_js_named_exports(self) -> None:
        content = (
            "export function a() {}\n"
            "export const b = 1;\n"
            "export class C {}\n"
            "export default function d() {}\n"
        )
        with tempfile.NamedTemporaryFile("w", suffix=".ts", delete=False) as f:
            f.write(content)
            path = Path(f.name)
        try:
            self.assertEqual(count_exports(path, "javascript"), 4)
        finally:
            path.unlink()


if __name__ == "__main__":
    unittest.main()
