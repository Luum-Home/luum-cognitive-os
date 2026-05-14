#!/usr/bin/env bash
# SCOPE: os-only
# CONCERNS: fault-tolerance, recovery
# Crash Recovery -- detects unclean shutdown and offers recovery
# SessionStart hook
#
# Author: luum
set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"

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

# ── New-style snapshot recovery (ADR-099) ────────────────────────────────────
# Surface incomplete snapshots from .cognitive-os/snapshots/ that have both
# untracked file copies and/or a tracked stash ref.
SNAPSHOTS_DIR="$PROJECT_DIR/.cognitive-os/snapshots"
if [ -d "$SNAPSHOTS_DIR" ] && command -v python3 >/dev/null 2>&1; then
    SNAPSHOT_REPORT=$(python3 - <<'PYEOF' 2>/dev/null
import sys, json, os
project_dir = os.environ.get("COGNITIVE_OS_PROJECT_DIR") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
sys.path.insert(0, project_dir)
try:
    from lib.snapshot_manager import list_snapshots
    from pathlib import Path
    snaps = list_snapshots(Path(project_dir))
    if not snaps:
        sys.exit(0)
    # Show the 3 most recent
    for s in snaps[:3]:
        sid = s.get("snapshot_id", "?")
        ts = s.get("timestamp_iso", "?")
        untracked = s.get("untracked_files", [])
        stash = s.get("tracked_stash_ref") or "none"
        mode = s.get("mode", "?")
        status = s.get("status", "?")
        print(f"  [{mode}|{status}] {sid}")
        print(f"    created: {ts}")
        print(f"    untracked files backed up: {len(untracked)}")
        print(f"    tracked stash: {stash}")
        if untracked:
            for f in untracked[:5]:
                print(f"      - {f}")
            if len(untracked) > 5:
                print(f"      ... and {len(untracked)-5} more")
except Exception as exc:
    pass
PYEOF
)
    if [ -n "$SNAPSHOT_REPORT" ]; then
        echo "" >&2
        echo "INFO: SNAPSHOT RECOVERY (ADR-099): Found recent pre-agent snapshots:" >&2
        echo "$SNAPSHOT_REPORT" >&2
        echo "" >&2
        echo "  To restore a snapshot (all files):" >&2
        echo "    python3 -c \"from lib.snapshot_manager import restore_snapshot; from pathlib import Path; restore_snapshot(Path('.'), '<snapshot_id>')\"" >&2
        echo "  To restore specific files:" >&2
        echo "    python3 -c \"from lib.snapshot_manager import restore_snapshot; from pathlib import Path; restore_snapshot(Path('.'), '<snapshot_id>', files=['path/to/file'])\"" >&2
        echo "  To prune old snapshots (>30d):" >&2
        echo "    python3 -c \"from lib.snapshot_manager import prune_expired; from pathlib import Path; prune_expired(Path('.'))\"" >&2
        echo "" >&2
    fi
fi

# ── Legacy stash recovery (cos- stashes from old pre-agent-snapshot path) ────
STASHES=$(git -C "$PROJECT_DIR" stash list 2>/dev/null | grep -E "(cos-|auto-pre-agent-)" | head -5)
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
echo "  To list all: git stash list | grep -E '(cos-|auto-pre-agent-)'" >&2
echo "" >&2
echo "  NOTE: cos-* stashes were created by the legacy pre-agent-snapshot path." >&2
echo "  To inspect: git stash show -p <stash@{N}>" >&2
echo "  These coexist with new-style snapshots in .cognitive-os/snapshots/ (ADR-099)." >&2
echo "" >&2

exit 0
