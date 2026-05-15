#!/usr/bin/env bash
# SCOPE: both
# ai-provider-identity-guard.sh — PostToolUse guard for invented AI-provider emails.
# CONCERNS: provenance, credibility, public-history-safety
set -uo pipefail

INPUT=$(cat)
TOOL_NAME=$(printf '%s' "$INPUT" | jq -r '.tool_name // ""' 2>/dev/null || echo "")
case "$TOOL_NAME" in
  Edit|Write) ;;
  *) exit 0 ;;
esac

FILE_PATH=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // .tool_input.filePath // ""' 2>/dev/null || echo "")
[ -n "$FILE_PATH" ] || exit 0
[ -f "$FILE_PATH" ] || exit 0

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${COGNITIVE_OS_PROJECT_DIR:-$(pwd)}}"
if [ -x "$PROJECT_DIR/scripts/ai-provider-identity-guard" ]; then
  "$PROJECT_DIR/scripts/ai-provider-identity-guard" --project-dir "$PROJECT_DIR" --path "$FILE_PATH" || exit 2
fi
exit 0
