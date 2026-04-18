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

  MERGE_LOCK_DIR="$PROJECT_DIR/.cognitive-os/runtime/locks"
  mkdir -p "$MERGE_LOCK_DIR" 2>/dev/null || true

  for metric_file in "$SESSION_DIR/metrics"/*.jsonl; do
    [ ! -f "$metric_file" ] && continue
    basename_file=$(basename "$metric_file")
    global_file="$GLOBAL_METRICS_DIR/$basename_file"
    lockfile="$MERGE_LOCK_DIR/merge-${basename_file}.lock"

    # Acquire per-file exclusive lock with 30s timeout; fail-open on timeout
    if command -v flock >/dev/null 2>&1; then
      if ! (
        flock -w 30 9 || {
          echo "[session-cleanup] WARN: lock timeout for $basename_file — skipping merge" >&2
          exit 1
        }
        cat "$metric_file" >> "$global_file"
      ) 9>"$lockfile"; then
        continue
      fi
    else
      # Fallback: mkdir-based advisory lock (atomic on POSIX, no flock needed)
      _lock_dir="${lockfile}.d"
      _lock_acquired=false
      _lock_deadline=$(( $(date +%s) + 30 ))
      while true; do
        if mkdir "$_lock_dir" 2>/dev/null; then
          _lock_acquired=true
          break
        fi
        if [ "$(date +%s)" -ge "$_lock_deadline" ]; then
          echo "[session-cleanup] WARN: lock timeout (mkdir) for $basename_file — skipping merge" >&2
          break
        fi
        sleep 0.2 2>/dev/null || sleep 1
      done
      if [ "$_lock_acquired" = true ]; then
        cat "$metric_file" >> "$global_file"
        rmdir "$_lock_dir" 2>/dev/null || true
      else
        continue
      fi
    fi
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

# --- Step 5: Mark lost agents and log them ---
# Any task still in_progress when the session ends is considered lost.
TASKS_FILE="$PROJECT_DIR/.cognitive-os/tasks/active-tasks.json"
if [ -f "$TASKS_FILE" ] && command -v jq &>/dev/null && command -v python3 &>/dev/null; then
  LOST_TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  METRICS_DIR="$GLOBAL_METRICS_DIR"
  mkdir -p "$METRICS_DIR" 2>/dev/null

  # Collect in_progress tasks before marking them lost
  LOST_TASKS=$(jq -c \
    '.tasks[] | select(.status == "in_progress")' \
    "$TASKS_FILE" 2>/dev/null || true)

  if [ -n "$LOST_TASKS" ]; then
    # Write one log entry per lost task
    while IFS= read -r task; do
      TASK_ID=$(echo "$task" | jq -r '.id // ""' 2>/dev/null)
      TASK_DESC=$(echo "$task" | jq -r '.description // ""' 2>/dev/null | head -c 200)
      LAUNCHED_AT=$(echo "$task" | jq -r '.launchedAt // ""' 2>/dev/null)

      # Calculate how long it was running (best effort)
      DURATION=0
      if [ -n "$LAUNCHED_AT" ]; then
        DURATION=$(python3 -c "
import sys
from datetime import datetime, timezone

def parse_iso(s):
    s = s.rstrip('Z')
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)

try:
    launched = parse_iso('$LAUNCHED_AT')
    from datetime import datetime as dt
    now = datetime.fromisoformat('$LOST_TIMESTAMP'.rstrip('Z')).replace(tzinfo=timezone.utc)
    print(int((now - launched).total_seconds()))
except Exception:
    print(0)
" 2>/dev/null || echo "0")
      fi

      printf '{"timestamp":"%s","task_id":"%s","duration_secs":%s,"status":"lost","description":"%s"}\n' \
        "$LOST_TIMESTAMP" "$TASK_ID" "$DURATION" \
        "$(echo "$TASK_DESC" | sed 's/"/\\"/g')" \
        >> "$METRICS_DIR/agent-timeouts.jsonl" 2>/dev/null || true
    done <<< "$LOST_TASKS"

    # Mark all in_progress tasks as lost in the file
    LOCK_FILE="$PROJECT_DIR/.cognitive-os/tasks/.active-tasks.lock"
    (
      flock -w 5 200 2>/dev/null || true
      MARKED=$(jq \
        --arg ts "$LOST_TIMESTAMP" \
        '(.tasks[] | select(.status == "in_progress")) |= . + {"status": "lost", "completedAt": $ts}' \
        "$TASKS_FILE" 2>/dev/null)
      [ -n "$MARKED" ] && echo "$MARKED" > "$TASKS_FILE"
    ) 200>"$LOCK_FILE" || true
  fi
fi

# --- Step 5b: Self-improve KPI flag ---
# Check last KPI snapshot. If first_pass_success_rate < 0.70 OR
# avg_trust_score < 60, write a flag so session-init warns next session.
SELF_IMPROVE_FLAG="$GLOBAL_METRICS_DIR/.self-improve-recommended"
KPI_FILE="$GLOBAL_METRICS_DIR/kpi-history.jsonl"

if [ -f "$KPI_FILE" ] && command -v python3 >/dev/null 2>&1; then
  KPI_VERDICT=$(python3 -c "
import json, sys

kpi_file = '$KPI_FILE'
flag_file = '$SELF_IMPROVE_FLAG'

try:
    with open(kpi_file, 'r') as f:
        lines = [l.strip() for l in f if l.strip()]
    if not lines:
        sys.exit(0)
    last = json.loads(lines[-1])
    first_pass = float(last.get('first_pass_success_rate', 1.0))
    avg_trust  = float(last.get('avg_trust_score', 100.0))
    if first_pass < 0.70 or avg_trust < 60.0:
        with open(flag_file, 'w') as fh:
            json.dump({'reason': 'first_pass_success_rate={:.2f} avg_trust_score={:.1f}'.format(first_pass, avg_trust),
                       'timestamp': last.get('timestamp', '')}, fh)
        print('RECOMMENDED')
    else:
        # Clear stale flag if KPIs recovered
        import os
        if os.path.exists(flag_file):
            os.remove(flag_file)
        print('OK')
except Exception as ex:
    print('ERROR:' + str(ex))
" 2>/dev/null || echo "SKIP")

  if [ "$KPI_VERDICT" = "RECOMMENDED" ]; then
    echo "SELF-IMPROVE RECOMMENDED: KPIs below threshold — run /self-improve at next session start." >&2
  fi
fi

# --- Step 6: Symbiosis Check (organism health) ---
# Measure overhead-to-value ratio. Alert if parasitic.
if command -v python3 >/dev/null 2>&1; then
  _symbiosis=$(python3 -c "
import sys
sys.path.insert(0, '$PROJECT_DIR/lib')
try:
    from symbiosis_monitor import SymbiosisMonitor
    m = SymbiosisMonitor('$PROJECT_DIR')
    r = m.generate_report()
    m.log_report(r)
    if r.health == 'parasitic':
        print('SYMBIOSIS WARNING: COS overhead ratio is {:.0%} (parasitic). {}'.format(r.overhead_ratio, r.recommendation or ''))
except Exception:
    pass
" 2>/dev/null)
  [ -n "$_symbiosis" ] && echo "$_symbiosis" >&2
fi

# --- Advisory: suggest session wrapup ---
# Non-blocking advisory so the user knows /session-wrapup is available.
echo "TIP: Run /session-wrapup before closing to inventory pending work and save session state to engram." >&2

exit 0
