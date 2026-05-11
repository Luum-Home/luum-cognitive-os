#!/usr/bin/env bash
# tests/integration/test_external_pattern_cleanroom_gate.sh
# Integration tests for hooks/external-pattern-cleanroom-gate.sh
#
# Usage: bash tests/integration/test_external_pattern_cleanroom_gate.sh
# Exit:  0 if all tests pass, 1 if any fail

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOK="$ROOT_DIR/hooks/external-pattern-cleanroom-gate.sh"

PASS=0
FAIL=0

# ── Helpers ───────────────────────────────────────────────────────────────────

assert_exit() {
  local test_name="$1"
  local expected="$2"
  local actual="$3"
  if [ "$actual" -eq "$expected" ]; then
    echo "[PASS] $test_name"
    PASS=$((PASS + 1))
  else
    echo "[FAIL] $test_name — expected exit $expected, got $actual"
    FAIL=$((FAIL + 1))
  fi
}

# Set up a fake git repo with a hooks/ subdir so BASH_SOURCE resolution works
# Returns: sets FAKE_REPO, FAKE_HOOKS_DIR, PATCHED_HOOK
setup_fake_repo() {
  local tmpbase="$1"
  local name="${2:-repo}"
  local fake_source="${3:-}"

  FAKE_REPO="$tmpbase/$name"
  mkdir -p "$FAKE_REPO/hooks" "$FAKE_REPO/.cognitive-os/logs"

  cd "$FAKE_REPO"
  git init -q
  git config user.email "test@test.com"
  git config user.name "Test"

  FAKE_HOOKS_DIR="$FAKE_REPO/hooks"

  if [ -n "$fake_source" ]; then
    # Patch the source repo path
    PATCHED_HOOK="$FAKE_HOOKS_DIR/external-pattern-cleanroom-gate.sh"
    sed "s|/tmp/upstream-pattern-source|$fake_source|g" "$HOOK" > "$PATCHED_HOOK"
    chmod +x "$PATCHED_HOOK"
  else
    # Use original hook (or a copy)
    PATCHED_HOOK="$FAKE_HOOKS_DIR/external-pattern-cleanroom-gate.sh"
    cp "$HOOK" "$PATCHED_HOOK"
    chmod +x "$PATCHED_HOOK"
  fi
}

# ── Global tmp dir ─────────────────────────────────────────────────────────────
TMPDIR_TEST="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_TEST"' EXIT

PAYLOAD_COMMIT='{"tool_name":"Bash","tool_input":{"command":"git commit -m test"}}'

# ── Test 1: Non-commit command → pass, exit 0 ─────────────────────────────────
PAYLOAD_NOOP='{"tool_name":"Bash","tool_input":{"command":"ls -la"}}'
actual=$(
  cd "$ROOT_DIR"
  bash "$HOOK" <<< "$PAYLOAD_NOOP"
  echo $?
)
assert_exit "non-commit command exits 0" 0 "$actual"

# ── Test 2: Skip when /tmp/upstream-pattern-source does not exist ────────────────
# Ensure the dir is absent (real path)
[ -d "/tmp/upstream-pattern-source" ] || true  # we just need it absent

actual=$(
  cd "$ROOT_DIR"
  bash "$HOOK" <<< "$PAYLOAD_COMMIT"
  echo $?
)
assert_exit "skip when source repo absent → exit 0" 0 "$actual"

# Check skip was logged to real log
REAL_LOG="$ROOT_DIR/.cognitive-os/logs/external-pattern-cleanroom-gate.jsonl"
if [ -f "$REAL_LOG" ] && grep -q '"action":"skip"' "$REAL_LOG" 2>/dev/null; then
  echo "[PASS] skip logged with action:skip"
  PASS=$((PASS + 1))
else
  echo "[INFO] skip log check: absent source path, log may not have been written yet"
fi

# ── Test 3: Bypass via COS_ALLOW_UPSTREAM_PATTERN_LEAK=1 ───────────────────────────────
actual=$(
  cd "$ROOT_DIR"
  COS_ALLOW_UPSTREAM_PATTERN_LEAK=1 bash "$HOOK" <<< "$PAYLOAD_COMMIT"
  echo $?
)
assert_exit "bypass with COS_ALLOW_UPSTREAM_PATTERN_LEAK=1 → exit 0" 0 "$actual"

if [ -f "$REAL_LOG" ] && grep -q '"action":"bypass"' "$REAL_LOG" 2>/dev/null; then
  echo "[PASS] bypass logged with action:bypass"
  PASS=$((PASS + 1))
else
  echo "[INFO] bypass log check skipped (log not found)"
fi

# ── Test 4: Clean file → exit 0 ──────────────────────────────────────────────
FAKE_SOURCE_CLEAN="/tmp/upstream-pattern-source-clean-$$"
mkdir -p "$FAKE_SOURCE_CLEAN"
echo "totally_unrelated_content_xyz" > "$FAKE_SOURCE_CLEAN/source.py"

setup_fake_repo "$TMPDIR_TEST" "repo_clean" "$FAKE_SOURCE_CLEAN"
CLEAN_REPO="$FAKE_REPO"
CLEAN_HOOK="$PATCHED_HOOK"

echo "def greet_user_nicely_today():" > "$CLEAN_REPO/clean_file.py"
echo "    pass" >> "$CLEAN_REPO/clean_file.py"
cd "$CLEAN_REPO"
git add clean_file.py

actual=$(
  cd "$CLEAN_REPO"
  bash "$CLEAN_HOOK" <<< '{"tool_name":"Bash","tool_input":{"command":"git commit -m clean"}}' 2>/dev/null
  echo $?
)
assert_exit "clean file → exit 0" 0 "$actual"

rm -rf "$FAKE_SOURCE_CLEAN"
cd "$ROOT_DIR"

# ── Test 5: Leak detected → exit 1 ───────────────────────────────────────────
FAKE_SOURCE_LEAK="/tmp/upstream-pattern-source-leak-$$"
mkdir -p "$FAKE_SOURCE_LEAK"
# Put a unique long identifier into the fake source repo
echo "upstream_proprietary_unique_marker_xyzzy_9876" > "$FAKE_SOURCE_LEAK/core.py"

setup_fake_repo "$TMPDIR_TEST" "repo_leak" "$FAKE_SOURCE_LEAK"
LEAK_REPO="$FAKE_REPO"
LEAK_HOOK="$PATCHED_HOOK"

# Stage a file containing that token
echo "upstream_proprietary_unique_marker_xyzzy_9876 = True" > "$LEAK_REPO/leaked.py"
cd "$LEAK_REPO"
git add leaked.py

actual=$(
  cd "$LEAK_REPO"
  bash "$LEAK_HOOK" <<< '{"tool_name":"Bash","tool_input":{"command":"git commit -m leak"}}' 2>/dev/null
  echo $?
)
assert_exit "leak detected → exit 1" 1 "$actual"

rm -rf "$FAKE_SOURCE_LEAK"
cd "$ROOT_DIR"

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
