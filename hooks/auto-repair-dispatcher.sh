#!/usr/bin/env bash
# SCOPE: os-only
# PostToolUse hook: Auto-Repair Dispatcher
# Fires on "Agent" completions — checks if known fixes exist for detected errors.
# When 3+ same errors are detected, attempts worktree-isolated repair.
# Advisory only (exit 0 always).

set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="auto-repair-dispatcher"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
source "$(dirname "$0")/_lib/common.sh"

check_private_mode
read_stdin_json

# Extract tool output from various response formats:
#   - Agent format: tool_response is an array of {type, text} objects
#   - Bash format: tool_response is a plain string (stdout)
#   - Object format: tool_response.content is a string or array
TOOL_OUTPUT=$(echo "$_STDIN_JSON" | jq -r '
  if .tool_response | type == "array" then
    [.tool_response[] | .text // ""] | join(" ")
  elif .tool_response | type == "object" then
    if .tool_response.content | type == "array" then
      [.tool_response.content[] | .text // ""] | join(" ")
    else
      .tool_response.content // .tool_response.stdout // ""
    end
  else
    .tool_response // ""
  end
' 2>/dev/null || true)

# Only process if there's failure content
if ! echo "$TOOL_OUTPUT" | grep -qiE '(FAIL|ERROR|build failed|test failed)'; then
  exit 0
fi

METRICS_DIR=$(_resolve_metrics_dir)
ERROR_LOG="$METRICS_DIR/error-learning.jsonl"

# Classify the error type from output
detect_error_type() {
  local output="$1"
  if echo "$output" | grep -qiE '(test.*fail|assertion|pytest|FAILED)'; then
    echo "TEST_FAILURE"
  elif echo "$output" | grep -qiE '(build fail|compilation|cannot compile|go build|tsc)'; then
    echo "BUILD_ERROR"
  elif echo "$output" | grep -qiE '(lint|eslint|golangci|ruff|pyflakes|F401)'; then
    echo "LINT_ERROR"
  else
    echo "AGENT_FAILURE"
  fi
}

detect_service() {
  local output="$1"
  # Try to extract service from file paths in the output
  echo "$output" | grep -oE '(internal|services|packages)/[a-z_-]+' | head -1 | cut -d/ -f2 || echo "unknown"
}

ERROR_TYPE=$(detect_error_type "$TOOL_OUTPUT")
SERVICE=$(detect_service "$TOOL_OUTPUT")

# Check if this error has occurred 3+ times in error-learning.jsonl
SAME_ERROR_COUNT=0
if [ -f "$ERROR_LOG" ]; then
  SAME_ERROR_COUNT=$(grep -c "\"type\":\"$ERROR_TYPE\"" "$ERROR_LOG" 2>/dev/null || echo "0")
fi

# Try worktree-isolated repair when 3+ same errors detected
if [ "$SAME_ERROR_COUNT" -ge 3 ]; then
  echo "AUTO-REPAIR: Detected $SAME_ERROR_COUNT $ERROR_TYPE errors — attempting worktree repair..." >&2

  REPAIR_RESULT=$(python3 -c "
import sys, os
sys.path.insert(0, os.environ.get('CLAUDE_PROJECT_DIR', '.'))
try:
    from lib.auto_repair import AutoRepairEngine
    engine = AutoRepairEngine()
    result = engine.attempt_repair(
        error_type='$ERROR_TYPE',
        service='$SERVICE',
        error_msg='''$(echo "$TOOL_OUTPUT" | head -c 1000)'''
    )
    if result.success:
        print('SUCCESS')
        print('FIX:', result.fix_applied)
        if result.diff:
            print('DIFF_PREVIEW:', result.diff[:500])
    else:
        print('FAILED:', result.reason)
except Exception as e:
    print('ERROR:', str(e))
" 2>/dev/null || echo "ERROR: python3 unavailable")

  if echo "$REPAIR_RESULT" | grep -q "^SUCCESS"; then
    echo "AUTO-REPAIR SUCCESS: $(echo "$REPAIR_RESULT" | grep 'FIX:' | cut -d: -f2-)" >&2
    echo "Diff available — recommend applying via 'git apply'" >&2

    safe_jsonl_append "$METRICS_DIR/repair-dispatch.jsonl" \
      "{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"source\":\"worktree_repair\",\"error_type\":\"$ERROR_TYPE\",\"service\":\"$SERVICE\",\"status\":\"success\"}"
  else
    FAILURE_REASON=$(echo "$REPAIR_RESULT" | grep -v "^$" | head -1)
    echo "AUTO-REPAIR: Worktree repair failed — $FAILURE_REASON" >&2

    safe_jsonl_append "$METRICS_DIR/repair-dispatch.jsonl" \
      "{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"source\":\"worktree_repair\",\"error_type\":\"$ERROR_TYPE\",\"service\":\"$SERVICE\",\"status\":\"failed\",\"reason\":$(echo "$FAILURE_REASON" | jq -Rs '.')}"
  fi
  exit 0
fi

# Fewer than 3 errors — use lightweight suggestion (original behavior)
REPAIR_SUGGESTION=$(python3 -c "
import sys, os
sys.path.insert(0, os.environ.get('CLAUDE_PROJECT_DIR', '.'))
try:
    from lib.auto_repair import classify_error, format_repair_suggestion
    msg = '''$TOOL_OUTPUT'''[:2000]
    r = classify_error('AGENT_FAILURE', msg)
    if r:
        print(format_repair_suggestion(r, msg))
    else:
        print('')
except Exception:
    print('')
" 2>/dev/null || echo "")

if [ -n "$REPAIR_SUGGESTION" ]; then
  echo "AUTO-REPAIR: $REPAIR_SUGGESTION" >&2
  safe_jsonl_append "$METRICS_DIR/repair-dispatch.jsonl" \
    "{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"source\":\"auto_repair.py\",\"suggestion\":$(echo "$REPAIR_SUGGESTION" | jq -Rs '.')}"
  exit 0
fi

# Fallback: search JSONL registry for matching patterns
REGISTRY="$_PROJECT_DIR/.cognitive-os/metrics/remediation-registry.jsonl"
[ -f "$REGISTRY" ] || exit 0

TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

while IFS= read -r line; do
  PATTERN=$(echo "$line" | jq -r '.error_pattern // .pattern // empty' 2>/dev/null)
  DESCRIPTION=$(echo "$line" | jq -r '.description // empty' 2>/dev/null)
  FIX=$(echo "$line" | jq -r '.fix // .fix_command // empty' 2>/dev/null)

  [ -z "$PATTERN" ] && continue

  if echo "$TOOL_OUTPUT" | grep -qiE "$PATTERN"; then
    echo "KNOWN FIX AVAILABLE: $DESCRIPTION" >&2
    if [ -n "$FIX" ]; then
      echo "Suggested fix: $FIX" >&2
    fi

    safe_jsonl_append "$METRICS_DIR/repair-dispatch.jsonl" \
      "{\"timestamp\":\"$TIMESTAMP\",\"pattern\":$(echo "$PATTERN" | jq -Rs '.'),\"description\":$(echo "$DESCRIPTION" | jq -Rs '.')}"
    break
  fi
done < "$REGISTRY"

exit 0
