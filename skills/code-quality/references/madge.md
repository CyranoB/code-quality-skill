# Madge Reference

Madge creates dependency graphs from JS/TS modules and detects circular dependencies.

**JavaScript/TypeScript only.** For Python, see `pydeps.md`.

## CLI Usage

### Circular dependencies (primary use case)

```bash
# JavaScript (directory works):
npx madge --circular --json src/

# TypeScript (use file entry point + --extensions):
npx madge --circular --json --ts-config tsconfig.json --extensions ts,tsx src/index.ts
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
- **For TypeScript projects with a clear entry**: Use a file entry point (e.g., `src/server.ts`, `src/index.ts`) instead of a directory. Madge with `--ts-config` resolves from entry points — passing `src/` alone may find 0 files. Also add `--extensions ts,tsx` so TypeScript files are included.
- **For Next.js / Remix / SvelteKit / Astro**: there is no single entry file — the framework handles routing. Pass the source directory instead (`app/` for Next.js App Router, `pages/` for Next.js Pages Router, `src/` for Vite-based frameworks). Keep `--ts-config tsconfig.json --extensions ts,tsx` if the project is TypeScript.
- **Multi-root projects**: scan top-level source dirs (`app/`, `components/`, `lib/`) separately if they aren't all reached from one entry, otherwise isolated cycles get missed.
- **Verify your entry**: `npx madge --json <entry> | jq 'length'` shows how many files were resolved. 0 or unexpectedly low means the entry is wrong.
- For monorepos, run from the package directory, not the workspace root.
- Circular deps involving only type imports (`import type`) are usually safe at runtime but still indicate coupling — flag them as MAJOR instead of CRITICAL.
- Use `--warning` during debugging to see which imports madge couldn't resolve.
- `--exclude` is useful to skip generated files: `--exclude '(\.d\.ts|\.generated\.)'`.

## Troubleshooting

**`npm error Missing script: "madge"` and `Unknown cli config "--circular"` warnings.**
The `npx` invocation is being intercepted — typically by a shell alias, a Claude Code PreToolUse hook, or an RTK-style proxy that rewrites `npx <pkg>` into `npm run <pkg>`. The error comes from npm, not madge. Don't conclude madge is missing.

Bypass:
```bash
command npx madge --version          # confirms madge actually runs
command npx madge --circular --json --ts-config tsconfig.json --extensions ts,tsx app/
```
`command npx` skips aliases and most pre-tool-use rewriters. `$(which npx) madge ...` works too.

**`No files found` or 0-length output.** Wrong entry point. For framework projects, pass a directory instead of a file (see Tips above). Run `npx madge --json <entry> | jq 'length'` to confirm files were resolved.

**Path-alias imports unresolved (`@/components/...` shown as warnings).** Pass `--ts-config tsconfig.json` explicitly. Without it madge can't read `compilerOptions.paths`.
