# Semgrep Reference (Workflow J)

Semgrep is the cross-language SAST engine powering Workflow J's security scan.
It supports JS/TS, Python, Go, Java, Ruby, PHP, C, C#, Rust, and ~20 more, with
a community ruleset of ~2000+ rules covering OWASP Top 10, CWE Top 25, and
language-specific dangerous patterns.

The skill invokes Semgrep via `uvx` so the user needs no local install — only
`uv`. First run downloads the ruleset (~few MB, cached afterward).

## Default invocation

```bash
uvx --from semgrep semgrep scan \
  --config p/security-audit \
  --json --quiet --metrics=off \
  --error \
  --exclude node_modules --exclude .git --exclude dist \
  <project-root>
```

Notes:
- `--metrics=off` keeps privacy (no telemetry to r2c). Without this, Semgrep
  pings telemetry; with it, the `auto` config is unavailable (use a named
  pack instead).
- `--error` makes exit code 1 mean "findings emitted" so the runner can
  distinguish that from a runtime error (exit 2+).
- `--exclude` is repeatable. The skill defaults to a wide set; users can add
  more via `security-scan.sh --exclude <pattern>`.

## Config registry — what to point `--config` at

| Pack | Coverage | Speed | When to use |
|------|----------|-------|-------------|
| `p/security-audit` (default) | Cross-language SAST, ~600 rules, OWASP/CWE | medium | Most projects, broad first scan |
| `p/owasp-top-ten` | OWASP A01–A10 specifically | fast | Compliance-focused review |
| `p/cwe-top-25` | MITRE CWE Top 25 | fast | Comparison with security-tracker data |
| `p/python` | Python-only rules (broader than security-audit's Python subset) | medium | Python-only project, want depth |
| `p/javascript` | JS-specific patterns | medium | JS-only project, want depth |
| `p/r2c-ci` | Curated low-false-positive set | fast | Pre-commit / CI gate |
| `p/default` | Maintainer-curated mixed pack | medium | Broad scan, balanced |

Pass via `--semgrep-config p/owasp-top-ten` to `security-scan.sh`.

Multiple configs can be combined by repeating `--config`. The skill exposes
only the single-config form by default; for combined scans, drive Semgrep
directly.

## JSON output schema

Each entry in `results[]` has:

```json
{
  "check_id": "python.lang.security.audit.subprocess-shell-true.subprocess-shell-true",
  "path": "/abs/project/src/runner.py",
  "start": {"line": 12, "col": 5},
  "end":   {"line": 12, "col": 60},
  "extra": {
    "message": "Subprocess invocation with shell=True. ...",
    "severity": "ERROR",
    "metadata": {
      "cwe": ["CWE-78: ..."],
      "owasp": ["A03:2021 - Injection"],
      "category": "security"
    }
  }
}
```

`extra.severity` values are `ERROR`, `WARNING`, or `INFO`. The skill
normalizes them to BLK / CRT / MAJ (see `references/severity-map.md`).

After normalization, the skill emits each finding as:

```json
{
  "file": "/abs/project/src/runner.py",
  "line": 12,
  "rule_id": "python.lang.security.audit.subprocess-shell-true.subprocess-shell-true",
  "message": "Subprocess invocation with shell=True. ...",
  "raw_severity": "ERROR",
  "severity": "BLK",
  "cwe": "CWE-78: ..."
}
```

Severity mapping: `ERROR` → BLK, `WARNING` → CRT, `INFO` → MAJ. Unknown
severities fall back to MAJ.

## Suppression and false positives

Per-line, the literal directive is `// nosemgrep` (or `# nosemgrep` in
Python). Append the rule id for a scoped suppression:

```
// nosemgrep
// nosemgrep: javascript.lang.security.audit.xss.direct-response-write
```

Per-rule across the project: pass `--exclude-rule <rule_id>` (Semgrep CLI flag,
not yet exposed by `security-scan.sh` — drive Semgrep directly for one-off
exclusions).

Per-file across the project: extend the skill's default exclude set via
`security-scan.sh --exclude <glob>`. Useful for vendored code, generated
files, or known-safe wrappers.

## Default exclude set (shared with detect-secrets)

The skill applies these to every Workflow J run, in addition to anything you
pass via `--exclude`:

- `.git`, `node_modules`, `dist`, `build`
- `venv`, `.venv`, `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`
- `*.min.js`, `*.map`
- `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `poetry.lock`
- `*.snap`

These live in `security_scan/runner.py:DEFAULT_EXCLUDE_GLOBS`.
Semgrep additionally respects `.gitignore` by default.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Clean — no findings, no errors |
| 1 | Findings emitted (with `--error`) |
| 2 | Runtime error (bad config, parse failure, ruleset download failure) |
| 3+ | Internal Semgrep error |

The skill treats exit code > 1 as a runtime error and emits
`{"status": "error", "reason": "..."}` for that section. Findings still render
for any sub-tools that succeeded.

## Truncation

If a project produces > 200 findings in a single scan, the runner sorts by
severity-then-file and keeps the top 200, setting `"truncated": true` on the
section. The full count appears in the section summary so the user knows to
re-run with `--severity ERROR` (Semgrep flag, narrow to high-severity) or to
target specific paths.

## When to use Semgrep vs ESLint security plugins

The skill deliberately ships **no** ESLint security plugins
(`eslint-plugin-security` is intentionally NOT in `defaults/package.json`).
Semgrep covers the same JS/TS security ground with deeper taint-flow analysis,
plus all other languages. Two security engines is noise; one is signal.

If you specifically want ESLint-formatted security findings for a tight
pre-commit loop on JS-only code, install `eslint-plugin-security` in your
project — Workflow A/C/D will pick it up via your project's own ESLint config
without the skill bundling it.
