#!/usr/bin/env bash
# Behavior test: Session isolation
# Simulates 2 sessions and verifies they get separate task files and metrics directories.
set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../../.." && pwd)}"
AOS="$PROJECT_DIR/.cognitive-os"
SESSIONS_DIR="$AOS/sessions"
HOOKS_DIR="$AOS/hooks"

PASS=0
FAIL=0

pass() { PASS=$((PASS + 1)); echo "  PASS: $1"; }
fail() { FAIL=$((FAIL + 1)); echo "  FAIL: $1"; }

echo "=== SESSION ISOLATION TESTS ==="
echo ""

# Clean up any previous test state
TEST_CLEANUP_DIRS=()

# ---- Test 1: session-init.sh creates session directory ----
echo "--- Session initialization ---"

if [ ! -x "$HOOKS_DIR/session-init.sh" ]; then
  fail "session-init.sh not executable"
else
  # Simulate session 1
  OUTPUT1=$(CLAUDE_PROJECT_DIR="$PROJECT_DIR" bash "$HOOKS_DIR/session-init.sh" 2>&1)
  EXIT1=$?

  if [ "$EXIT1" -eq 0 ]; then
    pass "session-init.sh exits 0 (session 1)"
  else
    fail "session-init.sh exits $EXIT1 (session 1)"
  fi

  # Extract session ID from output
  SID1=$(echo "$OUTPUT1" | grep "Session ID:" | sed 's/.*Session ID: //')
  if [ -n "$SID1" ]; then
    pass "Session 1 ID generated: $SID1"
    TEST_CLEANUP_DIRS+=("$SESSIONS_DIR/$SID1")
  else
    fail "Session 1 ID not found in output"
  fi

  # Verify directory structure
  if [ -d "$SESSIONS_DIR/$SID1" ]; then
    pass "Session 1 directory created"
  else
    fail "Session 1 directory NOT created"
  fi

  if [ -f "$SESSIONS_DIR/$SID1/tasks.json" ]; then
    pass "Session 1 tasks.json exists"
  else
    fail "Session 1 tasks.json NOT created"
  fi

  if [ -d "$SESSIONS_DIR/$SID1/metrics" ]; then
    pass "Session 1 metrics/ directory exists"
  else
    fail "Session 1 metrics/ directory NOT created"
  fi

  if [ -f "$SESSIONS_DIR/$SID1/meta.json" ]; then
    pass "Session 1 meta.json exists"
    # Validate meta.json is valid JSON
    if jq empty "$SESSIONS_DIR/$SID1/meta.json" 2>/dev/null; then
      pass "Session 1 meta.json is valid JSON"
    else
      fail "Session 1 meta.json is INVALID JSON"
    fi
  else
    fail "Session 1 meta.json NOT created"
  fi

  # Simulate session 2
  OUTPUT2=$(CLAUDE_PROJECT_DIR="$PROJECT_DIR" bash "$HOOKS_DIR/session-init.sh" 2>&1)
  SID2=$(echo "$OUTPUT2" | grep "Session ID:" | sed 's/.*Session ID: //')

  if [ -n "$SID2" ]; then
    pass "Session 2 ID generated: $SID2"
    TEST_CLEANUP_DIRS+=("$SESSIONS_DIR/$SID2")
  else
    fail "Session 2 ID not found in output"
  fi

  # ---- Test 2: Sessions have DIFFERENT IDs ----
  echo ""
  echo "--- Session uniqueness ---"

  if [ "$SID1" != "$SID2" ]; then
    pass "Session IDs are unique ($SID1 != $SID2)"
  else
    fail "Session IDs are NOT unique!"
  fi

  # ---- Test 3: Each session has its own tasks.json ----
  echo ""
  echo "--- Task isolation ---"

  TASKS1="$SESSIONS_DIR/$SID1/tasks.json"
  TASKS2="$SESSIONS_DIR/$SID2/tasks.json"

  if [ -f "$TASKS1" ] && [ -f "$TASKS2" ]; then
    pass "Both sessions have separate tasks.json files"

    # Write different content to verify independence
    echo '[{"task":"from-session-1"}]' > "$TASKS1"
    echo '[{"task":"from-session-2"}]' > "$TASKS2"

    CONTENT1=$(jq -r '.[0].task' "$TASKS1" 2>/dev/null)
    CONTENT2=$(jq -r '.[0].task' "$TASKS2" 2>/dev/null)

    if [ "$CONTENT1" = "from-session-1" ] && [ "$CONTENT2" = "from-session-2" ]; then
      pass "Task files are independently writable"
    else
      fail "Task files are NOT independent"
    fi
  else
    fail "One or both sessions missing tasks.json"
  fi

  # ---- Test 4: Each session has its own metrics directory ----
  echo ""
  echo "--- Metrics isolation ---"

  METRICS1="$SESSIONS_DIR/$SID1/metrics"
  METRICS2="$SESSIONS_DIR/$SID2/metrics"

  if [ -d "$METRICS1" ] && [ -d "$METRICS2" ]; then
    pass "Both sessions have separate metrics/ directories"

    # Write test metric to each
    echo '{"test":"session1"}' > "$METRICS1/test.jsonl"
    echo '{"test":"session2"}' > "$METRICS2/test.jsonl"

    if [ "$(jq -r '.test' "$METRICS1/test.jsonl")" = "session1" ] && \
       [ "$(jq -r '.test' "$METRICS2/test.jsonl")" = "session2" ]; then
      pass "Metrics directories are independently writable"
    else
      fail "Metrics directories are NOT independent"
    fi
  else
    fail "One or both sessions missing metrics/ directory"
  fi

  # ---- Test 5: active-sessions.json contains both ----
  echo ""
  echo "--- Active sessions registry ---"

  if [ -f "$SESSIONS_DIR/active-sessions.json" ]; then
    COUNT=$(jq '[.sessions[] | select(.id == "'"$SID1"'" or .id == "'"$SID2"'")] | length' "$SESSIONS_DIR/active-sessions.json" 2>/dev/null)
    if [ "$COUNT" = "2" ]; then
      pass "Both sessions registered in active-sessions.json"
    else
      fail "Expected 2 sessions in registry, found $COUNT"
    fi
  else
    fail "active-sessions.json not found"
  fi
fi

# ---- Cleanup test sessions ----
echo ""
echo "--- Cleanup ---"
for dir in "${TEST_CLEANUP_DIRS[@]}"; do
  if [ -d "$dir" ]; then
    SID=$(basename "$dir")
    rm -rf "$dir"
    # Also remove from active-sessions.json
    if [ -f "$SESSIONS_DIR/active-sessions.json" ]; then
      jq --arg id "$SID" '.sessions = [.sessions[] | select(.id != $id)]' \
         "$SESSIONS_DIR/active-sessions.json" > "$SESSIONS_DIR/active-sessions.json.tmp" 2>/dev/null && \
         mv "$SESSIONS_DIR/active-sessions.json.tmp" "$SESSIONS_DIR/active-sessions.json"
    fi
  fi
done
echo "  Test sessions cleaned up."

# ---- Summary ----
echo ""
echo "=== SESSION ISOLATION SUMMARY ==="
echo "  PASS: $PASS"
echo "  FAIL: $FAIL"
echo ""

[ "$FAIL" -gt 0 ] && exit 1
exit 0
