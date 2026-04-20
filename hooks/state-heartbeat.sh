#!/usr/bin/env bash
# SCOPE: os-only
# state-heartbeat.sh — Continuous session state persistence
# PostToolUse hook: saves state snapshot every 10 tool calls or every 120 seconds.
#
# Fast path (<200ms): just increments a counter.
# Slow path (<1s): runs StateHeartbeat.save() via Python.
#
# Author: luum
set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

SESSION_DIR="${CLAUDE_SESSION_DIR:-${CLAUDE_PROJECT_DIR:-.}/.cognitive-os/sessions/default}"
SESSION_ID="${CLAUDE_SESSION_ID:-default}"
COUNTER_FILE="/tmp/cos-heartbeat-counter-${SESSION_ID}"
TIMESTAMP_FILE="/tmp/cos-heartbeat-ts-${SESSION_ID}"

# Increment counter (atomic enough for advisory use)
COUNT=1
if [ -f "$COUNTER_FILE" ]; then
    COUNT=$(( $(cat "$COUNTER_FILE" 2>/dev/null || echo 0) + 1 ))
fi
echo "$COUNT" > "$COUNTER_FILE"

# Check time-based fallback (>120 seconds since last save)
NOW=$(date +%s)
LAST_SAVE=0
if [ -f "$TIMESTAMP_FILE" ]; then
    LAST_SAVE=$(cat "$TIMESTAMP_FILE" 2>/dev/null || echo 0)
fi
TIME_ELAPSED=$(( NOW - LAST_SAVE ))

# Save every 10th call OR if >120 seconds have elapsed
if [ $(( COUNT % 10 )) -eq 0 ] || [ "$TIME_ELAPSED" -gt 120 ]; then
    python3 -c "
import sys
sys.path.insert(0, '${CLAUDE_PROJECT_DIR:-.}')
from lib.state_heartbeat import StateHeartbeat
h = StateHeartbeat('${SESSION_DIR}')
h.save()
" 2>/dev/null || true
    echo "$NOW" > "$TIMESTAMP_FILE"
    echo "0" > "$COUNTER_FILE"
fi

exit 0
