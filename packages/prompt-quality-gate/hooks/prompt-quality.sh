#!/usr/bin/env bash
# PreToolUse hook: Prompt Quality Scoring
# Fires on "Agent" tool use — scores prompt QUALITY on 5 dimensions
# ADVISORY ONLY: never blocks (always exits 0)
# Must complete in <3 seconds
#
# PURPOSE: Scores agent prompts on specificity, actionability, context,
# measurability, and scope clarity. Complementary to clarification-gate
# (which scores ambiguity). Quality is softer — it suggests improvements.

set -uo pipefail

_HOOK_NAME="prompt-quality"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
source "$(dirname "$0")/_lib/common.sh"

# Auto-disabled at capability level 4+
check_capability_level "prompt-quality" && exit 0

# Skip if private mode active
check_private_mode

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
METRICS_DIR=$(resolve_session_dir)
QUALITY_LOG="$METRICS_DIR/prompt-quality.jsonl"

# Read stdin (JSON with tool_name, tool_input)
INPUT=$(cat)

[ -z "$INPUT" ] && exit 0
command -v jq &>/dev/null || exit 0

# Only process Agent tool
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
[ "$TOOL_NAME" != "Agent" ] && exit 0

# Extract agent prompt/description
AGENT_PROMPT=$(echo "$INPUT" | jq -r '
  .tool_input.prompt // .tool_input.description // ""
' 2>/dev/null)

[ -z "$AGENT_PROMPT" ] || [ "$AGENT_PROMPT" = "null" ] && exit 0

# --- Quality Scoring (5 dimensions, each 0-20) ---
SPECIFICITY=0
ACTIONABILITY=0
CONTEXT=0
MEASURABILITY=0
SCOPE_CLARITY=0
SUGGESTIONS=""

add_suggestion() {
  if [ -z "$SUGGESTIONS" ]; then
    SUGGESTIONS="  - $1"
  else
    SUGGESTIONS="$SUGGESTIONS\n  - $1"
  fi
}

# 1. Specificity (0-20): file paths, function names, concrete references
if echo "$AGENT_PROMPT" | grep -qE '\.(go|ts|py|js|sh|yaml|yml|json|md)\b'; then
  SPECIFICITY=$((SPECIFICITY + 10))
fi
if echo "$AGENT_PROMPT" | grep -qE '(src/|internal/|pkg/|lib/|hooks/|rules/|skills/|tests/|templates/)'; then
  SPECIFICITY=$((SPECIFICITY + 5))
fi
if echo "$AGENT_PROMPT" | grep -qE '[A-Z][a-z]+[A-Z][a-z]+|[a-z]+_[a-z]+|func |function |class |def '; then
  SPECIFICITY=$((SPECIFICITY + 5))
fi
[ "$SPECIFICITY" -lt 10 ] && add_suggestion "Add specific file paths, function names, or concrete references"

# 2. Actionability (0-20): clear action verb + target
if echo "$AGENT_PROMPT" | grep -qiE '\b(implement|create|add|fix|refactor|migrate|remove|update|write|delete|replace|extract|move)\b'; then
  ACTIONABILITY=$((ACTIONABILITY + 10))
fi
if echo "$AGENT_PROMPT" | grep -qiE '\b(in|for|to|at|within)\b.*\.(go|ts|py|js|sh|yaml|json|md)\b'; then
  ACTIONABILITY=$((ACTIONABILITY + 10))
fi
[ "$ACTIONABILITY" -lt 10 ] && add_suggestion "Use a clear action verb with a target (e.g., 'implement X in Y')"

# 3. Context (0-20): background, constraints, prior decisions
if echo "$AGENT_PROMPT" | grep -qiE '\b(because|since|due to|context|background|constraint|requirement|decision|previously|existing|current)\b'; then
  CONTEXT=$((CONTEXT + 10))
fi
if echo "$AGENT_PROMPT" | grep -qiE '\b(pattern|convention|architecture|standard|follow|use the|using the)\b'; then
  CONTEXT=$((CONTEXT + 5))
fi
PROMPT_LENGTH=${#AGENT_PROMPT}
if [ "$PROMPT_LENGTH" -gt 200 ]; then
  CONTEXT=$((CONTEXT + 5))
fi
[ "$CONTEXT" -lt 10 ] && add_suggestion "Include relevant background, constraints, or prior decisions"

# 4. Measurability (0-20): acceptance criteria, verification commands, expected outcomes
if echo "$AGENT_PROMPT" | grep -qiE '(acceptance criteria|success criteria|definition of done|ACCEPTANCE CRITERIA)'; then
  MEASURABILITY=$((MEASURABILITY + 10))
fi
if echo "$AGENT_PROMPT" | grep -qiE '(exits? 0|should pass|must pass|returns? [0-9]|wc -l|grep -c)'; then
  MEASURABILITY=$((MEASURABILITY + 5))
fi
if echo "$AGENT_PROMPT" | grep -qiE '(verify|verification|expected result|expected output|test that)'; then
  MEASURABILITY=$((MEASURABILITY + 5))
fi
[ "$MEASURABILITY" -lt 10 ] && add_suggestion "Add acceptance criteria, verification commands, or expected outcomes"

# 5. Scope clarity (0-20): bounded scope vs unbounded
if echo "$AGENT_PROMPT" | grep -qiE '[0-9]+\s*(file|endpoint|service|item|route|test|module|function|component|line)'; then
  SCOPE_CLARITY=$((SCOPE_CLARITY + 10))
fi
if echo "$AGENT_PROMPT" | grep -qiE '\b(only|just|single|specific|this|one|the following)\b'; then
  SCOPE_CLARITY=$((SCOPE_CLARITY + 5))
fi
if echo "$AGENT_PROMPT" | grep -qiE '\b(all|every|entire|whole|everything|complete the)\b' && ! echo "$AGENT_PROMPT" | grep -qE '[0-9]+'; then
  # Unbounded scope detected — no points added
  :
else
  SCOPE_CLARITY=$((SCOPE_CLARITY + 5))
fi
[ "$SCOPE_CLARITY" -lt 10 ] && add_suggestion "Define bounded scope (e.g., '3 files', 'this endpoint') instead of unbounded terms"

# Cap each dimension at 20
[ "$SPECIFICITY" -gt 20 ] && SPECIFICITY=20
[ "$ACTIONABILITY" -gt 20 ] && ACTIONABILITY=20
[ "$CONTEXT" -gt 20 ] && CONTEXT=20
[ "$MEASURABILITY" -gt 20 ] && MEASURABILITY=20
[ "$SCOPE_CLARITY" -gt 20 ] && SCOPE_CLARITY=20

TOTAL=$((SPECIFICITY + ACTIONABILITY + CONTEXT + MEASURABILITY + SCOPE_CLARITY))

# --- Logging ---
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
AGENT_DESC=$(echo "$AGENT_PROMPT" | head -c 100)

ENTRY=$(jq -c -n \
  --arg ts "$TIMESTAMP" \
  --argjson total "$TOTAL" \
  --argjson specificity "$SPECIFICITY" \
  --argjson actionability "$ACTIONABILITY" \
  --argjson context "$CONTEXT" \
  --argjson measurability "$MEASURABILITY" \
  --argjson scope_clarity "$SCOPE_CLARITY" \
  --arg agent "$AGENT_DESC" \
  '{timestamp: $ts, score: $total, specificity: $specificity, actionability: $actionability, context: $context, measurability: $measurability, scope_clarity: $scope_clarity, agent: $agent}')
safe_jsonl_append "$QUALITY_LOG" "$ENTRY"

# --- Output ---
if [ "$TOTAL" -lt 30 ]; then
  echo ""
  echo "=== PROMPT QUALITY: LOW ($TOTAL/100) ==="
  echo ""
  echo "Prompt quality is low. Consider improving:"
  echo -e "$SUGGESTIONS"
  echo ""
  echo "  Scores: specificity=$SPECIFICITY actionability=$ACTIONABILITY context=$CONTEXT measurability=$MEASURABILITY scope=$SCOPE_CLARITY"
  echo ""
  echo "=== END PROMPT QUALITY ==="
  echo ""
fi

# Advisory only — never blocks
exit 0
