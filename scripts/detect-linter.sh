#!/usr/bin/env bash
# detect-linter.sh — Auto-detect project linter and output key=value config
# Usage: detect-linter.sh [project-path] [--changed-only] [--help]

set -euo pipefail

# --- Help ---
if [[ "${1:-}" == "--help" ]]; then
  cat <<'USAGE'
Usage: detect-linter.sh [project-path] [--changed-only]

Auto-detects the linter for a project and outputs key=value pairs:

  TOOL          - Linter name (eslint, biome, ruff, pylint, npm-script)
  COMMAND       - Full command to run analysis with JSON output
  FIX_COMMAND   - Full command to auto-fix issues
  CONFIG        - Path to detected config file (empty if fallback)
  LANGUAGE      - Primary language (javascript, python)
  FALLBACK      - "true" if no explicit config found
  PROJECT_ROOT  - Detected project root directory
  FILES         - Space-separated file list (only with --changed-only)

Options:
  --changed-only  Only list files changed in git (staged + unstaged)
  --help          Show this help message
USAGE
  exit 0
fi

# --- Args ---
CHANGED_ONLY=false
PROJECT_PATH=""
for arg in "$@"; do
  case "$arg" in
    --changed-only) CHANGED_ONLY=true ;;
    --*) ;; # skip unknown flags
    *) [[ -z "$PROJECT_PATH" ]] && PROJECT_PATH="$arg" ;;
  esac
done
PROJECT_PATH="${PROJECT_PATH:-.}"

# Resolve to absolute path
PROJECT_PATH="$(cd "$PROJECT_PATH" && pwd)"

# --- Find project root ---
find_project_root() {
  local dir="$1"
  while [[ "$dir" != "/" ]]; do
    for marker in .git package.json go.mod pyproject.toml; do
      [[ -e "$dir/$marker" ]] && echo "$dir" && return
    done
    dir="$(dirname "$dir")"
  done
  # No root found, use the given path
  echo "$1"
}

PROJECT_ROOT="$(find_project_root "$PROJECT_PATH")"

# --- Helpers ---
has_file() { [[ -f "$PROJECT_ROOT/$1" ]]; }
has_glob() { compgen -G "$PROJECT_ROOT/$1" >/dev/null 2>&1; }

# Check if package.json has a key in devDependencies or dependencies
pkg_has_dep() {
  local dep="$1"
  [[ -f "$PROJECT_ROOT/package.json" ]] || return 1
  node -e "
    const pkg = require('$PROJECT_ROOT/package.json');
    const deps = { ...pkg.dependencies, ...pkg.devDependencies };
    process.exit(deps['$dep'] ? 0 : 1);
  " 2>/dev/null
}

# Check if package.json scripts contain a lint command
pkg_has_lint_script() {
  [[ -f "$PROJECT_ROOT/package.json" ]] || return 1
  node -e "
    const pkg = require('$PROJECT_ROOT/package.json');
    const scripts = pkg.scripts || {};
    const has = Object.keys(scripts).some(k => k === 'lint' || k === 'lint:check');
    process.exit(has ? 0 : 1);
  " 2>/dev/null
}

# Check if pyproject.toml contains a section
pyproject_has_section() {
  local section="$1"
  [[ -f "$PROJECT_ROOT/pyproject.toml" ]] || return 1
  grep -qE "^\[${section//./\\.}\]" "$PROJECT_ROOT/pyproject.toml" 2>/dev/null
}

# --- Changed files ---
get_changed_files() {
  local exts="$1"
  local files=""
  if command -v git >/dev/null 2>&1 && git -C "$PROJECT_ROOT" rev-parse --git-dir >/dev/null 2>&1; then
    files=$(cd "$PROJECT_ROOT" && {
      git diff --name-only 2>/dev/null
      git diff --cached --name-only 2>/dev/null
    } | sort -u)
  fi
  # Filter by extensions
  local filtered=""
  for f in $files; do
    for ext in $exts; do
      if [[ "$f" == *".$ext" ]]; then
        filtered="$filtered $f"
        break
      fi
    done
  done
  echo "$filtered" | xargs
}

# --- Detection ---
detect_javascript() {
  local tool="" cmd="" fix_cmd="" config="" fallback="false"

  # 1. package.json lint script
  if pkg_has_lint_script; then
    local pkg_manager="npm"
    [[ -f "$PROJECT_ROOT/yarn.lock" ]] && pkg_manager="yarn"
    [[ -f "$PROJECT_ROOT/pnpm-lock.yaml" ]] && pkg_manager="pnpm"
    [[ -f "$PROJECT_ROOT/bun.lockb" || -f "$PROJECT_ROOT/bun.lock" ]] && pkg_manager="bun"

    # Still need to detect the underlying tool for JSON output
    # Check if it's biome or eslint underneath
    if has_file "biome.json" || has_file "biome.jsonc"; then
      tool="biome"
      cmd="npx @biomejs/biome check --reporter=json"
      fix_cmd="npx @biomejs/biome check --write"
      config="$(ls "$PROJECT_ROOT"/biome.json* 2>/dev/null | head -1)"
    elif has_glob "eslint.config.*" || has_glob ".eslintrc*"; then
      tool="eslint"
      cmd="npx eslint --format json"
      fix_cmd="npx eslint --fix"
      config="$(ls "$PROJECT_ROOT"/eslint.config.* "$PROJECT_ROOT"/.eslintrc* 2>/dev/null | head -1)"
    else
      # Use the npm script directly (no JSON output guaranteed)
      tool="npm-script"
      cmd="$pkg_manager run lint"
      fix_cmd="$pkg_manager run lint -- --fix"
      config="package.json"
    fi
    echo "TOOL=$tool"
    echo "COMMAND=$cmd"
    echo "FIX_COMMAND=$fix_cmd"
    echo "CONFIG=$config"
    echo "LANGUAGE=javascript"
    echo "FALLBACK=$fallback"
    return 0
  fi

  # 2. Explicit eslint config
  if has_glob "eslint.config.*" || has_glob ".eslintrc*"; then
    config="$(ls "$PROJECT_ROOT"/eslint.config.* "$PROJECT_ROOT"/.eslintrc* 2>/dev/null | head -1)"
    echo "TOOL=eslint"
    echo "COMMAND=npx eslint --format json"
    echo "FIX_COMMAND=npx eslint --fix"
    echo "CONFIG=$config"
    echo "LANGUAGE=javascript"
    echo "FALLBACK=false"
    return 0
  fi

  # 3. Explicit biome config
  if has_file "biome.json" || has_file "biome.jsonc"; then
    config="$(ls "$PROJECT_ROOT"/biome.json* 2>/dev/null | head -1)"
    echo "TOOL=biome"
    echo "COMMAND=npx @biomejs/biome check --reporter=json"
    echo "FIX_COMMAND=npx @biomejs/biome check --write"
    echo "CONFIG=$config"
    echo "LANGUAGE=javascript"
    echo "FALLBACK=false"
    return 0
  fi

  # 4. devDependencies detection
  if pkg_has_dep "eslint"; then
    echo "TOOL=eslint"
    echo "COMMAND=npx eslint --format json"
    echo "FIX_COMMAND=npx eslint --fix"
    echo "CONFIG="
    echo "LANGUAGE=javascript"
    echo "FALLBACK=false"
    return 0
  fi

  if pkg_has_dep "@biomejs/biome"; then
    echo "TOOL=biome"
    echo "COMMAND=npx @biomejs/biome check --reporter=json"
    echo "FIX_COMMAND=npx @biomejs/biome check --write"
    echo "CONFIG="
    echo "LANGUAGE=javascript"
    echo "FALLBACK=false"
    return 0
  fi

  # 5. Fallback: JS/TS files present (check common project layouts)
  if has_glob "*.js" || has_glob "*.ts" || has_glob "*.jsx" || has_glob "*.tsx" \
    || has_glob "src/*.js" || has_glob "src/*.ts" || has_glob "src/*.tsx" || has_glob "src/*.jsx" \
    || has_glob "lib/*.js" || has_glob "lib/*.ts" || has_glob "app/*.js" || has_glob "app/*.ts"; then
    echo "TOOL=eslint"
    echo "COMMAND=npx eslint --format json"
    echo "FIX_COMMAND=npx eslint --fix"
    echo "CONFIG="
    echo "LANGUAGE=javascript"
    echo "FALLBACK=true"
    return 0
  fi

  return 1
}

detect_python() {
  local tool="" cmd="" fix_cmd="" config="" fallback="false"

  # 1. Explicit ruff config
  if has_file "ruff.toml" || has_file ".ruff.toml"; then
    config="$(ls "$PROJECT_ROOT"/ruff.toml "$PROJECT_ROOT"/.ruff.toml 2>/dev/null | head -1)"
    echo "TOOL=ruff"
    echo "COMMAND=ruff check --output-format json"
    echo "FIX_COMMAND=ruff check --fix"
    echo "CONFIG=$config"
    echo "LANGUAGE=python"
    echo "FALLBACK=false"
    return 0
  fi

  # 2. pyproject.toml with [tool.ruff]
  if pyproject_has_section "tool.ruff"; then
    echo "TOOL=ruff"
    echo "COMMAND=ruff check --output-format json"
    echo "FIX_COMMAND=ruff check --fix"
    echo "CONFIG=$PROJECT_ROOT/pyproject.toml"
    echo "LANGUAGE=python"
    echo "FALLBACK=false"
    return 0
  fi

  # 3. pylint config
  if has_file ".pylintrc" || pyproject_has_section "tool.pylint"; then
    config=""
    has_file ".pylintrc" && config="$PROJECT_ROOT/.pylintrc"
    [[ -z "$config" ]] && config="$PROJECT_ROOT/pyproject.toml"
    echo "TOOL=pylint"
    echo "COMMAND=pylint --output-format=json"
    echo "FIX_COMMAND="
    echo "CONFIG=$config"
    echo "LANGUAGE=python"
    echo "FALLBACK=false"
    return 0
  fi

  # 4. Fallback: .py files present (check common project layouts)
  if has_glob "*.py" || has_glob "src/*.py" || has_glob "app/*.py" \
    || has_glob "lib/*.py" || has_glob "tests/*.py" || has_glob "test/*.py"; then
    echo "TOOL=ruff"
    echo "COMMAND=uvx ruff check --output-format json"
    echo "FIX_COMMAND=uvx ruff check --fix"
    echo "CONFIG="
    echo "LANGUAGE=python"
    echo "FALLBACK=true"
    return 0
  fi

  return 1
}

# --- Main ---
# Capture output and exit code in a single call (avoid running detection twice)
OUTPUT=""
if OUTPUT="$(detect_javascript 2>/dev/null)"; then
  :
elif OUTPUT="$(detect_python 2>/dev/null)"; then
  :
else
  echo "TOOL=none"
  echo "COMMAND="
  echo "FIX_COMMAND="
  echo "CONFIG="
  echo "LANGUAGE=unknown"
  echo "FALLBACK=true"
  echo "PROJECT_ROOT=$PROJECT_ROOT"
  echo "FILES="
  exit 1
fi

echo "$OUTPUT"
echo "PROJECT_ROOT=$PROJECT_ROOT"

# Changed files
if [[ "$CHANGED_ONLY" == "true" ]]; then
  LANG_LINE="$(echo "$OUTPUT" | grep "^LANGUAGE=")"
  LANG="${LANG_LINE#LANGUAGE=}"
  case "$LANG" in
    javascript) FILES="$(get_changed_files "js ts jsx tsx mjs cjs")" ;;
    python)     FILES="$(get_changed_files "py pyi")" ;;
    *)          FILES="" ;;
  esac
  echo "FILES=$FILES"
else
  echo "FILES="
fi
