#!/usr/bin/env bash
# Layer 2: Private Mode Behavior Tests
# Tests private-mode-gate.sh and private-mode-metrics-gate.sh flag behavior.
set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../../.." && pwd)}"
AOS="$PROJECT_DIR/.cognitive-os"
HOOKS_DIR="$AOS/hooks"
FLAG="/tmp/claude-private-mode-active"

PASS=0
FAIL=0
SKIP=0

pass() { PASS=$((PASS + 1)); echo "  PASS: $1"; }
fail() { FAIL=$((FAIL + 1)); echo "  FAIL: $1"; }
skip() { SKIP=$((SKIP + 1)); echo "  SKIP: $1"; }

# Ensure clean state
cleanup() {
  rm -f "$FLAG" 2>/dev/null
}
trap cleanup EXIT

echo "=== PRIVATE MODE BEHAVIOR TESTS ==="
echo ""

# ---- Test 1: private-mode-gate.sh allows when flag absent ----
echo "--- Flag absent (normal mode) ---"
GATE="$HOOKS_DIR/private-mode-gate.sh"
if [ ! -x "$GATE" ]; then
  skip "private-mode-gate.sh not executable"
else
  cleanup
  MOCK_INPUT='{"tool_name":"mem_save","tool_input":{"title":"test"}}'
  OUTPUT=$(echo "$MOCK_INPUT" | CLAUDE_PROJECT_DIR="$PROJECT_DIR" bash "$GATE" 2>&1)
  EXIT_CODE=$?

  if [ "$EXIT_CODE" -eq 0 ]; then
    pass "private-mode-gate.sh exits 0 when flag absent"
  else
    fail "private-mode-gate.sh exits $EXIT_CODE when flag absent"
  fi

  if echo "$OUTPUT" | grep -qi "deny"; then
    fail "private-mode-gate.sh denied when flag is absent"
  else
    pass "private-mode-gate.sh allows engram when flag absent"
  fi
fi

# ---- Test 2: private-mode-gate.sh blocks when flag present ----
echo ""
echo "--- Flag present (private mode) ---"
if [ ! -x "$GATE" ]; then
  skip "private-mode-gate.sh not executable"
else
  touch "$FLAG"
  MOCK_INPUT='{"tool_name":"mem_save","tool_input":{"title":"test"}}'
  OUTPUT=$(echo "$MOCK_INPUT" | CLAUDE_PROJECT_DIR="$PROJECT_DIR" bash "$GATE" 2>&1)
  EXIT_CODE=$?

  if [ "$EXIT_CODE" -eq 0 ]; then
    pass "private-mode-gate.sh exits 0 when flag present (graceful deny)"
  else
    fail "private-mode-gate.sh exits $EXIT_CODE when flag present"
  fi

  if echo "$OUTPUT" | grep -qi "deny"; then
    pass "private-mode-gate.sh correctly denies engram in private mode"
  else
    fail "private-mode-gate.sh did NOT deny engram in private mode"
  fi

  cleanup
fi

# ---- Test 3: private-mode-metrics-gate.sh suppresses in private mode ----
echo ""
echo "--- Metrics gate behavior ---"
METRICS_GATE="$HOOKS_DIR/private-mode-metrics-gate.sh"
if [ ! -x "$METRICS_GATE" ]; then
  skip "private-mode-metrics-gate.sh not executable"
else
  # Normal mode — should pass through
  cleanup
  MOCK_INPUT='{"tool_name":"Bash","tool_input":{"command":"test"}}'
  OUTPUT=$(echo "$MOCK_INPUT" | CLAUDE_PROJECT_DIR="$PROJECT_DIR" bash "$METRICS_GATE" 2>&1)
  EXIT_CODE=$?
  if [ "$EXIT_CODE" -eq 0 ]; then
    pass "metrics-gate exits 0 in normal mode"
  else
    fail "metrics-gate exits $EXIT_CODE in normal mode"
  fi

  # Private mode — should consume input silently
  touch "$FLAG"
  OUTPUT=$(echo "$MOCK_INPUT" | CLAUDE_PROJECT_DIR="$PROJECT_DIR" bash "$METRICS_GATE" 2>&1)
  EXIT_CODE=$?
  if [ "$EXIT_CODE" -eq 0 ]; then
    pass "metrics-gate exits 0 in private mode"
  else
    fail "metrics-gate exits $EXIT_CODE in private mode"
  fi

  cleanup
fi

# ---- Summary ----
echo ""
echo "=== PRIVATE MODE SUMMARY ==="
echo "  PASS: $PASS"
echo "  FAIL: $FAIL"
echo "  SKIP: $SKIP"
echo ""

[ "$FAIL" -gt 0 ] && exit 1
exit 0
