"""Wrapper around Workflow E's complexity commands (ruff C901, eslint complexity rule)."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List

RUFF_C901_MSG_RE = re.compile(
    r"`?(?P<fn>[A-Za-z_][A-Za-z0-9_]*)`?\s+is too complex\s+\((?P<cc>\d+)\s*>\s*(?P<max>\d+)\)"
)
ESLINT_COMPLEXITY_MSG_RE = re.compile(
    r"['\"](?P<fn>[A-Za-z_][A-Za-z0-9_]*)['\"]?.*?complexity of (?P<cc>\d+).*?Maximum allowed is (?P<max>\d+)"
)


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
        # ESLint: 0 clean, 1 problems found (expected), 2+ config/runtime error.
        if proc.returncode > 1:
            return {"status": "error", "reason": proc.stderr.strip() or "eslint failed"}
        findings = _parse_eslint_complexity(proc.stdout)
        return {"status": "found" if findings else "ok", "findings": findings}
    return {"status": "skipped", "reason": f"unsupported language: {language}"}
