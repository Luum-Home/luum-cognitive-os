#!/usr/bin/env bash
# SCOPE: both
# edit-lock-pre-tool.sh — ADR-098 PreToolUse[Edit|Write] enforcement
#
# Reads the tool input JSON from stdin, extracts the target file_path, and
# asks scripts/edit-coop.sh whether this session can edit it. If another
# session holds the lock with intent=exclusive-edit, exits 2 with a structured
# message that tells the agent what to do (park / negotiate / escalate).
#
# Self-acquires a lock on first edit by this session in this conversation.
# The lock is released by edit-lock-session-end.sh on session end.
#
# Bypass:
#   COS_BYPASS_EDIT_LOCK=1   — skip entirely (emergency only).
#
# Latency target: <30ms in uncontended case (own lock or no lock).
set -uo pipefail

[ "${COS_BYPASS_EDIT_LOCK:-}" = "1" ] && exit 0

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}"
COOP="$PROJECT_DIR/scripts/edit-coop.sh"
[ -x "$COOP" ] || exit 0   # graceful: missing primitive → no enforcement

# Read tool input JSON from stdin.
input="$(cat 2>/dev/null || true)"
[ -z "$input" ] && exit 0

# Extract file_path field. PreToolUse JSON shape is {"tool_input":{"file_path":"..."}}.
file_path="$(printf '%s' "$input" | python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)
ti = data.get("tool_input") or {}
fp = ti.get("file_path") or ti.get("path") or ""
if fp:
    print(fp)
' 2>/dev/null)"

[ -z "$file_path" ] && exit 0

# Normalize to repo-relative path.
case "$file_path" in
  "$PROJECT_DIR"/*) rel="${file_path#$PROJECT_DIR/}" ;;
  /*) rel="$file_path" ;;
  *) rel="$file_path" ;;
esac

# Try to acquire (idempotent on re-acquire by same session).
out="$("$COOP" acquire "$rel" \
  "${COS_EDIT_PURPOSE:-tool-edit}" \
  "${COS_EDIT_INTENT:-exclusive-edit}" 2>&1)"
status=$?

if [ "$status" -eq 0 ]; then
  exit 0
fi

# Conflict — read meta to give the structured response.
meta="$PROJECT_DIR/.cognitive-os/runtime/edit-locks/$(printf '%s' "$rel" | sed 's|/|--|g; s|\.\.||g')/meta.yaml"
holder="unknown"
purpose="unknown"
since="unknown"
intent="unknown"
heartbeat="unknown"
if [ -f "$meta" ]; then
  holder=$(sed -n 's/^session_id: *"\(.*\)"$/\1/p' "$meta" | head -1)
  purpose=$(sed -n 's/^purpose: *"\(.*\)"$/\1/p' "$meta" | head -1)
  since=$(sed -n 's/^since: *"\(.*\)"$/\1/p' "$meta" | head -1)
  intent=$(sed -n 's/^intent: *"\(.*\)"$/\1/p' "$meta" | head -1)
  heartbeat=$(sed -n 's/^heartbeat: *"\(.*\)"$/\1/p' "$meta" | head -1)
fi

cat >&2 <<EOF
EDIT-LOCK CONFLICT on $rel (ADR-098)
  Held by:    session=$holder
  Intent:     $intent
  Since:      $since   (heartbeat: $heartbeat)
  Purpose:    $purpose

What to do (response protocol):
  1. PARK        — save your edit to .cognitive-os/runtime/parked-edits/<your-session>/<file>.json
                   and continue with non-conflicting work. Apply when lock releases.
  2. READ-ONLY   — read $rel to inform your work, edit a DIFFERENT file instead.
  3. NEGOTIATE   — write a request to .cognitive-os/runtime/edit-negotiations/<their-session>/<your-session>.yaml
                   describing what you need; the holder reads on its next heartbeat.
  4. ESCALATE    — only if you have priority "critical-bugfix"; set
                   COS_BYPASS_EDIT_LOCK=1 and proceed (audit trail logged).

Inspect all active locks with:
  bash scripts/edit-coop.sh status
EOF
exit 2
