# Pydeps Reference

Pydeps generates Python module dependency graphs and detects import cycles.

**Python only.** Runs via `uvx pydeps` — no installation needed. Graphviz is only required for graph visualization (SVG/PNG), NOT for cycle detection.

## CLI Usage

### Circular import detection (primary use case)

```bash
uvx pydeps cycles
uvx pydeps cycles --noshow
```

The `cycles` subcommand analyzes the current package and reports import cycles. Must be run from within a Python package directory (one containing `__init__.py` or `pyproject.toml`).

### Dependency analysis (text output)

```bash
uvx pydeps --show-deps --no-output --noshow <package-name>
```

`--show-deps` prints the dependency tree to stdout. `--no-output` prevents SVG file creation. `--noshow` prevents opening a viewer.

### External dependencies (JSON output)

```bash
uvx pydeps --externals <package-name>
```

Returns a JSON list of direct external dependencies:

```json
[
  "requests",
  "click",
  "pydantic"
]
```

### Full graph (requires Graphviz)

```bash
uvx pydeps <package-name>                        # SVG to stdout
uvx pydeps <package-name> -o deps.svg            # SVG to file
uvx pydeps <package-name> -T png -o deps.png     # PNG to file
```

## Cycle Detection Output

`pydeps cycles` outputs text to stdout. Each cycle is printed as a chain of module names:

```
Cycle: mypackage.orders -> mypackage.orders.validate -> mypackage.orders
Cycle: mypackage.auth.session -> mypackage.auth.tokens -> mypackage.auth.refresh -> mypackage.auth.session
```

**No JSON output** — Claude must parse the text directly. Look for lines starting with `Cycle:` and extract the module chain from the `->` separators.

If no cycles are found, there is no output (empty stdout).

## Common Options

| Flag | Purpose |
|------|---------|
| `cycles` | Subcommand to detect import cycles |
| `--show-deps` | Print dependency analysis to stdout |
| `--no-output` | Don't create SVG/PNG file |
| `--noshow` | Don't open external viewer |
| `--externals` | List direct external dependencies (JSON) |
| `-x PATTERN` | Exclude modules matching pattern |
| `-xx MODULE` | Exclude module and its dependencies |
| `--only MODULE` | Only include modules starting with path |
| `--max-bacon N` | Exclude nodes more than N hops away (default: 2, 0 = infinite) |
| `--max-module-depth N` | Coalesce deep modules to N levels |
| `--reverse` | Show reverse dependency graph |
| `-o FILE` | Write output to file |
| `-T FORMAT` | Output format: svg (default) or png |
| `-v` | Verbose mode (-vv, -vvv for more) |

## Package Detection

Pydeps needs a Python package to analyze. It looks for:
1. A directory with `__init__.py`
2. A `pyproject.toml` with package metadata
3. A `setup.py` or `setup.cfg`

For script-only projects (loose `.py` files without package structure), pydeps may not work. In this case, suggest the user organize code into a package, or use an alternative like `depcycle`:

```bash
uvx depcycle .
```

`depcycle` is a simpler tool that works on any directory of Python files without requiring package structure.

## Tips

- `uvx pydeps` works without installation — uvx handles everything
- `pydeps cycles` does NOT require Graphviz (no graph rendering needed)
- Full graph visualization (`pydeps <pkg>`) DOES require Graphviz: `brew install graphviz` (macOS), `apt install graphviz` (Ubuntu)
- Use `--max-bacon 0` to see the full dependency tree (default is 2 hops)
- Use `-x tests -x docs` to exclude test and docs directories
- Pydeps respects `.gitignore` patterns
