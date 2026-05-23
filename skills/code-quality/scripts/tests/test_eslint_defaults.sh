#!/usr/bin/env bash
# Tests for scripts/eslint-defaults.sh — verifies the bootstrap wrapper
# is idempotent and execs the locally-installed eslint binary.
#
# Note: this test installs ~30MB of npm dependencies into the skill's
# defaults/node_modules. It runs slowly the first time on a clean checkout
# (~10-20s) and quickly thereafter.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILL_DIR="$(cd "$SCRIPTS_DIR/.." && pwd)"
DEFAULTS_DIR="$SKILL_DIR/defaults"
WRAPPER="$SCRIPTS_DIR/eslint-defaults.sh"

pass=0
fail=0

assert() {
  local desc="$1"; shift
  if "$@"; then
    pass=$((pass + 1))
    echo "  ok  - $desc"
  else
    fail=$((fail + 1))
    echo "  FAIL - $desc"
  fi
}

assert_contains() {
  local desc="$1" needle="$2" haystack="$3"
  if [[ "$haystack" == *"$needle"* ]]; then
    pass=$((pass + 1))
    echo "  ok  - $desc"
  else
    fail=$((fail + 1))
    echo "  FAIL - $desc"
    echo "         expected to contain: $needle"
    echo "         actual: $haystack"
  fi
}

echo "== eslint-defaults.sh tests =="

assert "wrapper file exists" test -f "$WRAPPER"
assert "wrapper is executable" test -x "$WRAPPER"
assert "defaults/package.json exists" test -f "$DEFAULTS_DIR/package.json"
assert "defaults/package-lock.json exists (committed)" test -f "$DEFAULTS_DIR/package-lock.json"

echo
echo "-- bootstrap: first run installs node_modules --"
# Snapshot whether deps are already installed; restore at the end so we don't
# delete the user's working state.
HAD_NODE_MODULES=false
if [ -d "$DEFAULTS_DIR/node_modules" ]; then
  HAD_NODE_MODULES=true
fi

# Force a clean bootstrap path.
rm -rf "$DEFAULTS_DIR/node_modules"
assert "node_modules is missing before first run" \
  test ! -e "$DEFAULTS_DIR/node_modules/.bin/eslint"

# --version goes to stdout; install progress goes to stderr.
# Discard stderr on the first run so we capture only the version line.
OUTPUT="$("$WRAPPER" --version 2>/dev/null || true)"
assert "first run produces an eslint version string" \
  bash -c "[[ \"$OUTPUT\" =~ ^v[0-9] ]]"
assert "node_modules exists after first run" \
  test -x "$DEFAULTS_DIR/node_modules/.bin/eslint"

echo
echo "-- bootstrap: second run is idempotent (no reinstall) --"
# Time the second run; should be fast (sub-second) because npm ci is skipped.
START=$(python3 -c "import time; print(time.time())")
OUTPUT2="$("$WRAPPER" --version 2>/dev/null || true)"
END=$(python3 -c "import time; print(time.time())")
ELAPSED=$(python3 -c "print($END - $START)")
assert "second run still produces a version string" \
  bash -c "[[ \"$OUTPUT2\" =~ ^v[0-9] ]]"
# Allow up to 5s for slower environments; install would take ~10-20s.
assert "second run is fast (skips reinstall, <5s)" \
  python3 -c "import sys; sys.exit(0 if $ELAPSED < 5 else 1)"

echo
echo "-- bootstrap: produces the sonarjs plugin in node_modules --"
assert "eslint-plugin-sonarjs is installed" \
  test -d "$DEFAULTS_DIR/node_modules/eslint-plugin-sonarjs"

echo
echo "-- bootstrap: rule loading works through the wrapper --"
# Run eslint with the bundled config against a tiny inline file. ESLint flat
# config requires cwd to contain (or be under) the target — use mktemp.
TMPDIR_OWN="$(mktemp -d -t eslint-defaults-test.XXXXXX)"
trap 'rm -rf "$TMPDIR_OWN"' EXIT

cat > "$TMPDIR_OWN/sample.js" <<'JS'
// Deliberately complex to trigger sonarjs/cognitive-complexity (threshold 15).
function tangled(u, c) {
  if (u) {
    if (u.role === 'admin') {
      if (c.f === 'a') {
        if (u.t > 2) {
          if (u.s) {
            return 1;
          }
          return 2;
        }
        return 3;
      } else if (c.f === 'b') {
        if (u.t > 2) {
          return 4;
        }
        return 5;
      }
    } else if (u.role === 'g') {
      if (c.f === 'a') {
        return 6;
      }
      return 7;
    }
  }
  return 8;
}
module.exports = tangled;
JS

cd "$TMPDIR_OWN"
LINT_OUT="$("$WRAPPER" \
  --no-config-lookup \
  --config "$DEFAULTS_DIR/eslint.config.js" \
  --format json sample.js 2>&1 || true)"
cd - >/dev/null

assert_contains "wrapper emits a sonarjs/cognitive-complexity finding" \
  "sonarjs/cognitive-complexity" "$LINT_OUT"

echo
echo "-- bootstrap: restoring pre-test state --"
if [ "$HAD_NODE_MODULES" = false ]; then
  # The user didn't have node_modules before — leave it in the bootstrapped
  # state so subsequent skill commands don't re-pay the install cost. Tests
  # are non-destructive of build artifacts.
  echo "  (left node_modules in place — it was created by this test)"
fi

echo
echo "== results: $pass passed, $fail failed =="
exit "$fail"
