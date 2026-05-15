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
# Root fix (2026-05-15): checkpoints are copy-only by default. The old stash
# round-trip path can hide WIP if apply conflicts or a hook is interrupted, so
# stash mutation now requires explicit COS_AUTO_CHECKPOINT_USE_STASH=1 plus
# COS_ALLOW_DESTRUCTIVE_GIT=1.
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

# ── Copy-only checkpoint (root fix) ─────────────────────────────────────────
# Previous revisions used `git stash push --include-untracked` followed by
# `git stash apply` as a checkpoint side effect. That makes a PostToolUse Bash
# hook capable of hiding files from the operator worktree when apply conflicts,
# is interrupted, or races with another stash-mutating hook. Checkpointing must
# be observational by default: copy dirty file bytes into .cognitive-os without
# mutating git state.
CHECKPOINT_PATH="$CHECKPOINT_DIR/$CHECKPOINT_ID"
CHECKPOINT_FILES_DIR="$CHECKPOINT_PATH/files"
CHECKPOINT_META="$CHECKPOINT_DIR/$CHECKPOINT_ID.json"
STASH_NAME="copy-only"
COPY_STATUS="ok"
COPY_SUMMARY='{"copied_files":[],"deleted_files":[],"skipped_files":[],"copied_bytes":0}'
mkdir -p "$CHECKPOINT_FILES_DIR" 2>/dev/null || COPY_STATUS="mkdir_failed"

if [ "$COPY_STATUS" = "ok" ]; then
    COPY_SUMMARY=$(python3 - "$PROJECT_DIR" "$CHECKPOINT_FILES_DIR" <<'PYEOF' 2>/dev/null
import json
import shutil
import subprocess
import sys
from pathlib import Path

repo = Path(sys.argv[1]).resolve()
dest = Path(sys.argv[2]).resolve()

def git(args):
    result = subprocess.run(["git", *args], cwd=str(repo), capture_output=True)
    if result.returncode != 0:
        return []
    return [p.decode("utf-8", "replace") for p in result.stdout.split(b"\0") if p]

# `git diff --name-only HEAD` includes staged and unstaged tracked changes.
# Fall back gracefully for unborn repositories.
head_exists = subprocess.run(["git", "rev-parse", "--verify", "HEAD"], cwd=str(repo), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
tracked = git(["diff", "--name-only", "-z", "HEAD", "--"]) if head_exists else git(["ls-files", "-z"])
untracked = git(["ls-files", "--others", "--exclude-standard", "-z"])
paths = []
for rel in [*tracked, *untracked]:
    if not rel or rel.startswith(".cognitive-os/"):
        continue
    if rel not in paths:
        paths.append(rel)

copied = []
deleted = []
skipped = []
copied_bytes = 0
for rel in paths:
    src = repo / rel
    if not src.exists():
        deleted.append(rel)
        continue
    if not src.is_file():
        skipped.append({"path": rel, "reason": "not_regular_file"})
        continue
    target = dest / rel
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
        copied.append(rel)
        copied_bytes += src.stat().st_size
    except Exception as exc:
        skipped.append({"path": rel, "reason": f"copy_failed: {exc}"})

print(json.dumps({
    "copied_files": copied,
    "deleted_files": deleted,
    "skipped_files": skipped,
    "copied_bytes": copied_bytes,
}, separators=(",", ":")))
PYEOF
)
    if [ -z "$COPY_SUMMARY" ]; then
        COPY_STATUS="copy_failed"
        COPY_SUMMARY='{"copied_files":[],"deleted_files":[],"skipped_files":[{"path":"<checkpoint>","reason":"python_failed"}],"copied_bytes":0}'
    fi
fi

# Emergency compatibility path only. It is intentionally opt-in because stash
# round-trips are destructive to the visible worktree and caused hidden WIP.
if [ "${COS_AUTO_CHECKPOINT_USE_STASH:-0}" = "1" ] && [ "${COS_ALLOW_DESTRUCTIVE_GIT:-0}" = "1" ]; then
    if command -v uuidgen >/dev/null 2>&1; then
        _UUID=$(uuidgen | tr '[:upper:]' '[:lower:]')
    else
        _UUID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null \
                || echo "$$-$(date +%s)-$RANDOM")
    fi
    STASH_NAME="auto-checkpoint-${_UUID}"
    if command -v cos_stash_lock_acquire >/dev/null 2>&1; then
        cos_stash_lock_acquire "auto-checkpoint" || STASH_NAME="copy-only-lock-failed"
        trap 'cos_stash_lock_release' EXIT INT TERM
    fi
    if [[ "$STASH_NAME" == auto-checkpoint-* ]]; then
        git -C "$PROJECT_DIR" stash push -m "$STASH_NAME" --include-untracked \
            -- ':(exclude).cognitive-os' ':(exclude).cognitive-os/**' . \
            >/dev/null 2>&1
        STASH_RC=$?
        if [ "$STASH_RC" -eq 0 ]; then
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
                git -C "$PROJECT_DIR" stash apply "$STASH_REF" >/dev/null 2>&1
                _APPLY_RC=$?
                if [ "$_APPLY_RC" -eq 0 ]; then
                    git -C "$PROJECT_DIR" stash drop "$STASH_REF" >/dev/null 2>&1 || true
                else
                    COPY_STATUS="stash_apply_failed_preserved"
                fi
            fi
        else
            COPY_STATUS="stash_push_failed"
        fi
    fi
    if command -v cos_stash_lock_release >/dev/null 2>&1; then
        cos_stash_lock_release
        trap - EXIT INT TERM
    fi
fi

# Save checkpoint metadata. Compose with Python so copied path lists stay valid
# JSON even when filenames contain spaces, quotes, or newlines.
python3 - "$CHECKPOINT_META" "$CHECKPOINT_ID" "$TIMESTAMP" "$DIRTY" "$STASH_NAME" "$COPY_STATUS" "$COPY_SUMMARY" <<'PYEOF' 2>/dev/null
import json
import sys
from pathlib import Path

meta_path = Path(sys.argv[1])
checkpoint_id, timestamp, dirty, stash_name, status, summary_raw = sys.argv[2:]
try:
    summary = json.loads(summary_raw)
except Exception:
    summary = {"copied_files": [], "deleted_files": [], "skipped_files": [{"path": "<summary>", "reason": "invalid_json"}], "copied_bytes": 0}
meta = {
    "checkpoint_id": checkpoint_id,
    "timestamp": timestamp,
    "dirty_files": int(dirty),
    "stash_name": stash_name,
    "mode": "copy" if stash_name == "copy-only" else "legacy_stash_opt_in",
    "status": status,
    "copied_files": summary.get("copied_files", []),
    "deleted_files": summary.get("deleted_files", []),
    "skipped_files": summary.get("skipped_files", []),
    "copied_bytes": summary.get("copied_bytes", 0),
    "checkpoint_files_dir": str(meta_path.with_suffix("") / "files"),
    "note": "periodic",
}
meta_path.write_text(json.dumps(meta, indent=2) + "\n")
PYEOF
_META_RC=$?
if [ "$_META_RC" -ne 0 ]; then
cat > "$CHECKPOINT_META" <<CHECKPOINT_EOF
{
  "checkpoint_id": "$CHECKPOINT_ID",
  "timestamp": "$TIMESTAMP",
  "dirty_files": $DIRTY,
  "stash_name": "$STASH_NAME",
  "mode": "copy",
  "status": "metadata_fallback",
  "note": "periodic"
}
CHECKPOINT_EOF
fi

# Update timestamp marker
date +%s > "$CHECKPOINT_MARKER"

exit 0
