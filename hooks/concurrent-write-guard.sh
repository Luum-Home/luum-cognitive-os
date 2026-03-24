#!/usr/bin/env bash
# PreToolUse hook: Advisory file locking for concurrent sessions
# Fires on Edit|Write — checks if another session has a lock on the target file.
# Advisory only: warns but does NOT block (no DENY).
# Lock auto-expires after 5 minutes (configurable via cognitive-os.yaml).
# Must complete in <2 seconds.

set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
SESSIONS_DIR="$PROJECT_DIR/.cognitive-os/sessions"
LOCKS_DIR="$SESSIONS_DIR/locks"

# Read tool input from stdin
INPUT=$(cat)

# Exit early if no input or no jq
if [ -z "$INPUT" ]; then exit 0; fi
if ! command -v jq &>/dev/null; then exit 0; fi

# Extract file path from tool input
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.path // empty' 2>/dev/null)
[ -z "$FILE_PATH" ] && exit 0

# Resolve session ID
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-}"
if [ -z "$SESSION_ID" ]; then
  SESSION_FILE="$SESSIONS_DIR/.current-session-$$"
  if [ -f "$SESSION_FILE" ]; then
    SESSION_ID=$(cat "$SESSION_FILE" 2>/dev/null)
  fi
fi

# If no session tracking, skip locking
[ -z "$SESSION_ID" ] && exit 0

# Read lock timeout from config (default 300 seconds = 5 minutes)
LOCK_TIMEOUT=300
CONFIG_FILE="$PROJECT_DIR/.cognitive-os/cognitive-os.yaml"
if [ -f "$CONFIG_FILE" ]; then
  PARSED_TIMEOUT=$(grep 'lock_timeout_seconds:' "$CONFIG_FILE" 2>/dev/null | head -1 | sed 's/.*lock_timeout_seconds:[[:space:]]*//' | tr -d '[:space:]')
  if [[ "$PARSED_TIMEOUT" =~ ^[0-9]+$ ]]; then
    LOCK_TIMEOUT="$PARSED_TIMEOUT"
  fi
fi

# Create lock directory
mkdir -p "$LOCKS_DIR"

# Generate a stable hash for the file path
if command -v md5 &>/dev/null; then
  FILE_HASH=$(echo -n "$FILE_PATH" | md5)
elif command -v md5sum &>/dev/null; then
  FILE_HASH=$(echo -n "$FILE_PATH" | md5sum | cut -d' ' -f1)
else
  # Fallback: use base64-encoded path (truncated)
  FILE_HASH=$(echo -n "$FILE_PATH" | base64 | tr -d '=/+' | head -c 32)
fi

LOCK_FILE="$LOCKS_DIR/${FILE_HASH}.lock"

NOW=$(date +%s)

# --- Check existing lock ---
if [ -f "$LOCK_FILE" ]; then
  LOCK_SESSION=$(jq -r '.session_id // empty' "$LOCK_FILE" 2>/dev/null)
  LOCK_PID=$(jq -r '.pid // 0' "$LOCK_FILE" 2>/dev/null)
  LOCK_TIME=$(jq -r '.timestamp_epoch // 0' "$LOCK_FILE" 2>/dev/null)
  LOCK_PATH=$(jq -r '.file_path // empty' "$LOCK_FILE" 2>/dev/null)

  # Same session — allow and refresh lock
  if [ "$LOCK_SESSION" = "$SESSION_ID" ]; then
    # Refresh lock timestamp
    jq --argjson now "$NOW" '.timestamp_epoch = $now | .timestamp = (now | strftime("%Y-%m-%dT%H:%M:%SZ"))' \
       "$LOCK_FILE" > "$LOCK_FILE.tmp" 2>/dev/null && mv "$LOCK_FILE.tmp" "$LOCK_FILE"
    exit 0
  fi

  # Check if lock is stale (expired or PID dead)
  LOCK_AGE=$((NOW - LOCK_TIME))
  IS_STALE=false

  if [ "$LOCK_AGE" -gt "$LOCK_TIMEOUT" ]; then
    IS_STALE=true
  fi

  # Check if locking PID is still running
  if [ "$LOCK_PID" -gt 0 ] && ! kill -0 "$LOCK_PID" 2>/dev/null; then
    IS_STALE=true
  fi

  if [ "$IS_STALE" = true ]; then
    # Remove stale lock, proceed to acquire
    rm -f "$LOCK_FILE"
  else
    # --- ADVISORY WARNING: Another session holds the lock ---
    SHORT_PATH=$(basename "$FILE_PATH")
    echo ""
    echo "=== CONCURRENT WRITE WARNING ==="
    echo "File: $FILE_PATH"
    echo "Currently being edited by session: $LOCK_SESSION"
    echo "Lock age: ${LOCK_AGE}s (expires after ${LOCK_TIMEOUT}s)"
    echo ""
    echo "This is an advisory warning. The write will proceed, but be aware"
    echo "that another session may overwrite your changes."
    echo "=== END WARNING ==="
    echo ""
    # Do NOT deny — advisory only
  fi
fi

# --- Acquire/refresh lock for this session ---
jq -n \
  --arg sid "$SESSION_ID" \
  --arg pid "$$" \
  --arg path "$FILE_PATH" \
  --argjson epoch "$NOW" \
  --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  '{session_id: $sid, pid: ($pid | tonumber), file_path: $path, timestamp_epoch: $epoch, timestamp: $ts}' \
  > "$LOCK_FILE" 2>/dev/null

exit 0
