#!/bin/bash
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"
# ===========================================================================
# Cognitive OS Sync Hook — Syncs .cognitive-os/ to a dedicated Cognitive OS repo on session end
# Trigger: Stop (session end)
#
# Configure COGNITIVE_OS_REPO_PATH env var to point to your Cognitive OS git repo.
# If not set, this hook is a no-op.
# ===========================================================================

COGNITIVE_OS_SOURCE="${CLAUDE_PROJECT_DIR}/.cognitive-os"
COGNITIVE_OS_REPO="${COGNITIVE_OS_REPO_PATH:-}"

# Skip if no repo configured
if [ -z "$COGNITIVE_OS_REPO" ] || [ ! -d "$COGNITIVE_OS_REPO/.git" ]; then
  exit 0
fi

# Skip in private mode
if [ -f /tmp/claude-private-mode-active ]; then
  exit 0
fi

# Check if .cognitive-os/ has changes (compare timestamps)
LAST_SYNC_MARKER="$COGNITIVE_OS_REPO/.last-sync"
if [ -f "$LAST_SYNC_MARKER" ]; then
  LAST_SYNC=$(cat "$LAST_SYNC_MARKER")
  NEWEST=$(find "$COGNITIVE_OS_SOURCE" -newer "$LAST_SYNC_MARKER" -type f | head -1)
  if [ -z "$NEWEST" ]; then
    # No changes since last sync
    exit 0
  fi
fi

# Sync (exclude runtime data + repo-only files)
rsync -av --delete \
  --exclude='.git' \
  --exclude='.git/' \
  --exclude='LICENSE' \
  --exclude='CHANGELOG.md' \
  --exclude='.gitignore' \
  --exclude='.last-sync' \
  --exclude='docs/business/' \
  --exclude='examples/' \
  --exclude='metrics/*.jsonl' \
  --exclude='tasks/active-tasks.json' \
  --exclude='checkpoints/*.json' \
  --exclude='.DS_Store' \
  --exclude='skills/auto-generated/' \
  "$COGNITIVE_OS_SOURCE/" "$COGNITIVE_OS_REPO/" \
  > /dev/null 2>&1

# Also sync docker-compose.cognitive-os.yml
if [ -f "${CLAUDE_PROJECT_DIR}/docker-compose.cognitive-os.yml" ]; then
  cp "${CLAUDE_PROJECT_DIR}/docker-compose.cognitive-os.yml" "$COGNITIVE_OS_REPO/" 2>/dev/null
fi

# Also sync business docs if they exist
if [ -d "${CLAUDE_PROJECT_DIR}/docs/business" ]; then
  mkdir -p "$COGNITIVE_OS_REPO/docs/business"
  rsync -av --delete "${CLAUDE_PROJECT_DIR}/docs/business/" "$COGNITIVE_OS_REPO/docs/business/" > /dev/null 2>&1
fi

# Auto-commit if there are changes
cd "$COGNITIVE_OS_REPO"
if [ -n "$(git status --porcelain)" ]; then
  git add -A
  git commit -m "sync: auto-update from project session $(date +%Y-%m-%d)" --quiet 2>/dev/null
  echo "Cognitive OS synced to repo"
fi

# Update marker
date +%s > "$LAST_SYNC_MARKER"

exit 0
