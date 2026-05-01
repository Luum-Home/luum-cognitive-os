#!/usr/bin/env bash
# SCOPE: both
# CONCERNS: quality, verification, metrics
# PostToolUse hook on Agent — validates Trust Report presence and logs trust scores.
# Checks agent output for Trust Report, extracts score, logs to metrics.

set -euo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="trust-score-validator"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
source "$(dirname "$0")/_lib/common.sh"

# Auto-disabled at capability level 5
check_capability_level "trust-score-validator"
# Runtime disable: DISABLE_HOOK_TRUST_SCORE_VALIDATOR=true skips this hook for the session
check_disabled_env "trust-score-validator"

# Read stdin and gate on Agent/task/delegate tool
read_stdin_json
INPUT="$_STDIN_JSON"
require_tool "Agent" "task" "delegate"

PROJECT_DIR="$_PROJECT_DIR"
COGNITIVE_OS_DIR="$PROJECT_DIR/.cognitive-os"
METRICS_DIR="$COGNITIVE_OS_DIR/metrics"
TRUST_LOG="$METRICS_DIR/trust-scores.jsonl"

# Get agent output
AGENT_OUTPUT=$(echo "$INPUT" | jq -r '.tool_result // .output // empty' 2>/dev/null)
if [[ -z "$AGENT_OUTPUT" ]]; then
  exit 0
fi

# Check for Trust Report presence
HAS_TRUST_REPORT=false
if echo "$AGENT_OUTPUT" | grep -qiE '(TRUST REPORT:|Trust Report:|trust report:)'; then
  HAS_TRUST_REPORT=true
fi

# Also check for common abbreviated forms
if echo "$AGENT_OUTPUT" | grep -qiE '(Trust:\s*[0-9]+|Score:\s*[0-9]+/100)'; then
  HAS_TRUST_REPORT=true
fi

if [[ "$HAS_TRUST_REPORT" == "false" ]]; then
  echo ""
  echo "WARNING: Agent did not provide Trust Report. Confidence cannot be assessed."
  echo "Agents MUST include a Trust Report with score, evidence, uncertainties, and human verification steps."
  echo ""
  exit 0
fi

# Extract score (look for patterns like "Score: 75/100" or "Trust: 75")
SCORE=$(echo "$AGENT_OUTPUT" | grep -oiE 'Score:\s*([0-9]+)(/100)?' | head -1 | grep -oE '[0-9]+' | head -1 || echo "")

if [[ -z "$SCORE" ]]; then
  # Try alternate pattern: "Trust: XX"
  SCORE=$(echo "$AGENT_OUTPUT" | grep -oiE 'Trust:\s*([0-9]+)' | head -1 | grep -oE '[0-9]+' | head -1 || echo "")
fi

if [[ -z "$SCORE" ]]; then
  echo ""
  echo "WARNING: Trust Report found but score could not be extracted."
  echo ""
  exit 0
fi

# Ensure metrics directory exists
mkdir -p "$METRICS_DIR"

# Extract agent name if available
AGENT_NAME=$(echo "$INPUT" | jq -r '.agent_name // .tool_input.prompt // "unknown"' 2>/dev/null | head -c 100)

# Log to metrics
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
ENTRY="{\"timestamp\":\"$TIMESTAMP\",\"agent\":\"$(echo "$AGENT_NAME" | jq -Rs '.' | tr -d '"' | head -c 100)\",\"score\":$SCORE}"
safe_jsonl_append "$TRUST_LOG" "$ENTRY"

# Alert on low confidence
if [[ "$SCORE" -lt 50 ]]; then
  echo ""
  echo "ALERT: Low confidence result (Trust Score: $SCORE/100). Human review strongly recommended."
  echo "The agent reported low confidence in its work. Please verify the output carefully."
  echo ""
elif [[ "$SCORE" -lt 70 ]]; then
  echo ""
  echo "NOTE: Medium-low confidence (Trust Score: $SCORE/100). Spot-check recommended."
  echo ""
fi

exit 0
