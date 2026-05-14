#!/usr/bin/env bash
# SCOPE: os-only
# session-heartbeat.sh — Liveness signal for ADR-047 session lifecycle watchdog.
#
# Fires on: UserPromptSubmit, PreToolUse (matcher: *)
#
# Writes an epoch timestamp to:
#   ${COGNITIVE_OS_SESSION_DIR}/${COGNITIVE_OS_SESSION_ID}/heartbeat
#
# or, if those env vars are absent, falls back to:
#   .cognitive-os/sessions/${SESSION_ID_FALLBACK}/heartbeat
#
# Write is atomic (temp file + mv) — no partial reads by the watchdog.
# Always exits 0 — liveness signal must never block a tool call.
# No stdout — hooks must not pollute context.
#
# Distinct from hooks/state-heartbeat.sh (crash recovery, PostToolUse Agent).
# This hook is ONLY for watchdog liveness detection.

# Source portable helpers for cross-platform stat/date (best-effort — hook
# remains functional even if portable.sh is absent because we only use
# portable_epoch_now which wraps `date +%s`, universally available).
_PORTABLE_LIB="$(dirname "${BASH_SOURCE[0]}")/_lib/portable.sh"
if [ -f "$_PORTABLE_LIB" ]; then
  source "$_PORTABLE_LIB" 2>/dev/null || true
fi

# Determine session directory.
# Priority:
#   1. $COGNITIVE_OS_SESSION_DIR (explicit override)
#   2. ${CLAUDE_PROJECT_DIR}/.cognitive-os/sessions/${COGNITIVE_OS_SESSION_ID}
#   3. ${CLAUDE_PROJECT_DIR:-.}/.cognitive-os/sessions/default  (absolute fallback)
_resolve_session_dir() {
  if [ -n "${COGNITIVE_OS_SESSION_DIR:-}" ]; then
    echo "$COGNITIVE_OS_SESSION_DIR"
    return
  fi

  local project_dir="${CLAUDE_PROJECT_DIR:-.}"
  local session_id="${COGNITIVE_OS_SESSION_ID:-${CLAUDE_SESSION_ID:-default}}"
  echo "${project_dir}/.cognitive-os/sessions/${session_id}"
}

SESSION_DIR="$(_resolve_session_dir)"
HEARTBEAT_FILE="${SESSION_DIR}/heartbeat"

# Get current epoch (uses portable_epoch_now if sourced, else date +%s directly)
if command -v portable_epoch_now >/dev/null 2>&1; then
  NOW="$(portable_epoch_now)"
else
  NOW="$(date +%s)"
fi

# Ensure session directory exists (silent)
mkdir -p "$SESSION_DIR" 2>/dev/null || true

# Atomic write: write to temp file then mv so the watchdog never reads partial content.
TMP_FILE="${SESSION_DIR}/.heartbeat.tmp.$$"
printf '%s\n' "$NOW" > "$TMP_FILE" 2>/dev/null && \
  mv "$TMP_FILE" "$HEARTBEAT_FILE" 2>/dev/null || \
  rm -f "$TMP_FILE" 2>/dev/null || true

exit 0
