#!/usr/bin/env bash
# SCOPE: both
# PostToolUse hook on Agent — detects NEEDS_CLARIFICATION marker in agent output.
# Extracts questions and signals the orchestrator to handle resolution.
# Advisory only (exit 0) — does NOT block, tells orchestrator to act.
# Must complete in <3 seconds
#
# PURPOSE: Enables the split-and-resume pattern where sub-agents can request
# mid-task clarification instead of making incorrect assumptions.

set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="clarification-interceptor"
source "$(dirname "$0")/_lib/safe-jsonl.sh"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
CLARIFICATION_LOG="$METRICS_DIR/clarifications.jsonl"

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
    CLARIFICATION_LOG="$SESSION_METRICS/clarifications.jsonl"
  fi
fi

MAX_ROUNDS=2

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

# Only process Agent tool results
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
if [ "$TOOL_NAME" != "Agent" ] && [ "$TOOL_NAME" != "task" ] && [ "$TOOL_NAME" != "delegate" ]; then
  exit 0
fi

# Check private mode — skip if active
if [ -f "/tmp/claude-private-mode-active" ]; then
  exit 0
fi

# Extract agent output (check multiple possible fields)
AGENT_OUTPUT=$(echo "$INPUT" | jq -r '
  .tool_result // .tool_response.result // .tool_response.output // .tool_response.content // .tool_response // ""
' 2>/dev/null)

if [ -z "$AGENT_OUTPUT" ] || [ "$AGENT_OUTPUT" = "null" ]; then
  exit 0
fi

# --- Detect NEEDS_CLARIFICATION marker ---
if ! echo "$AGENT_OUTPUT" | grep -q 'NEEDS_CLARIFICATION:'; then
  exit 0
fi

# --- Extract questions ---
# Questions appear after NEEDS_CLARIFICATION: marker, one per line
# They may be numbered (1. 2. 3.) or use dashes (-) or plain text
QUESTIONS=$(echo "$AGENT_OUTPUT" | sed -n '/NEEDS_CLARIFICATION:/,/^$/p' | tail -n +2 | grep -vE '^\s*$' | head -10)

if [ -z "$QUESTIONS" ]; then
  # Try alternate: everything after NEEDS_CLARIFICATION: on the same line
  QUESTIONS=$(echo "$AGENT_OUTPUT" | grep -oP 'NEEDS_CLARIFICATION:\s*\K.*' | head -1)
  if [ -z "$QUESTIONS" ]; then
    # Fallback for grep without -P: use sed
    QUESTIONS=$(echo "$AGENT_OUTPUT" | sed -n 's/.*NEEDS_CLARIFICATION:[[:space:]]*//p' | head -1)
  fi
fi

if [ -z "$QUESTIONS" ]; then
  exit 0
fi

QUESTION_COUNT=$(echo "$QUESTIONS" | wc -l | tr -d ' ')

# --- Determine clarification round ---
# Check how many clarification rounds have already occurred for this agent
# by counting CLARIFICATION ANSWERS sections in the original prompt
AGENT_PROMPT=$(echo "$INPUT" | jq -r '
  .tool_input.prompt // .tool_input.description // ""
' 2>/dev/null)

CURRENT_ROUND=1
if [ -n "$AGENT_PROMPT" ]; then
  PREV_ROUNDS=$(echo "$AGENT_PROMPT" | grep -c 'CLARIFICATION ANSWERS:' 2>/dev/null || echo "0")
  CURRENT_ROUND=$((PREV_ROUNDS + 1))
fi

# --- Logging ---
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
mkdir -p "$METRICS_DIR" 2>/dev/null

AGENT_DESC=$(echo "$AGENT_PROMPT" | head -c 100)

# Build questions array for JSON
QUESTIONS_JSON=$(echo "$QUESTIONS" | jq -R -s 'split("\n") | map(select(length > 0) | gsub("^\\s*[0-9]+\\.\\s*"; "") | gsub("^\\s*-\\s*"; ""))')

ENTRY=$(jq -c -n \
  --arg ts "$TIMESTAMP" \
  --arg agent "$AGENT_DESC" \
  --argjson round "$CURRENT_ROUND" \
  --argjson max_rounds "$MAX_ROUNDS" \
  --argjson question_count "$QUESTION_COUNT" \
  --argjson questions "$QUESTIONS_JSON" \
  --arg resolution "pending" \
  '{timestamp: $ts, agent: $agent, round: $round, max_rounds: $max_rounds, questions: $questions, question_count: $question_count, resolution: $resolution}')
safe_jsonl_append "$CLARIFICATION_LOG" "$ENTRY"

# --- Output based on round ---
if [ "$CURRENT_ROUND" -gt "$MAX_ROUNDS" ]; then
  echo ""
  echo "=== SPLIT-AND-RESUME: MAX ROUNDS EXCEEDED ==="
  echo ""
  echo "Agent has requested clarification $CURRENT_ROUND times (max: $MAX_ROUNDS)."
  echo "This task may be too ambiguous for autonomous execution."
  echo ""
  echo "Escalate to the user with these unresolved questions:"
  echo ""
  echo "$QUESTIONS"
  echo ""
  echo "=== END SPLIT-AND-RESUME ==="
  echo ""
  exit 0
fi

echo ""
echo "=== SPLIT-AND-RESUME: CLARIFICATION NEEDED ==="
echo ""
echo "ORCHESTRATOR ACTION REQUIRED: Agent needs clarification."
echo "Round: $CURRENT_ROUND/$MAX_ROUNDS"
echo ""
echo "Questions:"
echo "$QUESTIONS"
echo ""
echo "Resolution steps:"
echo "  1. Search Engram for answers (mem_search with question keywords)"
echo "  2. If found: re-launch agent with answers in CLARIFICATION ANSWERS: section"
echo "  3. If not found: ask the USER, save answer to Engram, then re-launch"
echo ""
echo "=== END SPLIT-AND-RESUME ==="
echo ""

exit 0
