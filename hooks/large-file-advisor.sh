#!/usr/bin/env bash
# SCOPE: both
# CONCERNS: quality, observability
# PreToolUse hook: Large File Advisor for Read tool
# Checks file size BEFORE the Read happens. If the file exceeds ~40KB (~10K tokens),
# outputs an advisory message suggesting offset/limit parameters.
# Advisory only (exit 0 always) — does NOT block reads.
# Must complete in <200ms.

set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="large-file-advisor"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
source "$(dirname "$0")/_lib/common.sh"

# Skip in private mode
check_private_mode

# Read stdin JSON (tool_name, tool_input)
read_stdin_json

# Only process Read tool
TOOL_NAME=$(stdin_field '.tool_name' '')
if [ "$TOOL_NAME" != "Read" ]; then
  exit 0
fi

PROJECT_DIR="$_PROJECT_DIR"

# Extract file_path from tool_input
FILE_PATH=$(stdin_field '.tool_input.file_path' '')
if [ -z "$FILE_PATH" ]; then
  exit 0
fi

# If offset/limit already provided, the user knows what they're doing
OFFSET=$(stdin_field '.tool_input.offset' '')
LIMIT=$(stdin_field '.tool_input.limit' '')
if [ -n "$OFFSET" ] || [ -n "$LIMIT" ]; then
  exit 0
fi

# Check if file exists
if [ ! -f "$FILE_PATH" ]; then
  exit 0
fi

# Check file size (threshold: 40KB ~ 10K tokens)
THRESHOLD=40000
FILE_SIZE=$(wc -c < "$FILE_PATH" 2>/dev/null | tr -d ' ')

if [ -z "$FILE_SIZE" ] || [ "$FILE_SIZE" -le "$THRESHOLD" ]; then
  exit 0
fi

# File exceeds threshold — generate advisory
EST_TOKENS=$((FILE_SIZE / 4))
LINE_COUNT=$(wc -l < "$FILE_PATH" 2>/dev/null | tr -d ' ')

# Generate section hints for common file types
SECTIONS=""
EXT="${FILE_PATH##*.}"
case "$EXT" in
  py)
    SECTIONS=$(grep -n "^class \|^def \|^async def " "$FILE_PATH" 2>/dev/null | head -8 | sed 's/^/    /')
    ;;
  go)
    SECTIONS=$(grep -n "^func \|^type .* struct\|^type .* interface" "$FILE_PATH" 2>/dev/null | head -8 | sed 's/^/    /')
    ;;
  md)
    SECTIONS=$(grep -n "^#" "$FILE_PATH" 2>/dev/null | head -8 | sed 's/^/    /')
    ;;
  sh|bash)
    SECTIONS=$(grep -n "^[a-zA-Z_].*() {" "$FILE_PATH" 2>/dev/null | head -8 | sed 's/^/    /')
    ;;
  ts|js)
    SECTIONS=$(grep -n "^export \|^class \|^function \|^interface " "$FILE_PATH" 2>/dev/null | head -8 | sed 's/^/    /')
    ;;
esac

# Output advisory to stderr (visible to the agent but doesn't modify tool behavior)
{
  echo "LARGE FILE ADVISORY: $(basename "$FILE_PATH")"
  echo "  Size: ${FILE_SIZE} bytes (${LINE_COUNT} lines, ~${EST_TOKENS} tokens)"
  echo "  This file may exceed the Read tool's token limit."
  echo "  Consider using offset+limit parameters for targeted reads."
  if [ -n "$SECTIONS" ]; then
    echo "  File sections:"
    echo "$SECTIONS"
  fi
} >&2

# Log to metrics
METRICS_DIR="$(resolve_session_dir)"
METRICS_FILE="$METRICS_DIR/large-file-reads.jsonl"

TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
REL_PATH="${FILE_PATH#$PROJECT_DIR/}"
ENTRY="{\"timestamp\":\"${TIMESTAMP}\",\"path\":\"${REL_PATH}\",\"bytes\":${FILE_SIZE},\"lines\":${LINE_COUNT},\"est_tokens\":${EST_TOKENS},\"advisory\":true}"
safe_jsonl_append "$METRICS_FILE" "$ENTRY"

exit 0
