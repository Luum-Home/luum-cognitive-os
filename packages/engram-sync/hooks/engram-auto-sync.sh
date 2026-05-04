#!/usr/bin/env bash
# SCOPE: os-only
# Hook: Engram Auto-Sync (Stop/SessionEnd)
# Automatically exports Engram observations and commits to git
# when a Claude Code session ends. Does NOT push.

set -euo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
EXPORT_DIR="$PROJECT_DIR/.engram/exports"
SYNC_SCRIPT="$PROJECT_DIR/scripts/engram-sync.sh"

# Only run if engram is available
if ! command -v engram &>/dev/null; then
  exit 0
fi

# Only run if the sync script exists
if [ ! -x "$SYNC_SCRIPT" ]; then
  exit 0
fi

# Export observations through the existing git-jsonl path first. ADR-141 cloud
# sync is additive, never a replacement for this local/offline export.
"$SYNC_SCRIPT" >/dev/null 2>&1 || true

if [ "${ENGRAM_CLOUD_AUTOSYNC:-0}" = "1" ]; then
  "$SYNC_SCRIPT" --cloud >/dev/null 2>&1 || true
fi

# Stage and commit if there are changes
cd "$PROJECT_DIR"
if git diff --quiet .engram/ 2>/dev/null && git diff --cached --quiet .engram/ 2>/dev/null; then
  # Check for untracked files in .engram/
  UNTRACKED=$(git ls-files --others --exclude-standard .engram/ 2>/dev/null)
  if [ -z "$UNTRACKED" ]; then
    # No changes to commit
    exit 0
  fi
fi

git add .engram/ 2>/dev/null || true
git commit -m "sync: engram auto-sync $(date +%Y-%m-%d-%H%M)" --no-verify 2>/dev/null || true
