#!/bin/bash
# CONCERNS: performance, quality, observability
# Hook: Result Truncator — PostToolUse for Bash
# Prevents large tool outputs from flooding the context window.
# Reads the tool result JSON from stdin, truncates tool_response if too long,
# and outputs the modified JSON. Preserves the JSON structure.
#
# Configuration from cognitive-os.yaml:
#   tokens.result_truncation.enabled: true
#   tokens.result_truncation.max_chars: 5000
#   tokens.result_truncation.head_chars: 2000
#   tokens.result_truncation.tail_chars: 1000
#   tokens.result_truncation.never_truncate_patterns: ["FAIL", "ERROR", ...]

set -uo pipefail

_HOOK_NAME="result-truncator"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
source "$(dirname "$0")/_lib/common.sh"

PROJECT_DIR="$_PROJECT_DIR"
COGNITIVE_OS_DIR="$PROJECT_DIR/.cognitive-os"
CONFIG="$_CONFIG_FILE"
METRICS_DIR="$(resolve_session_dir)"
METRICS_FILE="$METRICS_DIR/truncation-events.jsonl"

# Read tool result from stdin (cached via common.sh)
read_stdin_json
INPUT="$_STDIN_JSON"

# --- Load configuration ---
# Defaults
MAX_CHARS=5000
HEAD_CHARS=2000
TAIL_CHARS=1000
ENABLED="true"
PATTERNS=""

if [ -f "$CONFIG" ]; then
  # Check if truncation is enabled
  ENABLED_VAL=$(grep -A1 "result_truncation:" "$CONFIG" 2>/dev/null | grep "enabled:" | awk '{print $2}' || echo "true")
  [ -n "$ENABLED_VAL" ] && ENABLED="$ENABLED_VAL"

  # Read char limits
  MAX_VAL=$(grep -A10 "result_truncation:" "$CONFIG" 2>/dev/null | grep "max_chars:" | awk '{print $2}' || true)
  HEAD_VAL=$(grep -A10 "result_truncation:" "$CONFIG" 2>/dev/null | grep "head_chars:" | awk '{print $2}' || true)
  TAIL_VAL=$(grep -A10 "result_truncation:" "$CONFIG" 2>/dev/null | grep "tail_chars:" | awk '{print $2}' || true)

  [ -n "$MAX_VAL" ] && [[ "$MAX_VAL" =~ ^[0-9]+$ ]] && MAX_CHARS="$MAX_VAL"
  [ -n "$HEAD_VAL" ] && [[ "$HEAD_VAL" =~ ^[0-9]+$ ]] && HEAD_CHARS="$HEAD_VAL"
  [ -n "$TAIL_VAL" ] && [[ "$TAIL_VAL" =~ ^[0-9]+$ ]] && TAIL_CHARS="$TAIL_VAL"

  # Read never_truncate_patterns from YAML (lines starting with - under never_truncate_patterns)
  PATTERNS=$(awk '/never_truncate_patterns:/,/^[^ ]/{if(/^ *- /) print}' "$CONFIG" 2>/dev/null | sed 's/^ *- *//;s/"//g;s/'"'"'//g' || true)
fi

# If disabled, pass through unchanged
if [ "$ENABLED" != "true" ]; then
  echo "$INPUT"
  exit 0
fi

# --- Extract tool_response ---
RESPONSE=$(echo "$INPUT" | jq -r '.tool_response // empty' 2>/dev/null)

# No response or empty — pass through
if [ -z "$RESPONSE" ]; then
  echo "$INPUT"
  exit 0
fi

# --- Check length ---
RESPONSE_LEN=${#RESPONSE}

if [ "$RESPONSE_LEN" -le "$MAX_CHARS" ]; then
  # Under threshold — pass through unchanged
  echo "$INPUT"
  exit 0
fi

# --- Check never_truncate_patterns ---
# If the response contains critical patterns, do NOT truncate
if [ -n "$PATTERNS" ]; then
  SKIP_TRUNCATION=false
  while IFS= read -r pattern; do
    [ -z "$pattern" ] && continue
    if echo "$RESPONSE" | grep -qF "$pattern"; then
      # Pattern found — check if this is a summary section (last 2000 chars)
      # containing the pattern. If the whole output is huge but the important
      # content is in the tail, we still want to keep it.
      # Strategy: if pattern appears in both head and tail, skip truncation entirely.
      # If pattern only in tail, the tail will be preserved by truncation anyway.
      HEAD_CHECK=$(echo "$RESPONSE" | head -c "$HEAD_CHARS")
      TAIL_CHECK=$(echo "$RESPONSE" | tail -c "$TAIL_CHARS")
      if echo "$HEAD_CHECK" | grep -qF "$pattern" || echo "$TAIL_CHECK" | grep -qF "$pattern"; then
        # Pattern is in the preserved sections — truncation is safe
        continue
      else
        # Pattern only in middle — skip truncation to preserve it
        SKIP_TRUNCATION=true
        break
      fi
    fi
  done <<< "$PATTERNS"

  if [ "$SKIP_TRUNCATION" = true ]; then
    echo "$INPUT"
    exit 0
  fi
fi

# --- Truncate ---
HEAD_PART=$(echo "$RESPONSE" | head -c "$HEAD_CHARS")
TAIL_PART=$(echo "$RESPONSE" | tail -c "$TAIL_CHARS")
TRUNCATION_MSG="\n... [TRUNCATED: ${RESPONSE_LEN} chars total, showing first ${HEAD_CHARS} + last ${TAIL_CHARS}] ...\n"

TRUNCATED_RESPONSE="${HEAD_PART}${TRUNCATION_MSG}${TAIL_PART}"

# --- Rebuild JSON with truncated response ---
# Use jq to safely replace the tool_response field while preserving all other fields
RESULT=$(echo "$INPUT" | jq --arg tr "$TRUNCATED_RESPONSE" '.tool_response = $tr' 2>/dev/null)

if [ $? -eq 0 ] && [ -n "$RESULT" ]; then
  echo "$RESULT"
else
  # If jq fails for any reason, output original to avoid breaking the protocol
  echo "$INPUT"
  exit 0
fi

# --- Log truncation event ---
mkdir -p "$METRICS_DIR"

COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // "unknown"' 2>/dev/null | head -c 200)
COMMAND_ESCAPED=$(echo "$COMMAND" | jq -Rs '.' 2>/dev/null || echo '"unknown"')
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

ENTRY="{\"timestamp\":\"${TIMESTAMP}\",\"original_chars\":${RESPONSE_LEN},\"truncated_chars\":${#TRUNCATED_RESPONSE},\"head_chars\":${HEAD_CHARS},\"tail_chars\":${TAIL_CHARS},\"command\":${COMMAND_ESCAPED}}"
safe_jsonl_append "$METRICS_FILE" "$ENTRY"

exit 0
