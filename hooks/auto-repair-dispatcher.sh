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

TOOL_OUTPUT=$(stdin_field '.tool_response.content' '')
if [ -z "$TOOL_OUTPUT" ]; then
  TOOL_OUTPUT=$(stdin_field '.tool_response' '' | jq -r 'if type == "array" then .[].text // "" else . // "" end' 2>/dev/null || true)
fi

# Only process if there's failure content
if ! echo "$TOOL_OUTPUT" | grep -qiE '(FAIL|ERROR|build failed|test failed)'; then
  exit 0
fi

METRICS_DIR=$(_resolve_metrics_dir)
REGISTRY="$_PROJECT_DIR/.cognitive-os/metrics/remediation-registry.jsonl"

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
