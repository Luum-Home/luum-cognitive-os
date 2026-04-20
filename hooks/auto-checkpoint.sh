#!/usr/bin/env bash
# SCOPE: both
# CONCERNS: fault-tolerance, recovery, checkpoints
# Auto-checkpoint -- periodic WAL-like saves for crash recovery
# PostToolUse hook on Bash|Edit|Write
# Runs lightweight -- only does real work every N minutes
#
# Author: luum
set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
CHECKPOINT_DIR="$PROJECT_DIR/.cognitive-os/checkpoints"
CHECKPOINT_MARKER="$CHECKPOINT_DIR/.last-checkpoint"
INTERVAL_SECONDS=300  # 5 minutes

# Quick exit: check if enough time has elapsed
if [ -f "$CHECKPOINT_MARKER" ]; then
    LAST=""
    LAST=$(cat "$CHECKPOINT_MARKER" 2>/dev/null) || LAST="0"
    if [ -z "$LAST" ]; then
        LAST="0"
    fi
    NOW=$(date +%s)
    ELAPSED=$((NOW - LAST))
    if [ "$ELAPSED" -lt "$INTERVAL_SECONDS" ]; then
        exit 0
    fi
fi

# Ensure we are in a git repo
if ! git -C "$PROJECT_DIR" rev-parse --git-dir >/dev/null 2>&1; then
    exit 0
fi

# Count dirty files
DIRTY=$(git -C "$PROJECT_DIR" status --porcelain 2>/dev/null | wc -l | tr -d ' ')
if [ "$DIRTY" = "" ]; then
    DIRTY=0
fi

# No dirty files -- just update marker and exit
if [ "$DIRTY" -eq 0 ]; then
    mkdir -p "$CHECKPOINT_DIR"
    date +%s > "$CHECKPOINT_MARKER"
    exit 0
fi

# Time for a real checkpoint
mkdir -p "$CHECKPOINT_DIR"

CHECKPOINT_ID="cos-$(date +%Y%m%d-%H%M%S)"

# Create a named stash (survives crashes)
git -C "$PROJECT_DIR" stash push -m "$CHECKPOINT_ID" --include-untracked >/dev/null 2>&1
STASH_RC=$?

if [ "$STASH_RC" -eq 0 ]; then
    # Restore working directory -- stash stays as backup
    git -C "$PROJECT_DIR" stash pop >/dev/null 2>&1
fi

# Save checkpoint metadata
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
cat > "$CHECKPOINT_DIR/$CHECKPOINT_ID.json" <<CHECKPOINT_EOF
{
  "checkpoint_id": "$CHECKPOINT_ID",
  "timestamp": "$TIMESTAMP",
  "dirty_files": $DIRTY,
  "note": "periodic"
}
CHECKPOINT_EOF

# Update timestamp marker
date +%s > "$CHECKPOINT_MARKER"

exit 0
