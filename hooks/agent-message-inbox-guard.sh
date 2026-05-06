#!/usr/bin/env bash
# SCOPE: both
# Blocks or warns when this session has unacknowledged blocking messages.

set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-${COGNITIVE_OS_PROJECT_DIR:-$(pwd)}}"
SCRIPT="$PROJECT_DIR/scripts/cos_agent_message.py"
[ -f "$SCRIPT" ] || exit 0

MODE="${COS_AGENT_MESSAGE_GUARD_MODE:-warn}"
[ "$MODE" = "off" ] && exit 0

SESSION_ID="${COGNITIVE_OS_SESSION_ID:-${CODEX_SESSION_ID:-${CLAUDE_SESSION_ID:-unknown}}}"
if python3 "$SCRIPT" --project-dir "$PROJECT_DIR" check --session-id "$SESSION_ID" >/tmp/cos-agent-message-guard.out 2>/tmp/cos-agent-message-guard.err; then
  exit 0
fi

cat /tmp/cos-agent-message-guard.err >&2 || true
[ "$MODE" = "block" ] && exit 2
exit 0
