#!/usr/bin/env bash
# SCOPE: os-only
# install-pre-commit.sh — Symlink pre-commit-gate.sh into .git/hooks/pre-commit
#
# Usage: bash scripts/install-pre-commit.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

HOOK_SOURCE="$ROOT_DIR/hooks/pre-commit-gate.sh"
GIT_HOOKS_DIR="$ROOT_DIR/.git/hooks"
HOOK_TARGET="$GIT_HOOKS_DIR/pre-commit"

if [ ! -d "$GIT_HOOKS_DIR" ]; then
  echo "ERROR: .git/hooks directory not found. Is this a git repository?" >&2
  exit 1
fi

if [ ! -f "$HOOK_SOURCE" ]; then
  echo "ERROR: hooks/pre-commit-gate.sh not found." >&2
  exit 1
fi

# Make the hook executable
chmod +x "$HOOK_SOURCE"

# Remove existing hook if it's a file (not a symlink to our hook)
if [ -e "$HOOK_TARGET" ] && [ ! -L "$HOOK_TARGET" ]; then
  echo "WARNING: Existing pre-commit hook found. Backing up to pre-commit.bak"
  mv "$HOOK_TARGET" "${HOOK_TARGET}.bak"
elif [ -L "$HOOK_TARGET" ]; then
  rm "$HOOK_TARGET"
fi

# Create the symlink
ln -s "$HOOK_SOURCE" "$HOOK_TARGET"

echo "Pre-commit hook installed: $HOOK_TARGET -> $HOOK_SOURCE"
