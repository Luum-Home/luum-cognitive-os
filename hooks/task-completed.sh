#!/usr/bin/env bash
# TaskCompleted hook: Verify completion criteria when a teammate marks a task done.
#
# Event: TaskCompleted
# Type: command
# Async: false
# Exit 0: Accept completion
# Exit 2: Reject completion (criteria not met)
#
# When a teammate marks a task as complete, this hook validates that
# basic completion signals are present: the output is not empty, and
# file claims can be partially verified. It also logs the completion
# to metrics and updates active-tasks.json if a matching task exists.

set -euo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

source "$(dirname "$0")/_lib/common.sh"

# Skip in private mode
check_private_mode

# Read stdin JSON (completion details)
read_stdin_json

# ─── Metrics logging ────────────────────────────────────────────────────────

METRICS_DIR=$(resolve_session_dir)
METRICS_FILE="$METRICS_DIR/task-completed.jsonl"

log_completion_event() {
  local action="$1"
  local reason="${2:-}"
  local timestamp
  timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%SZ")

  local entry="{\"timestamp\":\"$timestamp\",\"action\":\"$action\",\"reason\":\"$reason\"}"
  echo "$entry" >> "$METRICS_FILE" 2>/dev/null || true
}

# ─── Extract completion output ──────────────────────────────────────────────

task_output=$(echo "$_STDIN_JSON" | jq -r '.output // .result // .message // empty' 2>/dev/null | head -100 || true)
task_id=$(echo "$_STDIN_JSON" | jq -r '.task_id // .id // empty' 2>/dev/null || true)

# If no output at all, allow completion (graceful degradation — the hook
# should not break Teams if stdin format is unexpected)
if [ -z "$task_output" ]; then
  log_completion_event "allow" "no_output_field"
  exit 0
fi

# ─── Verify: output is not trivially empty ──────────────────────────────────

output_length=${#task_output}

if [ "$output_length" -lt 20 ]; then
  log_completion_event "reject" "output_too_short"
  echo "TASK_COMPLETED: REJECTED — Completion output is too short ($output_length chars)."
  echo "Provide a substantive completion report before marking done."
  exit 2
fi

# ─── Verify: check for trust report in production phases ────────────────────

phase=$(get_phase "reconstruction")

if [ "$phase" = "production" ] || [ "$phase" = "maintenance" ]; then
  has_trust_report=false
  if echo "$task_output" | grep -qE '(TRUST_REPORT:|Trust Report|Score: [0-9]+/100)' 2>/dev/null; then
    has_trust_report=true
  fi

  if [ "$has_trust_report" = "false" ]; then
    log_completion_event "reject" "missing_trust_report_in_$phase"
    echo "TASK_COMPLETED: REJECTED — Missing Trust Report in $phase phase."
    echo "All task completions must include a Trust Report with score."
    exit 2
  fi
fi

# ─── Update active-tasks.json if matching task found ────────────────────────

TASKS_FILE="$_PROJECT_DIR/.claude/tasks/active-tasks.json"

if [ -n "$task_id" ] && [ -f "$TASKS_FILE" ]; then
  # Check if this task exists in active-tasks.json and mark it completed
  task_exists=$(jq --arg id "$task_id" '.tasks[]? | select(.id == $id) | .id' "$TASKS_FILE" 2>/dev/null || true)

  if [ -n "$task_exists" ]; then
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%SZ")
    jq --arg id "$task_id" \
       --arg ts "$timestamp" \
       '(.tasks[] | select(.id == $id)) |= . + {status: "completed", completedAt: $ts}' \
       "$TASKS_FILE" > "${TASKS_FILE}.tmp" 2>/dev/null && \
       mv "${TASKS_FILE}.tmp" "$TASKS_FILE" 2>/dev/null || true
  fi
fi

# ─── All checks passed ─────────────────────────────────────────────────────

log_completion_event "accept" "passed_validation"
exit 0
