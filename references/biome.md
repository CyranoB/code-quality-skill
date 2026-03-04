# Biome Reference

## CLI Usage

### Analyze (JSON output)

```bash
npx @biomejs/biome check --reporter=json [files...]
npx @biomejs/biome check --reporter=json src/
npx @biomejs/biome lint --reporter=json [files...]  # lint only, no formatting
```

### Auto-fix

```bash
npx @biomejs/biome check --write [files...]    # lint + format fixes
npx @biomejs/biome lint --write [files...]      # lint fixes only
```

### Lint only (no format checks)

```bash
npx @biomejs/biome lint --reporter=json [files...]
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0    | No issues |
| 1    | Issues found (normal — parse output) |
| 2    | Config/runtime error |

**Important**: Exit code 1 is expected when issues exist. Do NOT treat it as a failure.

## JSON Output Schema

Biome `--reporter=json` returns:

```json
{
  "diagnostics": [
    {
      "category": "lint/suspicious/noDoubleEquals",
      "severity": "error",
      "description": "Use === instead of ==",
      "message": [
        {
          "content": "Use ",
          "elements": []
        }
      ],
      "advices": {},
      "verboseAdvices": {},
      "location": {
        "path": {
          "file": "src/index.ts"
        },
        "span": [120, 135],
        "sourceCode": "if (a == b) {"
      },
      "tags": [],
      "source": null
    }
  ],
  "command": "check"
}
```

### Key fields

- `category`: Rule identifier (e.g., `lint/suspicious/noDoubleEquals`)
- `severity`: `"error"`, `"warning"`, `"information"`, `"hint"`
- `location.path.file`: Relative file path
- `location.sourceCode`: Source line containing the issue
- `location.span`: Byte offsets in file

### Extracting line numbers

Biome reports byte spans, not line numbers. To get line numbers from the output, look at `location.sourceCode` for context. When displaying results, if line numbers are unavailable, use the source code snippet instead.

Alternatively, use `--reporter=github` for line-number output (but less structured):
```bash
npx @biomejs/biome check --reporter=github [files...]
# Output: ::error file=src/index.ts,line=10,col=5::lint/suspicious/noDoubleEquals
```

## Config Files

- `biome.json` (primary)
- `biome.jsonc` (with comments)

### Minimal config example

```json
{
  "$schema": "https://biomejs.dev/schemas/1.9.0/schema.json",
  "linter": {
    "enabled": true,
    "rules": {
      "recommended": true
    }
  }
}
```

## Rule Categories

| Category | What it covers |
|----------|---------------|
| `lint/suspicious` | Likely bugs (noDoubleEquals, noExplicitAny) |
| `lint/correctness` | Definite errors (noUnusedVariables, noUnreachable) |
| `lint/style` | Code style (useConst, noVar) |
| `lint/complexity` | Unnecessary complexity (noForEach, useFlatMap) |
| `lint/a11y` | Accessibility (useAltText, useKeyWithClickEvents) |
| `lint/security` | Security issues (noDangerouslySetInnerHtml) |
| `lint/nursery` | Experimental rules |

## Common Rules

| Rule | Category | What it catches |
|------|----------|----------------|
| `noDoubleEquals` | suspicious | `==` instead of `===` |
| `noExplicitAny` | suspicious | TypeScript `any` type |
| `noUnusedVariables` | correctness | Unused variables |
| `noUnreachable` | correctness | Unreachable code |
| `useConst` | style | `let` for never-reassigned variables |
| `noVar` | style | `var` usage |
| `noConsoleLog` | suspicious | `console.log` in production code |

## Tips

- Biome is a single tool for both linting and formatting
- Use `lint` subcommand to skip format checks when only linting is needed
- Biome is significantly faster than ESLint for large codebases
- `--write` applies safe fixes; `--write --unsafe` applies all fixes
