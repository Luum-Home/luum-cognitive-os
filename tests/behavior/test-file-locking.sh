#!/usr/bin/env bash
# Behavior test: File locking
# Tests advisory file locking: create lock, verify warning, verify auto-expiry.
set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../../.." && pwd)}"
AOS="$PROJECT_DIR/.cognitive-os"
SESSIONS_DIR="$AOS/sessions"
LOCKS_DIR="$SESSIONS_DIR/locks"
HOOKS_DIR="$AOS/hooks"

PASS=0
FAIL=0

pass() { PASS=$((PASS + 1)); echo "  PASS: $1"; }
fail() { FAIL=$((FAIL + 1)); echo "  FAIL: $1"; }

echo "=== FILE LOCKING TESTS ==="
echo ""

# Ensure directories exist
mkdir -p "$LOCKS_DIR" 2>/dev/null

GUARD_HOOK="$HOOKS_DIR/concurrent-write-guard.sh"

if [ ! -x "$GUARD_HOOK" ]; then
  fail "concurrent-write-guard.sh not executable"
  echo ""
  echo "=== FILE LOCKING SUMMARY ==="
  echo "  PASS: $PASS"
  echo "  FAIL: $FAIL"
  exit 1
fi

# ---- Test 1: Lock creation on write ----
echo "--- Lock creation ---"

# Create a fake session
TEST_SESSION_1="test-session-lock-1"
TEST_SESSION_DIR="$SESSIONS_DIR/$TEST_SESSION_1"
mkdir -p "$TEST_SESSION_DIR/metrics" 2>/dev/null

TEST_FILE="/tmp/test-file-for-locking.txt"

# Simulate an Edit tool invocation
MOCK_INPUT='{"tool_name":"Edit","tool_input":{"file_path":"'"$TEST_FILE"'","old_string":"a","new_string":"b"}}'
OUTPUT=$(echo "$MOCK_INPUT" | CLAUDE_PROJECT_DIR="$PROJECT_DIR" COGNITIVE_OS_SESSION_ID="$TEST_SESSION_1" bash "$GUARD_HOOK" 2>&1)
EXIT_CODE=$?

if [ "$EXIT_CODE" -eq 0 ]; then
  pass "concurrent-write-guard.sh exits 0"
else
  fail "concurrent-write-guard.sh exits $EXIT_CODE"
fi

# Check that a lock file was created
LOCK_COUNT=$(ls "$LOCKS_DIR"/*.lock 2>/dev/null | wc -l | tr -d ' ')
if [ "$LOCK_COUNT" -gt 0 ]; then
  pass "Lock file created in $LOCKS_DIR"
else
  fail "No lock file created"
fi

# Find the lock file for our test file
LOCK_FOUND=false
for lockfile in "$LOCKS_DIR"/*.lock; do
  [ ! -f "$lockfile" ] && continue
  LOCK_SID=$(jq -r '.session_id // empty' "$lockfile" 2>/dev/null)
  LOCK_PATH=$(jq -r '.file_path // empty' "$lockfile" 2>/dev/null)
  if [ "$LOCK_SID" = "$TEST_SESSION_1" ] && [ "$LOCK_PATH" = "$TEST_FILE" ]; then
    LOCK_FOUND=true
    LOCK_FILE_PATH="$lockfile"
    pass "Lock contains correct session ID and file path"
    break
  fi
done

if [ "$LOCK_FOUND" = false ]; then
  fail "Lock file with correct metadata not found"
fi

# ---- Test 2: Warning when different session tries to write ----
echo ""
echo "--- Cross-session warning ---"

TEST_SESSION_2="test-session-lock-2"
TEST_SESSION_DIR2="$SESSIONS_DIR/$TEST_SESSION_2"
mkdir -p "$TEST_SESSION_DIR2/metrics" 2>/dev/null

OUTPUT2=$(echo "$MOCK_INPUT" | CLAUDE_PROJECT_DIR="$PROJECT_DIR" COGNITIVE_OS_SESSION_ID="$TEST_SESSION_2" bash "$GUARD_HOOK" 2>&1)
EXIT_CODE2=$?

if [ "$EXIT_CODE2" -eq 0 ]; then
  pass "Guard exits 0 (advisory, does not block)"
else
  fail "Guard exits $EXIT_CODE2 (should be 0 for advisory)"
fi

if echo "$OUTPUT2" | grep -qi "CONCURRENT WRITE WARNING\|being edited by session"; then
  pass "Warning message displayed for cross-session write"
else
  fail "No warning message for cross-session write"
fi

# ---- Test 3: Same session does NOT get warning ----
echo ""
echo "--- Same-session no warning ---"

OUTPUT3=$(echo "$MOCK_INPUT" | CLAUDE_PROJECT_DIR="$PROJECT_DIR" COGNITIVE_OS_SESSION_ID="$TEST_SESSION_1" bash "$GUARD_HOOK" 2>&1)

if echo "$OUTPUT3" | grep -qi "WARNING"; then
  fail "Same session should NOT get a warning"
else
  pass "Same session does not get a warning"
fi

# ---- Test 4: Stale lock detection (expired) ----
echo ""
echo "--- Stale lock expiry ---"

if [ "$LOCK_FOUND" = true ] && [ -n "${LOCK_FILE_PATH:-}" ]; then
  # Set timestamp to 10 minutes ago (past the 300s default timeout)
  PAST_EPOCH=$(($(date +%s) - 600))
  jq --argjson epoch "$PAST_EPOCH" '.timestamp_epoch = $epoch' "$LOCK_FILE_PATH" > "$LOCK_FILE_PATH.tmp" 2>/dev/null && \
    mv "$LOCK_FILE_PATH.tmp" "$LOCK_FILE_PATH"

  # Now a different session should NOT get a warning (stale lock removed)
  OUTPUT4=$(echo "$MOCK_INPUT" | CLAUDE_PROJECT_DIR="$PROJECT_DIR" COGNITIVE_OS_SESSION_ID="$TEST_SESSION_2" bash "$GUARD_HOOK" 2>&1)

  if echo "$OUTPUT4" | grep -qi "WARNING"; then
    fail "Stale lock should be auto-expired, no warning expected"
  else
    pass "Stale lock correctly auto-expired"
  fi
fi

# ---- Test 5: Stale lock detection (dead PID) ----
echo ""
echo "--- Dead PID lock removal ---"

# Create a lock with a non-existent PID
DEAD_PID=99999
while kill -0 "$DEAD_PID" 2>/dev/null; do
  DEAD_PID=$((DEAD_PID + 1))
done

TEST_FILE_2="/tmp/test-file-for-locking-2.txt"
if command -v md5 &>/dev/null; then
  HASH2=$(echo -n "$TEST_FILE_2" | md5)
elif command -v md5sum &>/dev/null; then
  HASH2=$(echo -n "$TEST_FILE_2" | md5sum | cut -d' ' -f1)
else
  HASH2="deadpidtest"
fi

jq -n --arg sid "dead-session" --argjson pid "$DEAD_PID" --arg path "$TEST_FILE_2" --argjson epoch "$(date +%s)" \
  '{session_id: $sid, pid: $pid, file_path: $path, timestamp_epoch: $epoch}' \
  > "$LOCKS_DIR/${HASH2}.lock"

MOCK_INPUT_2='{"tool_name":"Write","tool_input":{"file_path":"'"$TEST_FILE_2"'","content":"test"}}'
OUTPUT5=$(echo "$MOCK_INPUT_2" | CLAUDE_PROJECT_DIR="$PROJECT_DIR" COGNITIVE_OS_SESSION_ID="$TEST_SESSION_1" bash "$GUARD_HOOK" 2>&1)

if echo "$OUTPUT5" | grep -qi "WARNING"; then
  fail "Dead PID lock should be auto-removed, no warning expected"
else
  pass "Dead PID lock correctly auto-removed"
fi

# ---- Cleanup ----
echo ""
echo "--- Cleanup ---"
rm -rf "$TEST_SESSION_DIR" "$TEST_SESSION_DIR2" 2>/dev/null
rm -f "$LOCKS_DIR"/*.lock 2>/dev/null
# Remove test sessions from active-sessions.json if present
if [ -f "$SESSIONS_DIR/active-sessions.json" ]; then
  jq '.sessions = [.sessions[] | select(.id != "test-session-lock-1" and .id != "test-session-lock-2")]' \
     "$SESSIONS_DIR/active-sessions.json" > "$SESSIONS_DIR/active-sessions.json.tmp" 2>/dev/null && \
     mv "$SESSIONS_DIR/active-sessions.json.tmp" "$SESSIONS_DIR/active-sessions.json"
fi
echo "  Test state cleaned up."

# ---- Summary ----
echo ""
echo "=== FILE LOCKING SUMMARY ==="
echo "  PASS: $PASS"
echo "  FAIL: $FAIL"
echo ""

[ "$FAIL" -gt 0 ] && exit 1
exit 0
