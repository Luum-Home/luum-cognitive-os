#!/usr/bin/env bash
# SCOPE: both
# PreToolUse hook: Register sub-agent tasks before launch
# Fires on "Agent" tool use — records task in active-tasks.json
# Must complete in <3 seconds

set -euo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

TASKS_DIR="${CLAUDE_PROJECT_DIR:-.}/.cognitive-os/tasks"
TASKS_FILE="$TASKS_DIR/active-tasks.json"

# Ensure tasks directory and file exist
mkdir -p "$TASKS_DIR"
if [ ! -f "$TASKS_FILE" ]; then
  echo '{"version":1,"tasks":[],"lastUpdated":""}' > "$TASKS_FILE"
fi

# Read stdin (JSON with tool_name, tool_input)
INPUT=$(cat)

# Exit early if no input
if [ -z "$INPUT" ]; then
  exit 0
fi

# Require jq
if ! command -v jq &>/dev/null; then
  exit 0
fi

# Only process Agent tool
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
if [ "$TOOL_NAME" != "Agent" ]; then
  exit 0
fi

# Extract agent description/prompt
DESCRIPTION=$(echo "$INPUT" | jq -r '
  .tool_input.description // .tool_input.prompt // "unknown task"
' 2>/dev/null | head -c 500)

# Extract Claude Code's native tool_use_id for panel correlation (ADR-024)
TOOL_USE_ID=$(echo "$INPUT" | jq -r '.tool_use_id // empty' 2>/dev/null)

if [ -z "$DESCRIPTION" ] || [ "$DESCRIPTION" = "null" ]; then
  DESCRIPTION="unknown task"
fi

# Generate a simple ID using timestamp + random
TASK_ID="task-$(date +%s)-$RANDOM"

# Get current timestamp
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Fix 1 (ADR-097): write "pending" here, not "in_progress".
# The hook fires at PreToolUse — after dispatch-gate has allowed the launch —
# but BEFORE the agent process actually starts.  Status flips to "in_progress"
# once the agent's own preamble runs write_context_marker.py (which knows its PID).
# If the agent never starts (crash, rate-limit cancel), the record stays "pending"
# and the zombie reaper will mark it "cancelled-stale" after 30 min.

# Build the new task entry (includes toolUseId for native panel correlation)
NEW_TASK=$(jq -c -n \
  --arg id "$TASK_ID" \
  --arg tui "$TOOL_USE_ID" \
  --arg desc "$DESCRIPTION" \
  --arg ts "$TIMESTAMP" \
  '{
    id: $id,
    toolUseId: (if $tui == "" then null else $tui end),
    description: $desc,
    status: "pending",
    requested_at: $ts,
    launchedAt: $ts,
    started_at: $ts,
    pid: null,
    completedAt: null,
    outputSummary: null,
    expectedOutputs: [],
    checkCommand: null
  }' 2>/dev/null)

if [ -z "$NEW_TASK" ]; then
  exit 0
fi

# Use a lock file to prevent concurrent writes
LOCK_FILE="$TASKS_DIR/.active-tasks.lock"
exec 200>"$LOCK_FILE"
flock -w 2 200 2>/dev/null || true

# Add task to the tasks array and update lastUpdated
UPDATED=$(jq \
  --argjson task "$NEW_TASK" \
  --arg ts "$TIMESTAMP" \
  '.tasks += [$task] | .lastUpdated = $ts' \
  "$TASKS_FILE" 2>/dev/null)

if [ -n "$UPDATED" ]; then
  echo "$UPDATED" > "$TASKS_FILE"
fi

exec 200>&-

exit 0
