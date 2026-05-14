#!/usr/bin/env bash
# SCOPE: os-only
# PreToolUse hook on Agent — checks resource budget before agent launches.
# Reads daily/monthly spend from cost-events.jsonl, compares against budget in cognitive-os.yaml.
# If approaching limit: injects model downgrade instruction.
# If over limit: returns deny decision with message.

set -euo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="resource-check"
source "$(dirname "$0")/_lib/safe-jsonl.sh"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
COGNITIVE_OS_DIR="$PROJECT_DIR/.cognitive-os"
# Canonical config location is $PROJECT_DIR/cognitive-os.yaml; legacy path kept
# as fallback for projects that used to nest it under .cognitive-os/.
CONFIG="$PROJECT_DIR/cognitive-os.yaml"
[[ ! -f "$CONFIG" ]] && CONFIG="$COGNITIVE_OS_DIR/cognitive-os.yaml"
COST_FILE="$COGNITIVE_OS_DIR/metrics/cost-events.jsonl"
CHECK_LOG="$COGNITIVE_OS_DIR/metrics/resource-checks.jsonl"

# Read input from stdin
INPUT=$(cat)

# Only process Agent tool calls
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
if [[ "$TOOL_NAME" != "Agent" && "$TOOL_NAME" != "task" && "$TOOL_NAME" != "delegate" ]]; then
  exit 0
fi

# If no config, allow everything
if [[ ! -f "$CONFIG" ]]; then
  exit 0
fi

# Ensure metrics dir exists
mkdir -p "$COGNITIVE_OS_DIR/metrics"

# Parse budget limits from cognitive-os.yaml (simple grep-based parsing)
MONTHLY_LIMIT=$(grep 'monthly_limit_usd:' "$CONFIG" 2>/dev/null | head -1 | awk '{print $2}' || echo "200")
DAILY_ALERT=$(grep 'daily_alert_usd:' "$CONFIG" 2>/dev/null | head -1 | awk '{print $2}' || echo "10")
PER_AGENT_MAX=$(grep 'per_agent_max_usd:' "$CONFIG" 2>/dev/null | head -1 | awk '{print $2}' || echo "2")

# Default to generous limits if parsing fails
MONTHLY_LIMIT="${MONTHLY_LIMIT:-200}"
DAILY_ALERT="${DAILY_ALERT:-10}"
PER_AGENT_MAX="${PER_AGENT_MAX:-2}"

# If no cost file, nothing to check — allow
if [[ ! -f "$COST_FILE" ]] || [[ ! -s "$COST_FILE" ]]; then
  exit 0
fi

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
TODAY=$(date -u +"%Y-%m-%d")
MONTH=$(date -u +"%Y-%m")

# Calculate daily spend
DAILY_SPEND=$(grep "\"$TODAY" "$COST_FILE" 2>/dev/null | \
  jq -s '[.[].estimated_cost_usd // 0] | add // 0' 2>/dev/null || echo "0")

# Calculate monthly spend
MONTHLY_SPEND=$(grep "\"$MONTH" "$COST_FILE" 2>/dev/null | \
  jq -s '[.[].estimated_cost_usd // 0] | add // 0' 2>/dev/null || echo "0")

# Calculate budget percentage used
if command -v bc &>/dev/null; then
  MONTHLY_PCT=$(echo "scale=0; $MONTHLY_SPEND * 100 / $MONTHLY_LIMIT" | bc 2>/dev/null || echo "0")
  DAILY_PCT=$(echo "scale=0; $DAILY_SPEND * 100 / $DAILY_ALERT" | bc 2>/dev/null || echo "0")
else
  # Fallback: integer math (multiply by 100 first to avoid truncation)
  MONTHLY_SPEND_INT=$(printf "%.0f" "$MONTHLY_SPEND" 2>/dev/null || echo "0")
  MONTHLY_LIMIT_INT=$(printf "%.0f" "$MONTHLY_LIMIT" 2>/dev/null || echo "200")
  DAILY_SPEND_INT=$(printf "%.0f" "$DAILY_SPEND" 2>/dev/null || echo "0")
  DAILY_ALERT_INT=$(printf "%.0f" "$DAILY_ALERT" 2>/dev/null || echo "10")
  if [[ "$MONTHLY_LIMIT_INT" -gt 0 ]]; then
    MONTHLY_PCT=$(( MONTHLY_SPEND_INT * 100 / MONTHLY_LIMIT_INT ))
  else
    MONTHLY_PCT=0
  fi
  if [[ "$DAILY_ALERT_INT" -gt 0 ]]; then
    DAILY_PCT=$(( DAILY_SPEND_INT * 100 / DAILY_ALERT_INT ))
  else
    DAILY_PCT=0
  fi
fi

# Decision logic
DECISION="allow"
REASON=""
MODEL_OVERRIDE=""

if [[ "$MONTHLY_PCT" -ge 100 ]]; then
  DECISION="deny"
  REASON="Monthly budget EXCEEDED: \$${MONTHLY_SPEND} / \$${MONTHLY_LIMIT} (${MONTHLY_PCT}%). Agent launches blocked until budget resets."
  # Log the check
  ENTRY="{\"timestamp\":\"$TIMESTAMP\",\"action\":\"agent_launch\",\"decision\":\"deny\",\"reason\":\"monthly_budget_exceeded\",\"monthly_spend\":$MONTHLY_SPEND,\"monthly_limit\":$MONTHLY_LIMIT,\"monthly_pct\":$MONTHLY_PCT}"
  safe_jsonl_append "$CHECK_LOG" "$ENTRY"
  # Output deny
  echo ""
  echo "RESOURCE GOVERNOR: BLOCKED"
  echo "$REASON"
  echo "Run /resource-governor for details. Monthly budget resets on the 1st."
  echo ""
  exit 0

elif [[ "$MONTHLY_PCT" -ge 95 ]]; then
  DECISION="downgrade"
  MODEL_OVERRIDE="haiku"
  REASON="Monthly budget at ${MONTHLY_PCT}% (\$${MONTHLY_SPEND}/\$${MONTHLY_LIMIT}). Forcing haiku model."
  ENTRY="{\"timestamp\":\"$TIMESTAMP\",\"action\":\"model_downgrade\",\"decision\":\"downgrade\",\"reason\":\"budget_95pct\",\"model_override\":\"haiku\",\"monthly_spend\":$MONTHLY_SPEND,\"monthly_pct\":$MONTHLY_PCT}"
  safe_jsonl_append "$CHECK_LOG" "$ENTRY"
  echo ""
  echo "RESOURCE GOVERNOR: BUDGET WARNING (${MONTHLY_PCT}%)"
  echo "$REASON"
  echo "MODEL OVERRIDE: Use haiku for this agent. Only security/critical tasks may use sonnet."
  echo ""

elif [[ "$MONTHLY_PCT" -ge 80 ]]; then
  DECISION="downgrade"
  MODEL_OVERRIDE="sonnet"
  REASON="Monthly budget at ${MONTHLY_PCT}% (\$${MONTHLY_SPEND}/\$${MONTHLY_LIMIT}). Downgrading opus -> sonnet."
  ENTRY="{\"timestamp\":\"$TIMESTAMP\",\"action\":\"model_downgrade\",\"decision\":\"downgrade\",\"reason\":\"budget_80pct\",\"model_override\":\"sonnet\",\"monthly_spend\":$MONTHLY_SPEND,\"monthly_pct\":$MONTHLY_PCT}"
  safe_jsonl_append "$CHECK_LOG" "$ENTRY"
  echo ""
  echo "RESOURCE GOVERNOR: BUDGET PRESSURE (${MONTHLY_PCT}%)"
  echo "$REASON"
  echo "MODEL OVERRIDE: Use sonnet instead of opus for non-critical tasks."
  echo ""

elif [[ "$DAILY_PCT" -ge 100 ]]; then
  REASON="Daily spend alert: \$${DAILY_SPEND} / \$${DAILY_ALERT} (${DAILY_PCT}%). Consider pacing."
  ENTRY="{\"timestamp\":\"$TIMESTAMP\",\"action\":\"agent_launch\",\"decision\":\"allow_with_warning\",\"reason\":\"daily_alert_exceeded\",\"daily_spend\":$DAILY_SPEND,\"daily_alert\":$DAILY_ALERT,\"daily_pct\":$DAILY_PCT}"
  safe_jsonl_append "$CHECK_LOG" "$ENTRY"
  echo ""
  echo "RESOURCE GOVERNOR: DAILY SPEND ALERT"
  echo "$REASON"
  echo ""

else
  # Everything OK — no output needed, allow silently
  # Only log periodically (every 10th check) to avoid log bloat
  CHECK_COUNT=$(wc -l < "$CHECK_LOG" 2>/dev/null || echo "0")
  CHECK_COUNT=$(echo "$CHECK_COUNT" | tr -d ' ')
  if [[ $((CHECK_COUNT % 10)) -eq 0 ]]; then
    ENTRY="{\"timestamp\":\"$TIMESTAMP\",\"action\":\"agent_launch\",\"decision\":\"allow\",\"reason\":\"within_budget\",\"monthly_pct\":$MONTHLY_PCT,\"daily_pct\":$DAILY_PCT}"
    safe_jsonl_append "$CHECK_LOG" "$ENTRY"
  fi
fi

exit 0
