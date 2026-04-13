#!/usr/bin/env bash
# SCOPE: both
# Hook: agent-work-tracker
# Events: PreToolUse (Agent), PostToolUse (Agent)
# Purpose: Track agent tasks in persistent work queue so the next session
#          knows exactly what was running and what was completed.
#
# Fires on the Agent tool for both pre and post events.
# On PreToolUse: enqueue the task with status "pending".
# On PostToolUse: mark the task as completed (or leave as pending if no match).
#
# Must complete in <500ms — exits 0 always (advisory, never blocks).

set -uo pipefail

# Read hook input from stdin
INPUT=$(cat)
[ -z "$INPUT" ] && exit 0

# Require jq
command -v jq &>/dev/null || exit 0

TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // ""' 2>/dev/null)
[ "$TOOL_NAME" = "Agent" ] || exit 0

EVENT=$(echo "$INPUT" | jq -r '.event // ""' 2>/dev/null)

PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"

if [ "$EVENT" = "PreToolUse" ]; then
    # Extract agent description — prefer .tool_input.description, fallback to first 200 chars of prompt
    DESCRIPTION=$(echo "$INPUT" | jq -r '
        (.tool_input.description // (.tool_input.prompt // "unknown task" | .[0:200]))
    ' 2>/dev/null)
    [ -z "$DESCRIPTION" ] || [ "$DESCRIPTION" = "null" ] && DESCRIPTION="unknown task"

    # Generate a stable task ID: timestamp + truncated description slug
    SLUG=$(echo "$DESCRIPTION" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | cut -c1-40 | sed 's/-*$//')
    TASK_ID="agent-$(date +%s)-${SLUG}"

    python3 - <<PYEOF 2>/dev/null || true
import sys, os
sys.path.insert(0, '$PROJECT_ROOT')
from lib.work_queue import WorkQueue
q = WorkQueue(queue_path='$PROJECT_ROOT/.cognitive-os/work-queue.json')
q.add_task(
    task_id='$TASK_ID',
    description='''$DESCRIPTION''',
    priority=5,
    context='auto-tracked by agent-work-tracker hook',
)
PYEOF

elif [ "$EVENT" = "PostToolUse" ]; then
    # Extract the description to find the matching task
    DESCRIPTION=$(echo "$INPUT" | jq -r '
        (.tool_input.description // (.tool_input.prompt // "unknown task" | .[0:200]))
    ' 2>/dev/null)
    [ -z "$DESCRIPTION" ] || [ "$DESCRIPTION" = "null" ] && DESCRIPTION="unknown task"

    SLUG=$(echo "$DESCRIPTION" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | cut -c1-40 | sed 's/-*$//')

    # Extract a summary from the tool response (first 300 chars)
    SUMMARY=$(echo "$INPUT" | jq -r '.tool_response // "" | .[0:300]' 2>/dev/null || true)

    python3 - <<PYEOF 2>/dev/null || true
import sys, os, re
sys.path.insert(0, '$PROJECT_ROOT')
from lib.work_queue import WorkQueue
q = WorkQueue(queue_path='$PROJECT_ROOT/.cognitive-os/work-queue.json')

# Find the most recent pending task whose ID contains our slug
slug = '$SLUG'
summary = '''$SUMMARY'''
data = q._data
pending = [
    t for t in data.get('priority_queue', [])
    if t.get('status') == 'pending' and slug in t.get('id', '')
]
if pending:
    # Sort by added_at descending, complete the latest
    pending.sort(key=lambda t: t.get('added_at', ''), reverse=True)
    q.complete_task(pending[0]['id'], summary=summary[:200] if summary else '')
PYEOF
fi

exit 0
