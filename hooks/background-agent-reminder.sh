#!/usr/bin/env bash
# SCOPE: os-only
# background-agent-reminder.sh — UserPromptSubmit hook
#
# Reminds the orchestrator about pending background agents so it doesn't
# block waiting for them. Fires on every user message.
#
# Type: UserPromptSubmit
# Exit: 0 (always advisory)
set -euo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

# Check if there are running background tasks via the tasks system
TASKS_FILE="${CLAUDE_PROJECT_DIR:-.}/.cognitive-os/tasks/active-tasks.json"

if [ -f "$TASKS_FILE" ] && command -v jq >/dev/null 2>&1; then
  in_progress=$(jq '[.tasks[]? | select(.status == "in_progress")] | length' "$TASKS_FILE" 2>/dev/null || echo 0)
  if [ "$in_progress" -gt 0 ]; then
    echo "REMINDER: $in_progress background agent(s) running. Do NOT wait for them — respond to the user NOW and continue with the next task." >&2
  fi
fi

exit 0
