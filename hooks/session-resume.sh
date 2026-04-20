#!/usr/bin/env bash
# SCOPE: os-only
# SessionStart hook: Auto-detect incomplete tasks from previous sessions
# Checks active-tasks.json for in_progress/failed tasks and verifies their state
# Must complete in <3 seconds

set -euo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

TASKS_DIR="${CLAUDE_PROJECT_DIR:-.}/.cognitive-os/tasks"
TASKS_FILE="$TASKS_DIR/active-tasks.json"

# Exit silently if no tasks file
if [ ! -f "$TASKS_FILE" ]; then
  exit 0
fi

# Require jq
if ! command -v jq &>/dev/null; then
  exit 0
fi

# Count incomplete tasks
INCOMPLETE_COUNT=$(jq '[.tasks[] | select(.status == "in_progress" or .status == "failed")] | length' "$TASKS_FILE" 2>/dev/null)

if [ "$INCOMPLETE_COUNT" = "0" ] || [ -z "$INCOMPLETE_COUNT" ]; then
  exit 0
fi

# Get incomplete tasks
INCOMPLETE_TASKS=$(jq -c '[.tasks[] | select(.status == "in_progress" or .status == "failed")]' "$TASKS_FILE" 2>/dev/null)

# Build output report
REPORT=""
NEEDS_RELAUNCH=0
AUTO_COMPLETED=0
CHANGED=false

# Process each incomplete task
while IFS= read -r TASK; do
  TASK_ID=$(echo "$TASK" | jq -r '.id')
  TASK_DESC=$(echo "$TASK" | jq -r '.description' | head -c 80)
  TASK_STATUS=$(echo "$TASK" | jq -r '.status')
  CHECK_CMD=$(echo "$TASK" | jq -r '.checkCommand // empty')
  EXPECTED=$(echo "$TASK" | jq -c '.expectedOutputs // []')

  WORK_EXISTS=false

  # Check via checkCommand if defined
  if [ -n "$CHECK_CMD" ] && [ "$CHECK_CMD" != "null" ]; then
    if eval "$CHECK_CMD" &>/dev/null 2>&1; then
      WORK_EXISTS=true
    fi
  fi

  # Check via expectedOutputs if defined and checkCommand didn't confirm
  if [ "$WORK_EXISTS" = "false" ]; then
    OUTPUT_COUNT=$(echo "$EXPECTED" | jq 'length' 2>/dev/null)
    if [ "$OUTPUT_COUNT" -gt 0 ] 2>/dev/null; then
      ALL_EXIST=true
      while IFS= read -r FILEPATH; do
        if [ ! -e "$FILEPATH" ]; then
          ALL_EXIST=false
          break
        fi
      done < <(echo "$EXPECTED" | jq -r '.[]' 2>/dev/null)
      if [ "$ALL_EXIST" = "true" ]; then
        WORK_EXISTS=true
      fi
    fi
  fi

  if [ "$WORK_EXISTS" = "true" ]; then
    REPORT="${REPORT}\n  [COMPLETED] ${TASK_DESC} (outputs verified present)"
    AUTO_COMPLETED=$((AUTO_COMPLETED + 1))
    # Mark as completed in the tasks file
    TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    TASKS_FILE_CONTENT=$(jq \
      --arg id "$TASK_ID" \
      --arg ts "$TIMESTAMP" \
      '(.tasks[] | select(.id == $id)) |= . + {status: "completed", completedAt: $ts, outputSummary: "Auto-recovered: outputs verified present"}' \
      "$TASKS_FILE" 2>/dev/null)
    if [ -n "$TASKS_FILE_CONTENT" ]; then
      echo "$TASKS_FILE_CONTENT" > "$TASKS_FILE"
      CHANGED=true
    fi
  else
    REPORT="${REPORT}\n  [NEEDS RELAUNCH] ${TASK_DESC} (${TASK_STATUS}, outputs missing)"
    NEEDS_RELAUNCH=$((NEEDS_RELAUNCH + 1))
  fi
done < <(echo "$INCOMPLETE_TASKS" | jq -c '.[]' 2>/dev/null)

# Output the report (this goes to Claude's context)
TOTAL=$((AUTO_COMPLETED + NEEDS_RELAUNCH))
echo ""
echo "WARNING: Found ${TOTAL} incomplete task(s) from previous session:"
echo -e "$REPORT"
echo ""

if [ "$NEEDS_RELAUNCH" -gt 0 ]; then
  echo "Action required: ${NEEDS_RELAUNCH} task(s) need to be re-launched."
  echo "Run /resume-tasks to review and re-launch incomplete tasks, or inspect .cognitive-os/tasks/active-tasks.json manually."
fi

if [ "$AUTO_COMPLETED" -gt 0 ]; then
  echo "${AUTO_COMPLETED} task(s) were auto-marked as completed (outputs verified present)."
fi

exit 0
