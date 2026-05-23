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

## Pyright

| Native Severity | Normalized |
|-----------------|------------|
| error           | CRITICAL   |
| warning         | MAJOR      |
| information     | MINOR      |

Pyright's `severity` field in JSON output maps directly. Type errors (`error`) are definite bugs — they indicate code that will fail at runtime or violates declared type contracts.

## TypeScript Compiler (tsc)

| Native Severity | Normalized |
|-----------------|------------|
| error           | CRITICAL   |
| warning         | MAJOR      |

tsc output lines contain `error TSxxxx` or (rarely) `warning TSxxxx`. Type errors are CRITICAL because they indicate code that won't compile or has type mismatches.

## Dependency Analysis (madge / depcycle)

| Finding | Normalized | Rationale |
|---------|------------|-----------|
| Circular dependency (JS/TS) | CRITICAL | Runtime TDZ crashes, breaks tree-shaking, signals tight coupling |
| Circular dependency (Python) | CRITICAL | `ImportError` at runtime, signals tight coupling between modules |
| Orphan module | INFO | Dead code — not harmful but indicates unused files |

## Cognitive Complexity

Cognitive complexity (Sonar-style; sources: `sonarjs/cognitive-complexity` for
JS/TS, `flake8-cognitive-complexity` CCR001 for Python) drives the severity for
complexity findings when measured. The threshold is 15 (matching SonarQube's
"Sonar way" default); above that, severity scales with the measured value:

| Measured cognitive | Normalized | Rationale |
|--------------------|------------|-----------|
| ≤ 15 | clean | At or below threshold — no finding emitted |
| 16 – 25 | MAJOR | Above threshold but still tractable to refactor |
| ≥ 26 | CRITICAL | High defect-density correlation; readability significantly impaired |

Cyclomatic complexity (`ruff C901`, ESLint core `complexity`) stays at MAJOR for
any reported violation — the tool itself only emits above the configured cap
(default 10). When both metrics are present on the same function, cognitive
drives the severity tag and cyclomatic appears as a secondary column.

The raw severity field set by the linter (e.g., ESLint `"warn"` → 1) is
**ignored** for these rules — what matters is the measured value, not the
configured severity level.

## Semgrep (Security Scan)

| Native Severity | Normalized | Rationale |
|-----------------|------------|-----------|
| ERROR           | BLOCKER    | Clear vulnerabilities (command injection, SQL injection, auth bypass) |
| WARNING         | CRITICAL   | Likely vulnerabilities (taint flows, dangerous APIs, weak crypto) |
| INFO            | MAJOR      | Security smells — worth attention but not always actionable |

Unknown severity strings fall back to MAJOR. Semgrep's `extra.metadata.cwe`
field is preserved verbatim in the finding (joined to a comma-separated string
if the source provides a list) so users can cross-reference with their threat
model.

## Secret Scanning (Security Scan)

| Finding | Normalized | Rationale |
|---------|------------|-----------|
| Any detect-secrets finding | BLOCKER | A committed credential is leaked regardless of plugin source — rotate the secret and remove from history |
| Any gitleaks finding (alternative tool) | BLOCKER | Same rationale |

There is no severity gradient: the secret either exists in the repo or it
doesn't. Users can suppress individual lines with `# pragma: allowlist secret`
(detect-secrets) or `# gitleaks:allow` (gitleaks) — see `references/secrets.md`
for the false-positive triage playbook.
