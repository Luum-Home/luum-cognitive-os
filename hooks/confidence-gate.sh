#!/usr/bin/env bash
# PostToolUse hook on Agent — enforces confidence thresholds from Trust Reports.
# Complements trust-score-validator.sh by adding BLOCKING behavior for very low scores.
# - Score < 30: CRITICAL warning (blocks in production/maintenance)
# - Score < 50: Gate warning (blocks in production/maintenance)
# - Score >= 50: passes through
# In reconstruction/stabilization: warn only (never blocks)
# Logs to .cognitive-os/metrics/confidence-gates.jsonl

set -uo pipefail

_HOOK_NAME="confidence-gate"
source "$(dirname "$0")/_lib/safe-jsonl.sh"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
METRICS_DIR="$(_resolve_metrics_dir)"
GATE_LOG="$METRICS_DIR/confidence-gates.jsonl"

# Read input from stdin
INPUT=$(cat)

# Only process Agent tool results
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
if [[ "$TOOL_NAME" != "Agent" && "$TOOL_NAME" != "task" && "$TOOL_NAME" != "delegate" ]]; then
  exit 0
fi

# Get agent output
AGENT_OUTPUT=$(echo "$INPUT" | jq -r '.tool_result // .tool_response // .output // empty' 2>/dev/null)
if [[ -z "$AGENT_OUTPUT" ]]; then
  exit 0
fi

# Check for Trust Report presence
HAS_TRUST_REPORT=false
if echo "$AGENT_OUTPUT" | grep -qiE '(TRUST REPORT:|Trust Report:|trust report:)'; then
  HAS_TRUST_REPORT=true
fi
if echo "$AGENT_OUTPUT" | grep -qiE '(Trust:\s*[0-9]+|Score:\s*[0-9]+/100)'; then
  HAS_TRUST_REPORT=true
fi

# If no trust report, exit — trust-score-validator.sh handles missing reports
if [[ "$HAS_TRUST_REPORT" == "false" ]]; then
  exit 0
fi

# Extract score
SCORE=$(echo "$AGENT_OUTPUT" | grep -oiE 'Score:\s*([0-9]+)(/100)?' | head -1 | grep -oE '[0-9]+' | head -1 || echo "")
if [[ -z "$SCORE" ]]; then
  SCORE=$(echo "$AGENT_OUTPUT" | grep -oiE 'Trust:\s*([0-9]+)' | head -1 | grep -oE '[0-9]+' | head -1 || echo "")
fi

if [[ -z "$SCORE" ]]; then
  exit 0
fi

# Score is above threshold — no action needed
if [[ "$SCORE" -ge 50 ]]; then
  exit 0
fi

# Read project phase from cognitive-os.yaml
PHASE="reconstruction"
CONFIG_FILE="$PROJECT_DIR/cognitive-os.yaml"
if [[ -f "$CONFIG_FILE" ]]; then
  DETECTED_PHASE=$(grep -oE 'phase:\s*\S+' "$CONFIG_FILE" | head -1 | awk '{print $2}' || echo "")
  if [[ -n "$DETECTED_PHASE" ]]; then
    PHASE="$DETECTED_PHASE"
  fi
fi

# Extract agent name
AGENT_NAME=$(echo "$INPUT" | jq -r '.agent_name // .tool_input.prompt // "unknown"' 2>/dev/null | head -c 100)

# Determine action based on score and phase
ACTION="warn"
SEVERITY="low"
if [[ "$SCORE" -lt 30 ]]; then
  SEVERITY="critical"
  if [[ "$PHASE" == "production" || "$PHASE" == "maintenance" ]]; then
    ACTION="block"
  fi
elif [[ "$SCORE" -lt 50 ]]; then
  SEVERITY="low"
  if [[ "$PHASE" == "production" || "$PHASE" == "maintenance" ]]; then
    ACTION="block"
  fi
fi

# Log to metrics
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
mkdir -p "$METRICS_DIR" 2>/dev/null
ENTRY=$(jq -c -n \
  --arg ts "$TIMESTAMP" \
  --arg agent "$(echo "$AGENT_NAME" | head -c 100)" \
  --argjson score "$SCORE" \
  --arg severity "$SEVERITY" \
  --arg action "$ACTION" \
  --arg phase "$PHASE" \
  '{timestamp: $ts, agent: $agent, score: $score, severity: $severity, action: $action, phase: $phase}')
safe_jsonl_append "$GATE_LOG" "$ENTRY"

# Output gate message
if [[ "$SCORE" -lt 30 ]]; then
  echo ""
  echo "=== CONFIDENCE GATE: CRITICAL ==="
  echo ""
  echo "CRITICAL: Agent has very low confidence (Score: $SCORE/100)."
  echo "Do NOT proceed without human review."
  echo ""
  if [[ "$ACTION" == "block" ]]; then
    echo "Phase '$PHASE': This result is BLOCKED. Human review is required before proceeding."
  else
    echo "Phase '$PHASE': WARNING only (not blocking in reconstruction/stabilization)."
  fi
  echo ""
  echo "=== END CONFIDENCE GATE ==="
  echo ""
else
  echo ""
  echo "=== CONFIDENCE GATE ==="
  echo ""
  echo "CONFIDENCE GATE: Agent confidence is very low ($SCORE/100)."
  echo "Human review required before proceeding."
  echo ""
  if [[ "$ACTION" == "block" ]]; then
    echo "Phase '$PHASE': This result is BLOCKED. Human review is required before proceeding."
  else
    echo "Phase '$PHASE': WARNING only (not blocking in reconstruction/stabilization)."
  fi
  echo ""
  echo "=== END CONFIDENCE GATE ==="
  echo ""
fi

# Block in production/maintenance phases
if [[ "$ACTION" == "block" ]]; then
  exit 2
fi

exit 0
