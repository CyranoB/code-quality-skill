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
    """Run `npx --yes knip --reporter json`. Returns {status, findings|reason}."""
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
    findings = _parse_knip_json(proc.stdout)
    return {"status": "found" if findings else "ok", "findings": findings}


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
    if proc.returncode > 1:
        return {"status": "error", "reason": proc.stderr.strip() or "vulture failed"}
    findings = _parse_vulture_text(proc.stdout)
    return {"status": "found" if findings else "ok", "findings": findings}
