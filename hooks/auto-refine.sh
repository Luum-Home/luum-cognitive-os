#!/usr/bin/env bash
# CONCERNS: quality, refinement, piter-loop, phase-aware
# Auto-Refine Hook — PostToolUse for Agent
# Detects failure markers in the agent's output and emits retry instructions
# for the orchestrator (PITER Evaluate -> Refine edge). Phase-aware:
#   reconstruction / stabilization : enabled (emit retry context)
#   production     / maintenance   : suggestion-only (human approval required)
#
# Advisory: exits 0 always. Tracks retry count per task fingerprint under
# .cognitive-os/metrics/auto-refine/{fingerprint}.count with MAX_RETRIES=3.
#
# Contract: described in rules/closed-loop-prompts.md, rules/phase-aware-agents.md,
# and skills/auto-refine/SKILL.md. Related: completion-gate.sh performs the same
# logic as part of its 3-phase pipeline. This standalone hook is available for
# users that wire auto-refine separately.
set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="auto-refine"
source "$(dirname "$0")/_lib/safe-jsonl.sh"

INPUT=$(cat)
[ -z "$INPUT" ] && exit 0
command -v jq >/dev/null 2>&1 || exit 0

TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
[ "$TOOL_NAME" != "Agent" ] && exit 0

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
CONFIG_FILE="$PROJECT_DIR/.cognitive-os/cognitive-os.yaml"
[ ! -f "$CONFIG_FILE" ] && CONFIG_FILE="$PROJECT_DIR/cognitive-os.yaml"

# Session-scoped metrics
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-}"
if [ -z "$SESSION_ID" ]; then
  _SESSION_FILE="$PROJECT_DIR/.cognitive-os/sessions/.current-session-$$"
  [ -f "$_SESSION_FILE" ] && SESSION_ID=$(cat "$_SESSION_FILE" 2>/dev/null)
fi
if [ -n "$SESSION_ID" ] && [ -d "$PROJECT_DIR/.cognitive-os/sessions/$SESSION_ID" ]; then
  METRICS_DIR="$PROJECT_DIR/.cognitive-os/sessions/$SESSION_ID/metrics"
fi

REFINE_DIR="$METRICS_DIR/auto-refine"
MAX_RETRIES=3

# Resolve phase
PHASE="reconstruction"
if [ -f "$CONFIG_FILE" ]; then
  PARSED=$(grep -E '^\s*phase:' "$CONFIG_FILE" | head -1 | sed 's/.*phase:[[:space:]]*//' | sed 's/[[:space:]]*#.*//' | tr -d '[:space:]')
  [ -n "$PARSED" ] && PHASE="$PARSED"
fi

MODE="auto"
case "$PHASE" in
  reconstruction|stabilization) MODE="auto" ;;
  production|maintenance)       MODE="suggest" ;;
esac

# Extract response + prompt
RESPONSE=$(echo "$INPUT" | jq -r '.tool_response.result // .tool_response.output // .tool_response.content // .tool_response // ""' 2>/dev/null)
AGENT_PROMPT=$(echo "$INPUT" | jq -r '.tool_input.prompt // .tool_input.description // ""' 2>/dev/null)
[ -z "$RESPONSE" ] || [ "$RESPONSE" = "null" ] && exit 0

# Detect failures
FAIL=false
FAIL_TYPE=""
FAIL_DETAILS=""

if echo "$RESPONSE" | grep -qiE '(FAIL|FAILED|test.*fail|failing test|tests? failed|assertion.*error|expect.*received)'; then
  FAIL=true; FAIL_TYPE="TEST_FAILURE"
  FAIL_DETAILS=$(echo "$RESPONSE" | grep -iE '(FAIL|FAILED|Error|expect|assertion)' | head -5)
fi
if echo "$RESPONSE" | grep -qiE '(build failed|compilation error|compile error|cannot find|syntax error|type error|TS[0-9]{4}|cannot resolve|module not found)'; then
  FAIL=true; [ -z "$FAIL_TYPE" ] && FAIL_TYPE="BUILD_ERROR"
  [ -z "$FAIL_DETAILS" ] && FAIL_DETAILS=$(echo "$RESPONSE" | grep -iE '(error|cannot|undefined|syntax)' | head -5)
fi
if echo "$RESPONSE" | grep -qiE '(lint error|linting failed|eslint.*error|golangci-lint.*error)'; then
  FAIL=true; [ -z "$FAIL_TYPE" ] && FAIL_TYPE="LINT_ERROR"
  [ -z "$FAIL_DETAILS" ] && FAIL_DETAILS=$(echo "$RESPONSE" | grep -iE '(error|warning|lint)' | head -5)
fi
if echo "$INPUT" | jq -e '.tool_response.error // .tool_response.is_error' >/dev/null 2>&1; then
  FAIL=true; [ -z "$FAIL_TYPE" ] && FAIL_TYPE="AGENT_ERROR"
  [ -z "$FAIL_DETAILS" ] && FAIL_DETAILS=$(echo "$RESPONSE" | head -5)
fi

AGENT_ID=$(echo "$AGENT_PROMPT" | head -c 100)
FINGERPRINT=$(echo "$AGENT_ID" | head -c 50 | md5 2>/dev/null || echo "$AGENT_ID" | head -c 50 | md5sum 2>/dev/null | cut -d' ' -f1 || echo "unknown")

# Success path: clear retry state, exit
if [ "$FAIL" = false ]; then
  if [ -d "$REFINE_DIR" ] && [ -f "$REFINE_DIR/$FINGERPRINT.count" ]; then
    rm -f "$REFINE_DIR/$FINGERPRINT.count" "$REFINE_DIR/$FINGERPRINT.history" 2>/dev/null
  fi
  exit 0
fi

# Increment retry counter
mkdir -p "$REFINE_DIR" 2>/dev/null
RETRY_FILE="$REFINE_DIR/$FINGERPRINT.count"
COUNT=0
[ -f "$RETRY_FILE" ] && COUNT=$(cat "$RETRY_FILE" 2>/dev/null || echo "0")
[[ "$COUNT" =~ ^[0-9]+$ ]] || COUNT=0
COUNT=$((COUNT + 1))
echo "$COUNT" > "$RETRY_FILE"
safe_jsonl_append "$REFINE_DIR/$FINGERPRINT.history" "{\"attempt\":$COUNT,\"type\":\"$FAIL_TYPE\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"details\":$(echo "$FAIL_DETAILS" | head -c 200 | jq -Rs .)}"

# Escalation: exhausted retries
if [ "$COUNT" -ge "$MAX_RETRIES" ]; then
  echo ""
  echo "=== AUTO-REFINE: ESCALATION REQUIRED ==="
  echo "Agent failed $MAX_RETRIES times. Human intervention needed."
  echo "Task:         $AGENT_ID"
  echo "Failure type: $FAIL_TYPE"
  echo "Latest error:"
  echo "$FAIL_DETAILS" | head -5
  echo "=== END ESCALATION ==="
  echo ""
  rm -f "$RETRY_FILE" "$REFINE_DIR/$FINGERPRINT.history" 2>/dev/null
  exit 0
fi

# Suggestion mode (production / maintenance): no auto-retry
if [ "$MODE" = "suggest" ]; then
  echo ""
  echo "=== AUTO-REFINE: FAILURE DETECTED (phase: $PHASE) ==="
  echo "Attempt $COUNT/$MAX_RETRIES. Failure type: $FAIL_TYPE"
  echo "Phase '$PHASE' requires human approval before auto-refinement."
  echo "=== END AUTO-REFINE ==="
  echo ""
  exit 0
fi

# Auto mode (reconstruction / stabilization): emit retry instructions
echo ""
echo "=== AUTO-REFINE: RETRY $COUNT/$MAX_RETRIES (phase: $PHASE) ==="
echo "ORCHESTRATOR ACTION REQUIRED: Re-launch the agent with this context:"
echo "---"
echo "PITER REFINEMENT (attempt $((COUNT + 1))/$MAX_RETRIES)"
echo "Previous attempt failed with $FAIL_TYPE:"
echo "$FAIL_DETAILS" | head -5
echo ""
echo "Instructions:"
echo "1. Analyze WHY the previous attempt failed (root cause, not symptoms)."
echo "2. Use a DIFFERENT approach on this attempt."
echo "3. Re-run verification to confirm the fix."
[ "$COUNT" -ge 2 ] && echo "4. LAST ATTEMPT — if this fails, escalate with full diagnosis."
echo "---"
echo "=== END AUTO-REFINE ==="
echo ""

exit 0
