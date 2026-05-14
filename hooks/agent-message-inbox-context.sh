#!/usr/bin/env bash
# SCOPE: os-only
# ADR-185: inject pending directed agent messages on UserPromptSubmit.

set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_lib/context_budget_lib.sh"

if [[ "${DISABLE_HOOK_AGENT_MESSAGE_INBOX_CONTEXT:-0}" == "1" || "${DISABLE_HOOK_AGENT_MESSAGE_INBOX_CONTEXT:-}" == "true" ]]; then
  exit 0
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${COGNITIVE_OS_PROJECT_DIR:-$(pwd)}}"
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COS_ROOT="$(cd "$HOOK_DIR/.." && pwd)"
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-${CODEX_SESSION_ID:-${CLAUDE_SESSION_ID:-unknown}}}"

CONTEXT_JSON="$(python3 - "$PROJECT_DIR" "$SESSION_ID" "$COS_ROOT" <<'PY' 2>/dev/null || true
from __future__ import annotations

import json
import sys
from pathlib import Path

project = Path(sys.argv[1]).resolve()
session_id = sys.argv[2]
cos_root = Path(sys.argv[3]).resolve()
sys.path.insert(0, str(cos_root))
from lib.agent_message_bus import inbox  # noqa: E402

rows = inbox(project, session_id=session_id)[:5]
if not rows:
    sys.exit(0)
lines = ["Pending directed agent messages:"]
for row in rows:
    mid = str(row.get("message_id", ""))[:8]
    sev = row.get("severity")
    sender = row.get("from_session")
    target = row.get("target") or "general"
    body = str(row.get("body") or "")[:160]
    lines.append(f"- {mid} [{sev}] from={sender} target={target}: {body}")
lines.append("Acknowledge with scripts/cos-agent-message ack after applying/triaging.")
print(json.dumps({"additionalContext": "\n".join(lines)}, ensure_ascii=False))
PY
)"
if [ -n "$CONTEXT_JSON" ]; then
  CONTEXT_JSON="$(context_budget_filter_json "agent-message-inbox-context" "$CONTEXT_JSON" "static")"
  [ -n "$CONTEXT_JSON" ] && printf '%s\n' "$CONTEXT_JSON"
fi

exit 0
