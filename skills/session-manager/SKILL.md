# Session Manager

> Manage concurrent Cognitive OS sessions: list, inspect, and clean up.

## Invoke

`/sessions`

## Subcommands

### `/sessions list`

Show all active sessions with IDs, start times, and PIDs.

**Implementation:**

```bash
SESSIONS_DIR="$CLAUDE_PROJECT_DIR/.cognitive-os/sessions"
ACTIVE_FILE="$SESSIONS_DIR/active-sessions.json"

if [ ! -f "$ACTIVE_FILE" ]; then
  echo "No active sessions file found."
  exit 0
fi

echo "=== Active Sessions ==="
echo ""

jq -r '.sessions[] | "  ID: \(.id)\n  PID: \(.pid)\n  Started: \(.start_time)\n  Directory: \(.working_directory)\n  Status: \(if (.pid | tostring | test("^[0-9]+$")) then "unknown" else "registered" end)\n"' "$ACTIVE_FILE" 2>/dev/null

TOTAL=$(jq '.sessions | length' "$ACTIVE_FILE" 2>/dev/null || echo "0")
echo "Total: $TOTAL session(s)"
```

For each session, also check if the PID is still running:
- Run `kill -0 {pid}` to verify the process is alive
- Mark as "running" or "stale" accordingly

### `/sessions current`

Show current session info.

**Implementation:**

```bash
SESSIONS_DIR="$CLAUDE_PROJECT_DIR/.cognitive-os/sessions"
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-}"

if [ -z "$SESSION_ID" ]; then
  # Try PID-based discovery
  SESSION_FILE="$SESSIONS_DIR/.current-session-$$"
  if [ -f "$SESSION_FILE" ]; then
    SESSION_ID=$(cat "$SESSION_FILE")
  fi
fi

if [ -z "$SESSION_ID" ]; then
  echo "No active session detected for this process."
  exit 0
fi

META_FILE="$SESSIONS_DIR/$SESSION_ID/meta.json"
if [ -f "$META_FILE" ]; then
  echo "=== Current Session ==="
  jq '.' "$META_FILE"
else
  echo "Session ID: $SESSION_ID (metadata not found)"
fi
```

Also report:
- Number of metrics files in the session directory
- Number of active locks held by this session
- Session uptime (current time - start time)

### `/sessions cleanup`

Remove stale sessions where the PID is no longer running.

**Implementation:**

```bash
SESSIONS_DIR="$CLAUDE_PROJECT_DIR/.cognitive-os/sessions"
ACTIVE_FILE="$SESSIONS_DIR/active-sessions.json"
LOCKS_DIR="$SESSIONS_DIR/locks"

if [ ! -f "$ACTIVE_FILE" ]; then
  echo "No active sessions to clean up."
  exit 0
fi

CLEANED=0

# Check each session
jq -c '.sessions[]' "$ACTIVE_FILE" 2>/dev/null | while IFS= read -r session; do
  SID=$(echo "$session" | jq -r '.id')
  SPID=$(echo "$session" | jq -r '.pid')

  # Check if PID is still running
  if ! kill -0 "$SPID" 2>/dev/null; then
    echo "Removing stale session: $SID (PID $SPID not running)"

    # Remove from active sessions
    jq --arg id "$SID" '.sessions = [.sessions[] | select(.id != $id)]' \
       "$ACTIVE_FILE" > "$ACTIVE_FILE.tmp" && mv "$ACTIVE_FILE.tmp" "$ACTIVE_FILE"

    # Clean up locks held by this session
    if [ -d "$LOCKS_DIR" ]; then
      for lockfile in "$LOCKS_DIR"/*.lock; do
        [ ! -f "$lockfile" ] && continue
        LOCK_SID=$(jq -r '.session_id // empty' "$lockfile" 2>/dev/null)
        if [ "$LOCK_SID" = "$SID" ]; then
          rm -f "$lockfile"
          echo "  Released lock: $(basename "$lockfile")"
        fi
      done
    fi

    # Remove session directory
    SESSION_DIR="$SESSIONS_DIR/$SID"
    if [ -d "$SESSION_DIR" ]; then
      rm -rf "$SESSION_DIR"
      echo "  Removed directory: $SESSION_DIR"
    fi

    # Remove PID file
    rm -f "$SESSIONS_DIR/.current-session-$SPID" 2>/dev/null

    CLEANED=$((CLEANED + 1))
  fi
done

echo ""
echo "Cleaned $CLEANED stale session(s)."
```

## Notes

- Session isolation is controlled by `sessions.concurrency` in `cognitive-os.yaml`
- File locking is advisory only -- it warns but does not block writes
- Engram handles its own concurrency via SQLite WAL mode
- Session metrics are merged into global metrics on clean exit
- If a session crashes without cleanup, use `/sessions cleanup` to remove stale entries
