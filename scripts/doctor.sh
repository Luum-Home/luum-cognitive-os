#!/usr/bin/env bash
# SCOPE: both
# Cognitive OS Doctor — Health check for all dependencies
# Usage: bash scripts/doctor.sh [--quiet]
#
# Exit 0 if all critical checks pass, exit 1 if issues found.
# --quiet: only print failures and summary (used by setup.sh)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
QUIET=false
[ "${1:-}" = "--quiet" ] && QUIET=true

# Counters
PASS=0
WARN=0
FAIL=0

# Colors
if [ -t 1 ]; then
  GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
else
  GREEN=''; YELLOW=''; RED=''; NC=''
fi

pass() {
  PASS=$((PASS + 1))
  $QUIET || echo -e "${GREEN}[PASS]${NC} $*"
}
warn_msg() {
  WARN=$((WARN + 1))
  echo -e "${YELLOW}[WARN]${NC} $*"
}
fail_msg() {
  FAIL=$((FAIL + 1))
  echo -e "${RED}[FAIL]${NC} $*"
}

has_cmd() { command -v "$1" &>/dev/null; }

resolve_path() {
  python3 -c 'import os, sys; print(os.path.realpath(sys.argv[1]))' "$1" 2>/dev/null || echo "$1"
}

$QUIET || echo "======================================"
$QUIET || echo "  Cognitive OS Doctor"
$QUIET || echo "======================================"
$QUIET || echo ""

# ── 1. Python ───────────────────────────────────────────────────────
$QUIET || echo "--- Python ---"

if has_cmd python3; then
  PY_VER=$(python3 --version 2>/dev/null | awk '{print $2}')
  PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
  PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
  if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 11 ]; then
    pass "Python $PY_VER (>= 3.11)"
  else
    fail_msg "Python $PY_VER is below required 3.11"
  fi
else
  fail_msg "python3 not found"
fi

# ── 2. Go ───────────────────────────────────────────────────────────
$QUIET || echo "--- Go ---"

GO_VERSION_FILE="$PROJECT_DIR/.go-version"
if [ -f "$GO_VERSION_FILE" ]; then
  REQUIRED_GO=$(cat "$GO_VERSION_FILE" | tr -d '[:space:]')
  if has_cmd go; then
    CURRENT_GO=$(go version 2>/dev/null | awk '{print $3}' | sed 's/go//')
    if [ "$CURRENT_GO" = "$REQUIRED_GO" ]; then
      pass "Go $CURRENT_GO (matches .go-version)"
    else
      warn_msg "Go $CURRENT_GO installed but .go-version requires $REQUIRED_GO"
    fi
  else
    warn_msg "Go not installed (required version: $REQUIRED_GO for cos CLI/TUI)"
  fi
else
  warn_msg ".go-version file not found"
fi

# ── 3. Core CLI tools ──────────────────────────────────────────────
$QUIET || echo "--- Core tools ---"

if has_cmd jq; then
  pass "jq $(jq --version 2>/dev/null || echo '')"
else
  fail_msg "jq not installed (required by hooks)"
fi

if has_cmd uv; then
  pass "uv $(uv --version 2>/dev/null | awk '{print $2}' || echo '')"
else
  fail_msg "uv not installed (required for Python package management)"
fi

if has_cmd git; then
  GIT_VER=$(git --version | awk '{print $3}')
  pass "git $GIT_VER"
else
  fail_msg "git not found"
fi

if has_cmd gh; then
  # Check if authenticated
  if gh auth status &>/dev/null 2>&1; then
    pass "gh CLI (authenticated)"
  else
    warn_msg "gh CLI installed but not authenticated (run: gh auth login)"
  fi
else
  warn_msg "gh CLI not installed"
fi

# ── 4. Docker ───────────────────────────────────────────────────────
$QUIET || echo "--- Docker (optional) ---"

if has_cmd docker; then
  if docker info &>/dev/null 2>&1; then
    pass "Docker (running)"
  else
    warn_msg "Docker installed but not running"
  fi
else
  warn_msg "Docker not installed"
fi

# ── 5. Claude Code ─────────────────────────────────────────────────
$QUIET || echo "--- Claude Code ---"

if has_cmd claude; then
  pass "Claude Code CLI"
else
  warn_msg "Claude Code CLI not found"
fi

# ── 6. engram ───────────────────────────────────────────────────────
$QUIET || echo "--- Memory ---"

if has_cmd engram; then
  pass "engram CLI"
else
  warn_msg "engram CLI not found (memory features will degrade gracefully)"
fi

# ── 7. CLAMP ────────────────────────────────────────────────────────
$QUIET || echo "--- Migration tools ---"

if has_cmd clamp; then
  pass "CLAMP"
else
  warn_msg "CLAMP not found (optional, for project migrations)"
fi

# ── 8. Security tools ──────────────────────────────────────────────
$QUIET || echo "--- Security (optional) ---"

for tool in semgrep aguara parry-guard mcp-scan; do
  if has_cmd "$tool"; then
    pass "$tool"
  else
    warn_msg "$tool not installed (optional security tool)"
  fi
done

# ── 9. Python imports ──────────────────────────────────────────────
$QUIET || echo "--- Python imports ---"

PYTHON_CMD="python3"
if [ -f "$PROJECT_DIR/.venv/bin/python" ]; then
  PYTHON_CMD="$PROJECT_DIR/.venv/bin/python"
fi

check_import() {
  local module="$1" label="$2"
  if $PYTHON_CMD -c "import $module" 2>/dev/null; then
    pass "$label ($module)"
  else
    warn_msg "$label ($module) — import failed"
  fi
}

# Core (always required)
check_import "yaml" "PyYAML (core)"
check_import "jinja2" "Jinja2 (core)"

# Dev group — only check if venv has dev deps
if $PYTHON_CMD -c "import pytest" 2>/dev/null; then
  check_import "pytest" "pytest (testing)"
  check_import "ruff" "ruff (enforcement)"  # ruff is a binary, may not import
  check_import "vulture.core" "vulture (enforcement)"
  check_import "importlinter" "import-linter (enforcement)"
fi

# Optional groups
for pair in "litellm:llm" "fastapi:web" "crawl4ai:crawling"; do
  module="${pair%%:*}"
  group="${pair##*:}"
  if $PYTHON_CMD -c "import $module" 2>/dev/null; then
    pass "$group ($module)"
  else
    $QUIET || warn_msg "$group ($module) — not installed (optional)"
  fi
done

# ── 10. Hook scripts ───────────────────────────────────────────────
$QUIET || echo "--- Hook scripts ---"

HOOKS_DIR="$PROJECT_DIR/hooks"
if [ -d "$HOOKS_DIR" ]; then
  NON_EXEC=0
  BROKEN_LINKS=0
  TOTAL_HOOKS=0

  for hook in "$HOOKS_DIR"/*.sh; do
    [ -e "$hook" ] || continue
    TOTAL_HOOKS=$((TOTAL_HOOKS + 1))

    # Resolve symlinks before checking
    RESOLVED=$(resolve_path "$hook")

    if [ ! -e "$RESOLVED" ]; then
      BROKEN_LINKS=$((BROKEN_LINKS + 1))
    elif [ ! -x "$RESOLVED" ]; then
      NON_EXEC=$((NON_EXEC + 1))
    fi
  done

  if [ "$BROKEN_LINKS" -gt 0 ]; then
    fail_msg "$BROKEN_LINKS broken symlinks in hooks/"
  fi

  if [ "$NON_EXEC" -gt 0 ]; then
    warn_msg "$NON_EXEC hook scripts are not executable"
  fi

  if [ "$BROKEN_LINKS" -eq 0 ] && [ "$NON_EXEC" -eq 0 ]; then
    pass "All $TOTAL_HOOKS hook scripts OK (executable, symlinks resolve)"
  fi
else
  fail_msg "hooks/ directory not found"
fi

# ── 11. Symlink integrity ──────────────────────────────────────────
$QUIET || echo "--- Symlink integrity ---"

BROKEN=0
CHECKED=0
for link in "$HOOKS_DIR"/*.sh; do
  [ -L "$link" ] || continue
  CHECKED=$((CHECKED + 1))
  TARGET=$(resolve_path "$link")
  if [ -z "$TARGET" ] || [ ! -e "$TARGET" ]; then
    BROKEN=$((BROKEN + 1))
    $QUIET || fail_msg "Broken symlink: $link"
  fi
done

if [ "$BROKEN" -eq 0 ] && [ "$CHECKED" -gt 0 ]; then
  pass "All $CHECKED symlinks resolve correctly"
elif [ "$CHECKED" -eq 0 ]; then
  pass "No symlinks to check"
fi

# ── 12. Config files ───────────────────────────────────────────────
$QUIET || echo "--- Config files ---"

for f in cognitive-os.yaml pyproject.toml .go-version; do
  if [ -f "$PROJECT_DIR/$f" ]; then
    pass "$f exists"
  else
    warn_msg "$f not found"
  fi
done

# Validate cognitive-os.yaml syntax
if [ -f "$PROJECT_DIR/cognitive-os.yaml" ] && has_cmd python3; then
  if $PYTHON_CMD -c "import yaml; yaml.safe_load(open('$PROJECT_DIR/cognitive-os.yaml'))" 2>/dev/null; then
    pass "cognitive-os.yaml is valid YAML"
  else
    fail_msg "cognitive-os.yaml has YAML syntax errors"
  fi
fi

# ── Summary ─────────────────────────────────────────────────────────
echo ""
echo "======================================"
echo "  Doctor Summary"
echo "======================================"
echo ""
echo "  Pass: $PASS"
echo "  Warn: $WARN"
echo "  Fail: $FAIL"
echo ""

if [ "$FAIL" -gt 0 ]; then
  echo "  Status: UNHEALTHY ($FAIL critical issue(s))"
  echo "  Run: bash scripts/setup.sh   to fix missing dependencies"
  echo ""
  exit 1
elif [ "$WARN" -gt 0 ]; then
  echo "  Status: HEALTHY (with $WARN warning(s))"
  echo "  Warnings are for optional tools. Core functionality works."
  echo ""
  exit 0
else
  echo "  Status: HEALTHY"
  echo ""
  exit 0
fi
