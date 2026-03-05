---
name: code-quality
description: >-
  Run code quality analysis, linting, and auto-fixes using project-native tools
  (ESLint, Biome, ruff). Use this skill whenever the user asks to "review code",
  "lint this file", "check code quality", "fix linting errors", "audit my project",
  "check before commit", "run static analysis", "find bugs", "clean up this code",
  or "pre-commit check". Also triggers when mentioning ESLint, ruff, Biome, or
  code quality issues like unused variables, type errors, or style violations.
  Also triggers on "cyclomatic complexity", "check complexity", "find complex
  functions", "complexity analysis", "too complex", or "hard to test".
  Also triggers on "circular dependencies", "circular imports", "dependency
  graph", "check imports", "module dependencies", "find cycles", or "orphan
  modules".
---

# Code Quality Skill

Analyze and fix code quality issues using the project's own linting tools. This skill detects the project's linter (ESLint, Biome, or ruff), runs it with JSON output, normalizes the results into a consistent severity format, and presents actionable findings.

**Core principle**: Use what the project already has. No external services, no server setup, no token overhead when not in use.

**Supported tools**:
- **JavaScript/TypeScript**: ESLint, Biome
- **Python**: ruff

## Step 1: Detect the Project's Linter

Before any analysis, determine the skill directory (the directory containing this SKILL.md file) and run detection.

```bash
bash <skill-dir>/scripts/detect-linter.sh [target-path]
```

Replace `<skill-dir>` with the absolute path to the directory containing this SKILL.md. For example, if this file is at `/Users/alice/.claude/skills/code-quality/SKILL.md`, the command is `bash /Users/alice/.claude/skills/code-quality/scripts/detect-linter.sh [target-path]`.

This outputs key=value pairs. Parse these values:

| Key | Use |
|-----|-----|
| `TOOL` | Which linter (eslint, biome, ruff, npm-script, none) |
| `COMMAND` | Full command to run analysis with JSON output |
| `FIX_COMMAND` | Full command to auto-fix issues |
| `CONFIG` | Path to config file (empty = no explicit config) |
| `LANGUAGE` | javascript or python |
| `FALLBACK` | "true" if no explicit config was found |
| `PROJECT_ROOT` | Detected project root |
| `FILES` | File list (only with --changed-only) |

**If TOOL=none and LANGUAGE=unknown**: No supported language detected. Tell the user the skill doesn't support this project type yet.

**If FALLBACK=true**: The skill's built-in default config is being used (see "Default Configs" below). This is normal and the analysis will work out of the box. Inform the user:
> "No linter config found in your project. Running with the skill's built-in defaults (SonarQube-inspired rules). To customize, create your own config file."

**If TOOL=npm-script**: The project has a custom lint script but no recognized linter config for JSON output. Run the `COMMAND` (e.g., `npm run lint`) and parse the human-readable text output instead. Look for patterns like `file:line:col: message` or ESLint/Biome-style output. If the output is unstructured, present it verbatim and let the user interpret it.

**If TOOL=pylint**: Pylint has no auto-fix capability (`FIX_COMMAND` will be empty). Provide manual fix suggestions instead. Pylint's JSON output uses `message-id` (e.g., `C0114`) and `type` (`convention`, `refactor`, `warning`, `error`, `fatal`). Map these to the unified severity: `fatal` → BLOCKER, `error` → CRITICAL, `warning` → MAJOR, `refactor` → MINOR, `convention` → INFO.

After detection, load the matching reference file from `<skill-dir>/references/` for tool-specific guidance:
- `TOOL=eslint` → read `<skill-dir>/references/eslint.md`
- `TOOL=biome` → read `<skill-dir>/references/biome.md`
- `TOOL=ruff` → read `<skill-dir>/references/ruff.md`

Only load `<skill-dir>/references/severity-map.md` when the linter reports issues (not on clean results — saves tokens).

## Default Configs

The skill ships with built-in configs in `<skill-dir>/defaults/` so analysis works out of the box — no project setup required. Inspired by SonarQube's "Sonar way" quality profile.

When no project-level config is found (`FALLBACK=true`), the detect script automatically uses these defaults via `--config` flags. The developer doesn't need to configure anything.

### Python — `defaults/ruff.toml`

Rules enabled: `E` (pycodestyle errors), `F` (pyflakes), `W` (pycodestyle warnings), `C90` (cyclomatic complexity), `I` (import sorting), `N` (naming), `UP` (pyupgrade), `B` (bugbear), `S` (security/bandit), `SIM` (simplify), `T20` (print statements). Complexity threshold: 10. Runs via `uvx ruff` — zero install needed.

### JavaScript/TypeScript — `defaults/eslint.config.js`

Core ESLint rules only (no plugins required): error detection (`no-unused-vars`, `no-undef`, `no-unreachable`), best practices (`eqeqeq`, `prefer-const`, `no-var`), cyclomatic complexity (threshold 10), security (`no-eval`), debug artifacts (`no-console`, `no-debugger`). Requires ESLint to be available via `npx`.

### When to suggest project-level config

After presenting results with defaults, add: "These results use the skill's built-in rules. To customize (adjust severity, disable rules, add plugins), create your own config:" and suggest:
- **ruff**: `ruff.toml` or `[tool.ruff]` in `pyproject.toml`
- **ESLint**: `npm init @eslint/config@latest`

## Workflow A: Review File or Code

**Triggers**: "review", "check", "what's wrong with", "lint", "analyze", "any issues in"

### Steps

1. **Detect**: Run `bash <skill-dir>/scripts/detect-linter.sh [project-path]`
2. **Scope**: Determine target files from user request (specific file, directory, or project)
3. **Run linter**: Execute the `COMMAND` with target files appended
   ```bash
   # Example for eslint:
   npx eslint --format json src/index.ts
   # Example for ruff:
   ruff check --output-format json src/main.py
   ```
4. **Handle exit codes**: Exit code 1 means issues were found (expected). Exit code 2 means a config or runtime error — report this to the user.
5. **Parse JSON output**: Extract file path, line, column, rule, message, severity from each finding.
6. **Normalize severity**: Map tool-native severity to the unified scale using `references/severity-map.md`.
   - Cyclomatic complexity violations (ESLint `complexity` rule, ruff `C901`) always map to **[MAJ] MAJOR** regardless of raw tool severity. High complexity predicts bugs and poor testability. Include the measured complexity vs. the configured threshold in the message (e.g., "complexity 15 > max 10"). C901 has no auto-fix — suggest manual refactoring (extract sub-functions, simplify conditionals, use early returns).
7. **Present findings**: Use the output format below. For MAJOR and above, include a brief explanation of why it matters and suggest a fix.

If no issues are found, report a clean result.

## Workflow B: Fix Issues

**Triggers**: "fix", "clean up", "auto-fix", "fix linting", "fix lint errors"

### Steps

1. **Detect**: Run `bash <skill-dir>/scripts/detect-linter.sh [project-path]`
2. **Analyze first**: Run the `COMMAND` to get a baseline of current issues
3. **Count baseline issues**: Note total count and severity breakdown
4. **Run fix command**: Execute the `FIX_COMMAND` with target files
   ```bash
   # Example for eslint:
   npx eslint --fix src/index.ts
   # Example for ruff:
   ruff check --fix src/main.py
   ```
5. **Re-analyze**: Run the `COMMAND` again to verify what was fixed and what remains
6. **Report results**: Show what was fixed (count, types) and what remains. For remaining issues without auto-fix, provide specific code changes the user can apply.

**Important**: Always explain what was fixed in plain language. Don't just say "5 issues fixed" — say "Replaced 3 `==` with `===`, removed 2 unused imports."

If the `FIX_COMMAND` is empty (e.g., pylint), inform the user and provide manual fix suggestions instead.

## Workflow C: Project Audit

**Triggers**: "audit", "project scan", "full analysis", "scan the whole project", "overall code quality"

### Steps

1. **Detect**: Run `bash <skill-dir>/scripts/detect-linter.sh [project-path]`
2. **Scope files**: Run the linter on the project root. The tool will respect `.gitignore` and skip `node_modules/`, `dist/`, `build/`, `venv/`, `__pycache__/` etc.
3. **Run linter**: Execute `COMMAND` on the project root directory
   ```bash
   # Example: run on whole project
   npx eslint --format json .
   ruff check --output-format json .
   ```
4. **Parse and normalize**: Process all findings
5. **Cap output**: If more than 50 issues, show the top 50 sorted by severity (BLOCKER first). State the total count and offer to drill into specific files.
6. **Present audit report**: Use the output format below with a summary header showing:
   - Total issues by severity
   - Most problematic files (top 5 by issue count)
   - Quick wins (issues that are auto-fixable)

Offer follow-up actions: "I can fix the N auto-fixable issues, drill into a specific file, or check for circular dependencies."

## Workflow D: Pre-commit Check

**Triggers**: "check before commit", "pre-commit", "check my changes", "ready to commit?", "lint changed files"

### Steps

1. **Get changed files**: Run detection with the `--changed-only` flag
   ```bash
   bash <skill-dir>/scripts/detect-linter.sh [project-path] --changed-only
   ```
2. **Check FILES output**: If `FILES` is empty, report "No lintable files in current changes."
3. **Run linter on changed files only**:
   ```bash
   # Example for eslint:
   npx eslint --format json file1.ts file2.ts
   # Example for ruff:
   ruff check --output-format json file1.py file2.py
   ```
4. **Present pass/fail verdict**:
   - **PASS**: "All changed files pass lint checks. Ready to commit."
   - **FAIL**: Show issues in changed files only, with severity and suggested fixes

## Workflow E: Complexity Analysis

**Triggers**: "check complexity", "find complex functions", "cyclomatic complexity", "complexity analysis", "too complex", "hard to test"

This workflow runs **with built-in defaults** — no project configuration required. The skill injects complexity rules via CLI flags so it works even when the project has no complexity rules configured. Inspired by SonarQube's default quality gate, which ships with complexity checks enabled out of the box.

### Default Threshold

| Metric | Max | Rationale |
|--------|-----|-----------|
| Cyclomatic complexity | **10** | Industry standard; matches ESLint and ruff defaults. SonarQube uses 15 for cognitive complexity — cyclomatic 10 is the equivalent bar. |

Functions at or below 10 are manageable. 11–20 = moderate risk. 21+ = high risk, should be refactored.

### Steps

1. **Detect**: Run `bash <skill-dir>/scripts/detect-linter.sh [project-path]` to get `TOOL` and `LANGUAGE`.
2. **Construct complexity command**: Do **not** use the generic `COMMAND`. Build a complexity-specific command based on the detected `TOOL` and `LANGUAGE`:

   **TOOL=ruff** (configured):
   ```bash
   ruff check --select C901 --output-format json [files...]
   ```

   **TOOL=eslint** (configured):
   ```bash
   npx eslint --rule '{"complexity": ["warn", 10]}' --format json [files...]
   ```

   **TOOL=biome**: Biome has no cyclomatic complexity rule. Inform the user: "Biome does not support complexity analysis. Consider adding ESLint alongside Biome for complexity checks, or switch to ruff for Python projects."

   **TOOL=pylint**: Pylint does not include mccabe by default. Fall back to ruff:
   ```bash
   uvx ruff check --select C901 --output-format json [files...]
   ```

   **TOOL=none, LANGUAGE=python**: Use ruff via uvx (works with zero project setup):
   ```bash
   uvx ruff check --select C901 --output-format json [files...]
   ```

   **TOOL=none, LANGUAGE=javascript**: ESLint requires a config file (ESLint 9+). Suggest: "Run `npm init @eslint/config@latest` to set up ESLint, then re-run complexity analysis."

   **TOOL=npm-script**: Try ESLint directly (may already be installed as a dependency):
   ```bash
   npx eslint --rule '{"complexity": ["warn", 10]}' --format json [files...]
   ```
   If this fails with exit code 2 (no config), suggest ESLint setup.

3. **Run the command**: Execute on the target files/directory.
4. **Parse and normalize**: Extract function name, measured complexity, and threshold from each finding. Map **all** complexity violations to **[MAJ] MAJOR** regardless of raw tool severity.
5. **Present findings**: Use the output format below. For each violation, include:
   - Function name and location
   - Measured complexity vs. threshold (e.g., "complexity 15 > max 10")
   - Actionable refactoring suggestion (extract helper functions, simplify conditionals, use early returns, replace nested if/else with guard clauses)

### Example Output

```
## Complexity Analysis Report

**Tool**: ruff (C901) | **Threshold**: 10 | **Files scanned**: 12

| File | Line | Function | Complexity | Severity |
|------|------|----------|------------|----------|
| src/orders.py | 23 | process_order | 18 | [MAJ] |
| src/auth.py | 45 | validate_token | 12 | [MAJ] |

**src/orders.py:23** (`process_order`, complexity 18):
This function has nearly twice the recommended complexity. Consider extracting
the discount calculation and inventory check into separate functions.

**src/auth.py:45** (`validate_token`, complexity 12):
Slightly above threshold. Simplify by using early returns for invalid cases.
```

### Clean Result

```
## Complexity Analysis Report

**Tool**: ruff (C901) | **Threshold**: 10 | **Files scanned**: 12

No functions exceed the complexity threshold. Code is well-structured.
```

**Important**: Complexity violations have no auto-fix. Always provide manual refactoring suggestions. Do not offer to run `--fix`.

## Workflow F: Dependency Analysis

**Triggers**: "circular dependencies", "circular imports", "dependency graph", "check imports", "module dependencies", "find cycles", "orphan modules"

Analyzes module dependency structure to find circular dependencies and orphan modules using **madge**. JavaScript/TypeScript only — for Python, note that no zero-install equivalent exists yet.

### Steps

1. **Detect**: Run `bash <skill-dir>/scripts/detect-linter.sh [project-path]` to get `LANGUAGE` and `PROJECT_ROOT`.
2. **Check language**: If `LANGUAGE` is not `javascript`, inform the user: "Dependency analysis is currently supported for JavaScript/TypeScript projects only."
3. **Load reference**: Read `<skill-dir>/references/madge.md` for CLI details.
4. **Detect TypeScript**: Check if `tsconfig.json` exists in `PROJECT_ROOT`. If so, add `--ts-config tsconfig.json` to all madge commands.
5. **Determine entry point**: Use the target path from the user's request. If none specified, use `src/` if it exists, otherwise `.`.
6. **Run circular dependency check**:
   ```bash
   # Without TypeScript:
   npx madge --circular --json [entry-point]

   # With TypeScript:
   npx madge --circular --json --ts-config tsconfig.json [entry-point]
   ```
7. **Parse JSON output**: The result is an array of cycles. Each cycle is an array of file paths where the last file imports the first.
   - Empty array `[]` = no circular dependencies
   - Non-empty = circular dependencies found (exit code 1 is expected)
8. **Optionally check orphans**: If the user asked about orphan modules, or as part of a comprehensive analysis:
   ```bash
   npx madge --orphans [entry-point]
   ```
   This outputs file paths to stdout (one per line, not JSON).
9. **Normalize severity**:
   - Circular dependency → **[CRT] CRITICAL** (can cause runtime crashes from Temporal Dead Zone errors, breaks tree-shaking, signals tight coupling)
   - Orphan module → **[INF] INFO** (dead code, not harmful but indicates unused files)
10. **Present findings**: Use the output format below.

### Example Output

```
## Dependency Analysis Report

**Tool**: madge | **Entry point**: src/ | **TypeScript**: yes

### Circular Dependencies — 2 cycles found [CRT]

**Cycle 1** (2 modules):
  src/orders/index.ts → src/orders/validate.ts → src/orders/index.ts

**Cycle 2** (3 modules):
  src/auth/session.ts → src/auth/tokens.ts → src/auth/refresh.ts → src/auth/session.ts

### Suggested Fixes

**Cycle 1**: `orders/validate.ts` imports from `orders/index.ts` — likely to access
a shared type or constant. Extract the shared dependency into a separate file
(e.g., `orders/types.ts`) that both can import without creating a cycle.

**Cycle 2**: This 3-module cycle suggests the auth module has tightly coupled
responsibilities. Consider extracting token refresh logic into a standalone
module that doesn't depend on session management.
```

### Clean Result

```
## Dependency Analysis Report

**Tool**: madge | **Entry point**: src/ | **TypeScript**: yes

No circular dependencies found. Module structure looks clean.
```

### Orphan Modules (when requested)

```
### Orphan Modules — 2 files [INF]

These files are not imported by any other module:
- src/utils/deprecated.ts
- src/helpers/old-format.ts

Consider removing them if they are unused, or adding imports if they were accidentally disconnected.
```

**Important**: Always provide actionable refactoring suggestions for circular dependencies. The fix is almost always to extract a shared dependency into a separate module. Do not suggest "just remove the import" without explaining where it should go instead.

## Output Format

### Summary Header

```
## Code Quality Report

**Tool**: ESLint | **Config**: eslint.config.js | **Files scanned**: 3

| Severity | Count |
|----------|-------|
| [CRT] CRITICAL | 2 |
| [MAJ] MAJOR | 5 |
| [MIN] MINOR | 3 |
| **Total** | **10** |
```

### Per-file Findings

```
### src/index.ts

| Line | Severity | Rule | Message |
|------|----------|------|---------|
| 10 | [CRT] | no-unused-vars | 'foo' is defined but never used |
| 25 | [MAJ] | eqeqeq | Expected '===' but found '==' |
| 42 | [MIN] | prefer-const | 'x' is never reassigned, use 'const' |
```

For MAJOR and above, add a brief explanation after the table:

```
**Line 10** (`no-unused-vars`): Unused variables indicate dead code. Remove `foo` or use it.
**Line 25** (`eqeqeq`): `==` performs type coercion which can cause subtle bugs. Use `===` for strict equality.
```

### Clean Result

```
## Code Quality Report

**Tool**: ESLint | **Config**: eslint.config.js | **Files scanned**: 3

No issues found. Code looks clean.
```

## Fix Strategy

1. **Prefer native auto-fix**: Always try the tool's `--fix` first. Tools handle line drift internally when fixing multiple issues in the same file.
2. **Re-analyze after fixing**: Always run the analysis command again after fixes to confirm the fix didn't introduce new issues.
3. **Safe vs unsafe fixes**: For ruff, `--fix` applies safe fixes only. Mention `--unsafe-fixes` if the user wants to apply all. For Biome, `--write` is safe, `--write --unsafe` is all.
4. **Manual fixes**: For issues without auto-fix, provide the specific code change (old → new) that the user can review before applying.
5. **Report clearly**: State what was fixed, what remains, and the severity of remaining issues.

## Error Handling

### Tool not installed

If the linter command fails with "command not found":
- **ruff**: `uvx ruff` runs without installation (requires `uv`). If `uv` is missing: `pip install ruff`
- **eslint**: `npm install --save-dev eslint` (the skill provides a default config, but ESLint itself must be available via `npx`)
- **biome**: `npm install --save-dev @biomejs/biome && npx @biomejs/biome init`

### Large output

If the linter returns more than 50 issues, truncate to the top 50 by severity and report:
> "Showing top 50 of N total issues. Run audit on specific files to see more."

### Parse errors / syntax errors

If the linter reports parsing errors (e.g., ESLint `ruleId: null` with "Parsing error"), report as BLOCKER severity. These must be fixed before other analysis is meaningful.

## Reference Files

Load these as needed based on the detected tool:

| File | When to load |
|------|-------------|
| `<skill-dir>/references/severity-map.md` | When issues are found — severity normalization |
| `<skill-dir>/references/eslint.md` | When TOOL=eslint — CLI flags, output schema, common rules |
| `<skill-dir>/references/biome.md` | When TOOL=biome — CLI flags, output schema, categories |
| `<skill-dir>/references/ruff.md` | When TOOL=ruff — CLI flags, output schema, rule prefixes |
| `<skill-dir>/references/madge.md` | Workflow F (dependency analysis) — CLI flags, output schema |
