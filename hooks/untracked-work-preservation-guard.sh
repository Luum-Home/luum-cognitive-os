#!/usr/bin/env bash
# SCOPE: both
# PreToolUse Bash guard: preserve untracked cross-session work.
# Blocks rm -r, git clean -f, and find -delete when they target untracked work
# unless the command carries an explicit delete classification, reason, and
# approval environment. Prefer scripts/cos-safe-clean for cleanups.
set -uo pipefail

_HOOK_NAME="untracked-work-preservation-guard"
source "$(dirname "$0")/_lib/safe-jsonl.sh"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-$(pwd)}}}"
SOURCE_ROOT="${COS_SOURCE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
DELETE_INTENT_PY="$SOURCE_ROOT/lib/delete_intent.py"
[ ! -f "$DELETE_INTENT_PY" ] && DELETE_INTENT_PY="$PROJECT_DIR/lib/delete_intent.py"
LOG_PATH="$PROJECT_DIR/.cognitive-os/metrics/untracked-delete-blocks.jsonl"

INPUT=""
if [ ! -t 0 ]; then
  INPUT=$(cat 2>/dev/null || true)
fi

TOOL_NAME=""
if [ -n "$INPUT" ] && command -v jq >/dev/null 2>&1; then
  TOOL_NAME=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || true)
  if [ -n "$TOOL_NAME" ] && [ "$TOOL_NAME" != "Bash" ]; then
    exit 0
  fi
fi

COMMAND="${CLAUDE_TOOL_INPUT:-}"
if [ -z "$COMMAND" ] && [ -n "$INPUT" ] && command -v jq >/dev/null 2>&1; then
  COMMAND=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null || true)
fi
[ -z "$COMMAND" ] && exit 0

if ! command -v python3 >/dev/null 2>&1; then
  exit 0
fi

[ ! -f "$DELETE_INTENT_PY" ] && exit 0
REPORT=$(python3 "$DELETE_INTENT_PY" guard --project-dir "$PROJECT_DIR" --command "$COMMAND" 2>/dev/null)
STATUS=$?
[ -z "$REPORT" ] && exit 0

if [ "$STATUS" -eq 0 ]; then
  exit 0
fi

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
esc_report=$(printf '%s' "$REPORT" | tr '\n\r' '  ' | sed 's/\\/\\\\/g; s/"/\\"/g' | head -c 2000)
ENTRY=$(printf '{"timestamp":"%s","event":"blocked","hook":"%s","report":"%s"}' "$TIMESTAMP" "$_HOOK_NAME" "$esc_report")
safe_jsonl_append "$LOG_PATH" "$ENTRY" 2>/dev/null || true

cat >&2 <<'EOF'

=== UNTRACKED-WORK-PRESERVATION-GUARD: BLOCKED ===
This delete command targets untracked or protected work. In a multi-agent repo,
untracked files under docs/research, docs/reports, and plans are treated as
human/agent-owned artifacts until proven otherwise.

Use the safer primitive first:
  scripts/cos-safe-clean --path <path> --dry-run

To execute a cleanup, provide all of:
  COS_SAFE_DELETE_APPROVED=1
  COS_DELETE_CLASSIFICATION=generated-cache|temp|duplicate|rejected|operator-approved
  COS_DELETE_REASON='<why this deletion is safe>'

EOF
printf '%s\n' "$REPORT" >&2
exit 2
