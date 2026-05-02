#!/usr/bin/env bash
# SCOPE: both
# concurrent-write-guard-codex-proxy.sh — UserPromptSubmit (prompt) Codex
# projection of hooks/concurrent-write-guard.sh.
#
# WHY THIS EXISTS:
#   Codex v0.126.0-alpha.8 only fires PreToolUse/PostToolUse hooks for the
#   Bash tool (ADR-081, manifests/harness-driver-capabilities.yaml). The
#   concurrent-write-guard fires on PreToolUse[Edit|Write], which Codex does
#   not expose natively. This proxy fires at UserPromptSubmit (Codex "prompt"
#   matcher) and performs a session-scoped stale-lock scan instead of
#   per-file lock acquisition.
#
# WHAT THIS DOES:
#   - Scans LOCKS_DIR for lock files held by other sessions that have NOT
#     expired (younger than LOCK_TIMEOUT and with a live PID).
#   - If cross-session live locks are found, emits a warning to stderr so the
#     agent sees the contention before making any file edits.
#   - Does NOT acquire locks (no file_path is available at prompt time).
#   - Stale lock cleanup is delegated to the per-file guard when running under
#     Claude Code, and to session cleanup hooks.
#
# PORTABILITY NOTE:
#   This is a degraded-but-honest projection.  Claude Code fires the full
#   per-file locking gate; Codex fires this prompt-level scan.  Both provide
#   the visibility guarantee that concurrent session contention is surfaced
#   before edits proceed.  The locking invariant (mutual exclusion per file)
#   is only enforced under Claude Code.  This gap is documented in ADR-111.
#
# BYPASS: COS_ALLOW_CONCURRENT_WRITES=1 (respects same env as full guard)

set -uo pipefail

# Respect killswitch
if [ "${DISABLE_HOOK_CONCURRENT_WRITE_GUARD:-false}" = "true" ]; then
  exit 0
fi
if [ "${COS_ALLOW_CONCURRENT_WRITES:-0}" = "1" ]; then
  exit 0
fi

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"
SESSIONS_DIR="$PROJECT_DIR/.cognitive-os/sessions"
LOCKS_DIR="$SESSIONS_DIR/locks"

# No lock directory — nothing to scan
[ -d "$LOCKS_DIR" ] || exit 0

# Need jq for lock file parsing; skip gracefully if absent
command -v jq &>/dev/null || exit 0

SESSION_ID="${COGNITIVE_OS_SESSION_ID:-${CODEX_SESSION_ID:-${CODEX_THREAD_ID:-}}}"
LOCK_TIMEOUT=300

CONFIG_FILE="$PROJECT_DIR/.cognitive-os/cognitive-os.yaml"
[ -f "$CONFIG_FILE" ] || CONFIG_FILE="$PROJECT_DIR/cognitive-os.yaml"
if [ -f "$CONFIG_FILE" ]; then
  PARSED_TIMEOUT=$(grep 'lock_timeout_seconds:' "$CONFIG_FILE" 2>/dev/null | head -1 \
    | sed 's/.*lock_timeout_seconds:[[:space:]]*//' | tr -d '[:space:]')
  if [[ "${PARSED_TIMEOUT:-}" =~ ^[0-9]+$ ]]; then
    LOCK_TIMEOUT="$PARSED_TIMEOUT"
  fi
fi

NOW=$(date +%s)
LIVE_CONTENTION=0
CONTENTION_DETAILS=""

for lock_file in "$LOCKS_DIR"/*.lock; do
  [ -f "$lock_file" ] || continue

  LOCK_SESSION=$(jq -r '.session_id // empty' "$lock_file" 2>/dev/null)
  LOCK_PID=$(jq -r '.pid // 0' "$lock_file" 2>/dev/null)
  LOCK_TIME=$(jq -r '.timestamp_epoch // 0' "$lock_file" 2>/dev/null)
  LOCK_PATH=$(jq -r '.file_path // "unknown"' "$lock_file" 2>/dev/null)

  # Same session — no contention
  if [ -n "$SESSION_ID" ] && [ "$LOCK_SESSION" = "$SESSION_ID" ]; then
    continue
  fi

  # Check staleness
  LOCK_AGE=$((NOW - LOCK_TIME))
  if [ "$LOCK_AGE" -gt "$LOCK_TIMEOUT" ]; then
    continue
  fi

  # Check if PID is still alive
  if [ "$LOCK_PID" -gt 0 ] && ! kill -0 "$LOCK_PID" 2>/dev/null; then
    continue
  fi

  LIVE_CONTENTION=$((LIVE_CONTENTION + 1))
  CONTENTION_DETAILS="${CONTENTION_DETAILS}  - ${LOCK_PATH} (session: ${LOCK_SESSION}, age: ${LOCK_AGE}s)\n"
done

if [ "$LIVE_CONTENTION" -gt 0 ]; then
  echo "" >&2
  echo "=== CONCURRENT-WRITE-GUARD (Codex proxy): $LIVE_CONTENTION live lock(s) detected ===" >&2
  printf '%b' "$CONTENTION_DETAILS" >&2
  echo "Another session is actively editing these files. Coordinate before proceeding." >&2
  echo "To bypass: COS_ALLOW_CONCURRENT_WRITES=1" >&2
  echo "=== END CONCURRENT-WRITE-GUARD ===" >&2
  # Warning only — Codex cannot block per-file; surfacing the information is the equivalent.
fi

exit 0
