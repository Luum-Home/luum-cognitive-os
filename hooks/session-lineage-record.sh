#!/usr/bin/env bash
# SCOPE: os-only
# session-lineage-record.sh — SessionStart hook: write this session's lineage row.
#
# Piece 1 of three. `parent_session_id` was declared in
# cos_lib/hook_event_types.py and appeared in 0 of 27,283 recorded events,
# because nothing wrote it. This is the writer.
#
# The parent comes from COS_PARENT_SESSION_ID, which only a launcher sets. A
# session a human started has no such variable and is recorded with
# parent=null — absent, not guessed. An invented parent would make the chain
# look complete while pointing at the wrong session, which is worse than a
# chain with a visible hole in it.
#
# Depth arrives the same way, in COS_SESSION_DEPTH, incremented by one per
# generation. That is the right vehicle for depth: depth is a property of the
# path, so siblings sharing a value is correct. It is NOT the right vehicle
# for how many sessions exist in total or how many children one parent has —
# those live in the counter file and are enforced by cos_relaunch.py.
#
# Never blocks. Never launches. Writes one line.

set -uo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

if [ "${DISABLE_HOOK_SESSION_LINEAGE_RECORD:-}" = "true" ]; then
  exit 0
fi

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}}"

INPUT="$(cat 2>/dev/null || true)"

SESSION_ID=""
if [ -n "$INPUT" ] && command -v jq >/dev/null 2>&1; then
  SESSION_ID="$(printf '%s' "$INPUT" | jq -r '.session_id // empty' 2>/dev/null || true)"
fi
[ -z "$SESSION_ID" ] && SESSION_ID="${CLAUDE_SESSION_ID:-}"

# No id — record nothing rather than record a placeholder.
[ -z "$SESSION_ID" ] && exit 0

command -v python3 >/dev/null 2>&1 || exit 0

SOURCE="startup"
if [ -n "${COS_PARENT_SESSION_ID:-}" ]; then
  SOURCE="relaunch"
fi

python3 "$PROJECT_DIR/scripts/cos_lineage.py" \
  --project-dir "$PROJECT_DIR" \
  record --session-id "$SESSION_ID" --source "$SOURCE" --quiet \
  >/dev/null 2>&1 || true

exit 0
