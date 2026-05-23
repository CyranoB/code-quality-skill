# Nitpicky Narwhal

![Nitpicky Narwhal](assets/header.jpeg)

_Most creatures with a three-metre spike protruding from their face would use it for something dramatic. Jousting, perhaps, or opening letters in a threatening manner. The narwhal instead uses it to poke at things in cold, dark water where nobody is watching, which is more or less what this skill does to your code at two in the morning. It will find the unused variable you left in a file you forgot existed. It will notice that module A imports module B which imports module C which imports module A. It will not be thanked for this, and it does not expect to be._

A code quality skill for AI agents. Linting, type checking, complexity analysis, and architecture review using whatever tools your project already has.

## What It Does

The skill finds your project's linter, runs it, normalizes the output, and hands you back findings you can act on. No server setup. No MCP configuration. It also runs an architecture review that covers cycles, layering violations, coupling metrics (Ca/Ce/I), hub and god modules, deep import chains, oversized files, dead code, and complex functions. Useful for a one-off audit, or when you're new to a codebase and want to get your bearings.

**No config? No problem.** The skill ships with built-in default configs (inspired by SonarQube's "Sonar way" quality profile) so analysis works even on projects with zero linter setup. When your project has its own config, the skill uses that instead.

**Supported tools** (all zero-install via `npx` or `uvx`):
- **JavaScript/TypeScript**: ESLint, Biome, madge (cycles), knip (dead code), tsc (types)
- **Python**: ruff, depcycle (cycles), vulture (dead code), pyright (types)

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

## Usage

Once installed, the skill triggers automatically when you ask your agent to:

- **Review code**: "review src/index.ts for code quality"
- **Fix issues**: "fix linting errors in this file"
- **Audit a project**: "audit my project for code quality"
- **Pre-commit check**: "check my changes before committing"
- **Complexity analysis**: "check complexity in src/" or "find complex functions"
- **Dependency analysis**: "find circular dependencies" or "check imports"
- **Architecture review**: "review architecture", "find hub modules", "layering violations", "show me the structure"
- **Type check**: "verify types", "run pyright", "check types"
- **Linter setup**: "set up linting" or "configure eslint for my project"
- **Run a specific linter**: "run eslint on src/"
- **Find bugs**: "any issues in main.py?"

### Examples

```
> review src/index.ts
> fix lint issues in src/
> audit the whole project
> check before commit
> check complexity in my Python code
> find complex functions
> find circular dependencies in src/
> check for orphan modules
> review the architecture of this project
> find hub modules
> onboard me to this codebase
> set up linting for my project
> configure eslint with typescript
> run ruff on my Python files
> clean up this code
```

## How It Works

1. **Detection**: Automatically discovers your project's linter and framework by checking config files, `package.json`, and `pyproject.toml`
2. **Analysis**: Runs the linter with JSON output for structured parsing
3. **Normalization**: Maps tool-specific severity levels to a unified 5-tier scale (BLOCKER → CRITICAL → MAJOR → MINOR → INFO)
4. **Presentation**: Shows findings grouped by severity with explanations and fix suggestions
5. **Fixing**: Uses the tool's native `--fix` and re-analyzes to confirm
6. **Dependency analysis**: Detects circular dependencies and orphan modules — madge for JS/TS, depcycle for Python (both zero-install via `npx`/`uvx`)
7. **Architecture review**: A small Python orchestrator builds the dependency graph (using `ast` for Python and `npx madge` for JS/TS). From that graph it computes coupling metrics (Ca/Ce/I) and finds cycles, layering violations (the Dependency Rule), hub and god modules, deep import chains, oversized files, and excessive public exports. Layers are inferred from folder conventions, with adjustments for Next.js, Django, FastAPI, NestJS, Flask, and Express. Dead code (via `knip` or `vulture`) and complex functions (via ruff C901 or ESLint complexity) round out the report.

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

When no project-level linter config is found, the skill uses its built-in defaults from `defaults/`:

### Python (`defaults/ruff.toml`)

11 rule categories enabled: pycodestyle errors/warnings, pyflakes, cyclomatic complexity (max 10), import sorting, naming conventions, pyupgrade, bugbear, security (bandit), simplify, and print statements. Pragmatic per-file ignores (allows `assert` in tests, `print` in scripts).

### JavaScript/TypeScript — Biome (zero-config)

When no linter is configured, the skill uses Biome as the fallback. Biome handles both JS and TS natively — no parser plugins needed. Built-in rules cover correctness (unused variables, unreachable code), suspicious patterns (`noExplicitAny`, `noDoubleEquals`), complexity, and formatting. ESLint can't parse TypeScript without `@typescript-eslint/parser`, making Biome the better zero-config choice.

To use your own rules instead, create a config file in your project root (`ruff.toml`, `eslint.config.js`, etc.) and the skill will use that automatically.

## Severity Levels

| Tag | Level | Meaning |
|-----|-------|---------|
| `[BLK]` | BLOCKER | Crashes, data loss, security vulnerabilities |
| `[CRT]` | CRITICAL | Definite bugs, logic errors |
| `[MAJ]` | MAJOR | Likely bugs, bad practices |
| `[MIN]` | MINOR | Style issues, conventions |
| `[INF]` | INFO | Suggestions, formatting |

## File Structure

```
code-quality-skill/
├── .claude-plugin/
│   ├── plugin.json            # Plugin manifest
│   └── marketplace.json       # Self-hosted marketplace definition
├── skills/
│   └── code-quality/
│       ├── SKILL.md           # Core skill definition (Workflows A–I)
│       ├── scripts/
│       │   ├── detect-linter.sh   # Auto-detect linter + framework
│       │   ├── arch-review.sh     # Wrapper for the architecture-review orchestrator
│       │   └── arch_review/       # Stdlib-only Python package
│       │       ├── runner.py      # Parallel orchestrator → JSON
│       │       ├── graph.py       # Dep graph (ast + madge)
│       │       ├── metrics.py     # Cycles (Tarjan SCC), Ca/Ce/I, deep chains
│       │       ├── layers.py      # Heuristic layer inference + violations
│       │       ├── smells.py      # LoC, public exports
│       │       ├── dead_code.py   # knip + vulture wrappers
│       │       ├── complexity.py  # ruff C901 + ESLint complexity wrappers
│       │       ├── fixtures/      # clean / violations × py / js
│       │       └── tests/         # 56 unit + integration tests
│       ├── defaults/
│       │   ├── ruff.toml          # Default Python config (SonarQube-inspired)
│       │   └── eslint.config.js   # Default JS/TS config (SonarQube-inspired)
│       └── references/
│           ├── eslint.md          # ESLint CLI reference
│           ├── biome.md           # Biome CLI reference
│           ├── ruff.md            # Ruff CLI reference
│           ├── pyright.md         # Pyright CLI reference
│           ├── madge.md           # Madge (JS/TS dependency analysis)
│           ├── pydeps.md          # Python dependency analysis (depcycle + pydeps)
│           ├── architecture.md    # Workflow I: layers, framework rules, JSON schema
│           ├── knip.md            # Knip (JS/TS dead code)
│           ├── vulture.md         # Vulture (Python dead code)
│           └── severity-map.md    # Severity normalization
├── docs/
│   └── superpowers/               # Design specs, plans, and research notes
├── README.md
└── LICENSE
```

## Requirements

- A supported coding agent. Install with `npx skills add CyranoB/code-quality-skill` for Claude Code, Codex CLI, Cursor, Cline, Gemini CLI, Windsurf, and other supported agents.
- **Python**: nothing to install. `uvx ruff` runs without a permanent install.
- **JavaScript/TypeScript**: nothing to install for the fallback path. Biome via `npx` handles both JS and TS natively. If you prefer ESLint, create an `eslint.config.js` and the skill picks it up.
- **Dependency analysis**: madge (`npx madge`) for JS/TS, depcycle (`uvx depcycle`) for Python. Both run without installing anything globally.
- **Architecture review (Workflow I)**: `python3` on the host. The system Python on macOS or Linux works; nothing else to install. Two optional sub-checks need extra tools: `npx knip` for JS/TS dead code, and `uvx vulture` for Python dead code. Both get fetched on first use.

## License

MIT
