#!/usr/bin/env bash
# SCOPE: both
# PreToolUse hook: Register sub-agent tasks before launch
# Fires on "Agent" tool use — records task in active-tasks.json
# Must complete in <3 seconds

set -euo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"
source "$(dirname "${BASH_SOURCE[0]}")/_lib/task-identity.sh"

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"
TASKS_DIR="$PROJECT_DIR/.cognitive-os/tasks"
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

# Get current timestamp
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

SESSION_ID="${COGNITIVE_OS_SESSION_ID:-default-session}"
TASK_ID=$(cos_resolve_task_id "$INPUT" "$DESCRIPTION" "$TOOL_USE_ID")
AGENT_LEDGER_ID="$TASK_ID"
if [ -n "$TOOL_USE_ID" ] && [ "$TOOL_USE_ID" != "null" ]; then
  AGENT_LEDGER_ID="$TOOL_USE_ID"
fi

# ADR-116 P1.1/P3.3: acquire the shared active task claim and prove the
# coordination surface is clean before recording or launching the agent.
ACTIVE_CLAIM_ACQUIRED=0
if command -v python3 >/dev/null 2>&1 && [ -x "$PROJECT_DIR/scripts/cos_task_claims.py" ]; then
  set +e
  ACTIVE_CLAIM_OUT=$(python3 "$PROJECT_DIR/scripts/cos_task_claims.py" --project-dir "$PROJECT_DIR" \
    claim --task-id "$TASK_ID" --session-id "$SESSION_ID" --description "$DESCRIPTION" 2>&1)
  ACTIVE_CLAIM_RC=$?
  set -e
  if [ "$ACTIVE_CLAIM_RC" -eq 2 ]; then
    echo "ADR-116 ACTIVE TASK CLAIM BLOCK: task '$TASK_ID' is already claimed by another session." >&2
    echo "$ACTIVE_CLAIM_OUT" >&2
    exit 2
  elif [ "$ACTIVE_CLAIM_RC" -eq 0 ]; then
    ACTIVE_CLAIM_ACQUIRED=1
  elif [ "$ACTIVE_CLAIM_RC" -ne 0 ]; then
    echo "$ACTIVE_CLAIM_OUT" >&2
    exit "$ACTIVE_CLAIM_RC"
  fi
fi

if command -v python3 >/dev/null 2>&1 && [ -x "$PROJECT_DIR/scripts/claim_task.py" ]; then
  set +e
  CLAIM_OUT=$(python3 "$PROJECT_DIR/scripts/claim_task.py" --project-dir "$PROJECT_DIR" \
    acquire "$TASK_ID" --agent-id "$AGENT_LEDGER_ID" --session-id "$SESSION_ID" \
    --scope "$DESCRIPTION" --ttl-seconds 1800 2>&1)
  CLAIM_RC=$?
  set -e
  if [ "$CLAIM_RC" -eq 2 ]; then
    echo "ADR-116 TASK CLAIM BLOCK: task '$TASK_ID' is already claimed by another session." >&2
    echo "$CLAIM_OUT" >&2
    if [ "$ACTIVE_CLAIM_ACQUIRED" -eq 1 ]; then
      python3 "$PROJECT_DIR/scripts/cos_task_claims.py" --project-dir "$PROJECT_DIR" \
        release --task-id "$TASK_ID" --session-id "$SESSION_ID" >/dev/null 2>&1 || true
    fi
    exit 2
  fi
fi

if command -v python3 >/dev/null 2>&1 && [ -x "$PROJECT_DIR/scripts/cos_work_inventory.py" ] && [ "${COS_SKIP_GOVERNED_INVENTORY:-0}" != "1" ]; then
  set +e
  INVENTORY_OUT=$(python3 "$PROJECT_DIR/scripts/cos_work_inventory.py" --project-dir "$PROJECT_DIR" --all --strict --json 2>&1)
  INVENTORY_RC=$?
  set -e
  if [ "$INVENTORY_RC" -ne 0 ]; then
    echo "ADR-116 GOVERNED PREFLIGHT BLOCK: cos_work_inventory.py --all --strict failed before Agent launch." >&2
    echo "$INVENTORY_OUT" >&2
    if [ "$ACTIVE_CLAIM_ACQUIRED" -eq 1 ]; then
      python3 "$PROJECT_DIR/scripts/cos_task_claims.py" --project-dir "$PROJECT_DIR" \
        release --task-id "$TASK_ID" --session-id "$SESSION_ID" >/dev/null 2>&1 || true
    fi
    python3 "$PROJECT_DIR/scripts/claim_task.py" --project-dir "$PROJECT_DIR" \
      release "$TASK_ID" --session-id "$SESSION_ID" --agent-id "$AGENT_LEDGER_ID" >/dev/null 2>&1 || true
    exit "$INVENTORY_RC"
  fi
fi

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

# ADR-108: record automatic agent work start and acquire cooperative leases
# for critical domains mentioned in the task prompt. These calls are best-effort
# except lease contention, which blocks the agent launch to prevent concurrent
# mutation of a shared logical primitive.
if command -v python3 >/dev/null 2>&1; then
  python3 "$PROJECT_DIR/scripts/agent_work_ledger.py" --project-dir "$PROJECT_DIR" \
    record --agent-id "$AGENT_LEDGER_ID" --session-id "$SESSION_ID" \
    --task "$TASK_ID" --status started --scope "$DESCRIPTION" >/dev/null 2>&1 || true

  DOMAINS=$(python3 - "$PROJECT_DIR" <<'PYEOF' 2>/dev/null || true
import sys
sys.path.insert(0, sys.argv[1])
try:
    from lib.concurrency_safety import load_concurrency_safety_config
    cfg = load_concurrency_safety_config(sys.argv[1] + "/cognitive-os.yaml")
    print("\n".join(cfg.resource_leases.critical_domains))
except Exception:
    print("auth\nbilling\nmigrations\ninfrastructure")
PYEOF
)
  DESCRIPTION_LOWER=$(printf '%s' "$DESCRIPTION" | tr '[:upper:]' '[:lower:]')
  while IFS= read -r domain; do
    [ -z "$domain" ] && continue
    domain_lower=$(printf '%s' "$domain" | tr '[:upper:]' '[:lower:]')
    domain_singular="${domain_lower%s}"
    if printf '%s' "$DESCRIPTION_LOWER" | grep -Eq "(^|[^[:alnum:]_-])(${domain_lower}|${domain_singular})([^[:alnum:]_-]|$)"; then
      set +e
      LEASE_OUT=$(python3 "$PROJECT_DIR/scripts/resource_lease.py" --project-dir "$PROJECT_DIR" \
        acquire "$domain" --agent-id "$AGENT_LEDGER_ID" --session-id "$SESSION_ID" \
        --reason "Agent task $TASK_ID: $(printf '%s' "$DESCRIPTION" | head -c 120)" 2>&1)
      LEASE_RC=$?
      set -e
      if [ "$LEASE_RC" -eq 2 ]; then
        echo "ADR-108 RESOURCE LEASE BLOCK: resource '$domain' is already leased." >&2
        echo "$LEASE_OUT" >&2
        exit 2
      fi
    fi
  done <<< "$DOMAINS"
fi

exit 0
