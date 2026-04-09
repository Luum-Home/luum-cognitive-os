#!/usr/bin/env bash
# PostToolUse hook: Auto-Repair Dispatcher
# Fires on "Agent" completions — checks if known fixes exist for detected errors.
# Advisory only (exit 0 always).

set -uo pipefail

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
REGISTRY="$_PROJECT_DIR/.cognitive-os/metrics/remediation-registry.jsonl"

# Try Python auto_repair.py first (built-in patterns)
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
[ -f "$REGISTRY" ] || exit 0

TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Search registry for matching patterns
FOUND=false
while IFS= read -r line; do
  PATTERN=$(echo "$line" | jq -r '.error_pattern // empty' 2>/dev/null)
  DESCRIPTION=$(echo "$line" | jq -r '.description // empty' 2>/dev/null)
  FIX=$(echo "$line" | jq -r '.fix // empty' 2>/dev/null)

  [ -z "$PATTERN" ] && continue

  if echo "$TOOL_OUTPUT" | grep -qiE "$PATTERN"; then
    echo "KNOWN FIX AVAILABLE: $DESCRIPTION" >&2
    if [ -n "$FIX" ]; then
      echo "Suggested fix: $FIX" >&2
    fi
    FOUND=true

    safe_jsonl_append "$METRICS_DIR/repair-dispatch.jsonl" \
      "{\"timestamp\":\"$TIMESTAMP\",\"pattern\":$(echo "$PATTERN" | jq -Rs '.'),\"description\":$(echo "$DESCRIPTION" | jq -Rs '.')}"
    break
  fi
done < "$REGISTRY"

exit 0
