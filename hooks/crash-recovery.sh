#!/usr/bin/env bash
# CONCERNS: fault-tolerance, recovery
# Crash Recovery -- detects unclean shutdown and offers recovery
# SessionStart hook
#
# Author: luum
set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"

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
