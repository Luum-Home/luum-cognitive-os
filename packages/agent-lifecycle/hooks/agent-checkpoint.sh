#!/usr/bin/env bash
# CONCERNS: state, lifecycle, orchestration
# PostToolUse hook: Update sub-agent task status after completion
# Fires on "Agent" tool use — updates task in active-tasks.json
# Must complete in <3 seconds

set -euo pipefail

source "$(dirname "$0")/_lib/common.sh"

# Read stdin and gate on Agent tool
read_stdin_json
INPUT="$_STDIN_JSON"
require_tool "Agent"

TASKS_DIR="$_PROJECT_DIR/.cognitive-os/tasks"
TASKS_FILE="$TASKS_DIR/active-tasks.json"

# Exit if tasks file doesn't exist
if [ ! -f "$TASKS_FILE" ]; then
  exit 0
fi

# Exit early if no input or no jq
if [ -z "$INPUT" ]; then
  exit 0
fi
if ! command -v jq &>/dev/null; then
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

# ── Timeout detection ────────────────────────────────────────────────────────
# Read agent_timeout_seconds from cognitive-os.yaml (default: 300)
TIMEOUT_SECS=300
CONFIG_FILE="$_PROJECT_DIR/cognitive-os.yaml"
[ ! -f "$CONFIG_FILE" ] && CONFIG_FILE="$_PROJECT_DIR/.cognitive-os/cognitive-os.yaml"
if [ -f "$CONFIG_FILE" ]; then
  PARSED_TIMEOUT=$(grep 'agent_timeout_seconds:' "$CONFIG_FILE" 2>/dev/null | head -1 \
    | sed 's/.*agent_timeout_seconds:[[:space:]]*//' | tr -d '[:space:]' | grep -E '^[0-9]+$' || true)
  [ -n "$PARSED_TIMEOUT" ] && TIMEOUT_SECS="$PARSED_TIMEOUT"
fi

# Re-read the updated task to get its timestamps
if [ -f "$TASKS_FILE" ] && command -v jq &>/dev/null; then
  MATCH_PREFIX_TIMEOUT=$(echo "$DESCRIPTION" | head -c 50)

  # Fetch the task we just updated (by prefix match, last completed/failed entry)
  TASK_DATA=$(jq -r \
    --arg prefix "$MATCH_PREFIX_TIMEOUT" \
    --arg ts "$TIMESTAMP" \
    '
    (.tasks | to_entries
      | map(select(
          (.value.status == "completed" or .value.status == "failed")
          and (.value.description[0:50] == $prefix)
          and (.value.completedAt == $ts)
        ))
      | last // null
    )' "$TASKS_FILE" 2>/dev/null)

  if [ -n "$TASK_DATA" ] && [ "$TASK_DATA" != "null" ]; then
    LAUNCHED_AT=$(echo "$TASK_DATA" | jq -r '.value.launchedAt // ""' 2>/dev/null)
    TASK_ID=$(echo "$TASK_DATA" | jq -r '.value.id // ""' 2>/dev/null)
    TASK_DESC=$(echo "$TASK_DATA" | jq -r '.value.description // ""' 2>/dev/null | head -c 200)

    if [ -n "$LAUNCHED_AT" ] && [ -n "$TASK_ID" ]; then
      # Calculate duration in seconds using Python (portable, handles ISO8601)
      DURATION=$(python3 -c "
import sys
from datetime import datetime, timezone

def parse_iso(s):
    s = s.rstrip('Z')
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)

try:
    launched = parse_iso('$LAUNCHED_AT')
    completed = parse_iso('$TIMESTAMP')
    print(int((completed - launched).total_seconds()))
except Exception:
    print(0)
" 2>/dev/null || echo "0")

      if [ "$DURATION" -gt "$TIMEOUT_SECS" ] 2>/dev/null; then
        # Mark task as slow
        exec 200>"$LOCK_FILE"
        flock -w 2 200 2>/dev/null || true
        SLOW_UPDATED=$(jq \
          --arg id "$TASK_ID" \
          'if (.tasks | map(select(.id == $id)) | length) > 0
           then (.tasks[] | select(.id == $id)) |= . + {"slow": true}
           else .
           end' "$TASKS_FILE" 2>/dev/null)
        [ -n "$SLOW_UPDATED" ] && echo "$SLOW_UPDATED" > "$TASKS_FILE"
        exec 200>&-

        # Log to metrics
        METRICS_DIR="$_PROJECT_DIR/.cognitive-os/metrics"
        mkdir -p "$METRICS_DIR" 2>/dev/null
        TIMEOUT_LOG="$METRICS_DIR/agent-timeouts.jsonl"
        printf '{"timestamp":"%s","task_id":"%s","duration_secs":%s,"timeout":%s,"description":"%s"}\n' \
          "$TIMESTAMP" "$TASK_ID" "$DURATION" "$TIMEOUT_SECS" \
          "$(echo "$TASK_DESC" | sed 's/"/\\"/g')" \
          >> "$TIMEOUT_LOG" 2>/dev/null || true
      fi
    fi
  fi
fi

exit 0
