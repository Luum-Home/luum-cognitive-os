#!/usr/bin/env bash
# paperclip-task-sync.sh — Push active tasks to Paperclip as issues on session start
# Trigger: SessionStart
#
# Reads .claude/tasks/active-tasks.json and pushes in_progress/pending tasks
# to Paperclip as issues. One-directional: COS -> Paperclip only.
# Fire-and-forget — never blocks session startup.

_HOOK_NAME="paperclip-task-sync"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
set -uo pipefail

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
PAPERCLIP_URL="${COGNITIVE_OS_PAPERCLIP_URL:-http://localhost:3200}"
TASKS_FILE="$PROJECT_DIR/.claude/tasks/active-tasks.json"

# No tasks file? Skip silently.
[ -f "$TASKS_FILE" ] || exit 0
[ -s "$TASKS_FILE" ] || exit 0

# Check if Paperclip is available (quick check, skip if not)
if ! curl -s --connect-timeout 2 "$PAPERCLIP_URL/api/health" >/dev/null 2>&1; then
  exit 0
fi

# Fire-and-forget: sync in background
(
  python3 -c "
import sys, os, json
sys.path.insert(0, '$PROJECT_DIR/lib')
os.environ.setdefault('COGNITIVE_OS_PAPERCLIP_URL', '$PAPERCLIP_URL')

try:
    from paperclip_client import PaperclipClient
    client = PaperclipClient()
    if not client.is_available():
        sys.exit(0)

    with open('$TASKS_FILE', 'r') as f:
        data = json.load(f)

    tasks = data.get('tasks', [])
    synced = 0
    for task in tasks:
        status = task.get('status', '')
        if status not in ('in_progress', 'pending'):
            continue
        task_id = task.get('id', 'unknown')
        desc = task.get('description', task_id)

        # Map COS task status to Paperclip issue status
        pc_status = 'in_progress' if status == 'in_progress' else 'open'

        client.create_issue(
            project_id='cos-session',
            title='Task: %s' % str(desc)[:80],
            description='COS Task ID: %s, Status: %s' % (task_id, status),
        )
        synced += 1
        if synced >= 20:  # Cap to avoid flooding
            break

except Exception:
    pass  # Fire-and-forget
" 2>/dev/null
) &

exit 0
