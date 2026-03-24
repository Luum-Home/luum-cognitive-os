#!/usr/bin/env bash
# install.sh — Install Cognitive OS into the current project
set -euo pipefail

REPO_URL="https://github.com/luum-home/luum-cognitive-os.git"
VERSION="${COGNITIVE_OS_VERSION:-main}"
TARGET_DIR=".cognitive-os"
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

# Check if already installed
if [ -d "$TARGET_DIR" ]; then
  echo "Cognitive OS is already installed in $TARGET_DIR"
  read -rp "Overwrite? (y/N): " confirm
  if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
  fi
  rm -rf "$TARGET_DIR"
fi

# Clone and extract
echo "Downloading Cognitive OS ($VERSION)..."
git clone --depth 1 --branch "$VERSION" "$REPO_URL" "$TEMP_DIR" 2>/dev/null || \
  git clone --depth 1 "$REPO_URL" "$TEMP_DIR"

if [ ! -d "$TEMP_DIR/.cognitive-os" ]; then
  echo "Error: .cognitive-os/ not found in repository."
  exit 1
fi

# Install
cp -r "$TEMP_DIR/.cognitive-os" "$TARGET_DIR"

# Copy cognitive-os.yaml if not present
if [ ! -f "cognitive-os.yaml" ] && [ -f "$TEMP_DIR/cognitive-os.yaml" ]; then
  cp "$TEMP_DIR/cognitive-os.yaml" cognitive-os.yaml
fi

echo ""
echo "Cognitive OS installed successfully!"
echo ""
echo "Next steps:"
echo "  1. Open Claude Code: claude"
echo "  2. Run: /cognitive-os-init"
echo "  3. (Optional) Start infrastructure:"
echo "     docker compose -f .cognitive-os/docker-compose.cognitive-os.yml up -d"
echo ""
