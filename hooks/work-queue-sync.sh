#!/usr/bin/env bash
# SCOPE: os-only
# CONCERNS: task-tracking, observability
# work-queue-sync.sh — PostToolUse hook for TodoWrite and Agent
# Appends task events to .cognitive-os/work-queue.jsonl so every todo write
# and agent completion is captured in the canonical work queue log.
# ADR-033 canonical event format.

set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="work-queue-sync"
source "$(dirname "$0")/_lib/safe-jsonl.sh"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
WORK_QUEUE_LOG="$PROJECT_DIR/.cognitive-os/work-queue.jsonl"

# Ensure metrics dir exists
mkdir -p "$(dirname "$WORK_QUEUE_LOG")"

# Read hook input
INPUT="$(cat)"

TOOL_NAME="${CLAUDE_TOOL_NAME:-unknown}"
TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
EPOCH="$(date +%s)"

# ── Determine event type ───────────────────────────────────────────────────
if [[ "$TOOL_NAME" == "TodoWrite" ]]; then
    EVENT_TYPE="todo_write"
    # Extract todo count from input if possible
    TODO_COUNT="$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    todos = data.get('todos', data) if isinstance(data, dict) else data
    print(len(todos) if isinstance(todos, list) else 0)
except Exception:
    print(0)
" 2>/dev/null || echo "0")"
    DETAIL="{\"todo_count\": $TODO_COUNT}"
elif [[ "$TOOL_NAME" == "Agent" ]]; then
    EVENT_TYPE="agent_completion"
    # Try to extract agent result summary (first 200 chars)
    SUMMARY="$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    result = data.get('result', '')
    print(str(result)[:200].replace('\"', '\\\\\"').replace('\n', ' '))
except Exception:
    print('')
" 2>/dev/null || echo "")"
    DETAIL="{\"summary\": \"$SUMMARY\"}"
else
    # Unexpected — still log but with unknown type
    EVENT_TYPE="unknown_tool"
    DETAIL="{}"
fi

# ── Build JSONL record ─────────────────────────────────────────────────────
RECORD="{\"timestamp\": \"$TIMESTAMP\", \"epoch\": $EPOCH, \"event\": \"$EVENT_TYPE\", \"tool\": \"$TOOL_NAME\", \"detail\": $DETAIL, \"source\": \"$_HOOK_NAME\"}"

# Append (safe-jsonl handles concurrent writes if available, else direct append)
if declare -f safe_jsonl_append &>/dev/null; then
    safe_jsonl_append "$WORK_QUEUE_LOG" "$RECORD"
else
    echo "$RECORD" >> "$WORK_QUEUE_LOG"
fi

exit 0
