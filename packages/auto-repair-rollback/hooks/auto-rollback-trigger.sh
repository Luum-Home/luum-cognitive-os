#!/usr/bin/env bash
# SCOPE: both
# PostToolUse hook on Agent — detects verify-apply retry exhaustion and requests
# a human-approved rollback plan. It never executes destructive git commands.

set -uo pipefail
PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}}}"
HOOK_NAME="auto-rollback-trigger.sh"
_HOOK_NAME="auto-rollback-trigger"
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
METRICS_DIR="$(_resolve_metrics_dir)"
ROLLBACK_LOG="$METRICS_DIR/auto-rollback.jsonl"
INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
if [[ "$TOOL_NAME" != "Agent" && "$TOOL_NAME" != "task" && "$TOOL_NAME" != "delegate" ]]; then exit 0; fi
AGENT_OUTPUT=$(echo "$INPUT" | jq -r '.tool_result // .tool_response // .output // empty' 2>/dev/null)
if [[ -z "$AGENT_OUTPUT" ]]; then exit 0; fi
EXHAUSTION_DETECTED=false
CHANGE_NAME=""
if echo "$AGENT_OUTPUT" | grep -qiE 'Verify-apply loop exceeded [0-9]+ retries'; then EXHAUSTION_DETECTED=true; fi
if echo "$AGENT_OUTPUT" | grep -qiE 'max retries.*(exceeded|reached|exhausted).*verify'; then EXHAUSTION_DETECTED=true; fi
if echo "$AGENT_OUTPUT" | grep -qiE 'retry_count.*:.*3' && echo "$AGENT_OUTPUT" | grep -qiE 'verdict.*:.*FAIL'; then EXHAUSTION_DETECTED=true; fi
if [[ "$EXHAUSTION_DETECTED" == "false" ]]; then exit 0; fi
CHANGE_NAME=$(echo "$AGENT_OUTPUT" | grep -oiE '(change|feature|Change):[[:space:]]*[a-z0-9_-]+' | head -1 | sed -E 's/.*:[[:space:]]*//' || echo "")
if [[ -z "$CHANGE_NAME" ]]; then CHANGE_NAME=$(echo "$AGENT_OUTPUT" | grep -oiE 'sdd-apply[[:space:]]+[a-z0-9_-]+' | head -1 | awk '{print $2}' || echo "unknown"); fi
[ -z "$CHANGE_NAME" ] && CHANGE_NAME="unknown"
PHASE="reconstruction"
CONFIG_FILE="$PROJECT_DIR/cognitive-os.yaml"
if [[ -f "$CONFIG_FILE" ]] && command -v grep >/dev/null 2>&1; then
  DETECTED_PHASE=$(grep -oE 'phase:[[:space:]]*\S+' "$CONFIG_FILE" | head -1 | awk '{print $2}' || echo "")
  [[ -n "$DETECTED_PHASE" ]] && PHASE="$DETECTED_PHASE"
fi
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
mkdir -p "$METRICS_DIR" 2>/dev/null
ENTRY=$(jq -c -n --arg ts "$TIMESTAMP" --arg change "$CHANGE_NAME" --arg phase "$PHASE" '{timestamp: $ts, change: $change, phase: $phase, trigger: "verify-apply-exhaustion", mode: "plan_required", approval_required: true, destructive_commands_executed: false}')
safe_jsonl_append "$ROLLBACK_LOG" "$ENTRY"
cat <<EOF

=== ROLLBACK PLAN REQUIRED ===

Verify-apply loop exceeded max retries for change: $CHANGE_NAME
Phase: $PHASE

Human approval is required before any destructive git operation.
No git revert, git restore, git reset, git clean, stash mutation, branch deletion,
or worktree mutation was executed by this hook.

Required next step:
  1. Build a rollback evidence package with exact candidate commits, dirty worktree status, affected files, and verification commands.
  2. Ask the operator for explicit approval before running any destructive git.
  3. Keep hooks/destructive-git-blocker.sh enabled as the enforcement backstop.

Reference: ADR-107 Human-Approved Rollback Boundary

=== END ROLLBACK PLAN REQUIRED ===
EOF
exit 0
