# Architecture Review (Workflow I) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Workflow I to the `code-quality` skill that produces a structured architecture review report covering circular deps, layering violations, coupling metrics (Ca/Ce/I), hub/god modules, deep chains, oversized files, excessive exports, dead code, and complex functions, for JS/TS and Python projects.

**Architecture:** A small stdlib-only Python package `skills/code-quality/scripts/arch_review/` (modules: `runner`, `graph`, `metrics`, `layers`, `smells`, `dead_code`) invoked through a thin bash wrapper `arch-review.sh`. The orchestrator subprocesses to `madge` / `knip` / `vulture` / `eslint` / `ruff`, builds the Python dependency graph itself via `ast`, computes metrics in-process, and emits a JSON document that the SKILL.md workflow renders as markdown.

**Tech Stack:** Python 3 (stdlib only — `argparse`, `ast`, `json`, `subprocess`, `concurrent.futures`, `pathlib`, `re`, `unittest`), bash (wrapper + `detect-linter.sh` extension), subprocess to `npx madge`, `npx knip`, `uvx vulture`, `npx eslint`, `ruff` (existing). No new third-party Python dependencies.

**Spec:** `docs/superpowers/specs/2026-05-21-architecture-review-design.md`. Read this before starting; the plan assumes you've internalized the constraints (zero-install third-party tools, top-N reporting, no user config).

---

## File Structure

**New files:**

| Path | Responsibility |
|------|----------------|
| `skills/code-quality/scripts/arch-review.sh` | Bash wrapper. Resolves script dir, sets `PYTHONPATH`, execs `python3 -m arch_review`. ~5 lines. |
| `skills/code-quality/scripts/arch_review/__init__.py` | Package marker. Empty. |
| `skills/code-quality/scripts/arch_review/__main__.py` | CLI entry. `argparse` setup, dispatch to `runner.run_audit`. ~80 lines. |
| `skills/code-quality/scripts/arch_review/runner.py` | Orchestrator. Parallel sub-check dispatch via `ThreadPoolExecutor`. Assembles final JSON. ~150 lines. |
| `skills/code-quality/scripts/arch_review/graph.py` | Dep graph extraction. `build_python_graph(root)` via `ast`, `build_js_graph(root)` via `npx madge`. TS entry-point detection. ~180 lines. |
| `skills/code-quality/scripts/arch_review/metrics.py` | `find_cycles(graph)` (Tarjan SCC), `compute_coupling(graph)` (Ca/Ce/I), `find_deep_chains(graph, max_depth)`. ~140 lines. |
| `skills/code-quality/scripts/arch_review/layers.py` | `infer_layer(path, framework)`, `assign_layers(nodes, framework)`, `find_layer_violations(graph, layers)`. ~150 lines. |
| `skills/code-quality/scripts/arch_review/smells.py` | `count_loc(file)`, `find_oversized_files(root, threshold)`, `count_exports(file, language)`, `find_excessive_exports(files, threshold)`. ~120 lines. |
| `skills/code-quality/scripts/arch_review/dead_code.py` | `run_knip(root)`, `run_vulture(root)`. Subprocess + parse. ~100 lines. |
| `skills/code-quality/scripts/arch_review/complexity.py` | `run_complexity_check(root, language)`. Subprocess to `ruff`/`eslint`, parse JSON. ~80 lines. |
| `skills/code-quality/scripts/arch_review/tests/__init__.py` | Package marker. Empty. |
| `skills/code-quality/scripts/arch_review/tests/test_graph.py` | Unit tests for `graph.py`. |
| `skills/code-quality/scripts/arch_review/tests/test_metrics.py` | Unit tests for `metrics.py`. |
| `skills/code-quality/scripts/arch_review/tests/test_layers.py` | Unit tests for `layers.py`. |
| `skills/code-quality/scripts/arch_review/tests/test_smells.py` | Unit tests for `smells.py`. |
| `skills/code-quality/scripts/arch_review/tests/test_dead_code.py` | Unit tests for `dead_code.py`. |
| `skills/code-quality/scripts/arch_review/tests/test_complexity.py` | Unit tests for `complexity.py`. |
| `skills/code-quality/scripts/arch_review/fixtures/clean-py/` | Synthetic clean Python project. |
| `skills/code-quality/scripts/arch_review/fixtures/violations-py/` | Synthetic Python project with planted issues. |
| `skills/code-quality/scripts/arch_review/fixtures/clean-js/` | Synthetic clean TS project. |
| `skills/code-quality/scripts/arch_review/fixtures/violations-js/` | Synthetic TS project with planted issues. |
| `skills/code-quality/scripts/arch_review/SMOKE.md` | Manual smoke-test procedure. |
| `skills/code-quality/references/architecture.md` | Layer mapping, framework overrides, JSON schema. |
| `skills/code-quality/references/knip.md` | Knip CLI reference (JS/TS dead-code). |
| `skills/code-quality/references/vulture.md` | Vulture CLI reference (Python dead-code). |

**Modified files:**

| Path | Change |
|------|--------|
| `skills/code-quality/scripts/detect-linter.sh` | Add framework detection block. Emit new `FRAMEWORK=…` key. ~30 lines added. |
| `skills/code-quality/SKILL.md` | Add Workflow I section + new triggers in the description. ~150 lines added. |

---

## Conventions

**Test invocation:** Tests run from inside the orchestrator package. From the repo root:
```bash
PYTHONPATH=skills/code-quality/scripts python3 -m unittest discover -s skills/code-quality/scripts/arch_review/tests -v
```

**Conventional commits:** Per `CLAUDE.md`, use `feat:` for new features, `fix:` for bug fixes, `docs:` for docs only, `refactor:` for restructuring.

**Pure-stdlib rule:** No `pip install` in tests, fixtures, or production code. If you reach for a third-party library, stop — use stdlib.

---

## Task 1: Package skeleton + wrapper script

**Files:**
- Create: `skills/code-quality/scripts/arch-review.sh`
- Create: `skills/code-quality/scripts/arch_review/__init__.py`
- Create: `skills/code-quality/scripts/arch_review/__main__.py`
- Create: `skills/code-quality/scripts/arch_review/tests/__init__.py`

- [ ] **Step 1: Create the empty package markers**

Create `skills/code-quality/scripts/arch_review/__init__.py` with content:
```python
"""arch_review — orchestrator for Workflow I (architecture review)."""
```

Create `skills/code-quality/scripts/arch_review/tests/__init__.py` empty (literally no content; just `touch` it).

- [ ] **Step 2: Write a smoke-test `__main__.py` that exits with help**

Create `skills/code-quality/scripts/arch_review/__main__.py`:
```python
"""CLI entry point for arch_review. Use the arch-review.sh wrapper to invoke."""
from __future__ import annotations

import argparse
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="arch_review",
        description="Architecture review orchestrator (Workflow I of code-quality skill).",
    )
    parser.add_argument("--project-root", required=True, help="Absolute path to the project root.")
    parser.add_argument("--language", required=True, choices=["python", "javascript"], help="Project language as detected by detect-linter.sh.")
    parser.add_argument("--framework", default="none", help="Framework hint from detect-linter.sh (nextjs|django|fastapi|nestjs|express|flask|none).")
    parser.add_argument("--top", type=int, default=10, help="Top-N findings per section.")
    parser.add_argument("--include-tests", action="store_true", help="Include test files in the audit.")
    parser.add_argument("--max-file-loc", type=int, default=500)
    parser.add_argument("--max-exports", type=int, default=30)
    parser.add_argument("--max-ca", type=int, default=20)
    parser.add_argument("--max-ce", type=int, default=20)
    parser.add_argument("--max-chain-depth", type=int, default=6)
    parser.add_argument("--skip-section", action="append", default=[], help="Section name to skip (repeatable).")
    parser.add_argument("--timeout-per-section", type=int, default=60)
    parser.add_argument("--output-format", default="json", choices=["json"])
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    # Stub: just echo args. Real runner wiring lands in Task 14.
    print(f'{{"summary": {{"language": "{args.language}", "framework": "{args.framework}", "stub": true}}}}')
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Create the wrapper script**

Create `skills/code-quality/scripts/arch-review.sh`:
```bash
#!/usr/bin/env bash
# Thin wrapper for the arch_review package. Resolves the script directory
# and adds it to PYTHONPATH so `python3 -m arch_review` can find the package.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec env PYTHONPATH="$SCRIPT_DIR${PYTHONPATH:+:$PYTHONPATH}" python3 -m arch_review "$@"
```

Make it executable:
```bash
chmod +x skills/code-quality/scripts/arch-review.sh
```

- [ ] **Step 4: Manual smoke test**

Run:
```bash
bash skills/code-quality/scripts/arch-review.sh --project-root /tmp --language python
```
Expected output (one line):
```
{"summary": {"language": "python", "framework": "none", "stub": true}}
```

Also run:
```bash
bash skills/code-quality/scripts/arch-review.sh --help
```
Expected: argparse help text listing all flags including `--top`, `--include-tests`, etc.

- [ ] **Step 5: Commit**

```bash
git add skills/code-quality/scripts/arch-review.sh skills/code-quality/scripts/arch_review/
git commit -m "feat: scaffold arch_review package and wrapper (Workflow I)"
```

---

## Task 2: Extend detect-linter.sh with FRAMEWORK detection

**Files:**
- Modify: `skills/code-quality/scripts/detect-linter.sh`

- [ ] **Step 1: Read the current detect-linter.sh end and find where to add the framework block**

Run:
```bash
grep -n '^echo' skills/code-quality/scripts/detect-linter.sh | tail -20
```
You should see existing `echo "KEY=$VALUE"` lines at the end. The framework detection appends one more.

- [ ] **Step 2: Add the framework-detection function**

Insert this function near the top of `detect-linter.sh` (after the existing helper functions, before the main detection logic that emits `echo` lines). If unsure, place it right before the first `echo "TOOL=..."` line.

```bash
detect_framework() {
  local root="$1"

  # Priority order: nextjs > nestjs > django > fastapi > flask > express
  if ls "$root"/next.config.{js,ts,mjs} >/dev/null 2>&1; then
    echo "nextjs"
    return
  fi
  if [ -f "$root/nest-cli.json" ]; then
    echo "nestjs"
    return
  fi
  if [ -f "$root/manage.py" ] && find "$root" -maxdepth 3 -name 'settings.py' -print -quit | grep -q .; then
    echo "django"
    return
  fi
  if [ -f "$root/pyproject.toml" ] && grep -qE '(^|[^a-zA-Z_])fastapi([^a-zA-Z_]|$)' "$root/pyproject.toml" 2>/dev/null; then
    echo "fastapi"
    return
  fi
  if [ -f "$root/requirements.txt" ] && grep -qE '^fastapi([=<>!~]|$)' "$root/requirements.txt" 2>/dev/null; then
    echo "fastapi"
    return
  fi
  if [ -f "$root/pyproject.toml" ] && grep -qE '(^|[^a-zA-Z_])flask([^a-zA-Z_]|$)' "$root/pyproject.toml" 2>/dev/null; then
    echo "flask"
    return
  fi
  if [ -f "$root/requirements.txt" ] && grep -qE '^flask([=<>!~]|$)' "$root/requirements.txt" 2>/dev/null; then
    echo "flask"
    return
  fi
  if [ -f "$root/package.json" ] && grep -q '"express"' "$root/package.json" 2>/dev/null; then
    echo "express"
    return
  fi
  echo "none"
}
```

- [ ] **Step 3: Emit the FRAMEWORK key at the end of the script**

Find the final block of `echo "KEY=..."` lines (where the script writes its detection output). Append:

```bash
FRAMEWORK=$(detect_framework "$PROJECT_ROOT")
echo "FRAMEWORK=$FRAMEWORK"
```

(Use `$PROJECT_ROOT` if that's the variable name in the existing script — otherwise use whichever variable holds the resolved project root. Read the existing script and use the same variable name.)

- [ ] **Step 4: Manual test against fixtures**

Run against the skill's own repo (which has no framework markers):
```bash
bash skills/code-quality/scripts/detect-linter.sh /tmp 2>/dev/null | grep '^FRAMEWORK='
```
Expected:
```
FRAMEWORK=none
```

Run against a synthetic Django repo:
```bash
mkdir -p /tmp/dj-fixture && touch /tmp/dj-fixture/manage.py && touch /tmp/dj-fixture/settings.py
bash skills/code-quality/scripts/detect-linter.sh /tmp/dj-fixture | grep '^FRAMEWORK='
```
Expected:
```
FRAMEWORK=django
```
Clean up:
```bash
rm -rf /tmp/dj-fixture
```

- [ ] **Step 5: Commit**

```bash
git add skills/code-quality/scripts/detect-linter.sh
git commit -m "feat: add FRAMEWORK detection to detect-linter.sh"
```

---

## Task 3: Python dependency graph via ast

**Files:**
- Create: `skills/code-quality/scripts/arch_review/graph.py`
- Create: `skills/code-quality/scripts/arch_review/tests/test_graph.py`

- [ ] **Step 1: Write failing tests for `build_python_graph`**

Create `skills/code-quality/scripts/arch_review/tests/test_graph.py`:
```python
"""Unit tests for graph.py."""
from __future__ import annotations

import os
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
```

- [ ] **Step 2: Run the tests, verify failure**

```bash
PYTHONPATH=skills/code-quality/scripts python3 -m unittest discover -s skills/code-quality/scripts/arch_review/tests -v
```
Expected: `ImportError` or `ModuleNotFoundError: arch_review.graph` (file doesn't exist yet).

- [ ] **Step 3: Implement `build_python_graph`**

Create `skills/code-quality/scripts/arch_review/graph.py`:
```python
"""Dependency graph extraction.

Exposes:
- build_python_graph(root, exclude_tests)  — stdlib ast-based walker
- build_js_graph(root, exclude_tests)      — subprocess to `npx madge --json`
"""
from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path
from typing import Iterable

# Folders that are noise by default.
DEFAULT_EXCLUDES = {
    "node_modules", "dist", "build", ".next", "coverage",
    "__pycache__", ".venv", "venv", ".tox", ".mypy_cache", ".pytest_cache",
    "tests", "test", "__tests__", "migrations",
}
TEST_FILE_PATTERNS = ("*_test.py", "test_*.py", "*.test.ts", "*.test.tsx", "*.test.js", "*.spec.ts", "*.spec.tsx", "*.spec.js", "conftest.py")


def _should_exclude(path: Path, exclude_tests: bool) -> bool:
    parts = set(path.parts)
    if not exclude_tests:
        return False
    if parts & DEFAULT_EXCLUDES:
        return True
    name = path.name
    for pat in TEST_FILE_PATTERNS:
        if path.match(pat):
            return True
    return False


def _iter_py_files(root: Path, exclude_tests: bool) -> Iterable[Path]:
    for p in root.rglob("*.py"):
        if _should_exclude(p.relative_to(root), exclude_tests):
            continue
        yield p


def _build_module_index(py_files: list[Path], root: Path) -> dict[str, Path]:
    """Map dotted module names → file paths.

    Strategy: walk every .py file, derive its dotted name from its path relative
    to the nearest ancestor that is NOT a package (i.e., has no __init__.py).
    """
    index: dict[str, Path] = {}
    for fp in py_files:
        # Find the highest ancestor with __init__.py (the package root).
        parts = list(fp.relative_to(root).with_suffix("").parts)
        # Walk upward in the path looking for the first directory without __init__.py.
        current = fp.parent
        package_parts: list[str] = []
        while current != root and (current / "__init__.py").exists():
            package_parts.insert(0, current.name)
            current = current.parent
        module_name = ".".join(package_parts + [fp.stem]) if package_parts else fp.stem
        index[module_name] = fp
        # Also index the package __init__.py under just the package dotted name.
        if fp.name == "__init__.py" and package_parts:
            index[".".join(package_parts)] = fp
    return index


def _resolve_import(
    name: str,
    importer: Path,
    root: Path,
    index: dict[str, Path],
    level: int = 0,
) -> Path | None:
    if level > 0:
        # Relative import: walk up `level` levels from importer's package.
        base = importer.parent
        for _ in range(level - 1):
            base = base.parent
        try:
            rel = base.relative_to(root)
        except ValueError:
            return None
        package_prefix = ".".join(rel.parts)
        full = f"{package_prefix}.{name}" if name else package_prefix
        return index.get(full)
    # Absolute import.
    # Try exact match, then progressively shorter prefixes (covers `from x.y import z` where z is a name not a module).
    if name in index:
        return index[name]
    if "." in name:
        prefix = name.rsplit(".", 1)[0]
        return index.get(prefix)
    return None


def build_python_graph(root: Path, exclude_tests: bool = True) -> dict[str, list[str]]:
    """Build dependency graph from Python source files.

    Returns: {file_path: [imported_file_paths, ...]}
    Only edges to files within `root` are recorded. External imports are dropped.
    Files with SyntaxError are silently skipped (caller can inspect via warnings).
    """
    root = Path(root)
    py_files = list(_iter_py_files(root, exclude_tests))
    index = _build_module_index(py_files, root)

    graph: dict[str, list[str]] = {}
    for fp in py_files:
        deps: list[str] = []
        try:
            tree = ast.parse(fp.read_text(encoding="utf-8", errors="replace"))
        except (SyntaxError, ValueError):
            graph[str(fp)] = []
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    target = _resolve_import(alias.name, fp, root, index, level=0)
                    if target and str(target) != str(fp):
                        deps.append(str(target))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                target = _resolve_import(module, fp, root, index, level=node.level)
                if target and str(target) != str(fp):
                    deps.append(str(target))
        # Dedupe while preserving order.
        seen: set[str] = set()
        graph[str(fp)] = [d for d in deps if not (d in seen or seen.add(d))]
    return graph


def build_js_graph(root: Path, exclude_tests: bool = True) -> dict[str, list[str]]:
    """Placeholder — implemented in Task 4."""
    raise NotImplementedError("build_js_graph lands in Task 4")
```

- [ ] **Step 4: Run tests, verify all pass**

```bash
PYTHONPATH=skills/code-quality/scripts python3 -m unittest discover -s skills/code-quality/scripts/arch_review/tests -v
```
Expected: 6 tests pass.

- [ ] **Step 5: Commit**

```bash
git add skills/code-quality/scripts/arch_review/graph.py skills/code-quality/scripts/arch_review/tests/test_graph.py
git commit -m "feat: ast-based Python dependency graph for arch_review"
```

---

## Task 4: JS/TS dependency graph via madge

**Files:**
- Modify: `skills/code-quality/scripts/arch_review/graph.py`
- Modify: `skills/code-quality/scripts/arch_review/tests/test_graph.py`

- [ ] **Step 1: Write failing tests for entry-point detection and JS graph**

Append to `skills/code-quality/scripts/arch_review/tests/test_graph.py`:
```python
from arch_review.graph import detect_ts_entry_point, build_js_graph


class DetectTSEntryPointTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_prefers_package_json_main(self) -> None:
        write_file(self.root, "package.json", '{"main": "dist/index.js"}')
        write_file(self.root, "src/index.ts", "")
        write_file(self.root, "dist/index.js", "")
        self.assertEqual(detect_ts_entry_point(self.root), self.root / "dist/index.js")

    def test_falls_back_to_src_index_ts(self) -> None:
        write_file(self.root, "src/index.ts", "")
        self.assertEqual(detect_ts_entry_point(self.root), self.root / "src/index.ts")

    def test_falls_back_to_src_server_ts(self) -> None:
        write_file(self.root, "src/server.ts", "")
        self.assertEqual(detect_ts_entry_point(self.root), self.root / "src/server.ts")

    def test_returns_none_when_no_entry_point(self) -> None:
        write_file(self.root, "README.md", "")
        self.assertIsNone(detect_ts_entry_point(self.root))


class BuildJsGraphTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_parses_madge_json_output(self) -> None:
        # Use the internal parser directly with a synthetic madge payload.
        from arch_review.graph import _parse_madge_json
        payload = json.dumps({
            "src/a.ts": ["src/b.ts"],
            "src/b.ts": [],
        })
        graph = _parse_madge_json(payload, self.root)
        a = str(self.root / "src/a.ts")
        b = str(self.root / "src/b.ts")
        self.assertEqual(graph[a], [b])
        self.assertEqual(graph[b], [])
```

You also need `import json` at the top of the test module — add it if not present.

- [ ] **Step 2: Run tests, verify failure**

```bash
PYTHONPATH=skills/code-quality/scripts python3 -m unittest discover -s skills/code-quality/scripts/arch_review/tests -v
```
Expected: `ImportError: cannot import name 'detect_ts_entry_point' from 'arch_review.graph'`.

- [ ] **Step 3: Implement entry-point detection and JS graph in `graph.py`**

Replace the `build_js_graph` stub in `skills/code-quality/scripts/arch_review/graph.py` with:
```python
TS_FALLBACK_ENTRIES = (
    "src/index.ts", "src/index.tsx",
    "src/server.ts", "src/main.ts", "src/app.ts",
)


def detect_ts_entry_point(root: Path) -> Path | None:
    """Pick a TypeScript entry point for madge.

    Priority: package.json main → package.json module → conventional src/ files.
    Returns absolute path or None if nothing found.
    """
    pkg = root / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
        for key in ("main", "module"):
            value = data.get(key)
            if isinstance(value, str):
                candidate = (root / value).resolve()
                if candidate.exists():
                    return candidate
    for rel in TS_FALLBACK_ENTRIES:
        candidate = root / rel
        if candidate.exists():
            return candidate
    return None


def _parse_madge_json(payload: str, root: Path) -> dict[str, list[str]]:
    """Convert madge's relative-path JSON output to absolute-path adjacency dict."""
    raw = json.loads(payload)
    graph: dict[str, list[str]] = {}
    for src, deps in raw.items():
        src_abs = str((root / src).resolve())
        graph[src_abs] = [str((root / d).resolve()) for d in deps]
    return graph


def build_js_graph(root: Path, exclude_tests: bool = True) -> dict[str, list[str]]:
    """Build JS/TS dependency graph via `npx madge --json`.

    Returns: {file_path: [imported_file_paths, ...]}
    Raises RuntimeError if madge cannot resolve an entry point or fails.
    """
    root = Path(root)
    has_tsconfig = (root / "tsconfig.json").exists()
    cmd: list[str] = ["npx", "--yes", "madge", "--json"]
    if has_tsconfig:
        entry = detect_ts_entry_point(root)
        if entry is None:
            raise RuntimeError("no detectable TypeScript entry point — add a `main` to package.json or src/index.ts")
        cmd += ["--ts-config", str(root / "tsconfig.json"), "--extensions", "ts,tsx", str(entry)]
    else:
        cmd += [str(root / "src") if (root / "src").exists() else str(root)]
    if exclude_tests:
        cmd += ["--exclude", "(__tests__|\\.test\\.|\\.spec\\.|node_modules|dist|build|coverage)"]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(root))
    if proc.returncode not in (0, 1):  # 1 = cycles found, expected
        raise RuntimeError(f"madge failed: {proc.stderr.strip()}")
    return _parse_madge_json(proc.stdout, root)
```

- [ ] **Step 4: Run tests, verify all pass**

```bash
PYTHONPATH=skills/code-quality/scripts python3 -m unittest discover -s skills/code-quality/scripts/arch_review/tests -v
```
Expected: 10 tests pass total (6 from Task 3 + 4 new TS entry-point + 1 new madge parse = 11). If any fail, fix the implementation.

- [ ] **Step 5: Commit**

```bash
git add skills/code-quality/scripts/arch_review/graph.py skills/code-quality/scripts/arch_review/tests/test_graph.py
git commit -m "feat: JS/TS dependency graph via madge with entry-point detection"
```

---

## Task 5: Cycle detection (Tarjan SCC) + coupling metrics + deep chains

**Files:**
- Create: `skills/code-quality/scripts/arch_review/metrics.py`
- Create: `skills/code-quality/scripts/arch_review/tests/test_metrics.py`

- [ ] **Step 1: Write failing tests for cycles, coupling, deep chains**

Create `skills/code-quality/scripts/arch_review/tests/test_metrics.py`:
```python
"""Unit tests for metrics.py."""
from __future__ import annotations

import unittest

from arch_review.metrics import find_cycles, compute_coupling, find_deep_chains


class FindCyclesTest(unittest.TestCase):
    def test_no_cycles_in_dag(self) -> None:
        graph = {"a": ["b"], "b": ["c"], "c": []}
        self.assertEqual(find_cycles(graph), [])

    def test_finds_two_node_cycle(self) -> None:
        graph = {"a": ["b"], "b": ["a"]}
        cycles = find_cycles(graph)
        self.assertEqual(len(cycles), 1)
        self.assertEqual(set(cycles[0]), {"a", "b"})

    def test_finds_three_node_cycle(self) -> None:
        graph = {"a": ["b"], "b": ["c"], "c": ["a"]}
        cycles = find_cycles(graph)
        self.assertEqual(len(cycles), 1)
        self.assertEqual(set(cycles[0]), {"a", "b", "c"})

    def test_finds_multiple_independent_cycles(self) -> None:
        graph = {
            "a": ["b"], "b": ["a"],
            "c": ["d"], "d": ["c"],
            "e": [],
        }
        cycles = find_cycles(graph)
        self.assertEqual(len(cycles), 2)


class ComputeCouplingTest(unittest.TestCase):
    def test_isolated_node(self) -> None:
        graph = {"a": []}
        m = compute_coupling(graph)
        self.assertEqual(m["a"], {"ca": 0, "ce": 0, "i": 0.0})

    def test_simple_chain(self) -> None:
        graph = {"a": ["b"], "b": ["c"], "c": []}
        m = compute_coupling(graph)
        # a: imports b (Ce=1), no importers (Ca=0)
        self.assertEqual(m["a"]["ca"], 0)
        self.assertEqual(m["a"]["ce"], 1)
        self.assertEqual(m["a"]["i"], 1.0)
        # b: imported by a (Ca=1), imports c (Ce=1)
        self.assertEqual(m["b"]["ca"], 1)
        self.assertEqual(m["b"]["ce"], 1)
        self.assertEqual(m["b"]["i"], 0.5)
        # c: imported by b (Ca=1), no imports (Ce=0)
        self.assertEqual(m["c"]["ca"], 1)
        self.assertEqual(m["c"]["ce"], 0)
        self.assertEqual(m["c"]["i"], 0.0)

    def test_hub_module(self) -> None:
        # a, b, c, d all import e
        graph = {"a": ["e"], "b": ["e"], "c": ["e"], "d": ["e"], "e": []}
        m = compute_coupling(graph)
        self.assertEqual(m["e"]["ca"], 4)
        self.assertEqual(m["e"]["ce"], 0)


class FindDeepChainsTest(unittest.TestCase):
    def test_linear_chain(self) -> None:
        graph = {"a": ["b"], "b": ["c"], "c": ["d"], "d": []}
        chains = find_deep_chains(graph, min_depth=3)
        self.assertTrue(any(c[0] == "a" and c[-1] == "d" for c in chains))

    def test_does_not_report_chains_shorter_than_min(self) -> None:
        graph = {"a": ["b"], "b": []}
        chains = find_deep_chains(graph, min_depth=3)
        self.assertEqual(chains, [])

    def test_safe_with_cycle(self) -> None:
        # Cycle must not cause infinite recursion.
        graph = {"a": ["b"], "b": ["a"]}
        chains = find_deep_chains(graph, min_depth=3)
        # No chain longer than 2 unique nodes is possible; just verify it returns.
        self.assertIsInstance(chains, list)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests, verify failure**

```bash
PYTHONPATH=skills/code-quality/scripts python3 -m unittest discover -s skills/code-quality/scripts/arch_review/tests -v
```
Expected: `ModuleNotFoundError: arch_review.metrics`.

- [ ] **Step 3: Implement `metrics.py`**

Create `skills/code-quality/scripts/arch_review/metrics.py`:
```python
"""Graph metrics — cycles, coupling (Ca/Ce/I), deep chains."""
from __future__ import annotations

from typing import Dict, List


def find_cycles(graph: Dict[str, List[str]]) -> List[List[str]]:
    """Find all simple cycles via Tarjan's SCC algorithm.

    Returns a list of cycles, each cycle being a list of node ids. A non-trivial
    SCC (size > 1, or single-node with self-loop) counts as a cycle.
    """
    index_counter = [0]
    stack: List[str] = []
    lowlinks: Dict[str, int] = {}
    indices: Dict[str, int] = {}
    on_stack: Dict[str, bool] = {}
    result: List[List[str]] = []

    def strongconnect(node: str) -> None:
        indices[node] = index_counter[0]
        lowlinks[node] = index_counter[0]
        index_counter[0] += 1
        stack.append(node)
        on_stack[node] = True

        for successor in graph.get(node, []):
            if successor not in indices:
                strongconnect(successor)
                lowlinks[node] = min(lowlinks[node], lowlinks[successor])
            elif on_stack.get(successor):
                lowlinks[node] = min(lowlinks[node], indices[successor])

        if lowlinks[node] == indices[node]:
            scc: List[str] = []
            while True:
                w = stack.pop()
                on_stack[w] = False
                scc.append(w)
                if w == node:
                    break
            if len(scc) > 1 or (len(scc) == 1 and scc[0] in graph.get(scc[0], [])):
                result.append(scc)

    for n in list(graph):
        if n not in indices:
            strongconnect(n)
    return result


def compute_coupling(graph: Dict[str, List[str]]) -> Dict[str, Dict[str, float]]:
    """Compute Ca (afferent), Ce (efferent), I (instability) per node.

    I = Ce / (Ca + Ce), defaulting to 0.0 when both are zero.
    """
    ca: Dict[str, int] = {n: 0 for n in graph}
    ce: Dict[str, int] = {n: len(set(deps)) for n, deps in graph.items()}
    for src, deps in graph.items():
        for d in set(deps):
            if d in ca:
                ca[d] += 1
    out: Dict[str, Dict[str, float]] = {}
    for n in graph:
        denom = ca[n] + ce[n]
        i = (ce[n] / denom) if denom else 0.0
        out[n] = {"ca": ca[n], "ce": ce[n], "i": round(i, 3)}
    return out


def find_deep_chains(graph: Dict[str, List[str]], min_depth: int = 6, max_paths: int = 50) -> List[List[str]]:
    """Find the deepest acyclic import chains.

    Returns up to `max_paths` chains of length >= min_depth, sorted by length descending.
    Cycle-safe via a per-path visited set.
    """
    chains: List[List[str]] = []

    def dfs(node: str, path: List[str], visited: set) -> None:
        if len(chains) >= max_paths and any(len(c) > len(path) for c in chains):
            return  # already have enough longer chains
        successors = [s for s in graph.get(node, []) if s not in visited]
        if not successors:
            if len(path) >= min_depth:
                chains.append(list(path))
            return
        for s in successors:
            visited.add(s)
            path.append(s)
            dfs(s, path, visited)
            path.pop()
            visited.discard(s)

    for start in list(graph):
        dfs(start, [start], {start})

    chains.sort(key=len, reverse=True)
    return chains[:max_paths]
```

- [ ] **Step 4: Run tests, verify all pass**

```bash
PYTHONPATH=skills/code-quality/scripts python3 -m unittest discover -s skills/code-quality/scripts/arch_review/tests -v
```
Expected: all metric tests pass.

- [ ] **Step 5: Commit**

```bash
git add skills/code-quality/scripts/arch_review/metrics.py skills/code-quality/scripts/arch_review/tests/test_metrics.py
git commit -m "feat: cycle detection, coupling metrics, deep chains for arch_review"
```

---

## Task 6: Layer inference and violation detection

**Files:**
- Create: `skills/code-quality/scripts/arch_review/layers.py`
- Create: `skills/code-quality/scripts/arch_review/tests/test_layers.py`

- [ ] **Step 1: Write failing tests**

Create `skills/code-quality/scripts/arch_review/tests/test_layers.py`:
```python
"""Unit tests for layers.py."""
from __future__ import annotations

import unittest

from arch_review.layers import infer_layer, assign_layers, find_layer_violations


class InferLayerTest(unittest.TestCase):
    def test_presentation_match(self) -> None:
        self.assertEqual(infer_layer("src/api/users.py", "none"), "presentation")
        self.assertEqual(infer_layer("src/routes/auth.ts", "none"), "presentation")

    def test_application_match(self) -> None:
        self.assertEqual(infer_layer("src/services/orders.py", "none"), "application")
        self.assertEqual(infer_layer("src/usecases/checkout.ts", "none"), "application")

    def test_domain_match(self) -> None:
        self.assertEqual(infer_layer("src/domain/user.py", "none"), "domain")
        self.assertEqual(infer_layer("src/entities/order.py", "none"), "domain")

    def test_infrastructure_match(self) -> None:
        self.assertEqual(infer_layer("src/db/session.py", "none"), "infrastructure")
        self.assertEqual(infer_layer("src/repositories/user_repo.py", "none"), "infrastructure")

    def test_unclassified(self) -> None:
        self.assertIsNone(infer_layer("src/foo/bar.py", "none"))

    def test_nextjs_app_is_presentation(self) -> None:
        self.assertEqual(infer_layer("app/dashboard/page.tsx", "nextjs"), "presentation")
        self.assertEqual(infer_layer("pages/index.tsx", "nextjs"), "presentation")

    def test_django_models_is_infrastructure(self) -> None:
        # Per spec: Django models.py and models/ map to infrastructure (ORM-bound).
        self.assertEqual(infer_layer("myapp/models.py", "django"), "infrastructure")
        self.assertEqual(infer_layer("myapp/models/user.py", "django"), "infrastructure")
        # Without the Django framework hint, `models/` falls back to domain.
        self.assertEqual(infer_layer("myapp/models/user.py", "none"), "domain")

    def test_fastapi_routers_is_presentation(self) -> None:
        self.assertEqual(infer_layer("src/routers/users.py", "fastapi"), "presentation")


class FindLayerViolationsTest(unittest.TestCase):
    def test_detects_domain_to_infrastructure(self) -> None:
        graph = {
            "src/domain/order.py": ["src/db/session.py"],
            "src/db/session.py": [],
        }
        layers = {"src/domain/order.py": "domain", "src/db/session.py": "infrastructure"}
        violations = find_layer_violations(graph, layers)
        self.assertEqual(len(violations), 1)
        v = violations[0]
        self.assertEqual(v["importer_layer"], "domain")
        self.assertEqual(v["imported_layer"], "infrastructure")

    def test_allows_outer_to_inner(self) -> None:
        graph = {
            "src/api/users.py": ["src/domain/user.py"],
            "src/domain/user.py": [],
        }
        layers = {"src/api/users.py": "presentation", "src/domain/user.py": "domain"}
        violations = find_layer_violations(graph, layers)
        self.assertEqual(violations, [])

    def test_unclassified_imports_are_ignored(self) -> None:
        graph = {
            "src/foo/bar.py": ["src/db/session.py"],
            "src/db/session.py": [],
        }
        layers = {"src/foo/bar.py": None, "src/db/session.py": "infrastructure"}
        violations = find_layer_violations(graph, layers)
        self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests, verify failure**

```bash
PYTHONPATH=skills/code-quality/scripts python3 -m unittest discover -s skills/code-quality/scripts/arch_review/tests -v
```
Expected: `ModuleNotFoundError: arch_review.layers`.

- [ ] **Step 3: Implement `layers.py`**

Create `skills/code-quality/scripts/arch_review/layers.py`:
```python
"""Heuristic layer inference + Dependency Rule violation detection."""
from __future__ import annotations

from typing import Dict, List, Optional

# Convergent default mapping. Substring match against any path segment.
DEFAULT_LAYER_MAP: Dict[str, tuple[str, ...]] = {
    "presentation": ("ui", "views", "routes", "routers", "controllers", "api", "pages", "app", "web", "http", "handlers"),
    "application": ("services", "usecases", "use_cases", "commands", "queries", "application", "core"),
    "domain": ("domain", "entities", "models", "business"),
    "infrastructure": ("infrastructure", "infra", "adapters", "repositories", "repos", "db", "persistence", "storage", "clients"),
}

# Framework-specific overrides applied IN ADDITION to the default map.
# Each entry maps a segment name to a layer; framework override wins.
FRAMEWORK_OVERRIDES: Dict[str, Dict[str, str]] = {
    "nextjs": {
        "app": "presentation",
        "pages": "presentation",
    },
    "django": {
        "models": "infrastructure",
        "views": "presentation",
        "admin": "presentation",
    },
    "nestjs": {
        "handlers": "application",
        "controllers": "presentation",
        "dto": "application",
    },
    "fastapi": {
        "routers": "presentation",
        "endpoints": "presentation",
        "dependencies": "application",
    },
    "flask": {
        "views": "presentation",
        "routes": "presentation",
        "blueprints": "presentation",
    },
    "express": {
        "routes": "presentation",
        "controllers": "presentation",
        "middleware": "presentation",
    },
    "none": {},
}

# Allowed transitions (importer_layer → imported_layer). Anything else is a violation.
ALLOWED_TRANSITIONS = {
    ("presentation", "application"),
    ("presentation", "domain"),
    ("application", "domain"),
    ("infrastructure", "application"),
    ("infrastructure", "domain"),
    # Same-layer imports are always allowed.
}


def _path_segments(path: str) -> list[str]:
    return [seg for seg in path.replace("\\", "/").split("/") if seg]


def infer_layer(path: str, framework: str) -> Optional[str]:
    """Infer layer from a file path. Returns None if unclassified."""
    segments = _path_segments(path)
    overrides = FRAMEWORK_OVERRIDES.get(framework, {})
    # Stem-name match for files like models.py / views.py.
    last = segments[-1].rsplit(".", 1)[0] if segments else ""
    # Framework override (file-stem level).
    if last in overrides:
        return overrides[last]
    # Framework override (any path segment).
    for seg in segments:
        if seg in overrides:
            return overrides[seg]
    # Default mapping (any path segment).
    for layer, names in DEFAULT_LAYER_MAP.items():
        for seg in segments:
            if seg in names:
                return layer
        if last in names:
            return layer
    return None


def assign_layers(nodes: List[str], framework: str, project_root: str = "") -> Dict[str, Optional[str]]:
    """Assign a layer to every node. Returns {path: layer_or_none}."""
    result: Dict[str, Optional[str]] = {}
    for n in nodes:
        rel = n[len(project_root):] if project_root and n.startswith(project_root) else n
        result[n] = infer_layer(rel, framework)
    return result


def find_layer_violations(
    graph: Dict[str, List[str]],
    layers: Dict[str, Optional[str]],
) -> List[Dict[str, str]]:
    """Find imports that violate the Dependency Rule (inner → outer).

    Returns a list of findings with importer/imported/layer info.
    """
    violations: List[Dict[str, str]] = []
    for src, deps in graph.items():
        src_layer = layers.get(src)
        if src_layer is None:
            continue
        for d in deps:
            d_layer = layers.get(d)
            if d_layer is None or d_layer == src_layer:
                continue
            if (src_layer, d_layer) in ALLOWED_TRANSITIONS:
                continue
            violations.append({
                "importer": src,
                "importer_layer": src_layer,
                "imported": d,
                "imported_layer": d_layer,
            })
    return violations
```

- [ ] **Step 4: Run tests, verify all pass**

```bash
PYTHONPATH=skills/code-quality/scripts python3 -m unittest discover -s skills/code-quality/scripts/arch_review/tests -v
```
Expected: all layer tests pass.

- [ ] **Step 5: Commit**

```bash
git add skills/code-quality/scripts/arch_review/layers.py skills/code-quality/scripts/arch_review/tests/test_layers.py
git commit -m "feat: heuristic layer inference + Dependency Rule violations"
```

---

## Task 7: Smells — file LoC and excessive exports

**Files:**
- Create: `skills/code-quality/scripts/arch_review/smells.py`
- Create: `skills/code-quality/scripts/arch_review/tests/test_smells.py`

- [ ] **Step 1: Write failing tests**

Create `skills/code-quality/scripts/arch_review/tests/test_smells.py`:
```python
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
            self.assertEqual(count_loc(path), 2)  # `def f():` and `return 1`
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
            self.assertEqual(count_exports(path, "python"), 2)  # public_fn + Public
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
```

- [ ] **Step 2: Run tests, verify failure**

```bash
PYTHONPATH=skills/code-quality/scripts python3 -m unittest discover -s skills/code-quality/scripts/arch_review/tests -v
```
Expected: `ModuleNotFoundError: arch_review.smells`.

- [ ] **Step 3: Implement `smells.py`**

Create `skills/code-quality/scripts/arch_review/smells.py`:
```python
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
PY_EXPORT_DEF_RE = re.compile(r"^(def|class)\s+([A-Za-z][A-Za-z0-9_]*)")
JS_EXPORT_RE = re.compile(r"^\s*export\s+(default\s+)?(function|class|const|let|var|interface|type|enum|async\s+function)")


def count_loc(path: Path) -> int:
    """Count code lines (blank + comment lines stripped)."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0
    suffix = path.suffix.lower()
    if suffix == ".py":
        lines = [
            line for line in text.splitlines()
            if line.strip() and not PY_COMMENT_RE.match(line)
        ]
        return len(lines)
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
        # Prefer __all__ if explicitly defined.
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return 0
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


def find_excessive_exports(files: Iterable[Path], language: str, threshold: int) -> List[Dict[str, object]]:
    """Return files with export count above `threshold`."""
    out: List[Dict[str, object]] = []
    for f in files:
        c = count_exports(f, language)
        if c > threshold:
            out.append({"file": str(f), "exports": c})
    out.sort(key=lambda x: x["exports"], reverse=True)
    return out
```

- [ ] **Step 4: Run tests, verify all pass**

```bash
PYTHONPATH=skills/code-quality/scripts python3 -m unittest discover -s skills/code-quality/scripts/arch_review/tests -v
```
Expected: all smells tests pass.

- [ ] **Step 5: Commit**

```bash
git add skills/code-quality/scripts/arch_review/smells.py skills/code-quality/scripts/arch_review/tests/test_smells.py
git commit -m "feat: LoC + excessive-exports detection for arch_review"
```

---

## Task 8: Dead code — knip + vulture subprocess wrappers

**Files:**
- Create: `skills/code-quality/scripts/arch_review/dead_code.py`
- Create: `skills/code-quality/scripts/arch_review/tests/test_dead_code.py`

- [ ] **Step 1: Write failing tests**

Create `skills/code-quality/scripts/arch_review/tests/test_dead_code.py`:
```python
"""Unit tests for dead_code.py.

We don't invoke knip/vulture for real here — we test the parsers against
synthetic CLI outputs.
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
```

- [ ] **Step 2: Run tests, verify failure**

```bash
PYTHONPATH=skills/code-quality/scripts python3 -m unittest discover -s skills/code-quality/scripts/arch_review/tests -v
```
Expected: `ModuleNotFoundError: arch_review.dead_code`.

- [ ] **Step 3: Implement `dead_code.py`**

Create `skills/code-quality/scripts/arch_review/dead_code.py`:
```python
"""Dead-code wrappers — knip (JS/TS) and vulture (Python)."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List

VULTURE_LINE_RE = re.compile(
    r"^(?P<file>.+?):(?P<line>\d+):\s+(?P<message>.+?)\s+\((?P<confidence>\d+)% confidence\)\s*$"
)


def _parse_knip_json(payload: str) -> List[Dict[str, object]]:
    """Parse knip's JSON output into a flat list of findings."""
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return []
    findings: List[Dict[str, object]] = []
    for f in data.get("files", []) or []:
        findings.append({"kind": "unused_file", "file": f})
    exports = data.get("exports", {}) or {}
    for file, items in exports.items():
        for item in items or []:
            findings.append({
                "kind": "unused_export",
                "file": file,
                "name": item.get("name", ""),
                "line": item.get("line", 0),
            })
    return findings


def _parse_vulture_text(text: str) -> List[Dict[str, object]]:
    """Parse vulture's text output into a flat list of findings."""
    findings: List[Dict[str, object]] = []
    for line in text.splitlines():
        m = VULTURE_LINE_RE.match(line)
        if not m:
            continue
        findings.append({
            "file": m.group("file"),
            "line": int(m.group("line")),
            "message": m.group("message"),
            "confidence": int(m.group("confidence")),
        })
    return findings


def run_knip(project_root: Path, timeout: int = 60) -> Dict[str, object]:
    """Run `npx knip --reporter json`. Returns {status, findings|reason}."""
    if not shutil.which("npx"):
        return {"status": "skipped", "reason": "npx not available"}
    try:
        proc = subprocess.run(
            ["npx", "--yes", "knip", "--reporter", "json"],
            capture_output=True, text=True, cwd=str(project_root), timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"status": "error", "reason": "knip timed out"}
    if proc.returncode > 1:
        return {"status": "error", "reason": proc.stderr.strip() or "knip failed"}
    return {"status": "found" if proc.stdout.strip() else "ok", "findings": _parse_knip_json(proc.stdout)}


def run_vulture(project_root: Path, min_confidence: int = 80, timeout: int = 60) -> Dict[str, object]:
    """Run `uvx vulture <root> --min-confidence N`. Returns {status, findings|reason}."""
    if not shutil.which("uvx"):
        return {"status": "skipped", "reason": "uvx not available"}
    try:
        proc = subprocess.run(
            ["uvx", "vulture", str(project_root), "--min-confidence", str(min_confidence)],
            capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"status": "error", "reason": "vulture timed out"}
    # vulture exits 0 (clean), 1 (findings), 2+ (error)
    if proc.returncode > 1:
        return {"status": "error", "reason": proc.stderr.strip() or "vulture failed"}
    findings = _parse_vulture_text(proc.stdout)
    return {"status": "found" if findings else "ok", "findings": findings}
```

- [ ] **Step 4: Run tests, verify all pass**

```bash
PYTHONPATH=skills/code-quality/scripts python3 -m unittest discover -s skills/code-quality/scripts/arch_review/tests -v
```
Expected: all dead-code parser tests pass. (The subprocess functions `run_knip` and `run_vulture` are not exercised by unit tests — they're covered by smoke tests in Task 13/18.)

- [ ] **Step 5: Commit**

```bash
git add skills/code-quality/scripts/arch_review/dead_code.py skills/code-quality/scripts/arch_review/tests/test_dead_code.py
git commit -m "feat: knip + vulture dead-code wrappers for arch_review"
```

---

## Task 9: Complex functions — Workflow E command wrappers

**Files:**
- Create: `skills/code-quality/scripts/arch_review/complexity.py`
- Create: `skills/code-quality/scripts/arch_review/tests/test_complexity.py`

- [ ] **Step 1: Write failing tests**

Create `skills/code-quality/scripts/arch_review/tests/test_complexity.py`:
```python
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
```

- [ ] **Step 2: Run tests, verify failure**

```bash
PYTHONPATH=skills/code-quality/scripts python3 -m unittest discover -s skills/code-quality/scripts/arch_review/tests -v
```
Expected: `ModuleNotFoundError: arch_review.complexity`.

- [ ] **Step 3: Implement `complexity.py`**

Create `skills/code-quality/scripts/arch_review/complexity.py`:
```python
"""Wrapper around Workflow E's complexity commands (ruff C901, eslint complexity rule)."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List

RUFF_C901_MSG_RE = re.compile(r"`?(?P<fn>[A-Za-z_][A-Za-z0-9_]*)`?\s+is too complex\s+\((?P<cc>\d+)\s*>\s*(?P<max>\d+)\)")
ESLINT_COMPLEXITY_MSG_RE = re.compile(r"['\"](?P<fn>[A-Za-z_][A-Za-z0-9_]*)['\"]?.*?complexity of (?P<cc>\d+).*?Maximum allowed is (?P<max>\d+)")


def _parse_ruff_c901(payload: str) -> List[Dict[str, object]]:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return []
    findings: List[Dict[str, object]] = []
    for item in data:
        if item.get("code") != "C901":
            continue
        m = RUFF_C901_MSG_RE.search(item.get("message", ""))
        if not m:
            continue
        findings.append({
            "file": item.get("filename", ""),
            "line": item.get("location", {}).get("row", 0),
            "function": m.group("fn"),
            "complexity": int(m.group("cc")),
            "threshold": int(m.group("max")),
        })
    return findings


def _parse_eslint_complexity(payload: str) -> List[Dict[str, object]]:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return []
    findings: List[Dict[str, object]] = []
    for file_entry in data:
        file_path = file_entry.get("filePath", "")
        for msg in file_entry.get("messages", []) or []:
            if msg.get("ruleId") != "complexity":
                continue
            m = ESLINT_COMPLEXITY_MSG_RE.search(msg.get("message", ""))
            if not m:
                continue
            findings.append({
                "file": file_path,
                "line": msg.get("line", 0),
                "function": m.group("fn"),
                "complexity": int(m.group("cc")),
                "threshold": int(m.group("max")),
            })
    return findings


def run_complexity_check(project_root: Path, language: str, timeout: int = 60) -> Dict[str, object]:
    if language == "python":
        if not shutil.which("uvx") and not shutil.which("ruff"):
            return {"status": "skipped", "reason": "neither uvx nor ruff is available"}
        cmd = ["uvx", "ruff", "check", "--select", "C901", "--output-format", "json", str(project_root)]
        if not shutil.which("uvx"):
            cmd = ["ruff", "check", "--select", "C901", "--output-format", "json", str(project_root)]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return {"status": "error", "reason": "ruff timed out"}
        if proc.returncode > 1:
            return {"status": "error", "reason": proc.stderr.strip() or "ruff failed"}
        findings = _parse_ruff_c901(proc.stdout)
        return {"status": "found" if findings else "ok", "findings": findings}
    if language == "javascript":
        if not shutil.which("npx"):
            return {"status": "skipped", "reason": "npx not available"}
        cmd = [
            "npx", "--yes", "eslint",
            "--rule", '{"complexity": ["warn", 10]}',
            "--format", "json",
            str(project_root),
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return {"status": "error", "reason": "eslint timed out"}
        if proc.returncode > 2:
            return {"status": "error", "reason": proc.stderr.strip() or "eslint failed"}
        findings = _parse_eslint_complexity(proc.stdout)
        return {"status": "found" if findings else "ok", "findings": findings}
    return {"status": "skipped", "reason": f"unsupported language: {language}"}
```

- [ ] **Step 4: Run tests, verify all pass**

```bash
PYTHONPATH=skills/code-quality/scripts python3 -m unittest discover -s skills/code-quality/scripts/arch_review/tests -v
```
Expected: all complexity tests pass.

- [ ] **Step 5: Commit**

```bash
git add skills/code-quality/scripts/arch_review/complexity.py skills/code-quality/scripts/arch_review/tests/test_complexity.py
git commit -m "feat: complexity (Workflow E) wrapper for arch_review"
```

---

## Task 10: Runner orchestrator + JSON output

**Files:**
- Create: `skills/code-quality/scripts/arch_review/runner.py`
- Create: `skills/code-quality/scripts/arch_review/tests/test_runner.py`

- [ ] **Step 1: Write failing tests using a synthetic Python fixture**

Create `skills/code-quality/scripts/arch_review/tests/test_runner.py`:
```python
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
        self.root = Path(self._tmp.name)
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
        # Skip dead_code & complex_functions — they need subprocess tools we don't
        # want to depend on in unit tests.
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
        json.dumps(result)  # raises if not serializable

    def test_monorepo_warning_when_workspaces_present(self) -> None:
        # Add a package.json with workspaces — should trigger monorepo warning.
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
```

- [ ] **Step 2: Run tests, verify failure**

```bash
PYTHONPATH=skills/code-quality/scripts python3 -m unittest discover -s skills/code-quality/scripts/arch_review/tests -v
```
Expected: `ModuleNotFoundError: arch_review.runner`.

- [ ] **Step 3: Implement `runner.py`**

Create `skills/code-quality/scripts/arch_review/runner.py`:
```python
"""Orchestrator — runs sub-checks in parallel and assembles the JSON report."""
from __future__ import annotations

import concurrent.futures
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from arch_review import complexity, dead_code, graph, layers, metrics, smells


def _detect_monorepo(root: Path) -> Optional[str]:
    """Return a short description of the monorepo flavour if detected, else None."""
    if (root / "pnpm-workspace.yaml").exists():
        return "pnpm workspaces"
    if (root / "lerna.json").exists():
        return "lerna"
    if (root / "turbo.json").exists():
        return "turborepo"
    pkg = root / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
        if "workspaces" in data:
            return "npm/yarn workspaces"
    pyproj = root / "pyproject.toml"
    if pyproj.exists():
        try:
            text = pyproj.read_text(encoding="utf-8")
        except OSError:
            text = ""
        if "[tool.uv.workspace]" in text:
            return "uv workspace"
    return None

ALL_SECTIONS = [
    "cycles", "layering", "hubs", "gods", "unstable_central",
    "deep_chains", "oversized_files", "excessive_exports",
    "dead_code", "complex_functions",
]

# Severity mapping
SEV_CRT, SEV_MAJ, SEV_MIN, SEV_INF = "CRT", "MAJ", "MIN", "INF"


def _highest_severity(sevs: List[str]) -> Optional[str]:
    order = [SEV_CRT, SEV_MAJ, SEV_MIN, SEV_INF]
    for s in order:
        if s in sevs:
            return s
    return None


def _section_cycles(graph_data: Dict[str, List[str]]) -> Dict[str, Any]:
    cycles = metrics.find_cycles(graph_data)
    findings = [{"modules": c, "severity": SEV_CRT} for c in cycles]
    return {
        "status": "found" if findings else "ok",
        "severity": SEV_CRT if findings else None,
        "findings": findings,
    }


def _section_layering(graph_data: Dict[str, List[str]], framework: str, root: str) -> Dict[str, Any]:
    layer_map = layers.assign_layers(list(graph_data), framework, project_root=root)
    inferred = {}
    for path, layer in layer_map.items():
        if layer is None:
            continue
        inferred.setdefault(layer, set()).add(str(Path(path).parent))
    violations = layers.find_layer_violations(graph_data, layer_map)
    for v in violations:
        v["severity"] = SEV_MAJ
    return {
        "status": "found" if violations else "ok",
        "severity": SEV_MAJ if violations else None,
        "inferred_layers": {k: sorted(list(v)) for k, v in inferred.items()},
        "findings": violations,
    }


def _section_hubs(coupling: Dict[str, Dict[str, float]], top: int, max_ca: int) -> Dict[str, Any]:
    sorted_nodes = sorted(coupling.items(), key=lambda kv: kv[1]["ca"], reverse=True)
    findings = []
    for path, m in sorted_nodes[:top]:
        if m["ca"] <= max_ca:
            continue
        sev = SEV_MAJ if m["ca"] > max_ca * 2.5 else SEV_MIN
        findings.append({"file": path, "ca": m["ca"], "ce": m["ce"], "i": m["i"], "severity": sev})
    return {
        "status": "found" if findings else "ok",
        "severity": _highest_severity([f["severity"] for f in findings]),
        "findings": findings,
    }


def _section_gods(coupling: Dict[str, Dict[str, float]], top: int, max_ce: int) -> Dict[str, Any]:
    sorted_nodes = sorted(coupling.items(), key=lambda kv: kv[1]["ce"], reverse=True)
    findings = []
    for path, m in sorted_nodes[:top]:
        if m["ce"] <= max_ce:
            continue
        sev = SEV_MAJ if m["ce"] > max_ce * 2.5 else SEV_MIN
        findings.append({"file": path, "ca": m["ca"], "ce": m["ce"], "i": m["i"], "severity": sev})
    return {
        "status": "found" if findings else "ok",
        "severity": _highest_severity([f["severity"] for f in findings]),
        "findings": findings,
    }


def _section_unstable_central(coupling: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
    findings = []
    for path, m in coupling.items():
        if m["i"] > 0.7 and m["ca"] > 10:
            findings.append({"file": path, "ca": m["ca"], "ce": m["ce"], "i": m["i"], "severity": SEV_MAJ})
    findings.sort(key=lambda f: (f["ca"], f["i"]), reverse=True)
    return {
        "status": "found" if findings else "ok",
        "severity": SEV_MAJ if findings else None,
        "findings": findings,
    }


def _section_deep_chains(graph_data: Dict[str, List[str]], min_depth: int) -> Dict[str, Any]:
    chains = metrics.find_deep_chains(graph_data, min_depth=min_depth)
    findings = []
    for chain in chains:
        sev = SEV_MAJ if len(chain) > min_depth * 1.5 else SEV_MIN
        findings.append({"chain": chain, "depth": len(chain), "severity": sev})
    return {
        "status": "found" if findings else "ok",
        "severity": _highest_severity([f["severity"] for f in findings]),
        "findings": findings,
    }


def _section_oversized_files(files: List[Path], threshold: int) -> Dict[str, Any]:
    raw = smells.find_oversized_files(files, threshold)
    findings = []
    for entry in raw:
        sev = SEV_MAJ if entry["loc"] > threshold * 2 else SEV_MIN
        findings.append({**entry, "severity": sev})
    return {
        "status": "found" if findings else "ok",
        "severity": _highest_severity([f["severity"] for f in findings]),
        "findings": findings,
    }


def _section_excessive_exports(files: List[Path], language: str, threshold: int) -> Dict[str, Any]:
    raw = smells.find_excessive_exports(files, language, threshold)
    findings = []
    for entry in raw:
        sev = SEV_MAJ if entry["exports"] > threshold * 1.5 else SEV_MIN
        findings.append({**entry, "severity": sev})
    return {
        "status": "found" if findings else "ok",
        "severity": _highest_severity([f["severity"] for f in findings]),
        "findings": findings,
    }


def _section_dead_code(root: Path, language: str) -> Dict[str, Any]:
    if language == "javascript":
        outcome = dead_code.run_knip(root)
    else:
        outcome = dead_code.run_vulture(root)
    # Demote all dead-code findings to INF (per spec).
    findings = outcome.get("findings", []) if "findings" in outcome else []
    for f in findings:
        f["severity"] = SEV_INF
    if outcome["status"] in ("skipped", "error"):
        return {"status": outcome["status"], "reason": outcome.get("reason", "")}
    return {
        "status": outcome["status"],
        "severity": SEV_INF if findings else None,
        "findings": findings,
    }


def _section_complex_functions(root: Path, language: str) -> Dict[str, Any]:
    outcome = complexity.run_complexity_check(root, language)
    if outcome["status"] in ("skipped", "error"):
        return {"status": outcome["status"], "reason": outcome.get("reason", "")}
    findings = outcome.get("findings", [])
    for f in findings:
        f["severity"] = SEV_MAJ
    return {
        "status": outcome["status"],
        "severity": SEV_MAJ if findings else None,
        "findings": findings,
    }


def _enumerate_source_files(root: Path, language: str, exclude_tests: bool) -> List[Path]:
    if language == "python":
        return [p for p in graph._iter_py_files(root, exclude_tests)]
    extensions = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")
    files: List[Path] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in extensions:
            continue
        rel = p.relative_to(root)
        if graph._should_exclude(rel, exclude_tests):
            continue
        files.append(p)
    return files


def run_audit(
    project_root: Path | str,
    language: str,
    framework: str = "none",
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run the full architecture audit.

    Returns the JSON-serializable report. See references/architecture.md for schema.
    """
    options = options or {}
    project_root = Path(project_root).resolve()
    skip = set(options.get("skip_section", []))
    top = options.get("top", 10)
    include_tests = options.get("include_tests", False)
    max_file_loc = options.get("max_file_loc", 500)
    max_exports = options.get("max_exports", 30)
    max_ca = options.get("max_ca", 20)
    max_ce = options.get("max_ce", 20)
    max_chain_depth = options.get("max_chain_depth", 6)
    timeout = options.get("timeout_per_section", 60)

    started = time.time()
    warnings: List[str] = []
    errored: List[str] = []
    skipped: List[str] = list(skip)
    sections: Dict[str, Any] = {}

    mono = _detect_monorepo(project_root)
    if mono is not None:
        warnings.append(f"monorepo detected ({mono}) — running flat; metrics may be diluted")

    # Build the graph once. Sections 1-6 reuse it.
    graph_data: Dict[str, List[str]] = {}
    graph_error: Optional[str] = None
    try:
        if language == "python":
            graph_data = graph.build_python_graph(project_root, exclude_tests=not include_tests)
        elif language == "javascript":
            graph_data = graph.build_js_graph(project_root, exclude_tests=not include_tests)
        else:
            graph_error = f"unsupported language: {language}"
    except Exception as exc:
        graph_error = str(exc)

    files = _enumerate_source_files(project_root, language, exclude_tests=not include_tests)
    coupling = metrics.compute_coupling(graph_data) if graph_data else {}

    def safe(name: str, fn):
        if name in skip:
            return
        try:
            sections[name] = fn()
        except Exception as exc:
            errored.append(name)
            sections[name] = {"status": "error", "reason": str(exc)}

    # Graph-dependent sections (1-6) require graph_data; skip on failure.
    if graph_error:
        for sec in ("cycles", "layering", "hubs", "gods", "unstable_central", "deep_chains"):
            if sec in skip:
                continue
            sections[sec] = {"status": "error", "reason": f"graph extraction failed: {graph_error}"}
            errored.append(sec)
    else:
        safe("cycles", lambda: _section_cycles(graph_data))
        safe("layering", lambda: _section_layering(graph_data, framework, str(project_root)))
        safe("hubs", lambda: _section_hubs(coupling, top, max_ca))
        safe("gods", lambda: _section_gods(coupling, top, max_ce))
        safe("unstable_central", lambda: _section_unstable_central(coupling))
        safe("deep_chains", lambda: _section_deep_chains(graph_data, max_chain_depth))

    safe("oversized_files", lambda: _section_oversized_files(files, max_file_loc))
    safe("excessive_exports", lambda: _section_excessive_exports(files, language, max_exports))

    # Subprocess-heavy sections run in parallel with timeouts.
    if "dead_code" not in skip or "complex_functions" not in skip:
        pending: Dict[str, concurrent.futures.Future] = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as exe:
            if "dead_code" not in skip:
                pending["dead_code"] = exe.submit(_section_dead_code, project_root, language)
            if "complex_functions" not in skip:
                pending["complex_functions"] = exe.submit(_section_complex_functions, project_root, language)
            for name, fut in pending.items():
                try:
                    sections[name] = fut.result(timeout=timeout)
                except concurrent.futures.TimeoutError:
                    sections[name] = {"status": "error", "reason": "timed out"}
                    errored.append(name)
                except Exception as exc:
                    sections[name] = {"status": "error", "reason": str(exc)}
                    errored.append(name)

    sections_run = [s for s in ALL_SECTIONS if s in sections and sections[s].get("status") in ("ok", "found")]
    sections_skipped = [s for s in ALL_SECTIONS if s in skip or (s in sections and sections[s].get("status") == "skipped")]

    return {
        "summary": {
            "language": language,
            "framework": framework,
            "project_root": str(project_root),
            "files_scanned": len(files),
            "sections_run": len(sections_run),
            "sections_skipped": sections_skipped,
            "sections_errored": errored,
            "warnings": warnings,
            "elapsed_seconds": round(time.time() - started, 2),
        },
        "sections": sections,
    }
```

- [ ] **Step 4: Run tests, verify all pass**

```bash
PYTHONPATH=skills/code-quality/scripts python3 -m unittest discover -s skills/code-quality/scripts/arch_review/tests -v
```
Expected: all runner tests pass.

- [ ] **Step 5: Commit**

```bash
git add skills/code-quality/scripts/arch_review/runner.py skills/code-quality/scripts/arch_review/tests/test_runner.py
git commit -m "feat: arch_review runner — parallel orchestration + JSON output"
```

---

## Task 11: Wire `__main__.py` to the runner

**Files:**
- Modify: `skills/code-quality/scripts/arch_review/__main__.py`

- [ ] **Step 1: Replace the stub `main()` with real dispatch**

Replace the entire contents of `skills/code-quality/scripts/arch_review/__main__.py` with:
```python
"""CLI entry point for arch_review. Use the arch-review.sh wrapper to invoke."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from arch_review.runner import run_audit


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="arch_review",
        description="Architecture review orchestrator (Workflow I of code-quality skill).",
    )
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--language", required=True, choices=["python", "javascript"])
    parser.add_argument("--framework", default="none")
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--include-tests", action="store_true")
    parser.add_argument("--max-file-loc", type=int, default=500)
    parser.add_argument("--max-exports", type=int, default=30)
    parser.add_argument("--max-ca", type=int, default=20)
    parser.add_argument("--max-ce", type=int, default=20)
    parser.add_argument("--max-chain-depth", type=int, default=6)
    parser.add_argument("--skip-section", action="append", default=[])
    parser.add_argument("--timeout-per-section", type=int, default=60)
    parser.add_argument("--output-format", default="json", choices=["json"])
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    project_root = Path(args.project_root)
    if not project_root.exists():
        print(json.dumps({"error": f"project root does not exist: {project_root}"}), file=sys.stderr)
        return 2
    result = run_audit(
        project_root=project_root,
        language=args.language,
        framework=args.framework,
        options={
            "top": args.top,
            "include_tests": args.include_tests,
            "max_file_loc": args.max_file_loc,
            "max_exports": args.max_exports,
            "max_ca": args.max_ca,
            "max_ce": args.max_ce,
            "max_chain_depth": args.max_chain_depth,
            "skip_section": args.skip_section,
            "timeout_per_section": args.timeout_per_section,
        },
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Manual end-to-end smoke test**

Create a tiny synthetic Python project:
```bash
mkdir -p /tmp/arch-smoke/src/myapp/{domain,db}
touch /tmp/arch-smoke/src/myapp/__init__.py
touch /tmp/arch-smoke/src/myapp/domain/__init__.py
echo 'from myapp.db import session' > /tmp/arch-smoke/src/myapp/domain/order.py
touch /tmp/arch-smoke/src/myapp/db/__init__.py
touch /tmp/arch-smoke/src/myapp/db/session.py
```

Run the wrapper:
```bash
bash skills/code-quality/scripts/arch-review.sh \
  --project-root /tmp/arch-smoke \
  --language python \
  --framework none \
  --skip-section dead_code \
  --skip-section complex_functions \
  | python3 -m json.tool | head -40
```

Expected: a JSON document with `"summary"` and `"sections"`. The `layering` section should report a `domain → infrastructure` violation. Clean up:
```bash
rm -rf /tmp/arch-smoke
```

- [ ] **Step 3: Run the full unit suite to make sure nothing regressed**

```bash
PYTHONPATH=skills/code-quality/scripts python3 -m unittest discover -s skills/code-quality/scripts/arch_review/tests -v
```
Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add skills/code-quality/scripts/arch_review/__main__.py
git commit -m "feat: wire arch_review CLI to runner"
```

---

## Task 12: Integration fixtures (clean + violations × Python, JS)

**Files:**
- Create: `skills/code-quality/scripts/arch_review/fixtures/clean-py/` (with files)
- Create: `skills/code-quality/scripts/arch_review/fixtures/violations-py/` (with files)
- Create: `skills/code-quality/scripts/arch_review/fixtures/clean-js/` (with files)
- Create: `skills/code-quality/scripts/arch_review/fixtures/violations-js/` (with files)
- Create: `skills/code-quality/scripts/arch_review/tests/test_fixtures.py`

- [ ] **Step 1: Create the clean-py fixture**

```bash
mkdir -p skills/code-quality/scripts/arch_review/fixtures/clean-py/src/myapp/{api,services,domain,db}
cat > skills/code-quality/scripts/arch_review/fixtures/clean-py/src/myapp/__init__.py << 'EOF'
EOF
cat > skills/code-quality/scripts/arch_review/fixtures/clean-py/src/myapp/api/__init__.py << 'EOF'
EOF
cat > skills/code-quality/scripts/arch_review/fixtures/clean-py/src/myapp/api/users.py << 'EOF'
from myapp.services import user_service

def get_user(user_id: int):
    return user_service.fetch(user_id)
EOF
cat > skills/code-quality/scripts/arch_review/fixtures/clean-py/src/myapp/services/__init__.py << 'EOF'
EOF
cat > skills/code-quality/scripts/arch_review/fixtures/clean-py/src/myapp/services/user_service.py << 'EOF'
from myapp.domain import user as user_domain

def fetch(user_id):
    return user_domain.User(id=user_id)
EOF
cat > skills/code-quality/scripts/arch_review/fixtures/clean-py/src/myapp/domain/__init__.py << 'EOF'
EOF
cat > skills/code-quality/scripts/arch_review/fixtures/clean-py/src/myapp/domain/user.py << 'EOF'
class User:
    def __init__(self, id):
        self.id = id
EOF
cat > skills/code-quality/scripts/arch_review/fixtures/clean-py/src/myapp/db/__init__.py << 'EOF'
EOF
cat > skills/code-quality/scripts/arch_review/fixtures/clean-py/src/myapp/db/session.py << 'EOF'
from myapp.domain import user as user_domain

def load(user_id):
    return user_domain.User(id=user_id)
EOF
```

- [ ] **Step 2: Create the violations-py fixture**

```bash
mkdir -p skills/code-quality/scripts/arch_review/fixtures/violations-py/src/myapp/{api,domain,db}
cat > skills/code-quality/scripts/arch_review/fixtures/violations-py/src/myapp/__init__.py << 'EOF'
EOF
cat > skills/code-quality/scripts/arch_review/fixtures/violations-py/src/myapp/api/__init__.py << 'EOF'
EOF
cat > skills/code-quality/scripts/arch_review/fixtures/violations-py/src/myapp/api/handlers.py << 'EOF'
from myapp.domain import order
EOF
cat > skills/code-quality/scripts/arch_review/fixtures/violations-py/src/myapp/domain/__init__.py << 'EOF'
EOF
# Planted violation: domain → infrastructure
cat > skills/code-quality/scripts/arch_review/fixtures/violations-py/src/myapp/domain/order.py << 'EOF'
from myapp.db import session  # VIOLATION: domain imports infrastructure

class Order:
    def save(self):
        session.persist(self)
EOF
cat > skills/code-quality/scripts/arch_review/fixtures/violations-py/src/myapp/db/__init__.py << 'EOF'
EOF
cat > skills/code-quality/scripts/arch_review/fixtures/violations-py/src/myapp/db/session.py << 'EOF'
def persist(obj):
    pass
EOF
# Planted cycle: a ↔ b
cat > skills/code-quality/scripts/arch_review/fixtures/violations-py/src/myapp/a.py << 'EOF'
from myapp import b
EOF
cat > skills/code-quality/scripts/arch_review/fixtures/violations-py/src/myapp/b.py << 'EOF'
from myapp import a
EOF
# Oversized file (>500 LoC).
python3 -c "
import os
path = 'skills/code-quality/scripts/arch_review/fixtures/violations-py/src/myapp/oversized.py'
with open(path, 'w') as f:
    f.write('# planted oversized file\n')
    for i in range(600):
        f.write(f'X{i} = {i}\n')
"
```

- [ ] **Step 3: Create the clean-js and violations-js fixtures**

```bash
mkdir -p skills/code-quality/scripts/arch_review/fixtures/clean-js/src/api
mkdir -p skills/code-quality/scripts/arch_review/fixtures/clean-js/src/services
mkdir -p skills/code-quality/scripts/arch_review/fixtures/clean-js/src/domain
cat > skills/code-quality/scripts/arch_review/fixtures/clean-js/package.json << 'EOF'
{ "name": "clean-js-fixture", "version": "0.0.0", "main": "src/index.ts" }
EOF
cat > skills/code-quality/scripts/arch_review/fixtures/clean-js/tsconfig.json << 'EOF'
{ "compilerOptions": { "target": "es2020", "module": "commonjs", "strict": false, "esModuleInterop": true } }
EOF
cat > skills/code-quality/scripts/arch_review/fixtures/clean-js/src/index.ts << 'EOF'
import { getUser } from './api/users';
console.log(getUser(1));
EOF
cat > skills/code-quality/scripts/arch_review/fixtures/clean-js/src/api/users.ts << 'EOF'
import { fetchUser } from '../services/userService';
export function getUser(id: number) { return fetchUser(id); }
EOF
cat > skills/code-quality/scripts/arch_review/fixtures/clean-js/src/services/userService.ts << 'EOF'
import { User } from '../domain/user';
export function fetchUser(id: number) { return new User(id); }
EOF
cat > skills/code-quality/scripts/arch_review/fixtures/clean-js/src/domain/user.ts << 'EOF'
export class User { constructor(public id: number) {} }
EOF
```

Violations JS:
```bash
mkdir -p skills/code-quality/scripts/arch_review/fixtures/violations-js/src/{api,domain,db}
cat > skills/code-quality/scripts/arch_review/fixtures/violations-js/package.json << 'EOF'
{ "name": "violations-js-fixture", "version": "0.0.0", "main": "src/index.ts" }
EOF
cat > skills/code-quality/scripts/arch_review/fixtures/violations-js/tsconfig.json << 'EOF'
{ "compilerOptions": { "target": "es2020", "module": "commonjs", "strict": false, "esModuleInterop": true } }
EOF
cat > skills/code-quality/scripts/arch_review/fixtures/violations-js/src/index.ts << 'EOF'
import { handler } from './api/handler';
handler();
EOF
cat > skills/code-quality/scripts/arch_review/fixtures/violations-js/src/api/handler.ts << 'EOF'
import { Order } from '../domain/order';
export function handler() { return new Order().save(); }
EOF
cat > skills/code-quality/scripts/arch_review/fixtures/violations-js/src/domain/order.ts << 'EOF'
// VIOLATION: domain imports infrastructure
import { persist } from '../db/session';
export class Order { save() { return persist(this); } }
EOF
cat > skills/code-quality/scripts/arch_review/fixtures/violations-js/src/db/session.ts << 'EOF'
export function persist(o: unknown) { return o; }
EOF
# Planted cycle: a ↔ b
cat > skills/code-quality/scripts/arch_review/fixtures/violations-js/src/a.ts << 'EOF'
import { b } from './b';
export function a() { return b(); }
EOF
cat > skills/code-quality/scripts/arch_review/fixtures/violations-js/src/b.ts << 'EOF'
import { a } from './a';
export function b() { return a(); }
EOF
```

- [ ] **Step 4: Write the fixture integration test**

Create `skills/code-quality/scripts/arch_review/tests/test_fixtures.py`:
```python
"""Integration tests against committed fixtures.

These run the full arch_review pipeline (excluding subprocess sections that
require external tools) against checked-in synthetic projects.
"""
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
        kinds = [(v["importer_layer"], v["imported_layer"]) for v in result["sections"]["layering"]["findings"]]
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
```

JS fixtures are NOT covered by this test file because they require `npx madge`, which we don't depend on in unit tests. They're covered by smoke tests (Task 15).

- [ ] **Step 5: Run tests**

```bash
PYTHONPATH=skills/code-quality/scripts python3 -m unittest discover -s skills/code-quality/scripts/arch_review/tests -v
```
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add skills/code-quality/scripts/arch_review/fixtures/ skills/code-quality/scripts/arch_review/tests/test_fixtures.py
git commit -m "test: add fixtures and integration tests for arch_review"
```

---

## Task 13: Reference files — architecture.md, knip.md, vulture.md

**Files:**
- Create: `skills/code-quality/references/architecture.md`
- Create: `skills/code-quality/references/knip.md`
- Create: `skills/code-quality/references/vulture.md`

- [ ] **Step 1: Create `references/architecture.md`**

Create `skills/code-quality/references/architecture.md`:
```markdown
# Architecture Review Reference (Workflow I)

This file documents the layer-inference heuristics, framework overrides, severity thresholds, and JSON output schema used by `scripts/arch_review/`.

## Default layer mapping

Substring match against any path segment. First match wins per layer (case-sensitive).

| Layer | Folder names |
|---|---|
| presentation | `ui`, `views`, `routes`, `routers`, `controllers`, `api`, `pages`, `app`, `web`, `http`, `handlers` |
| application | `services`, `usecases`, `use_cases`, `commands`, `queries`, `application`, `core` |
| domain | `domain`, `entities`, `models`, `business` |
| infrastructure | `infrastructure`, `infra`, `adapters`, `repositories`, `repos`, `db`, `persistence`, `storage`, `clients` |

## Framework overrides

Applied IN ADDITION to the default mapping; the override wins.

| Framework | Override |
|---|---|
| nextjs | `app/` and `pages/` → presentation |
| django | `models.py`/`models/` → infrastructure; `views.py` → presentation; `admin.py` → presentation |
| nestjs | `handlers/` → application; `controllers/` → presentation; `dto/` → application |
| fastapi | `routers/`, `endpoints/` → presentation; `dependencies/` → application |
| flask | `views.py`, `routes.py`, `blueprints/` → presentation |
| express | `routes/`, `controllers/`, `middleware/` → presentation |
| none | only the default mapping applies |

## Dependency Rule (allowed transitions)

The Dependency Rule says: outer layers may import inner layers; inner layers may not import outer layers.

| Importer → Imported | Verdict |
|---|---|
| presentation → application | OK |
| presentation → domain | OK |
| application → domain | OK |
| infrastructure → application | OK |
| infrastructure → domain | OK |
| any → unclassified | OK (not flagged) |
| unclassified → any | OK (not flagged) |
| same → same | OK |
| anything else | VIOLATION |

## Severity thresholds

| Section | Watch (MIN) | Alarm (MAJ) |
|---|---|---|
| Hub modules (Ca) | > 20 | > 50 |
| God modules (Ce) | > 20 | > 50 |
| Unstable + central | I > 0.7 AND Ca > 10 | (alarm-only) |
| Deep chains | depth > 6 | depth > 10 |
| Oversized files (LoC) | > 500 | > 1000 |
| Excessive exports | > 30 | > 50 |
| Complex functions (CC) | > 10 | > 20 |

Dead-code findings are demoted one tier per the spec → all `[INF]`.

## JSON output schema

```json
{
  "summary": {
    "language": "python | javascript",
    "framework": "nextjs | django | fastapi | nestjs | express | flask | none",
    "project_root": "/abs/path",
    "files_scanned": 0,
    "sections_run": 0,
    "sections_skipped": [],
    "sections_errored": [],
    "warnings": [],
    "elapsed_seconds": 0.0
  },
  "sections": {
    "cycles": { "status": "ok | found | skipped | error", "severity": "CRT|null", "findings": [{ "modules": ["a", "b"], "severity": "CRT" }] },
    "layering": { "status": "...", "severity": "MAJ|null", "inferred_layers": { "presentation": ["src/api"] }, "findings": [{ "importer": "...", "importer_layer": "...", "imported": "...", "imported_layer": "...", "severity": "MAJ" }] },
    "hubs": { "status": "...", "severity": "...", "findings": [{ "file": "...", "ca": 0, "ce": 0, "i": 0.0, "severity": "..." }] },
    "gods": { "...same as hubs..." },
    "unstable_central": { "...same as hubs..." },
    "deep_chains": { "findings": [{ "chain": [], "depth": 0, "severity": "..." }] },
    "oversized_files": { "findings": [{ "file": "...", "loc": 0, "severity": "..." }] },
    "excessive_exports": { "findings": [{ "file": "...", "exports": 0, "severity": "..." }] },
    "dead_code": { "findings": [{ "kind": "unused_file | unused_export", "file": "...", "severity": "INF" }] },
    "complex_functions": { "findings": [{ "file": "...", "line": 0, "function": "...", "complexity": 0, "threshold": 0, "severity": "MAJ" }] }
  }
}
```

`status ∈ {"ok", "found", "skipped", "error"}`. `severity` is the highest severity of any finding in that section, or `null` if the section is clean / skipped.
```

- [ ] **Step 2: Create `references/knip.md`**

Create `skills/code-quality/references/knip.md`:
```markdown
# Knip Reference

Knip finds unused files, exports, dependencies, and types in JavaScript/TypeScript projects.

**Zero-install**: runs via `npx --yes knip` — no permanent installation.

## CLI Usage

```bash
npx --yes knip --reporter json
```

Run from the project root containing `package.json`.

## JSON output shape

```json
{
  "files": ["src/unused.ts"],
  "dependencies": {},
  "exports": {
    "src/a.ts": [
      { "name": "foo", "line": 10 },
      { "name": "bar", "line": 12 }
    ]
  }
}
```

The arch_review wrapper parses `files` (unused files) and `exports` (unused named exports).

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | No issues found |
| 1 | Issues found (expected — parse output) |
| 2+ | Error |

## Caveats

- Without a config, knip uses sensible defaults. False positives are possible for dynamic imports, runtime registration patterns, and re-export chains. For this reason, the arch_review skill maps ALL knip findings to `[INF]` severity.
- `npx --yes` is important — without it, npx prompts interactively in some terminals.
```

- [ ] **Step 3: Create `references/vulture.md`**

Create `skills/code-quality/references/vulture.md`:
```markdown
# Vulture Reference

Vulture finds unused code in Python — functions, classes, variables.

**Zero-install**: runs via `uvx vulture` — no permanent installation.

## CLI Usage

```bash
uvx vulture <path> --min-confidence 80
```

`--min-confidence 80` filters out the default 60% noise. The arch_review skill uses 80 to keep false positives down.

## Text output shape

```
src/myapp/orphan.py:42: unused function 'foo' (90% confidence)
src/myapp/old.py:5: unused variable 'X' (60% confidence)
```

Vulture has no JSON output. The arch_review wrapper parses the text with the regex:

```
^<file>:<line>:\s+<message>\s+\((<confidence>)% confidence\)\s*$
```

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | No issues found |
| 1 | Issues found (expected — parse output) |
| 2+ | Error |

## Caveats

- Vulture cannot see code referenced only via reflection (`getattr`, `__init_subclass__`, etc.). Treat findings as suggestions, not certainties.
- The arch_review skill maps ALL vulture findings to `[INF]` severity.
```

- [ ] **Step 4: Commit**

```bash
git add skills/code-quality/references/architecture.md skills/code-quality/references/knip.md skills/code-quality/references/vulture.md
git commit -m "docs: add architecture, knip, vulture references"
```

---

## Task 14: Add Workflow I to SKILL.md

**Files:**
- Modify: `skills/code-quality/SKILL.md`

- [ ] **Step 1: Add new triggers to the front-matter description**

Open `skills/code-quality/SKILL.md`. Find the YAML front matter block at the top. Locate the existing description (multi-line). Append the following to it (preserve YAML indentation; the description is a single quoted block):

```
  Also triggers on "architecture review", "review architecture", "arch audit",
  "find hub modules", "find god modules", "layering violations", "coupling
  metrics", "module coupling", "instability", "show me the structure",
  "onboard me to this codebase".
```

(Place it after the existing trigger paragraphs. Match the existing wrapping/indentation style — likely 2-space indent under `description:`.)

- [ ] **Step 2: Add the Workflow I section**

Find the end of the existing `## Workflow H: Type Checking` section in `SKILL.md`. Before `## Output Format` (or whichever section follows the workflows), insert:

```markdown
## Workflow I: Architecture Review

**Triggers**: "architecture review", "review architecture", "arch audit", "find god modules", "find hub modules", "layering violations", "coupling metrics", "instability", "module coupling", "show me the structure", "onboard me to this codebase"

Produces a structured architecture report with ten sections — cycles, layering violations, hub/god modules, instability hotspots, deep import chains, oversized files, excessive exports, dead code, and complex functions. Designed for **on-demand audits + onboarding new developers** to an unfamiliar codebase. Not a pre-commit gate; findings are top-N, not pass/fail.

### Steps

1. **Detect**: Run `bash <skill-dir>/scripts/detect-linter.sh [project-path]` to get `LANGUAGE`, `PROJECT_ROOT`, and `FRAMEWORK`.
2. **Run the orchestrator**:
   ```bash
   bash <skill-dir>/scripts/arch-review.sh \
     --project-root "$PROJECT_ROOT" \
     --language "$LANGUAGE" \
     --framework "$FRAMEWORK"
   ```
   The script reads `$LANGUAGE` and `$FRAMEWORK` exported from detection. It outputs a JSON document to stdout. Useful flags:
   - `--top N` (default 10) — findings per section
   - `--include-tests` — opt in to scanning test files
   - `--skip-section <name>` (repeatable) — drop a noisy section
   - `--max-file-loc`, `--max-exports`, `--max-ca`, `--max-ce`, `--max-chain-depth` — threshold overrides
3. **Load reference**: read `<skill-dir>/references/architecture.md` for the JSON schema, layer mapping, and severity thresholds.
4. **Render the report**: parse the JSON and produce a markdown report using the format below.

### Output format

Render the report using the same severity-table style as Workflows A/C/E/F. Each non-clean section gets its own block; clean sections appear only in a one-line footer.

#### Summary header

```
## Architecture Review Report

**Language**: <lang> | **Framework**: <framework> | **Files scanned**: <N> | **Top-N**: <N>

| Severity | Count |
|----------|-------|
| [CRT] CRITICAL | <count> |
| [MAJ] MAJOR | <count> |
| [MIN] MINOR | <count> |
| [INF] INFO | <count> |
| **Total** | **<sum>** |

**Sections**: <N> run, <N> skipped (<list>)
```

#### Per-section block

For each section with `status: "found"`, render a heading, a severity tag, a top-N table of findings, then prose explanations for `[MAJ]` and above. Examples:

```
### Layering Violations [MAJ] — <N> findings

**Inferred layers** (heuristic + framework: <framework>):
- presentation: <folder list>
- application:  <folder list>
- domain:       <folder list>
- infrastructure: <folder list>

| Violation | Importer | Imports |
|-----------|----------|---------|
| domain → infrastructure | src/domain/order.py:12 | src/db/session.py |

**src/domain/order.py:12**: `domain` should not depend on `infrastructure`. Extract the persistence concern into a repository interface defined in `domain/` and inject the concrete implementation from `infrastructure/`.
```

```
### Hub Modules [MAJ] — top N by fan-in (Ca)

| File | Ca | Ce | I | Severity |
|------|----|----|---|----------|

**<file>** (Ca=N): N modules depend on this. Changes here ripple widely.
```

#### Clean sections footer

```
**Clean sections**: cycles, deep_chains, excessive_exports
```

#### Skipped sections

```
**Skipped**: dead_code (vulture not available — `pip install vulture` or install `uv`)
```

#### Onboarding hints (always include if any modules have Ca > 0)

```
### Onboarding hints

Based on coupling metrics, the modules most central to understanding this codebase are:
1. **<file with highest Ca>** — used everywhere; read this first
2. **<second highest>**
3. **<third highest>**
```

#### Followups (always include)

```
### Followups

- Drill into a specific cycle: "show me cycle 1 in detail"
- See all complex functions (not just top-N): "run complexity analysis"
- Re-run including tests: "architecture review --include-tests"
- Skip dead-code: "architecture review --skip dead_code"
```

### Error handling

- If `detect-linter.sh` returns `LANGUAGE=unknown`: report "Architecture review supports Python and JS/TS projects. This project is not recognized."
- If `python3` is not on PATH: report "Workflow I requires `python3` (universally available on macOS/Linux). Install via `brew install python` or `apt install python3`."
- If a section has `status: "error"`: include it in the report with the underlying `reason` so the user understands why it failed. Other sections still render.
- If a section has `status: "skipped"`: include it in the "Skipped" footer line with the `reason`.

### Important

- Findings are **not** errors. Always present a useful report even if many sections returned `found`.
- Workflow F still exists as the focused cycles-only entry point. If the user just wants cycle detection, prefer F. Workflow I includes cycles as one of its ten sections.
- After presenting the report, offer the follow-up actions verbatim — they are parseable by the user.
```

- [ ] **Step 3: Add the new reference files to the Reference Files table**

Find the table at the bottom of `SKILL.md` titled "Reference Files" (the table that lists `severity-map.md`, `eslint.md`, etc.). Append three rows:

```
| `<skill-dir>/references/architecture.md` | Workflow I — layer mapping, framework rules, JSON schema |
| `<skill-dir>/references/knip.md` | Workflow I, JS/TS dead-code section |
| `<skill-dir>/references/vulture.md` | Workflow I, Python dead-code section |
```

- [ ] **Step 4: Manual sanity check**

Run:
```bash
grep -n "Workflow I:" skills/code-quality/SKILL.md
```
Expected: at least one match showing the new section heading.

Run:
```bash
grep -n "architecture review" skills/code-quality/SKILL.md
```
Expected: trigger phrases appear in the front matter description.

- [ ] **Step 5: Commit**

```bash
git add skills/code-quality/SKILL.md
git commit -m "feat: add Workflow I (architecture review) to SKILL.md"
```

---

## Task 15: SMOKE.md + dogfood smoke test

**Files:**
- Create: `skills/code-quality/scripts/arch_review/SMOKE.md`

- [ ] **Step 1: Create SMOKE.md**

Create `skills/code-quality/scripts/arch_review/SMOKE.md`:
```markdown
# Smoke tests for arch_review

Manual smoke tests to run before shipping. Unit tests cover correctness on synthetic data; these verify the workflow works on real repos.

## 1. Self-dogfood

The skill itself is a Python project. Run Workflow I on it.

```bash
bash skills/code-quality/scripts/arch-review.sh \
  --project-root . \
  --language python \
  --framework none \
  --skip-section dead_code \
  | python3 -m json.tool | head -80
```

Expected:
- Exits 0
- Reports `files_scanned > 0`
- `cycles` section is `ok` (the skill has no circular deps)
- `complex_functions` section runs (may report none)

## 2. Clean Python fixture

```bash
bash skills/code-quality/scripts/arch-review.sh \
  --project-root skills/code-quality/scripts/arch_review/fixtures/clean-py \
  --language python --framework none \
  --skip-section dead_code --skip-section complex_functions \
  | python3 -m json.tool
```

Expected: cycles `ok`, layering `ok`, hubs/gods/etc. all `ok`.

## 3. Violations Python fixture

```bash
bash skills/code-quality/scripts/arch-review.sh \
  --project-root skills/code-quality/scripts/arch_review/fixtures/violations-py \
  --language python --framework none \
  --skip-section dead_code --skip-section complex_functions \
  | python3 -m json.tool
```

Expected: cycles `found` (a↔b), layering `found` (domain → infrastructure), oversized_files `found` (oversized.py > 500 LoC).

## 4. Clean JS fixture (requires npm/npx)

```bash
bash skills/code-quality/scripts/arch-review.sh \
  --project-root skills/code-quality/scripts/arch_review/fixtures/clean-js \
  --language javascript --framework none \
  --skip-section dead_code --skip-section complex_functions \
  | python3 -m json.tool | head -60
```

Expected: cycles `ok`, layering `ok`.

## 5. Violations JS fixture

```bash
bash skills/code-quality/scripts/arch-review.sh \
  --project-root skills/code-quality/scripts/arch_review/fixtures/violations-js \
  --language javascript --framework none \
  --skip-section dead_code --skip-section complex_functions \
  | python3 -m json.tool | head -80
```

Expected: cycles `found` (a↔b), layering `found` (domain → infrastructure).

## 6. Performance check on a medium repo

Pick any local repo with ~300-1000 source files. Run with all sections including dead_code and complex_functions. Verify total elapsed time under 30 seconds (excluding cold-start npx download of knip).

## 7. Backward-compat check on Workflow F

After implementing Workflow I, run Workflow F against `fixtures/violations-py` and `fixtures/violations-js` exactly as before. Behavior must be unchanged. Workflow I MUST NOT regress Workflow F.
```

- [ ] **Step 2: Run the dogfood smoke test now**

```bash
bash skills/code-quality/scripts/arch-review.sh \
  --project-root . \
  --language python \
  --framework none \
  --skip-section dead_code \
  --skip-section complex_functions \
  | python3 -m json.tool | head -40
```
Expected output (representative): JSON with `summary.language == "python"`, `sections.cycles.status == "ok"`, etc.

If anything fails, fix the underlying module — don't relax the smoke test.

- [ ] **Step 3: Commit**

```bash
git add skills/code-quality/scripts/arch_review/SMOKE.md
git commit -m "docs: add SMOKE.md for arch_review manual verification"
```

---

## Final verification

After all tasks are complete, run the full test suite once more from a clean state:

```bash
PYTHONPATH=skills/code-quality/scripts python3 -m unittest discover -s skills/code-quality/scripts/arch_review/tests -v
```

Expected: all tests pass.

Then run the dogfood smoke test (Step 1 of Task 15) and confirm a clean JSON document is emitted.

Run a final `git log --oneline` and confirm there are roughly 15 commits, each with a clear conventional-commit subject.
