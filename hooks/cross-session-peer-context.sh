#!/usr/bin/env bash
# SCOPE: both
# ADR-183: inject compact peer-session awareness on UserPromptSubmit.

set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_lib/context_budget_lib.sh"

if [[ "${DISABLE_HOOK_CROSS_SESSION_PEER_CONTEXT:-0}" == "1" || "${DISABLE_HOOK_CROSS_SESSION_PEER_CONTEXT:-}" == "true" ]]; then
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
from lib.session_bus import peers  # noqa: E402

items = peers(project_dir=project, within_seconds=1800, alive_only=True, current_session_id=session_id, limit=200)[:3]
if not items:
    sys.exit(0)
lines = ["Peer orchestrator sessions detected:"]
for peer in items:
    topics = ", ".join(peer.topic_keywords) if peer.topic_keywords else "unknown"
    writes = ", ".join(peer.recent_writes[:3]) if peer.recent_writes else "no recent write intents"
    branch = peer.branch or "unknown-branch"
    lines.append(f"- session {peer.session_id} on branch {branch}; recent writes: {writes}; topics: {topics}")
lines.append("Coordinate before issuing conflicting ADR/path/policy changes.")
print(json.dumps({"additionalContext": "\n".join(lines)}, ensure_ascii=False))
PY
)"
if [ -n "$CONTEXT_JSON" ]; then
  CONTEXT_JSON="$(context_budget_filter_json "cross-session-peer-context" "$CONTEXT_JSON" "static")"
  [ -n "$CONTEXT_JSON" ] && printf '%s\n' "$CONTEXT_JSON"
fi

exit 0
