#!/usr/bin/env bash
# migrate-to-cognitive-os.sh — Migrate a project from .agent-os/ to .cognitive-os/
#
# Usage: bash /path/to/cognitive-os/scripts/migrate-to-cognitive-os.sh [project-dir]
#        (defaults to current directory)
#
# What it does:
#   1. Renames .agent-os/ → .cognitive-os/
#   2. Renames agent-os.yaml → cognitive-os.yaml (if exists)
#   3. Updates all references in .cognitive-os/ files
#   4. Updates .claude/settings.json hook paths
#   5. Creates a symlink .agent-os → .cognitive-os for backward compat

set -euo pipefail

PROJECT_DIR="${1:-$(pwd)}"

echo "=== Cognitive OS Migration ==="
echo "Project: $PROJECT_DIR"
echo ""

# Check if already migrated
if [ -d "$PROJECT_DIR/.cognitive-os" ] && [ ! -L "$PROJECT_DIR/.cognitive-os" ]; then
  echo "Already migrated (.cognitive-os/ exists). Nothing to do."
  exit 0
fi

# Check if .agent-os exists
if [ ! -d "$PROJECT_DIR/.agent-os" ]; then
  echo "ERROR: No .agent-os/ directory found in $PROJECT_DIR"
  echo "This project doesn't have Cognitive OS installed."
  exit 1
fi

# 1. Rename directory
echo "[1/5] Renaming .agent-os/ → .cognitive-os/..."
mv "$PROJECT_DIR/.agent-os" "$PROJECT_DIR/.cognitive-os"

# 2. Create backward-compat symlink
echo "[2/5] Creating symlink .agent-os → .cognitive-os..."
ln -s .cognitive-os "$PROJECT_DIR/.agent-os"

# 3. Rename config file if exists
if [ -f "$PROJECT_DIR/.cognitive-os/agent-os.yaml" ]; then
  echo "[3/5] Renaming agent-os.yaml → cognitive-os.yaml..."
  mv "$PROJECT_DIR/.cognitive-os/agent-os.yaml" "$PROJECT_DIR/.cognitive-os/cognitive-os.yaml"
elif [ -f "$PROJECT_DIR/agent-os.yaml" ]; then
  echo "[3/5] Renaming root agent-os.yaml → cognitive-os.yaml..."
  mv "$PROJECT_DIR/agent-os.yaml" "$PROJECT_DIR/cognitive-os.yaml"
else
  echo "[3/5] No agent-os.yaml found, skipping..."
fi

# 4. Update references in all files under .cognitive-os/
echo "[4/5] Updating references in .cognitive-os/ files..."
UPDATED=0
while IFS= read -r file; do
  if grep -q "agent-os\|AGENT_OS\|agent_os" "$file" 2>/dev/null; then
    # macOS sed requires backup extension with -i
    sed -i.bak \
      -e 's/\.agent-os/\.cognitive-os/g' \
      -e 's/agent-os\.yaml/cognitive-os.yaml/g' \
      -e 's/AGENT_OS_/COGNITIVE_OS_/g' \
      -e 's/agent_os/cognitive_os/g' \
      -e 's/agent-os-network/cognitive-os-network/g' \
      "$file"
    rm -f "${file}.bak"
    UPDATED=$((UPDATED + 1))
  fi
done < <(find "$PROJECT_DIR/.cognitive-os" -type f \( -name "*.sh" -o -name "*.yaml" -o -name "*.yml" -o -name "*.json" -o -name "*.md" -o -name "*.py" \) 2>/dev/null)
echo "  Updated $UPDATED files"

# 5. Update .claude/settings.json if exists
SETTINGS="$PROJECT_DIR/.claude/settings.json"
if [ -f "$SETTINGS" ]; then
  echo "[5/5] Updating .claude/settings.json hook paths..."
  sed -i.bak 's/\.agent-os/\.cognitive-os/g' "$SETTINGS"
  rm -f "${SETTINGS}.bak"
  echo "  Hook paths updated"
else
  echo "[5/5] No .claude/settings.json found, skipping..."
fi

echo ""
echo "=== Migration complete ==="
echo "  .cognitive-os/  — main directory (new)"
echo "  .agent-os/      — symlink for backward compat"
echo ""
echo "You can safely delete the .agent-os symlink once all tools are updated."
