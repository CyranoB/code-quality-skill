# Cognitive Complexity Reference

Cognitive complexity is Sonar's metric for how hard a function is to *read*,
not just how many execution paths it has. Where cyclomatic counts independent
paths (each `if`, `case`, `for` +1), cognitive applies graduated penalties for
nesting and control-flow disruptions:

- **Nesting** — each level of nesting inside an existing control structure
  adds an extra increment on top of the base +1.
- **Sequence breaks** — `break`, `continue`, `goto`, recursion, and ternaries
  embedded in expressions all add cost because they fragment the reader's
  mental model of linear flow.
- **Sequential `if/else`** — penalized once for the chain, not once per branch.
  A `switch` with 20 cases scores low on cognitive even though cyclomatic
  reports 20.

This is why a function with deeply nested `if`s often has *higher* cognitive
than cyclomatic, while a flat `switch` has the inverse. The two metrics tell
different stories; Lint and Architecture Review report both.

## Severity thresholds

| Measured cognitive | Severity | Action |
|--------------------|----------|--------|
| ≤ 15 | clean | No finding emitted |
| 16 – 25 | **[MAJ] MAJOR** | Refactor when you next touch the function |
| ≥ 26 | **[CRT] CRITICAL** | High defect-density correlation — refactor before adding features |

The 15 threshold matches SonarQube's "Sonar way" default. See
`references/severity-map.md` for the full table.

## Tools the skill drives

### JavaScript / TypeScript — `eslint-plugin-sonarjs`

SonarSource's official ESLint port. Bundled in the skill's
`defaults/package.json` and invoked through `scripts/eslint-defaults.sh`.

```bash
bash skills/code-quality/scripts/eslint-defaults.sh \
  --no-config-lookup \
  --config skills/code-quality/defaults/eslint.config.js \
  --rule '{"sonarjs/cognitive-complexity":["warn",15]}' \
  --format json <files>
```

**Rule message format**: `Refactor this function to reduce its Cognitive
Complexity from X to the Y allowed.` The rule message does **not** include the
function name — the skill's merger pairs it with the cyclomatic finding (which
does include the name) by `(file, line ±2)`.

**ESLint flat-config caveat**: invoke from the project root (cwd), not from the
skill defaults directory. ESLint silently ignores files "outside the base
path" of the cwd. Workflows that consume `ESLINT_DEFAULTS_CMD` from
`detect-linter.sh` should `cd` into the project before running.

### Python — `flake8-cognitive-complexity` (CCR001) via `uvx --with`

```bash
uvx --with flake8-cognitive-complexity flake8 \
  --select=CCR001 --max-cognitive-complexity=15 <files>
```

**Output format** (text, not JSON):
```
src/orders.py:23:1: CCR001 Cognitive complexity is too high (28 > 15)
```

The skill parses this with the regex
`^(?P<file>[^:]+):(?P<line>\d+):\d+:\s+CCR001\s+.*?\((?P<cc>\d+)\s*>\s*(?P<max>\d+)\)\s*$`.
Function name is not in the message; comes from the matched cyclomatic finding
where possible.

**Why flake8 not ruff**: ruff doesn't yet ship a cognitive complexity rule
(only cyclomatic via C901). The flake8 plugin is the standard Python source.
The skill uses `uvx --with` so neither flake8 nor the plugin needs a permanent
install.

## Refactoring patterns that reduce cognitive

Listed roughly by impact. The skill's report suggests these when reporting a
finding.

### 1. Early returns (guard clauses)

```python
# Cognitive: high (deep nesting)
def classify(user):
    if user is not None:
        if user.active:
            if user.role == 'admin':
                return 'admin'
            else:
                return 'user'
    return 'anon'

# Cognitive: low (flat with early exits)
def classify(user):
    if user is None or not user.active:
        return 'anon'
    return 'admin' if user.role == 'admin' else 'user'
```

Every level of nesting collapsed adds a multiplicative reduction (level-2
nesting costs 2 vs level-1's 1).

### 2. Extract method

When the inner body of a loop or conditional grows past a few statements, lift
it to a named function. Cognitive resets at each function boundary, so
extracting a 15-cognitive inner block into its own function leaves the outer
function with ~0 contributed from that branch.

### 3. Replace nested conditionals with table dispatch

```python
# Cognitive: ~12 (nested chain)
if kind == 'a':
    if priority > 5:
        return high_a(x)
    return low_a(x)
elif kind == 'b':
    if priority > 5:
        return high_b(x)
    return low_b(x)
# ...

# Cognitive: ~2 (lookup)
HANDLERS = {
    ('a', True): high_a, ('a', False): low_a,
    ('b', True): high_b, ('b', False): low_b,
}
return HANDLERS[(kind, priority > 5)](x)
```

### 4. Polymorphism

For long `switch`/`elif` chains where each branch has substantial body, prefer
polymorphism (or a strategy dict mapping discriminator → handler). Each handler
gets its own cognitive budget rather than competing inside one function.

### 5. Avoid ternary chaining

`a if cond1 else (b if cond2 else c)` reads worse than a sequence of `if`s with
early returns. Cognitive penalizes nested ternaries explicitly.

## Anti-patterns the skill flags hardest

- Nested `try`/`except` blocks (each adds nesting and a sequence break)
- Loops containing conditionals containing loops (every extra level multiplies)
- Functions with both `return` and side-effects scattered across branches
- Long if/elif chains over discriminator strings (table dispatch is almost
  always better)
