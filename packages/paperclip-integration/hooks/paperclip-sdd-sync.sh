#!/usr/bin/env bash
# paperclip-sdd-sync.sh — Sync SDD pipeline phase transitions to Paperclip
# Trigger: PostToolUse on Agent
#
# When SDD phases transition (apply, verify, archive), creates/updates
# Paperclip issues to reflect pipeline state. Fire-and-forget (async).

_HOOK_NAME="paperclip-sdd-sync"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
set -uo pipefail

# Read hook input from stdin
INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // ""' 2>/dev/null)
[ "$TOOL_NAME" != "Agent" ] && exit 0

RESPONSE=$(echo "$INPUT" | jq -r '.tool_response // ""' 2>/dev/null)
[ -z "$RESPONSE" ] && exit 0

# Detect SDD phase transitions in agent output
SDD_PHASE=""
SDD_STATUS=""

if echo "$RESPONSE" | grep -qiE 'sdd-apply.*complet|apply phase.*done|PROGRESS.*apply.*complet'; then
  SDD_PHASE="sdd-apply"
  SDD_STATUS="done"
elif echo "$RESPONSE" | grep -qiE 'sdd-apply|apply phase|sdd_apply'; then
  SDD_PHASE="sdd-apply"
  SDD_STATUS="in_progress"
fi

if echo "$RESPONSE" | grep -qiE 'sdd-verify.*complet|verify phase.*done|PROGRESS.*verify.*complet'; then
  SDD_PHASE="sdd-verify"
  SDD_STATUS="done"
elif echo "$RESPONSE" | grep -qiE 'sdd-verify|verify phase|sdd_verify'; then
  SDD_PHASE="sdd-verify"
  SDD_STATUS="${SDD_STATUS:-in_progress}"
fi

if echo "$RESPONSE" | grep -qiE 'sdd-archive.*complet|archive phase.*done'; then
  SDD_PHASE="sdd-archive"
  SDD_STATUS="done"
elif echo "$RESPONSE" | grep -qiE 'sdd-archive|archive phase'; then
  SDD_PHASE="sdd-archive"
  SDD_STATUS="${SDD_STATUS:-in_progress}"
fi

# Also detect FAIL/BLOCK
if echo "$RESPONSE" | grep -qiE 'FAIL.*CRITICAL|BLOCK|verify.*failed'; then
  SDD_STATUS="blocked"
fi

# Nothing detected, exit silently
[ -z "$SDD_PHASE" ] && exit 0

# Extract change name from prompt if possible
TASK_DESC=$(echo "$INPUT" | jq -r '.tool_input.prompt // ""' 2>/dev/null | head -c 300)
CHANGE_NAME=$(echo "$TASK_DESC" | grep -oE 'change[: ]+[a-z0-9_-]+' | head -1 | sed 's/change[: ]*//' || echo "")
[ -z "$CHANGE_NAME" ] && CHANGE_NAME="unknown-change"

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
PAPERCLIP_URL="${COGNITIVE_OS_PAPERCLIP_URL:-http://localhost:3200}"

# Fire-and-forget: push to Paperclip in background, never block
(
  python3 -c "
import sys, os
sys.path.insert(0, '$PROJECT_DIR/lib')
sys.path.insert(0, '$PROJECT_DIR/packages/ecosystem-tools/lib')
os.environ.setdefault('COGNITIVE_OS_PAPERCLIP_URL', '$PAPERCLIP_URL')

try:
    from paperclip_client import PaperclipClient
    client = PaperclipClient()
    if not client.is_available():
        sys.exit(0)

    phase = '$SDD_PHASE'
    status = '$SDD_STATUS'
    change = '$CHANGE_NAME'

    # Create or update issue for this SDD phase
    title = '%s: %s' % (phase, change)
    desc = 'SDD pipeline phase %s for change %s. Status: %s' % (phase, change, status)

    if status == 'in_progress':
        result = client.create_issue(
            project_id=change,
            title=title,
            description=desc,
            assignee=phase + '-agent',
        )
        issue_id = result.get('id', '')
        if issue_id:
            client.update_issue_status(issue_id, 'in_progress')
    elif status in ('done', 'blocked'):
        # Try to update existing; if no issue_id available, push notification instead
        client.push_notification(
            title='%s: %s' % (phase, status.upper()),
            body='Change: %s' % change,
            severity='info' if status == 'done' else 'warning',
        )
except Exception:
    pass  # Fire-and-forget: never fail the hook
" 2>/dev/null
) &

# Log the detection
METRICS_DIR="$(_resolve_metrics_dir)"
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
ENTRY=$(jq -cn \
  --arg ts "$TIMESTAMP" \
  --arg phase "$SDD_PHASE" \
  --arg status "$SDD_STATUS" \
  --arg change "$CHANGE_NAME" \
  '{timestamp: $ts, phase: $phase, status: $status, change: $change}')
safe_jsonl_append "$METRICS_DIR/paperclip-sdd-sync.jsonl" "$ENTRY"

exit 0
