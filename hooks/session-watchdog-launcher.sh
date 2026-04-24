#!/usr/bin/env bash
# SCOPE: os-only
# session-watchdog-launcher.sh — SessionStart hook: ensure singleton Phase A
# session lifecycle watchdog daemon (ADR-047 Phase A).
#
# Starts `python3 scripts/so_session_watchdog.py --daemon --interval 60` in
# the background if (and only if) no live daemon is already tracked by the
# pidfile. Pattern mirrors `hooks/reaper-daemon-launcher.sh`:
#
#   - atomic mkdir-based single-instance lock prevents TOCTOU races across
#     concurrent SessionStart invocations
#   - pidfile at .cognitive-os/runtime/session-watchdog.pid tracks the live
#     daemon; stale pidfiles are removed
#   - orphan cleanup kills legacy watchdog processes not matching the pidfile
#   - opt-out via COS_SESSION_WATCHDOG_DISABLE=1
#   - feature flag: reads runtime.session_watchdog.enabled from
#     cognitive-os.yaml via grep (no PyYAML dependency)
#   - exit 0 always — MUST NOT block session start

set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}"
RUNTIME_DIR="$PROJECT_DIR/.cognitive-os/runtime"
PID_FILE="$RUNTIME_DIR/session-watchdog.pid"
LOCKDIR="$RUNTIME_DIR/session-watchdog.lockdir"
WATCHDOG="$PROJECT_DIR/scripts/so_session_watchdog.py"
CONFIG_FILE="$PROJECT_DIR/cognitive-os.yaml"

mkdir -p "$RUNTIME_DIR"

# ── Opt-out env var ─────────────────────────────────────────────────────────
if [ "${COS_SESSION_WATCHDOG_DISABLE:-0}" = "1" ]; then
    exit 0
fi

# ── Feature flag (simple grep, no PyYAML) ───────────────────────────────────
# Looks for the session_watchdog block and its `enabled:` line. If explicitly
# false, exit silently. If absent or true, proceed.
if [ -f "$CONFIG_FILE" ]; then
    sw_enabled=$(awk '
        /^[[:space:]]*session_watchdog:[[:space:]]*$/ { in_block=1; next }
        in_block && /^[[:space:]]*[a-zA-Z_]+:[[:space:]]*$/ && !/^[[:space:]]{4,}/ { in_block=0 }
        in_block && /^[[:space:]]+enabled:[[:space:]]*/ {
            sub(/^[[:space:]]+enabled:[[:space:]]*/, "")
            sub(/[[:space:]]*#.*$/, "")
            gsub(/["\x27]/, "")
            print
            exit
        }
    ' "$CONFIG_FILE" 2>/dev/null || echo "")
    if [ "$sw_enabled" = "false" ]; then
        exit 0
    fi
fi

# ── Atomic single-instance lock (mkdir is atomic on POSIX filesystems) ──────
if ! mkdir "$LOCKDIR" 2>/dev/null; then
    # Another launcher holds the lock — nothing to do.
    exit 0
fi
trap 'rmdir "$LOCKDIR" 2>/dev/null || true' EXIT

# ── Single-instance guard ───────────────────────────────────────────────────
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE" 2>/dev/null || echo "")
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        # Confirm the process cmdline actually references so-session-watchdog
        # (defensive — guards against PID reuse).
        if ps -p "$OLD_PID" -o command= 2>/dev/null | grep -q "so.session.watchdog"; then
            echo "[session-watchdog] daemon ensured (PID=$OLD_PID)" >&2
            exit 0
        fi
    fi
    # Stale or mismatched pidfile — remove it.
    rm -f "$PID_FILE"
fi

# ── Orphan cleanup: kill stray watchdog processes not matching pidfile ──────
TRACKED_PID=$(cat "$PID_FILE" 2>/dev/null || echo "")
if command -v pgrep &>/dev/null; then
    while IFS= read -r candidate_pid; do
        [ -z "$candidate_pid" ] && continue
        [ "$candidate_pid" = "$$" ] && continue
        [ -n "$TRACKED_PID" ] && [ "$candidate_pid" = "$TRACKED_PID" ] && continue
        if kill -0 "$candidate_pid" 2>/dev/null; then
            kill "$candidate_pid" 2>/dev/null || true
        fi
    done < <(pgrep -f "so_session_watchdog.py" 2>/dev/null || true)
fi

# ── Sanity check ────────────────────────────────────────────────────────────
if [ ! -f "$WATCHDOG" ]; then
    echo "[session-watchdog] WARNING: $WATCHDOG not found, skipping." >&2
    exit 0
fi

# ── Launch daemon (detached) ────────────────────────────────────────────────
(
    # Detach fully: new session, stdin/stdout closed, stderr preserved briefly.
    nohup python3 "$WATCHDOG" --daemon --interval 60 \
        </dev/null \
        >>"$RUNTIME_DIR/session-watchdog.log" \
        2>&1 &
    echo $!
) > "$RUNTIME_DIR/.watchdog-spawn-pid" 2>/dev/null

DAEMON_PID=$(cat "$RUNTIME_DIR/.watchdog-spawn-pid" 2>/dev/null || echo "")
rm -f "$RUNTIME_DIR/.watchdog-spawn-pid"

if [ -n "$DAEMON_PID" ]; then
    echo "$DAEMON_PID" > "$PID_FILE"
    echo "[session-watchdog] daemon ensured (PID=$DAEMON_PID)" >&2
fi

exit 0
