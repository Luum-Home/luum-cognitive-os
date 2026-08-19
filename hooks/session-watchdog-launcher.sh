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
# The match below must be the full script path, not the basename. Matching
# "so_session_watchdog.py" alone finds every watchdog on the machine, so a
# launcher run here killed the operator's watchdog in every other project --
# and running the e2e suite, which invokes this launcher against a fake tree,
# killed the real one. That is how "0 watchdogs running" was measured on
# 2026-08-19 and misread as "nobody starts sessions".
#
# pgrep still casts the wide net, because -f patterns match loosely and a narrow
# one can miss; the argv check is what decides. A candidate whose argv cannot be
# read is left alone: killing on unreadable state is how this defect comes back.
TRACKED_PID=$(cat "$PID_FILE" 2>/dev/null || echo "")
if command -v pgrep &>/dev/null; then
    while IFS= read -r candidate_pid; do
        [ -z "$candidate_pid" ] && continue
        [ "$candidate_pid" = "$$" ] && continue
        [ -n "$TRACKED_PID" ] && [ "$candidate_pid" = "$TRACKED_PID" ] && continue
        candidate_args=$(ps -p "$candidate_pid" -o args= 2>/dev/null || true)
        [ -z "$candidate_args" ] && continue
        case "$candidate_args" in
            *"$WATCHDOG"*) ;;
            *) continue ;;
        esac
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

# ── Confirm the daemon outlived its own import before claiming success ──────
# nohup hands back a PID the instant the process is forked, so a daemon that
# dies inside `import` still yields one. Writing it straight to the pidfile made
# the hook print "daemon ensured" for a process that was already gone; the next
# SessionStart then found the pidfile stale, cleared it and spawned again. A
# crash-looping daemon reported success at every session and never once ran.
#
# The wait is a fixed window, not a poll: returning as soon as the process is
# alive would return BEFORE the import that kills it, which is the whole failure
# mode. It costs nothing on the session's critical path -- this launcher is
# registered `async: true` on SessionStart, a contract asserted by
# tests/unit/test_session_start_budget.py.
if [ -n "$DAEMON_PID" ]; then
    sleep "${COS_SESSION_WATCHDOG_STARTUP_GRACE:-0.5}"
    if kill -0 "$DAEMON_PID" 2>/dev/null; then
        echo "$DAEMON_PID" > "$PID_FILE"
        echo "[session-watchdog] daemon ensured (PID=$DAEMON_PID)" >&2
    else
        echo "[session-watchdog] WARNING: daemon exited during startup (PID=$DAEMON_PID); see $RUNTIME_DIR/session-watchdog.log" >&2
    fi
fi

exit 0
