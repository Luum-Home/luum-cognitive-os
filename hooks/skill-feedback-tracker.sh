#!/usr/bin/env bash
# PostToolUse hook: Skill Feedback Tracker
# Fires on "Agent" completions — tracks skill success/failure rates.
# Warns when a skill has degraded (3+ failures).

set -uo pipefail

_HOOK_NAME="skill-feedback-tracker"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
source "$(dirname "$0")/_lib/common.sh"

check_private_mode
read_stdin_json

TOOL_PROMPT=$(stdin_field '.tool_input.prompt' '')
TOOL_OUTPUT=$(stdin_field '.tool_response.content' '')
if [ -z "$TOOL_OUTPUT" ]; then
  TOOL_OUTPUT=$(stdin_field '.tool_response' '' | jq -r 'if type == "array" then .[].text // "" else . // "" end' 2>/dev/null || true)
fi

# Extract skill name from prompt
SKILL_NAME=""
if echo "$TOOL_PROMPT" | grep -qE 'SKILL: Load'; then
  SKILL_NAME=$(echo "$TOOL_PROMPT" | grep -oE 'SKILL: Load `[^`]+`' | head -1 \
    | sed 's/SKILL: Load `//' | sed 's/`.*//' | xargs basename 2>/dev/null || true)
fi
if [ -z "$SKILL_NAME" ] && echo "$TOOL_PROMPT" | grep -qE '/[a-z][a-z0-9-]+'; then
  SKILL_NAME=$(echo "$TOOL_PROMPT" | grep -oE '/[a-z][a-z0-9-]+' | head -1 | tr -d '/')
fi

[ -z "$SKILL_NAME" ] && exit 0

# Detect success or failure
SUCCESS=true
if echo "$TOOL_OUTPUT" | grep -qiE '(FAIL|ERROR|build failed|test failed|ESCALATION)'; then
  SUCCESS=false
fi

METRICS_DIR=$(_resolve_metrics_dir)
FEEDBACK_LOG="$METRICS_DIR/skill-feedback.jsonl"
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

safe_jsonl_append "$FEEDBACK_LOG" \
  "{\"timestamp\":\"$TIMESTAMP\",\"skill\":\"$SKILL_NAME\",\"success\":$SUCCESS}"

# Count recent failures for this skill (last 24h)
if [ "$SUCCESS" = "false" ] && [ -f "$FEEDBACK_LOG" ]; then
  CUTOFF=$(( $(date +%s) - 86400 ))
  FAIL_COUNT=$(grep "\"skill\":\"$SKILL_NAME\"" "$FEEDBACK_LOG" 2>/dev/null \
    | grep '"success":false' | wc -l | tr -d ' ')
  if [ "${FAIL_COUNT:-0}" -ge 3 ]; then
    echo "SKILL DEGRADED: Skill '$SKILL_NAME' has failed ${FAIL_COUNT} times. Consider running /optimize-skill $SKILL_NAME" >&2
  fi
fi

exit 0
