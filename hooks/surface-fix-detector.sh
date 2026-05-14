#!/usr/bin/env bash
# SCOPE: os-only
# CONCERNS: quality, decision-depth, invariant-drift
# surface-fix-detector — PostToolUse for Edit|Write|MultiEdit
# Advisory hook: detects "surface fix" patterns where a diff is ~100% additions
# (no substantive code changes) AND the additions contain clarifying-prose
# trigger words. Such edits often resolve a finding by clarifying prose
# instead of pinning the invariant, legitimising the status quo.
#
# Always exits 0 (advisory, never blocking).
# Logs to .cognitive-os/metrics/surface-fix-detector.jsonl
#
# Contract: rules/decision-depth-gate.md; paired with skills/invariant-check.
set -uo pipefail

# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh" 2>/dev/null || true

_HOOK_NAME="surface-fix-detector"
# safe_jsonl_append is preferred; fall back to raw append if lib unavailable.
if [ -f "$(dirname "$0")/_lib/safe-jsonl.sh" ]; then
  # shellcheck disable=SC1091
  source "$(dirname "$0")/_lib/safe-jsonl.sh"
fi

INPUT=$(cat)
[ -z "$INPUT" ] && exit 0
command -v jq >/dev/null 2>&1 || exit 0

TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
case "$TOOL_NAME" in
  Edit|Write|MultiEdit) ;;
  *) exit 0 ;;
esac

FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
[ -z "$FILE_PATH" ] && exit 0

# Collect the "new" text depending on tool.
NEW_TEXT=""
OLD_TEXT=""
case "$TOOL_NAME" in
  Write)
    NEW_TEXT=$(echo "$INPUT" | jq -r '.tool_input.content // empty' 2>/dev/null)
    ;;
  Edit)
    OLD_TEXT=$(echo "$INPUT" | jq -r '.tool_input.old_string // empty' 2>/dev/null)
    NEW_TEXT=$(echo "$INPUT" | jq -r '.tool_input.new_string // empty' 2>/dev/null)
    ;;
  MultiEdit)
    OLD_TEXT=$(echo "$INPUT" | jq -r '[.tool_input.edits[]?.old_string] | join("\n")' 2>/dev/null)
    NEW_TEXT=$(echo "$INPUT" | jq -r '[.tool_input.edits[]?.new_string] | join("\n")' 2>/dev/null)
    ;;
esac

[ -z "$NEW_TEXT" ] && exit 0

# Count lines added vs replaced/removed. Empty strings count as 0 lines.
_count_lines() {
  if [ -z "$1" ]; then
    echo 0
  else
    printf '%s' "$1" | awk 'END{print NR+0}'
  fi
}
NEW_LINES=$(_count_lines "$NEW_TEXT")
OLD_LINES=$(_count_lines "$OLD_TEXT")
: "${NEW_LINES:=0}"
: "${OLD_LINES:=0}"

# For Write: treat entirely as additions (ratio = 100%).
# For Edit/MultiEdit: additions_ratio = new_lines / (new_lines + old_lines).
ADDITIONS_RATIO=0
if [ "$NEW_LINES" -ge 4 ]; then
  TOTAL=$((NEW_LINES + OLD_LINES))
  if [ "$TOTAL" -gt 0 ]; then
    ADDITIONS_RATIO=$(( (NEW_LINES * 100) / TOTAL ))
  fi
fi

# Trigger word scan (case-insensitive) over the new text only.
TRIGGER_HIT=""
# Portable case-insensitive grep
if printf '%s' "$NEW_TEXT" | grep -qiE 'clarify|aclarar|clarification|explanation|explanatory|to document|to clarify|nota:|note:|^note |^nota '; then
  TRIGGER_HIT="true"
fi

# Decide: advisory only when additions_ratio > 90 AND trigger hit.
if [ -z "$TRIGGER_HIT" ] || [ "$ADDITIONS_RATIO" -le 90 ]; then
  exit 0
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
mkdir -p "$METRICS_DIR" 2>/dev/null || true
LOG_FILE="$METRICS_DIR/surface-fix-detector.jsonl"

TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
REL_FILE=$(echo "$FILE_PATH" | sed "s|$PROJECT_DIR/||")
ENTRY=$(printf '{"timestamp":"%s","tool":"%s","file":"%s","additions_ratio":%d,"new_lines":%d,"old_lines":%d}' \
  "$TS" "$TOOL_NAME" "$REL_FILE" "$ADDITIONS_RATIO" "$NEW_LINES" "$OLD_LINES")

if command -v safe_jsonl_append >/dev/null 2>&1; then
  safe_jsonl_append "$LOG_FILE" "$ENTRY"
else
  printf '%s\n' "$ENTRY" >> "$LOG_FILE" 2>/dev/null || true
fi

cat <<'EOF'

[surface-fix-detector] ADVISORY: This edit appears to add prose without changing underlying values.
If the finding flagged an inconsistency, run /invariant-check on the touched file pair BEFORE
committing to ensure values are coherent. Clarifying prose legitimises status quo — verify first.

EOF

exit 0
