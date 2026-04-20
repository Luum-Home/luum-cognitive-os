#!/usr/bin/env bash
# TeammateIdle hook: Check for unclaimed tasks when a teammate is about to go idle.
#
# Event: TeammateIdle
# Type: command
# Async: false
# Exit 0: Allow teammate to go idle
# Exit 2: Keep teammate working (suggest next task)
#
# When a teammate has no more tasks to claim and is about to shut down,
# this hook checks active-tasks.json for pending tasks that could be assigned.
# If pending tasks exist, it outputs a suggestion and exits 2 to keep the
# teammate active.

set -euo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

source "$(dirname "$0")/_lib/common.sh"

# Skip in private mode
check_private_mode

# Read stdin JSON (teammate details)
read_stdin_json

# ─── Metrics logging ────────────────────────────────────────────────────────

METRICS_DIR=$(resolve_session_dir)
METRICS_FILE="$METRICS_DIR/teammate-idle.jsonl"

log_idle_event() {
  local action="$1"
  local pending_count="${2:-0}"
  local timestamp
  timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%SZ")

  local entry="{\"timestamp\":\"$timestamp\",\"action\":\"$action\",\"pending_tasks\":$pending_count}"
  echo "$entry" >> "$METRICS_FILE" 2>/dev/null || true
}

# ─── Check for unclaimed tasks ──────────────────────────────────────────────

TASKS_FILE="$_PROJECT_DIR/.claude/tasks/active-tasks.json"

# If no active tasks file, allow idle
if [ ! -f "$TASKS_FILE" ]; then
  log_idle_event "idle_no_tasks_file" 0
  exit 0
fi

# Count pending tasks
pending_count=$(jq '[.tasks[]? | select(.status == "pending")] | length' "$TASKS_FILE" 2>/dev/null || echo "0")

if [ "$pending_count" -gt 0 ]; then
  # Get the first pending task description
  next_task=$(jq -r '[.tasks[] | select(.status == "pending")][0].description // "unnamed task"' "$TASKS_FILE" 2>/dev/null || echo "unknown")

  log_idle_event "redirect" "$pending_count"

  echo "TEAMMATE_IDLE: $pending_count pending task(s) remain in active-tasks.json."
  echo "Next unclaimed task: $next_task"
  echo "Suggestion: Claim the next pending task before going idle."

  # Exit 2 to keep teammate active
  exit 2
fi

# No pending tasks — allow idle
log_idle_event "idle_ok" 0
exit 0
