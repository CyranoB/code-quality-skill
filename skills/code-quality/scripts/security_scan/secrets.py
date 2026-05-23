"""Secret scanner wrapper for Workflow J.

Primary tool: detect-secrets (zero-install via uvx). detect-secrets uses
multiple plugins (AWS keys, private keys, high-entropy strings, etc.) and
emits a baseline JSON with one entry per finding. Any finding is treated as
a BLOCKER — committed credentials must be rotated and removed.

Alternative: gitleaks (richer rule set, but requires brew install or a
prebuilt binary). Documented in references/secrets.md; this module sticks
to detect-secrets for the zero-install promise.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Sequence


def _parse(payload: str, project_root: Path) -> List[Dict[str, object]]:
    """Parse the detect-secrets baseline JSON into normalized findings.

    Strips the project_root prefix from displayed paths so output is portable
    across machines.
    """
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return []
    findings: List[Dict[str, object]] = []
    root_str = str(project_root.resolve())
    for raw_path, entries in (data.get("results") or {}).items():
        # Make path relative to project_root when possible for compact display.
        display_path = raw_path
        abs_path = str(Path(raw_path).resolve())
        if abs_path.startswith(root_str + "/"):
            display_path = abs_path[len(root_str) + 1:]
        for entry in entries or []:
            findings.append({
                "file": display_path,
                "line": int(entry.get("line_number", 0) or 0),
                "type": str(entry.get("type", "")),
                "hashed_secret": str(entry.get("hashed_secret", "")),
                "is_verified": bool(entry.get("is_verified", False)),
                "severity": "BLK",
            })
    return findings


def run_detect_secrets(
    project_root: Path,
    exclude_regex: str = "",
    timeout: int = 120,
    max_findings: int = 200,
) -> Dict[str, object]:
    """Run detect-secrets and return a section dict.

    `exclude_regex` is a single regex (detect-secrets's --exclude-files takes
    one regex, not a list of globs like semgrep).
    """
    if not shutil.which("uvx"):
        return {"status": "skipped", "reason": "uvx not available (detect-secrets runs via uvx)"}

    # detect-secrets only recurses correctly when cwd is the target dir AND
    # paths are passed as relative ("."). Passing an absolute path from outside
    # returns empty results — see GitHub issue history. Mitigate by running
    # from inside the project root.
    #
    # File input handling: subprocess refuses cwd=<file>, so when the caller
    # passes a single file (the documented "audit one file" flow), use the
    # parent directory as cwd and scan just the basename instead of ".".
    resolved = project_root.resolve()
    if resolved.is_file():
        scan_cwd = resolved.parent
        scan_target = resolved.name
        # Path-stripping in _parse compares against scan_cwd, not the file path.
        strip_root = scan_cwd
    else:
        scan_cwd = resolved
        scan_target = "."
        strip_root = resolved

    cmd: List[str] = ["uvx", "detect-secrets", "scan", "--all-files"]
    if exclude_regex:
        cmd.extend(["--exclude-files", exclude_regex])
    cmd.append(scan_target)

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(scan_cwd),
        )
    except subprocess.TimeoutExpired:
        return {"status": "error", "reason": f"detect-secrets timed out after {timeout}s"}

    # detect-secrets exits 0 even when secrets are found — it always emits a baseline.
    # A non-zero exit code means a real runtime failure.
    if proc.returncode != 0:
        return {
            "status": "error",
            "reason": (proc.stderr.strip() or "detect-secrets failed").splitlines()[-1][:500],
        }

    findings = _parse(proc.stdout, strip_root)
    truncated = len(findings) > max_findings
    if truncated:
        findings = findings[:max_findings]

    result: Dict[str, object] = {
        "status": "found" if findings else "ok",
        "severity": "BLK" if findings else None,
        "findings": findings,
    }
    if truncated:
        result["truncated"] = True
    return result
