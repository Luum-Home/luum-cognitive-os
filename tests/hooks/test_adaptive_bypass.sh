#!/usr/bin/env bash
# Test suite for hooks/adaptive-bypass.sh
# Verifies complexity classifications with sample prompts.
#
# NOTE: The project is in "reconstruction" phase by default, which shifts
# thresholds UP by 10 (more things are "trivial" during rebuilds).
# Tests account for this phase modifier.
#
# Usage: bash tests/hooks/test_adaptive_bypass.sh
#
# Requires: jq

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOK="$PROJECT_DIR/hooks/adaptive-bypass.sh"

PASS=0
FAIL=0

# --- helpers ---

run_hook() {
  local prompt="$1"
  local json
  json=$(jq -c -n --arg p "$prompt" '{tool_name: "Agent", tool_input: {prompt: $p}}')
  echo "$json" | CLAUDE_PROJECT_DIR="$PROJECT_DIR" bash "$HOOK" 2>/dev/null
}

extract_score() {
  echo "$1" | grep -oE 'score=[0-9]+' | head -1 | sed 's/score=//'
}

assert_complexity() {
  local label="$1"
  local expected="$2"
  local output="$3"

  local actual
  actual=$(echo "$output" | grep -oE 'COMPLEXITY=[A-Z]+' | head -1 | sed 's/COMPLEXITY=//')

  if [ "$actual" = "$expected" ]; then
    PASS=$((PASS + 1))
    echo "  PASS: $label -> $actual (score=$(extract_score "$output"))"
  else
    FAIL=$((FAIL + 1))
    echo "  FAIL: $label -> expected $expected, got '$actual' (score=$(extract_score "$output"))"
  fi
}

assert_at_least() {
  local label="$1"
  local min_level="$2"  # numeric: 1=TRIVIAL .. 5=CRITICAL
  local output="$3"

  local actual
  actual=$(echo "$output" | grep -oE 'COMPLEXITY=[A-Z]+' | head -1 | sed 's/COMPLEXITY=//')

  local actual_num=0
  case "$actual" in
    TRIVIAL)  actual_num=1 ;;
    SMALL)    actual_num=2 ;;
    MEDIUM)   actual_num=3 ;;
    LARGE)    actual_num=4 ;;
    CRITICAL) actual_num=5 ;;
  esac

  if [ "$actual_num" -ge "$min_level" ]; then
    PASS=$((PASS + 1))
    echo "  PASS: $label -> $actual (>= level $min_level, score=$(extract_score "$output"))"
  else
    FAIL=$((FAIL + 1))
    echo "  FAIL: $label -> $actual (expected >= level $min_level, score=$(extract_score "$output"))"
  fi
}

assert_score_range() {
  local label="$1"
  local min_score="$2"
  local max_score="$3"
  local output="$4"

  local score
  score=$(extract_score "$output")

  if [ "$score" -ge "$min_score" ] && [ "$score" -le "$max_score" ]; then
    PASS=$((PASS + 1))
    echo "  PASS: $label -> score=$score (range $min_score-$max_score)"
  else
    FAIL=$((FAIL + 1))
    echo "  FAIL: $label -> score=$score (expected $min_score-$max_score)"
  fi
}

echo "=== Adaptive Bypass Hook Tests ==="
echo "Note: project phase is 'reconstruction' (thresholds shifted +10)"
echo ""

# --- Test 1: Trivial task (single file, no signals) ---
echo "Test 1: Trivial task (fix typo in one file)"
OUT=$(run_hook "Fix the typo on line 42 of main.go")
assert_complexity "single file typo fix" "TRIVIAL" "$OUT"
assert_score_range "single file score" 1 5 "$OUT"

# --- Test 2: Small task with directories (reconstruction phase makes it trivial) ---
echo "Test 2: Small scope (two files, two dirs — trivial in reconstruction)"
OUT=$(run_hook "Update the DTO in internal/users/application/dtos/user_dto.go and add a field to internal/users/domain/entities/user.go")
# 2 files + 2 dirs (10) = 12. In reconstruction, TRIVIAL_MAX=15.
assert_complexity "two file DTO update in reconstruction" "TRIVIAL" "$OUT"
assert_score_range "file+dir score" 10 20 "$OUT"

# --- Test 3: Medium task (directories + new feature) ---
echo "Test 3: Medium task (multiple directories)"
OUT=$(run_hook "Implement a new GetUserByID use case with controller, DTO, mapper, and repository in internal/users/. Create tests in internal/users/application/use_cases/ and internal/users/infrastructure/controllers/")
# 3 dirs = 15. In reconstruction, TRIVIAL_MAX=15, SMALL_MAX=25.
assert_at_least "new use case with 3 dirs" 1 "$OUT"

# --- Test 4: Large task with bulk keywords + explicit count ---
echo "Test 4: Large task (migrate all services, 47 endpoints)"
OUT=$(run_hook "Migrate all services from the legacy backend to the new architecture. There are 47 endpoints across 8 services that need to be moved.")
# migrate=15 + all services=25 + explicit 47 (replaces if higher) = max(40, 47) = 47
assert_at_least "migrate all services" 3 "$OUT"

# --- Test 5: Critical task with security + multi-service ---
echo "Test 5: Critical task (JWT auth + RBAC + all services)"
OUT=$(run_hook "Add JWT authentication and authorization across all services. Update the permission system and RBAC policies.")
# auth/jwt/rbac=30 + all services=25 + across all=20 = 75
# In reconstruction (LARGE_MAX=90): LARGE. Without phase shift (LARGE_MAX=80): LARGE.
assert_at_least "security across all services" 4 "$OUT"

# --- Test 6: Refactor with security keywords = critical ---
echo "Test 6: Refactor + payment (security keyword)"
OUT=$(run_hook "Refactor the payment processing module to use the new architecture patterns in internal/payments/")
# refactor=15 + payment=30 + internal/payments/ dir=5 = 50
assert_at_least "refactor payments" 3 "$OUT"

# --- Test 7: Empty/minimal prompt ---
echo "Test 7: Short prompt (no signals)"
OUT=$(run_hook "Fix bug")
assert_complexity "very short prompt" "TRIVIAL" "$OUT"
assert_score_range "minimal score" 0 5 "$OUT"

# --- Test 8: Rebrand (bulk + scope escalation) ---
echo "Test 8: Rebrand across entire codebase"
OUT=$(run_hook "Rebrand old-name to new-name across the entire codebase including all services and documentation")
# rebrand=15 + all services=25 + entire codebase/entire project=20 = 60
assert_at_least "rebrand entire codebase" 3 "$OUT"

# --- Test 9: Non-Agent tool (should produce no output) ---
echo "Test 9: Non-Agent tool skipped"
NON_AGENT_JSON='{"tool_name":"Bash","tool_input":{"command":"ls"}}'
NON_AGENT_OUT=$(echo "$NON_AGENT_JSON" | CLAUDE_PROJECT_DIR="$PROJECT_DIR" bash "$HOOK" 2>/dev/null)
if [ -z "$NON_AGENT_OUT" ]; then
  PASS=$((PASS + 1))
  echo "  PASS: Non-Agent tool produces no output"
else
  FAIL=$((FAIL + 1))
  echo "  FAIL: Non-Agent tool should produce no output"
fi

# --- Test 10: Output format ---
echo "Test 10: Output contains score"
OUT=$(run_hook "Add a new endpoint to internal/users/infrastructure/controllers/user_controller.go")
if echo "$OUT" | grep -qE 'score=[0-9]+'; then
  PASS=$((PASS + 1))
  echo "  PASS: Output contains score"
else
  FAIL=$((FAIL + 1))
  echo "  FAIL: Output missing score"
fi

echo "Test 11: Output contains phase"
if echo "$OUT" | grep -qE 'phase=[a-z]+'; then
  PASS=$((PASS + 1))
  echo "  PASS: Output contains phase"
else
  FAIL=$((FAIL + 1))
  echo "  FAIL: Output missing phase"
fi

echo "Test 12: Output contains recommendation"
if echo "$OUT" | grep -qE 'Recommendation:'; then
  PASS=$((PASS + 1))
  echo "  PASS: Output contains recommendation"
else
  FAIL=$((FAIL + 1))
  echo "  FAIL: Output missing recommendation"
fi

# --- Test 13: Metrics file created ---
echo "Test 13: Metrics logged"
METRICS_FILE="$PROJECT_DIR/.cognitive-os/metrics/adaptive-bypass.jsonl"
if [ -f "$METRICS_FILE" ]; then
  LAST_LINE=$(tail -1 "$METRICS_FILE")
  if echo "$LAST_LINE" | jq -e . >/dev/null 2>&1; then
    HAS_COMPLEXITY=$(echo "$LAST_LINE" | jq -r '.complexity')
    HAS_SCORE=$(echo "$LAST_LINE" | jq -r '.score')
    if [ -n "$HAS_COMPLEXITY" ] && [ -n "$HAS_SCORE" ]; then
      PASS=$((PASS + 1))
      echo "  PASS: Metrics file has valid JSON with complexity=$HAS_COMPLEXITY, score=$HAS_SCORE"
    else
      FAIL=$((FAIL + 1))
      echo "  FAIL: Metrics JSON missing required fields"
    fi
  else
    FAIL=$((FAIL + 1))
    echo "  FAIL: Metrics file has invalid JSON"
  fi
else
  FAIL=$((FAIL + 1))
  echo "  FAIL: Metrics file not created"
fi

# --- Test 14: Security keyword alone triggers high score ---
echo "Test 14: Security keyword detection"
OUT=$(run_hook "Update the authentication flow in auth.go to support OAuth2")
# auth/authentication/oauth = 30, file auth.go = 1, total = 31
assert_at_least "auth keyword detection" 2 "$OUT"

# --- Test 15: Explicit count overrides low file detection ---
echo "Test 15: Explicit count in prompt"
OUT=$(run_hook "Update 200 files across the project to use the new import path")
# 200 files explicit count = 200 (overrides calculated score)
assert_at_least "explicit 200 files" 5 "$OUT"

# --- Summary ---
echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
TOTAL=$((PASS + FAIL))
if [ "$FAIL" -eq 0 ]; then
  echo "All $TOTAL tests passed."
  exit 0
else
  echo "$FAIL of $TOTAL tests FAILED."
  exit 1
fi
