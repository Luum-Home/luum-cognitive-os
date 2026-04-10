#!/usr/bin/env bash
# SessionStart hook: Initialize session isolation
# Creates a unique session directory with isolated tasks and metrics.
# Registers the session in active-sessions.json with file locking.
# Must complete in <3 seconds.

set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
SESSIONS_DIR="$PROJECT_DIR/.cognitive-os/sessions"
ACTIVE_FILE="$SESSIONS_DIR/active-sessions.json"
LOCKS_DIR="$SESSIONS_DIR/locks"

# Generate unique session ID: timestamp-PID-random
SESSION_ID="$(date +%s)-$$-$(head -c 4 /dev/urandom | od -An -tx1 | tr -d ' \n')"

# Create session directory structure
SESSION_DIR="$SESSIONS_DIR/$SESSION_ID"
mkdir -p "$SESSION_DIR/metrics"
mkdir -p "$LOCKS_DIR"

# Create empty session-scoped tasks file
echo "[]" > "$SESSION_DIR/tasks.json"

# Write session metadata
cat > "$SESSION_DIR/meta.json" <<EOF
{
  "session_id": "$SESSION_ID",
  "pid": $$,
  "start_time": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "start_epoch": $(date +%s),
  "working_directory": "$PROJECT_DIR",
  "hostname": "$(hostname -s 2>/dev/null || echo 'unknown')",
  "user": "$(whoami 2>/dev/null || echo 'unknown')"
}
EOF

# Register session in active-sessions.json with file locking
_register_session() {
  local lockfile="$SESSIONS_DIR/.active-sessions.lock"

  # Use flock for atomic read-modify-write
  (
    flock -w 5 200 || { echo "WARN: Could not acquire lock for session registration" >&2; return 1; }

    # Initialize if missing or invalid
    if [ ! -f "$ACTIVE_FILE" ] || ! jq empty "$ACTIVE_FILE" 2>/dev/null; then
      echo '{"sessions":[]}' > "$ACTIVE_FILE"
    fi

    # Read max_concurrent from cognitive-os.yaml (default 10)
    MAX_CONCURRENT=10
    CONFIG_FILE="$PROJECT_DIR/.cognitive-os/cognitive-os.yaml"
    if [ -f "$CONFIG_FILE" ]; then
      PARSED_MAX=$(grep 'max_concurrent:' "$CONFIG_FILE" 2>/dev/null | head -1 | sed 's/.*max_concurrent:[[:space:]]*//' | tr -d '[:space:]')
      if [[ "$PARSED_MAX" =~ ^[0-9]+$ ]]; then
        MAX_CONCURRENT="$PARSED_MAX"
      fi
    fi

    # Check current count
    CURRENT_COUNT=$(jq '.sessions | length' "$ACTIVE_FILE" 2>/dev/null || echo "0")
    if [ "$CURRENT_COUNT" -ge "$MAX_CONCURRENT" ]; then
      echo "WARN: Maximum concurrent sessions ($MAX_CONCURRENT) reached. Session registered but may degrade performance." >&2
    fi

    # Add this session
    jq --arg id "$SESSION_ID" \
       --arg pid "$$" \
       --arg start "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
       --arg dir "$PROJECT_DIR" \
       '.sessions += [{"id": $id, "pid": ($pid | tonumber), "start_time": $start, "working_directory": $dir}]' \
       "$ACTIVE_FILE" > "$ACTIVE_FILE.tmp" && mv "$ACTIVE_FILE.tmp" "$ACTIVE_FILE"

  ) 200>"$lockfile"
}

_register_session

# Export session ID for downstream hooks
# Note: Claude Code hooks communicate via stdout/env; we print for the session to pick up
echo ""
echo "=== COGNITIVE OS SESSION INITIALIZED ==="
echo "Session ID: $SESSION_ID"
echo "Session dir: $SESSION_DIR"
echo ""
echo "Set COGNITIVE_OS_SESSION_ID=$SESSION_ID for this session."
echo ""

# Write session ID to a discoverable file so other hooks can read it
echo "$SESSION_ID" > "$SESSIONS_DIR/.current-session-$$"

# ─── Self-improve KPI flag check ─────────────────────────────────────────────
SELF_IMPROVE_FLAG="$PROJECT_DIR/.cognitive-os/metrics/.self-improve-recommended"
if [ -f "$SELF_IMPROVE_FLAG" ]; then
  REASON=$(python3 -c "
import json
try:
    with open('$SELF_IMPROVE_FLAG') as f:
        d = json.load(f)
    print(d.get('reason','KPIs below threshold'))
except Exception:
    print('KPIs below threshold')
" 2>/dev/null || echo "KPIs below threshold")
  echo "SELF-IMPROVE RECOMMENDED: $REASON — consider running /self-improve" >&2
fi

# Load user model for this session
python3 -c "
import sys; sys.path.insert(0, '$PROJECT_DIR')
from lib.user_model import UserModel
model = UserModel.load_from_engram()
if model.preferences:
    profile = model.get_profile_summary()
    with open('$SESSION_DIR/user-profile.txt', 'w') as f:
        f.write(profile)
" 2>/dev/null || true

# ─── Singularity auto-suggestion ─────────────────────────────────────────────
# Advisory only — always exits 0. Lightweight file checks only (no subprocess).
_singularity_suggestion() {
  local metrics_dir="$PROJECT_DIR/.cognitive-os/metrics"
  local events_file="$metrics_dir/singularity-events.jsonl"
  local errors_file="$metrics_dir/error-learning.jsonl"
  local stale_file="$metrics_dir/stale-docs.jsonl"

  # Collect signals
  # bash-specific: arrays require bash (#!/usr/bin/env bash)
  local signals=()
  local never_ran=false

  # Signal 1: Singularity has never been run
  if [ ! -f "$events_file" ]; then
    never_ran=true
  fi

  # Signal 2: 3+ errors in last 24 hours (check line count as a proxy — cheap)
  if [ -f "$errors_file" ]; then
    local cutoff
    cutoff=$(( $(date +%s) - 86400 ))
    # POSIX awk: extract timestamp_epoch value and compare (no gawk capture groups)
    local recent_errors
    recent_errors=$(awk -v cutoff="$cutoff" '
      /timestamp_epoch/ {
        n = split($0, parts, /timestamp_epoch":[[:space:]]*/);
        if (n >= 2) {
          val = parts[2] + 0;
          if (val >= cutoff) print;
        }
      }
    ' "$errors_file" 2>/dev/null | wc -l | tr -d ' ')
    if [ "${recent_errors:-0}" -ge 3 ]; then
      signals+=("${recent_errors} errors in last 24h")
    fi
  fi

  # Signal 3: stale docs pending
  if [ -f "$stale_file" ] && [ -s "$stale_file" ]; then
    local stale_count
    stale_count=$(wc -l < "$stale_file" | tr -d ' ')
    signals+=("${stale_count} stale doc(s) pending")
  fi

  # No signals and already ran — nothing to say
  if [ "$never_ran" = false ] && [ "${#signals[@]}" -eq 0 ]; then
    return 0
  fi

  # Check for user opt-out (config flag or sentinel file)
  local config_file="$PROJECT_DIR/.cognitive-os/cognitive-os.yaml"
  if grep -q 'singularity_suggestion:[[:space:]]*false' "$config_file" 2>/dev/null; then
    return 0
  fi
  if [ -f "$PROJECT_DIR/.cognitive-os/.singularity-suggestion-dismissed" ]; then
    return 0
  fi

  # Emit suggestion block to stderr
  {
    echo ""
    echo "=== SINGULARITY SUGGESTION ==="
    if [ "$never_ran" = true ]; then
      echo "Singularity has never been run in this project."
    else
      # Build comma-space separated string without relying on IFS join semantics
      local signal_str=""
      for s in "${signals[@]}"; do
        [[ -n "$signal_str" ]] && signal_str="$signal_str, $s" || signal_str="$s"
      done
      echo "Detected: $signal_str"
      echo "Consider activating Singularity for autonomous monitoring."
    fi
    echo "Try: SINGULARITY_ENABLED=true python3 lib/singularity.py dry-run"
    echo "=== END SINGULARITY ==="
    echo ""
  } >&2
}

_singularity_suggestion

exit 0
