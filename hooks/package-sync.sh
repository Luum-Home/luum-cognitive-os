#!/usr/bin/env bash
# SCOPE: os-only
# @manual-trigger: CI or developer-triggered; not a Claude event hook default
# package-sync.sh — PostToolUse on Write
# Auto-syncs package rules when package files change:
#   1. Creates missing symlinks in rules/ for new package rules
#   2. Regenerates the package index
#   3. Triggers self-install.sh to sync .claude/rules/cos/
#
# Triggers only when writes hit: packages/*/rules/*.md or packages/*/cos-package.yaml
set -euo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"

# Read tool input from stdin
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.filePath // empty' 2>/dev/null || true)

# Exit early if no file path
[ -z "$FILE_PATH" ] && exit 0

# Normalize: strip PROJECT_DIR prefix if present to get relative path
REL_PATH="${FILE_PATH#"$PROJECT_DIR/"}"

# Only trigger for package rule files or cos-package.yaml
case "$REL_PATH" in
  packages/*/rules/*.md|packages/*/cos-package.yaml) ;;
  *) exit 0 ;;
esac

synced=0

# Step 1: Create missing symlinks in rules/ for package rules
for pkg_rule in "$PROJECT_DIR"/packages/*/rules/*.md; do
  [ -f "$pkg_rule" ] || continue
  base=$(basename "$pkg_rule")
  link="$PROJECT_DIR/rules/$base"
  if [ ! -e "$link" ]; then
    # Create relative symlink
    rel=$(python3 -c "import os; print(os.path.relpath('$pkg_rule', '$PROJECT_DIR/rules/'))" 2>/dev/null || echo "../$pkg_rule")
    ln -sf "$rel" "$link"
    synced=$((synced + 1))
  fi
done

# Step 2: Regenerate package index (if the script exists)
INDEX_SCRIPT="$PROJECT_DIR/packages/cos-index/scripts/generate-index.sh"
if [ -f "$INDEX_SCRIPT" ]; then
  bash "$INDEX_SCRIPT" "$PROJECT_DIR/packages" 2>/dev/null || true
fi

# Step 3: Trigger self-install.sh to sync .claude/rules/cos/ (if exists)
SELF_INSTALL="$PROJECT_DIR/hooks/self-install.sh"
if [ -f "$SELF_INSTALL" ]; then
  bash "$SELF_INSTALL" 2>/dev/null || true
fi

if [ "$synced" -gt 0 ]; then
  echo "Package sync: created $synced new rule symlink(s)" >&2
fi

exit 0
