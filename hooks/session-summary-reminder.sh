#!/usr/bin/env bash
# SCOPE: both
# Stop hook: ensures mem_session_summary was called this session.
# If not, blocks the stop and reminds the agent to call it.
# Fires the reminder at most once per session (state file gate).
#
# Detection: queries engram HTTP API (port 7437) for any observation of
# type "session_summary" created today. If found, exits silently.
#
# Harness-agnostic: works in CC and Codex via shared COGNITIVE_OS_* env vars.

set -uo pipefail

# Respect global killswitch (ADR-028 §584)
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-${CODEX_PROJECT_DIR:-$(pwd)}}}"
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-${CLAUDE_SESSION_ID:-${CODEX_SESSION_ID:-}}}"

# No session context — nothing to track. Exit silently.
[ -z "$SESSION_ID" ] && exit 0

STATE_FILE="$PROJECT_DIR/.cognitive-os/sessions/$SESSION_ID/.summary-reminder-fired"

# Already reminded once — let the agent stop on its own this time.
[ -f "$STATE_FILE" ] && exit 0

# Engram daemon must be reachable to verify summary presence.
# If unreachable, exit silently (don't block on infrastructure absence).
curl -sf -m 2 http://127.0.0.1:7437/health >/dev/null 2>&1 || exit 0

PROJECT_NAME=$(basename "$PROJECT_DIR")
TODAY=$(date -u +%Y-%m-%d)

# Search engram for a session_summary observation created today.
# Heuristic: today's date prefix on created_at AND type == session_summary.
RESULT=$(curl -sf -m 5 -G "http://127.0.0.1:7437/search" \
  --data-urlencode "q=session_summary ${PROJECT_NAME}" \
  --data-urlencode "limit=20" 2>/dev/null || echo "[]")

if echo "$RESULT" | python3 -c "
import json, sys
try:
    data = json.loads(sys.stdin.read())
except Exception:
    sys.exit(1)
today = '$TODAY'
items = data if isinstance(data, list) else data.get('results', [])
for obs in items:
    if obs.get('type') == 'session_summary' and str(obs.get('created_at', '')).startswith(today):
        sys.exit(0)
sys.exit(1)
" 2>/dev/null; then
  # Summary already saved today — agent did its job.
  exit 0
fi

# No summary saved this session — fire the reminder once.
mkdir -p "$(dirname "$STATE_FILE")"
touch "$STATE_FILE"

# Block the stop and inject reminder. CC + Codex both accept this JSON shape
# on Stop hooks per the standard hook protocol.
if command -v jq >/dev/null 2>&1; then
  jq -c -n '{
    decision: "block",
    reason: "Session ending without mem_session_summary. Call it now (Goal, Discoveries, Accomplished, Next Steps, Relevant Files). Engram protocol — see rules/engram-help. This reminder fires at most once per session."
  }'
else
  printf '{"decision":"block","reason":"Session ending without mem_session_summary. Call it now (Goal, Discoveries, Accomplished, Next Steps, Relevant Files). Engram protocol. This reminder fires at most once per session."}\n'
fi

exit 0
