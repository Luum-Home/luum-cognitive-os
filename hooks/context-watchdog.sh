#!/usr/bin/env bash
# SCOPE: both
# Context Watchdog — estimates context usage and emits one-shot checkpoint warnings.
# Type: PostToolUse
# Matcher: (none — fires on all tools when projected)
#
# Logic:
#   - Counts tool calls in a session-scoped counter file.
#   - Uses ~750 tokens per tool call and 200K usable context by default.
#   - 15%: light checkpoint reminder (one-shot).
#   - 50%: efficiency mode metric only (one-shot, silent).
#   - 70%: save decisions/discoveries to Engram (one-shot warning).
#   - 85%: stop new work and hand off (one-shot urgent warning).
#
# Must be fast and always exits 0.
set -uo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/_lib/common.sh"
check_disabled_env "context-watchdog"

PROJECT_DIR="$_PROJECT_DIR"
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-${CODEX_SESSION_ID:-${CLAUDE_SESSION_ID:-}}}"
if [ -n "$SESSION_ID" ]; then
  SESSION_DIR="$PROJECT_DIR/.cognitive-os/sessions/$SESSION_ID"
else
  SESSION_DIR="$PROJECT_DIR/.cognitive-os/sessions/current"
fi
COUNTER_FILE="$SESSION_DIR/tool-call-count"
MARKER_DIR="$SESSION_DIR/context-watchdog-markers"
METRICS_FILE="$PROJECT_DIR/.cognitive-os/metrics/context-watchdog.jsonl"

# Thresholds are expressed as approximate tool-call counts against a 200K window.
# 200K / 750 ~= 267 calls. Keep env overrides for harness/model calibration.
THRESHOLD_15="${CONTEXT_WATCHDOG_THRESHOLD_15:-40}"
THRESHOLD_50="${CONTEXT_WATCHDOG_THRESHOLD_50:-130}"
THRESHOLD_70="${CONTEXT_WATCHDOG_THRESHOLD_70:-185}"
THRESHOLD_85="${CONTEXT_WATCHDOG_THRESHOLD_85:-225}"
MAX_CALLS="${CONTEXT_WATCHDOG_MAX_CALLS:-267}"

mkdir -p "$SESSION_DIR" "$MARKER_DIR" "$(dirname "$METRICS_FILE")" 2>/dev/null || true

COUNT=0
if [ -f "$COUNTER_FILE" ]; then
  COUNT=$(cat "$COUNTER_FILE" 2>/dev/null) || COUNT=0
  case "$COUNT" in
    ''|*[!0-9]*) COUNT=0 ;;
  esac
fi
COUNT=$((COUNT + 1))
printf '%d' "$COUNT" > "$COUNTER_FILE" 2>/dev/null || true

if [ "$MAX_CALLS" -le 0 ] 2>/dev/null; then
  MAX_CALLS=267
fi
USAGE_PCT=$(( (COUNT * 100) / MAX_CALLS ))
[ "$USAGE_PCT" -gt 100 ] && USAGE_PCT=100

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
LEVEL="ok"
MESSAGE=""

_emit_once() {
  local marker="$1"
  local level="$2"
  local message="$3"
  if [ -f "$MARKER_DIR/$marker" ]; then
    return 1
  fi
  : > "$MARKER_DIR/$marker" 2>/dev/null || true
  LEVEL="$level"
  MESSAGE="$message"
  return 0
}

if [ "$COUNT" -ge "$THRESHOLD_85" ]; then
  _emit_once "85" "urgent" "CONTEXT WATCHDOG [URGENT]: ~85% context used (${COUNT} tool calls, ~${USAGE_PCT}%). STOP new work, save session state to Engram, and call mem_session_summary before compaction."
elif [ "$COUNT" -ge "$THRESHOLD_70" ]; then
  _emit_once "70" "warning" "CONTEXT WATCHDOG [WARNING]: ~70% context used (${COUNT} tool calls, ~${USAGE_PCT}%). Save decisions, bugs, and discoveries to Engram now; reduce verbosity and plan wrap-up."
elif [ "$COUNT" -ge "$THRESHOLD_50" ]; then
  _emit_once "50" "info" ""
elif [ "$COUNT" -ge "$THRESHOLD_15" ]; then
  _emit_once "15" "checkpoint" "CONTEXT WATCHDOG [CHECKPOINT]: ~15% context used (${COUNT} tool calls, ~${USAGE_PCT}%). Create a lightweight checkpoint: current goal, decisions so far, files touched, and next step."
fi

if [ -n "$MESSAGE" ]; then
  printf '%s\n' "$MESSAGE" >&2
fi

# Log at one-shot thresholds or every 10 calls for trend visibility.
if [ "$LEVEL" != "ok" ] || [ "$((COUNT % 10))" -eq 0 ]; then
  printf '{"timestamp":"%s","session_id":"%s","tool_calls":%d,"usage_pct":%d,"level":"%s","threshold_15":%d,"threshold_50":%d,"threshold_70":%d,"threshold_85":%d}\n' \
    "$TIMESTAMP" "${SESSION_ID:-current}" "$COUNT" "$USAGE_PCT" "$LEVEL" "$THRESHOLD_15" "$THRESHOLD_50" "$THRESHOLD_70" "$THRESHOLD_85" >> "$METRICS_FILE" 2>/dev/null || true
fi

exit 0
