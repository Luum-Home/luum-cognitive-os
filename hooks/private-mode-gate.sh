#!/usr/bin/env bash
# PreToolUse hook: Block all Engram persistence tools when private mode is active
# Checks for /tmp/claude-private-mode-active flag file
# Must complete in <1 second

set -euo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

FLAG="/tmp/claude-private-mode-active"

# If private mode is NOT active, allow everything
if [ ! -f "$FLAG" ]; then
  exit 0
fi

# Private mode IS active — block the tool call
echo '{"decision": "deny", "reason": "Private mode active — persistence disabled"}'
exit 0
