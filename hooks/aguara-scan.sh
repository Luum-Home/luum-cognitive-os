#!/usr/bin/env bash
# SCOPE: project
# PreToolUse hook: Aguara AI Agent Security Scanner
# Fires on "Agent" tool use — scans agent prompts before execution
# Deterministic rule-based scanning (no LLM required)
# OFF by default — graceful skip if aguara is not installed
#
# PURPOSE: Scans agent skill content and prompts for prompt injection,
# data exfiltration, supply chain attacks using 189 rules across 14 threat categories.
# Complements parry-guard (ML-based) with deterministic pattern matching.

set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="aguara-scan"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
source "$(dirname "$0")/_lib/common.sh"
# Runtime disable: DISABLE_HOOK_AGUARA_SCAN=true skips this hook for the session
check_disabled_env "aguara-scan"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
METRICS_DIR="$(_resolve_metrics_dir)"
FINDINGS_LOG="$METRICS_DIR/aguara-findings.jsonl"

# Check private mode
if [ -f "/tmp/claude-private-mode-active" ]; then
  exit 0
fi

# Require aguara — graceful degradation if not installed
if ! command -v aguara &>/dev/null; then
  exit 0
fi

# Require jq for JSON parsing
if ! command -v jq &>/dev/null; then
  exit 0
fi

# Read stdin (JSON with tool_name, tool_input)
INPUT=$(cat)

# Only process Agent tool uses
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
if [[ "$TOOL_NAME" != "Agent" && "$TOOL_NAME" != "task" && "$TOOL_NAME" != "delegate" ]]; then
  exit 0
fi

# Extract the agent prompt from tool input
AGENT_PROMPT=$(echo "$INPUT" | jq -r '.tool_input.prompt // .tool_input.description // .tool_input // empty' 2>/dev/null)
if [ -z "$AGENT_PROMPT" ]; then
  exit 0
fi

# --- Run Aguara scan ---
AGUARA_OUTPUT=$(echo "$AGENT_PROMPT" | aguara scan --stdin --format json 2>/dev/null) || true

if [ -z "$AGUARA_OUTPUT" ]; then
  exit 0
fi

# --- Parse results ---
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
mkdir -p "$METRICS_DIR" 2>/dev/null

# Extract findings count
TOTAL_FINDINGS=$(echo "$AGUARA_OUTPUT" | jq '.findings // .results // [] | length' 2>/dev/null || echo "0")

if [ "$TOTAL_FINDINGS" -eq 0 ]; then
  exit 0
fi

# Classify and output findings
CRITICALS=0
WARNINGS=0
INFOS=0

echo ""
echo "=== AGUARA SECURITY SCAN: $TOTAL_FINDINGS finding(s) ==="
echo ""

# Process each finding
echo "$AGUARA_OUTPUT" | jq -c '(.findings // .results // [])[]' 2>/dev/null | while IFS= read -r finding; do
  SEVERITY=$(echo "$finding" | jq -r '.severity // .level // "INFO"' | tr '[:lower:]' '[:upper:]')
  RULE_ID=$(echo "$finding" | jq -r '.rule_id // .rule // .id // "unknown"')
  MESSAGE=$(echo "$finding" | jq -r '.message // .description // "No message"' | head -c 300)
  CATEGORY=$(echo "$finding" | jq -r '.category // .type // "unknown"')

  # Map aguara severity to adversarial review format
  case "$SEVERITY" in
    CRITICAL|ERROR|HIGH)
      TIER="BLOCKER"
      ;;
    WARNING|MEDIUM)
      TIER="CONCERN"
      ;;
    *)
      TIER="SUGGESTION"
      ;;
  esac

  echo "### [$TIER] $RULE_ID"
  echo ""
  echo "**Category**: $CATEGORY"
  echo "**What**: $MESSAGE"
  echo "**Severity**: $SEVERITY"
  echo ""

  # Log each finding to JSONL
  ENTRY=$(jq -c -n \
    --arg ts "$TIMESTAMP" \
    --arg tier "$TIER" \
    --arg rule_id "$RULE_ID" \
    --arg message "$(echo "$MESSAGE" | head -c 300)" \
    --arg category "$CATEGORY" \
    --arg severity "$SEVERITY" \
    '{timestamp: $ts, tier: $tier, rule_id: $rule_id, message: $message, category: $category, severity: $severity}')
  safe_jsonl_append "$FINDINGS_LOG" "$ENTRY"
done

# Count by tier
CRITICALS=$(echo "$AGUARA_OUTPUT" | jq '[(.findings // .results // [])[] | select((.severity // .level // "INFO") | ascii_upcase | test("CRITICAL|ERROR|HIGH"))] | length' 2>/dev/null || echo "0")
WARNINGS=$(echo "$AGUARA_OUTPUT" | jq '[(.findings // .results // [])[] | select((.severity // .level // "INFO") | ascii_upcase | test("WARNING|MEDIUM"))] | length' 2>/dev/null || echo "0")
INFOS=$(echo "$AGUARA_OUTPUT" | jq '[(.findings // .results // [])[] | select((.severity // .level // "INFO") | ascii_upcase | test("CRITICAL|ERROR|HIGH|WARNING|MEDIUM") | not)] | length' 2>/dev/null || echo "0")

echo "---"
echo "Summary: $CRITICALS BLOCKER(s), $WARNINGS CONCERN(s), $INFOS SUGGESTION(s)"

if [ "$CRITICALS" -gt 0 ]; then
  echo ""
  echo "AGUARA SECURITY BLOCK: $CRITICALS CRITICAL finding(s) detected in agent prompt."
  echo "Agent launch blocked. Review and address security findings before proceeding."
  echo ""
  echo "=== END AGUARA SCAN ==="
  echo ""
  exit 2
fi

echo ""
echo "=== END AGUARA SCAN ==="
echo ""

exit 0
