# code-quality

A Claude Code skill for code quality analysis, linting, and auto-fixes. Works out of the box — no linter configuration required.

## What It Does

This skill detects your project's linter, runs it, normalizes the output, and presents actionable findings — all without any server setup or MCP configuration.

**No config? No problem.** The skill ships with built-in default configs (inspired by SonarQube's "Sonar way" quality profile) so analysis works even on projects with zero linter setup. When your project has its own config, the skill uses that instead.

**Supported tools**:
- **JavaScript/TypeScript**: ESLint, Biome, madge (dependency analysis)
- **Python**: ruff, pydeps (dependency analysis)

## Installation

### From the marketplace (recommended)

```bash
# Add the marketplace
claude plugin marketplace add CyranoB/code-quality-skill

# Install the plugin
claude plugin install code-quality@code-quality-marketplace
```

### From a local clone

```bash
claude skill install /path/to/code-quality-skill
```

## Usage

Once installed, the skill triggers automatically when you ask Claude Code to:

- **Review code**: "review src/index.ts for code quality"
- **Fix issues**: "fix linting errors in this file"
- **Audit a project**: "audit my project for code quality"
- **Pre-commit check**: "check my changes before committing"
- **Complexity analysis**: "check complexity in src/" or "find complex functions"
- **Dependency analysis**: "find circular dependencies" or "check imports"
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
> run ruff on my Python files
> clean up this code
```

## How It Works

1. **Detection**: Automatically discovers your project's linter by checking config files, `package.json`, and `pyproject.toml`
2. **Analysis**: Runs the linter with JSON output for structured parsing
3. **Normalization**: Maps tool-specific severity levels to a unified 5-tier scale (BLOCKER → CRITICAL → MAJOR → MINOR → INFO)
4. **Presentation**: Shows findings grouped by severity with explanations and fix suggestions
5. **Fixing**: Uses the tool's native `--fix` and re-analyzes to confirm
6. **Dependency analysis**: Detects circular dependencies and orphan modules — madge for JS/TS, pydeps for Python (both zero-install via `npx`/`uvx`)

## Detection Priority

### JavaScript/TypeScript
1. `package.json` lint script
2. `eslint.config.*` or `.eslintrc*` → ESLint
3. `biome.json` / `biome.jsonc` → Biome
4. `eslint` in devDependencies → ESLint
5. `@biomejs/biome` in devDependencies → Biome
6. Fallback: JS/TS files present → ESLint with built-in default config

### Python
1. `ruff.toml` / `.ruff.toml` → ruff
2. `pyproject.toml` with `[tool.ruff]` → ruff
3. `.pylintrc` or `[tool.pylint]` → pylint
4. Fallback: .py files present → `uvx ruff` with built-in default config (no install needed)

## Default Configs

When no project-level linter config is found, the skill uses its built-in defaults from `defaults/`:

### Python (`defaults/ruff.toml`)

11 rule categories enabled: pycodestyle errors/warnings, pyflakes, cyclomatic complexity (max 10), import sorting, naming conventions, pyupgrade, bugbear, security (bandit), simplify, and print statements. Pragmatic per-file ignores (allows `assert` in tests, `print` in scripts).

### JavaScript (`defaults/eslint.config.js`)

Core ESLint rules only (no plugins required): error detection (`no-unused-vars`, `no-unreachable`), best practices (`eqeqeq`, `prefer-const`), cyclomatic complexity (max 10), security (`no-eval`), debug artifacts (`no-console`, `no-debugger`).

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
│       ├── SKILL.md           # Core skill definition
│       ├── scripts/
│       │   └── detect-linter.sh   # Auto-detect project linter
│       ├── defaults/
│       │   ├── ruff.toml          # Default Python config (SonarQube-inspired)
│       │   └── eslint.config.js   # Default JS/TS config (SonarQube-inspired)
│       └── references/
│           ├── eslint.md      # ESLint CLI reference
│           ├── biome.md       # Biome CLI reference
│           ├── ruff.md        # Ruff CLI reference
│           ├── madge.md       # Madge CLI reference (JS/TS dependency analysis)
│           ├── pydeps.md      # Pydeps CLI reference (Python dependency analysis)
│           └── severity-map.md    # Severity normalization
├── README.md
└── LICENSE
```

## Requirements

- Claude Code CLI
- **Python**: No setup needed — uses `uvx ruff` which runs without installation
- **JavaScript/TypeScript**: ESLint must be available via `npx` (install with `npm install --save-dev eslint` if needed). Alternatively, Biome works too (`npm install --save-dev @biomejs/biome`)
- **Dependency analysis**: madge (`npx madge`) for JS/TS, pydeps (`uvx pydeps`) for Python — both zero-install

## License

MIT
