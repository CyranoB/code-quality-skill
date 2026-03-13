# Claude Code Development Guide — code-quality-skill

## Git Workflow

**Never push without explicit user confirmation.** Always stage and commit, then ask the user before pushing.

## Commit Convention

Use conventional commits:
- `feat:` — New features (new workflows, tools, reference files)
- `fix:` — Bug fixes
- `docs:` — Documentation only
- `refactor:` — Code restructuring

## Project Structure

```
skills/code-quality/
├── SKILL.md              # Core skill definition (workflows A–F)
├── scripts/
│   └── detect-linter.sh  # Auto-detect project linter
├── defaults/
│   ├── ruff.toml         # Default Python config (SonarQube-inspired)
│   └── eslint.config.js  # Default JS/TS config (SonarQube-inspired)
└── references/
    ├── eslint.md         # ESLint CLI reference
    ├── biome.md          # Biome CLI reference
    ├── ruff.md           # Ruff CLI reference
    ├── pyright.md        # Pyright CLI reference (Python type checking)
    ├── madge.md          # Madge (JS/TS dependency analysis)
    ├── pydeps.md         # Pydeps (Python dependency analysis)
    └── severity-map.md   # Severity normalization mapping
```

## Key Design Principles

- **Zero-config by default**: Ship built-in configs so analysis works out of the box (SonarQube "Sonar way" inspired)
- **Use what the project has**: If a project has its own linter config, use it; only fall back to defaults when none exists
- **Zero-install where possible**: `uvx ruff`, `uvx pydeps`, `npx madge` — no permanent installation needed
- **Structured output**: Always use JSON output from tools when available, parse text when not

## Workflows

| Workflow | Purpose | Tools |
|----------|---------|-------|
| A | Review file/code | ESLint, Biome, ruff |
| B | Fix issues | ESLint --fix, ruff --fix, Biome --write |
| C | Project audit | Same as A, full project scope |
| D | Pre-commit check | Linter + type checker on changed files |
| E | Complexity analysis | ESLint complexity rule, ruff C901 |
| F | Dependency analysis | madge (JS/TS), depcycle (Python) |
| G | Linter setup | npm init @eslint/config, ruff.toml, biome init |
| H | Type checking | pyright (Python), tsc (TypeScript) |
