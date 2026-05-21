"""Heuristic layer inference + Dependency Rule violation detection."""
from __future__ import annotations

from typing import Dict, List, Optional

DEFAULT_LAYER_MAP: Dict[str, tuple[str, ...]] = {
    "presentation": ("ui", "views", "routes", "routers", "controllers", "api", "pages", "app", "web", "http", "handlers"),
    "application": ("services", "usecases", "use_cases", "commands", "queries", "application", "core"),
    "domain": ("domain", "entities", "models", "business"),
    "infrastructure": ("infrastructure", "infra", "adapters", "repositories", "repos", "db", "persistence", "storage", "clients"),
}

# Framework-specific overrides applied IN ADDITION to the default map.
# Override wins.
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

# Allowed transitions (importer_layer → imported_layer). Same-layer always allowed.
ALLOWED_TRANSITIONS = {
    ("presentation", "application"),
    ("presentation", "domain"),
    ("application", "domain"),
    ("infrastructure", "application"),
    ("infrastructure", "domain"),
}


def _path_segments(path: str) -> list[str]:
    return [seg for seg in path.replace("\\", "/").split("/") if seg]


def infer_layer(path: str, framework: str) -> Optional[str]:
    """Infer layer from a file path. Returns None if unclassified."""
    segments = _path_segments(path)
    if not segments:
        return None
    overrides = FRAMEWORK_OVERRIDES.get(framework, {})
    last_stem = segments[-1].rsplit(".", 1)[0]
    # Framework override on file stem (e.g., Django models.py).
    if last_stem in overrides:
        return overrides[last_stem]
    # Framework override on any segment.
    for seg in segments:
        if seg in overrides:
            return overrides[seg]
    # Default mapping on any segment.
    for layer, names in DEFAULT_LAYER_MAP.items():
        for seg in segments:
            if seg in names:
                return layer
        if last_stem in names:
            return layer
    return None


def assign_layers(
    nodes: List[str],
    framework: str,
    project_root: str = "",
) -> Dict[str, Optional[str]]:
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
    """Find imports that violate the Dependency Rule (inner → outer)."""
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
