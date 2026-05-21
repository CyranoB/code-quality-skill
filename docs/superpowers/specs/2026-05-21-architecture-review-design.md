# Architecture Review — Workflow I Design

**Date**: 2026-05-21
**Skill**: `code-quality`
**New workflow**: `I — Architecture Review`
**Status**: design approved, ready for implementation planning

## Goal

Add a comprehensive **architecture review** workflow to the existing `code-quality` skill. Today the skill covers linting (A–C), pre-commit checks (D), complexity (E), circular dependencies (F), linter setup (G), and type checking (H). This workflow fills the gap between function-level (E) and import-graph (F) by surfacing module- and project-level architectural signals.

## Primary use cases

1. **On-demand audit** — "run an architecture review of this project" produces a structured report.
2. **Onboarding** — a developer joining a repo runs it to understand structure, central modules, and risk hotspots.

Explicitly **not** in scope: pre-commit gating, CI enforcement, layered architecture enforcement via user config.

## Constraints

| Constraint | Detail |
|---|---|
| Languages | JavaScript / TypeScript + Python (same as the rest of the skill). |
| Zero-config | No user config file. All layering / framework knowledge is heuristic. |
| Zero-install (third-party tools) | Third-party analysis tools must run via `npx <tool>` or `uvx <tool>` — no `pip install` / `npm install -g`. Otherwise we roll our own on top of dependency-graph data. |
| Local runtimes (required) | `python3` is required on the host (used by the orchestrator package — treated like `bash` or `sh`, not a third-party install). `npx` required when analyzing JS/TS projects; `uvx` required when analyzing Python projects. Missing `python3` is a hard failure for this workflow. |
| Output | Text-only structured report matching existing severity-table style. No diagrams in v1. |
| Reporting model | Top-N findings, not pass/fail. Aligned with audit + onboarding use cases. |

## High-level architecture

Workflow I adds one new workflow section to `SKILL.md`, plus a small Python package that does the analysis.

### Artifacts

```
skills/code-quality/
├── SKILL.md                            # MODIFIED: add Workflow I section
├── scripts/
│   ├── detect-linter.sh                # MODIFIED: emit FRAMEWORK key
│   ├── arch-review.sh                  # NEW: thin wrapper (sets PYTHONPATH, invokes package)
│   └── arch_review/                    # NEW: orchestrator package (stdlib only)
│       ├── __main__.py                 # CLI entry — invoked via the wrapper, not directly
│       ├── runner.py                   # Orchestration, parallel sub-checks, JSON output
│       ├── graph.py                    # Dep-graph extraction (madge for JS/TS, ast for Python)
│       ├── metrics.py                  # Ca/Ce/I, fan-in/out, deep chains (Tarjan-style)
│       ├── layers.py                   # Heuristic layer inference + violation detection
│       ├── smells.py                   # File LoC, public exports count
│       └── dead_code.py                # Subprocess wrappers for knip / vulture
└── references/
    ├── architecture.md                 # NEW: layer heuristics, framework rules, thresholds, schemas
    ├── knip.md                         # NEW: knip CLI reference (JS/TS dead-code)
    └── vulture.md                      # NEW: vulture CLI reference (Python dead-code)
```

### Wrapper script — `scripts/arch-review.sh`

Thin shim so callers don't need to know about `PYTHONPATH`. The package directory is not on `sys.path` by default, so `python3 -m arch_review …` would fail with `No module named arch_review`. The wrapper sets the path once and forwards all arguments:

```bash
#!/usr/bin/env bash
# Resolve the directory containing this script, then add it to PYTHONPATH so
# `python3 -m arch_review` can find the package directly beneath it.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec env PYTHONPATH="$SCRIPT_DIR${PYTHONPATH:+:$PYTHONPATH}" python3 -m arch_review "$@"
```

All Workflow I invocations (SKILL.md, tests, fixtures) call the wrapper:

```bash
bash <skill-dir>/scripts/arch-review.sh --project-root <path> --language <lang> --framework <framework>
```

### Why a Python package, not a single bash script

The metric math (Ca/Ce/I, graph traversal for deep chains, Tarjan SCC for cycles, LoC counting, layer inference with framework adjustments) is unwieldy in bash + jq and clean in stdlib Python. Splitting into a package keeps each module ~100–200 lines, independently testable, and avoids the irony of shipping a god module to detect god modules.

### Why `python3` is acceptable

The zero-install constraint applies to **third-party analysis tools** (the things we'd be asking users to add to their environment). `python3` is a host runtime — universally present on macOS (system Python) and Linux (apt/yum default), and the skill already assumes it indirectly via `uvx`. See the Constraints table for the explicit policy.

### Relationship to existing Workflow F

Workflow F (cycles-only) stays as the focused entry point for users who just want cycle detection. Workflow I builds its own dependency graph using the same upstream tool family (madge for JS/TS, custom Python AST walker for Python) and derives cycles from that graph as one of ten sections. Both workflows are independent — running one does not affect the other.

## Sub-checks

Ten sections, each ranked top-N (default 10), each mapping to the existing 5-tier severity scale.

| # | Section | Source | Watch / Alarm | Severity |
|---|---|---|---|---|
| 1 | Circular dependencies | Derived in-process from the dep graph (Tarjan SCC). Same upstream tools as Workflow F. | any cycle | `[CRT]` |
| 2 | Layering violations | Heuristic layer inference + framework adjustment, then Dependency Rule check (inner→outer is a violation) | any violation | `[MAJ]` |
| 3 | Hub modules (high Ca) | Graph metric — afferent coupling | Ca > 20 / > 50 | `[MIN]` / `[MAJ]` |
| 4 | God modules (high Ce) | Graph metric — efferent coupling | Ce > 20 / > 50 | `[MIN]` / `[MAJ]` |
| 5 | Unstable + central | Combined: I = Ce/(Ca+Ce) AND Ca > 10 | I > 0.7 AND Ca > 10 | `[MAJ]` |
| 6 | Deep import chains | Longest acyclic paths in the graph | depth > 6 / > 10 | `[MIN]` / `[MAJ]` |
| 7 | Oversized files | LoC per source file (blank/comment stripped) | LoC > 500 / > 1000 | `[MIN]` / `[MAJ]` |
| 8 | Excessive public exports | JS/TS: count of `export` declarations. Python: size of `__all__` or count of non-underscore top-level symbols. | exports > 30 / > 50 | `[MIN]` / `[MAJ]` |
| 9 | Dead code | `npx knip --reporter json` (JS/TS) or `uvx vulture <root> --min-confidence 80` (Python). All findings demoted one tier. | any | `[INF]` (all subcategories) |
| 10 | Complex functions | Reuses Workflow E commands: `ruff check --select C901 --output-format json` or `npx eslint --rule '{"complexity": ["warn", 10]}' --format json` | CC > 10 / > 20 | `[MAJ]` |

### Why these and not more

- **Skipped: Abstractness (A) and Distance from Main Sequence (D)** — they require reliable abstract-vs-concrete classification of modules, which is unreliable in dynamic languages (Python, JS). The research surfaced this consensus.
- **Skipped: LCOM (cohesion)** — too noisy for dynamic languages, same reason.
- **Skipped: type-only TS cycle distinction** — `madge --json` does not preserve per-edge type-only metadata, so a cycle can't be reliably classified as "all edges are `import type`" from madge output alone. All cycles map to `[CRT]` in v1. Revisit in v1.1, potentially via `dependency-cruiser` which exposes edge-level dependency types.
- **Section 8 is intentionally heuristic** — regex-based, will have false positives on barrel re-exports. Kept because it's a cheap signal and only `[MIN]`.

### Threshold rationale

All thresholds come from the practitioner ranges surfaced in the web research (Martin's metrics in modern usage). Configurable via CLI flags but not via config file — keeps the zero-config promise.

## Data flow

```
user request
  │
  ▼
SKILL.md Workflow I
  │
  ├─► detect-linter.sh                          # returns LANGUAGE, PROJECT_ROOT, FRAMEWORK
  │
  ├─► bash <skill-dir>/scripts/arch-review.sh --project-root … --language … --framework …
  │     │
  │     ├─► graph.py: build full dependency graph
  │     │     ├─ JS/TS: subprocess `npx madge --json src/` (one call, full graph)
  │     │     └─ Python: stdlib ast walker over .py files (no subprocess)
  │     │
  │     ├─► runner.py: dispatch sub-checks in parallel on the shared graph
  │     │     (ThreadPoolExecutor; sections that subprocess to knip/vulture/eslint/ruff
  │     │      are I/O-bound so GIL is fine)
  │     │
  │     ├─► metrics.py     (sections 3, 4, 5, 6)
  │     ├─► layers.py      (section 2)
  │     ├─► smells.py      (sections 7, 8)
  │     ├─► dead_code.py   (section 9 — subprocess to knip/vulture)
  │     ├─► (section 1: Tarjan SCC inside runner.py — no extra module needed)
  │     └─► (section 10: subprocess to ruff or eslint, parse JSON)
  │
  └─► JSON to stdout → SKILL.md renders markdown report
```

### `detect-linter.sh` enhancement

Add a single new emitted key — everything else stays the same.

```
FRAMEWORK=nextjs | django | fastapi | nestjs | express | flask | none
```

Detection rules:

| Framework | Trigger |
|---|---|
| `nextjs` | `next.config.{js,ts,mjs}` exists |
| `django` | `manage.py` AND a `settings.py` anywhere |
| `nestjs` | `nest-cli.json` exists |
| `fastapi` | `fastapi` listed in `pyproject.toml` or `requirements.txt` |
| `flask` | `flask` listed in `pyproject.toml` or `requirements.txt` |
| `express` | `package.json` lists `express` in `dependencies` |
| `none` | nothing matched |

If multiple match, return the first match in this priority order: `nextjs > nestjs > django > fastapi > flask > express`. (Frameworks higher in the list dominate; e.g., NestJS-on-Express still maps to NestJS.)

### CLI surface

```
bash <skill-dir>/scripts/arch-review.sh \
  --project-root <path> \
  --language python | javascript \
  --framework <name> \
  [--top N]                       # default 10
  [--include-tests]               # default off
  [--max-file-loc N]              # default 500
  [--max-exports N]               # default 30
  [--max-ca N]                    # default 20
  [--max-ce N]                    # default 20
  [--max-chain-depth N]           # default 6
  [--skip-section <name>]         # repeatable
  [--timeout-per-section SECONDS] # default 60
  [--output-format json]          # only json in v1
```

All flags optional. Defaults match the threshold table above.

### JSON output schema

Stable contract between `arch_review` and the SKILL.md renderer. Schema defined formally in `references/architecture.md`.

```json
{
  "summary": {
    "language": "python",
    "framework": "fastapi",
    "project_root": "/abs/path",
    "files_scanned": 312,
    "sections_run": 10,
    "sections_skipped": ["dead_code"],
    "sections_errored": [],
    "warnings": ["monorepo detected — running flat; metrics may be diluted"],
    "elapsed_seconds": 14.2
  },
  "sections": {
    "cycles": {
      "status": "found",
      "severity": "CRT",
      "findings": [
        { "kind": "runtime", "modules": ["a.py", "b.py", "a.py"], "severity": "CRT" }
      ]
    },
    "layering": {
      "status": "found",
      "severity": "MAJ",
      "inferred_layers": {
        "presentation": ["src/api", "src/routers"],
        "application":  ["src/services"],
        "domain":       ["src/domain", "src/models"],
        "infrastructure": ["src/db", "src/repositories"]
      },
      "findings": [
        {
          "importer": "src/domain/order.py",
          "importer_layer": "domain",
          "imported": "src/db/session.py",
          "imported_layer": "infrastructure",
          "line": 12,
          "severity": "MAJ"
        }
      ]
    },
    "hubs": { "status": "found", "severity": "MAJ", "findings": [ { "file": "...", "ca": 62, "ce": 3, "i": 0.05, "severity": "MAJ" } ] },
    "gods": { "status": "ok", "severity": null, "findings": [] },
    "unstable_central": { "...": "..." },
    "deep_chains": { "...": "..." },
    "oversized_files": { "...": "..." },
    "excessive_exports": { "...": "..." },
    "dead_code": { "status": "skipped", "reason": "knip not available" },
    "complex_functions": { "...": "..." }
  }
}
```

`status ∈ {ok, found, skipped, error}`. `severity` is the highest severity found in that section, or `null`.

## Graph extraction details

### JS/TS — single madge call

Madge's resolution behavior differs by language, so `graph.py` selects the entry point at runtime to match Workflow F's existing guidance (see `references/madge.md`):

| Project | Command |
|---|---|
| Plain JS (no `tsconfig.json`) | `npx madge --json src/` — directory entry works fine. |
| TypeScript (`tsconfig.json` present) | `npx madge --json --ts-config tsconfig.json --extensions ts,tsx src/index.ts` — must use a **file entry point**; passing `src/` alone often returns 0 files. |

Entry-point selection for TS (in priority order, first match wins):

1. `package.json` `main` field (resolved to absolute path)
2. `package.json` `module` field
3. `src/index.ts`, `src/index.tsx`
4. `src/server.ts`, `src/main.ts`, `src/app.ts`
5. If none found: skip graph-dependent sections (1–6) with reason "no detectable TypeScript entry point — pass one via `--entry <file>` or add a `main` to package.json".

The same logic is used by Workflow F today; `graph.py` lifts it into a reusable helper so both workflows share it.

Returns the full adjacency dict. Cycles are derived in-process using Tarjan's SCC. No separate `--circular` call is needed. Type-only cycles are not distinguished in v1 (see "Why these and not more" above).

### Python — stdlib AST walker

depcycle only emits cycle output, not the full graph, so it cannot feed sections 2–6. The arch_review package builds its own graph using the stdlib `ast` module:

1. Walk `PROJECT_ROOT` for `.py` files (respect excludes — see below).
2. For each file, parse with `ast.parse(...)` and collect `Import` and `ImportFrom` nodes.
3. Resolve module names to file paths using the project's `sys.path`-equivalent (project root + standard layouts: `src/`, the project package roots).
4. Build adjacency dict `{ file_path: [imported_file_paths, ...] }`.
5. Use the same Tarjan SCC for cycle detection.

This is ~80 lines of stdlib code. No new third-party dependency.

### Default exclusions

Both languages exclude by default:

```
node_modules, dist, build, .next, coverage, __pycache__, .venv, venv,
tests, test, __tests__, migrations,
*.test.*, *.spec.*, *_test.py, conftest.py,
*.d.ts, *.generated.*
```

Override with `--include-tests`.

### Monorepo handling (v1: flat with warning)

Detection: `package.json` with `workspaces`, `pnpm-workspace.yaml`, `lerna.json`, `turbo.json`, or a `pyproject.toml` with `[tool.uv.workspace]`.

v1 behavior: detect, log a warning in `summary.warnings`, run the analysis flat across the whole tree.

v1.1 (out of scope here): enumerate workspaces, run graph + metrics per package, aggregate.

## Layer inference

### Convergent folder-name mapping

Default mapping, regardless of language:

| Layer | Folder names (case-insensitive substring match) |
|---|---|
| `presentation` | `ui`, `views`, `routes`, `routers`, `controllers`, `api`, `pages`, `app`, `web`, `http`, `handlers` (NestJS) |
| `application` | `services`, `usecases`, `use_cases`, `commands`, `queries`, `application`, `core` |
| `domain` | `domain`, `entities`, `models` (when not a Django project), `business` |
| `infrastructure` | `infrastructure`, `infra`, `adapters`, `repositories`, `repos`, `db`, `persistence`, `storage`, `clients` |

### Framework overrides

| Framework | Override |
|---|---|
| `nextjs` | `app/` and `pages/` are **presentation**. `lib/`, `utils/` are unclassified. |
| `django` | `models.py` and `models/` are **infrastructure** (Django models are ORM-bound). `views.py` is presentation. `admin.py` is presentation. |
| `nestjs` | `handlers/` is application (not presentation). `controllers/` is presentation. `dto/` is application. |
| `fastapi` | `routers/` and `endpoints/` are presentation. `dependencies/` is application. |
| `flask` | `views.py`, `routes.py`, `blueprints/` are presentation. |
| `express` | `routes/`, `controllers/`, `middleware/` are presentation. |
| `none` | Only the convergent mapping applies. |

If a folder matches no layer, it is **unclassified** and excluded from violation checks (but still contributes to metrics).

### Dependency Rule

A file in layer L1 must not import a file in layer L2 if L1 is inner to L2:

```
presentation > application > domain
infrastructure > application > domain
```

(presentation and infrastructure are both outer; cross-outer imports are not flagged in v1 — only inner→outer.)

Violations:
- `domain → application` — violation
- `domain → infrastructure` — violation
- `domain → presentation` — violation
- `application → presentation` — violation
- `application → infrastructure` — violation
- `presentation → application` — OK
- `infrastructure → application` — OK
- `infrastructure → domain` — OK
- Anything → unclassified — not flagged
- Unclassified → anything — not flagged

## Output rendering (SKILL.md)

The SKILL.md workflow consumes the JSON and renders one markdown report.

### Report skeleton

```
## Architecture Review Report

**Language**: python | **Framework**: fastapi | **Files scanned**: 312 | **Top-N**: 10

| Severity | Count |
|----------|-------|
| [CRT] CRITICAL | 1 |
| [MAJ] MAJOR | 14 |
| [MIN] MINOR | 9 |
| [INF] INFO | 3 |
| **Total** | **27** |

**Sections**: 9 run, 1 skipped (dead_code — vulture not available)
```

Each non-clean section renders its own block. Clean sections appear only as a one-line footer: `**Clean sections**: cycles, deep_chains, excessive_exports`.

### Per-section block style

Findings table first, then prose explanations for `[MAJ]` and above (same convention as Workflows A/C/E/F). For example, a hub finding:

```
### Hub Modules [MAJ] — top 10 by fan-in (Ca)

| File | Ca | Ce | I | Severity |
|------|----|----|---|----------|
| src/db/session.py | 62 | 3 | 0.05 | [MAJ] |
| …

**src/db/session.py** (Ca=62): 62 modules depend on this. Changes here ripple
widely. Expected for a session factory, but consider whether some consumers
should go through a narrower interface (e.g., a repository) instead.
```

### Onboarding hints (new — distinctive to this workflow)

Footer block listing top-3 highest-Ca modules as "read these first" — turns the audit output into onboarding material:

```
### Onboarding hints

The modules most central to understanding this codebase:
1. **src/db/session.py** — used everywhere; read first
2. **src/domain/user.py** — central domain entity
3. **src/auth/jwt.py** — security-critical surface
```

### Followups (parseable)

```
### Followups

- Drill into a specific cycle: "show me cycle 1 in detail"
- See all complex functions: "run complexity analysis"
- Re-run including tests: "architecture review --include-tests"
- Skip dead-code: "architecture review --skip dead_code"
```

## Error handling

Per-section degradation — a failure in one sub-check never aborts the whole audit. Each sub-check writes a `status` + `reason` field; the renderer surfaces partial results.

| Failure | Behavior |
|---|---|
| `python3` not on PATH | Workflow exits with hint: `brew install python` / `apt install python3`. Hard failure. |
| `npx` not on PATH | Sections needing Node (1, 3–6, 9 JS/TS, 10 JS/TS) skipped with install hint. Others run. |
| `uvx` not on PATH | Sections needing uv (9 Python, 10 Python) skipped with install hint. Others run. |
| madge fails (parse error, no tsconfig) | Sections 1–6 errored; sections 7, 8, 10 still run. |
| Python ast parse error on a file | Skip that file, continue. Log filename in `summary.warnings`. |
| `knip` / `vulture` unavailable | Section 9 skipped. |
| ESLint without TS parser on TS project | Section 10 skipped with same hint Workflow E uses (`npm init @eslint/config@latest`). |
| No source files in `PROJECT_ROOT` | Workflow exits cleanly with: "No analyzable source files found." |
| Multiple frameworks detected | Use priority order, warn in `summary.warnings`. |
| Zero recognized layer folders | Section 2 skipped with reason "no recognizable layer folders — flat or feature-based structure". |
| Monorepo detected | Run flat, warn in `summary.warnings`. |
| Per-section subprocess timeout (60s default) | Section errored with `reason: "timeout"`. |
| Pathologically large repo (>10k files) | Run with bounded depth and top-N; warn in `summary.warnings`. |

**Exit code policy**: findings are not errors. Exit 0 on completion regardless of findings. Exit non-zero only on environment / setup failures (no `python3`, invalid args, project root missing).

## Testing

### Unit tests — `scripts/arch_review/tests/` (stdlib `unittest`)

- **`test_layers.py`** — feed synthetic folder lists, assert layer assignments for each framework override.
- **`test_metrics.py`** — feed hand-built adjacency dicts, assert exact Ca/Ce/I and deepest-chain values.
- **`test_graph_python.py`** — feed small synthetic packages, assert correct adjacency, correct cycle detection.
- **`test_smells.py`** — fixture files, assert LoC counts (blank/comment stripped) and export counts.
- **`test_severity.py`** — assert each metric maps to MIN/MAJ at watch/alarm boundaries.

### Integration fixtures — `scripts/arch_review/fixtures/`

- `clean-js/` — small TS project with no cycles, clean layering. All sections return `ok` or `found:0`.
- `violations-js/` — TS project with one planted cycle, one layering violation, one hub, one oversized file. Each section finds exactly its planted issue.
- `clean-py/` — Python equivalent of clean.
- `violations-py/` — Python equivalent with planted issues.

Run via `bash <skill-dir>/scripts/arch-review.sh --project-root fixtures/<name>` and snapshot-compare the JSON.

### Smoke tests — `scripts/arch_review/SMOKE.md` (manual)

- Medium FastAPI repo (~300 files) — runtime under 30 s, no crashes.
- Next.js app-router project — framework detection picks `nextjs`, `app/` maps to presentation.
- Django project — `manage.py` triggers Django path, `models.py` maps to infrastructure.
- The code-quality skill itself — dogfooding.

### Backward compatibility

Run Workflow F (existing cycles) before and after the change against `violations-js/` and `violations-py/`. Output must be unchanged. Workflow I must not regress F.

### Out of scope for v1 tests

- No upstream tool output-schema tests (we trust madge / knip / vulture / ruff JSON). Integration fixtures catch shape changes.
- No formal performance benchmarks beyond the 30 s smoke target.

## What's intentionally deferred to v1.1+

- **Per-package metrics for monorepos** — significant scope, not needed for first useful version.
- **Diagram output (mermaid / SVG)** — out of scope; v1 is text-only by user choice.
- **User-configurable layer rules via `arch.yaml`** — out of scope; v1 is heuristic-only by user choice.
- **Pre-commit / CI mode** — not the v1 use case.
- **Abstractness (A) and Distance (D) metrics** — not reliable in dynamic languages.
- **LCOM cohesion metric** — not reliable in dynamic languages.

## Open questions for implementation planning

None at design time. Surface during plan writing if any arise.

## References

- Web research report: `docs/superpowers/research/2026-05-21-architecture-review.md` (full source list, committed alongside this spec).
- Existing skill design: `skills/code-quality/SKILL.md`, `skills/code-quality/scripts/detect-linter.sh`, `skills/code-quality/references/madge.md`, `skills/code-quality/references/pydeps.md`.
