"""Semgrep wrapper for Security Scan.

Invokes Semgrep via uvx so the user needs no local install — only `uv`.
Default config is `p/security-audit` (cross-language security ruleset);
the caller can override via --semgrep-config.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Sequence

DEFAULT_CONFIG = "p/security-audit"

# Map Semgrep's severity to the skill's unified scale. See
# references/severity-map.md.
#   ERROR   -> BLOCKER (clear vulnerabilities)
#   WARNING -> CRITICAL (likely vulnerabilities)
#   INFO    -> MAJOR    (security smells worth attention)
_SEVERITY_MAP = {
    "ERROR": "BLK",
    "WARNING": "CRT",
    "INFO": "MAJ",
}


def _section_severity(findings: Sequence[Dict[str, object]]) -> str | None:
    """Most-severe-wins for the section badge."""
    order = ["BLK", "CRT", "MAJ", "MIN", "INF"]
    seen = {f["severity"] for f in findings}
    for level in order:
        if level in seen:
            return level
    return None


def _parse(payload: str) -> List[Dict[str, object]]:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return []
    findings: List[Dict[str, object]] = []
    for r in data.get("results", []) or []:
        raw_sev = (r.get("extra", {}) or {}).get("severity", "INFO").upper()
        severity = _SEVERITY_MAP.get(raw_sev, "MAJ")
        extra = r.get("extra", {}) or {}
        meta = extra.get("metadata", {}) or {}
        cwe = meta.get("cwe")
        if isinstance(cwe, list):
            cwe = ", ".join(str(c) for c in cwe)
        findings.append({
            "file": str(r.get("path", "")),
            "line": int((r.get("start", {}) or {}).get("line", 0)),
            "rule_id": str(r.get("check_id", "")),
            "message": str(extra.get("message", "")).strip(),
            "raw_severity": raw_sev,
            "severity": severity,
            "cwe": cwe or "",
        })
    return findings


def run_semgrep(
    project_root: Path,
    config: str = DEFAULT_CONFIG,
    excludes: Sequence[str] = (),
    timeout: int = 180,
    max_findings: int = 200,
) -> Dict[str, object]:
    """Run semgrep and return a section dict shaped like arch_review sections.

    Returns:
      * status: "ok" / "found" / "skipped" / "error"
      * severity: BLK / CRT / MAJ / None (most-severe finding)
      * findings: list of normalized finding dicts (capped at max_findings)
      * truncated: True if more findings existed than max_findings
    """
    if not shutil.which("uvx"):
        return {"status": "skipped", "reason": "uvx not available (semgrep runs via uvx)"}

    cmd: List[str] = [
        "uvx", "--from", "semgrep", "semgrep", "scan",
        "--config", config,
        "--json", "--quiet", "--metrics=off",
        "--error",  # exit 1 on findings so we can detect runtime errors separately
    ]
    for ex in excludes:
        cmd.extend(["--exclude", ex])
    cmd.append(str(project_root))

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"status": "error", "reason": f"semgrep timed out after {timeout}s"}

    # Semgrep exit codes: 0 clean, 1 findings (with --error), 2+ runtime error.
    if proc.returncode > 1:
        return {
            "status": "error",
            "reason": (proc.stderr.strip() or "semgrep failed").splitlines()[-1][:500],
        }

    findings = _parse(proc.stdout)
    truncated = len(findings) > max_findings
    if truncated:
        # Sort severity-first so the kept findings are the most actionable.
        order = {"BLK": 0, "CRT": 1, "MAJ": 2, "MIN": 3, "INF": 4}
        findings.sort(key=lambda f: (order.get(str(f.get("severity", "INF")), 9), str(f.get("file", "")), int(f.get("line", 0) or 0)))
        findings = findings[:max_findings]

    result: Dict[str, object] = {
        "status": "found" if findings else "ok",
        "severity": _section_severity(findings),
        "findings": findings,
    }
    if truncated:
        result["truncated"] = True
    return result
