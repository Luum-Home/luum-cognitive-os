#!/usr/bin/env bash
# setup-git-hooks.sh — Install git hooks in the COS repo for auto-update
#
# Installs a post-merge hook that automatically updates all registered
# COS installations when the OS repo is pulled/updated.
#
# Usage:
#   bash scripts/setup-git-hooks.sh           # install hooks
#   bash scripts/setup-git-hooks.sh --remove  # remove hooks
#   bash scripts/setup-git-hooks.sh --status  # check if hooks are installed
#
# Safe: does NOT overwrite existing post-merge hooks. If one exists,
# it appends the auto-update call.
#
# Bash 3.x compatible (no associative arrays, no bash 4+ features).
# Author: luum
set -euo pipefail

COS_SOURCE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
GIT_HOOKS_DIR="$COS_SOURCE_DIR/.git/hooks"
POST_MERGE_HOOK="$GIT_HOOKS_DIR/post-merge"
MARKER="# COS_AUTO_UPDATE"

# ── Parse args ─────────────────────────────────────────────────────
ACTION="install"
for arg in "$@"; do
  case "$arg" in
    --remove) ACTION="remove" ;;
    --status) ACTION="status" ;;
    --help|-h)
      echo "Usage: bash scripts/setup-git-hooks.sh [--remove|--status]"
      echo ""
      echo "  (default)  Install the post-merge hook for auto-updating projects"
      echo "  --remove   Remove the COS auto-update from post-merge hook"
      echo "  --status   Check if the hook is installed"
      exit 0
      ;;
    *)
      echo "Unknown option: $arg" >&2
      exit 1
      ;;
  esac
done

# ── Verify we're in a git repo ─────────────────────────────────────
if [ ! -d "$COS_SOURCE_DIR/.git" ]; then
  echo "Error: Not a git repository: $COS_SOURCE_DIR" >&2
  exit 1
fi

# ── Status check ───────────────────────────────────────────────────
if [ "$ACTION" = "status" ]; then
  if [ -f "$POST_MERGE_HOOK" ] && grep -qF "$MARKER" "$POST_MERGE_HOOK" 2>/dev/null; then
    echo "COS auto-update hook: INSTALLED"
    echo "Location: $POST_MERGE_HOOK"
  else
    echo "COS auto-update hook: NOT INSTALLED"
    echo "Run: bash scripts/setup-git-hooks.sh"
  fi
  exit 0
fi

# ── Remove ─────────────────────────────────────────────────────────
if [ "$ACTION" = "remove" ]; then
  if [ ! -f "$POST_MERGE_HOOK" ]; then
    echo "No post-merge hook found. Nothing to remove."
    exit 0
  fi

  if ! grep -qF "$MARKER" "$POST_MERGE_HOOK" 2>/dev/null; then
    echo "Post-merge hook exists but does not contain COS auto-update."
    exit 0
  fi

  # Remove the COS block (from marker to end-marker)
  sed -i '' "/$MARKER BEGIN/,/$MARKER END/d" "$POST_MERGE_HOOK" 2>/dev/null || \
    sed -i "/$MARKER BEGIN/,/$MARKER END/d" "$POST_MERGE_HOOK" 2>/dev/null

  # If the file is now empty (just shebang + whitespace), remove it
  non_empty_lines=$(grep -cv '^\s*$\|^#!/' "$POST_MERGE_HOOK" 2>/dev/null || echo 0)
  if [ "$non_empty_lines" -eq 0 ]; then
    rm -f "$POST_MERGE_HOOK"
    echo "Removed post-merge hook (was COS-only)."
  else
    echo "Removed COS auto-update block from post-merge hook."
    echo "Other hook content preserved."
  fi
  exit 0
fi

# ── Install ────────────────────────────────────────────────────────
mkdir -p "$GIT_HOOKS_DIR"

# Check if our marker already exists
if [ -f "$POST_MERGE_HOOK" ] && grep -qF "$MARKER" "$POST_MERGE_HOOK" 2>/dev/null; then
  echo "COS auto-update hook already installed."
  echo "Location: $POST_MERGE_HOOK"
  exit 0
fi

# The hook content
HOOK_BLOCK=$(cat << 'HOOKEOF'

# COS_AUTO_UPDATE BEGIN — Do not edit this block manually
# Auto-updates all registered COS installations after git pull/merge.
# Installed by: bash scripts/setup-git-hooks.sh
# Remove with:  bash scripts/setup-git-hooks.sh --remove
_COS_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
if [ -f "$_COS_DIR/scripts/auto-update-projects.sh" ]; then
  echo ""
  echo "[COS] Checking for projects to update..."
  bash "$_COS_DIR/scripts/auto-update-projects.sh" 2>&1 | sed 's/^/[COS] /'
fi
# COS_AUTO_UPDATE END
HOOKEOF
)

if [ -f "$POST_MERGE_HOOK" ]; then
  # Append to existing hook
  echo "$HOOK_BLOCK" >> "$POST_MERGE_HOOK"
  echo "Appended COS auto-update to existing post-merge hook."
else
  # Create new hook
  cat > "$POST_MERGE_HOOK" << 'SHEBANG'
#!/usr/bin/env bash
SHEBANG
  echo "$HOOK_BLOCK" >> "$POST_MERGE_HOOK"
  chmod +x "$POST_MERGE_HOOK"
  echo "Created post-merge hook with COS auto-update."
fi

echo "Location: $POST_MERGE_HOOK"
echo ""
echo "Now when you 'git pull' this repo, all registered COS installations"
echo "will be automatically updated."
