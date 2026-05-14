#!/usr/bin/env bash
# SCOPE: os-only
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
source "$(dirname "$0")/_lib/task-event.sh"

# Skip in private mode
check_private_mode

# Read stdin JSON (task details)
read_stdin_json

# ─── Metrics logging ────────────────────────────────────────────────────────

METRICS_DIR=$(resolve_session_dir)
METRICS_FILE="$METRICS_DIR/task-created.jsonl"

log_task_event() {
  cos_log_task_event "$METRICS_FILE" "$1" "${2:-}"
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


# ─── ADR-233 file-IPC task mirror (optional) ────────────────────────────────

mirror_agent_team_task() {
  local team_name task_id os_root
  team_name=$(echo "$_STDIN_JSON" | jq -r '.team_name // .team // empty' 2>/dev/null | head -1 || true)
  task_id=$(echo "$_STDIN_JSON" | jq -r '.task_id // .id // empty' 2>/dev/null | head -1 || true)

  if [ -z "$team_name" ]; then
    team_name="${COS_AGENT_TEAM_NAME:-}"
  fi
  if [ -z "$team_name" ] || ! command -v python3 >/dev/null 2>&1; then
    return 0
  fi

  os_root="$(cd "$(dirname "$0")/.." && pwd)"
  PYTHONPATH="$os_root:${PYTHONPATH:-}" python3 - "$os_root" "$_PROJECT_DIR" "$team_name" "$task_desc" "$task_id" <<'PYEOF' >/dev/null 2>&1 || true
import sys
from pathlib import Path

os_root, project_dir, team_name, title, task_id = sys.argv[1:6]
sys.path.insert(0, os_root)
from lib.agent_team import AgentTeam

team = AgentTeam(team_name, project_dir=Path(project_dir))
team.create_task(title, task_id=(task_id or None))
PYEOF
}

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

mirror_agent_team_task
log_task_event "allow" "passed_validation"
exit 0
