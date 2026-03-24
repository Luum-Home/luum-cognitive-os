#!/usr/bin/env bash
# test-circuit-breaker.sh — Unit tests for hooks/_lib/circuit-breaker.sh
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LIB_DIR="$PROJECT_ROOT/hooks/_lib"

FAILURES=0
TESTS=0
TMPDIR_BASE=""

setup() {
  TMPDIR_BASE=$(mktemp -d)
  export COGNITIVE_OS_PROJECT_DIR="$TMPDIR_BASE/project"
  export COGNITIVE_OS_HOOK_HEARTBEAT="false"
  export COGNITIVE_OS_SESSION_ID=""
  export COGNITIVE_OS_CB_MAX_FAILURES=2
  export COGNITIVE_OS_CB_COOLDOWN=5           # 5 seconds for test speed
  export COGNITIVE_OS_CB_HOURLY_CAP=10
  mkdir -p "$COGNITIVE_OS_PROJECT_DIR/.cognitive-os/metrics"
  # Source libraries
  _SAFE_JSONL_LOADED=""
  source "$LIB_DIR/safe-jsonl.sh"
  source "$LIB_DIR/circuit-breaker.sh"
}

teardown() {
  rm -rf "$TMPDIR_BASE" 2>/dev/null
}

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

# ─── Test: cb_check returns 0 (CLOSED) with no state ────────────────────────

test_check_closed_no_state() {
  setup
  cb_check "TEST" "service-a"
  local rc=$?
  assert_eq "cb_check CLOSED with no state" "0" "$rc"
  teardown
}

# ─── Test: cb_record_failure increments counter ─────────────────────────────

test_record_failure_increments() {
  setup
  cb_record_failure "TEST" "service-a"

  local state_dir
  state_dir=$(_cb_state_dir)
  local key
  key=$(_cb_key "TEST" "service-a")
  local failures
  failures=$(jq -r '.consecutive_failures' "$state_dir/$key.json" 2>/dev/null)
  assert_eq "first failure: counter=1" "1" "$failures"

  teardown
}

# ─── Test: 2 consecutive failures trips breaker (OPEN) ──────────────────────

test_two_failures_trip_breaker() {
  setup
  cb_record_failure "BUILD" "service-b"
  cb_record_failure "BUILD" "service-b"

  local state_dir
  state_dir=$(_cb_state_dir)
  local key
  key=$(_cb_key "BUILD" "service-b")
  local state
  state=$(jq -r '.state' "$state_dir/$key.json" 2>/dev/null)
  assert_eq "2 failures: state=open" "open" "$state"

  teardown
}

# ─── Test: cb_check returns 1 when OPEN ──────────────────────────────────────

test_check_returns_1_when_open() {
  setup
  cb_record_failure "LINT" "service-c"
  cb_record_failure "LINT" "service-c"

  cb_check "LINT" "service-c"
  local rc=$?
  assert_eq "cb_check returns 1 when OPEN" "1" "$rc"

  teardown
}

# ─── Test: cooldown transitions to HALF-OPEN ─────────────────────────────────

test_cooldown_half_open() {
  setup
  # Trip the breaker
  cb_record_failure "TEST" "service-d"
  cb_record_failure "TEST" "service-d"

  # Manually set tripped_at to past (cooldown=5s, set to 10s ago)
  local state_dir
  state_dir=$(_cb_state_dir)
  local key
  key=$(_cb_key "TEST" "service-d")
  local past_epoch
  past_epoch=$(( $(date +%s) - 10 ))
  _cb_write_state "$state_dir/$key.json" "open" 2 "$past_epoch"

  # Now cb_check should return 0 (HALF-OPEN)
  cb_check "TEST" "service-d"
  local rc=$?
  assert_eq "cooldown: cb_check returns 0 (HALF-OPEN)" "0" "$rc"

  # Verify state transitioned to half-open
  local state
  state=$(jq -r '.state' "$state_dir/$key.json" 2>/dev/null)
  assert_eq "cooldown: state=half-open" "half-open" "$state"

  teardown
}

# ─── Test: cb_record_success resets to CLOSED ────────────────────────────────

test_record_success_resets() {
  setup
  cb_record_failure "BUILD" "service-e"
  cb_record_success "BUILD" "service-e"

  local state_dir
  state_dir=$(_cb_state_dir)
  local key
  key=$(_cb_key "BUILD" "service-e")
  local state
  state=$(jq -r '.state' "$state_dir/$key.json" 2>/dev/null)
  local failures
  failures=$(jq -r '.consecutive_failures' "$state_dir/$key.json" 2>/dev/null)

  assert_eq "success resets: state=closed" "closed" "$state"
  assert_eq "success resets: failures=0" "0" "$failures"

  teardown
}

# ─── Test: cb_reset clears state ─────────────────────────────────────────────

test_reset_clears_state() {
  setup
  cb_record_failure "TEST" "service-f"
  cb_reset "TEST" "service-f"

  local state_dir
  state_dir=$(_cb_state_dir)
  local key
  key=$(_cb_key "TEST" "service-f")

  TESTS=$((TESTS + 1))
  if [ ! -f "$state_dir/$key.json" ]; then
    : # pass
  else
    echo "  FAIL: cb_reset: state file still exists"
    FAILURES=$((FAILURES + 1))
  fi

  # cb_check should return 0 after reset
  cb_check "TEST" "service-f"
  local rc=$?
  assert_eq "cb_check returns 0 after reset" "0" "$rc"

  teardown
}

# ─── Test: cb_global_budget_ok counts correctly ──────────────────────────────

test_global_budget() {
  setup
  # With no outcomes file, budget should be OK
  cb_global_budget_ok
  local rc=$?
  assert_eq "global budget: OK with no outcomes" "0" "$rc"

  # Create outcomes file with many recent entries
  local outcomes="$COGNITIVE_OS_PROJECT_DIR/.cognitive-os/metrics/repair-outcomes.jsonl"
  local now_epoch
  now_epoch=$(date +%s)
  for i in $(seq 1 11); do
    echo "{\"timestamp_epoch\":$now_epoch,\"error_type\":\"TEST\",\"service\":\"svc\",\"outcome\":\"failure\"}" >> "$outcomes"
  done

  export COGNITIVE_OS_CB_HOURLY_CAP=10
  # Re-source to pick up new cap
  source "$LIB_DIR/circuit-breaker.sh"

  cb_global_budget_ok
  rc=$?
  assert_eq "global budget: exceeded with 11 entries" "1" "$rc"

  teardown
}

# ─── Test: cb_status output format ───────────────────────────────────────────

test_status_output() {
  setup
  # No state files
  local output
  output=$(cb_status 2>&1)
  TESTS=$((TESTS + 1))
  if echo "$output" | grep -q "Circuit Breaker Status"; then
    : # pass
  else
    echo "  FAIL: cb_status: missing header"
    FAILURES=$((FAILURES + 1))
  fi

  # With a breaker
  cb_record_failure "TEST" "svc-g"
  cb_record_failure "TEST" "svc-g"
  output=$(cb_status 2>&1)
  TESTS=$((TESTS + 1))
  if echo "$output" | grep -q "OPEN"; then
    : # pass
  else
    echo "  FAIL: cb_status: should show OPEN breaker"
    FAILURES=$((FAILURES + 1))
  fi

  teardown
}

# ─── Run all tests ───────────────────────────────────────────────────────────

test_check_closed_no_state
test_record_failure_increments
test_two_failures_trip_breaker
test_check_returns_1_when_open
test_cooldown_half_open
test_record_success_resets
test_reset_clears_state
test_global_budget
test_status_output

echo "circuit-breaker: $TESTS tests, $FAILURES failures"
[ "$FAILURES" -eq 0 ] && exit 0 || exit 1
