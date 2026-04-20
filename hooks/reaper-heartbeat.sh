#!/usr/bin/env bash
# SCOPE: os-only
# reaper-heartbeat.sh — SessionStart hook: schedule periodic process reaper (ADR-028 D1.B)
#
# Starts a background loop that runs scripts/so-reaper.sh every 300 s.
# Single-instance: only one loop per project directory per OS session.
# PID file at .cognitive-os/runtime/reaper-heartbeat.pid prevents duplicates.
#
# Why shell loop instead of mcp__scheduled-tasks:
#   SessionStart runs before any MCP tool is available; shell background
#   process is fully portable and has no external dependencies.

set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}"
RUNTIME_DIR="$PROJECT_DIR/.cognitive-os/runtime"
PID_FILE="$RUNTIME_DIR/reaper-heartbeat.pid"
REAPER="$PROJECT_DIR/scripts/so-reaper.sh"

mkdir -p "$RUNTIME_DIR"

# ── Single-instance guard ────────────────────────────────────────────────────
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE" 2>/dev/null || echo "")
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        # Existing loop still alive — nothing to do.
        exit 0
    fi
    # Stale PID file — remove it.
    rm -f "$PID_FILE"
fi

# ── Sanity check ────────────────────────────────────────────────────────────
if [ ! -f "$REAPER" ]; then
    echo "[reaper-heartbeat] WARNING: $REAPER not found, skipping." >&2
    exit 0
fi

# ── Launch background loop ──────────────────────────────────────────────────
(
    # Give the main session a moment to fully initialise before first run.
    sleep 10
    while true; do
        bash "$REAPER" 2>&1 || true
        sleep 300
    done
) &

LOOP_PID=$!
echo "$LOOP_PID" > "$PID_FILE"

echo "[reaper-heartbeat] background reaper loop started (pid=$LOOP_PID, interval=300s)" >&2
exit 0
