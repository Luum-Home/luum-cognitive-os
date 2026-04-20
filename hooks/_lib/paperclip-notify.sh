#!/usr/bin/env bash
# SCOPE: both
# paperclip-notify.sh — Shared helper for fire-and-forget Paperclip notifications
#
# Usage:
#   source "$(dirname "$0")/_lib/paperclip-notify.sh"
#   paperclip_notify "Safety Mesh BLOCK" "Hook: completion-gate, Reason: criteria failed" "warning"
#   paperclip_update_issue_status "issue-123" "blocked"
#   paperclip_push_spend 0.15 "sonnet" 5000
#   paperclip_push_tasks_as_issues
#
# All functions are fire-and-forget: they run in background subshells,
# never block the caller, and silently swallow errors.

_PAPERCLIP_PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
_PAPERCLIP_URL="${COGNITIVE_OS_PAPERCLIP_URL:-http://localhost:3200}"

# ADR-028 D1.B — register a background PID with process_registry (silent no-op if
# python3 unavailable or registry import fails).
_paperclip_register_bg() {
  local _pid="$1" _owner="$2"
  local _py
  _py=$(command -v python3 || true)
  [ -z "$_py" ] && return 0
  (
    COGNITIVE_OS_PROJECT_DIR="$_PAPERCLIP_PROJECT_DIR" \
      "$_py" - "$_pid" "$_owner" <<'PYEOF' >/dev/null 2>&1
import sys, os
root = os.environ.get("COGNITIVE_OS_PROJECT_DIR") or os.getcwd()
sys.path.insert(0, root)
try:
    import lib.process_registry as process_registry
    process_registry.register(int(sys.argv[1]), sys.argv[2], 30, "short_lived")
except Exception:
    pass
PYEOF
  ) &
}

# paperclip_notify <title> <body> <severity>
# Pushes a notification to the Paperclip inbox.
# severity: info | warning | critical
paperclip_notify() {
  local title="${1:-}" body="${2:-}" severity="${3:-info}"
  [ -z "$title" ] && return 0

  (
    python3 -c "
import sys, os
sys.path.insert(0, '$_PAPERCLIP_PROJECT_DIR/lib')
os.environ.setdefault('COGNITIVE_OS_PAPERCLIP_URL', '$_PAPERCLIP_URL')
try:
    from paperclip_client import PaperclipClient
    client = PaperclipClient()
    if client.is_available():
        client.push_notification('''$title''', '''$body''', '$severity')
except Exception:
    pass
" 2>/dev/null
  ) &
  _paperclip_register_bg $! "paperclip-notify"
}

# paperclip_update_issue_status <issue_id> <status>
# Updates an issue status in Paperclip.
# status: open | in_progress | blocked | done
paperclip_update_issue_status() {
  local issue_id="${1:-}" status="${2:-}"
  [ -z "$issue_id" ] || [ -z "$status" ] && return 0

  (
    python3 -c "
import sys, os
sys.path.insert(0, '$_PAPERCLIP_PROJECT_DIR/lib')
os.environ.setdefault('COGNITIVE_OS_PAPERCLIP_URL', '$_PAPERCLIP_URL')
try:
    from paperclip_client import PaperclipClient
    client = PaperclipClient()
    if client.is_available():
        client.update_issue_status('$issue_id', '$status')
except Exception:
    pass
" 2>/dev/null
  ) &
  _paperclip_register_bg $! "paperclip-update-issue"
}

# paperclip_push_spend <amount_usd> <model> <tokens>
# Pushes a cost data point to Paperclip spend tracker.
paperclip_push_spend() {
  local amount="${1:-0}" model="${2:-unknown}" tokens="${3:-0}"

  (
    python3 -c "
import sys, os
sys.path.insert(0, '$_PAPERCLIP_PROJECT_DIR/lib')
os.environ.setdefault('COGNITIVE_OS_PAPERCLIP_URL', '$_PAPERCLIP_URL')
try:
    from paperclip_client import PaperclipClient
    client = PaperclipClient()
    if client.is_available():
        client.push_spend(float('$amount'), '$model', int('$tokens'))
except Exception:
    pass
" 2>/dev/null
  ) &
  _paperclip_register_bg $! "paperclip-push-spend"
}

# paperclip_push_tasks_as_issues
# Reads active-tasks.json and pushes in_progress tasks as Paperclip issues.
paperclip_push_tasks_as_issues() {
  local tasks_file="$_PAPERCLIP_PROJECT_DIR/.claude/tasks/active-tasks.json"
  [ -f "$tasks_file" ] || return 0

  (
    python3 -c "
import sys, os, json
sys.path.insert(0, '$_PAPERCLIP_PROJECT_DIR/lib')
os.environ.setdefault('COGNITIVE_OS_PAPERCLIP_URL', '$_PAPERCLIP_URL')
try:
    from paperclip_client import PaperclipClient
    client = PaperclipClient()
    if not client.is_available():
        sys.exit(0)

    with open('$tasks_file', 'r') as f:
        data = json.load(f)

    tasks = data.get('tasks', [])
    for task in tasks:
        status = task.get('status', '')
        if status not in ('in_progress', 'pending'):
            continue
        task_id = task.get('id', 'unknown')
        desc = task.get('description', task_id)
        # Create issue using task id as title prefix for traceability
        client.create_issue(
            project_id='cos-session',
            title='Task: %s' % desc[:80],
            description='Status: %s. Task ID: %s' % (status, task_id),
        )
except Exception:
    pass
" 2>/dev/null
  ) &
  _paperclip_register_bg $! "paperclip-push-tasks"
}
