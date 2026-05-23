"""Wrapper around the code-quality skill's complexity commands.

Cyclomatic:
  * Python:    ruff C901
  * JS/TS:     ESLint core `complexity` rule

Cognitive (Sonar-style; measures human reading effort, weights nesting heavily):
  * Python:    flake8-cognitive-complexity (CCR001) via uvx
  * JS/TS:     eslint-plugin-sonarjs (sonarjs/cognitive-complexity) via the
               bundled ESLint wrapper at scripts/eslint-defaults.sh

`run_complexity_check` accepts a `metric` kwarg:
  * "cyclomatic" (default; back-compat with the original complexity path)
  * "cognitive"  (cognitive only)
  * "both"       (runs both and merges findings by (file, line ±2))

In "both" mode, severity is driven by cognitive when present (16-25 MAJOR,
26+ CRITICAL); falls back to cyclomatic (>10 MAJOR) when only cyclomatic
is available. Architecture Review's complex_functions section uses metric="both".
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

RUFF_C901_MSG_RE = re.compile(
    r"`?(?P<fn>[A-Za-z_][A-Za-z0-9_]*)`?\s+is too complex\s+\((?P<cc>\d+)\s*>\s*(?P<max>\d+)\)"
)
ESLINT_COMPLEXITY_MSG_RE = re.compile(
    r"['\"](?P<fn>[A-Za-z_][A-Za-z0-9_]*)['\"]?.*?complexity of (?P<cc>\d+).*?Maximum allowed is (?P<max>\d+)"
)
FLAKE8_CCR001_RE = re.compile(
    r"^(?P<file>[^:]+):(?P<line>\d+):\d+:\s+CCR001\s+.*?\((?P<cc>\d+)\s*>\s*(?P<max>\d+)\)\s*$"
)
ESLINT_COGNITIVE_MSG_RE = re.compile(
    r"Cognitive Complexity from (?P<cc>\d+) to the (?P<max>\d+) allowed"
)

# Cognitive complexity severity tiers — keep in sync with references/severity-map.md.
COGNITIVE_MAJOR_MIN = 16
COGNITIVE_CRITICAL_MIN = 26
MERGE_LINE_TOLERANCE = 2


def _normalize_paths(findings: List[Dict[str, object]]) -> None:
    """Resolve `file` fields to absolute paths so cyclomatic + cognitive can be
    merged consistently — ruff (absolute) and flake8 (cwd-relative) emit paths
    differently. Subprocess cwd is the same for both, so Path(p).resolve()
    produces a consistent absolute path."""
    for f in findings:
        f["file"] = str(Path(str(f["file"])).resolve())


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


def _parse_flake8_cognitive(payload: str) -> List[Dict[str, object]]:
    findings: List[Dict[str, object]] = []
    for line in payload.splitlines():
        m = FLAKE8_CCR001_RE.match(line.strip())
        if not m:
            continue
        findings.append({
            "file": m.group("file"),
            "line": int(m.group("line")),
            "function": "",  # flake8 message doesn't include the function name
            "cognitive": int(m.group("cc")),
            "cognitive_threshold": int(m.group("max")),
        })
    return findings


def _parse_eslint_cognitive(payload: str) -> List[Dict[str, object]]:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return []
    findings: List[Dict[str, object]] = []
    for file_entry in data:
        file_path = file_entry.get("filePath", "")
        for msg in file_entry.get("messages", []) or []:
            if msg.get("ruleId") != "sonarjs/cognitive-complexity":
                continue
            m = ESLINT_COGNITIVE_MSG_RE.search(msg.get("message", ""))
            if not m:
                continue
            findings.append({
                "file": file_path,
                "line": msg.get("line", 0),
                "function": "",  # sonarjs message doesn't include the function name
                "cognitive": int(m.group("cc")),
                "cognitive_threshold": int(m.group("max")),
            })
    return findings


def _merge_dual(
    cyclomatic_findings: List[Dict[str, object]],
    cognitive_findings: List[Dict[str, object]],
    tolerance: int = MERGE_LINE_TOLERANCE,
) -> List[Dict[str, object]]:
    """Merge cyclomatic + cognitive findings by (file, line ±tolerance).

    Function name comes from cyclomatic (ruff/ESLint expose it in the message)
    when available; cognitive parsers leave it blank.
    """
    cognitive_by_file: Dict[str, List[Dict[str, object]]] = {}
    for f in cognitive_findings:
        cognitive_by_file.setdefault(str(f["file"]), []).append(f)

    consumed: set = set()
    merged: List[Dict[str, object]] = []

    for cyc in cyclomatic_findings:
        file_path = str(cyc["file"])
        cyc_line = int(cyc.get("line", 0) or 0)
        match_idx: Optional[int] = None
        for i, cog in enumerate(cognitive_by_file.get(file_path, [])):
            if (file_path, i) in consumed:
                continue
            cog_line = int(cog.get("line", 0) or 0)
            if abs(cog_line - cyc_line) <= tolerance:
                match_idx = i
                break
        entry = dict(cyc)
        if match_idx is not None:
            cog = cognitive_by_file[file_path][match_idx]
            entry["cognitive"] = cog["cognitive"]
            entry["cognitive_threshold"] = cog["cognitive_threshold"]
            consumed.add((file_path, match_idx))
        merged.append(entry)

    # Cognitive-only findings (no cyclomatic counterpart at this line).
    for file_path, cogs in cognitive_by_file.items():
        for i, cog in enumerate(cogs):
            if (file_path, i) in consumed:
                continue
            merged.append({
                "file": cog["file"],
                "line": cog["line"],
                "function": cog.get("function", ""),
                "cognitive": cog["cognitive"],
                "cognitive_threshold": cog["cognitive_threshold"],
            })

    return merged


def severity_for(finding: Dict[str, object]) -> str:
    """Return 'CRITICAL', 'MAJOR' or '' for a complexity finding.

    Cognitive (when present) drives severity: >=26 CRITICAL, >=16 MAJOR.
    Otherwise cyclomatic finding implies MAJOR (ruff/ESLint only emit above threshold).
    """
    cog = finding.get("cognitive")
    if isinstance(cog, int):
        if cog >= COGNITIVE_CRITICAL_MIN:
            return "CRITICAL"
        if cog >= COGNITIVE_MAJOR_MIN:
            return "MAJOR"
        return ""
    if finding.get("complexity") is not None:
        return "MAJOR"
    return ""


def _run_cyclomatic(project_root: Path, language: str, timeout: int) -> Dict[str, object]:
    if language == "python":
        if shutil.which("uvx"):
            cmd = ["uvx", "ruff", "check", "--select", "C901", "--output-format", "json", str(project_root)]
        elif shutil.which("ruff"):
            cmd = ["ruff", "check", "--select", "C901", "--output-format", "json", str(project_root)]
        else:
            return {"status": "skipped", "reason": "neither uvx nor ruff is available"}
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return {"status": "error", "reason": "ruff timed out"}
        if proc.returncode > 1:
            return {"status": "error", "reason": proc.stderr.strip() or "ruff failed"}
        findings = _parse_ruff_c901(proc.stdout)
        _normalize_paths(findings)
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
        if proc.returncode > 1:
            return {"status": "error", "reason": proc.stderr.strip() or "eslint failed"}
        findings = _parse_eslint_complexity(proc.stdout)
        _normalize_paths(findings)
        return {"status": "found" if findings else "ok", "findings": findings}
    return {"status": "skipped", "reason": f"unsupported language: {language}"}


def _skill_paths() -> Dict[str, Path]:
    """Resolve skill-relative paths so cognitive checks find the bundled ESLint."""
    scripts_dir = Path(__file__).resolve().parent.parent
    return {
        "wrapper": scripts_dir / "eslint-defaults.sh",
        "defaults_config": scripts_dir.parent / "defaults" / "eslint.config.js",
    }


def _run_cognitive(project_root: Path, language: str, timeout: int) -> Dict[str, object]:
    if language == "python":
        if not shutil.which("uvx"):
            return {"status": "skipped", "reason": "uvx not available (needed for flake8-cognitive-complexity)"}
        cmd = [
            "uvx", "--with", "flake8-cognitive-complexity",
            "flake8", "--select=CCR001", "--max-cognitive-complexity=15",
            str(project_root),
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return {"status": "error", "reason": "flake8 timed out"}
        # flake8: 0=clean, 1=findings, 2+=error.
        if proc.returncode > 1:
            return {"status": "error", "reason": proc.stderr.strip() or "flake8 failed"}
        findings = _parse_flake8_cognitive(proc.stdout)
        _normalize_paths(findings)
        return {"status": "found" if findings else "ok", "findings": findings}
    if language == "javascript":
        paths = _skill_paths()
        if not paths["wrapper"].exists():
            return {"status": "skipped", "reason": f"eslint-defaults.sh not found at {paths['wrapper']}"}
        cmd = [
            "bash", str(paths["wrapper"]),
            "--no-config-lookup",
            "--config", str(paths["defaults_config"]),
            "--rule", '{"sonarjs/cognitive-complexity":["warn",15]}',
            "--format", "json",
            str(project_root),
        ]
        # ESLint flat config refuses files outside cwd's base path — run from
        # project_root so the target is in-scope.
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(project_root))
        except subprocess.TimeoutExpired:
            return {"status": "error", "reason": "eslint timed out"}
        if proc.returncode > 1:
            return {"status": "error", "reason": proc.stderr.strip() or "eslint failed"}
        findings = _parse_eslint_cognitive(proc.stdout)
        _normalize_paths(findings)
        return {"status": "found" if findings else "ok", "findings": findings}
    return {"status": "skipped", "reason": f"unsupported language: {language}"}


def run_complexity_check(
    project_root: Path,
    language: str,
    timeout: int = 60,
    metric: str = "cyclomatic",
) -> Dict[str, object]:
    """Run complexity analysis. See module docstring for `metric` values."""
    if metric == "cyclomatic":
        return _run_cyclomatic(project_root, language, timeout)
    if metric == "cognitive":
        return _run_cognitive(project_root, language, timeout)
    if metric == "both":
        cyc = _run_cyclomatic(project_root, language, timeout)
        cog = _run_cognitive(project_root, language, timeout)
        cyc_ok = cyc["status"] in ("ok", "found")
        cog_ok = cog["status"] in ("ok", "found")
        # If neither backend produced usable output, surface skipped/error
        # explicitly so callers don't render "Code is
        # well-structured" when nothing actually ran.
        if not cyc_ok and not cog_ok:
            reasons: List[str] = []
            if cyc["status"] != "ok":
                reasons.append(f"cyclomatic {cyc['status']}: {cyc.get('reason', '')}")
            if cog["status"] != "ok":
                reasons.append(f"cognitive {cog['status']}: {cog.get('reason', '')}")
            status = "error" if "error" in (cyc["status"], cog["status"]) else "skipped"
            return {"status": status, "reason": "; ".join(reasons)}
        cyc_findings = cyc.get("findings", []) if cyc_ok else []
        cog_findings = cog.get("findings", []) if cog_ok else []
        merged = _merge_dual(cyc_findings, cog_findings)
        warnings: List[str] = []
        if not cyc_ok:
            warnings.append(f"cyclomatic {cyc['status']}: {cyc.get('reason', '')}")
        if not cog_ok:
            warnings.append(f"cognitive {cog['status']}: {cog.get('reason', '')}")
        return {
            "status": "found" if merged else "ok",
            "findings": merged,
            "warnings": warnings,
        }
    return {"status": "skipped", "reason": f"unknown metric: {metric}"}
