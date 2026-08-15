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

# The harness sends no exit_code (measured: zero occurrences at any nesting
# level across 2,684 tool results). Agent/Skill payloads carry their own verdict
# fields instead, and their shapes differ from Bash:
#   object with .status -> "async_launched" (150) | "completed" (5)
#   object with .success (Skill invocations, 10)
#   string              -> failure or refusal (17)
# hooks/_lib/tool-outcome.sh classifies all three plus the drift case.
source "$(dirname "$0")/_lib/tool-outcome.sh"
classify_tool_outcome "$INPUT"
EXIT_CODE="$TOOL_EXIT_CODE"

# --- Extract skill name ---
# The `skill` field feeds five KPI modules (cos_lib/kpi_collector.py,
# repetition_detector.py, component_usage_tracker.py, singularity.py,
# performance_ledger.py), so only a real skill identifier may land in it.
# Until this fix the fallback chain was
# `.tool_input.skill // .tool_input.description // .tool_input.prompt`
# followed by "keep the first word", which turned every Agent launch into a
# fake skill named after the first word of its description — "juez", "forense",
# "test" — and truncated at the first non-ASCII byte, so "Decisión ..." was
# recorded as the skill "decisi".
_skill_exists() {
  [ -n "${1:-}" ] || return 1
  [ -f "$_PROJECT_DIR/skills/$1/SKILL.md" ] && return 0
  [ -f "$_PROJECT_DIR/.cognitive-os/skills/cos/$1/SKILL.md" ] && return 0
  return 1
}

# 1. The Skill tool carries the name explicitly: that value is authoritative.
SKILL_NAME=$(echo "$INPUT" | jq -r '.tool_input.skill // ""' 2>/dev/null \
  | head -c 100 | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9:_-' || true)

# 2. Agent launches carry no skill field. The only trustworthy signal is an
#    explicit `skills/<name>` reference in the prompt, and it still has to name
#    a skill that exists on disk. No inference from free text.
if [ -z "$SKILL_NAME" ]; then
  PROMPT_REFS=$(echo "$INPUT" | jq -r '.tool_input.prompt // ""' 2>/dev/null \
    | grep -oE 'skills/[a-z0-9][a-z0-9_-]*' | sed 's|^skills/||' | head -5 || true)
  while IFS= read -r candidate; do
    [ -n "$candidate" ] || continue
    if _skill_exists "$candidate"; then
      SKILL_NAME="$candidate"
      break
    fi
  done <<EOF_REFS
$PROMPT_REFS
EOF_REFS
fi

# 3. An agent run nobody can attribute to a skill is recorded as exactly that.
[ -z "$SKILL_NAME" ] && SKILL_NAME="unknown-agent"

# --- Part 1: Failure detection + Engram feedback ---
FAILED=false
FAILURE_REASON=""

case "$TOOL_OUTCOME" in
  failed)
    FAILED=true
    FAILURE_REASON="tool reported failure${TOOL_EXIT_CODE:+ (exit ${TOOL_EXIT_CODE})}"
    ;;
  blocked)
    # The launch was refused before it ran. Not the skill's fault — do not feed
    # it back to Engram as skill failure evidence.
    FAILED=false
    ;;
  absent)
    exit 0
    ;;
esac

# The pattern match only ever looked at the harness's own words, never at the
# prompt we sent it. Agent payloads embed the full `prompt`, and agent prompts
# routinely contain "error" or "failed" as ordinary subject matter, so grepping
# the whole payload marked healthy runs as failures. Scope it to the string
# form, which is the only shape that carries a harness error message.
if [ "$TOOL_OUTCOME" = "failed" ] || [ "$TOOL_OUTCOME" = "blocked" ]; then
  if echo "$TOOL_RESULT" | head -c 500 \
     | grep -qi "error\|failed\|rejected\|exception\|timed out\|permission denied" 2>/dev/null; then
    FAILURE_REASON="${FAILURE_REASON:+$FAILURE_REASON | }$(echo "$TOOL_RESULT" | head -c 120 | tr '\n' ' ')"
  fi
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
