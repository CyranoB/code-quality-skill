# Secret Scanning Reference (Workflow J)

Workflow J's secret-scanning sub-tool finds committed credentials — API keys,
tokens, private keys, passwords, high-entropy strings — that should never have
made it into source control.

The skill's primary tool is **detect-secrets** (Yelp), invoked via `uvx` for
zero-install. **gitleaks** is documented here as an alternative for users who
already have it installed.

## Why secrets are always BLOCKER

Severity for any secret-scan finding is **BLOCKER**, regardless of plugin
source or entropy score. Rationale: a credential committed to git history is
leaked the moment it's pushed, even if removed later (history is queryable;
forks and mirrors retain the leak). The remediation is non-negotiable:

1. **Rotate the secret** at the issuing service first
2. **Then** remove from current source (and consider history rewrite)

Triage is binary: false-positive (suppress + document why) or true-positive
(rotate + remove). Severity gradients would muddy that decision.

## detect-secrets — primary tool

### Invocation

The skill drives detect-secrets via `uvx`:

```bash
uvx detect-secrets scan --all-files --exclude-files <regex> .
```

**Important**: detect-secrets only emits findings when invoked with `cwd` set
to the target directory and the path passed as `.` (relative). Passing an
absolute path from outside `--all-files` returns empty results — this is a
known detect-secrets quirk and the skill's wrapper sets `cwd=project_root`
automatically.

### Plugins

By default detect-secrets loads 25+ plugins. Notable ones the skill cares
about:

- **AWSKeyDetector** — `AKIA[A-Z0-9]{16}` and similar AWS key formats
- **PrivateKeyDetector** — RSA/EC/OpenSSH private key headers
- **Base64HighEntropyString** (limit 4.5) — long random-looking strings
- **HexHighEntropyString** (limit 3.0) — same, for hex
- **KeywordDetector** — strings near keywords like `password`, `secret`, `token`
- **SlackDetector**, **StripeDetector**, **GitHubTokenDetector**, **GitLabTokenDetector**, ...
- **JwtTokenDetector** — JWT structure

To list active plugins at runtime: `uvx detect-secrets scan --list-all-plugins`.

### Baseline JSON schema

`detect-secrets scan` outputs a baseline JSON on stdout:

```json
{
  "version": "1.5.0",
  "plugins_used": [...],
  "filters_used": [...],
  "results": {
    "/abs/project/src/config.py": [
      {
        "type": "AWS Access Key",
        "filename": "/abs/project/src/config.py",
        "hashed_secret": "abc...hash",
        "is_verified": false,
        "line_number": 5
      }
    ]
  },
  "generated_at": "2026-05-23T00:00:00Z"
}
```

The skill flattens `results` to a finding list and strips the `project_root`
prefix from displayed paths.

### False-positive triage

detect-secrets has built-in heuristic filters (see `filters_used` in the
output). Common ones that suppress automatically:

- `is_indirect_reference` — variable referencing another var, not a literal
- `is_likely_id_string` — looks like an ID (UUID, version, hash)
- `is_lock_file` — `package-lock.json` etc. (also in skill default excludes)
- `is_potential_uuid`
- `is_sequential_string` — `123456...`, `abcdef...`
- `is_templated_secret` — capital-letter VARS that look like placeholders

When a real finding is a known false positive (test fixture, public docs
example, sample env file), suppress it explicitly:

**Per-line allowlist**:
```python
TEST_KEY = "AKIA..." # pragma: allowlist secret
```

**Per-file exclude** (regex via `--exclude-files`):
```bash
bash scripts/security-scan.sh --exclude tests/fixtures
```
The skill's `--exclude` flag extends the default exclude regex.

**Disable a plugin** for the whole project:
```bash
# Not exposed by security-scan.sh; drive detect-secrets directly:
uvx detect-secrets scan --disable-plugin Base64HighEntropyString --all-files .
```

### Baseline management

detect-secrets supports baseline files for incremental review:

```bash
uvx detect-secrets scan --all-files . > .secrets.baseline
git add .secrets.baseline
# Future scans compare against the baseline; only new secrets are reported.
uvx detect-secrets scan --baseline .secrets.baseline
```

The skill does **not** use baseline files by default — every Workflow J run
starts fresh. Users who want incremental review should drive detect-secrets
directly or wire it into a pre-commit hook.

## gitleaks — alternative tool

When `uvx` is not available but the user has gitleaks installed
(`brew install gitleaks` or a prebuilt binary), `detect-linter.sh` emits
`SECRETS_TOOL=gitleaks`. The skill currently ships only the detect-secrets
adapter — gitleaks support would land in a follow-up if needed.

If invoking gitleaks directly:

```bash
gitleaks detect --no-git --report-format json --report-path .gitleaks.json
```

Gitleaks's rule set is broader than detect-secrets in some areas (more
provider-specific tokens) but lacks detect-secrets's entropy heuristics and
keyword detector. For most projects detect-secrets is the better default.

Severity mapping for gitleaks (when implemented): any finding → BLOCKER, same
rationale as detect-secrets.

## Default exclude set

The skill's runner builds a single regex applied to both Semgrep (as globs)
and detect-secrets (as `--exclude-files` regex). Components:

```
\.git/  node_modules/  dist/  build/
venv/   .venv/         __pycache__/
.pytest_cache/  .mypy_cache/  .ruff_cache/
*.min.js  *.map
package-lock.json  yarn.lock  pnpm-lock.yaml  poetry.lock
*.snap
```

Override / extend via `security-scan.sh --exclude <pattern>`. The flag is
repeatable.
