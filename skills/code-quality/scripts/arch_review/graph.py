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

# Vendor / generated / cache folders. Always excluded — `--include-tests` does
# NOT loosen this. Scanning these distorts metrics with third-party code.
ALWAYS_EXCLUDED_DIRS = {
    "node_modules", "dist", "build", ".next", "coverage",
    "__pycache__", ".venv", "venv", ".tox", ".mypy_cache", ".pytest_cache",
    "migrations", "fixtures",
}
# Test directories — excluded by default; `--include-tests` opts them in.
TEST_DIRS = {"tests", "test", "__tests__"}
TEST_FILE_PATTERNS = (
    "*_test.py", "test_*.py",
    "*.test.ts", "*.test.tsx", "*.test.js", "*.test.jsx",
    "*.spec.ts", "*.spec.tsx", "*.spec.js", "*.spec.jsx",
    "conftest.py",
)

# Kept for backward compatibility with any callers that referenced the old name.
DEFAULT_EXCLUDES = ALWAYS_EXCLUDED_DIRS | TEST_DIRS


def _should_exclude(path: Path, exclude_tests: bool) -> bool:
    parts = set(path.parts)
    # ALWAYS_EXCLUDED_DIRS apply regardless of --include-tests.
    if parts & ALWAYS_EXCLUDED_DIRS:
        return True
    if not exclude_tests:
        return False
    if parts & TEST_DIRS:
        return True
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

    Strategy: for each .py file, derive its dotted name by walking upward to
    collect package directories (those containing __init__.py).
    """
    index: dict[str, Path] = {}
    for fp in py_files:
        current = fp.parent
        package_parts: list[str] = []
        while current != root and (current / "__init__.py").exists():
            package_parts.insert(0, current.name)
            current = current.parent
        module_name = ".".join(package_parts + [fp.stem]) if package_parts else fp.stem
        index[module_name] = fp
        if fp.name == "__init__.py" and package_parts:
            index[".".join(package_parts)] = fp
    return index


def _package_dotted(file: Path, root: Path) -> str:
    """Return the dotted package name for a file's containing package.

    Walks upward from the file's directory, collecting directory names that
    contain __init__.py (i.e., are Python packages). Stops at the first
    non-package directory or the project root.
    """
    current = file.parent
    parts: list[str] = []
    while current != root and (current / "__init__.py").exists():
        parts.insert(0, current.name)
        current = current.parent
    return ".".join(parts)


def _resolve_import(
    name: str,
    importer: Path,
    root: Path,
    index: dict[str, Path],
    level: int = 0,
) -> Path | None:
    if level > 0:
        # Relative import: figure out the dotted package of the importer,
        # then walk up `level - 1` parts.
        pkg = _package_dotted(importer, root)
        if not pkg:
            return None
        pkg_parts = pkg.split(".")
        if level - 1 > len(pkg_parts):
            return None
        target_parts = pkg_parts[: len(pkg_parts) - (level - 1)]
        target_pkg = ".".join(target_parts)
        full = f"{target_pkg}.{name}" if name and target_pkg else (name or target_pkg)
        return index.get(full)
    # Absolute import.
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
    Files with SyntaxError are silently skipped.
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
                # For each imported name, try resolving `module.name` as a
                # submodule first; fall back to `module` as a package.
                resolved_any = False
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    full = f"{module}.{alias.name}" if module else alias.name
                    target = _resolve_import(full, fp, root, index, level=node.level)
                    if target and str(target) != str(fp):
                        deps.append(str(target))
                        resolved_any = True
                if not resolved_any:
                    target = _resolve_import(module, fp, root, index, level=node.level)
                    if target and str(target) != str(fp):
                        deps.append(str(target))
        seen: set[str] = set()
        graph[str(fp)] = [d for d in deps if not (d in seen or seen.add(d))]
    return graph


TS_FALLBACK_ENTRIES = (
    "src/index.ts", "src/index.tsx",
    "src/server.ts", "src/main.ts", "src/app.ts",
)


def detect_ts_entry_point(root: Path) -> Path | None:
    """Pick a TypeScript entry point for madge.

    Priority: package.json main → package.json module → conventional src/ files.
    Returns absolute path or None if nothing found.
    """
    root = Path(root)
    pkg = root / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
        for key in ("main", "module"):
            value = data.get(key) if isinstance(data, dict) else None
            if isinstance(value, str):
                candidate = (root / value).resolve()
                if candidate.exists():
                    return candidate
    for rel in TS_FALLBACK_ENTRIES:
        candidate = root / rel
        if candidate.exists():
            return candidate
    return None


_JS_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")


def _enumerate_js_files(root: Path, exclude_tests: bool) -> list[Path]:
    """Return all source files we want to include in the JS/TS graph."""
    out: list[Path] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in _JS_EXTENSIONS:
            continue
        if _should_exclude(p.relative_to(root), exclude_tests):
            continue
        out.append(p)
    return out


def _resolve_madge_path(
    rel_or_partial: str,
    root: Path,
    file_index: dict[str, Path],
) -> str | None:
    """Map a madge-emitted path to an absolute path inside the project.

    Madge emits paths relative to either the entry-point's directory or the
    scanned input directory, which varies by version and invocation. To stay
    robust, we look up by the full relative form first, then by progressively
    shorter trailing path suffixes against the file index we built ourselves.
    """
    # Try as-is relative to root.
    direct = (root / rel_or_partial).resolve()
    if direct.exists():
        return str(direct)
    # Suffix-match against the enumerated files (longest match wins).
    rel = rel_or_partial.replace("\\", "/").lstrip("./")
    suffix_parts = rel.split("/")
    while suffix_parts:
        candidate = "/".join(suffix_parts)
        hit = file_index.get(candidate)
        if hit is not None:
            return str(hit)
        suffix_parts = suffix_parts[1:]
    return None


def _parse_madge_json(
    payload: str,
    root: Path,
    file_index: dict[str, Path] | None = None,
) -> dict[str, list[str]]:
    """Convert madge's relative-path JSON output to absolute-path adjacency dict.

    `file_index` maps the trailing path form of each source file to its absolute
    Path. When provided, paths are resolved through the index (handles madge
    emitting paths relative to entry-point dir, src/, or anywhere else). When
    omitted (back-compat for older callers/tests), paths are resolved against
    `root` directly.
    """
    raw = json.loads(payload)
    if file_index is None:
        graph: dict[str, list[str]] = {}
        for src, deps in raw.items():
            src_abs = str((root / src).resolve())
            graph[src_abs] = [str((root / d).resolve()) for d in deps]
        return graph

    graph = {}
    for src, deps in raw.items():
        src_abs = _resolve_madge_path(src, root, file_index)
        if src_abs is None:
            continue  # path that doesn't correspond to any source file we saw
        resolved_deps: list[str] = []
        for d in deps:
            d_abs = _resolve_madge_path(d, root, file_index)
            if d_abs is not None and d_abs != src_abs:
                resolved_deps.append(d_abs)
        graph[src_abs] = resolved_deps
    return graph


def build_js_graph(root: Path, exclude_tests: bool = True) -> dict[str, list[str]]:
    """Build JS/TS dependency graph via `npx madge --json`.

    Strategy:
      - Enumerate every source file we care about ourselves.
      - Pass them all to madge so files not reachable from a single entry point
        (e.g., a planted cycle `a.ts <-> b.ts`) are still in the graph.
      - Resolve madge's relative output paths through an index of those files.

    Returns: {file_path: [imported_file_paths, ...]}
    Raises RuntimeError if no source files are found or madge fails.
    """
    root = Path(root).resolve()
    files = _enumerate_js_files(root, exclude_tests)
    if not files:
        raise RuntimeError("no JS/TS source files found in project root")

    # Build an index keyed by every trailing path form so madge's varying
    # relative output (vs entry-dir, vs src/, vs root) can all be resolved.
    file_index: dict[str, Path] = {}
    for fp in files:
        rel = fp.relative_to(root).as_posix()
        parts = rel.split("/")
        for i in range(len(parts)):
            key = "/".join(parts[i:])
            file_index.setdefault(key, fp)

    has_tsconfig = (root / "tsconfig.json").exists()
    cmd: list[str] = ["npx", "--yes", "madge", "--json"]
    if has_tsconfig:
        cmd += [
            "--ts-config", str(root / "tsconfig.json"),
            "--extensions", "ts,tsx,js,jsx",
        ]
    if exclude_tests:
        cmd += [
            "--exclude",
            "(__tests__|\\.test\\.|\\.spec\\.|node_modules|dist|build|coverage|fixtures)",
        ]
    cmd += [str(fp) for fp in files]

    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(root))
    if proc.returncode not in (0, 1):
        raise RuntimeError(f"madge failed: {proc.stderr.strip() or proc.stdout.strip()}")
    return _parse_madge_json(proc.stdout, root, file_index=file_index)
