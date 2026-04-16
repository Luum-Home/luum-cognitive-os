#!/usr/bin/env bash
# PreToolUse hook: Context Diet — Task-aware rule selection advisory
# Fires on "Agent" tool use — classifies task type and outputs which rules
# are relevant, so the orchestrator knows the minimal context needed.
# Advisory only (exit 0) — never blocks.
# Must complete in <1 second.
#
# PURPOSE: Reduces sub-agent cold start by advising which rules matter.
# Works with lib/context_diet.py to map task_type -> minimal rule set.

set -uo pipefail

_HOOK_NAME="context-diet"
source "$(dirname "$0")/_lib/common.sh"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
DIET_LOG="$METRICS_DIR/context-diet.jsonl"

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
    DIET_LOG="$SESSION_METRICS/context-diet.jsonl"
  fi
fi

# Read stdin
INPUT=$(cat)
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

# Check private mode
if [ -f "/tmp/claude-private-mode-active" ]; then
  exit 0
fi

# Extract agent prompt
AGENT_PROMPT=$(echo "$INPUT" | jq -r '
  .tool_input.prompt // .tool_input.description // ""
' 2>/dev/null)

if [ -z "$AGENT_PROMPT" ] || [ "$AGENT_PROMPT" = "null" ]; then
  exit 0
fi

# --- Task Type Classification ---
# Match keywords in the prompt to determine task type.
# This mirrors the mapping in lib/context_diet.py.
TASK_TYPE="unknown"
PROMPT_LOWER=$(echo "$AGENT_PROMPT" | tr '[:upper:]' '[:lower:]')

# Order matters: more specific patterns first
if echo "$PROMPT_LOWER" | grep -qE 'sdd-archive|archive|archivar'; then
  TASK_TYPE="archive"
elif echo "$PROMPT_LOWER" | grep -qE 'sdd-verify|verify|verificar|validate'; then
  TASK_TYPE="verify"
elif echo "$PROMPT_LOWER" | grep -qE 'sdd-explore|explore|explorar|investigate|feasibility'; then
  TASK_TYPE="explore"
elif echo "$PROMPT_LOWER" | grep -qE 'sdd-propose|propose|proposal|proponer'; then
  TASK_TYPE="propose"
elif echo "$PROMPT_LOWER" | grep -qE 'sdd-spec|spec|specification|especificacion'; then
  TASK_TYPE="spec"
elif echo "$PROMPT_LOWER" | grep -qE 'sdd-design|design|diseno|architecture'; then
  TASK_TYPE="design"
elif echo "$PROMPT_LOWER" | grep -qE 'review|code.review|revisar|adversarial'; then
  TASK_TYPE="review"
elif echo "$PROMPT_LOWER" | grep -qE 'debug|fix.bug|depurar|error|diagnos'; then
  TASK_TYPE="debug"
elif echo "$PROMPT_LOWER" | grep -qE 'test|tdd|unit.test|coverage'; then
  TASK_TYPE="test"
elif echo "$PROMPT_LOWER" | grep -qE 'doc|document|readme|changelog'; then
  TASK_TYPE="docs"
elif echo "$PROMPT_LOWER" | grep -qE 'implement|apply|sdd-apply|build|create|add|write|code'; then
  TASK_TYPE="implement"
fi

# --- Get minimal rules via prompt_builder (integrates context_diet + prompt_cache) ---
RULES_OUTPUT=""
if command -v python3 &>/dev/null; then
  # Use the integrated PromptBuilder which wires context_diet + prompt_cache together
  RULES_OUTPUT=$(python3 -c "
import sys
sys.path.insert(0, '$PROJECT_DIR')
try:
    from lib.prompt_builder import PromptBuilder
    builder = PromptBuilder.from_project('$PROJECT_DIR')
    rules = builder.selected_rules('$TASK_TYPE')
    print(','.join(rules))
except Exception:
    # Fallback to context_diet directly
    try:
        from lib.context_diet import ContextDiet
        diet = ContextDiet.from_yaml('$PROJECT_DIR/cognitive-os.yaml', rules_dir='$PROJECT_DIR/rules')
        rules = diet.select_rules('$TASK_TYPE')
        print(','.join(rules))
    except Exception:
        pass
" 2>/dev/null || true)
fi

# --- Advisory output ---
if [ -n "$RULES_OUTPUT" ]; then
  RULE_COUNT=$(echo "$RULES_OUTPUT" | tr ',' '\n' | wc -l | tr -d ' ')
  echo "CONTEXT DIET: task_type=$TASK_TYPE, $RULE_COUNT rules needed: $RULES_OUTPUT" >&2
fi

# --- Log to metrics ---
mkdir -p "$(dirname "$DIET_LOG")"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%SZ")
PROMPT_SHORT=$(echo "$AGENT_PROMPT" | head -c 100 | tr '\n' ' ' | tr '"' "'")

if command -v jq &>/dev/null; then
  jq -n \
    --arg ts "$TIMESTAMP" \
    --arg task_type "$TASK_TYPE" \
    --arg rules "$RULES_OUTPUT" \
    --arg prompt "$PROMPT_SHORT" \
    '{timestamp: $ts, task_type: $task_type, rules: $rules, prompt: $prompt}' \
    >> "$DIET_LOG" 2>/dev/null || true
fi

exit 0
