#!/usr/bin/env bash
# SCOPE: both
# Context Watchdog — estimates context usage and warns at thresholds
# Type: PostToolUse
# Matcher: (none — fires on ALL tools)
#
# Logic:
#   - Counts tool calls in .cognitive-os/sessions/current/tool-call-count
#   - ~750 tokens per tool call average, 200K usable context
#   - 130 calls (~50%): log INFO to metrics only (silent)
#   - 185 calls (~70%): WARNING to stderr — save to engram now
#   - 225 calls (~85%): URGENT to stderr — split session
#
# Must be fast (<50ms) and always exits 0.
set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
SESSION_DIR="$PROJECT_DIR/.cognitive-os/sessions/current"
COUNTER_FILE="$SESSION_DIR/tool-call-count"
METRICS_FILE="$PROJECT_DIR/.cognitive-os/metrics/context-watchdog.jsonl"

# Thresholds (tool call counts)
THRESHOLD_50=130
THRESHOLD_70=185
THRESHOLD_85=225

# Ensure dirs exist
mkdir -p "$SESSION_DIR" 2>/dev/null || true
mkdir -p "$(dirname "$METRICS_FILE")" 2>/dev/null || true

# Read current count, increment, write back
COUNT=0
if [ -f "$COUNTER_FILE" ]; then
    COUNT=$(cat "$COUNTER_FILE" 2>/dev/null) || COUNT=0
    case "$COUNT" in
        ''|*[!0-9]*) COUNT=0 ;;
    esac
fi
COUNT=$((COUNT + 1))
printf '%d' "$COUNT" > "$COUNTER_FILE"

# Estimate usage percentage (200K context / 750 tokens per call = 267 calls max)
USAGE_PCT=$(( (COUNT * 100) / 267 ))

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

LEVEL="ok"

if [ "$COUNT" -ge "$THRESHOLD_85" ]; then
    LEVEL="urgent"
    echo "CONTEXT WATCHDOG [URGENT]: ~85% context used (${COUNT} tool calls, ~${USAGE_PCT}%)." >&2
    echo "  STOP new work. Save session state to Engram now, then inform user." >&2
    echo "  Call mem_session_summary before context is compacted." >&2
elif [ "$COUNT" -ge "$THRESHOLD_70" ]; then
    LEVEL="warning"
    echo "CONTEXT WATCHDOG [WARNING]: ~70% context used (${COUNT} tool calls, ~${USAGE_PCT}%)." >&2
    echo "  Save decisions, bugs, and discoveries to Engram immediately." >&2
    echo "  Reduce verbosity. Avoid large file reads. Plan wrap-up." >&2
elif [ "$COUNT" -ge "$THRESHOLD_50" ]; then
    LEVEL="info"
fi

# Log to metrics at thresholds or every 10 calls
if [ "$LEVEL" != "ok" ] || [ "$((COUNT % 10))" -eq 0 ]; then
    printf '{"timestamp":"%s","tool_calls":%d,"usage_pct":%d,"level":"%s"}\n' \
        "$TIMESTAMP" "$COUNT" "$USAGE_PCT" "$LEVEL" >> "$METRICS_FILE" 2>/dev/null || true
fi

exit 0
