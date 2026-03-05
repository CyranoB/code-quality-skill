# code-quality

A Claude Code skill for code quality analysis, linting, and auto-fixes using project-native tools.

## What It Does

This skill detects your project's linter, runs it, normalizes the output, and presents actionable findings — all without any server setup or MCP configuration.

**Supported tools**:
- **JavaScript/TypeScript**: ESLint, Biome
- **Python**: ruff

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
- **Run a specific linter**: "run eslint on src/"
- **Find bugs**: "any issues in main.py?"

### Examples

```
> review src/index.ts
> fix lint issues in src/
> audit the whole project
> check before commit
> run ruff on my Python files
> clean up this code
```

## How It Works

1. **Detection**: Automatically discovers your project's linter by checking config files, `package.json`, and `pyproject.toml`
2. **Analysis**: Runs the linter with JSON output for structured parsing
3. **Normalization**: Maps tool-specific severity levels to a unified 5-tier scale (BLOCKER → CRITICAL → MAJOR → MINOR → INFO)
4. **Presentation**: Shows findings grouped by severity with explanations and fix suggestions
5. **Fixing**: Uses the tool's native `--fix` and re-analyzes to confirm

## Detection Priority

### JavaScript/TypeScript
1. `package.json` lint script
2. `eslint.config.*` or `.eslintrc*` → ESLint
3. `biome.json` / `biome.jsonc` → Biome
4. `eslint` in devDependencies → ESLint
5. `@biomejs/biome` in devDependencies → Biome
6. Fallback: JS/TS files present → ESLint with defaults

### Python
1. `ruff.toml` / `.ruff.toml` → ruff
2. `pyproject.toml` with `[tool.ruff]` → ruff
3. `.pylintrc` or `[tool.pylint]` → pylint
4. Fallback: .py files present → `uvx ruff` (no install needed)

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
│       └── references/
│           ├── eslint.md      # ESLint CLI reference
│           ├── biome.md       # Biome CLI reference
│           ├── ruff.md        # Ruff CLI reference
│           └── severity-map.md    # Severity normalization
├── README.md
└── LICENSE
```

## Requirements

- Claude Code CLI
- At least one supported linter installed in your project (or globally):
  - ESLint (`npm install --save-dev eslint`)
  - Biome (`npm install --save-dev @biomejs/biome`)
  - ruff (`pip install ruff` or use via `uvx ruff`)

## License

MIT
