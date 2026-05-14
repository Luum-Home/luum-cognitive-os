#!/usr/bin/env bash
# SCOPE: os-only
# PreToolUse hook: Context Diet — Task-aware rule selection advisory
# Fires on "Agent" tool use — classifies task type and outputs which rules
# are relevant, so the orchestrator knows the minimal context needed.
# Advisory only (exit 0) — never blocks.
# Must complete in <1 second.
#
# PURPOSE: Reduces sub-agent cold start by advising which rules matter.
# Works with lib/context_diet.py to map task_type -> minimal rule set.
#
# Transport: emits hookSpecificOutput.additionalContext on stdout (Claude Code native).
# Falls back to stderr when invoked outside Claude Code (no valid stdin JSON).

set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="context-diet"
source "$(dirname "$0")/_lib/common.sh"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
DIET_LOG="$METRICS_DIR/context-diet.jsonl"

# additionalContext hard limit per Claude Code spec
MAX_CONTEXT_CHARS=10000

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

# Detect "real" Claude Code invocation: stdin is a JSON object with tool_name.
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || echo "")
HAS_VALID_INPUT=0
if [ -n "$TOOL_NAME" ]; then
  HAS_VALID_INPUT=1
fi

# Only process Agent tool
if [ -n "$TOOL_NAME" ] && [ "$TOOL_NAME" != "Agent" ]; then
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

# --- Compose advisory message ---
ADVISORY_MSG=""
if [ -n "$RULES_OUTPUT" ]; then
  RULE_COUNT=$(echo "$RULES_OUTPUT" | tr ',' '\n' | wc -l | tr -d ' ')
  ADVISORY_MSG="CONTEXT DIET: task_type=${TASK_TYPE}, ${RULE_COUNT} rules needed: ${RULES_OUTPUT}"
fi

# --- Truncate to 10K char limit ---
if [ -n "$ADVISORY_MSG" ]; then
  ADVISORY_LEN=${#ADVISORY_MSG}
  if [ "$ADVISORY_LEN" -gt "$MAX_CONTEXT_CHARS" ]; then
    if command -v python3 >/dev/null 2>&1; then
      # Use printf (no trailing newline) so truncation math stays exact
      ADVISORY_MSG=$(printf '%s' "$ADVISORY_MSG" | python3 -c "
import sys
buf = sys.stdin.read()
limit = ${MAX_CONTEXT_CHARS}
if len(buf) > limit:
    marker = '\n[truncated at 10K chars]'
    sys.stdout.write(buf[: limit - len(marker)] + marker)
else:
    sys.stdout.write(buf)
")
    else
      ADVISORY_MSG="${ADVISORY_MSG:0:9975}
[truncated at 10K chars]"
    fi
  fi
fi

# --- Emit via the selected transport ---
if [ -n "$ADVISORY_MSG" ]; then
  if [ "$HAS_VALID_INPUT" -eq 1 ]; then
    # Claude Code: emit hookSpecificOutput JSON on stdout
    if command -v python3 >/dev/null 2>&1; then
      printf '%s' "$ADVISORY_MSG" | python3 -c "
import json, sys
ctx = sys.stdin.read()
out = {
    'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'additionalContext': ctx,
        'permissionDecision': 'allow',
    }
}
sys.stdout.write(json.dumps(out))
"
    else
      jq -n \
        --arg ctx "$ADVISORY_MSG" \
        '{hookSpecificOutput: {hookEventName: "PreToolUse", additionalContext: $ctx, permissionDecision: "allow"}}'
    fi
  else
    # No valid Claude Code input — degrade to stderr for manual/test invocations
    echo "$ADVISORY_MSG" >&2
  fi
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
