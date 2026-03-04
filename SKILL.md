---
name: code-quality
description: >-
  Run code quality analysis, linting, and auto-fixes using project-native tools
  (ESLint, Biome, ruff). Use this skill whenever the user asks to "review code",
  "lint this file", "check code quality", "fix linting errors", "audit my project",
  "check before commit", "run static analysis", "find bugs", "clean up this code",
  or "pre-commit check". Also triggers when mentioning ESLint, ruff, Biome, or
  code quality issues like unused variables, type errors, or style violations.
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

**If TOOL=none**: Tell the user no supported linter was detected. Suggest installing one based on the project's language.

**If FALLBACK=true**: Inform the user that no explicit linter config was found and the tool is running with default settings. Suggest they create a config for customized rules.

**If TOOL=npm-script**: The project has a custom lint script but no recognized linter config for JSON output. Run the `COMMAND` (e.g., `npm run lint`) and parse the human-readable text output instead. Look for patterns like `file:line:col: message` or ESLint/Biome-style output. If the output is unstructured, present it verbatim and let the user interpret it.

**If TOOL=pylint**: Pylint has no auto-fix capability (`FIX_COMMAND` will be empty). Provide manual fix suggestions instead. Pylint's JSON output uses `message-id` (e.g., `C0114`) and `type` (`convention`, `refactor`, `warning`, `error`, `fatal`). Map these to the unified severity: `fatal` → BLOCKER, `error` → CRITICAL, `warning` → MAJOR, `refactor` → MINOR, `convention` → INFO.

After detection, load the matching reference file from `<skill-dir>/references/` for tool-specific guidance:
- `TOOL=eslint` → read `<skill-dir>/references/eslint.md`
- `TOOL=biome` → read `<skill-dir>/references/biome.md`
- `TOOL=ruff` → read `<skill-dir>/references/ruff.md`

Only load `<skill-dir>/references/severity-map.md` when the linter reports issues (not on clean results — saves tokens).

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

Offer follow-up actions: "I can fix the N auto-fixable issues, or drill into a specific file."

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

If the linter command fails with "command not found" or similar:
- **eslint**: `npm install --save-dev eslint` or `npx eslint --init`
- **biome**: `npm install --save-dev @biomejs/biome` and `npx @biomejs/biome init`
- **ruff**: `pip install ruff` or use `uvx ruff` (runs without install)

### No config file

If `FALLBACK=true`, inform the user:
> "No ESLint/Biome/ruff config found. Running with default rules. For customized analysis, create a config file."

Suggest init commands:
- **eslint**: `npx eslint --init` or create `eslint.config.js`
- **biome**: `npx @biomejs/biome init`
- **ruff**: Create `ruff.toml` or add `[tool.ruff]` to `pyproject.toml`

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
