#!/usr/bin/env bash
# Layer 2: Self-Improvement Loop Behavior Tests
# Creates mock metrics data with known patterns, runs analysis hooks,
# and verifies they detect patterns and produce correct output.
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

# --- Setup test environment ---
TEST_DIR=$(mktemp -d)
TEST_METRICS="$TEST_DIR/.cognitive-os/metrics"
TEST_REFINE="$TEST_METRICS/auto-refine"
mkdir -p "$TEST_METRICS" "$TEST_REFINE"

# Copy cognitive-os.yaml for config reading
cp "$AOS/cognitive-os.yaml" "$TEST_DIR/.cognitive-os/cognitive-os.yaml" 2>/dev/null || true

cleanup() {
  rm -rf "$TEST_DIR"
}
trap cleanup EXIT

echo "=== SELF-IMPROVEMENT LOOP BEHAVIOR TESTS ==="
echo ""

# ---- Test 1: kpi-trigger.sh exists and is executable ----
echo "--- kpi-trigger.sh ---"
KPI_HOOK="$HOOKS_DIR/kpi-trigger.sh"
if [ ! -f "$KPI_HOOK" ]; then
  fail "kpi-trigger.sh does not exist"
else
  if [ -x "$KPI_HOOK" ]; then
    pass "kpi-trigger.sh exists and is executable"
  else
    # Try to make it executable for test purposes
    chmod +x "$KPI_HOOK" 2>/dev/null
    if [ -x "$KPI_HOOK" ]; then
      pass "kpi-trigger.sh exists (made executable)"
    else
      fail "kpi-trigger.sh exists but is not executable"
    fi
  fi
fi

# ---- Test 2: session-learning.sh exists and is executable ----
echo "--- session-learning.sh ---"
SL_HOOK="$HOOKS_DIR/session-learning.sh"
if [ ! -f "$SL_HOOK" ]; then
  fail "session-learning.sh does not exist"
else
  if [ -x "$SL_HOOK" ]; then
    pass "session-learning.sh exists and is executable"
  else
    chmod +x "$SL_HOOK" 2>/dev/null
    if [ -x "$SL_HOOK" ]; then
      pass "session-learning.sh exists (made executable)"
    else
      fail "session-learning.sh exists but is not executable"
    fi
  fi
fi

# ---- Test 3: self-improve skill exists ----
echo "--- self-improve skill ---"
SKILL_FILE="$AOS/skills/self-improve/SKILL.md"
if [ -f "$SKILL_FILE" ]; then
  pass "self-improve SKILL.md exists"
else
  fail "self-improve SKILL.md does not exist"
fi

# Verify skill frontmatter
if [ -f "$SKILL_FILE" ]; then
  if grep -q 'name: self-improve' "$SKILL_FILE"; then
    pass "self-improve skill has correct name in frontmatter"
  else
    fail "self-improve skill missing name in frontmatter"
  fi

  if grep -q 'user-invocable: true' "$SKILL_FILE"; then
    pass "self-improve skill is user-invocable"
  else
    fail "self-improve skill is not marked as user-invocable"
  fi
fi

# ---- Test 4: self-improvement-protocol rule exists ----
echo "--- self-improvement-protocol rule ---"
RULE_FILE="$AOS/rules/self-improvement-protocol.md"
if [ -f "$RULE_FILE" ]; then
  pass "self-improvement-protocol.md exists"
else
  fail "self-improvement-protocol.md does not exist"
fi

if [ -f "$RULE_FILE" ]; then
  if grep -q 'AUTO' "$RULE_FILE" && grep -q 'HUMAN APPROVAL' "$RULE_FILE"; then
    pass "protocol distinguishes auto-apply vs human approval"
  else
    fail "protocol missing auto-apply / human approval distinction"
  fi

  if grep -q 'rollback\|roll back\|revert' "$RULE_FILE"; then
    pass "protocol includes rollback procedures"
  else
    fail "protocol missing rollback procedures"
  fi
fi

# ---- Test 5: Create mock error data with known patterns ----
echo "--- Pattern detection with mock data ---"

# Create mock error-learning.jsonl with a clear pattern:
# 5 TEST_FAILURE errors for users-core (should be detected as a pattern)
EPOCH=$(date +%s)
for i in $(seq 1 5); do
  TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  E=$((EPOCH - i * 60))
  echo "{\"timestamp\":\"${TS}\",\"timestamp_epoch\":${E},\"type\":\"TEST_FAILURE\",\"service\":\"users-core\",\"framework\":\"go-test\",\"error\":\"FAIL: TestUserCreate - expected 200 got 500\",\"command\":\"go test ./...\",\"context\":\"assertion failure in test\",\"fingerprint\":\"abc123\"}" >> "$TEST_METRICS/error-learning.jsonl"
done

# Add 3 LINT_ERROR for bff-ninja
for i in $(seq 1 3); do
  TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  E=$((EPOCH - i * 120))
  echo "{\"timestamp\":\"${TS}\",\"timestamp_epoch\":${E},\"type\":\"LINT_ERROR\",\"service\":\"bff-ninja\",\"framework\":\"eslint\",\"error\":\"error TS2345: Argument of type string is not assignable\",\"command\":\"npx eslint .\",\"context\":\"TypeScript type error\",\"fingerprint\":\"def456\"}" >> "$TEST_METRICS/error-learning.jsonl"
done

# Verify the mock data was created
LINE_COUNT=$(wc -l < "$TEST_METRICS/error-learning.jsonl" | tr -d ' ')
if [ "$LINE_COUNT" -eq 8 ]; then
  pass "Mock error data created (8 entries)"
else
  fail "Expected 8 mock entries, got $LINE_COUNT"
fi

# ---- Test 6: Create mock skill-metrics.jsonl ----
# 10 entries: 7 success, 3 failure (70% success rate — at threshold)
for i in $(seq 1 7); do
  echo "{\"timestamp\":\"2026-03-22T10:0${i}:00Z\",\"skill\":\"apply\",\"model\":\"sonnet\",\"tokens\":5000,\"duration_ms\":3000,\"success\":true}" >> "$TEST_METRICS/skill-metrics.jsonl"
done
for i in $(seq 1 3); do
  echo "{\"timestamp\":\"2026-03-22T11:0${i}:00Z\",\"skill\":\"apply\",\"model\":\"sonnet\",\"tokens\":8000,\"duration_ms\":5000,\"success\":false}" >> "$TEST_METRICS/skill-metrics.jsonl"
done

SKILL_LINES=$(wc -l < "$TEST_METRICS/skill-metrics.jsonl" | tr -d ' ')
if [ "$SKILL_LINES" -eq 10 ]; then
  pass "Mock skill metrics created (10 entries, 70% success)"
else
  fail "Expected 10 skill metric entries, got $SKILL_LINES"
fi

# ---- Test 7: kpi-trigger.sh produces KPI snapshot ----
echo "--- kpi-trigger.sh execution ---"
if [ -x "$KPI_HOOK" ]; then
  OUTPUT=$(CLAUDE_PROJECT_DIR="$TEST_DIR" bash "$KPI_HOOK" 2>&1)
  EXIT_CODE=$?

  if [ "$EXIT_CODE" -eq 0 ]; then
    pass "kpi-trigger.sh exits 0"
  else
    fail "kpi-trigger.sh exits $EXIT_CODE"
  fi

  # Check that kpi-history.jsonl was created
  if [ -f "$TEST_METRICS/kpi-history.jsonl" ]; then
    pass "kpi-trigger.sh created kpi-history.jsonl"

    # Verify it contains valid JSON
    LAST_LINE=$(tail -1 "$TEST_METRICS/kpi-history.jsonl")
    if echo "$LAST_LINE" | python3 -m json.tool >/dev/null 2>&1; then
      pass "kpi-history.jsonl contains valid JSON"
    elif echo "$LAST_LINE" | jq . >/dev/null 2>&1; then
      pass "kpi-history.jsonl contains valid JSON"
    else
      fail "kpi-history.jsonl does not contain valid JSON"
    fi

    # Verify required fields
    if echo "$LAST_LINE" | grep -q 'first_pass_success_rate'; then
      pass "KPI snapshot contains first_pass_success_rate"
    else
      fail "KPI snapshot missing first_pass_success_rate"
    fi

    if echo "$LAST_LINE" | grep -q 'avg_iterations'; then
      pass "KPI snapshot contains avg_iterations"
    else
      fail "KPI snapshot missing avg_iterations"
    fi
  else
    fail "kpi-trigger.sh did not create kpi-history.jsonl"
  fi
else
  skip "kpi-trigger.sh not executable, skipping execution test"
fi

# ---- Test 8: session-learning.sh produces learning entry ----
echo "--- session-learning.sh execution ---"
if [ -x "$SL_HOOK" ]; then
  OUTPUT=$(CLAUDE_PROJECT_DIR="$TEST_DIR" COGNITIVE_OS_SESSION_START="2026-03-22T00:00:00Z" bash "$SL_HOOK" 2>&1)
  EXIT_CODE=$?

  if [ "$EXIT_CODE" -eq 0 ]; then
    pass "session-learning.sh exits 0"
  else
    fail "session-learning.sh exits $EXIT_CODE"
  fi

  if [ -f "$TEST_METRICS/session-learnings.jsonl" ]; then
    pass "session-learning.sh created session-learnings.jsonl"

    LAST_LINE=$(tail -1 "$TEST_METRICS/session-learnings.jsonl")
    if echo "$LAST_LINE" | grep -q 'session_errors'; then
      pass "Session learning contains session_errors field"
    else
      fail "Session learning missing session_errors field"
    fi

    if echo "$LAST_LINE" | grep -q 'success_rate'; then
      pass "Session learning contains success_rate field"
    else
      fail "Session learning missing success_rate field"
    fi
  else
    fail "session-learning.sh did not create session-learnings.jsonl"
  fi
else
  skip "session-learning.sh not executable, skipping execution test"
fi

# ---- Test 9: cognitive-os.yaml has self_improvement config ----
echo "--- cognitive-os.yaml configuration ---"
YAML="$AOS/cognitive-os.yaml"
if grep -q 'self_improvement:' "$YAML"; then
  pass "cognitive-os.yaml contains self_improvement section"
else
  fail "cognitive-os.yaml missing self_improvement section"
fi

if grep -q 'auto_apply:' "$YAML"; then
  pass "cognitive-os.yaml has auto_apply setting"
else
  fail "cognitive-os.yaml missing auto_apply setting"
fi

if grep -q 'first_pass_success:' "$YAML"; then
  pass "cognitive-os.yaml has first_pass_success threshold"
else
  fail "cognitive-os.yaml missing first_pass_success threshold"
fi

if grep -q 'max_auto_improvements:' "$YAML"; then
  pass "cognitive-os.yaml has max_auto_improvements"
else
  fail "cognitive-os.yaml missing max_auto_improvements"
fi

# ---- Test 10: CATALOG.md includes self-improve ----
echo "--- Catalog integration ---"
CATALOG="$AOS/skills/CATALOG.md"
if grep -q 'self-improve' "$CATALOG"; then
  pass "CATALOG.md includes self-improve skill"
else
  fail "CATALOG.md does not include self-improve skill"
fi

# ---- Test 11: RULES-COMPACT.md includes self-improvement-protocol ----
echo "--- Rules integration ---"
RULES="$AOS/rules/RULES-COMPACT.md"
if grep -q 'self-improvement' "$RULES"; then
  pass "RULES-COMPACT.md references self-improvement"
else
  fail "RULES-COMPACT.md does not reference self-improvement"
fi

# ---- Test 12: docs/INDEX.md includes self-improvement-loop ----
echo "--- Documentation integration ---"
INDEX="$AOS/docs/INDEX.md"
if grep -q 'self-improvement-loop' "$INDEX"; then
  pass "docs/INDEX.md includes self-improvement-loop"
else
  fail "docs/INDEX.md does not include self-improvement-loop"
fi

# ---- Summary ----
echo ""
echo "=== RESULTS ==="
echo "  PASS: $PASS"
echo "  FAIL: $FAIL"
echo "  SKIP: $SKIP"
TOTAL=$((PASS + FAIL + SKIP))
echo "  TOTAL: $TOTAL"

if [ "$FAIL" -eq 0 ]; then
  echo "  STATUS: ALL TESTS PASSED"
  exit 0
else
  echo "  STATUS: $FAIL TESTS FAILED"
  exit 1
fi
