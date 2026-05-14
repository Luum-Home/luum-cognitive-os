#!/usr/bin/env bash
# SCOPE: os-only
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


# ─── ADR-233 file-IPC task claim (optional) ─────────────────────────────────

claim_agent_team_task() {
  local team_name session_id os_root claim_json claim_status claim_title claim_id
  team_name=$(echo "$_STDIN_JSON" | jq -r '.team_name // .team // empty' 2>/dev/null | head -1 || true)
  session_id=$(echo "$_STDIN_JSON" | jq -r '.session_id // .agent_id // .teammate_id // empty' 2>/dev/null | head -1 || true)

  if [ -z "$team_name" ]; then
    team_name="${COS_AGENT_TEAM_NAME:-}"
  fi
  if [ -z "$session_id" ]; then
    session_id="${COGNITIVE_OS_SESSION_ID:-${CLAUDE_SESSION_ID:-unknown}}"
  fi
  if [ -z "$team_name" ] || ! command -v python3 >/dev/null 2>&1; then
    return 0
  fi

  os_root="$(cd "$(dirname "$0")/.." && pwd)"
  claim_json=$(PYTHONPATH="$os_root:${PYTHONPATH:-}" python3 - "$os_root" "$_PROJECT_DIR" "$team_name" "$session_id" <<'PYEOF' 2>/dev/null || true
import json
import sys
from dataclasses import asdict
from pathlib import Path

os_root, project_dir, team_name, session_id = sys.argv[1:5]
sys.path.insert(0, os_root)
from lib.agent_team import AgentTeam

team = AgentTeam(team_name, project_dir=Path(project_dir))
task = team.claim_next(session_id=session_id)
print(json.dumps({"task": asdict(task) if task else None}, sort_keys=True))
PYEOF
)
  claim_status=$(echo "$claim_json" | jq -r 'if .task == null then "none" else "claimed" end' 2>/dev/null || echo "none")
  if [ "$claim_status" = "claimed" ]; then
    claim_id=$(echo "$claim_json" | jq -r '.task.task_id' 2>/dev/null || echo "unknown")
    claim_title=$(echo "$claim_json" | jq -r '.task.title' 2>/dev/null || echo "unknown")
    log_idle_event "agent_team_claimed" 1
    echo "TEAMMATE_IDLE: claimed ADR-233 team task $claim_id."
    echo "Next team task: $claim_title"
    echo "Suggestion: complete this claimed task before going idle."
    exit 2
  fi
}

# ─── Check for unclaimed tasks ──────────────────────────────────────────────

claim_agent_team_task

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
