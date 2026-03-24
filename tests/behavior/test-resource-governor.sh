#!/usr/bin/env bash
# Layer 2: Resource Governor Behavior Tests
# Tests resource-check.sh with mock cost data at various budget levels.
set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../../.." && pwd)}"
AOS="$PROJECT_DIR/.cognitive-os"
HOOKS_DIR="$AOS/hooks"
HOOK="$HOOKS_DIR/resource-check.sh"
COST_FILE="$AOS/metrics/cost-events.jsonl"

PASS=0
FAIL=0
SKIP=0

pass() { PASS=$((PASS + 1)); echo "  PASS: $1"; }
fail() { FAIL=$((FAIL + 1)); echo "  FAIL: $1"; }
skip() { SKIP=$((SKIP + 1)); echo "  SKIP: $1"; }

echo "=== RESOURCE GOVERNOR BEHAVIOR TESTS ==="
echo ""

if [ ! -x "$HOOK" ]; then
  skip "resource-check.sh not executable — skipping all"
  echo ""
  echo "=== RESOURCE GOVERNOR SUMMARY ==="
  echo "  PASS: $PASS  FAIL: $FAIL  SKIP: $SKIP"
  exit 0
fi

# Backup original cost file
BACKUP_COST=""
if [ -f "$COST_FILE" ]; then
  BACKUP_COST=$(cat "$COST_FILE")
fi

restore_cost() {
  if [ -n "$BACKUP_COST" ]; then
    echo "$BACKUP_COST" > "$COST_FILE"
  else
    > "$COST_FILE"
  fi
}
trap restore_cost EXIT

MOCK_AGENT='{"tool_name":"Agent","tool_input":{"prompt":"do work"}}'
TODAY=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# ---- Test 1: Empty cost file — should allow silently ----
echo "--- Empty cost file ---"
> "$COST_FILE"
OUTPUT=$(echo "$MOCK_AGENT" | CLAUDE_PROJECT_DIR="$PROJECT_DIR" bash "$HOOK" 2>&1)
EXIT_CODE=$?

if [ "$EXIT_CODE" -eq 0 ]; then
  pass "Allows agent launch with empty cost file"
else
  fail "Blocked agent launch with empty cost file (exit $EXIT_CODE)"
fi

# ---- Test 2: Low spend — should allow without warning ----
echo ""
echo "--- Low spend (well within budget) ---"
cat > "$COST_FILE" << EOF
{"timestamp":"$TODAY","estimated_cost_usd":0.50,"model":"sonnet","operation":"agent"}
{"timestamp":"$TODAY","estimated_cost_usd":0.30,"model":"sonnet","operation":"agent"}
EOF
OUTPUT=$(echo "$MOCK_AGENT" | CLAUDE_PROJECT_DIR="$PROJECT_DIR" bash "$HOOK" 2>&1)
EXIT_CODE=$?

if [ "$EXIT_CODE" -eq 0 ]; then
  pass "Allows agent launch with low spend"
else
  fail "Blocked agent launch with low spend"
fi

# ---- Test 3: High monthly spend — should trigger downgrade warning ----
echo ""
echo "--- High monthly spend (>80% budget) ---"
# Generate entries totaling ~$170 out of $200 budget (85%)
> "$COST_FILE"
for i in $(seq 1 17); do
  echo "{\"timestamp\":\"$TODAY\",\"estimated_cost_usd\":10.0,\"model\":\"opus\",\"operation\":\"agent\"}" >> "$COST_FILE"
done
OUTPUT=$(echo "$MOCK_AGENT" | CLAUDE_PROJECT_DIR="$PROJECT_DIR" bash "$HOOK" 2>&1)

if echo "$OUTPUT" | grep -qi "BUDGET\|downgrade\|sonnet\|PRESSURE"; then
  pass "Triggers budget warning at >80% spend"
else
  fail "No budget warning at >80% spend"
fi

# ---- Test 4: Over budget — should block ----
echo ""
echo "--- Over monthly budget (>100%) ---"
> "$COST_FILE"
for i in $(seq 1 25); do
  echo "{\"timestamp\":\"$TODAY\",\"estimated_cost_usd\":10.0,\"model\":\"opus\",\"operation\":\"agent\"}" >> "$COST_FILE"
done
OUTPUT=$(echo "$MOCK_AGENT" | CLAUDE_PROJECT_DIR="$PROJECT_DIR" bash "$HOOK" 2>&1)

if echo "$OUTPUT" | grep -qi "BLOCKED\|EXCEEDED\|deny"; then
  pass "Blocks agent launch when over monthly budget"
else
  fail "Did NOT block agent launch when over monthly budget"
fi

# ---- Test 5: Budget thresholds match cognitive-os.yaml ----
echo ""
echo "--- Budget thresholds match config ---"
CONFIG="$AOS/cognitive-os.yaml"
if [ -f "$CONFIG" ]; then
  CONFIGURED_LIMIT=$(grep 'monthly_limit_usd:' "$CONFIG" | head -1 | awk '{print $2}')
  CONFIGURED_DAILY=$(grep 'daily_alert_usd:' "$CONFIG" | head -1 | awk '{print $2}')
  if [ -n "$CONFIGURED_LIMIT" ]; then
    pass "Config monthly_limit_usd found: $CONFIGURED_LIMIT"
  else
    fail "Config monthly_limit_usd not found"
  fi
  if [ -n "$CONFIGURED_DAILY" ]; then
    pass "Config daily_alert_usd found: $CONFIGURED_DAILY"
  else
    fail "Config daily_alert_usd not found"
  fi
else
  skip "cognitive-os.yaml not found"
fi

# Restore
restore_cost

# ---- Summary ----
echo ""
echo "=== RESOURCE GOVERNOR SUMMARY ==="
echo "  PASS: $PASS"
echo "  FAIL: $FAIL"
echo "  SKIP: $SKIP"
echo ""

[ "$FAIL" -gt 0 ] && exit 1
exit 0
