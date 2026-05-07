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

# ADR-121: Detect read-only sub-agents to pass --allow-read-only to preflight.
# Whitelist: structurally read-only subagent types + explicit READ_ONLY marker.
SUBAGENT_TYPE=$(echo "$INPUT" | jq -r '.tool_input.subagent_type // empty' 2>/dev/null || true)
_RO_TYPES="Explore Plan Code Reviewer Security Engineer"
ALLOW_RO_ARG=""
if [[ " $_RO_TYPES " == *" $SUBAGENT_TYPE "* ]]; then
  ALLOW_RO_ARG="--allow-read-only"
elif echo "$DESCRIPTION" | grep -q "READ_ONLY: true" 2>/dev/null; then
  ALLOW_RO_ARG="--allow-read-only"
fi

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

# ADR-225: write/cloud/detached agents must run on their canonical task branch
# once the lifecycle lane declares branch-per-task enforcement. Generic legacy
# Agent launches stay advisory unless they explicitly opt into a write/cloud lane.
BRANCH_MODE=$(echo "$INPUT" | jq -r '.tool_input.lifecycle_mode // .tool_input.agent_mode // .tool_input.execution_mode // empty' 2>/dev/null | head -1 || true)
WRITE_CAPABLE=$(echo "$INPUT" | jq -r '.tool_input.write_capable // .tool_input.can_write // false' 2>/dev/null | head -1 || true)
BRANCH_ENFORCE=0
if [ "${COS_BRANCH_PER_TASK_ENFORCE:-0}" = "1" ]; then
  BRANCH_ENFORCE=1
elif echo "$BRANCH_MODE" | grep -qiE '^(write|cloud|detached|branch-per-task)$' 2>/dev/null; then
  BRANCH_ENFORCE=1
elif [ "$WRITE_CAPABLE" = "true" ] && echo "$DESCRIPTION" | grep -qiE 'BRANCH_PER_TASK: true|WRITE_AGENT: true' 2>/dev/null; then
  BRANCH_ENFORCE=1
fi

if [ "$BRANCH_ENFORCE" -eq 1 ] && [ "$ALLOW_RO_ARG" != "--allow-read-only" ] && [ "${COS_SKIP_BRANCH_PER_TASK_GATE:-0}" != "1" ]; then
  OS_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
  if command -v python3 >/dev/null 2>&1 && [ -x "$OS_ROOT/scripts/cos-branch-task-check" ]; then
    set +e
    BRANCH_CHECK_OUT=$("$OS_ROOT/scripts/cos-branch-task-check" --project-dir "$PROJECT_DIR" --task-id "$TASK_ID" --json --strict 2>&1)
    BRANCH_CHECK_RC=$?
    set -e
    if [ "$BRANCH_CHECK_RC" -ne 0 ]; then
      echo "ADR-225 BRANCH-PER-TASK PREFLIGHT BLOCK: write/cloud agent must run on canonical task branch." >&2
      echo "$BRANCH_CHECK_OUT" >&2
      echo "Command: scripts/cos agent worktree prepare --task-id '$TASK_ID' --session-id '$SESSION_ID' --json" >&2
      exit "$BRANCH_CHECK_RC"
    fi
  fi
fi

# ADR-220: before any Agent launch, prove linked worktrees are not silently
# divergent with overlapping dirty paths. This catches the "fix exists on main,
# stale worktree still shows old content" failure before another agent observes
# or mutates stale state.
if command -v python3 >/dev/null 2>&1 && [ -x "$PROJECT_DIR/scripts/cos-worktree-audit" ] && [ "${COS_SKIP_WORKTREE_DIVERGENCE_AUDIT:-0}" != "1" ]; then
  if git -C "$PROJECT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    WORKTREE_AUDIT_TMP=$(mktemp "${TMPDIR:-/tmp}/cos-worktree-audit.XXXXXX.json")
    WORKTREE_AUDIT_ERR=$(mktemp "${TMPDIR:-/tmp}/cos-worktree-audit.XXXXXX.err")
    set +e
    "$PROJECT_DIR/scripts/cos-worktree-audit" --project-dir "$PROJECT_DIR" --json --strict >"$WORKTREE_AUDIT_TMP" 2>"$WORKTREE_AUDIT_ERR"
    WORKTREE_AUDIT_RC=$?
    set -e
    if [ "$WORKTREE_AUDIT_RC" -ne 0 ]; then
      echo "ADR-220 WORKTREE PREFLIGHT BLOCK: linked worktree divergence may hide or overwrite WIP before Agent launch." >&2
      [ -s "$WORKTREE_AUDIT_ERR" ] && cat "$WORKTREE_AUDIT_ERR" >&2
      command -v python3 >/dev/null 2>&1 && python3 - "$WORKTREE_AUDIT_TMP" <<'PYEOF' >&2 || cat "$WORKTREE_AUDIT_TMP" >&2
import json, sys
from pathlib import Path
try:
    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
except Exception:
    print(Path(sys.argv[1]).read_text(encoding="utf-8")[:4000])
    raise SystemExit(0)
summary = payload.get("summary", {})
print(
    "ADR-220 worktree audit summary: "
    f"status={payload.get('status')} worktrees={summary.get('worktree_count', 0)} "
    f"blockers={summary.get('block_count', 0)} warnings={summary.get('warn_count', 0)}"
)
for finding in (payload.get("findings") or [])[:8]:
    print(f"- {finding.get('level')} {finding.get('code')} {finding.get('subject')}: {finding.get('detail')}")
    if finding.get("action"):
        print(f"  action: {finding.get('action')}")
print("Command: scripts/cos worktree audit --json --strict")
PYEOF
      rm -f "$WORKTREE_AUDIT_TMP" "$WORKTREE_AUDIT_ERR"
      exit "$WORKTREE_AUDIT_RC"
    fi
    rm -f "$WORKTREE_AUDIT_TMP" "$WORKTREE_AUDIT_ERR"
  fi
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


_cos_inventory_auto_stash_only() {
  command -v python3 >/dev/null 2>&1 || return 1
  python3 - "$1" <<'PYEOF'
import json, sys
from pathlib import Path
try:
    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
except Exception:
    sys.exit(1)

def is_auto(stash):
    subject = str(stash.get("subject") or "")
    return bool(stash.get("is_auto_pre_agent")) or "auto-pre-agent" in subject

blockers = [f for f in payload.get("findings", []) if f.get("level") == "BLOCK"]
if not blockers:
    sys.exit(1)
allowed_codes = {"stash-aged", "linked-worktree-stashes-present"}
if any(f.get("code") not in allowed_codes for f in blockers):
    sys.exit(1)

all_stashes = []
all_stashes.extend(payload.get("stashes_extended") or payload.get("stashes") or [])
for group in payload.get("worktree_stashes", []):
    all_stashes.extend(group.get("stashes") or [])
blocking_stashes = [s for s in all_stashes if (s.get("level") == "BLOCK" or is_auto(s))]
if not blocking_stashes:
    sys.exit(1)
if not all(is_auto(s) for s in blocking_stashes):
    sys.exit(1)
for risk in payload.get("race_risks", []):
    details = "\n".join(str(d) for d in risk.get("details", []))
    if risk.get("code") == "stale-orphan-stash" and "auto-pre-agent" not in details:
        sys.exit(1)
print("auto-pre-agent-only")
PYEOF
}

_cos_print_inventory_compact() {
  command -v python3 >/dev/null 2>&1 || { cat "$1" >&2; return 0; }
  python3 - "$1" <<'PYEOF' >&2
import json, sys
from pathlib import Path
try:
    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
except Exception:
    print(Path(sys.argv[1]).read_text(encoding="utf-8")[:4000])
    raise SystemExit(0)
summary = payload.get("summary", {})
print(
    "ADR-116 preflight summary: "
    f"blockers={summary.get('blockers', 0)} warnings={summary.get('warnings', 0)} "
    f"stashes={summary.get('stash_count', 0)} worktree_stashes={summary.get('worktree_stash_count', 0)} "
    f"race_risks={summary.get('race_risk_count', 0)}"
)
findings = payload.get("findings", [])
if findings:
    print("Findings:")
    for finding in findings[:8]:
        print(f"- {finding.get('level')} {finding.get('code')} {finding.get('subject')}: {finding.get('detail')}")
        action = finding.get("action")
        if action:
            print(f"  action: {action}")
if len(findings) > 8:
    print(f"- ... {len(findings) - 8} more finding(s) omitted")
risks = payload.get("race_risks", [])
if risks:
    print("Race risks:")
    for risk in risks[:5]:
        print(f"- {risk.get('code')}: {risk.get('description')}")
        for detail in (risk.get("details") or [])[:3]:
            print(f"  {detail}")
print("Commands:")
print("- Auto-stash repair: scripts/cos stash cleanup --execute")
print("- Full JSON: python3 scripts/cos_work_inventory.py --all --strict --json")
PYEOF
}

if command -v python3 >/dev/null 2>&1 && [ -x "$PROJECT_DIR/scripts/cos_work_inventory.py" ] && [ "${COS_SKIP_GOVERNED_INVENTORY:-0}" != "1" ]; then
  # Work inventory is a git-backed coordination gate. Consumer/project test
  # fixtures can exercise Agent hooks before git init; those fixtures should
  # still get task claims and resource leases instead of being blocked by a
  # non-applicable repository inventory check.
  if git -C "$PROJECT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    INVENTORY_TMP=$(mktemp "${TMPDIR:-/tmp}/cos-inventory.XXXXXX.json")
    INVENTORY_ERR=$(mktemp "${TMPDIR:-/tmp}/cos-inventory.XXXXXX.err")
    set +e
    python3 "$PROJECT_DIR/scripts/cos_work_inventory.py" --project-dir "$PROJECT_DIR" --all --strict --json $ALLOW_RO_ARG >"$INVENTORY_TMP" 2>"$INVENTORY_ERR"
    INVENTORY_RC=$?
    set -e
    if [ "$INVENTORY_RC" -ne 0 ] && [ -x "$PROJECT_DIR/scripts/state_retention_audit.py" ] && _cos_inventory_auto_stash_only "$INVENTORY_TMP" >/dev/null 2>&1; then
      echo "ADR-199 PREFLIGHT REPAIR: stale auto-pre-agent stash residue detected; archiving and cleaning once before blocking." >&2
      python3 "$PROJECT_DIR/scripts/state_retention_audit.py" --project-dir "$PROJECT_DIR" --repair-before-block --reap --execute --cooldown-seconds "${COS_STATE_RETENTION_PREFLIGHT_COOLDOWN_SECONDS:-300}" --no-metrics >/dev/null 2>&1 || true
      set +e
      python3 "$PROJECT_DIR/scripts/cos_work_inventory.py" --project-dir "$PROJECT_DIR" --all --strict --json $ALLOW_RO_ARG >"$INVENTORY_TMP" 2>"$INVENTORY_ERR"
      INVENTORY_RC=$?
      set -e
    fi
    if [ "$INVENTORY_RC" -ne 0 ]; then
      echo "ADR-116 GOVERNED PREFLIGHT BLOCK: cos_work_inventory.py --all --strict failed before Agent launch." >&2
      [ -s "$INVENTORY_ERR" ] && cat "$INVENTORY_ERR" >&2
      _cos_print_inventory_compact "$INVENTORY_TMP"
      rm -f "$INVENTORY_TMP" "$INVENTORY_ERR"
      if [ "$ACTIVE_CLAIM_ACQUIRED" -eq 1 ]; then
        python3 "$PROJECT_DIR/scripts/cos_task_claims.py" --project-dir "$PROJECT_DIR" \
          release --task-id "$TASK_ID" --session-id "$SESSION_ID" >/dev/null 2>&1 || true
      fi
      python3 "$PROJECT_DIR/scripts/claim_task.py" --project-dir "$PROJECT_DIR" \
        release "$TASK_ID" --session-id "$SESSION_ID" --agent-id "$AGENT_LEDGER_ID" >/dev/null 2>&1 || true
      exit "$INVENTORY_RC"
    fi
    rm -f "$INVENTORY_TMP" "$INVENTORY_ERR"
  fi
fi


AGENT_WORKTREE_CONTEXT=""
if [ "${COS_AGENT_LIFECYCLE_MODE:-worktree}" = "worktree" ] && [ -z "$ALLOW_RO_ARG" ] && [ -x "$PROJECT_DIR/scripts/cos-agent-worktree-prepare" ] && git -C "$PROJECT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  set +e
  WORKTREE_OUT=$("$PROJECT_DIR/scripts/cos-agent-worktree-prepare" --project-dir "$PROJECT_DIR" --task-id "$TASK_ID" --session-id "$SESSION_ID" --json 2>&1)
  WORKTREE_RC=$?
  set -e
  if [ "$WORKTREE_RC" -ne 0 ]; then
    echo "ADR-223 AGENT LIFECYCLE BLOCK: failed to prepare dedicated write-agent worktree." >&2
    echo "$WORKTREE_OUT" >&2
    exit 2
  fi
  if command -v jq >/dev/null 2>&1; then
    AGENT_WORKTREE_PATH=$(printf '%s' "$WORKTREE_OUT" | jq -r '.worktree_path // empty' 2>/dev/null || true)
    AGENT_WORKTREE_BRANCH=$(printf '%s' "$WORKTREE_OUT" | jq -r '.branch // empty' 2>/dev/null || true)
    if [ -n "$AGENT_WORKTREE_PATH" ]; then
      mkdir -p "$PROJECT_DIR/.cognitive-os/runtime" 2>/dev/null || true
      printf '{"schema_version":"agent-lifecycle-snapshot-suppression/v1","agent_id":"%s","task_id":"%s","session_id":"%s","worktree_path":"%s","branch":"%s","created_at":"%s"}
' \
        "$AGENT_LEDGER_ID" "$TASK_ID" "$SESSION_ID" "$AGENT_WORKTREE_PATH" "$AGENT_WORKTREE_BRANCH" "$TIMESTAMP" \
        > "$PROJECT_DIR/.cognitive-os/runtime/suppress-agent-snapshot-${AGENT_LEDGER_ID}.json" 2>/dev/null || true
      AGENT_WORKTREE_CONTEXT="WORKING DIR: $AGENT_WORKTREE_PATH
(ADR-223: dedicated worktree-per-write-agent, branch=$AGENT_WORKTREE_BRANCH.)
Do not write in the operator worktree. Scope git commands with: git -C "$AGENT_WORKTREE_PATH" ..."
    fi
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

if [ -n "${AGENT_WORKTREE_CONTEXT:-}" ]; then
  if command -v python3 >/dev/null 2>&1; then
    AGENT_WORKTREE_CONTEXT="$AGENT_WORKTREE_CONTEXT" python3 - <<'PYEOF'
import json, os
print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": os.environ.get("AGENT_WORKTREE_CONTEXT", "")}}))
PYEOF
  fi
fi

exit 0
