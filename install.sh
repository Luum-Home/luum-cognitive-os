#!/usr/bin/env bash
# install.sh — Install Cognitive OS into the current project
set -euo pipefail

REPO_URL="https://github.com/luum-home/luum-cognitive-os.git"
VERSION="${COGNITIVE_OS_VERSION:-main}"
TARGET_DIR=".cognitive-os"
FORCE="${COGNITIVE_OS_FORCE:-false}"
TEMP_DIR=$(mktemp -d)

cleanup() { rm -rf "$TEMP_DIR"; }
trap cleanup EXIT

echo "=== Cognitive OS Installer ==="
echo ""

# Check prerequisites
if ! command -v git >/dev/null 2>&1; then
  echo "Error: git is required but not installed."
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "Warning: jq is not installed. Settings merge requires jq."
  echo "         Install jq for safe merge with existing .claude/settings.json"
  HAS_JQ=false
else
  HAS_JQ=true
fi

# ── Pre-install conflict detection ──────────────────────────────────
if [ -d ".claude" ]; then
  echo "Detected existing .claude/ configuration:"
  existing_hooks=0
  existing_rules=0
  existing_commands=0
  has_claude_md=false

  if [ -f ".claude/settings.json" ]; then
    existing_hooks=$(jq '[.hooks // {} | to_entries[] | .value[] | .hooks[]? ] | length' .claude/settings.json 2>/dev/null || echo "?")
    echo "  - settings.json: $existing_hooks hooks registered"
  fi

  if [ -d ".claude/rules" ]; then
    existing_rules=$(find .claude/rules -maxdepth 2 -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
    echo "  - rules/: $existing_rules rule files"
  fi

  if [ -d ".claude/commands" ]; then
    existing_commands=$(find .claude/commands -maxdepth 1 -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
    echo "  - commands/: $existing_commands command files"
  fi

  if [ -f ".claude/CLAUDE.md" ]; then
    has_claude_md=true
    echo "  - CLAUDE.md: present"
  fi

  echo ""
  echo "Cognitive OS will MERGE settings and namespace rules under cos/"
  echo "Your existing configuration will be preserved."
  echo ""
fi

# Check if already installed
if [ -d "$TARGET_DIR" ]; then
  if [ "$FORCE" = "true" ]; then
    echo "Overwriting existing installation..."
    rm -rf "$TARGET_DIR"
  elif [ -t 0 ]; then
    # Interactive terminal — ask for confirmation
    echo "Cognitive OS is already installed in $TARGET_DIR"
    read -rp "Overwrite? (y/N): " confirm </dev/tty
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
      echo "Aborted."
      exit 0
    fi
    rm -rf "$TARGET_DIR"
  else
    # Non-interactive (piped) — abort safely
    echo "Cognitive OS is already installed in $TARGET_DIR"
    echo "To overwrite, run: COGNITIVE_OS_FORCE=true bash install.sh"
    exit 0
  fi
fi

# Clone and extract
echo "Downloading Cognitive OS ($VERSION)..."
git clone --depth 1 --branch "$VERSION" "$REPO_URL" "$TEMP_DIR" 2>/dev/null || \
  git clone --depth 1 "$REPO_URL" "$TEMP_DIR"

if [ ! -d "$TEMP_DIR/.cognitive-os" ]; then
  echo "Error: .cognitive-os/ not found in repository."
  exit 1
fi

# Install .cognitive-os/
cp -r "$TEMP_DIR/.cognitive-os" "$TARGET_DIR"

# Copy cognitive-os.yaml if not present
if [ ! -f "cognitive-os.yaml" ] && [ -f "$TEMP_DIR/cognitive-os.yaml" ]; then
  cp "$TEMP_DIR/cognitive-os.yaml" cognitive-os.yaml
fi

# ── Namespace rules under .claude/rules/cos/ ──────────────────────────
# COS rules go into a cos/ subdirectory to avoid mixing with project rules.
if [ -d "$TEMP_DIR/rules" ]; then
  mkdir -p ".claude/rules/cos"
  for rule in "$TEMP_DIR"/rules/*.md; do
    [ -f "$rule" ] || continue
    cp "$rule" ".claude/rules/cos/$(basename "$rule")"
  done
  echo "Rules installed to .claude/rules/cos/"
fi

# ── Merge or create .claude/settings.json ─────────────────────────────
# COS hooks reference (generated from the repo's .claude/settings.json)
COS_SETTINGS="$TEMP_DIR/.claude/settings.json"

if [ -f ".claude/settings.json" ] && [ -f "$COS_SETTINGS" ]; then
  # Existing settings.json — merge COS hooks without losing project hooks
  if [ "$HAS_JQ" = "true" ] && [ -f "$TEMP_DIR/scripts/merge-settings.sh" ]; then
    echo "Merging COS hooks into existing .claude/settings.json..."
    MERGED=$(mktemp)
    bash "$TEMP_DIR/scripts/merge-settings.sh" ".claude/settings.json" "$COS_SETTINGS" "$MERGED"
    mv "$MERGED" ".claude/settings.json"
    echo "Settings merged successfully."
  else
    echo "Warning: Cannot merge settings (jq or merge script missing)."
    echo "         Your existing .claude/settings.json was preserved."
    echo "         You may need to manually add COS hooks."
  fi
elif [ -f "$COS_SETTINGS" ]; then
  # No existing settings.json — copy COS one as-is
  mkdir -p ".claude"
  cp "$COS_SETTINGS" ".claude/settings.json"
  echo "Created .claude/settings.json with COS hooks."
fi

echo ""
echo "Cognitive OS installed successfully!"
echo ""
echo "Project structure:"
echo "  .cognitive-os/       — Cognitive OS core (skills, hooks, templates)"
echo "  .claude/rules/cos/   — COS rules (namespaced, won't conflict with yours)"
echo "  .claude/rules/*.md   — Your project rules (untouched)"
echo "  .claude/settings.json — Hooks (merged with your existing hooks)"
echo ""
echo "Next steps:"
echo "  1. Open Claude Code: claude"
echo "  2. Run: /cognitive-os-init"
echo "  3. (Optional) Start infrastructure:"
echo "     docker compose -f .cognitive-os/docker-compose.cognitive-os.yml up -d"
echo ""
