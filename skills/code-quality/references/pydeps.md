# Python Dependency Analysis Reference

## Primary Tool: depcycle

`depcycle` detects circular dependencies in Python projects. It works on any directory of Python files — no package structure required.

**Zero install**: Runs via `uvx depcycle` — no pip install needed.

### CLI Usage

```bash
uvx depcycle <path>
uvx depcycle src/mypackage
uvx depcycle .
```

### Output

**Clean result**:
```
Analyzing project: src/web_forager
Building dependency graph...
Found 28 modules
✓ No circular dependencies detected
```

**Circular dependencies found**:
```
Analyzing project: src/mypackage
Building dependency graph...
Found 15 modules
✗ Circular dependencies detected:

  mypackage.orders -> mypackage.orders.validate -> mypackage.orders
  mypackage.auth.session -> mypackage.auth.tokens -> mypackage.auth.session
```

Parse the text output: look for lines with `->` chains showing the cycle. The `✓` / `✗` prefix indicates clean vs. findings.

**Note**: depcycle also generates a `dependencies.png` visualization file in the current directory. This is a side effect — the text output is what the skill uses.

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | No circular dependencies |
| 1 | Circular dependencies found (expected — parse output) |

## Secondary Tool: pydeps

Pydeps is a graph visualization tool for Python module dependencies. It is primarily useful for generating SVG/PNG dependency graphs, NOT for cycle detection.

**Use pydeps when**: The user asks for a dependency graph/visualization, not just cycle detection.

**Requires**: Graphviz for graph output (`brew install graphviz` on macOS).

### CLI Usage

```bash
# External dependencies (JSON output — no Graphviz needed)
uvx pydeps --externals <package-path>

# Dependency graph (requires Graphviz)
uvx pydeps <package-path>                    # SVG to stdout
uvx pydeps <package-path> -o deps.svg        # SVG to file
uvx pydeps <package-path> -T png -o deps.png # PNG to file

# Suppress viewer
uvx pydeps <package-path> --noshow -o deps.svg
```

### Common Options

| Flag | Purpose |
|------|---------|
| `--externals` | List direct external dependencies (JSON output) |
| `--no-output` | Don't create SVG/PNG file |
| `--noshow` | Don't open external viewer |
| `--show-deps` | Print dependency analysis to stdout |
| `-x PATTERN` | Exclude modules matching pattern |
| `-xx MODULE` | Exclude module and its dependencies |
| `--only MODULE` | Only include modules starting with path |
| `--max-bacon N` | Max hops from entry (default: 2, 0 = infinite) |
| `--reverse` | Show reverse dependency graph |
| `-o FILE` | Write output to file |
| `-T FORMAT` | Output format: svg (default) or png |

## Tips

- **Always prefer depcycle for cycle detection** — it's simpler, faster, and gives clear text output
- depcycle works on any directory; pydeps needs a proper Python package (with `__init__.py`)
- Both tools run via `uvx` with zero installation
- `pydeps --externals` is useful for auditing third-party dependencies (JSON output)
