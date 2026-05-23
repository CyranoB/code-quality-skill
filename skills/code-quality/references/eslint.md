# ESLint Reference

## CLI Usage

### Analyze (JSON output)

```bash
npx eslint --format json [files...]
npx eslint --format json src/
npx eslint --format json "src/**/*.ts"
```

### Auto-fix

```bash
npx eslint --fix [files...]
npx eslint --fix src/
```

### Specific rules only

```bash
npx eslint --rule '{"no-unused-vars": "error"}' [files...]
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0    | No issues found |
| 1    | Lint issues found (normal — parse output) |
| 2    | Config error or crash (report to user) |

**Important**: Exit code 1 is expected when issues exist. Do NOT treat it as a failure.

## JSON Output Schema

ESLint `--format json` returns an array of file results:

```json
[
  {
    "filePath": "/absolute/path/to/file.ts",
    "messages": [
      {
        "ruleId": "no-unused-vars",
        "severity": 2,
        "message": "'foo' is assigned a value but never used.",
        "line": 10,
        "column": 7,
        "nodeType": "Identifier",
        "endLine": 10,
        "endColumn": 10,
        "fix": {
          "range": [120, 135],
          "text": ""
        }
      }
    ],
    "errorCount": 1,
    "warningCount": 0,
    "fixableErrorCount": 0,
    "fixableWarningCount": 0
  }
]
```

### Key fields

- `severity`: 1 = warning, 2 = error
- `ruleId`: Rule identifier (may be null for parsing errors)
- `line`, `column`: 1-based location
- `fix`: Present if auto-fixable (has `range` and replacement `text`)
- `errorCount`, `warningCount`: Per-file summary

## Config Detection

### Flat config (ESLint 9+, recommended)
- `eslint.config.js` / `eslint.config.mjs` / `eslint.config.cjs`
- Exports an array of config objects

### Legacy config
- `.eslintrc.js` / `.eslintrc.cjs` / `.eslintrc.json` / `.eslintrc.yml` / `.eslintrc.yaml`
- `.eslintrc` (deprecated)
- `package.json` `"eslintConfig"` key

### Ignore files
- `.eslintignore` (legacy)
- Flat config uses `ignores` array in config

## Common Rules

| Rule | Severity | What it catches |
|------|----------|----------------|
| `no-unused-vars` | error | Variables declared but never used |
| `no-undef` | error | References to undeclared variables |
| `eqeqeq` | warning | `==` instead of `===` |
| `no-console` | warning | `console.log` left in code |
| `prefer-const` | warning | `let` when value is never reassigned |
| `no-var` | warning | `var` instead of `let`/`const` |
| `no-empty` | warning | Empty block statements |
| `no-debugger` | error | `debugger` statements |
| `no-duplicate-case` | error | Duplicate case labels in switch |
| `no-unreachable` | error | Code after return/throw/break |

## TypeScript-specific

When `@typescript-eslint` is installed:

| Rule | What it catches |
|------|----------------|
| `@typescript-eslint/no-unused-vars` | Unused vars (TS-aware) |
| `@typescript-eslint/no-explicit-any` | `any` type usage |
| `@typescript-eslint/no-non-null-assertion` | `!` assertions |
| `@typescript-eslint/consistent-type-imports` | Import type consistency |

## Parsing Errors

If `ruleId` is `null` and the message starts with "Parsing error:", the file has a syntax error. Report these as BLOCKER severity — they prevent all other analysis.

## Cyclomatic Complexity

ESLint's built-in `complexity` rule reports functions exceeding a max branch count.

**Not enabled by default** — must be configured:

```js
// eslint.config.js
rules: { "complexity": ["warn", 10] }   // warn at 10 (ESLint default)
rules: { "complexity": ["error", 15] }  // error at 15
```

**JSON output** (from `--format json`):

```json
{
  "ruleId": "complexity",
  "severity": 1,
  "message": "Function 'processOrder' has a complexity of 18. Maximum allowed is 10.",
  "line": 42,
  "column": 1
}
```

**Thresholds**: 1–10 simple, 11–20 moderate, 21+ high risk. ESLint default max is 10.

**Severity mapping**: Apply normal ESLint mapping — `error` (severity 2) → CRITICAL, `warning` (severity 1) → MAJOR.

## Tips

- Use `--no-warn-ignored` to suppress warnings about ignored files (ESLint 9+)
- Use `--max-warnings 0` to treat warnings as errors
- For monorepos, run from the package directory, not the root
- ESLint respects `.gitignore` by default in flat config mode

## Running with skill defaults & bundled plugins

Workflows that need rules from `eslint-plugin-sonarjs` (Lint complexity checks
and Architecture Review `complex_functions`) invoke ESLint via the bundled
wrapper, **not** plain `npx eslint`:

```bash
bash <skill-dir>/scripts/eslint-defaults.sh \
  --no-config-lookup \
  --config <skill-dir>/defaults/eslint.config.js \
  --rule '{"sonarjs/cognitive-complexity":["warn",15]}' \
  --format json <files>
```

`detect-linter.sh` emits this command shape ready-to-use as
`COGNITIVE_COMMAND` (JS/TS) and the wrapper path as `ESLINT_DEFAULTS_CMD`.

### Why a wrapper instead of `npx --prefix`

`npx --prefix DIR pkg` does **not** install devDependencies declared in
`DIR/package.json`. To make the bundled plugins resolvable, the skill needs an
explicit `npm ci --prefix DIR` first. The wrapper at
`scripts/eslint-defaults.sh` handles this:

1. Check whether `defaults/node_modules/.bin/eslint` exists
2. If not, run `npm ci --prefix defaults/` (falls back to `npm install` when
   there's no lockfile)
3. Exec `defaults/node_modules/.bin/eslint "$@"`

First-run cost: ~10–20s and ~30MB into `defaults/node_modules` (gitignored).
Subsequent calls are instant.

### Scope: complexity checks only

The bundled ESLint is **not** the general JS/TS fallback. Lint's regular
JS/TS pass keeps using the project linter or Biome fallback (faster, native TS,
no parser plugins needed). The bundled wrapper is used for explicit complexity
passes so cognitive complexity and curated sonarjs code-smell rules can run
without requiring the target project to install sonarjs.

If the user wants sonarjs rules during normal linting, they should install
`eslint-plugin-sonarjs` in their own project's `package.json` — the project's
ESLint config will pick it up via Lint's normal detection path.

### Flat-config `cwd` requirement

ESLint flat config silently ignores files "outside the base path" of the
current working directory. Always invoke the wrapper with `cwd` set to (or
under) the project being analyzed:

```bash
cd /path/to/project
bash <skill-dir>/scripts/eslint-defaults.sh --config <skill-dir>/defaults/eslint.config.js src/index.ts
```

Workflows that consume `COGNITIVE_COMMAND` from `detect-linter.sh` already do
this; users wiring the wrapper into custom scripts should be aware.
