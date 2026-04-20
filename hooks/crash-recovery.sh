#!/usr/bin/env bash
# CONCERNS: fault-tolerance, recovery
# Crash Recovery -- detects unclean shutdown and offers recovery
# SessionStart hook
#
# Author: luum
set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"

# ── State-snapshot recovery ──────────────────────────────────────────────────
# Check the most recent session dir for an orphaned state-snapshot.json.
# An "orphaned" snapshot is one where the session is no longer active.
SESSIONS_DIR="$PROJECT_DIR/.cognitive-os/sessions"
if [ -d "$SESSIONS_DIR" ] && command -v python3 >/dev/null 2>&1; then
    # Find the most recently modified session dir (excluding 'current' symlink)
    RECENT_SESSION=$(find "$SESSIONS_DIR" -mindepth 1 -maxdepth 1 -type d \
        ! -name "current" ! -name "default" \
        -printf '%T@ %p\n' 2>/dev/null \
        | sort -rn | head -1 | awk '{print $2}')
    if [ -z "$RECENT_SESSION" ]; then
        # macOS fallback (no -printf)
        RECENT_SESSION=$(ls -td "$SESSIONS_DIR"/*/  2>/dev/null \
            | grep -v '/current/' | grep -v '/default/' | head -1)
        RECENT_SESSION="${RECENT_SESSION%/}"
    fi

    if [ -n "$RECENT_SESSION" ] && [ -f "$RECENT_SESSION/state-snapshot.json" ]; then
        RECOVERY_MSG=$(python3 -c "
import sys
sys.path.insert(0, '$PROJECT_DIR')
try:
    from lib.state_heartbeat import StateHeartbeat
    h = StateHeartbeat('$RECENT_SESSION')
    print(h.format_recovery_prompt())
except Exception as e:
    pass
" 2>/dev/null)
        if [ -n "$RECOVERY_MSG" ]; then
            echo "" >&2
            echo "INFO: STATE SNAPSHOT FOUND from previous session:" >&2
            echo "$RECOVERY_MSG" | while IFS= read -r line; do
                echo "  $line" >&2
            done
            echo "" >&2
        fi
    fi
fi

# ── Work Queue Brief ─────────────────────────────────────────────────────
# Show pending work from persistent queue (survives across sessions)
QUEUE_FILE="$PROJECT_DIR/.cognitive-os/work-queue.json"
if [ -f "$QUEUE_FILE" ] && command -v python3 >/dev/null 2>&1; then
    QUEUE_BRIEF=$(python3 -c "
import sys
sys.path.insert(0, '$PROJECT_DIR')
try:
    from lib.work_queue import WorkQueue
    q = WorkQueue('$QUEUE_FILE')
    pending = q.get_pending()
    if pending:
        print(q.format_session_brief())
except Exception:
    pass
" 2>/dev/null)
    if [ -n "$QUEUE_BRIEF" ]; then
        echo "$QUEUE_BRIEF" >&2
        echo "" >&2
    fi
fi

# Ensure we are in a git repo
if ! git -C "$PROJECT_DIR" rev-parse --git-dir >/dev/null 2>&1; then
    exit 0
fi

# Check for cos- checkpoint stashes
STASHES=$(git -C "$PROJECT_DIR" stash list 2>/dev/null | grep "cos-" | head -5)
if [ -z "$STASHES" ]; then
    exit 0
fi

# Check if last session ended cleanly
LAST_CLEANUP="$PROJECT_DIR/.cognitive-os/sessions/.last-cleanup"
LAST_CHECKPOINT=""
if [ -d "$PROJECT_DIR/.cognitive-os/checkpoints" ]; then
    LAST_CHECKPOINT=$(ls -t "$PROJECT_DIR/.cognitive-os/checkpoints"/cos-*.json 2>/dev/null | head -1)
fi

STASH_COUNT=0
STASH_COUNT=$(echo "$STASHES" | wc -l | tr -d ' ')

echo "" >&2
echo "WARNING: CRASH RECOVERY: Found $STASH_COUNT checkpoint stash(es) from previous session." >&2
echo "  Stashes available:" >&2
echo "$STASHES" | while IFS= read -r line; do
    echo "    $line" >&2
done

if [ -n "$LAST_CHECKPOINT" ]; then
    # Extract info from checkpoint metadata
    if command -v python3 >/dev/null 2>&1; then
        CHECKPOINT_INFO=$(python3 -c "
import json, sys
try:
    with open('$LAST_CHECKPOINT') as f:
        d = json.load(f)
    ts = d.get('timestamp', 'unknown')
    dirty = d.get('dirty_files', d.get('uncommitted_changes', 0))
    print(f'  Last checkpoint: {ts} ({dirty} uncommitted files)')
except Exception:
    pass
" 2>/dev/null)
        if [ -n "$CHECKPOINT_INFO" ]; then
            echo "$CHECKPOINT_INFO" >&2
        fi
    fi
fi

echo "" >&2
echo "  To restore: git stash apply (picks most recent)" >&2
echo "  To discard: git stash drop" >&2
echo "  To list all: git stash list | grep cos-" >&2
echo "" >&2

exit 0
