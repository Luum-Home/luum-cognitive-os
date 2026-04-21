#!/bin/bash
# SCOPE: os-only
# KPI Trigger Hook — Stop hook (runs at session end)
# Reads KPI data from metrics/, checks thresholds, logs snapshot to kpi-history.jsonl.
# If any KPI is below threshold, flags self-improvement for next session.
# Designed to be fast (<3s) and non-blocking.

set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="kpi-trigger"
source "$(dirname "$0")/_lib/safe-jsonl.sh"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
KPI_HISTORY="$METRICS_DIR/kpi-history.jsonl"
FLAG_FILE="$METRICS_DIR/.self-improve-recommended"

# Session-aware metrics directory
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-}"
if [ -z "$SESSION_ID" ]; then
  _SESSION_FILE="$PROJECT_DIR/.cognitive-os/sessions/.current-session-$$"
  [ -f "$_SESSION_FILE" ] && SESSION_ID=$(cat "$_SESSION_FILE" 2>/dev/null)
fi
SESSION_METRICS_DIR=""
if [ -n "$SESSION_ID" ]; then
  SESSION_METRICS_DIR="$PROJECT_DIR/.cognitive-os/sessions/$SESSION_ID/metrics"
fi

mkdir -p "$METRICS_DIR"

# --- Read config thresholds from cognitive-os.yaml ---
YAML="$PROJECT_DIR/.cognitive-os/cognitive-os.yaml"
FIRST_PASS_THRESHOLD=0.70
ITERATION_THRESHOLD=3
MAX_AUTO_IMPROVEMENTS=5

if [ -f "$YAML" ] && command -v yq &>/dev/null; then
  FPT=$(yq '.self_improvement.trigger_threshold.first_pass_success // 0.70' "$YAML" 2>/dev/null)
  IT=$(yq '.self_improvement.trigger_threshold.iteration_count // 3' "$YAML" 2>/dev/null)
  MAI=$(yq '.self_improvement.max_auto_improvements // 5' "$YAML" 2>/dev/null)
  [ -n "$FPT" ] && FIRST_PASS_THRESHOLD="$FPT"
  [ -n "$IT" ] && ITERATION_THRESHOLD="$IT"
  [ -n "$MAI" ] && MAX_AUTO_IMPROVEMENTS="$MAI"
fi

# --- Calculate KPIs from metrics files ---

# 1. First-pass success rate from skill-metrics.jsonl
SKILL_METRICS="$METRICS_DIR/skill-metrics.jsonl"
FIRST_PASS_SUCCESS=1.0
TOTAL_TASKS=0
SUCCESSFUL_TASKS=0

if [ -f "$SKILL_METRICS" ]; then
  TOTAL_TASKS=$(wc -l < "$SKILL_METRICS" 2>/dev/null | tr -d ' ')
  if [ "$TOTAL_TASKS" -gt 0 ]; then
    SUCCESSFUL_TASKS=$(grep -c '"success":\s*true\|"success": true' "$SKILL_METRICS" 2>/dev/null || echo "0")
    if [ "$TOTAL_TASKS" -gt 0 ]; then
      FIRST_PASS_SUCCESS=$(printf '%.2f' "$(echo "scale=4; $SUCCESSFUL_TASKS / $TOTAL_TASKS" | bc 2>/dev/null)" 2>/dev/null || echo "1.0")
    fi
  fi
fi

# 2. Error count from error-learning.jsonl (last 24h)
ERROR_FILE="$METRICS_DIR/error-learning.jsonl"
ERROR_COUNT_24H=0
if [ -f "$ERROR_FILE" ]; then
  CUTOFF=$(( $(date +%s) - 86400 ))
  ERROR_COUNT_24H=$(awk -F'"timestamp_epoch":' '{split($2,a,","); if(a[1]+0 > '"$CUTOFF"') count++} END{print count+0}' "$ERROR_FILE" 2>/dev/null || echo "0")
fi

# 3. Architecture compliance (count violations if file exists)
ARCH_VIOLATIONS=0
ARCH_FILE="$METRICS_DIR/architecture-violations.jsonl"
if [ -f "$ARCH_FILE" ]; then
  ARCH_VIOLATIONS=$(wc -l < "$ARCH_FILE" 2>/dev/null | tr -d ' ')
fi
ARCH_COMPLIANCE=1.0
if [ "$ARCH_VIOLATIONS" -gt 0 ] && [ "$TOTAL_TASKS" -gt 0 ]; then
  ARCH_COMPLIANCE=$(echo "scale=2; 1 - ($ARCH_VIOLATIONS / $TOTAL_TASKS)" | bc 2>/dev/null || echo "0.8")
fi

# 4. Average iterations from auto-refine data
AVG_ITERATIONS=1
REFINE_DIR="$METRICS_DIR/auto-refine"
if [ -d "$REFINE_DIR" ]; then
  REFINE_FILES=$(find "$REFINE_DIR" -name "*.jsonl" -type f 2>/dev/null | head -20)
  if [ -n "$REFINE_FILES" ]; then
    TOTAL_ITERS=0
    REFINE_COUNT=0
    for f in $REFINE_FILES; do
      ITERS=$(wc -l < "$f" 2>/dev/null | tr -d ' ')
      TOTAL_ITERS=$((TOTAL_ITERS + ITERS))
      REFINE_COUNT=$((REFINE_COUNT + 1))
    done
    if [ "$REFINE_COUNT" -gt 0 ]; then
      AVG_ITERATIONS=$(echo "scale=1; $TOTAL_ITERS / $REFINE_COUNT" | bc 2>/dev/null || echo "1")
    fi
  fi
fi

# --- Log KPI snapshot ---
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
SNAPSHOT="{\"timestamp\":\"${TIMESTAMP}\",\"first_pass_success_rate\":${FIRST_PASS_SUCCESS},\"avg_iterations\":${AVG_ITERATIONS},\"architecture_compliance\":${ARCH_COMPLIANCE},\"error_count_24h\":${ERROR_COUNT_24H},\"total_tasks\":${TOTAL_TASKS},\"successful_tasks\":${SUCCESSFUL_TASKS}}"

safe_jsonl_append "$KPI_HISTORY" "$SNAPSHOT"

# --- Check thresholds and flag if needed ---
ALERTS=""
FLAG_REASON=""

# Check first-pass success rate
BELOW_FPS=$(echo "$FIRST_PASS_SUCCESS < $FIRST_PASS_THRESHOLD" | bc 2>/dev/null || echo "0")
if [ "$BELOW_FPS" = "1" ]; then
  ALERTS="${ALERTS}ALERT: First-pass success rate ${FIRST_PASS_SUCCESS} is below threshold ${FIRST_PASS_THRESHOLD}\n"
  FLAG_REASON="${FLAG_REASON}first_pass_below_threshold,"
fi

# Check iteration count
ABOVE_ITER=$(echo "$AVG_ITERATIONS > $ITERATION_THRESHOLD" | bc 2>/dev/null || echo "0")
if [ "$ABOVE_ITER" = "1" ]; then
  ALERTS="${ALERTS}ALERT: Average iterations ${AVG_ITERATIONS} exceeds threshold ${ITERATION_THRESHOLD}\n"
  FLAG_REASON="${FLAG_REASON}iterations_above_threshold,"
fi

# Check architecture compliance
BELOW_ARCH=$(echo "$ARCH_COMPLIANCE < 0.80" | bc 2>/dev/null || echo "0")
if [ "$BELOW_ARCH" = "1" ]; then
  ALERTS="${ALERTS}ALERT: Architecture compliance ${ARCH_COMPLIANCE} is below 80%\n"
  FLAG_REASON="${FLAG_REASON}architecture_below_threshold,"
fi

# Check high error count
if [ "$ERROR_COUNT_24H" -gt 10 ]; then
  ALERTS="${ALERTS}ALERT: ${ERROR_COUNT_24H} errors in last 24 hours\n"
  FLAG_REASON="${FLAG_REASON}high_error_count,"
fi

# --- Write flag file if any threshold breached ---
if [ -n "$FLAG_REASON" ]; then
  echo "{\"timestamp\":\"${TIMESTAMP}\",\"reasons\":\"${FLAG_REASON}\",\"kpi_snapshot\":${SNAPSHOT}}" > "$FLAG_FILE"
fi

# --- Output alerts (injected into session context) ---
if [ -n "$ALERTS" ]; then
  echo ""
  echo "=== KPI THRESHOLD ALERTS ==="
  echo -e "$ALERTS"
  echo "Recommendation: Run /self-improve to analyze patterns and propose improvements."
  echo "=== END KPI ALERTS ==="
fi

exit 0
