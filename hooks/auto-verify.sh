#!/usr/bin/env bash
# PostToolUse hook: Auto-Verify (acceptance criteria extraction)
# Fires on "Agent" completions — checks if output contains ACCEPTANCE CRITERIA section.
# Advisory only (exit 0 always). Logs result to metrics.

set -uo pipefail

_HOOK_NAME="auto-verify"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
source "$(dirname "$0")/_lib/common.sh"

check_private_mode
read_stdin_json

TOOL_OUTPUT=$(stdin_field '.tool_response.content' '')
if [ -z "$TOOL_OUTPUT" ]; then
  TOOL_OUTPUT=$(stdin_field '.tool_response' '' | jq -r 'if type == "array" then .[].text // "" else . // "" end' 2>/dev/null || true)
fi

METRICS_DIR=$(_resolve_metrics_dir)
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Check for acceptance criteria section
STATUS="NO_CRITERIA"
CRITERIA_COUNT=0

if echo "$TOOL_OUTPUT" | grep -qiE 'ACCEPTANCE CRITERIA:'; then
  STATUS="FOUND"
  # Count numbered criteria lines (lines starting with a number)
  CRITERIA_COUNT=$(echo "$TOOL_OUTPUT" | grep -cE '^\s*[0-9]+\.' 2>/dev/null || echo 0)
fi

# Log result
safe_jsonl_append "$METRICS_DIR/auto-verify.jsonl" \
  "{\"timestamp\":\"$TIMESTAMP\",\"status\":\"$STATUS\",\"criteria_count\":$CRITERIA_COUNT}"

if [ "$STATUS" = "NO_CRITERIA" ]; then
  echo "AUTO-VERIFY: No ACCEPTANCE CRITERIA section found. Add numbered criteria for measurable verification." >&2
fi

exit 0
