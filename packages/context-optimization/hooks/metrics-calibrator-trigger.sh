#!/usr/bin/env bash
# SCOPE: os-only
# metrics-calibrator-trigger.sh — Check if metrics calibration is due
# Trigger: SessionStart (after kpi-trigger.sh)

_HOOK_NAME="metrics-calibrator-trigger"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
METRICS_DIR="$(_resolve_metrics_dir)"
CALIBRATION_FILE="$PROJECT_DIR/.cognitive-os/metrics/calibration-history.jsonl"
KPI_FILE="$METRICS_DIR/kpi-history.jsonl"

# Check last calibration date
LAST_CALIBRATION=0
if [ -f "$CALIBRATION_FILE" ]; then
  LAST_CALIBRATION=$(tail -1 "$CALIBRATION_FILE" 2>/dev/null | jq -r '.timestamp_epoch // 0' 2>/dev/null || echo 0)
fi

NOW=$(date +%s)
DAYS_SINCE=$(( (NOW - LAST_CALIBRATION) / 86400 ))

# Trigger calibration if:
# 1. Never calibrated, OR
# 2. More than 7 days since last calibration, OR
# 3. KPI anomaly detected (value > 3 std dev from recent mean)
SHOULD_CALIBRATE=false

if [ "$DAYS_SINCE" -ge 7 ] || [ "$LAST_CALIBRATION" -eq 0 ]; then
  SHOULD_CALIBRATE=true
fi

# Quick anomaly check: any KPI changed by > 30% vs last 5 entries
if [ -f "$KPI_FILE" ] && [ "$SHOULD_CALIBRATE" = "false" ]; then
  ENTRY_COUNT=$(wc -l < "$KPI_FILE" 2>/dev/null | tr -d ' ')
  if [ "$ENTRY_COUNT" -ge 5 ]; then
    # Compare latest first_pass_success_rate vs mean of previous 4
    LATEST=$(tail -1 "$KPI_FILE" | jq -r '.first_pass_success_rate // 0' 2>/dev/null || echo 0)
    PREV_MEAN=$(tail -5 "$KPI_FILE" | head -4 | jq -r '.first_pass_success_rate // 0' 2>/dev/null | awk '{sum+=$1} END{if(NR>0) printf "%.2f", sum/NR; else print 0}')
    if [ -n "$LATEST" ] && [ -n "$PREV_MEAN" ] && [ "$PREV_MEAN" != "0" ]; then
      DIFF=$(echo "$LATEST $PREV_MEAN" | awk '{d=($1-$2)/$2; if(d<0) d=-d; printf "%.2f", d}')
      if [ "$(echo "$DIFF 0.30" | awk '{print ($1 > $2)}')" = "1" ]; then
        SHOULD_CALIBRATE=true
        echo "[metrics-calibrator] Anomaly detected: first_pass_success_rate changed by ${DIFF}x" >&2
      fi
    fi
  fi
fi

if [ "$SHOULD_CALIBRATE" = "true" ]; then
  echo "[metrics-calibrator] Calibration due (last: ${DAYS_SINCE}d ago). Recommend running /metrics-calibrator" >&2
fi

exit 0
