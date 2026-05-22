# Knip Reference

Knip finds unused files, exports, dependencies, and types in JavaScript/TypeScript projects.

**Zero-install**: runs via `npx --yes knip` — no permanent installation.

## CLI Usage

```bash
npx --yes knip --reporter json
```

Run from the project root containing `package.json`.

## JSON output shape

```json
{
  "files": ["src/unused.ts"],
  "dependencies": {},
  "exports": {
    "src/a.ts": [
      { "name": "foo", "line": 10 },
      { "name": "bar", "line": 12 }
    ]
  }
}
```

The arch_review wrapper parses `files` (unused files) and `exports` (unused named exports).

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | No issues found |
| 1 | Issues found (expected — parse output) |
| 2+ | Error |

## Caveats

- Without a config, knip uses sensible defaults. False positives are possible for dynamic imports, runtime registration patterns, and re-export chains. For this reason, the arch_review skill maps ALL knip findings to `[INF]` severity.
- `npx --yes` is important — without it, npx prompts interactively in some terminals.
