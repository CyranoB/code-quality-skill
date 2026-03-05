# Severity Normalization Map

Normalize tool-native severity levels to a unified 5-tier system for consistent reporting.

## Unified Severity Levels

| Tag   | Level    | Meaning                                    |
|-------|----------|--------------------------------------------|
| `[BLK]` | BLOCKER  | Crashes, data loss, security vulnerabilities |
| `[CRT]` | CRITICAL | Definite bugs, logic errors                 |
| `[MAJ]` | MAJOR    | Likely bugs, bad practices                  |
| `[MIN]` | MINOR    | Style issues, conventions                   |
| `[INF]` | INFO     | Suggestions, formatting                     |

## ESLint

| Native Severity | Value | Normalized |
|-----------------|-------|------------|
| error           | 2     | CRITICAL   |
| warning         | 1     | MAJOR      |

ESLint has only two levels. Map `error` → CRITICAL, `warning` → MAJOR.

The `complexity` rule follows normal ESLint mapping: configured as `"error"` → CRITICAL, configured as `"warn"` → MAJOR.

## Biome

| Native Severity | Normalized |
|-----------------|------------|
| error           | CRITICAL   |
| warning         | MAJOR      |
| information     | MINOR      |
| hint            | INFO       |

## Ruff

Map by rule code prefix:

| Prefix | Category         | Normalized |
|--------|------------------|------------|
| F      | Pyflakes         | CRITICAL   |
| E      | pycodestyle error| CRITICAL   |
| W      | pycodestyle warn | MAJOR      |
| C901   | mccabe complexity| MAJOR      | ← specific override; takes precedence over generic C
| C      | Convention       | MINOR      |
| I      | isort            | INFO       |
| N      | pep8-naming      | MINOR      |
| D      | pydocstyle       | INFO       |
| UP     | pyupgrade        | MINOR      |
| S      | flake8-bandit    | CRITICAL   |
| B      | flake8-bugbear   | MAJOR      |
| A      | flake8-builtins  | MAJOR      |
| SIM    | flake8-simplify  | MINOR      |
| T      | flake8-print     | MINOR      |
| PT     | flake8-pytest    | MINOR      |
| RUF    | Ruff-specific    | MAJOR      |

For prefixes not listed, default to MAJOR.

## Pylint

| Native Type | Normalized |
|-------------|------------|
| fatal       | BLOCKER    |
| error       | CRITICAL   |
| warning     | MAJOR      |
| refactor    | MINOR      |
| convention  | INFO       |

Pylint uses `type` field in JSON output: `"fatal"`, `"error"`, `"warning"`, `"refactor"`, `"convention"`.

## Display Format

When presenting findings, use the tag prefix:

```
[CRT] src/index.ts:42 no-unused-vars — 'foo' is defined but never used
[MAJ] src/index.ts:58 eqeqeq — Expected '===' but found '=='
[MIN] src/utils.ts:12 prefer-const — 'x' is never reassigned, use 'const'
```

Group findings by severity (BLOCKER first), then by file, then by line number.

## Madge (Dependency Analysis)

| Finding | Normalized | Rationale |
|---------|------------|-----------|
| Circular dependency | CRITICAL | Can cause runtime crashes (TDZ errors), breaks tree-shaking, signals tight coupling |
| Orphan module | INFO | Dead code — not harmful but indicates unused files |
