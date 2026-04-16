#!/usr/bin/env bash
# PreToolUse hook: Register sub-agent tasks before launch
# Fires on "Agent" tool use — records task in active-tasks.json
# Must complete in <3 seconds

set -euo pipefail

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

# PID is not stored — the hook fires before the agent process starts,
# so $$ is the hook's own (already-exiting) PID, not the agent's.
# Health classification relies on age-based timeout only.

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
    status: "in_progress",
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
