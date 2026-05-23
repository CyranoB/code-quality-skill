"""Workflow J orchestrator — runs semgrep + detect-secrets in parallel.

Mirrors the arch_review.runner pattern: safe() wrapper around each sub-tool,
ThreadPoolExecutor with max_workers=2 (the two tools are heavy and IO-bound,
parallelism roughly halves wall time), JSON shape {summary, sections}.
"""
from __future__ import annotations

import concurrent.futures
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from security_scan import secrets as secrets_mod
from security_scan import semgrep as semgrep_mod

ALL_SECTIONS = ["semgrep", "secrets"]

# Default exclude set applied to both tools. Documented in
# references/semgrep.md and references/secrets.md. Override via --exclude.
DEFAULT_EXCLUDE_GLOBS: List[str] = [
    ".git", "node_modules", "dist", "build", "venv", ".venv",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "*.min.js", "*.map",
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock",
    "*.snap",
]

# detect-secrets wants a single regex; build it from the same intent.
DEFAULT_EXCLUDE_REGEX: str = (
    r"(^|/)("
    r"\.git|node_modules|dist|build|venv|\.venv|"
    r"__pycache__|\.pytest_cache|\.mypy_cache|\.ruff_cache"
    r")(/|$)"
    r"|\.min\.js$|\.map$"
    r"|(^|/)(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|poetry\.lock)$"
    r"|\.snap$"
)


def _safe(name: str, fn) -> Dict[str, Any]:
    try:
        return fn()
    except Exception as exc:
        return {"status": "error", "reason": f"{type(exc).__name__}: {exc}"}


def run_scan(
    project_root: Path | str,
    language: str = "auto",
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run the security scan and return the JSON-serializable report.

    options keys:
      * skip_section: list[str]                 sub-tools to skip
      * semgrep_config: str                     ruleset override (e.g. p/owasp-top-ten)
      * exclude: list[str]                      additional excludes; concat with defaults
      * timeout_per_section: int                seconds per sub-tool
      * max_findings: int                       cap per section before truncation
    """
    options = options or {}
    project_root = Path(project_root).resolve()
    skip = set(options.get("skip_section") or [])
    extra_excludes: Sequence[str] = options.get("exclude") or []
    semgrep_config = options.get("semgrep_config") or semgrep_mod.DEFAULT_CONFIG
    timeout = int(options.get("timeout_per_section", 180))
    max_findings = int(options.get("max_findings", 200))

    semgrep_excludes = list(DEFAULT_EXCLUDE_GLOBS) + [e for e in extra_excludes if e]
    secrets_regex_parts = [DEFAULT_EXCLUDE_REGEX]
    for e in extra_excludes:
        # Escape special chars conservatively; users can pass a glob, we treat
        # it as a substring match in the path. This is intentionally loose.
        secrets_regex_parts.append(_glob_to_loose_regex(e))
    secrets_regex = "|".join(p for p in secrets_regex_parts if p)

    started = time.time()
    sections: Dict[str, Any] = {}
    errored: List[str] = []

    pending: Dict[str, concurrent.futures.Future] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as exe:
        if "semgrep" not in skip:
            pending["semgrep"] = exe.submit(
                _safe, "semgrep",
                lambda: semgrep_mod.run_semgrep(
                    project_root,
                    config=semgrep_config,
                    excludes=semgrep_excludes,
                    timeout=timeout,
                    max_findings=max_findings,
                ),
            )
        if "secrets" not in skip:
            pending["secrets"] = exe.submit(
                _safe, "secrets",
                lambda: secrets_mod.run_detect_secrets(
                    project_root,
                    exclude_regex=secrets_regex,
                    timeout=timeout,
                    max_findings=max_findings,
                ),
            )

        for name, fut in pending.items():
            try:
                sections[name] = fut.result(timeout=timeout + 30)
            except concurrent.futures.TimeoutError:
                sections[name] = {"status": "error", "reason": f"timed out at orchestrator level"}
            if sections[name].get("status") == "error":
                errored.append(name)

    sections_run = [s for s in ALL_SECTIONS if sections.get(s, {}).get("status") in ("ok", "found")]
    sections_skipped = sorted(
        set(skip) | {s for s in ALL_SECTIONS if sections.get(s, {}).get("status") == "skipped"}
    )

    return {
        "summary": {
            "language": language,
            "project_root": str(project_root),
            "sections_run": len(sections_run),
            "sections_skipped": sections_skipped,
            "sections_errored": errored,
            "elapsed_seconds": round(time.time() - started, 2),
        },
        "sections": sections,
    }


def _glob_to_loose_regex(glob: str) -> str:
    """Convert a user-supplied glob into a loose regex fragment for detect-secrets.

    Not a full fnmatch translation — just enough so `node_modules` matches a
    path segment and `*.min.js` matches a suffix. Conservative on purpose.
    """
    if not glob:
        return ""
    if glob.startswith("*"):
        # Treat as suffix match.
        suffix = glob.lstrip("*").replace(".", r"\.")
        return rf"{suffix}$"
    # Treat as path-segment match.
    escaped = glob.replace(".", r"\.").replace("*", ".*")
    return rf"(^|/){escaped}(/|$)"
