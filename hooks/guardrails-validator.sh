#!/usr/bin/env bash
# SCOPE: project
# PostToolUse hook: Guardrails AI Validator
# Fires on "Agent" tool use — runs PII check on agent responses
# Advisory only (exit 0) — warns on PII detection
# OFF by default — set GUARDRAILS_ENABLED=true to activate
#
# PURPOSE: Adds PII and jailbreak detection to agent output.
# Uses lib/guardrails_validators.py for pattern-based detection
# with optional guardrails-ai package for enhanced detection.

set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="guardrails-validator"
source "$(dirname "$0")/_lib/safe-jsonl.sh"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
METRICS_DIR="$(_resolve_metrics_dir)"
FINDINGS_LOG="$METRICS_DIR/guardrails-findings.jsonl"

# --- Feature gate: OFF by default ---
if [ "${GUARDRAILS_ENABLED:-false}" != "true" ]; then
  exit 0
fi

# Check private mode
if [ -f "/tmp/claude-private-mode-active" ]; then
  exit 0
fi

# Require python3
if ! command -v python3 &>/dev/null; then
  exit 0
fi

# Require jq
if ! command -v jq &>/dev/null; then
  exit 0
fi

# Read stdin (JSON with tool_name, tool_result)
INPUT=$(cat)

# Only process Agent tool results
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
if [[ "$TOOL_NAME" != "Agent" && "$TOOL_NAME" != "task" && "$TOOL_NAME" != "delegate" ]]; then
  exit 0
fi

# Get agent output
AGENT_OUTPUT=$(echo "$INPUT" | jq -r '.tool_result // .tool_response // .output // empty' 2>/dev/null)
if [ -z "$AGENT_OUTPUT" ]; then
  exit 0
fi

# Limit output size to prevent slow scanning
AGENT_OUTPUT=$(echo "$AGENT_OUTPUT" | head -c 10000)

# --- Run PII check via Python ---
# Resolve the lib directory relative to hooks/
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

PII_RESULT=$(python3 -c "
import sys
import json
sys.path.insert(0, '$SCRIPT_DIR')
from lib.guardrails_validators import check_pii

text = sys.stdin.read()
findings = check_pii(text)
result = [f.to_dict() for f in findings]
print(json.dumps(result))
" <<< "$AGENT_OUTPUT" 2>/dev/null) || true

if [ -z "$PII_RESULT" ] || [ "$PII_RESULT" = "[]" ]; then
  exit 0
fi

# --- Parse and report findings ---
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
mkdir -p "$METRICS_DIR" 2>/dev/null

FINDING_COUNT=$(echo "$PII_RESULT" | jq 'length' 2>/dev/null || echo "0")

if [ "$FINDING_COUNT" -eq 0 ]; then
  exit 0
fi

echo ""
echo "=== GUARDRAILS VALIDATOR: $FINDING_COUNT PII finding(s) ==="
echo ""

echo "$PII_RESULT" | jq -c '.[]' 2>/dev/null | while IFS= read -r finding; do
  SEVERITY=$(echo "$finding" | jq -r '.severity')
  CATEGORY=$(echo "$finding" | jq -r '.category')
  MESSAGE=$(echo "$finding" | jq -r '.message')
  MATCH=$(echo "$finding" | jq -r '.match')

  echo "WARNING: [$SEVERITY] $CATEGORY - $MESSAGE"
  if [ "$MATCH" != "" ] && [ "$MATCH" != "null" ]; then
    echo "  Matched: $MATCH"
  fi
  echo ""

  # Log each finding to JSONL
  ENTRY=$(jq -c -n \
    --arg ts "$TIMESTAMP" \
    --arg severity "$SEVERITY" \
    --arg type "PII" \
    --arg category "$CATEGORY" \
    --arg message "$MESSAGE" \
    --arg match "$MATCH" \
    '{timestamp: $ts, severity: $severity, type: $type, category: $category, message: $message, match: $match}')
  safe_jsonl_append "$FINDINGS_LOG" "$ENTRY"
done

CRITICAL_COUNT=$(echo "$PII_RESULT" | jq '[.[] | select(.severity == "CRITICAL")] | length' 2>/dev/null || echo "0")

if [ "$CRITICAL_COUNT" -gt 0 ]; then
  echo "CRITICAL: $CRITICAL_COUNT critical PII finding(s) detected in agent output."
  echo "Review the output for exposed credentials, SSNs, or credit card numbers."
fi

echo ""
echo "=== END GUARDRAILS VALIDATOR ==="
echo ""

exit 0
