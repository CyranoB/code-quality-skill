# Vulture Reference

Vulture finds unused code in Python — functions, classes, variables.

**Zero-install**: runs via `uvx vulture` — no permanent installation.

## CLI Usage

```bash
uvx vulture <path> --min-confidence 80
```

`--min-confidence 80` filters out the default 60% noise. The arch_review skill uses 80 to keep false positives down.

## Text output shape

```
src/myapp/orphan.py:42: unused function 'foo' (90% confidence)
src/myapp/old.py:5: unused variable 'X' (60% confidence)
```

Vulture has no JSON output. The arch_review wrapper parses the text with the regex:

```
^<file>:<line>:\s+<message>\s+\((<confidence>)% confidence\)\s*$
```

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | No issues found |
| 1 | Issues found (expected — parse output) |
| 2+ | Error |

## Caveats

- Vulture cannot see code referenced only via reflection (`getattr`, `__init_subclass__`, etc.). Treat findings as suggestions, not certainties.
- The arch_review skill maps ALL vulture findings to `[INF]` severity.
