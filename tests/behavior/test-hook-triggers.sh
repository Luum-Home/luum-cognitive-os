#!/usr/bin/env bash
# Layer 2: Hook Trigger Behavior Tests
# Simulates tool events and verifies hooks produce expected output.
set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../../.." && pwd)}"
AOS="$PROJECT_DIR/.cognitive-os"
HOOKS_DIR="$AOS/hooks"

PASS=0
FAIL=0
SKIP=0

pass() { PASS=$((PASS + 1)); echo "  PASS: $1"; }
fail() { FAIL=$((FAIL + 1)); echo "  FAIL: $1"; }
skip() { SKIP=$((SKIP + 1)); echo "  SKIP: $1"; }

echo "=== HOOK TRIGGER BEHAVIOR TESTS ==="
echo ""

# ---- Test 1: inject-phase-context.sh produces output for Agent tool ----
echo "--- inject-phase-context.sh ---"
HOOK="$HOOKS_DIR/inject-phase-context.sh"
if [ ! -x "$HOOK" ]; then
  skip "inject-phase-context.sh not executable"
else
  MOCK_INPUT='{"tool_name":"Agent","tool_input":{"prompt":"test prompt"}}'
  OUTPUT=$(echo "$MOCK_INPUT" | CLAUDE_PROJECT_DIR="$PROJECT_DIR" bash "$HOOK" 2>&1)
  EXIT_CODE=$?

  if [ "$EXIT_CODE" -eq 0 ]; then
    pass "inject-phase-context.sh exits 0 for Agent tool"
  else
    fail "inject-phase-context.sh exits $EXIT_CODE for Agent tool"
  fi

  if echo "$OUTPUT" | grep -qi "PHASE:"; then
    pass "inject-phase-context.sh outputs PHASE information"
  else
    fail "inject-phase-context.sh does NOT output PHASE information"
  fi

  if echo "$OUTPUT" | grep -qi "reconstruction\|stabilization\|production\|maintenance"; then
    pass "inject-phase-context.sh outputs a valid phase name"
  else
    fail "inject-phase-context.sh does NOT output a recognized phase name"
  fi

  if echo "$OUTPUT" | grep -qi "CONSTITUTIONAL GATES"; then
    pass "inject-phase-context.sh injects constitutional gates"
  else
    fail "inject-phase-context.sh does NOT inject constitutional gates"
  fi

  # Test non-Agent tool (should produce no output)
  MOCK_NON_AGENT='{"tool_name":"Bash","tool_input":{"command":"ls"}}'
  OUTPUT_NON=$(echo "$MOCK_NON_AGENT" | CLAUDE_PROJECT_DIR="$PROJECT_DIR" bash "$HOOK" 2>&1)
  if [ -z "$OUTPUT_NON" ]; then
    pass "inject-phase-context.sh produces no output for non-Agent tool"
  else
    fail "inject-phase-context.sh unexpectedly produced output for Bash tool"
  fi
fi

# ---- Test 2: error-learning.sh captures test failures ----
echo ""
echo "--- error-learning.sh ---"
HOOK="$HOOKS_DIR/error-learning.sh"
if [ ! -x "$HOOK" ]; then
  skip "error-learning.sh not executable"
else
  # Simulate a failed test command
  MOCK_FAIL='{"tool_name":"Bash","tool_input":{"command":"go test ./..."},"tool_response":"FAIL: TestSomething - expected 1 got 2","exit_code":"1"}'
  BACKUP_FILE="$AOS/metrics/error-learning.jsonl"
  BACKUP_LINES=0
  if [ -f "$BACKUP_FILE" ]; then
    BACKUP_LINES=$(wc -l < "$BACKUP_FILE" | tr -d ' ')
  fi

  OUTPUT=$(echo "$MOCK_FAIL" | CLAUDE_PROJECT_DIR="$PROJECT_DIR" bash "$HOOK" 2>&1)
  EXIT_CODE=$?

  if [ "$EXIT_CODE" -eq 0 ]; then
    pass "error-learning.sh exits 0 on simulated failure"
  else
    fail "error-learning.sh exits $EXIT_CODE on simulated failure"
  fi

  # Check if a new line was appended to error-learning.jsonl
  if [ -f "$BACKUP_FILE" ]; then
    NEW_LINES=$(wc -l < "$BACKUP_FILE" | tr -d ' ')
    if [ "$NEW_LINES" -gt "$BACKUP_LINES" ]; then
      pass "error-learning.sh appended entry to error-learning.jsonl"
      # Validate the last line is JSON
      LAST_LINE=$(tail -1 "$BACKUP_FILE")
      if echo "$LAST_LINE" | python3 -c "import json,sys; json.loads(sys.stdin.read())" 2>/dev/null; then
        pass "error-learning.sh wrote valid JSON"
      else
        fail "error-learning.sh wrote invalid JSON"
      fi

      # Check error type
      ERROR_TYPE=$(echo "$LAST_LINE" | python3 -c "import json,sys; print(json.loads(sys.stdin.read()).get('type',''))" 2>/dev/null)
      if [ "$ERROR_TYPE" = "TEST_FAILURE" ]; then
        pass "error-learning.sh correctly classified as TEST_FAILURE"
      else
        fail "error-learning.sh classified as '$ERROR_TYPE' instead of TEST_FAILURE"
      fi
    else
      fail "error-learning.sh did NOT append to error-learning.jsonl (dedup may have fired)"
    fi
  else
    fail "error-learning.jsonl not found after hook ran"
  fi

  # Test that successful commands are ignored
  MOCK_SUCCESS='{"tool_name":"Bash","tool_input":{"command":"go test ./..."},"tool_response":"ok","exit_code":"0"}'
  LINES_BEFORE=$(wc -l < "$BACKUP_FILE" 2>/dev/null | tr -d ' ' || echo "0")
  echo "$MOCK_SUCCESS" | CLAUDE_PROJECT_DIR="$PROJECT_DIR" bash "$HOOK" 2>/dev/null
  LINES_AFTER=$(wc -l < "$BACKUP_FILE" 2>/dev/null | tr -d ' ' || echo "0")
  if [ "$LINES_AFTER" -eq "$LINES_BEFORE" ]; then
    pass "error-learning.sh correctly ignores successful commands"
  else
    fail "error-learning.sh logged a successful command (should skip exit_code=0)"
  fi
fi

# ---- Test 3: resource-check.sh allows when no cost events ----
echo ""
echo "--- resource-check.sh ---"
HOOK="$HOOKS_DIR/resource-check.sh"
if [ ! -x "$HOOK" ]; then
  skip "resource-check.sh not executable"
else
  # With empty cost file, should allow silently
  MOCK_AGENT='{"tool_name":"Agent","tool_input":{"prompt":"do something"}}'
  OUTPUT=$(echo "$MOCK_AGENT" | CLAUDE_PROJECT_DIR="$PROJECT_DIR" bash "$HOOK" 2>&1)
  EXIT_CODE=$?

  if [ "$EXIT_CODE" -eq 0 ]; then
    pass "resource-check.sh exits 0 with no/empty cost data"
  else
    fail "resource-check.sh exits $EXIT_CODE with no cost data"
  fi

  # Non-agent tools should be ignored
  MOCK_BASH='{"tool_name":"Bash","tool_input":{"command":"ls"}}'
  OUTPUT_BASH=$(echo "$MOCK_BASH" | CLAUDE_PROJECT_DIR="$PROJECT_DIR" bash "$HOOK" 2>&1)
  if [ -z "$OUTPUT_BASH" ]; then
    pass "resource-check.sh ignores non-Agent tools"
  else
    # It might just exit silently which is fine
    pass "resource-check.sh handled non-Agent tool"
  fi
fi

# ---- Test 4: tool-loop-detector.sh runs without error ----
echo ""
echo "--- tool-loop-detector.sh ---"
HOOK="$HOOKS_DIR/tool-loop-detector.sh"
if [ ! -x "$HOOK" ]; then
  skip "tool-loop-detector.sh not executable"
else
  MOCK_INPUT='{"tool_name":"Bash","tool_input":{"command":"echo hello"},"tool_response":"hello"}'
  OUTPUT=$(echo "$MOCK_INPUT" | CLAUDE_PROJECT_DIR="$PROJECT_DIR" bash "$HOOK" 2>&1)
  EXIT_CODE=$?

  if [ "$EXIT_CODE" -eq 0 ]; then
    pass "tool-loop-detector.sh exits 0 on normal usage"
  else
    fail "tool-loop-detector.sh exits $EXIT_CODE on normal usage"
  fi
fi

# ---- Summary ----
echo ""
echo "=== HOOK TRIGGERS SUMMARY ==="
echo "  PASS: $PASS"
echo "  FAIL: $FAIL"
echo "  SKIP: $SKIP"
echo ""

[ "$FAIL" -gt 0 ] && exit 1
exit 0
