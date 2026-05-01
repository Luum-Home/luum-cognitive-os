#!/usr/bin/env bash
# edit-lock-session-end.sh — ADR-098 Phase C: release this session's edit locks on Stop.
#
# Registered as a Stop hook. Walks .cognitive-os/runtime/edit-locks/ and removes
# every lock owned by the current session_id, so leaks are bounded by session
# lifetime instead of the 30-min TTL.
#
# Idempotent and graceful: missing primitive → no-op exit 0, never blocks
# session cleanup.
set -uo pipefail

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}"
COOP="$PROJECT_DIR/scripts/edit-coop.sh"
[ -x "$COOP" ] || exit 0

bash "$COOP" release-mine 2>&1 \
  | sed 's/^/[edit-lock-session-end] /' >&2 || true

exit 0
