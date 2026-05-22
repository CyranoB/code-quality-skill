# Architecture-Review Workflow — Research Report

Scope: tools, metrics, and heuristics for a `code-quality` skill workflow that adds basic architecture review on top of the existing linter / type-checker / circular-dep workflows. Strict zero-install constraint: only `npx` (JS/TS) or `uvx` (Python) — no `pip install` or `npm install -g`. Output is text-only.

---

## 1. Tool Survey

### 1.1 JavaScript / TypeScript

| Tool | What it does | Zero-install command | Strengths | Weaknesses | Latest release (as of mid-2026) |
|------|--------------|----------------------|-----------|------------|---------------------------------|
| **dependency-cruiser** | Validates dependencies against user rules; computes stability metrics; outputs JSON/dot/html [1][2] | `npx dependency-cruiser --output-type json src` or `npx depcruise --metrics src` | Native `--metrics` flag emits Ca/Ce/instability per module out-of-the-box [2]; powerful rule DSL; handles TS/JS/Coffee/Vue/SVG; JSON output for scripting | Rule DSL has a learning curve; needs `--ts-config` for path aliases; slow on huge monorepos | v17.4.0, May 2026 [1] |
| **madge** | Generates dependency graphs and detects circular dependencies; JSON output [3] | `npx madge --json --extensions ts,tsx,js,jsx src/` | Tiny, fast, well-known; JSON is a clean adjacency-map (`{file: [deps]}`) suitable for downstream metric computation; works with TS via `--ts-config` | No built-in stability/cohesion metrics; no rule DSL; circular detection only | v8.0.0, Aug 2024 [3] |
| **knip** | Finds unused files, exports, dependencies, members; ~150 plugins for framework entry points [4] | `npx knip --reporter json` | Best-in-class dead-code & orphan-export detection; understands Next.js/Vite/Astro/Nx entry points to reduce false positives; "successor" to ts-prune | Needs a small `knip.json` for non-default configs (still zero-install); some plugins assume specific folder layouts | v6.14.1, May 2026 [4] |
| **ts-prune** | Unused TypeScript exports | `npx ts-prune` | Zero-config historical default | **Archived since 2023, maintenance mode**; author recommends knip [5][6] | v0.10.3, Dec 2021; repo archived 2025 [6] |
| **arkit** | Generates architecture diagrams (SVG/PNG/PlantUML) from JS/TS/Flow/Vue [7] | `npx arkit -o architecture.svg src` | Diagram generation is fast | **Text-only constraint rules it out**; last npm release v2.1.0 (Mar 2026) but largely diagram-focused [7] | v2.1.0, Mar 2026 [7] |
| **eslint-plugin-boundaries** | ESLint rules that enforce a typed element graph (e.g. `domain` cannot import `infrastructure`) [8] | Requires ESLint + plugin install (NOT zero-install in practice — `npx eslint --rulesdir` workarounds are brittle) | Inline editor feedback; expressive `elements`/`rules` schema; flat-config support in v5/v6 | Needs persistent install + project ESLint config; significant config burden | v6.0.2, Mar 2026 [9] |
| **eslint-plugin-import** | `no-cycle`, `no-self-import`, `no-restricted-paths` | Same install constraints as ESLint plugins | `no-restricted-paths` can roughly enforce layers | Static imports only — dynamic `import()` is ignored [10] | n/a — bundled with most ESLint configs |

**JS/TS zero-install winners**: `dependency-cruiser` (full metrics + rules + JSON) and `knip` (dead-code/orphan exports). `madge --json` remains useful as a lightweight graph source. `eslint-plugin-boundaries` is the standard for boundary enforcement but is *not* genuinely zero-install — it requires plugin installation in a configured ESLint project, so for a one-shot audit it's out of scope.

### 1.2 Python

| Tool | What it does | Zero-install command | Strengths | Weaknesses | Latest release |
|------|--------------|----------------------|-----------|------------|----------------|
| **import-linter** | Declarative contracts (Layers, Forbidden, Independence, ForbiddenModules) over the package import graph; built on `grimp` [11][12] | `uvx import-linter lint` (reads `.importlinter` / `pyproject.toml`) | Most mature Python equivalent of ArchUnit; layered & forbidden-import contracts are well-modeled; clear violation reporting; interactive UI in 2.x [11] | Requires a config file describing contracts (still zero-install — config lives in repo); dynamic imports / metaclasses can hide edges | v2.11 (PyPI), 2.x line since Jan 2024 [11][12] |
| **tach** | Visualises + enforces module boundaries; written in Rust; declares each module's allowed deps + public interface in `tach.toml` [13][14] | `uvx tach check` / `uvx tach show` | Fast (Rust); `tach init` can auto-detect modules; supports interface enforcement (deep-import prevention) | Requires `tach.toml`; younger project (still 0.x); enforcement is project-specific | v0.35.0, May 2026 [13] |
| **pydeps** | Generates Python import graphs; emits text/dot/JSON; detects cycles [15] | `uvx pydeps --show-deps --no-output package_name` | Already used by the existing skill (similar role to madge); easy JSON output | Diagram-focused historically; cycle detection limited; some false positives with `if TYPE_CHECKING` blocks | v3.0.6, Apr 2026 [15] |
| **pylint cyclic-import (R0401)** | Detects cyclic imports as part of pylint runs [16] | `uvx pylint --disable=all --enable=cyclic-import package/` | Already in the Python ecosystem; per-message enablement | Slow on large codebases; only catches cycles (no other arch checks); known false positives with non-top-level imports [16] | bundled with pylint |
| **vulture** | Finds dead Python code (unused functions, classes, variables) [17] | `uvx vulture package/` | Zero-config; useful for orphan detection complementing depcycle | Confidence-based; needs whitelist for dynamic usage (e.g. `getattr`, Django ORM); not a structural tool | v2.16, Mar 2026 [17] |
| **pyflakes** | Detects unused imports and a few other issues | already covered by ruff (`F401`) in existing skill | — | Narrower than vulture | bundled |
| **grimp** | Low-level import-graph library (the engine behind import-linter) | `uvx --from grimp python -c "..."` | Programmatic access to the graph for custom metrics | Python API only; not a CLI tool | active alongside import-linter [12] |

**Python zero-install winners**: `import-linter` (boundary enforcement) + the **existing** `depcycle`/`pydeps` (graph extraction) + `vulture` (dead code). `tach` is promising and zero-install via `uvx tach check`, but **requires a `tach.toml` describing modules**; in an on-demand audit scenario with no pre-existing config, it would have to be auto-generated via `tach init` — workable but adds friction.

### 1.3 Summary recommendation

Under strict zero-install:

**JS/TS pipeline:**
1. `npx dependency-cruiser --output-type json src` — primary graph + stability metrics (`--metrics`) [2]
2. `npx knip --reporter json` — orphan exports, dead files, unused deps [4]
3. (already in skill) `npx madge --json --circular` for circular dep cross-check

**Python pipeline:**
1. `uvx import-linter lint` — boundary enforcement (only when a contract file exists or we auto-generate one)
2. (already in skill) `uvx depcycle` / `uvx pydeps --show-deps --no-output` for graph extraction
3. `uvx vulture src/` — dead-code and orphan detection

**Checks we must build ourselves** (because no zero-install tool covers them in one shot):

- **Layer inference + violation detection** from folder names (no contract file): nothing reliable, must roll our own using madge/depcycle JSON.
- **Fan-in/fan-out distribution**, hub-module/god-module detection, deep-import-chain depth: dependency-cruiser provides Ca/Ce per module but **not** distribution stats or god-module thresholds — must aggregate ourselves from JSON.
- **File-size / public-export count** smells: trivial AST counting on top of madge/depcycle node lists.
- **Layer violation reporting in text-only with file:line evidence**: dependency-cruiser does this for *configured* rules, but auto-generating those rules from heuristic folder names is our work.

This means the workflow's design pattern is: **let one zero-install tool extract the graph, then post-process its JSON in our own scripts** for the architecture-specific signals. dependency-cruiser (JS/TS) and grimp/import-linter or depcycle (Python) are the lift; the metrics layer is ours.

---

## 2. Best-Practice Architectural Metrics

Originating from Robert C. Martin's *Agile Software Development* and *Clean Architecture* [18][19][20]:

### Per-module / per-package

- **Afferent Coupling (Ca) — fan-in**: number of *outside* modules that depend on this module. High Ca = "stable" (changes here ripple widely). [18][19]
- **Efferent Coupling (Ce) — fan-out**: number of *outside* modules this module depends on. High Ce = sensitive to upstream changes. [18][19]
- **Instability (I) = Ce / (Ca + Ce)**, range `[0, 1]`. `I=0` is maximally stable (only depended on, depends on nothing); `I=1` is maximally unstable (depends on many, nobody depends on it). [18][19][20]
- **Abstractness (A)** = abstract classes / total classes (for OO languages with explicit abstracts). For JS/TS/Python lacking strict abstract markers, approximated as `interfaces+abstract bases / total module exports` — often skipped for dynamic languages. [21]
- **Distance from main sequence (D) = |A + I − 1|**, range `[0, 1]`. `D=0` lies on the "main sequence" (good balance); high `D` → *zone of pain* (stable + concrete) or *zone of uselessness* (unstable + abstract). [19][21]

### Typical thresholds (industry rule-of-thumb)

Thresholds are not standardized; common heuristic ranges from NDepend, dependency-cruiser docs, and practitioner posts [18][20][21]:

| Metric | Watch threshold | Alarm threshold |
|--------|-----------------|-----------------|
| Ca (fan-in) | > 20 | > 50 (likely god module / shared kernel pressure) |
| Ce (fan-out) | > 20 | > 50 (likely "junction" module doing too much) |
| Instability I | n/a (extreme values are fine *if* they match role) | high-Ca **and** high-I together = warning (used by many AND depends on many) |
| Distance D | > 0.5 | > 0.7 |
| Cyclomatic complexity per fn | > 10 | > 15 (already covered by C901/ESLint complexity in existing skill) |
| File LoC | > 500 | > 1000 (god-file proxy) |
| Public exports per module | > 30 | > 50 (broad surface area; couple with high Ca) |

### Cohesion (LCOM)

`LCOM` (Lack of Cohesion of Methods) measures how poorly the methods of a class share fields. Multiple variants exist (LCOM1–LCOM4, LCOM-HS). Higher = worse cohesion; threshold guidance is fuzzy — Stack Overflow practitioners caution that "LCOM-HS thresholds > 1 are odd" and there's no canonical cutoff [22][23]. **For JS/TS and Python (dynamic, often-modular, often-functional codebases), LCOM is generally not worth computing** in a basic architecture review — it's more meaningful in heavily OO Java/.NET codebases. We recommend **omitting LCOM** and instead surfacing per-file LoC, per-module export count, and Ca/Ce as the cohesion proxy.

---

## 3. Heuristic Layering from Folder Names

There is **no single canonical mapping**, but there is broad convergence across Clean Architecture, Hexagonal/Ports-and-Adapters, DDD, and framework conventions [24][25][26][27]:

| Layer (outer → inner) | Common folder names | Frameworks reinforcing this |
|-----------------------|---------------------|-----------------------------|
| **Presentation / Interface / Delivery** | `presentation/`, `ui/`, `views/`, `pages/`, `app/` (Next.js App Router), `routes/`, `controllers/`, `handlers/`, `api/`, `endpoints/`, `routers/` | Next.js `app/`, `pages/` [28]; NestJS `controllers/` [29]; FastAPI `router.py` [27]; Django `views.py` / `urls.py` [30]; Express `routes/` |
| **Application / Use-case** | `application/`, `services/`, `usecases/`, `use_cases/`, `commands/`, `queries/`, `handlers/` (in CQRS), `service.py` | Clean Architecture canonical [24]; NestJS `services/` [29]; FastAPI `service.py` per Netflix Dispatch layout [27] |
| **Domain / Model** | `domain/`, `entities/`, `models/`, `core/`, `business/`, `aggregates/`, `value_objects/` | Clean Architecture / DDD canonical [24]; Django `models.py` (NOTE: framework collision — see risks); SQLAlchemy `models.py` |
| **Infrastructure / Adapter / Data** | `infrastructure/`, `infra/`, `adapters/`, `repositories/`, `repository/`, `persistence/`, `db/`, `database/`, `dao/`, `gateways/`, `clients/`, `external/` | Hexagonal (Ports & Adapters) canonical [25][26]; Clean Architecture outer ring [24] |
| **Shared / Cross-cutting** | `shared/`, `common/`, `utils/`, `lib/`, `helpers/`, `kernel/` | Conventionally importable by all layers |

**The Dependency Rule**: outer layers may import inner layers; inner layers must not import outer ones [24][26]. Concretely:

```
presentation → application → domain
infrastructure → domain (NOT the other way)
domain → (nothing outside)
```

Common violation: a file under `domain/` importing from `infrastructure/db/` (a domain entity should never directly touch the ORM session). Detecting this is a string-match over the absolute import paths in the dependency graph.

### Framework-specific conventions to handle

- **Next.js (App Router)**: `app/` is the *presentation* layer, *not* "application" — naming collision. `lib/` is shared. `actions/` / Server Actions blur the line between presentation and application [28].
- **Django**: Each app folder contains `models.py` (domain), `views.py` (presentation), `serializers.py` (application/marshalling), `forms.py` (presentation), `admin.py` (presentation). Layering is *per-app* not project-wide [30].
- **FastAPI**: The mainstream "Netflix Dispatch" convention is package-per-domain with `router.py` (presentation), `service.py` (application), `models.py` (domain ORM), `schemas.py` (DTOs), `dependencies.py`, `exceptions.py` [27]. Layering is again *per-domain-package*.
- **NestJS**: Per-feature modules each with `*.controller.ts` (presentation), `*.service.ts` (application), `*.entity.ts` / `*.repository.ts` (domain / infra). Modules wire everything via DI [29].
- **Flask / Express**: No prescribed layout; convention is whatever the author chose.

**Recommended heuristic** for the workflow:

1. Detect framework first (presence of `next.config.*`, `nest-cli.json`, `manage.py`, `main.py` + FastAPI import, etc.).
2. If framework is recognized, apply *its* mapping (e.g. for Next.js, treat `app/` as presentation).
3. Otherwise apply a default keyword mapping over folder names using the table above.
4. Report layering inference as *advisory*: "I inferred these layers from folder names — confirm before treating violations as bugs."

---

## 4. Risks & Known Pitfalls

1. **Dynamic imports / runtime resolution.** ESLint's `no-restricted-imports` (and most static checkers) only inspect static `import` statements — dynamic `import()` is ignored [10]. Python equivalents: `importlib.import_module(name)`, factory patterns, Django's `INSTALLED_APPS` string lookups, Celery autodiscovery. False negatives are inherent. Pydeps notes false positives in the *other* direction with `if TYPE_CHECKING:` blocks [15].

2. **Monorepos.** A single `src/` heuristic breaks when the repo contains multiple packages (`packages/foo`, `apps/bar`). dependency-cruiser handles this with workspace-aware config; without one, fan-in/fan-out gets diluted across packages. Recommendation: detect `pnpm-workspace.yaml`, `package.json#workspaces`, Nx/Turborepo configs, and `pyproject.toml` `[tool.uv.workspace]` and treat each workspace package as an independent graph.

3. **Framework folder conventions clash with Clean Architecture vocabulary.** Django's `models.py` is OR-mapping (closer to infra than domain). Next.js's `app/` is *not* the "application" layer. Naive keyword mapping will mis-classify. Hence the framework-detection step above is essential.

4. **Test code skew.** Tests should normally be allowed to import everything. The workflow needs to exclude `tests/`, `__tests__/`, `*.test.*`, `*.spec.*`, `conftest.py` from layer-violation reports (but they're useful for fan-in counts).

5. **Generated code & migrations.** Django `migrations/`, Prisma `prisma/generated/`, OpenAPI clients — typically high fan-in/fan-out, will pollute hub/god-module rankings. Should be excluded.

6. **Re-export barrel files** (`index.ts` that re-exports everything). Inflate Ca on the barrel itself; deflate Ca on the underlying files. knip and dependency-cruiser have specific handling but it's imperfect [4][2].

7. **Type-only imports.** `import type { Foo } from '...'` in TS does not create a runtime edge. dependency-cruiser distinguishes them via `dependencyTypes`; pure madge does not.

8. **First-run noise.** On a large legacy codebase, every metric will trip thresholds. The workflow should report findings as *prioritized* (top-10 hub modules, top-10 high-D modules) rather than as pass/fail gates — matches the stated use case (on-demand audit + onboarding, not pre-commit gating).

9. **import-linter contract drift.** Once a contract is written, the *project* must keep it updated; for an *on-demand audit* with no prior contract, we should run import-linter only if `.importlinter` or `[tool.importlinter]` already exists — otherwise rely on heuristics. Same applies to `tach.toml`.

10. **ts-prune is dead.** Older blogs still recommend it; the author explicitly redirects users to knip [5][6]. Use knip exclusively for JS/TS dead-code detection.

---

## Sources

1. [GitHub - sverweij/dependency-cruiser](https://github.com/sverweij/dependency-cruiser) — Validate & visualise JS/TS dependencies, latest v17.4.0 (May 2026).
2. [dependency-cruiser CLI doc — `--metrics` flag](https://github.com/sverweij/dependency-cruiser/blob/main/doc/cli.md) — Built-in stability metrics output.
3. [GitHub - pahen/madge](https://github.com/pahen/madge) — Dependency-graph CLI, v8.0.0 (Aug 2024).
4. [Knip homepage](https://knip.dev/) and [GitHub - webpro-nl/knip](https://github.com/webpro-nl/knip) — Dead-code / unused-export tool, v6.14.1 (May 2026).
5. [Effective TypeScript — "Use knip to detect dead code"](https://effectivetypescript.com/2023/07/29/knip/) — Migration recommendation away from ts-prune.
6. [GitHub - nadeesha/ts-prune](https://github.com/nadeesha/ts-prune) — Maintenance-mode notice, archived 2025.
7. [GitHub - dyatko/arkit](https://github.com/dyatko/arkit) — Diagram tool, v2.1.0 (Mar 2026). Excluded for text-only constraint.
8. [GitHub - javierbrea/eslint-plugin-boundaries](https://github.com/javierbrea/eslint-plugin-boundaries) — Architecture-boundary ESLint plugin.
9. [eslint-plugin-boundaries npm registry](https://www.npmjs.com/package/eslint-plugin-boundaries) — v6.0.2 (Mar 2026).
10. [ESLint `no-restricted-imports`](https://eslint.org/docs/latest/rules/no-restricted-imports) — Notes static-only nature.
11. [Import Linter docs](https://import-linter.readthedocs.io/en/stable/) — Contract DSL for Python imports; v2.x line Jan 2024+.
12. [Piglei — 6 ways to improve Python project architecture](https://www.piglei.com/articles/en-6-ways-to-improve-the-arch-of-you-py-project/) — Practical import-linter usage walkthrough.
13. [GitHub - tach-org/tach](https://github.com/tach-org/tach) — Rust-powered Python boundary tool; v0.35.0 (May 2026).
14. [Tach documentation](https://docs.gauge.sh/) — `tach init`, `tach check`, interface enforcement.
15. [GitHub - thebjorn/pydeps](https://github.com/thebjorn/pydeps) and [Issue #22 false cycles with TYPE_CHECKING](https://github.com/thebjorn/pydeps/issues/22) — Known false positive.
16. [Pylint `cyclic-import` R0401 docs](https://pylint.pycqa.org/en/latest/user_guide/messages/refactor/cyclic-import.html) and [false-positive issue #9124](https://github.com/pylint-dev/pylint/issues/9124).
17. [GitHub - jendrikseipp/vulture](https://github.com/jendrikseipp/vulture) — Dead-code finder; v2.16 (Mar 2026).
18. [Entrofi — Coupling Metrics: Afferent & Efferent Coupling](https://www.entrofi.net/coupling-metrics-afferent-and-efferent-coupling/) — Ca/Ce/I formulas with Martin attribution.
19. [Mario Carrion — Measuring Instability as Software Package Metrics](https://mariocarrion.com/2021/06/18/golang-software-architecture-instability-efferent-afferent.html) — Worked example.
20. [DevLead.io — Principles of Component Coupling](https://devlead.io/DevTips/PrinciplesOfComponentCoupling) — Robert Martin's component principles.
21. [Hanselman — NDepend metrics placemats PDF](https://www.hanselman.com/blog/content/binary/NDepend+metrics+placemats+1.1.pdf) and [UML.org.cn OO Design Principles & Metrics](http://www.uml.org.cn/mxdx/OODesignPrinciplesMetrics2.pdf) — Abstractness, distance-from-main-sequence formulas.
22. [Stack Overflow — Suggested thresholds for software metrics](https://stackoverflow.com/questions/3388373/suggested-thresholds-for-some-software-metrics) — Threshold guidance and limits.
23. [NDepend blog — Lack of Cohesion of Methods](https://blog.ndepend.com/lack-of-cohesion-methods/) — LCOM variants and caveats.
24. [Milan Jovanović — Clean Architecture Folder Structure](https://www.milanjovanovic.tech/blog/clean-architecture-folder-structure) — Domain / Application / Infrastructure / Presentation canonical layout.
25. [Herbert Graca — Ports & Adapters Architecture](https://herbertograca.com/2017/09/14/ports-adapters-architecture/) — Hexagonal origins.
26. [AWS Prescriptive Guidance — Hexagonal architecture pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/hexagonal-architecture.html) — Ports/adapters in practice.
27. [GitHub - zhanymkanov/fastapi-best-practices](https://github.com/zhanymkanov/fastapi-best-practices) — De-facto FastAPI project structure (Netflix Dispatch-inspired).
28. [Next.js folder structure guide](https://www.marketingscoop.com/developer/next-js-folder-structure-what-each-layer-does-and-how-to-keep-large-apps-from-turning-messy/) — App Router conventions.
29. [NestJS docs — First steps](https://docs.nestjs.com/first-steps) and community NestJS project-structure guides — Module/controller/service convention.
30. [Django folder structure best practices guide](https://medium.com/@sizanmahmud08/django-folder-structure-best-practices-a-complete-guide-to-scalable-project-organization-508437899736) — App-per-feature with `models.py` / `views.py` / `serializers.py`.
