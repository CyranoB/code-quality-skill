"""Orchestrator — runs sub-checks in parallel and assembles the JSON report."""
from __future__ import annotations

import concurrent.futures
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from arch_review import complexity, dead_code, graph, layers, metrics, smells

ALL_SECTIONS = [
    "cycles", "layering", "hubs", "gods", "unstable_central",
    "deep_chains", "oversized_files", "excessive_exports",
    "dead_code", "complex_functions",
]

SEV_CRT, SEV_MAJ, SEV_MIN, SEV_INF = "CRT", "MAJ", "MIN", "INF"


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
        if isinstance(data, dict) and "workspaces" in data:
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


def _highest_severity(sevs: List[Optional[str]]) -> Optional[str]:
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


def _section_layering(
    graph_data: Dict[str, List[str]], framework: str, root: str
) -> Dict[str, Any]:
    layer_map = layers.assign_layers(list(graph_data), framework, project_root=root)
    inferred: Dict[str, set] = {}
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


def _section_hubs(
    coupling: Dict[str, Dict[str, float]], top: int, max_ca: int
) -> Dict[str, Any]:
    sorted_nodes = sorted(coupling.items(), key=lambda kv: kv[1]["ca"], reverse=True)
    findings = []
    for path, m in sorted_nodes[:top]:
        if m["ca"] <= max_ca:
            continue
        sev = SEV_MAJ if m["ca"] > max_ca * 2.5 else SEV_MIN
        findings.append({
            "file": path, "ca": m["ca"], "ce": m["ce"], "i": m["i"], "severity": sev,
        })
    return {
        "status": "found" if findings else "ok",
        "severity": _highest_severity([f["severity"] for f in findings]),
        "findings": findings,
    }


def _section_gods(
    coupling: Dict[str, Dict[str, float]], top: int, max_ce: int
) -> Dict[str, Any]:
    sorted_nodes = sorted(coupling.items(), key=lambda kv: kv[1]["ce"], reverse=True)
    findings = []
    for path, m in sorted_nodes[:top]:
        if m["ce"] <= max_ce:
            continue
        sev = SEV_MAJ if m["ce"] > max_ce * 2.5 else SEV_MIN
        findings.append({
            "file": path, "ca": m["ca"], "ce": m["ce"], "i": m["i"], "severity": sev,
        })
    return {
        "status": "found" if findings else "ok",
        "severity": _highest_severity([f["severity"] for f in findings]),
        "findings": findings,
    }


def _section_unstable_central(coupling: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
    findings = []
    for path, m in coupling.items():
        if m["i"] > 0.7 and m["ca"] > 10:
            findings.append({
                "file": path, "ca": m["ca"], "ce": m["ce"], "i": m["i"], "severity": SEV_MAJ,
            })
    findings.sort(key=lambda f: (f["ca"], f["i"]), reverse=True)
    return {
        "status": "found" if findings else "ok",
        "severity": SEV_MAJ if findings else None,
        "findings": findings,
    }


def _section_deep_chains(
    graph_data: Dict[str, List[str]], min_depth: int
) -> Dict[str, Any]:
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


def _section_excessive_exports(
    files: List[Path], language: str, threshold: int
) -> Dict[str, Any]:
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
    if outcome["status"] in ("skipped", "error"):
        return {"status": outcome["status"], "reason": outcome.get("reason", "")}
    findings = outcome.get("findings", [])
    for f in findings:
        f["severity"] = SEV_INF
    return {
        "status": outcome["status"],
        "severity": SEV_INF if findings else None,
        "findings": findings,
    }


def _section_complex_functions(root: Path, language: str) -> Dict[str, Any]:
    # Workflow I uses both metrics: cyclomatic for path-count, cognitive for
    # human-reading effort. Cognitive drives severity when present.
    outcome = complexity.run_complexity_check(root, language, metric="both")
    if outcome["status"] in ("skipped", "error"):
        return {"status": outcome["status"], "reason": outcome.get("reason", "")}
    findings = outcome.get("findings", [])
    section_severity: Optional[str] = None
    for f in findings:
        raw = complexity.severity_for(f)
        if raw == "CRITICAL":
            f["severity"] = SEV_CRT
            section_severity = SEV_CRT
        elif raw == "MAJOR":
            f["severity"] = SEV_MAJ
            if section_severity != SEV_CRT:
                section_severity = SEV_MAJ
        else:
            f["severity"] = SEV_MAJ
            if section_severity is None:
                section_severity = SEV_MAJ
    result: Dict[str, Any] = {
        "status": outcome["status"],
        "severity": section_severity,
        "findings": findings,
    }
    warnings = outcome.get("warnings") or []
    if warnings:
        result["warnings"] = warnings
    return result


def _enumerate_source_files(root: Path, language: str, exclude_tests: bool) -> List[Path]:
    if language == "python":
        return list(graph._iter_py_files(root, exclude_tests))
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
    """Run the full architecture audit and return the JSON-serializable report."""
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
    sections: Dict[str, Any] = {}

    mono = _detect_monorepo(project_root)
    if mono is not None:
        warnings.append(f"monorepo detected ({mono}) — running flat; metrics may be diluted")

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

    sections_run = [
        s for s in ALL_SECTIONS
        if s in sections and sections[s].get("status") in ("ok", "found")
    ]
    sections_skipped = sorted(
        set(skip)
        | {s for s in ALL_SECTIONS if s in sections and sections[s].get("status") == "skipped"}
    )

    return {
        "summary": {
            "language": language,
            "framework": framework,
            "project_root": str(project_root),
            "files_scanned": len(files),
            "sections_run": len(sections_run),
            "sections_skipped": list(sections_skipped),
            "sections_errored": errored,
            "warnings": warnings,
            "elapsed_seconds": round(time.time() - started, 2),
        },
        "sections": sections,
    }
