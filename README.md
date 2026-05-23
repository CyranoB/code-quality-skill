# Nitpicky Narwhal

![Nitpicky Narwhal](assets/header.jpeg)

_Most creatures with a three-metre spike protruding from their face would use it for something dramatic. Jousting, perhaps, or opening letters in a threatening manner. The narwhal instead uses it to poke at things in cold, dark water where nobody is watching, which is more or less what this skill does to your code at two in the morning. It will find the unused variable you left in a file you forgot existed. It will notice that module A imports module B which imports module C which imports module A. It will not be thanked for this, and it does not expect to be._

A code quality skill for AI agents. Linting, type checking, complexity analysis, security scanning, and architecture review using whatever tools your project already has.

## What It Does

The skill finds your project's linter, runs it, normalizes the output, and hands you back findings you can act on. No server setup. No MCP configuration. No tokens wasted when not in use. It also runs deeper analysis: architecture review, dual-metric complexity, security scanning, and type checking — all zero-install where possible via `npx` or `uvx`.

**No config? No problem.** The skill ships with built-in defaults (inspired by SonarQube's "Sonar way" quality profile) so analysis works even on projects with zero linter setup. When your project has its own config, the skill uses that instead.

**Supported languages and tools**:
- **JavaScript/TypeScript**: ESLint, Biome, madge (cycles), knip (dead code), tsc (types), eslint-plugin-sonarjs (cognitive complexity)
- **Python**: ruff, depcycle (cycles), vulture (dead code), pyright (types), flake8-cognitive-complexity
- **Security (all languages)**: Semgrep (SAST, 2000+ OWASP/CWE rules), detect-secrets (hardcoded credentials)

## Install

```bash
npx skills add CyranoB/code-quality-skill
```

Auto-detects your coding agent, installs into the current project by default, and supports Claude Code, Cursor, Codex, Cline, Gemini CLI, Windsurf, and [50+ others](https://github.com/vercel-labs/skills).

**Global install** (available in every project):

```bash
npx skills add CyranoB/code-quality-skill -g
```

<details>
<summary><strong>Alternative install methods</strong></summary>

### Claude Code plugin marketplace

```text
/plugin marketplace add CyranoB/code-quality-skill
/plugin install code-quality@code-quality-marketplace
```

Restart Claude Code, then check `/skills`.

### Manual clone

Copy the skill directory into the skills directory used by your agent. For agents that read `.agents/skills/`:

```bash
git clone https://github.com/CyranoB/code-quality-skill.git
mkdir -p .agents/skills
cp -R code-quality-skill/skills/code-quality .agents/skills/
```

Agent-specific paths vary, so use your agent's documented project or global skills directory if it does not read `.agents/skills/`.

### Aider

Aider has no skill loader. Load the workflow file as a read-only convention:

```bash
git clone https://github.com/CyranoB/code-quality-skill.git
aider --read code-quality-skill/skills/code-quality/SKILL.md
```

Or add the path to your `.aider.conf.yml` under `read:`.

</details>

The skill needs `bash`, `python3`, `npx`, and `uvx` on PATH. Local agents almost always have these. If your agent runs in a sandbox, check that the sandbox includes them.

## Workflows

### A — Review File or Code

**Triggers**: "review src/index.ts", "what's wrong with this file?", "lint main.py", "any issues in auth.ts?"

Runs the project's linter on a specific file or directory. Maps tool-native severity to a unified 5-tier scale (BLOCKER → CRITICAL → MAJOR → MINOR → INFO). For MAJOR and above, explains why the issue matters and suggests a concrete fix.

### B — Fix Issues

**Triggers**: "fix linting errors", "clean up src/", "auto-fix this file"

Runs the linter to get a baseline, applies `--fix` / `--write`, then re-analyzes to show exactly what changed and what couldn't be auto-fixed. For issues without a fix, provides specific code changes to apply manually.

### C — Project Audit

**Triggers**: "audit my project", "scan the whole project", "overall code quality report"

Full-project lint run. Caps output at 50 findings sorted by severity. Shows the most problematic files, a severity breakdown, and quick-win auto-fixable counts. Offers follow-up actions (fix, drill into a file, check dependencies).

### D — Pre-commit Check

**Triggers**: "check before commit", "pre-commit check", "ready to commit?", "lint my changes"

Detects changed files via git, lints only those files, and also runs the type checker (pyright for Python, tsc for TypeScript) if one is configured. Returns a clear PASS or FAIL verdict. Designed to be fast enough to run every commit.

### E — Complexity Analysis (Cognitive + Cyclomatic)

**Triggers**: "check complexity", "find complex functions", "cognitive complexity", "hard to test", "hard to read", "refactor candidates"

Reports **both** cyclomatic and cognitive complexity in a single table. Cognitive is the headline metric — it tracks human reading effort (the strongest predictor of defect density) by penalizing nesting and sequence breaks. Cyclomatic stays as a secondary column for test coverage planning.

| Metric | Threshold | Severity |
|--------|-----------|---------|
| Cognitive complexity | 15 | 16–25 → MAJOR, ≥26 → CRITICAL |
| Cyclomatic complexity | 10 | any excess → MAJOR |

Python uses `ruff C901` + `flake8-cognitive-complexity` (both via `uvx`). JS/TS uses the core ESLint `complexity` rule + `eslint-plugin-sonarjs` `cognitive-complexity` (bundled in `defaults/package.json`, installed once on first use via `npm ci`). For each finding, provides refactoring suggestions: extract method, early returns, guard clauses, table dispatch.

### F — Dependency Analysis

**Triggers**: "find circular dependencies", "check imports", "find cycles", "orphan modules", "dependency graph"

Detects circular imports (CRITICAL — causes runtime crashes and breaks tree-shaking) and orphan modules (INFO — unused files). Uses `npx madge` for JS/TS and `uvx depcycle` for Python, both zero-install. For each cycle, explains the coupling and recommends the extraction move to break it.

### G — Linter Setup

**Triggers**: "set up linting", "configure eslint", "configure ruff", "add a linter to my project"

The only workflow that modifies the project. Detects the language, checks if a config already exists, then sets up the appropriate linter (ruff for Python, ESLint for JS/TS, Biome as an alternative). Uses the skill's built-in defaults as a starting point. Verifies the setup by re-running detection and offers to run an initial audit.

### H — Type Checking

**Triggers**: "type check", "verify types", "run pyright", "check types", "type errors"

Runs `npx pyright` (Python) or `npx tsc --noEmit` (TypeScript) and normalizes the output. Pyright errors map to CRITICAL; warnings to MAJOR. Filters `reportMissingTypeStubs` noise into a single summary line. Also wires into Workflow D — type errors block the pre-commit verdict just like lint errors.

### I — Architecture Review

**Triggers**: "architecture review", "find hub modules", "layering violations", "coupling metrics", "show me the structure", "onboard me to this codebase"

A full structural audit with ten sections, intended for audits and onboarding. A Python orchestrator runs all sections in parallel and returns a single JSON report.

| Section | What it detects |
|---------|----------------|
| Cycles | Circular dependency clusters (Tarjan SCC) |
| Layering violations | Imports that break the Dependency Rule |
| Hub modules | Modules with abnormally high in-degree (Ca) |
| God modules | Modules that are both heavy importers and importees |
| Instability hotspots | Modules with low stability (Ce/(Ca+Ce)) |
| Deep import chains | Import paths longer than configured threshold |
| Oversized files | Files exceeding line-count threshold |
| Excessive exports | Modules exporting more than the threshold |
| Dead code | Unused exports (knip for JS/TS, vulture for Python) |
| Complex functions | Functions over cyclomatic + cognitive thresholds |

Framework-aware layer inference (Next.js, Django, FastAPI, NestJS, Flask, Express). All thresholds configurable via CLI flags. Use `--skip-section` to drop any noisy section.

### J — Security Scan

**Triggers**: "security scan", "OWASP scan", "find vulnerabilities", "SAST", "check for hardcoded secrets", "find API keys", "leaked credentials", "any secrets in this repo?"

Runs two tools in parallel (both zero-install via `uvx`):

- **Semgrep** with the `p/security-audit` ruleset (~2000 rules covering OWASP Top 10, CWE Top 25, injection, XSS, SSRF, path traversal, deserialization, and more). Severity: ERROR → BLOCKER, WARNING → CRITICAL, INFO → MAJOR.
- **detect-secrets** scans for hardcoded credentials: AWS keys, private keys, tokens, high-entropy strings, generic passwords. Every finding is a BLOCKER — committed credentials must be rotated.

Default exclude list: `.git/`, `node_modules/`, `dist/`, `build/`, `venv/`, lockfiles, `*.min.js`, `*.map`. Use `--skip-section semgrep` or `--skip-section secrets` to run only one tool. Findings capped at 200 per section with `truncated: true` when exceeded.

## Usage

Once installed, the skill triggers automatically when you describe what you want:

```
> review src/index.ts
> fix lint issues in src/
> audit the whole project
> check before commit
> check complexity in my Python code
> find complex functions
> cognitive complexity in src/auth.py
> security scan this project
> any hardcoded secrets in this repo?
> OWASP scan src/
> find circular dependencies in src/
> check for orphan modules
> review the architecture of this project
> find hub modules
> onboard me to this codebase
> set up linting for my project
> configure eslint with typescript
> run ruff on my Python files
> type check my code
> verify types
> clean up this code
```

## Severity Scale

All workflows normalize tool-specific output to the same 5-tier scale:

| Tag | Level | Meaning |
|-----|-------|---------|
| `[BLK]` | BLOCKER | Crashes, data loss, hardcoded secrets, security vulnerabilities |
| `[CRT]` | CRITICAL | Definite bugs, logic errors, type errors, circular dependencies |
| `[MAJ]` | MAJOR | Likely bugs, bad practices, high complexity, Semgrep warnings |
| `[MIN]` | MINOR | Style issues, conventions, pyright warnings |
| `[INF]` | INFO | Suggestions, orphan modules, formatting |

## Detection Priority

### JavaScript/TypeScript
1. `package.json` lint script
2. `eslint.config.*` or `.eslintrc*` → ESLint
3. `biome.json` / `biome.jsonc` → Biome
4. `eslint` in devDependencies → ESLint
5. `@biomejs/biome` in devDependencies → Biome
6. Fallback: JS/TS files present → Biome (zero-config, handles both JS and TS natively)

### Python
1. `ruff.toml` / `.ruff.toml` → ruff
2. `pyproject.toml` with `[tool.ruff]` → ruff
3. `.pylintrc` or `[tool.pylint]` → pylint
4. Fallback: .py files present → `uvx ruff` with built-in default config (no install needed)

## Default Configs

When no project-level linter config is found, the skill uses its built-in defaults from `defaults/`.

### Python (`defaults/ruff.toml`)

11 rule categories enabled: pycodestyle errors/warnings, pyflakes, cyclomatic complexity (max 10), import sorting, naming conventions, pyupgrade, bugbear, security (bandit), simplify, and print statements. Pragmatic per-file ignores (allows `assert` in tests, `print` in scripts). Runs via `uvx ruff` — zero install needed.

### JavaScript/TypeScript — Biome (zero-config fallback for Workflows A/C/D)

When no linter is configured, Workflows A/C/D use Biome as the fallback. Biome handles both JS and TS natively — no parser plugins needed. Built-in rules cover correctness (unused variables, unreachable code), suspicious patterns (`noExplicitAny`, `noDoubleEquals`), complexity, and formatting. ESLint can't parse TypeScript without `@typescript-eslint/parser`, making Biome the better zero-config choice.

### JavaScript/TypeScript — Bundled ESLint + sonarjs (Workflows E and I)

Complexity analysis (Workflow E) and the complex-functions section of the architecture review (Workflow I) use a bundled ESLint with `eslint-plugin-sonarjs` for cognitive complexity. The skill installs this once on first use via `npm ci` (~30MB into `defaults/node_modules`, ~15s) using a committed lockfile for reproducible installs. Subsequent runs are instant. This is entirely separate from your project's own ESLint config — it won't interfere with Workflows A/C/D. Requires `npm` / Node.js on PATH.

To use your own rules instead, create a config file in your project root and the skill will pick it up for Workflows A/C/D.

## File Structure

```
code-quality-skill/
├── .claude-plugin/
│   ├── plugin.json            # Plugin manifest
│   └── marketplace.json       # Self-hosted marketplace definition
├── skills/
│   └── code-quality/
│       ├── SKILL.md           # Core skill definition (Workflows A–J)
│       ├── scripts/
│       │   ├── detect-linter.sh      # Auto-detect linter + framework
│       │   ├── arch-review.sh        # Wrapper for the architecture-review orchestrator
│       │   ├── security-scan.sh      # Wrapper for the security-scan orchestrator
│       │   ├── eslint-defaults.sh    # Lazy-bootstrap wrapper for bundled ESLint
│       │   ├── arch_review/          # Stdlib-only Python package
│       │   │   ├── runner.py         # Parallel orchestrator → JSON
│       │   │   ├── graph.py          # Dep graph (ast + madge)
│       │   │   ├── metrics.py        # Cycles (Tarjan SCC), Ca/Ce/I, deep chains
│       │   │   ├── layers.py         # Heuristic layer inference + violations
│       │   │   ├── smells.py         # LoC, public exports
│       │   │   ├── dead_code.py      # knip + vulture wrappers
│       │   │   ├── complexity.py     # Cyclomatic + cognitive complexity (dual-metric)
│       │   │   ├── fixtures/         # clean / violations × py / js
│       │   │   └── tests/            # 76 unit + integration tests
│       │   └── security_scan/        # Stdlib-only Python package
│       │       ├── runner.py         # Parallel orchestrator → JSON (semgrep + secrets)
│       │       ├── semgrep.py        # Semgrep SAST wrapper (uvx, p/security-audit)
│       │       ├── secrets.py        # detect-secrets wrapper (uvx, BLOCKER findings)
│       │       └── tests/            # 29 unit tests + fixtures
│       ├── defaults/
│       │   ├── ruff.toml             # Default Python config (SonarQube-inspired)
│       │   ├── eslint.config.js      # Default JS/TS config (sonarjs + core rules)
│       │   ├── package.json          # Pinned ESLint + sonarjs + TS parser deps
│       │   └── package-lock.json     # Committed lockfile for reproducible installs
│       └── references/
│           ├── eslint.md             # ESLint CLI reference + skill defaults usage
│           ├── biome.md              # Biome CLI reference
│           ├── ruff.md               # Ruff CLI reference
│           ├── pyright.md            # Pyright CLI reference
│           ├── madge.md              # Madge (JS/TS dependency analysis)
│           ├── pydeps.md             # Python dependency analysis (depcycle + pydeps)
│           ├── architecture.md       # Workflow I: layers, framework rules, JSON schema
│           ├── knip.md               # Knip (JS/TS dead code)
│           ├── vulture.md            # Vulture (Python dead code)
│           ├── cognitive-complexity.md  # Cognitive vs cyclomatic, parsers, refactoring
│           ├── semgrep.md            # Semgrep config registry, JSON schema, suppressions
│           ├── secrets.md            # detect-secrets plugins, false-positive triage
│           └── severity-map.md       # Severity normalization (all tools + cognitive tiers)
├── docs/
│   └── superpowers/               # Design specs, plans, and research notes
├── README.md
└── LICENSE
```

## Requirements

- A supported coding agent. Install with `npx skills add CyranoB/code-quality-skill` for Claude Code, Codex CLI, Cursor, Cline, Gemini CLI, Windsurf, and other supported agents.
- **Python linting / complexity**: nothing to install. `uvx ruff` and `uvx flake8-cognitive-complexity` run without a permanent install. Requires `uvx` (`pip install uv` or `brew install uv`).
- **JavaScript/TypeScript linting (Workflows A/C/D)**: nothing to install. Biome via `npx` handles both JS and TS natively. If you prefer ESLint, create an `eslint.config.js` and the skill picks it up.
- **JS/TS cognitive complexity (Workflows E/I)**: installs `eslint-plugin-sonarjs` once via `npm ci` on first use (~15s, ~30MB into `defaults/node_modules`). Requires `npm` / Node.js on PATH.
- **Dependency analysis**: madge (`npx madge`) for JS/TS, depcycle (`uvx depcycle`) for Python. Both run without installing anything globally.
- **Architecture review (Workflow I)**: `python3` on the host (system Python on macOS/Linux works). Optional sub-checks: `npx knip` for JS/TS dead code, `uvx vulture` for Python dead code, fetched on first use.
- **Security scan (Workflow J)**: `uvx` on PATH. Semgrep and detect-secrets are fetched on first use — no permanent install needed. If `uvx` is absent, the section skips with a warning rather than failing.
- **Type checking (Workflow H/D)**: `npx pyright` for Python (zero-install), `npx tsc` for TypeScript (requires the project to have TypeScript installed).

## License

MIT
