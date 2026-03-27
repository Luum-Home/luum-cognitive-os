#!/usr/bin/env bash
# Stop hook: Clean up session on exit
# Removes session from active-sessions.json, merges metrics, optionally cleans up directory.
# Must complete in <10 seconds.

set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
SESSIONS_DIR="$PROJECT_DIR/.cognitive-os/sessions"
ACTIVE_FILE="$SESSIONS_DIR/active-sessions.json"
GLOBAL_METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"

# Resolve session ID: env var > file-based discovery
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-}"
if [ -z "$SESSION_ID" ]; then
  # Try to find session file for this PID
  SESSION_FILE="$SESSIONS_DIR/.current-session-$$"
  if [ -f "$SESSION_FILE" ]; then
    SESSION_ID=$(cat "$SESSION_FILE" 2>/dev/null)
  fi
fi

# If no session, nothing to clean up
if [ -z "$SESSION_ID" ]; then
  exit 0
fi

SESSION_DIR="$SESSIONS_DIR/$SESSION_ID"

# Read cleanup config from cognitive-os.yaml
CLEANUP_ON_EXIT=true
MERGE_METRICS=true
CONFIG_FILE="$PROJECT_DIR/.cognitive-os/cognitive-os.yaml"
if [ -f "$CONFIG_FILE" ]; then
  PARSED_CLEANUP=$(grep 'cleanup_on_exit:' "$CONFIG_FILE" 2>/dev/null | head -1 | sed 's/.*cleanup_on_exit:[[:space:]]*//' | tr -d '[:space:]')
  [ "$PARSED_CLEANUP" = "false" ] && CLEANUP_ON_EXIT=false
  PARSED_MERGE=$(grep 'merge_metrics_on_exit:' "$CONFIG_FILE" 2>/dev/null | head -1 | sed 's/.*merge_metrics_on_exit:[[:space:]]*//' | tr -d '[:space:]')
  [ "$PARSED_MERGE" = "false" ] && MERGE_METRICS=false
fi

# --- Step 1: Merge session metrics into global metrics ---
if [ "$MERGE_METRICS" = true ] && [ -d "$SESSION_DIR/metrics" ]; then
  mkdir -p "$GLOBAL_METRICS_DIR"

  for metric_file in "$SESSION_DIR/metrics"/*.jsonl; do
    [ ! -f "$metric_file" ] && continue
    basename_file=$(basename "$metric_file")
    # Append session metrics to global (not overwrite)
    cat "$metric_file" >> "$GLOBAL_METRICS_DIR/$basename_file"
  done
fi

# --- Step 2: Remove session from active-sessions.json ---
_deregister_session() {
  local lockfile="$SESSIONS_DIR/.active-sessions.lock"

  (
    flock -w 5 200 || { echo "WARN: Could not acquire lock for session deregistration" >&2; return 1; }

    if [ -f "$ACTIVE_FILE" ] && jq empty "$ACTIVE_FILE" 2>/dev/null; then
      jq --arg id "$SESSION_ID" \
         '.sessions = [.sessions[] | select(.id != $id)]' \
         "$ACTIVE_FILE" > "$ACTIVE_FILE.tmp" && mv "$ACTIVE_FILE.tmp" "$ACTIVE_FILE"
    fi

  ) 200>"$lockfile"
}

_deregister_session

# --- Step 3: Release any locks held by this session ---
LOCKS_DIR="$SESSIONS_DIR/locks"
if [ -d "$LOCKS_DIR" ]; then
  for lockfile in "$LOCKS_DIR"/*.lock; do
    [ ! -f "$lockfile" ] && continue
    LOCK_SESSION=$(jq -r '.session_id // empty' "$lockfile" 2>/dev/null)
    if [ "$LOCK_SESSION" = "$SESSION_ID" ]; then
      rm -f "$lockfile"
    fi
  done
fi

# --- Step 4: Clean up session directory (if configured) ---
if [ "$CLEANUP_ON_EXIT" = true ] && [ -d "$SESSION_DIR" ]; then
  rm -rf "$SESSION_DIR"
fi

# Clean up PID-based session file
rm -f "$SESSIONS_DIR/.current-session-$$" 2>/dev/null

exit 0
