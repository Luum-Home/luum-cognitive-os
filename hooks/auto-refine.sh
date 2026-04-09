#!/usr/bin/env bash
# DEPRECATED: This hook's functionality is merged into completion-gate.sh (Phase 3).
# Do NOT wire this hook — it would duplicate the auto-refine/PITER loop in completion-gate.
# Original: PostToolUse hook: Auto-Refine (PITER loop)
# Fires on "Agent" completions — detects failures and tracks retry count.
# Outputs ORCHESTRATOR ACTION REQUIRED on failure (max 3 retries), ESCALATION at limit.

set -uo pipefail

_HOOK_NAME="auto-refine"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
source "$(dirname "$0")/_lib/common.sh"

check_private_mode
read_stdin_json

TOOL_OUTPUT=$(stdin_field '.tool_response.content' '')
if [ -z "$TOOL_OUTPUT" ]; then
  TOOL_OUTPUT=$(stdin_field '.tool_response' '' | jq -r 'if type == "array" then .[].text // "" else . // "" end' 2>/dev/null || true)
fi

# Detect failure signals
FAILURE=false
if echo "$TOOL_OUTPUT" | grep -qiE '(FAIL|ERROR|build failed|test failed|compilation error|lint error|exit code [1-9])'; then
  FAILURE=true
fi

[ "$FAILURE" = "false" ] && exit 0

METRICS_DIR=$(_resolve_metrics_dir)
STATE_DIR="$_PROJECT_DIR/.cognitive-os/sessions"
mkdir -p "$STATE_DIR" 2>/dev/null

# Determine session state file
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-}"
if [ -z "$SESSION_ID" ]; then
  SESSION_FILE="$_PROJECT_DIR/.cognitive-os/sessions/.current-session-$$"
  [ -f "$SESSION_FILE" ] && SESSION_ID=$(cat "$SESSION_FILE" 2>/dev/null)
fi
STATE_FILE="${STATE_DIR}/${SESSION_ID:-global}/auto-refine-state.json"
mkdir -p "$(dirname "$STATE_FILE")" 2>/dev/null

# Read current retry count
RETRY_COUNT=0
if [ -f "$STATE_FILE" ]; then
  RETRY_COUNT=$(jq -r '.retry_count // 0' "$STATE_FILE" 2>/dev/null || echo 0)
fi
RETRY_COUNT=$(( RETRY_COUNT + 1 ))

TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Update state
echo "{\"retry_count\": $RETRY_COUNT, \"last_failure\": \"$TIMESTAMP\"}" > "$STATE_FILE" 2>/dev/null

# Determine phase for messaging
PHASE=$(get_phase)

if [ "$RETRY_COUNT" -lt 3 ]; then
  echo "ORCHESTRATOR ACTION REQUIRED: Agent failed (attempt $RETRY_COUNT/3). Re-launch with error context." >&2
  echo "Phase: $PHASE. Analyze the error, use a DIFFERENT approach, then retry." >&2
else
  echo "ESCALATION: Max retries exceeded (3/3). Report failure to human with full diagnosis." >&2
  # Reset counter so next fresh task starts clean
  echo '{"retry_count": 0}' > "$STATE_FILE" 2>/dev/null
fi

safe_jsonl_append "$METRICS_DIR/auto-refine.jsonl" \
  "{\"timestamp\":\"$TIMESTAMP\",\"retry_count\":$RETRY_COUNT,\"phase\":\"$PHASE\"}"

exit 0
