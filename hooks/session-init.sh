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

# ─── Level-1 skills catalog pointer ──────────────────────────────────────────
# The compact catalog (CATALOG-COMPACT.md) is the Level-1 index loaded at
# session start. Full SKILL.md files load on demand. The full catalog with
# invocations and sections is available via /catalog-full.
CATALOG_COMPACT="$PROJECT_DIR/skills/CATALOG-COMPACT.md"
if [ -f "$CATALOG_COMPACT" ]; then
  echo "Skills catalog: skills/CATALOG-COMPACT.md (run /catalog-full for details)"
else
  echo "WARN: skills/CATALOG-COMPACT.md missing — run: python3 scripts/generate-compact-catalog.py" >&2
fi
echo ""

# Write session ID to a discoverable file so other hooks can read it
echo "$SESSION_ID" > "$SESSIONS_DIR/.current-session-$$"

# ─── Self-improve + user model + work queue (consolidated) ────────────────────
# Consolidated into a single python3 call (was 3 cold starts).
SELF_IMPROVE_FLAG="$PROJECT_DIR/.cognitive-os/metrics/.self-improve-recommended" \
SESSION_DIR="$SESSION_DIR" \
CLAUDE_PROJECT_DIR="$PROJECT_DIR" \
python3 "$(dirname "$0")/_lib/session_init_helper.py" 2>/dev/null || true

# ─── Singularity auto-suggestion ─────────────────────────────────────────────
# Advisory only — always exits 0. Lightweight file checks only (no subprocess).
# Function is extracted to _lib/singularity-suggestion.sh so tests can source
# it directly without running the full hook.
source "$(dirname "$0")/_lib/singularity-suggestion.sh"

_singularity_suggestion

# ─── Test baseline capture (non-blocking) ────────────────────────────────────
# Capture current test state so session-end can detect regressions introduced
# during this session. Runs in background — never slows session start.
(
  if command -v python3 &>/dev/null && python3 -m pytest --version &>/dev/null 2>&1; then
    python3 -m pytest --tb=no -q 2>&1 | tail -5 > "$SESSION_DIR/test-baseline.txt" 2>/dev/null || true
  else
    echo "baseline: unavailable" > "$SESSION_DIR/test-baseline.txt"
  fi
) &

# Work queue check moved to _lib/session_init_helper.py (consolidated above)


exit 0
