#!/usr/bin/env bash
# PreToolUse hook: Clarification Gate
# Fires on "Agent" tool use — scores prompt ambiguity and blocks if too vague
# BLOCKING: exit 2 if ambiguity score > 60 (blocks tool use)
# Must complete in <3 seconds
#
# PURPOSE: Prevents agents from launching with vague, ambiguous prompts.
# Ambiguous prompts let agents interpret scope minimally, producing
# incomplete results that waste tokens and require re-work.

set -uo pipefail

_HOOK_NAME="clarification-gate"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
source "$(dirname "$0")/_lib/common.sh"

# Auto-disabled at capability level 4
check_capability_level "clarification-gate"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
CLARIFICATION_LOG="$METRICS_DIR/clarification-events.jsonl"

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
    CLARIFICATION_LOG="$SESSION_METRICS/clarification-events.jsonl"
  fi
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

# Check private mode — skip if active
if [ -f "/tmp/claude-private-mode-active" ]; then
  exit 0
fi

# Extract agent prompt/description
AGENT_PROMPT=$(echo "$INPUT" | jq -r '
  .tool_input.prompt // .tool_input.description // ""
' 2>/dev/null)

if [ -z "$AGENT_PROMPT" ] || [ "$AGENT_PROMPT" = "null" ]; then
  exit 0
fi

# --- Ambiguity Scoring ---
SCORE=0
QUESTIONS=""
QUESTION_COUNT=0

add_question() {
  local points="$1"
  local question="$2"
  SCORE=$((SCORE + points))
  QUESTION_COUNT=$((QUESTION_COUNT + 1))
  if [ -z "$QUESTIONS" ]; then
    QUESTIONS="  $QUESTION_COUNT. $question"
  else
    QUESTIONS="$QUESTIONS\n  $QUESTION_COUNT. $question"
  fi
}

# Signal 1: No file paths mentioned (no / or . path separators in likely path patterns)
if ! echo "$AGENT_PROMPT" | grep -qE '(src/|internal/|pkg/|lib/|hooks/|rules/|skills/|tests/|\.go\b|\.ts\b|\.py\b|\.js\b|\.yaml\b|\.yml\b|\.json\b|\.md\b|\.sh\b)'; then
  add_question 15 "Which files or directories should be modified? No file paths detected in the prompt."
fi

# Signal 2: Scope words without quantifiers
if echo "$AGENT_PROMPT" | grep -qiE '\b(all|every|complete|entire|whole)\b' && ! echo "$AGENT_PROMPT" | grep -qiE '[0-9]+\s*(file|endpoint|service|item|route|test|module|function|component)'; then
  add_question 20 "How many items are in scope? Words like 'all/every/complete' used without a count."
fi

# Signal 3: Missing technology/framework specification
if echo "$AGENT_PROMPT" | grep -qiE '\b(add|implement|create|build|set up|setup|integrate)\b' && ! echo "$AGENT_PROMPT" | grep -qiE '\b(go|golang|typescript|python|react|nest|express|gin|docker|postgres|mongo|kafka|redis|graphql|rest|grpc|nextjs|vue|angular|fastapi|flask|spring|django)\b'; then
  add_question 15 "Which technology or framework should be used? No specific tech stack mentioned."
fi

# Signal 4: Action verbs without targets
if echo "$AGENT_PROMPT" | grep -qiE '\b(add auth|improve performance|fix bugs|add tests|add logging|add validation|add error handling|refactor code|clean up|optimize)\b' && ! echo "$AGENT_PROMPT" | grep -qiE '\b(in |for |to |at |within )\b[a-zA-Z0-9_/.-]+\.(go|ts|py|js|yaml|json|sh|md)\b'; then
  add_question 20 "Where exactly should this change be applied? Action described without specific targets."
fi

# Signal 5: Unanswered questions in prompt
if echo "$AGENT_PROMPT" | grep -qiE '\b(which\??|what type\??|where should\??|how should\??|should I\??|should we\??)\b'; then
  add_question 15 "The prompt contains open questions that need answers before implementation."
fi

# Signal 6: Very short prompt (under 50 chars) for Agent tool
PROMPT_LENGTH=${#AGENT_PROMPT}
if [ "$PROMPT_LENGTH" -lt 50 ]; then
  add_question 20 "Prompt is very short ($PROMPT_LENGTH chars). Agent prompts should include detailed task description, acceptance criteria, and verification steps."
fi

# Signal 7: No success criteria or acceptance criteria
if ! echo "$AGENT_PROMPT" | grep -qiE '(acceptance criteria|success criteria|definition of done|verify|verification|expected result|should pass|must pass|exits 0)'; then
  add_question 10 "No success/acceptance criteria found. How will completion be verified?"
fi

# --- Detail Discount — specific prompts should not be penalized for length ---
# File paths present: each file path reference reduces score by -5 (capped at -20)
FILE_PATH_COUNT=$(echo "$AGENT_PROMPT" | grep -oE '/[a-zA-Z0-9_./-]+\.[a-z]{1,4}' | wc -l | tr -d ' ')
if [ "$FILE_PATH_COUNT" -gt 0 ]; then
  DISCOUNT=$((FILE_PATH_COUNT * 5))
  [ "$DISCOUNT" -gt 20 ] && DISCOUNT=20
  SCORE=$((SCORE - DISCOUNT))
fi

# Long detailed prompt with file paths: additional -10
if [ "${#AGENT_PROMPT}" -gt 500 ] && [ "$FILE_PATH_COUNT" -gt 0 ]; then
  SCORE=$((SCORE - 10))
fi

# Engram/memory references indicate structured agent work: -10
if echo "$AGENT_PROMPT" | grep -qiE 'mem_save|mem_search|engram|topic_key'; then
  SCORE=$((SCORE - 10))
fi

# Numbered steps indicate structured instructions: -10
if echo "$AGENT_PROMPT" | grep -qE '^[0-9]+\.'; then
  SCORE=$((SCORE - 10))
fi

# Floor at 0
[ "$SCORE" -lt 0 ] && SCORE=0

# Cap score at 100
if [ "$SCORE" -gt 100 ]; then
  SCORE=100
fi

# --- Logging and Output ---
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
mkdir -p "$METRICS_DIR" 2>/dev/null

AGENT_DESC=$(echo "$AGENT_PROMPT" | head -c 100)

if [ "$SCORE" -gt 0 ]; then
  ENTRY=$(jq -c -n \
    --arg ts "$TIMESTAMP" \
    --argjson score "$SCORE" \
    --argjson questions "$QUESTION_COUNT" \
    --arg verdict "$([ "$SCORE" -gt 60 ] && echo "BLOCK" || ([ "$SCORE" -ge 30 ] && echo "WARN" || echo "PASS"))" \
    --arg agent "$AGENT_DESC" \
    '{timestamp: $ts, score: $score, questions: $questions, verdict: $verdict, agent: $agent}')
  safe_jsonl_append "$CLARIFICATION_LOG" "$ENTRY"
fi

# Score > 60: BLOCK
if [ "$SCORE" -gt 60 ]; then
  echo ""
  echo "=== CLARIFICATION GATE: BLOCKED (ambiguity score: $SCORE/100) ==="
  echo ""
  echo "The agent prompt is too ambiguous to produce reliable results."
  echo "Answer these questions before launching the agent:"
  echo ""
  echo -e "$QUESTIONS"
  echo ""
  echo "Ambiguous prompts let agents do the minimum. Clarify scope, targets,"
  echo "and success criteria before proceeding."
  echo ""
  echo "=== END CLARIFICATION GATE ==="
  echo ""
  exit 2
fi

# Score 30-60: WARN
if [ "$SCORE" -ge 30 ]; then
  echo ""
  echo "=== CLARIFICATION GATE: WARNING (ambiguity score: $SCORE/100) ==="
  echo ""
  echo "The agent prompt has some ambiguity. Consider clarifying:"
  echo ""
  echo -e "$QUESTIONS"
  echo ""
  echo "The agent will proceed, but results may be incomplete or require re-work."
  echo ""
  echo "=== END CLARIFICATION GATE ==="
  echo ""
fi

# Score < 30: pass silently
exit 0
