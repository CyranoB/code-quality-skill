# Architecture Review Reference

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
