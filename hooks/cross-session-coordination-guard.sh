#!/usr/bin/env bash
# SCOPE: both
# Guard high-risk multi-session operations with a shared coordination ledger.

set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-${COGNITIVE_OS_PROJECT_DIR:-$(pwd)}}"
SCRIPT="$PROJECT_DIR/scripts/cos_session_coordination.py"

[ -f "$SCRIPT" ] || exit 0

MODE="${COS_SESSION_COORDINATION_MODE:-warn}"
STRICT_FLAG=()
[ "$MODE" = "block" ] && STRICT_FLAG=(--require-worktree-intake)
[ "$MODE" != "block" ] && STRICT_FLAG=(--require-worktree-intake --warn-only)

if python3 "$SCRIPT" --project-dir "$PROJECT_DIR" check "${STRICT_FLAG[@]}" >/tmp/cos-session-coordination-guard.out 2>/tmp/cos-session-coordination-guard.err; then
  [ "$MODE" = "off" ] && exit 0
  if [ -s /tmp/cos-session-coordination-guard.out ] && [ "${COS_SESSION_COORDINATION_VERBOSE:-0}" = "1" ]; then
    cat /tmp/cos-session-coordination-guard.out >&2
  fi
  exit 0
fi

cat /tmp/cos-session-coordination-guard.err >&2 || true
if [ "$MODE" = "block" ]; then
  exit 2
fi
exit 0
