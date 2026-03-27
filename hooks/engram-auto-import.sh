#!/bin/bash
# Hook: Engram Auto-Import (SessionStart)
# Checks if .engram/exports/ has files newer than the last import
# and imports them automatically so every session starts with latest team memory.

set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
EXPORT_DIR="$PROJECT_DIR/.engram/exports"
IMPORT_MARKER="$EXPORT_DIR/.last-import"
IMPORT_SCRIPT="$PROJECT_DIR/scripts/engram-import.sh"

# Only run if engram is available
if ! command -v engram &>/dev/null; then
  exit 0
fi

# Only run if exports exist
if [ ! -d "$EXPORT_DIR" ]; then
  exit 0
fi

# Only run if the import script exists
if [ ! -x "$IMPORT_SCRIPT" ]; then
  exit 0
fi

# Find latest export file
LATEST_EXPORT=$(ls -t "$EXPORT_DIR"/observations-*.json 2>/dev/null | head -1)
if [ -z "$LATEST_EXPORT" ]; then
  exit 0
fi

# Check if we need to import (export is newer than last import marker)
if [ -f "$IMPORT_MARKER" ]; then
  if [ "$LATEST_EXPORT" -ot "$IMPORT_MARKER" ]; then
    # Already imported this or a newer file
    exit 0
  fi
fi

# Import latest observations
"$IMPORT_SCRIPT" "$LATEST_EXPORT" >/dev/null 2>&1 || true

# Update import marker
touch "$IMPORT_MARKER"
