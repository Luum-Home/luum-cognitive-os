#!/usr/bin/env bash
# PostToolUse hook: PITER Auto-Refinement Loop
# Fires on "Agent" tool use — detects failures and injects retry instructions
# Must complete in <3 seconds
#
# The PITER loop: Plan -> Implement -> Test -> Evaluate -> Refine
# This hook closes the Evaluate -> Refine gap by detecting failures in agent
# output and telling the orchestrator to re-launch with error context.

set -uo pipefail

_HOOK_NAME="auto-refine"
source "$(dirname "$0")/_lib/safe-jsonl.sh"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
CONFIG_FILE="$PROJECT_DIR/.cognitive-os/cognitive-os.yaml"
# Session-aware: use session-scoped refine directory if session is active
REFINE_DIR="$PROJECT_DIR/.cognitive-os/metrics/auto-refine"
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-}"
if [ -z "$SESSION_ID" ]; then
  _SESSION_FILE="$PROJECT_DIR/.cognitive-os/sessions/.current-session-$$"
  [ -f "$_SESSION_FILE" ] && SESSION_ID=$(cat "$_SESSION_FILE" 2>/dev/null)
fi
if [ -n "$SESSION_ID" ]; then
  SESSION_REFINE_DIR="$PROJECT_DIR/.cognitive-os/sessions/$SESSION_ID/metrics/auto-refine"
  [ -d "$PROJECT_DIR/.cognitive-os/sessions/$SESSION_ID" ] && REFINE_DIR="$SESSION_REFINE_DIR"
fi
MAX_RETRIES=3

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

# Read current phase from cognitive-os.yaml
PHASE="reconstruction"
if [ -f "$CONFIG_FILE" ]; then
  PARSED_PHASE=$(grep 'phase:' "$CONFIG_FILE" | head -1 | sed 's/.*phase:[[:space:]]*//' | sed 's/[[:space:]]*#.*//' | tr -d '[:space:]')
  if [ -n "$PARSED_PHASE" ]; then
    PHASE="$PARSED_PHASE"
  fi
fi

# In production/maintenance, auto-refine requires human approval for code changes
# The hook still detects failures but outputs a recommendation instead of auto-retry
AUTO_REFINE_MODE="auto"
case "$PHASE" in
  reconstruction|stabilization)
    AUTO_REFINE_MODE="auto"
    ;;
  production|maintenance)
    AUTO_REFINE_MODE="suggest"
    ;;
esac

# Extract agent description/prompt for tracking
AGENT_ID=$(echo "$INPUT" | jq -r '
  .tool_input.description // .tool_input.prompt // "unknown"
' 2>/dev/null | head -c 100)

# Create a stable fingerprint for this agent task (first 50 chars of description)
TASK_FINGERPRINT=$(echo "$AGENT_ID" | head -c 50 | md5 2>/dev/null || echo "$AGENT_ID" | head -c 50 | md5sum 2>/dev/null | cut -d' ' -f1 || echo "unknown")

# Extract agent output
AGENT_OUTPUT=$(echo "$INPUT" | jq -r '
  .tool_response.result // .tool_response.output // .tool_response.content // ""
' 2>/dev/null)

if [ -z "$AGENT_OUTPUT" ] || [ "$AGENT_OUTPUT" = "null" ]; then
  exit 0
fi

# --- Failure Detection ---
# Check for failure indicators in the agent output
FAILURE_DETECTED=false
FAILURE_TYPE=""
FAILURE_DETAILS=""

# Test failures
if echo "$AGENT_OUTPUT" | grep -qiE '(FAIL|FAILED|test.*fail|failing test|tests? failed|assertion.*error|expect.*received|✗|✕|ERROR.*test)'; then
  FAILURE_DETECTED=true
  FAILURE_TYPE="TEST_FAILURE"
  FAILURE_DETAILS=$(echo "$AGENT_OUTPUT" | grep -iE '(FAIL|FAILED|Error|✗|✕|expect|assertion)' | head -5)
fi

# Build/compilation errors
if echo "$AGENT_OUTPUT" | grep -qiE '(build failed|compilation error|compile error|cannot find|syntax error|type error|TS[0-9]{4}|cannot resolve|module not found|undefined reference)'; then
  FAILURE_DETECTED=true
  FAILURE_TYPE="BUILD_ERROR"
  FAILURE_DETAILS=$(echo "$AGENT_OUTPUT" | grep -iE '(error|cannot|undefined|syntax|type error|TS[0-9])' | head -5)
fi

# Lint errors
if echo "$AGENT_OUTPUT" | grep -qiE '(lint error|linting failed|eslint.*error|golangci-lint.*error|[0-9]+ error)'; then
  FAILURE_DETECTED=true
  FAILURE_TYPE="LINT_ERROR"
  FAILURE_DETAILS=$(echo "$AGENT_OUTPUT" | grep -iE '(error|warning|lint)' | head -5)
fi

# Coverage below threshold
if echo "$AGENT_OUTPUT" | grep -qiE '(coverage.*below|coverage.*[0-9]+%.*threshold|insufficient coverage|coverage requirement not met)'; then
  FAILURE_DETECTED=true
  FAILURE_TYPE="COVERAGE_FAILURE"
  FAILURE_DETAILS=$(echo "$AGENT_OUTPUT" | grep -iE 'coverage' | head -3)
fi

# Explicit error status from agent
if echo "$INPUT" | jq -e '.tool_response.error // .tool_response.is_error' &>/dev/null 2>&1; then
  FAILURE_DETECTED=true
  if [ -z "$FAILURE_TYPE" ]; then
    FAILURE_TYPE="AGENT_ERROR"
    FAILURE_DETAILS=$(echo "$AGENT_OUTPUT" | head -5)
  fi
fi

# --- Success Detection ---
# If no failure detected, reset retry counter and exit
if [ "$FAILURE_DETECTED" = false ]; then
  # Clean up retry counter on success
  if [ -d "$REFINE_DIR" ] && [ -f "$REFINE_DIR/$TASK_FINGERPRINT.count" ]; then
    # This is a SUCCESS AFTER RETRY — register the fix in remediation registry
    PREV_RETRY_COUNT=$(cat "$REFINE_DIR/$TASK_FINGERPRINT.count" 2>/dev/null || echo "0")
    if [ "$PREV_RETRY_COUNT" -gt 0 ] 2>/dev/null; then
      # Extract last failure type from history for registry
      _LAST_ERROR_TYPE=""
      _LAST_ERROR_PATTERN=""
      if [ -f "$REFINE_DIR/$TASK_FINGERPRINT.history" ]; then
        _LAST_ERROR_TYPE=$(tail -1 "$REFINE_DIR/$TASK_FINGERPRINT.history" | jq -r '.type // "UNKNOWN"' 2>/dev/null)
        _LAST_ERROR_PATTERN=$(tail -1 "$REFINE_DIR/$TASK_FINGERPRINT.history" | jq -r '.details // ""' 2>/dev/null)
      fi
      # Source remediation lib if not already loaded
      if type remediation_register >/dev/null 2>&1 || source "$(dirname "$0")/_lib/remediation.sh" 2>/dev/null; then
        remediation_register \
          "${_LAST_ERROR_TYPE:-UNKNOWN}" \
          "agent-task" \
          "${_LAST_ERROR_PATTERN:-$TASK_FINGERPRINT}" \
          "auto-refine success after retry (attempt $((PREV_RETRY_COUNT + 1)))" \
          "code_change" \
          ""  # no specific command, the fix was agent-driven
      fi
    fi
    rm -f "$REFINE_DIR/$TASK_FINGERPRINT.count" 2>/dev/null
    rm -f "$REFINE_DIR/$TASK_FINGERPRINT.history" 2>/dev/null
  fi
  exit 0
fi

# --- Retry Tracking ---
mkdir -p "$REFINE_DIR" 2>/dev/null

RETRY_FILE="$REFINE_DIR/$TASK_FINGERPRINT.count"
HISTORY_FILE="$REFINE_DIR/$TASK_FINGERPRINT.history"

# Read current retry count
RETRY_COUNT=0
if [ -f "$RETRY_FILE" ]; then
  RETRY_COUNT=$(cat "$RETRY_FILE" 2>/dev/null || echo "0")
  # Validate it's a number
  if ! [[ "$RETRY_COUNT" =~ ^[0-9]+$ ]]; then
    RETRY_COUNT=0
  fi
fi

# Increment retry count
RETRY_COUNT=$((RETRY_COUNT + 1))
echo "$RETRY_COUNT" > "$RETRY_FILE"

# Log attempt to history
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
ENTRY="{\"attempt\":$RETRY_COUNT,\"type\":\"$FAILURE_TYPE\",\"timestamp\":\"$TIMESTAMP\",\"details\":$(echo "$FAILURE_DETAILS" | head -c 200 | jq -Rs .)}"
safe_jsonl_append "$HISTORY_FILE" "$ENTRY"

# --- Decision: Retry or Escalate ---

if [ "$RETRY_COUNT" -ge "$MAX_RETRIES" ]; then
  # --- ESCALATE: Max retries reached ---
  # Build history summary
  HISTORY_SUMMARY=""
  if [ -f "$HISTORY_FILE" ]; then
    HISTORY_SUMMARY=$(cat "$HISTORY_FILE" | jq -s '
      [.[] | "Attempt \(.attempt) [\(.type)]: \(.details[0:100])"] | join("\n")
    ' 2>/dev/null | tr -d '"' || echo "History unavailable")
  fi

  echo ""
  echo "=== PITER AUTO-REFINE: ESCALATION REQUIRED ==="
  echo ""
  echo "Agent task failed after $MAX_RETRIES attempts. Human intervention needed."
  echo ""
  echo "Task: $AGENT_ID"
  echo "Failure type: $FAILURE_TYPE"
  echo ""
  echo "Attempt history:"
  echo "$HISTORY_SUMMARY"
  echo ""
  echo "Latest error:"
  echo "$FAILURE_DETAILS" | head -5
  echo ""
  echo "Recommended actions:"
  echo "  1. Review the error pattern — is this an infrastructure or code issue?"
  echo "  2. Check if the task scope needs adjustment"
  echo "  3. Run /error-analyzer for deeper pattern analysis"
  echo ""
  echo "=== END ESCALATION ==="
  echo ""

  # Clean up retry files after escalation
  rm -f "$RETRY_FILE" 2>/dev/null
  rm -f "$HISTORY_FILE" 2>/dev/null

  exit 0
fi

# --- RETRY: Auto-refine ---

if [ "$AUTO_REFINE_MODE" = "suggest" ]; then
  # Production/maintenance: suggest but don't auto-retry
  echo ""
  echo "=== PITER AUTO-REFINE: FAILURE DETECTED (phase: $PHASE) ==="
  echo ""
  echo "Agent task failed (attempt $RETRY_COUNT/$MAX_RETRIES)."
  echo "Failure type: $FAILURE_TYPE"
  echo ""
  echo "Error details:"
  echo "$FAILURE_DETAILS" | head -3
  echo ""
  echo "Phase '$PHASE' requires human approval for auto-refinement."
  echo "To retry: re-launch the agent with the error context above."
  echo "To skip: acknowledge and move on."
  echo ""
  echo "=== END AUTO-REFINE ==="
  echo ""
  exit 0
fi

# Reconstruction/stabilization: auto-retry
echo ""
echo "=== PITER AUTO-REFINE: RETRY $RETRY_COUNT/$MAX_RETRIES ==="
echo ""
echo "Agent task failed. Auto-refinement triggered."
echo "Failure type: $FAILURE_TYPE"
echo ""
echo "ORCHESTRATOR ACTION REQUIRED: Re-launch the agent with this context:"
echo ""
echo "---"
echo "PITER REFINEMENT (attempt $((RETRY_COUNT + 1))/$MAX_RETRIES)"
echo ""
echo "Previous attempt failed with $FAILURE_TYPE:"
echo "$FAILURE_DETAILS" | head -5
echo ""
echo "Instructions:"
echo "1. Analyze WHY the previous attempt failed"
echo "2. Fix the root cause (not just symptoms)"
echo "3. Re-run verification to confirm the fix"
echo "4. If a different approach is needed, explain why before implementing"
if [ "$RETRY_COUNT" -ge 2 ]; then
  echo "5. LAST ATTEMPT — if this fails, escalate with full diagnosis"
fi
echo "---"
echo ""
echo "=== END AUTO-REFINE ==="
echo ""

exit 0
