#!/usr/bin/env bash
# test-remediation.sh — Unit tests for hooks/_lib/remediation.sh
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
  export COGNITIVE_OS_REMEDIATION_CONFIDENCE="0.8"
  export COGNITIVE_OS_REMEDIATION_DISABLE_RATE="0.3"
  export COGNITIVE_OS_REMEDIATION_DISABLE_MIN="5"
  mkdir -p "$COGNITIVE_OS_PROJECT_DIR/.cognitive-os/metrics"
  # Source libraries
  _SAFE_JSONL_LOADED=""
  source "$LIB_DIR/safe-jsonl.sh"
  source "$LIB_DIR/remediation.sh"
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

# ─── Test: remediation_register creates new entry ────────────────────────────

test_register_creates_entry() {
  setup

  remediation_register "BUILD" "service-a" "cannot find module foo" "missing dependency" "command" "npm install foo"

  local registry
  registry=$(_rem_registry_file)
  local index
  index=$(_rem_index_file)

  # Registry should have 1 line
  local lines
  lines=$(wc -l < "$registry" | tr -d ' ')
  assert_eq "register: registry has 1 line" "1" "$lines"

  # Verify entry content
  local error_type
  error_type=$(head -1 "$registry" | jq -r '.error_type')
  assert_eq "register: error_type=BUILD" "BUILD" "$error_type"

  local fix_cmd
  fix_cmd=$(head -1 "$registry" | jq -r '.fix_command')
  assert_eq "register: fix_command correct" "npm install foo" "$fix_cmd"

  # Index should have 1 entry
  local index_total
  index_total=$(jq '.stats.total' "$index")
  assert_eq "register: index total=1" "1" "$index_total"

  teardown
}

# ─── Test: remediation_register updates existing entry ───────────────────────

test_register_updates_existing() {
  setup

  remediation_register "BUILD" "service-a" "cannot find module foo" "missing dependency" "command" "npm install foo"
  remediation_register "BUILD" "service-a" "cannot find module foo" "missing dependency" "command" "npm install foo"

  local registry
  registry=$(_rem_registry_file)

  # Should still be 1 line (updated, not appended)
  local lines
  lines=$(wc -l < "$registry" | tr -d ' ')
  assert_eq "register update: still 1 line" "1" "$lines"

  # times_applied should be incremented
  local times
  times=$(head -1 "$registry" | jq -r '.times_applied')
  assert_eq "register update: times_applied=2" "2" "$times"

  teardown
}

# ─── Test: remediation_lookup finds known fix ────────────────────────────────

test_lookup_finds_fix() {
  setup

  remediation_register "TEST" "service-b" "connection refused on port 5432" "pg not running" "command" "docker start postgres"

  local result
  result=$(remediation_lookup "TEST" "service-b" "connection refused on port 5432")
  local rc=$?

  assert_eq "lookup: returns 0 for known fix" "0" "$rc"

  local fix_type
  fix_type=$(echo "$result" | jq -r '.fix_type')
  assert_eq "lookup: fix_type=command" "command" "$fix_type"

  local fix_cmd
  fix_cmd=$(echo "$result" | jq -r '.fix_command')
  assert_eq "lookup: fix_command correct" "docker start postgres" "$fix_cmd"

  teardown
}

# ─── Test: remediation_lookup returns 1 for unknown ──────────────────────────

test_lookup_returns_1_unknown() {
  setup

  remediation_register "BUILD" "service-c" "some known error" "root cause" "command" "fix it"

  remediation_lookup "BUILD" "service-c" "completely different error message" >/dev/null 2>&1
  local rc=$?

  assert_eq "lookup: returns 1 for unknown error" "1" "$rc"

  teardown
}

# ─── Test: remediation_lookup respects confidence threshold ──────────────────

test_lookup_confidence_threshold() {
  setup

  remediation_register "BUILD" "service-d" "pattern X" "cause" "command" "fix X"

  # Record many failures to drop confidence below threshold
  local fingerprint
  fingerprint=$(_rem_fingerprint "pattern X")

  remediation_record_failure "$fingerprint"
  remediation_record_failure "$fingerprint"
  remediation_record_failure "$fingerprint"

  # Now confidence = 1/(1+3) = 0.25 which is below 0.8 threshold
  remediation_lookup "BUILD" "service-d" "pattern X" >/dev/null 2>&1
  local rc=$?

  assert_eq "lookup: rejects low-confidence fix" "1" "$rc"

  teardown
}

# ─── Test: remediation_record_failure increments failure count ───────────────

test_record_failure_increments() {
  setup

  remediation_register "LINT" "service-e" "lint error pattern" "bad config" "command" "fix lint"

  local fingerprint
  fingerprint=$(_rem_fingerprint "lint error pattern")

  remediation_record_failure "$fingerprint"

  local registry
  registry=$(_rem_registry_file)
  local times_failed
  times_failed=$(head -1 "$registry" | jq -r '.times_failed')
  assert_eq "record_failure: times_failed=1" "1" "$times_failed"

  remediation_record_failure "$fingerprint"
  times_failed=$(head -1 "$registry" | jq -r '.times_failed')
  assert_eq "record_failure: times_failed=2" "2" "$times_failed"

  teardown
}

# ─── Test: auto_applicable goes false at < 0.3 rate after 5+ attempts ───────

test_auto_applicable_disabled() {
  setup

  remediation_register "BUILD" "service-f" "error pattern Z" "unknown" "command" "attempt fix"

  local fingerprint
  fingerprint=$(_rem_fingerprint "error pattern Z")

  # Register gives times_applied=1, times_failed=0
  # We need total >= 5 attempts and success_rate < 0.3
  # Record 5 failures: times_applied=1, times_failed=5 => rate = 1/6 ~ 0.167
  for i in $(seq 1 5); do
    remediation_record_failure "$fingerprint"
  done

  local registry
  registry=$(_rem_registry_file)
  local auto
  auto=$(head -1 "$registry" | jq -r '.auto_applicable')
  assert_eq "auto_applicable disabled at low success rate" "false" "$auto"

  # Index should also reflect this
  local index
  index=$(_rem_index_file)
  local index_auto
  index_auto=$(jq --arg fp "$fingerprint" '.entries[$fp].auto_applicable' "$index")
  assert_eq "index auto_applicable=false" "false" "$index_auto"

  teardown
}

# ─── Test: index stays in sync with registry ─────────────────────────────────

test_index_sync() {
  setup

  # Register multiple entries
  remediation_register "BUILD" "svc1" "error alpha" "cause a" "command" "fix a"
  remediation_register "TEST" "svc2" "error beta" "cause b" "command" "fix b"
  remediation_register "LINT" "svc3" "error gamma" "cause c" "command" "fix c"

  local index
  index=$(_rem_index_file)
  local registry
  registry=$(_rem_registry_file)

  local index_total
  index_total=$(jq '.stats.total' "$index")
  local registry_lines
  registry_lines=$(wc -l < "$registry" | tr -d ' ')

  assert_eq "index total matches registry lines" "$registry_lines" "$index_total"

  # Verify each index entry points to correct line
  local all_ok=true
  for fp in $(jq -r '.entries | keys[]' "$index"); do
    local line_num
    line_num=$(jq -r --arg fp "$fp" '.entries[$fp].line' "$index")
    local entry_fp
    entry_fp=$(sed -n "${line_num}p" "$registry" | jq -r '.fingerprint')
    if [ "$fp" != "$entry_fp" ]; then
      all_ok=false
    fi
  done

  assert_eq "index line pointers match registry" "true" "$all_ok"

  teardown
}

# ─── Run all tests ───────────────────────────────────────────────────────────

test_register_creates_entry
test_register_updates_existing
test_lookup_finds_fix
test_lookup_returns_1_unknown
test_lookup_confidence_threshold
test_record_failure_increments
test_auto_applicable_disabled
test_index_sync

echo "remediation: $TESTS tests, $FAILURES failures"
[ "$FAILURES" -eq 0 ] && exit 0 || exit 1
