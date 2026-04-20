#!/usr/bin/env bash
# PostToolUse hook on Agent — detects when verify-apply loop exceeds max retries
# and triggers the auto-rollback skill.
# Looks for "Verify-apply loop exceeded 3 retries" in agent response.

set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="auto-rollback-trigger"
source "$(dirname "$0")/_lib/safe-jsonl.sh"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
METRICS_DIR="$(_resolve_metrics_dir)"
ROLLBACK_LOG="$METRICS_DIR/auto-rollback.jsonl"

# Read input from stdin
INPUT=$(cat)

# Only process Agent tool results
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
if [[ "$TOOL_NAME" != "Agent" && "$TOOL_NAME" != "task" && "$TOOL_NAME" != "delegate" ]]; then
  exit 0
fi

# Get agent output
AGENT_OUTPUT=$(echo "$INPUT" | jq -r '.tool_result // .tool_response // .output // empty' 2>/dev/null)
if [[ -z "$AGENT_OUTPUT" ]]; then
  exit 0
fi

# Check for verify-apply loop exhaustion pattern
EXHAUSTION_DETECTED=false
CHANGE_NAME=""

# Pattern 1: Explicit message from orchestrator
if echo "$AGENT_OUTPUT" | grep -qiE 'Verify-apply loop exceeded [0-9]+ retries'; then
  EXHAUSTION_DETECTED=true
fi

# Pattern 2: Max retries reached in verify context
if echo "$AGENT_OUTPUT" | grep -qiE 'max retries.*(exceeded|reached|exhausted).*verify'; then
  EXHAUSTION_DETECTED=true
fi

# Pattern 3: Retry count 3 with FAIL verdict
if echo "$AGENT_OUTPUT" | grep -qiE 'retry_count.*:.*3' && echo "$AGENT_OUTPUT" | grep -qiE 'verdict.*:.*FAIL'; then
  EXHAUSTION_DETECTED=true
fi

if [[ "$EXHAUSTION_DETECTED" == "false" ]]; then
  exit 0
fi

# Try to extract change name from the output
CHANGE_NAME=$(echo "$AGENT_OUTPUT" | grep -oiE '(change|feature|Change):\s*[a-z0-9_-]+' | head -1 | sed 's/.*:\s*//' || echo "")
if [[ -z "$CHANGE_NAME" ]]; then
  CHANGE_NAME=$(echo "$AGENT_OUTPUT" | grep -oiE 'sdd-apply\s+[a-z0-9_-]+' | head -1 | awk '{print $2}' || echo "unknown")
fi

# Read project phase from cognitive-os.yaml
PHASE="reconstruction"
CONFIG_FILE="$PROJECT_DIR/cognitive-os.yaml"
if [[ -f "$CONFIG_FILE" ]] && command -v grep &>/dev/null; then
  DETECTED_PHASE=$(grep -oE 'phase:\s*\S+' "$CONFIG_FILE" | head -1 | awk '{print $2}' || echo "")
  if [[ -n "$DETECTED_PHASE" ]]; then
    PHASE="$DETECTED_PHASE"
  fi
fi

# Log the detection
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
mkdir -p "$METRICS_DIR" 2>/dev/null
ENTRY=$(jq -c -n \
  --arg ts "$TIMESTAMP" \
  --arg change "$CHANGE_NAME" \
  --arg phase "$PHASE" \
  '{timestamp: $ts, change: $change, phase: $phase, trigger: "verify-apply-exhaustion"}')
safe_jsonl_append "$ROLLBACK_LOG" "$ENTRY"

# Output the trigger message
echo ""
echo "=== AUTO-ROLLBACK TRIGGERED ==="
echo ""
echo "Verify-apply loop exceeded max retries for change: $CHANGE_NAME"
echo ""

if [[ "$PHASE" == "production" || "$PHASE" == "maintenance" ]]; then
  echo "HALT: Phase is '$PHASE' — auto-rollback requires human approval."
  echo "Run '/auto-rollback $CHANGE_NAME' to execute the rollback manually."
  echo ""
  echo "=== END AUTO-ROLLBACK TRIGGER ==="
  echo ""
  exit 0
fi

echo "Phase: $PHASE — auto-rollback will execute automatically."
echo ""
echo "ORCHESTRATOR ACTION REQUIRED: Launch /auto-rollback skill for change '$CHANGE_NAME'"
echo ""
echo "=== END AUTO-ROLLBACK TRIGGER ==="
echo ""

exit 0
