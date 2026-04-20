#!/usr/bin/env bash
# SCOPE: os-only
# Stop hook: Persist session state checkpoint before session ends.
# Calls lib/session_state.py checkpoint so the next session can recover.
# Must complete in <5 seconds.

set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
STATE_FILE="$PROJECT_DIR/.cognitive-os/session-state.json"

# Only act if there is an existing state file to checkpoint
if [ ! -f "$STATE_FILE" ]; then
  exit 0
fi

# Resolve Python — prefer python3
PYTHON="python3"
if ! command -v python3 &>/dev/null; then
  PYTHON="python"
  if ! command -v python &>/dev/null; then
    echo "WARN: No Python interpreter found; skipping session state checkpoint." >&2
    exit 0
  fi
fi

# Run checkpoint via inline Python to avoid import path issues
$PYTHON -c "
import sys, os
sys.path.insert(0, os.path.join('$PROJECT_DIR'))
from lib.session_state import checkpoint
checkpoint('Session ended — checkpoint before shutdown', project_dir='$PROJECT_DIR')
" 2>/dev/null

exit 0
