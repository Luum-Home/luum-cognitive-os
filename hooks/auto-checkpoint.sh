#!/usr/bin/env bash
# SCOPE: both
# CONCERNS: fault-tolerance, recovery, checkpoints
# Auto-checkpoint -- periodic WAL-like saves for crash recovery
# PostToolUse hook on Bash|Edit|Write
# Runs lightweight -- only does real work every N minutes
#
# Complements ADR-028 D1.C agent heartbeat; see docs/02-Decisions/adrs/ADR-028a.md §2.
# This hook persists session-level state (WS13). D1.C writes per-agent liveness
# files under .cognitive-os/tasks/. Both are required; neither replaces the other.
#
# R2 (revert-investigation-2026-05-02): stash ops now use NAMED stashes with a
# UUID per invocation. `git stash pop` replaced by find-by-name → apply → drop
# to prevent stash@{0} index shift races with concurrent hooks (pre/post-agent-snapshot).
#
# ADR-055b: stash ops require COS_ALLOW_DESTRUCTIVE_GIT=1 in hook env.
#
# Author: luum
set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"
STASH_LOCK_LIB="$(dirname "${BASH_SOURCE[0]}")/_lib/stash-lock.sh"
[ -f "$STASH_LOCK_LIB" ] && source "$STASH_LOCK_LIB"

# Bypass: COS_DISABLE_AUTO_CHECKPOINT=1 skips this hook entirely
if [ "${COS_DISABLE_AUTO_CHECKPOINT:-0}" = "1" ]; then
    exit 0
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
CHECKPOINT_DIR="$PROJECT_DIR/.cognitive-os/checkpoints"
CHECKPOINT_MARKER="$CHECKPOINT_DIR/.last-checkpoint"
RUNTIME_DIR="$PROJECT_DIR/.cognitive-os/runtime"
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
mkdir -p "$RUNTIME_DIR"

CHECKPOINT_ID="cos-$(date +%Y%m%d-%H%M%S)"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# ── R2: UUID-named stash to prevent stash@{0} index shift race ─────────────
# Each invocation gets its own UUID so concurrent hooks cannot grab the wrong entry.
if command -v uuidgen >/dev/null 2>&1; then
    _UUID=$(uuidgen | tr '[:upper:]' '[:lower:]')
else
    _UUID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null \
            || echo "$$-$(date +%s)-$RANDOM")
fi
STASH_NAME="auto-checkpoint-${_UUID}"

# ADR-055b: stash ops gated on COS_ALLOW_DESTRUCTIVE_GIT=1
# Exclude .cognitive-os/ so the runtime dir is not swallowed by --include-untracked.
STASH_RC=0
if [ "${COS_ALLOW_DESTRUCTIVE_GIT:-0}" = "1" ]; then
    if command -v cos_stash_lock_acquire >/dev/null 2>&1; then
        cos_stash_lock_acquire "auto-checkpoint" || exit 0
        trap 'cos_stash_lock_release' EXIT INT TERM
    fi

    git -C "$PROJECT_DIR" stash push -m "$STASH_NAME" --include-untracked \
        -- ':(exclude).cognitive-os' ':(exclude).cognitive-os/**' . \
        >/dev/null 2>&1
    STASH_RC=$?
fi

if [ "$STASH_RC" -eq 0 ] && [ "${COS_ALLOW_DESTRUCTIVE_GIT:-0}" = "1" ]; then
    # Re-create runtime dir in case stash swept it (safety belt)
    mkdir -p "$RUNTIME_DIR" 2>/dev/null || true

    # Persist stash name to runtime marker BEFORE apply (survives crashes)
    MARKER_FILE="$RUNTIME_DIR/auto-checkpoint-$$.json"
    printf '{"stash_name":"%s","checkpoint_id":"%s","pid":%s,"timestamp":"%s"}\n' \
        "$STASH_NAME" "$CHECKPOINT_ID" "$$" "$TIMESTAMP" \
        > "$MARKER_FILE" 2>/dev/null || true

    # ── Find stash by name, NOT by positional index ─────────────────────────
    # `git stash list --format='%gd %s'` output:
    #   stash@{0} On main: auto-checkpoint-<UUID>
    STASH_REF=""
    while IFS= read -r _line; do
        _ref="${_line%% *}"
        _msg="${_line#* }"
        if [[ "$_msg" == *"$STASH_NAME"* ]]; then
            STASH_REF="$_ref"
            break
        fi
    done < <(git -C "$PROJECT_DIR" stash list --format='%gd %s' 2>/dev/null || true)

    if [ -n "$STASH_REF" ]; then
        # apply (not pop): stash is preserved on conflict so it can be inspected
        git -C "$PROJECT_DIR" stash apply "$STASH_REF" >/dev/null 2>&1
        _APPLY_RC=$?
        if [ "$_APPLY_RC" -eq 0 ]; then
            # Drop only after successful apply
            git -C "$PROJECT_DIR" stash drop "$STASH_REF" >/dev/null 2>&1 || true
        fi
    fi

    # Remove PID marker (best-effort; harmless if it lingers)
    rm -f "$MARKER_FILE" 2>/dev/null || true
fi

if command -v cos_stash_lock_release >/dev/null 2>&1; then
    cos_stash_lock_release
    trap - EXIT INT TERM
fi

# Save checkpoint metadata
cat > "$CHECKPOINT_DIR/$CHECKPOINT_ID.json" <<CHECKPOINT_EOF
{
  "checkpoint_id": "$CHECKPOINT_ID",
  "timestamp": "$TIMESTAMP",
  "dirty_files": $DIRTY,
  "stash_name": "$STASH_NAME",
  "note": "periodic"
}
CHECKPOINT_EOF

# Update timestamp marker
date +%s > "$CHECKPOINT_MARKER"

exit 0
