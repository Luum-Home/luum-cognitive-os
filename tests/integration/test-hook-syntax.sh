#!/usr/bin/env bash
# test-hook-syntax.sh — Validate all hooks for syntax, permissions, and patterns
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOKS_DIR="$PROJECT_ROOT/hooks"
LIB_DIR="$HOOKS_DIR/_lib"

FAILURES=0
TESTS=0

assert_eq() {
  local label="$1" expected="$2" actual="$3"
  TESTS=$((TESTS + 1))
  if [ "$expected" = "$actual" ]; then
    return 0
  else
    echo "  FAIL: $label (expected='$expected', got='$actual')"
    FAILURES=$((FAILURES + 1))
    return 1
  fi
}

# ─── Test: bash -n on every .sh file in hooks/ and hooks/_lib/ ──────────────

test_syntax_check() {
  local errors=0

  for sh_file in "$HOOKS_DIR"/*.sh "$LIB_DIR"/*.sh; do
    [ -f "$sh_file" ] || continue
    local name
    name=$(basename "$sh_file")
    if ! bash -n "$sh_file" 2>/dev/null; then
      echo "  SYNTAX ERROR: $name"
      errors=$((errors + 1))
    fi
  done

  assert_eq "all hooks pass bash -n syntax check" "0" "$errors"
}

# ─── Test: every hook is executable ──────────────────────────────────────────

test_executable_permission() {
  local non_exec=0
  local non_exec_list=""

  for sh_file in "$HOOKS_DIR"/*.sh; do
    [ -f "$sh_file" ] || continue
    if [ ! -x "$sh_file" ]; then
      non_exec_list="$non_exec_list $(basename "$sh_file")"
      non_exec=$((non_exec + 1))
    fi
  done

  # Lib files don't need to be executable (they're sourced), but hooks do
  TESTS=$((TESTS + 1))
  if [ "$non_exec" -gt 0 ]; then
    echo "  WARN: $non_exec hook(s) not executable:$non_exec_list"
    echo "  (Run: chmod +x hooks/*.sh to fix)"
    # This is a warning, not a hard failure — the hooks can still be invoked with bash
  fi
}

# ─── Test: every hook sources safe-jsonl.sh correctly ────────────────────────

test_sources_safe_jsonl() {
  local missing=0
  local missing_list=""
  local total_hooks=0

  for sh_file in "$HOOKS_DIR"/*.sh; do
    [ -f "$sh_file" ] || continue
    local name
    name=$(basename "$sh_file")
    total_hooks=$((total_hooks + 1))

    # Check if this hook uses safe_jsonl_append (direct JSONL write function)
    if grep -q 'safe_jsonl_append' "$sh_file" 2>/dev/null; then
      # It uses the safe append function — it should source safe-jsonl.sh (directly or via remediation.sh or circuit-breaker.sh)
      if ! grep -q 'source.*safe-jsonl\.sh\|source.*remediation\.sh\|source.*circuit-breaker\.sh' "$sh_file" 2>/dev/null; then
        missing_list="$missing_list $name"
        missing=$((missing + 1))
      fi
    fi
  done

  assert_eq "all safe_jsonl_append users source safe-jsonl.sh" "0" "$missing"
  if [ "$missing" -gt 0 ]; then
    echo "  Hooks missing source:$missing_list"
  fi
}

# ─── Test: no hook uses echo >> *.jsonl directly ─────────────────────────────

test_no_direct_echo_append() {
  local violations=0

  for sh_file in "$HOOKS_DIR"/*.sh; do
    [ -f "$sh_file" ] || continue
    local name
    name=$(basename "$sh_file")

    # Check for direct echo/printf >> *.jsonl (should use safe_jsonl_append)
    # Exclude comments and the safe-jsonl.sh library itself
    if grep -n 'echo.*>>.*\.jsonl\|printf.*>>.*\.jsonl' "$sh_file" 2>/dev/null | grep -v '^\s*#' | grep -v 'safe-jsonl' >/dev/null 2>&1; then
      echo "  VIOLATION: $name uses direct echo >> .jsonl (should use safe_jsonl_append)"
      violations=$((violations + 1))
    fi
  done

  # Also check lib files (except safe-jsonl.sh itself which is the implementation)
  for sh_file in "$LIB_DIR"/*.sh; do
    [ -f "$sh_file" ] || continue
    local name
    name=$(basename "$sh_file")
    [ "$name" = "safe-jsonl.sh" ] && continue

    if grep -n 'echo.*>>.*\.jsonl\|printf.*>>.*\.jsonl' "$sh_file" 2>/dev/null | grep -v '^\s*#' >/dev/null 2>&1; then
      echo "  VIOLATION: _lib/$name uses direct echo >> .jsonl"
      violations=$((violations + 1))
    fi
  done

  assert_eq "no direct echo >> .jsonl (use safe_jsonl_append)" "0" "$violations"
}

# ─── Test: lib files pass syntax check ───────────────────────────────────────

test_lib_syntax() {
  local errors=0

  for sh_file in "$LIB_DIR"/*.sh; do
    [ -f "$sh_file" ] || continue
    local name
    name=$(basename "$sh_file")
    if ! bash -n "$sh_file" 2>/dev/null; then
      echo "  LIB SYNTAX ERROR: $name"
      errors=$((errors + 1))
    fi
  done

  assert_eq "all lib files pass bash -n" "0" "$errors"
}

# ─── Run all tests ───────────────────────────────────────────────────────────

test_syntax_check
test_executable_permission
test_sources_safe_jsonl
test_no_direct_echo_append
test_lib_syntax

echo "hook-syntax: $TESTS tests, $FAILURES failures"
[ "$FAILURES" -eq 0 ] && exit 0 || exit 1
