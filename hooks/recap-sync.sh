#!/usr/bin/env bash
# SCOPE: os-only
# Stop hook: emit COS session state as additionalContext for Claude Code's
# native /recap command. Implements ADR-021 (vendor-agnostic state with
# provider adapters).
#
# Reads canonical state from .cognitive-os/sessions/{SESSION_ID}/ and prints
# a hookSpecificOutput JSON block on stdout. Claude Code merges that block
# into the /recap output the user sees.
#
# Must be fast (<2s) and silent on success unless there is state to report.
# Intentionally does NOT mutate any COS state — read-only adapter.

set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"

# Resolve symlinks (project uses symlinked directories per CLAUDE.md rules)
PROJECT_DIR=$(python3 -c 'import os, sys; print(os.path.realpath(sys.argv[1]))' "$PROJECT_DIR" 2>/dev/null || echo "$PROJECT_DIR")

# Load the symlink-aware file checker (mandatory per CLAUDE.md)
LIB_DIR="$PROJECT_DIR/hooks/_lib"
if [ -f "$LIB_DIR/file_checker.sh" ]; then
  # shellcheck disable=SC1091
  source "$LIB_DIR/file_checker.sh"
fi

ADAPTER="$LIB_DIR/recap_adapter.py"

# If the adapter is missing (or its symlink target is broken), exit silently.
if command -v file_exists_strict >/dev/null 2>&1; then
  file_exists_strict "$ADAPTER" || exit 0
else
  [ -f "$ADAPTER" ] || exit 0
fi

# python3 is required; if absent, no-op rather than fail the Stop event.
command -v python3 >/dev/null 2>&1 || exit 0

# Run the adapter. Suppress any stderr — the recap path must never block exit.
python3 "$ADAPTER" 2>/dev/null || true

exit 0
