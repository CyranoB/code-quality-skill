# Madge Reference

Madge creates dependency graphs from JS/TS modules and detects circular dependencies.

**JavaScript/TypeScript only.** For Python, see `pydeps.md`.

## CLI Usage

### Circular dependencies (primary use case)

```bash
npx madge --circular --json src/
npx madge --circular --json src/index.ts
npx madge --circular --json --ts-config tsconfig.json src/
```

### Orphan modules (not imported by anything)

```bash
npx madge --orphans src/
```

### Full dependency tree

```bash
npx madge --json src/
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0    | No circular dependencies found |
| 1    | Circular dependencies found (expected — parse output) |

**Important**: Exit code 1 is expected when circular deps exist. Do NOT treat it as a failure.

## JSON Output

### `--circular --json`

Returns an array of cycles. Each cycle is an array of file paths forming the loop (the last file imports the first):

```json
[
  ["src/a.ts", "src/b.ts"],
  ["src/orders/index.ts", "src/orders/validate.ts", "src/orders/pricing.ts"]
]
```

An empty array `[]` means no circular dependencies.

### `--json` (dependency tree)

Returns an object mapping each file to its direct dependencies:

```json
{
  "src/index.ts": ["src/app.ts", "src/config.ts"],
  "src/app.ts": ["src/routes.ts", "src/middleware.ts"],
  "src/config.ts": []
}
```

### `--orphans`

Outputs file paths to stdout (one per line, not JSON):

```
src/utils/deprecated.ts
src/helpers/old-format.ts
```

## TypeScript Support

For TypeScript projects, pass `--ts-config` to resolve path aliases and module resolution:

```bash
npx madge --circular --json --ts-config tsconfig.json src/
```

Without `--ts-config`, madge may miss dependencies that use path aliases (e.g., `@/components/...`).

**Auto-detection**: If `tsconfig.json` exists in the project root, always pass it.

## Common Options

| Flag | Purpose |
|------|---------|
| `--circular` | Find circular dependencies |
| `--orphans` | Find orphan modules |
| `--json` | JSON output (works with `--circular` and dependency tree) |
| `--ts-config <path>` | Path to tsconfig.json for TypeScript |
| `--webpack-config <path>` | Path to webpack config for aliases |
| `--extensions <ext,...>` | File extensions to scan (default: js,jsx,ts,tsx) |
| `--exclude <regex>` | Exclude files matching pattern |
| `--warning` | Show warnings about unresolvable dependencies |
| `--no-color` | Disable colored output |

## Tips

- `npx madge` works without installation — npx downloads it on the fly
- For monorepos, run from the package directory, not the workspace root
- Circular deps involving only type imports (`import type`) are usually safe at runtime but still indicate coupling — flag them as MAJOR instead of CRITICAL
- Use `--warning` during debugging to see which imports madge couldn't resolve
- `--exclude` is useful to skip generated files: `--exclude '(\.d\.ts|\.generated\.)'`
