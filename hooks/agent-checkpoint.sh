#!/usr/bin/env bash
# PostToolUse hook: Update sub-agent task status after completion
# Fires on "Agent" tool use — updates task in active-tasks.json
# Must complete in <3 seconds

set -euo pipefail

TASKS_DIR="${CLAUDE_PROJECT_DIR:-.}/.cognitive-os/tasks"
TASKS_FILE="$TASKS_DIR/active-tasks.json"

# Exit if tasks file doesn't exist
if [ ! -f "$TASKS_FILE" ]; then
  exit 0
fi

# Read stdin (JSON with tool_name, tool_input, tool_response)
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

# Extract agent description to match against registered tasks
DESCRIPTION=$(echo "$INPUT" | jq -r '
  .tool_input.description // .tool_input.prompt // ""
' 2>/dev/null | head -c 500)

if [ -z "$DESCRIPTION" ] || [ "$DESCRIPTION" = "null" ]; then
  exit 0
fi

# Determine if the agent completed successfully or failed
SUCCESS=$(echo "$INPUT" | jq -r '
  if .tool_response.error then "failed"
  elif .tool_response.is_error then "failed"
  elif (.tool_response.status // "ok") == "error" then "failed"
  else "completed"
  end
' 2>/dev/null)

# Extract a brief output summary (first 300 chars of response)
OUTPUT_SUMMARY=$(echo "$INPUT" | jq -r '
  .tool_response.result // .tool_response.output // .tool_response.content // "no output captured"
' 2>/dev/null | head -c 300)

# Get current timestamp
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Use a lock file to prevent concurrent writes
LOCK_FILE="$TASKS_DIR/.active-tasks.lock"
exec 200>"$LOCK_FILE"
flock -w 2 200 2>/dev/null || true

# Find the most recent in_progress task matching this description and update it
# Match by checking if the stored description starts with the same prefix
MATCH_PREFIX=$(echo "$DESCRIPTION" | head -c 50)
UPDATED=$(jq \
  --arg prefix "$MATCH_PREFIX" \
  --arg status "$SUCCESS" \
  --arg ts "$TIMESTAMP" \
  --arg summary "$OUTPUT_SUMMARY" \
  '
  # Find the last in_progress task whose description starts with the same prefix
  (.tasks | to_entries | map(select(.value.status == "in_progress" and (.value.description[0:50] == $prefix))) | last // null) as $match |
  if $match then
    .tasks[$match.key].status = $status |
    .tasks[$match.key].completedAt = $ts |
    .tasks[$match.key].outputSummary = $summary |
    .lastUpdated = $ts
  else
    # No exact match — update the most recent in_progress task
    (.tasks | to_entries | map(select(.value.status == "in_progress")) | last // null) as $fallback |
    if $fallback then
      .tasks[$fallback.key].status = $status |
      .tasks[$fallback.key].completedAt = $ts |
      .tasks[$fallback.key].outputSummary = $summary |
      .lastUpdated = $ts
    else .
    end
  end
  ' "$TASKS_FILE" 2>/dev/null)

if [ -n "$UPDATED" ]; then
  echo "$UPDATED" > "$TASKS_FILE"
fi

exec 200>&-

exit 0
