#!/usr/bin/env bash
# SCOPE: os-only
# CONCERNS: metrics, observability, quality
# PostToolUse hook: Combined skill feedback + metrics tracker
# Fires on "Agent|Skill" — saves failure feedback to Engram AND appends metrics to JSONL
# Replaces: skill-feedback-tracker.sh + skill-metrics-tracker.sh
# Must complete in <5 seconds

set -euo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

# Record wall-clock start time in milliseconds immediately on entry
_SKILL_TRACKER_START_MS=$(python3 -c "import time; print(int(time.time()*1000))" 2>/dev/null \
    || date +%s%3N 2>/dev/null \
    || echo "0")

_HOOK_NAME="skill-tracker"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
source "$(dirname "$0")/_lib/common.sh"

# Read stdin and gate on Agent/Skill tool
read_stdin_json
INPUT="$_STDIN_JSON"
require_tool "Agent" "Skill"

# Exit early if no input or no jq
if [ -z "$INPUT" ]; then exit 0; fi
if ! command -v jq &>/dev/null; then exit 0; fi

TOOL_NAME=$(stdin_field '.tool_name' 'unknown')

TOOL_RESULT=$(echo "$INPUT" | jq -r '.tool_response // empty' 2>/dev/null)
EXIT_CODE=$(echo "$INPUT" | jq -r '.exit_code // "0"' 2>/dev/null)

# --- Extract skill name ---
SKILL_NAME=$(echo "$INPUT" | jq -r '
  .tool_input.skill // .tool_input.description // .tool_input.prompt // "unknown"
' 2>/dev/null | head -c 100)

# Normalize: "sdd-explore: Explore the codebase" -> "sdd-explore"
SKILL_NAME=$(echo "$SKILL_NAME" | sed -E 's/^([a-zA-Z0-9_-]+).*/\1/' | tr '[:upper:]' '[:lower:]')

if [ -z "$SKILL_NAME" ] || [ "$SKILL_NAME" = "unknown" ]; then
  SKILL_NAME=$(echo "$INPUT" | jq -r '.tool_input.prompt // ""' 2>/dev/null | grep -oE '(sdd-[a-z]+|systematic-debugging|test-driven|verification|model-optimizer|skill-[a-z]+)' | head -1)
  [ -z "$SKILL_NAME" ] && SKILL_NAME="unknown-agent"
fi

# --- Part 1: Failure detection + Engram feedback ---
FAILED=false
FAILURE_REASON=""

if [ "$EXIT_CODE" != "0" ] && [ "$EXIT_CODE" != "" ]; then
  FAILED=true
  FAILURE_REASON="Exit code: $EXIT_CODE"
fi

if echo "$TOOL_RESULT" | grep -qi "error\|failed\|rejected\|exception\|timed out\|permission denied" 2>/dev/null; then
  FAILED=true
  FAILURE_REASON="${FAILURE_REASON:+$FAILURE_REASON | }Pattern match in result"
fi

if [ "$FAILED" = "true" ]; then
  ENGRAM_PORT="${ENGRAM_PORT:-7437}"
  curl -s -X POST "http://localhost:${ENGRAM_PORT}/api/observations" \
    -H "Content-Type: application/json" \
    -d "{
      \"title\": \"Skill feedback: ${SKILL_NAME} failed\",
      \"type\": \"discovery\",
      \"project\": \"${CLAUDE_PROJECT_NAME:-my-project}\",
      \"content\": \"**Skill**: ${SKILL_NAME}\\n**Failure**: ${FAILURE_REASON}\\n**Result excerpt**: $(echo "$TOOL_RESULT" | head -c 500 | jq -Rs .)\",
      \"topic_key\": \"skill-feedback/${SKILL_NAME}\"
    }" > /dev/null 2>&1 || true
fi

# --- Part 2: Metrics tracking (JSONL) ---
METRICS_DIR="$(resolve_session_dir)"
METRICS_FILE="$METRICS_DIR/skill-metrics.jsonl"

MODEL=$(echo "$INPUT" | jq -r 'try (.tool_response.model // .tool_response.usage.model // "unknown") catch "unknown"' 2>/dev/null || echo "unknown")

# --- Token estimation ---
# Claude Code's PostToolUse hook input does NOT expose token counts for the Agent tool.
# We estimate from output length: chars / 4 is a standard approximation.
TOOL_RESPONSE_TEXT=$(echo "$INPUT" | jq -r 'try (.tool_response // "") catch ""' 2>/dev/null || echo "")
TOOL_RESPONSE_LEN=${#TOOL_RESPONSE_TEXT}
TOTAL_TOKENS=$(( TOOL_RESPONSE_LEN / 4 ))
# Ensure minimum of 1 so entries are distinguishable from "not measured"
[ "$TOTAL_TOKENS" -lt 1 ] && TOTAL_TOKENS=1

# --- Duration tracking ---
# Compute wall-clock time since hook entry (captures agent execution time reflected
# in hook scheduling delay, not the full agent run, but gives a non-zero signal).
_SKILL_TRACKER_END_MS=$(python3 -c "import time; print(int(time.time()*1000))" 2>/dev/null \
    || date +%s%3N 2>/dev/null \
    || echo "0")
DURATION_MS=0
if [ "$_SKILL_TRACKER_START_MS" != "0" ] && [ "$_SKILL_TRACKER_END_MS" != "0" ]; then
    DURATION_MS=$(( _SKILL_TRACKER_END_MS - _SKILL_TRACKER_START_MS ))
fi
# Ensure duration is non-negative
[ "$DURATION_MS" -lt 0 ] && DURATION_MS=0

if [ "$FAILED" = "true" ]; then SUCCESS="false"; else SUCCESS="true"; fi
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

METRICS_LINE=$(jq -nc \
  --arg ts "$TIMESTAMP" \
  --arg skill "$SKILL_NAME" \
  --arg model "$MODEL" \
  --argjson tokens "${TOTAL_TOKENS:-0}" \
  --argjson duration "${DURATION_MS:-0}" \
  --argjson success "${SUCCESS:-true}" \
  '{timestamp: $ts, skill: $skill, model: $model, tokens: $tokens, duration_ms: $duration, success: $success}' 2>/dev/null)

[ -n "$METRICS_LINE" ] && safe_jsonl_append "$METRICS_FILE" "$METRICS_LINE"

exit 0
