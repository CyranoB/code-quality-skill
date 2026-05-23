#!/usr/bin/env bash
# Bootstrap + exec wrapper for the skill's bundled ESLint with eslint-plugin-sonarjs.
#
# Why this exists: `npx --prefix DIR` does NOT install devDependencies from
# DIR/package.json. To make the bundled plugins resolvable, we have to run
# `npm ci --prefix DIR` (or `npm install --prefix DIR` if no lockfile) once,
# then exec ESLint from DIR/node_modules/.bin.
#
# Used by Workflow E (cognitive complexity) and Workflow I (complex_functions)
# for JS/TS targets. NOT used for general A/C/D lint — Biome stays as the
# JS/TS fallback there.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULTS_DIR="$(cd "$SCRIPT_DIR/../defaults" && pwd)"
ESLINT_BIN="$DEFAULTS_DIR/node_modules/.bin/eslint"

if [ ! -x "$ESLINT_BIN" ]; then
  if ! command -v npm >/dev/null 2>&1; then
    echo "error: npm is required for Workflow E/I on JS/TS but is not installed." >&2
    echo "Install Node.js (which includes npm), then re-run." >&2
    exit 127
  fi
  echo "Installing skill ESLint defaults into $DEFAULTS_DIR/node_modules (one-time, ~10-20s)..." >&2
  if [ -f "$DEFAULTS_DIR/package-lock.json" ]; then
    npm ci --prefix "$DEFAULTS_DIR" >&2
  else
    npm install --prefix "$DEFAULTS_DIR" >&2
  fi
  if [ ! -x "$ESLINT_BIN" ]; then
    echo "error: npm install completed but $ESLINT_BIN is still missing." >&2
    exit 1
  fi
fi

exec "$ESLINT_BIN" "$@"
