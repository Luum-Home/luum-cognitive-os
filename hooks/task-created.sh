#!/usr/bin/env bash
# TaskCreated hook: Validate task quality when created in the shared task list.
#
# Event: TaskCreated
# Type: command
# Async: false
# Exit 0: Allow task creation
# Exit 2: Block task creation (validation failed)
#
# When a task is added to the Agent Teams shared task list, this hook
# validates that the task has a meaningful description and does not
# duplicate an existing task. In production/maintenance phases, tasks
# without acceptance criteria are blocked.

set -euo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

source "$(dirname "$0")/_lib/common.sh"

# Skip in private mode
check_private_mode

# Read stdin JSON (task details)
read_stdin_json

# ─── Metrics logging ────────────────────────────────────────────────────────

METRICS_DIR=$(resolve_session_dir)
METRICS_FILE="$METRICS_DIR/task-created.jsonl"

log_task_event() {
  local action="$1"
  local reason="${2:-}"
  local timestamp
  timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%SZ")

  local entry="{\"timestamp\":\"$timestamp\",\"action\":\"$action\",\"reason\":\"$reason\"}"
  echo "$entry" >> "$METRICS_FILE" 2>/dev/null || true
}

# ─── Extract task description ───────────────────────────────────────────────

task_desc=$(echo "$_STDIN_JSON" | jq -r '.description // .task_description // .prompt // .message // empty' 2>/dev/null | head -5 || true)

# If we cannot extract a description, allow creation (graceful degradation)
if [ -z "$task_desc" ]; then
  log_task_event "allow" "no_description_field_in_json"
  exit 0
fi

# ─── Validate: description is not empty or too short ────────────────────────

desc_length=${#task_desc}

if [ "$desc_length" -lt 10 ]; then
  log_task_event "block" "description_too_short"
  echo "TASK_CREATED: BLOCKED — Task description is too short ($desc_length chars)."
  echo "Tasks must have a meaningful description (at least 10 characters)."
  exit 2
fi

# ─── Check for duplicate tasks ──────────────────────────────────────────────

TASKS_FILE="$_PROJECT_DIR/.claude/tasks/active-tasks.json"

if [ -f "$TASKS_FILE" ]; then
  # Extract first 50 chars of new task for comparison
  task_slug=$(echo "$task_desc" | head -1 | cut -c1-50 | tr '[:upper:]' '[:lower:]')

  # Check if a similar task already exists (in_progress or pending)
  existing=$(jq -r '.tasks[]? | select(.status == "pending" or .status == "in_progress") | .description // .id' "$TASKS_FILE" 2>/dev/null | tr '[:upper:]' '[:lower:]' || true)

  if echo "$existing" | grep -qF "$task_slug" 2>/dev/null; then
    log_task_event "warn" "possible_duplicate"
    echo "TASK_CREATED: WARNING — A similar task may already exist in active-tasks.json."
    echo "Check for duplicates before proceeding."
    # Advisory only — do not block
  fi
fi

# ─── Phase-aware: check for acceptance criteria in production ───────────────

phase=$(get_phase "reconstruction")

if [ "$phase" = "production" ] || [ "$phase" = "maintenance" ]; then
  # Check if task description contains acceptance criteria signals
  has_criteria=false
  if echo "$task_desc" | grep -qiE '(acceptance|criteria|verify|verification|expect|assert|should|must pass)' 2>/dev/null; then
    has_criteria=true
  fi

  if [ "$has_criteria" = "false" ]; then
    log_task_event "block" "missing_acceptance_criteria_in_$phase"
    echo "TASK_CREATED: BLOCKED — Task lacks acceptance criteria."
    echo "In $phase phase, all tasks must include verifiable acceptance criteria."
    exit 2
  fi
fi

# ─── All checks passed ─────────────────────────────────────────────────────

log_task_event "allow" "passed_validation"
exit 0
