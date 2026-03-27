#!/usr/bin/env bash
# PostToolUse hook: Assumption Tracker
# Fires on "Agent" tool use — scans agent responses for assumption language
# Advisory only (exit 0) — warns when too many assumptions detected
# Must complete in <3 seconds
#
# PURPOSE: Tracks when agents make assumptions instead of asking for
# clarification. High assumption counts indicate the agent is guessing
# rather than working from verified requirements.

set -uo pipefail

_HOOK_NAME="assumption-tracker"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
source "$(dirname "$0")/_lib/common.sh"

# Auto-disabled at capability level 4
check_capability_level "assumption-tracking" && exit 0

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
ASSUMPTIONS_LOG="$METRICS_DIR/assumptions.jsonl"

# Session-aware metrics directory
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-}"
if [ -z "$SESSION_ID" ]; then
  _SESSION_FILE="$PROJECT_DIR/.cognitive-os/sessions/.current-session-$$"
  [ -f "$_SESSION_FILE" ] && SESSION_ID=$(cat "$_SESSION_FILE" 2>/dev/null)
fi
if [ -n "$SESSION_ID" ]; then
  SESSION_METRICS="$PROJECT_DIR/.cognitive-os/sessions/$SESSION_ID/metrics"
  if [ -d "$PROJECT_DIR/.cognitive-os/sessions/$SESSION_ID" ]; then
    METRICS_DIR="$SESSION_METRICS"
    ASSUMPTIONS_LOG="$SESSION_METRICS/assumptions.jsonl"
  fi
fi

# Read stdin (JSON with tool_name, tool_input, tool_response)
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

# Check private mode — skip if active
if [ -f "/tmp/claude-private-mode-active" ]; then
  exit 0
fi

# Extract agent response text
AGENT_RESPONSE=$(echo "$INPUT" | jq -r '
  if .tool_response | type == "string" then .tool_response
  elif .tool_response.response then .tool_response.response
  elif .tool_response.content then .tool_response.content
  elif .tool_response.result then .tool_response.result
  else (.tool_response | tostring)
  end
' 2>/dev/null)

if [ -z "$AGENT_RESPONSE" ] || [ "$AGENT_RESPONSE" = "null" ]; then
  exit 0
fi

# --- Assumption Detection ---
# Pattern groups with confidence levels:
# HIGH confidence: explicit assumption language
# MEDIUM confidence: hedging language that implies uncertainty

ASSUMPTIONS=""
ASSUMPTION_COUNT=0

# Helper: extract assumption context (the sentence containing the match)
extract_assumption() {
  local pattern="$1"
  local confidence="$2"
  local matches
  matches=$(echo "$AGENT_RESPONSE" | grep -oiE "[^.!?]*${pattern}[^.!?]*[.!?]?" | head -5)
  while IFS= read -r match; do
    if [ -n "$match" ]; then
      ASSUMPTION_COUNT=$((ASSUMPTION_COUNT + 1))
      # Trim to max 120 chars
      local trimmed
      trimmed=$(echo "$match" | head -c 120 | sed 's/^[[:space:]]*//')
      if [ -z "$ASSUMPTIONS" ]; then
        ASSUMPTIONS="[$confidence] $trimmed"
      else
        ASSUMPTIONS="$ASSUMPTIONS\n[$confidence] $trimmed"
      fi
    fi
  done <<< "$matches"
}

# HIGH confidence patterns — explicit assumption language
extract_assumption "I assume" "HIGH"
extract_assumption "I'm assuming" "HIGH"
extract_assumption "I'll assume" "HIGH"
extract_assumption "assuming that" "HIGH"
extract_assumption "presumably" "HIGH"
extract_assumption "without more info" "HIGH"
extract_assumption "in the absence of" "HIGH"
extract_assumption "based on context" "HIGH"

# MEDIUM confidence patterns — hedging/uncertainty language
extract_assumption "I think " "MEDIUM"
extract_assumption "probably " "MEDIUM"
extract_assumption "likely " "MEDIUM"
extract_assumption "it seems" "MEDIUM"
extract_assumption "appears to be" "MEDIUM"
extract_assumption "I believe " "MEDIUM"
extract_assumption "my best guess" "MEDIUM"
extract_assumption "if I had to guess" "MEDIUM"

# --- Logging ---
if [ "$ASSUMPTION_COUNT" -gt 0 ]; then
  TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  mkdir -p "$METRICS_DIR" 2>/dev/null

  # Extract agent description from prompt
  AGENT_DESC=$(echo "$INPUT" | jq -r '
    .tool_input.prompt // .tool_input.description // "unknown"
  ' 2>/dev/null | head -c 100)

  ENTRY=$(jq -c -n \
    --arg ts "$TIMESTAMP" \
    --argjson count "$ASSUMPTION_COUNT" \
    --arg agent "$AGENT_DESC" \
    --arg assumptions "$(echo -e "$ASSUMPTIONS" | head -c 500)" \
    '{timestamp: $ts, assumption_count: $count, agent: $agent, assumptions: $assumptions}')
  safe_jsonl_append "$ASSUMPTIONS_LOG" "$ENTRY"
fi

# --- Warning Output ---
if [ "$ASSUMPTION_COUNT" -ge 3 ]; then
  echo ""
  echo "=== ASSUMPTION TRACKER: WARNING ($ASSUMPTION_COUNT assumptions detected) ==="
  echo ""
  echo "The agent made $ASSUMPTION_COUNT assumptions in its response."
  echo "High assumption counts indicate the agent is guessing rather than"
  echo "working from verified requirements."
  echo ""
  echo "Assumptions found:"
  echo -e "$ASSUMPTIONS"
  echo ""
  echo "RECOMMENDATION: Review assumptions for correctness. Consider clarifying"
  echo "requirements and re-running with explicit specifications."
  echo ""
  echo "=== END ASSUMPTION TRACKER ==="
  echo ""
fi

# Advisory only — always exit 0
exit 0
