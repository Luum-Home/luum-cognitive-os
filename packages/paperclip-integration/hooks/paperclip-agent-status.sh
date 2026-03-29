#!/usr/bin/env bash
# paperclip-agent-status.sh — Push agent completion status to Paperclip
# Trigger: PostToolUse on Agent
#
# On agent completion, pushes agent status (active/completed/failed) and
# optional heartbeat data to Paperclip dashboard. Fire-and-forget.

_HOOK_NAME="paperclip-agent-status"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
set -uo pipefail

# Read hook input from stdin
INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // ""' 2>/dev/null)
[ "$TOOL_NAME" != "Agent" ] && exit 0

RESPONSE=$(echo "$INPUT" | jq -r '.tool_response // ""' 2>/dev/null)
[ -z "$RESPONSE" ] && exit 0

# Extract agent name from prompt (first 80 chars, sanitized)
AGENT_DESC=$(echo "$INPUT" | jq -r '.tool_input.prompt // ""' 2>/dev/null | head -c 80 | tr -d "'" | tr -d '"' | tr '\n' ' ')
[ -z "$AGENT_DESC" ] && AGENT_DESC="unknown-agent"

# Determine agent status from response
AGENT_STATUS="completed"
if echo "$RESPONSE" | grep -qiE 'FAIL|ERROR|BLOCK|ESCALATION:'; then
  AGENT_STATUS="failed"
fi

# Extract trust score if present
TRUST_SCORE=$(echo "$RESPONSE" | grep -oE 'SCORE=[0-9]+' | head -1 | grep -oE '[0-9]+' || echo "")
[ -z "$TRUST_SCORE" ] && TRUST_SCORE=$(echo "$RESPONSE" | grep -oE 'Score: [0-9]+' | head -1 | grep -oE '[0-9]+' || echo "0")

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
PAPERCLIP_URL="${COGNITIVE_OS_PAPERCLIP_URL:-http://localhost:3200}"

# Fire-and-forget: push to Paperclip in background
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

    heartbeat = {
        'trust_score': int('${TRUST_SCORE}') if '${TRUST_SCORE}'.isdigit() else 0,
        'status': '$AGENT_STATUS',
    }

    client.update_agent_status(
        agent_name='${AGENT_DESC}'[:60],
        status='$AGENT_STATUS',
        heartbeat=heartbeat,
    )
except Exception:
    pass  # Fire-and-forget
" 2>/dev/null
) &

exit 0
