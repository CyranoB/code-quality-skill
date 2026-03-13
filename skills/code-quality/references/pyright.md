# Pyright Reference

## CLI Usage

### Type Check (JSON output)

```bash
npx pyright --outputjson [files-or-directory]
npx pyright --outputjson src/
npx pyright --outputjson .
```

Zero install: pyright runs via `npx` without local installation.

### Specific files

```bash
npx pyright --outputjson src/main.py src/utils.py
```

### With config

Pyright reads `pyrightconfig.json` or `[tool.pyright]` in `pyproject.toml` automatically.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0    | No type errors found |
| 1    | Type errors found (normal — parse JSON output) |

**Important**: Exit code 1 is expected when errors exist. Do NOT treat it as a failure.

## JSON Output Schema

`pyright --outputjson` returns:

```json
{
  "version": "1.1.xxx",
  "time": "0.5sec",
  "generalDiagnostics": [
    {
      "file": "/path/to/file.py",
      "severity": "error",
      "message": "Cannot access attribute \"total\" for class \"Order\"",
      "range": {
        "start": {"line": 22, "character": 4},
        "end": {"line": 22, "character": 15}
      },
      "rule": "reportAttributeAccessIssue"
    }
  ],
  "summary": {
    "filesAnalyzed": 15,
    "errorCount": 3,
    "warningCount": 1,
    "informationCount": 0,
    "timeInSec": 0.5
  }
}
```

### Key fields

- `generalDiagnostics[]`: Array of diagnostic findings
  - `file`: Absolute file path
  - `severity`: `"error"`, `"warning"`, or `"information"`
  - `message`: Human-readable description
  - `range.start.line`: **0-based** line number (add 1 for display)
  - `range.start.character`: 0-based column
  - `rule`: Pyright rule name (e.g., `reportMissingImports`, `reportAttributeAccessIssue`)
- `summary`: Aggregate counts and timing
  - `filesAnalyzed`: Number of files checked
  - `errorCount`, `warningCount`, `informationCount`: Totals by severity

### Important notes

- Line numbers in pyright JSON are **0-based**. Add 1 when displaying to users.
- `rule` field may be absent for some diagnostics (e.g., syntax errors).
- pyright analyzes the entire project by default. To scope to specific files, pass them as arguments.
- When targeting specific files, pyright still needs to resolve imports — it may analyze more files than specified.

## Severity Mapping

| Pyright Severity | Normalized |
|-----------------|------------|
| error           | CRITICAL   |
| warning         | MAJOR      |
| information     | MINOR      |

## Common Rules

| Rule | What it catches |
|------|----------------|
| reportMissingImports | Import that can't be resolved |
| reportMissingModuleSource | Module found but source not available |
| reportAttributeAccessIssue | Attribute doesn't exist on type |
| reportIndexIssue | Invalid index operation on type |
| reportArgumentType | Wrong argument type in function call |
| reportReturnType | Return value doesn't match declared type |
| reportAssignmentType | Assignment value doesn't match variable type |
| reportGeneralClassIssue | Class-level type issues |
| reportOptionalMemberAccess | Accessing attribute on Optional without None check |
| reportOptionalSubscript | Subscripting Optional without None check |
| reportUnusedImport | Imported but unused (overlaps with ruff F401) |
| reportUnusedVariable | Variable assigned but unused (overlaps with ruff F841) |
| reportMissingTypeStubs | Type stubs not available for third-party package |
| reportCallIssue | Invalid function call (wrong arg count, types) |

## Config Files

Priority order:
1. `pyrightconfig.json` (project root)
2. `pyproject.toml` under `[tool.pyright]` section

### Minimal `pyrightconfig.json`

```json
{
  "include": ["src"],
  "reportMissingImports": true,
  "reportMissingTypeStubs": false,
  "pythonVersion": "3.11"
}
```

### In `pyproject.toml`

```toml
[tool.pyright]
include = ["src"]
reportMissingImports = true
reportMissingTypeStubs = false
pythonVersion = "3.11"
```

## Tips

- `npx pyright` runs the latest version without installation
- Pyright is significantly faster than mypy
- Use `--pythonversion 3.11` CLI flag to override Python version detection
- `reportMissingTypeStubs = false` silences noise from untyped third-party packages
- Pyright respects `py.typed` marker files in packages
- For projects without type annotations, pyright still catches obvious errors (undefined names, wrong argument counts, attribute access on wrong types)
- Use `--level basic` for fewer, higher-confidence diagnostics (skips strict-mode rules)
