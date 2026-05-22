"""File-level smells — LoC, excessive exports."""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Dict, Iterable, List

PY_COMMENT_RE = re.compile(r"^\s*#")
JS_LINE_COMMENT_RE = re.compile(r"^\s*//")
JS_BLOCK_OPEN_RE = re.compile(r"/\*")
JS_BLOCK_CLOSE_RE = re.compile(r"\*/")
JS_EXPORT_RE = re.compile(
    r"^\s*export\s+(default\s+)?(function|class|const|let|var|interface|type|enum|async\s+function)"
)


def count_loc(path: Path) -> int:
    """Count code lines (blank + comment lines stripped)."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0
    suffix = path.suffix.lower()
    if suffix == ".py":
        return sum(
            1 for line in text.splitlines()
            if line.strip() and not PY_COMMENT_RE.match(line)
        )
    # JS/TS family — strip line comments AND block comments.
    in_block = False
    count = 0
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if in_block:
            if JS_BLOCK_CLOSE_RE.search(stripped):
                in_block = False
            continue
        if JS_BLOCK_OPEN_RE.search(stripped) and not JS_BLOCK_CLOSE_RE.search(stripped):
            in_block = True
            continue
        if JS_LINE_COMMENT_RE.match(stripped):
            continue
        count += 1
    return count


def find_oversized_files(files: Iterable[Path], threshold: int) -> List[Dict[str, object]]:
    """Return files exceeding `threshold` LoC, sorted descending."""
    out: List[Dict[str, object]] = []
    for f in files:
        loc = count_loc(f)
        if loc > threshold:
            out.append({"file": str(f), "loc": loc})
    out.sort(key=lambda x: x["loc"], reverse=True)
    return out


def count_exports(path: Path, language: str) -> int:
    """Count public exports declared at module top level."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0
    if language == "python":
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return 0
        # Prefer __all__ if defined.
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        if isinstance(node.value, (ast.List, ast.Tuple)):
                            return sum(
                                1 for el in node.value.elts if isinstance(el, ast.Constant)
                            )
        # Fallback: top-level non-underscore def/class.
        count = 0
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if not node.name.startswith("_"):
                    count += 1
        return count
    # JS/TS: count export-keyword lines.
    count = 0
    for line in text.splitlines():
        if JS_EXPORT_RE.match(line):
            count += 1
    return count


def find_excessive_exports(
    files: Iterable[Path],
    language: str,
    threshold: int,
) -> List[Dict[str, object]]:
    """Return files with export count above `threshold`."""
    out: List[Dict[str, object]] = []
    for f in files:
        c = count_exports(f, language)
        if c > threshold:
            out.append({"file": str(f), "exports": c})
    out.sort(key=lambda x: x["exports"], reverse=True)
    return out
