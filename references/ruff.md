# Ruff Reference

## CLI Usage

### Analyze (JSON output)

```bash
ruff check --output-format json [files...]
ruff check --output-format json src/
ruff check --output-format json .
```

If ruff is not installed locally, use `uvx` to run without install:
```bash
uvx ruff check --output-format json [files...]
```

### Auto-fix

```bash
ruff check --fix [files...]
ruff check --fix --unsafe-fixes [files...]  # include unsafe fixes
```

### Specific rules

```bash
ruff check --select E,W [files...]          # only pycodestyle
ruff check --select F [files...]             # only pyflakes
ruff check --extend-select I --fix [files...] # add isort and fix
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0    | No issues found |
| 1    | Lint issues found (normal — parse output) |
| 2    | Config/runtime error |

**Important**: Exit code 1 is expected when issues exist. Do NOT treat it as a failure.

## JSON Output Schema

`ruff check --output-format json` returns an array:

```json
[
  {
    "cell": null,
    "code": "F841",
    "end_location": {
      "column": 5,
      "row": 10
    },
    "filename": "/path/to/file.py",
    "fix": {
      "applicability": "safe",
      "edits": [
        {
          "content": "",
          "end_location": { "column": 0, "row": 11 },
          "location": { "column": 0, "row": 10 }
        }
      ],
      "message": "Remove assignment to unused variable `x`"
    },
    "location": {
      "column": 5,
      "row": 10
    },
    "message": "Local variable `x` is assigned to but never used",
    "noqa_row": 10,
    "url": "https://docs.astral.sh/ruff/rules/unused-variable"
  }
]
```

### Key fields

- `code`: Rule code (e.g., `F841`, `E501`)
- `message`: Human-readable description
- `filename`: Absolute file path
- `location.row`, `location.column`: 1-based start position
- `end_location`: End position of the issue
- `fix`: Present if auto-fixable
  - `applicability`: `"safe"` or `"unsafe"`
  - `message`: Description of the fix
- `url`: Link to rule documentation

## Config Files

Priority order:
1. `ruff.toml` (project root)
2. `.ruff.toml` (project root)
3. `pyproject.toml` under `[tool.ruff]` section

### Minimal `ruff.toml` example

```toml
line-length = 88
target-version = "py311"

[lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "SIM"]
```

## Rule Code Prefixes

| Prefix | Source | What it covers |
|--------|--------|---------------|
| F | Pyflakes | Undefined names, unused imports/vars |
| E | pycodestyle | Style errors (line length, whitespace) |
| W | pycodestyle | Style warnings |
| C90 | mccabe | Cyclomatic complexity |
| I | isort | Import sorting |
| N | pep8-naming | Naming conventions |
| D | pydocstyle | Docstring conventions |
| UP | pyupgrade | Python version upgrade suggestions |
| S | flake8-bandit | Security issues |
| B | flake8-bugbear | Likely bugs, design problems |
| A | flake8-builtins | Shadowing Python builtins |
| SIM | flake8-simplify | Simplifiable code patterns |
| T20 | flake8-print | Print statements |
| PT | flake8-pytest-style | Pytest best practices |
| RUF | Ruff-specific | Ruff's own rules |

## Common Rules

| Code | What it catches |
|------|----------------|
| F401 | Unused import |
| F841 | Unused variable |
| E501 | Line too long |
| E711 | Comparison to None (use `is`) |
| E712 | Comparison to True/False |
| W291 | Trailing whitespace |
| I001 | Import not sorted |
| B006 | Mutable default argument |
| B007 | Unused loop variable |
| S101 | Use of `assert` (security) |
| UP035 | Deprecated import |
| SIM108 | Use ternary instead of if/else |

## Tips

- Ruff is written in Rust and is 10-100x faster than flake8/pylint
- `--fix` only applies safe fixes by default; `--unsafe-fixes` for all
- `--statistics` shows a count of issues by rule code
- Ruff respects `.gitignore` by default
- Use `ruff rule F841` to get detailed info on a specific rule
- `uvx ruff` runs the latest version without installation
