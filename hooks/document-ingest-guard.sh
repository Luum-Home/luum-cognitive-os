#!/usr/bin/env bash
# SCOPE: both
# PreToolUse Read guard: block direct PDF reads and route through cos-document-ingest.
set -uo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/_lib/common.sh"
check_disabled_env "document-ingest-guard"

read_stdin_json
TOOL_NAME=$(stdin_field '.tool_name' '')
[ "$TOOL_NAME" = "Read" ] || exit 0

FILE_PATH=$(stdin_field '.tool_input.file_path' '')
[ -n "$FILE_PATH" ] || exit 0

LOWER_PATH=$(printf '%s' "$FILE_PATH" | tr '[:upper:]' '[:lower:]')
case "$LOWER_PATH" in
  *.pdf) ;;
  *) exit 0 ;;
esac

PROJECT_DIR="$_PROJECT_DIR"
if [ -f "$FILE_PATH" ]; then
  DISPLAY_PATH="$FILE_PATH"
else
  DISPLAY_PATH="$PROJECT_DIR/$FILE_PATH"
fi

REASON="PDF files must be converted to Markdown before agent context ingestion. Run: scripts/cos-document-ingest \"$DISPLAY_PATH\" --json, then read the generated Markdown under .cognitive-os/ingest/."
if command -v jq >/dev/null 2>&1; then
  jq -cn --arg reason "$REASON" '{decision:"block", reason:$reason}'
else
  printf '{"decision":"block","reason":"%s"}\n' "$(printf '%s' "$REASON" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read())[1:-1])')"
fi
exit 2
