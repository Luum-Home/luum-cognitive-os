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
#
# DELIBERATELY LEFT MUTE (2026-08-15). The other two silenced call-sites in this
# family were converted; this one was not, for two reasons that are specific to
# it and do not generalise:
#
#   1. Its failure is already visible to the person, in the artifact they are
#      reading. The other helpers fail into a void — a session that starts with
#      no user model, or an agent planning without the queue state, looks
#      identical to a healthy one. Here the user typed /recap and is looking at
#      the output: the COS section is either in it or it is not. Announcing an
#      absence the reader can already see is noise, not observability.
#   2. This is a Stop hook, and stderr is the channel the Stop contract uses to
#      tell the model why a stop was refused. Today `|| true` pins the exit code
#      at 0 so stderr is inert, but wiring adapter diagnostics into that stream
#      leaves the hook one exit-code edit away from turning an adapter traceback
#      into a stop-refusal reason. The blast radius is the whole session ending.
#
# If this ever needs a diagnosis channel, it should be a metrics row, not stderr.
python3 "$ADAPTER" 2>/dev/null || true

exit 0
