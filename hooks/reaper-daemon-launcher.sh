#!/usr/bin/env bash
# SCOPE: os-only
# reaper-daemon-launcher.sh — SessionStart hook: schedule periodic process reaper (ADR-028 D1.B)
# Renamed from reaper-heartbeat.sh (v0.15): this script launches a daemon, not a heartbeat.
# Backwards-compat symlink: hooks/reaper-heartbeat.sh -> reaper-daemon-launcher.sh
#
# Starts a background loop that runs scripts/so-reaper.sh every 300 s.
# Single-instance: only one loop per project directory per OS session.
# PID file at .cognitive-os/runtime/reaper-daemon-launcher.pid prevents duplicates.
#
# Why shell loop instead of mcp__scheduled-tasks:
#   SessionStart runs before any MCP tool is available; shell background
#   process is fully portable and has no external dependencies.
#
# TOCTOU fix (2026-04-20):
#   The original check-then-spawn had a race window where two parallel
#   SessionStart invocations both passed the "no PID file" check and both
#   spawned daemons. Fixed with mkdir-based atomic lock (POSIX-portable,
#   no flock dependency) + legacy-orphan cleanup before spawn.

set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}"
RUNTIME_DIR="$PROJECT_DIR/.cognitive-os/runtime"
PID_FILE="$RUNTIME_DIR/reaper-heartbeat.pid"
LOCKDIR="$RUNTIME_DIR/reaper-heartbeat.lockdir"
REAPER="$PROJECT_DIR/scripts/so-reaper.sh"

mkdir -p "$RUNTIME_DIR"

# ── Atomic single-instance lock (mkdir is atomic on POSIX filesystems) ───────
# Only ONE process can create the directory; all others exit immediately.
if ! mkdir "$LOCKDIR" 2>/dev/null; then
    # Another instance is in the critical section — nothing to do.
    exit 0
fi
# We now hold the exclusive lock. Release it on any exit path.
trap 'rmdir "$LOCKDIR" 2>/dev/null || true' EXIT

# ── Single-instance guard (under lock) ──────────────────────────────────────
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE" 2>/dev/null || echo "")
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        # Existing loop still alive — nothing to do.
        exit 0
    fi
    # Stale PID file — remove it.
    rm -f "$PID_FILE"
fi

# ── Orphan cleanup (belt-and-suspenders for pre-fix legacy daemons) ──────────
# Kill any reaper-heartbeat daemons for this PROJECT_DIR that are NOT the
# currently tracked PID. This removes orphans left by the old TOCTOU races.
TRACKED_PID=$(cat "$PID_FILE" 2>/dev/null || echo "")
if command -v pgrep &>/dev/null; then
    THIS_SCRIPT="$(basename "$0")"
    while IFS= read -r candidate_pid; do
        [ -z "$candidate_pid" ] && continue
        # Skip self and the tracked daemon
        [ "$candidate_pid" = "$$" ] && continue
        [ -n "$TRACKED_PID" ] && [ "$candidate_pid" = "$TRACKED_PID" ] && continue
        # Only kill if the process cmdline actually references this script name
        if kill -0 "$candidate_pid" 2>/dev/null; then
            kill "$candidate_pid" 2>/dev/null || true
        fi
    done < <(pgrep -f "$THIS_SCRIPT" 2>/dev/null || true)
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
