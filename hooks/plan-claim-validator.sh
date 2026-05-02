#!/usr/bin/env bash
# SCOPE: both
# plan-claim-validator.sh — PreToolUse hook for Edit/Write/MultiEdit on plan files.
#
# Detects checkbox transitions ([ ] → [x]) in plan files that lack a
# (verified: ...) evidence reference per ADR-105 §3.2.
#
# Trigger: PreToolUse on Edit | Write | MultiEdit
# Env contract:
#   COS_PLAN_GLOB          — glob defining plan files
#                            Default (SO): .cognitive-os/plans/**/*.md
#                            Default (consumer): plans/**/*.md
#   COS_METRICS_DIR        — where to write metrics JSONL
#                            Default: .cognitive-os/metrics/
#   COS_PLAN_VALIDATOR_MODE — "warn" (default) or "block"
#
# Exit codes:
#   0 — validation passed (or warned in warn mode)
#   1 — invalid input / parse error
#   2 — block mode: checkbox marked done without (verified: ...) reference
#
# Part of: red-team-harness Wave W2
# Pattern-donor: hooks/claim-validator.sh (jq-based parsing + JSONL emission)
set -uo pipefail

_HOOK_NAME="plan-claim-validator"

# ── Env defaults ──────────────────────────────────────────────────────────────
PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"

# Determine default plan glob (SO-aware but portable)
if [ -d "$PROJECT_DIR/.cognitive-os" ]; then
  _DEFAULT_PLAN_GLOB=".cognitive-os/plans/**/*.md"
else
  _DEFAULT_PLAN_GLOB="plans/**/*.md"
fi
COS_PLAN_GLOB="${COS_PLAN_GLOB:-$_DEFAULT_PLAN_GLOB}"
COS_METRICS_DIR="${COS_METRICS_DIR:-$PROJECT_DIR/.cognitive-os/metrics}"
COS_PLAN_VALIDATOR_MODE="${COS_PLAN_VALIDATOR_MODE:-block}"

METRICS_FILE="$COS_METRICS_DIR/plan-claim-validator.jsonl"
TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# ── JSONL helper ──────────────────────────────────────────────────────────────
_emit_metric() {
  local decision="$1" file_path="$2" line_content="$3" line_num="${4:-0}"
  mkdir -p "$COS_METRICS_DIR" 2>/dev/null || true
  local escaped_content
  escaped_content="$(printf '%s' "$line_content" | sed 's/"/\\"/g' | tr -d '\n')"
  local escaped_path
  escaped_path="$(printf '%s' "$file_path" | sed 's/"/\\"/g')"
  printf '{"timestamp":"%s","hook":"%s","decision":"%s","file":"%s","line":%d,"content":"%s","mode":"%s"}\n' \
    "$TIMESTAMP" "$_HOOK_NAME" "$decision" "$escaped_path" "$line_num" \
    "$escaped_content" "$COS_PLAN_VALIDATOR_MODE" \
    >> "$METRICS_FILE" 2>/dev/null || true
}

# ── Read hook input from stdin ────────────────────────────────────────────────
INPUT="$(cat)"
[ -z "$INPUT" ] && exit 0

# ── Require jq ────────────────────────────────────────────────────────────────
if ! command -v jq &>/dev/null; then
  # Cannot parse without jq — skip (don't block)
  exit 0
fi

# ── Determine tool name and target file path ──────────────────────────────────
TOOL_NAME="$(printf '%s' "$INPUT" | jq -r '.tool_name // ""' 2>/dev/null)"
case "$TOOL_NAME" in
  Edit|Write|MultiEdit) ;;
  *) exit 0 ;;  # Only applies to file-writing tools
esac

# Extract target file path from tool input
case "$TOOL_NAME" in
  Edit|Write)
    FILE_PATH="$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // .tool_input.path // ""' 2>/dev/null)"
    ;;
  MultiEdit)
    # MultiEdit carries an array of edits; check the first file path
    FILE_PATH="$(printf '%s' "$INPUT" | jq -r '.tool_input.edits[0].file_path // .tool_input.file_path // ""' 2>/dev/null)"
    ;;
esac

[ -z "$FILE_PATH" ] || [ "$FILE_PATH" = "null" ] && exit 0

# ── Check if file matches COS_PLAN_GLOB ──────────────────────────────────────
# Use bash glob matching against the relative path from PROJECT_DIR
_rel_path="${FILE_PATH#$PROJECT_DIR/}"
# Build glob match using case statement (portable, no extglob needed)
_is_plan_file() {
  local fp="$1" glob="$2"
  # Strip leading ./ from path
  fp="${fp#./}"
  # If glob contains **, split into prefix (before **) and suffix (extension after last *)
  # E.g. "plans/**/*.md" → prefix="plans/", extension=".md"
  if [[ "$glob" == *"**"* ]]; then
    local prefix="${glob%%\*\**}"        # everything before **
    local after_ss="${glob##*\*\*}"      # everything after **  (e.g. "/*.md")
    # Strip leading /* to get the file extension (e.g. "/*.md" → ".md")
    local extension="${after_ss#/}"      # remove leading /  → "*.md"
    extension="${extension#\*}"          # remove leading *   → ".md"
    prefix="${prefix#./}"
    # Path must start with prefix (if non-empty) and end with extension (if non-empty)
    local ok=true
    [[ -n "$prefix" ]] && [[ "$fp" != "$prefix"* ]] && ok=false
    [[ -n "$extension" ]] && [[ "$fp" != *"$extension" ]] && ok=false
    $ok && return 0
    return 1
  fi
  # No **, use exact glob via case statement
  case "$fp" in
    $glob) return 0 ;;
    *) return 1 ;;
  esac
}

if ! _is_plan_file "$_rel_path" "$COS_PLAN_GLOB"; then
  exit 0   # Not a plan file — not our concern
fi

# ── Extract new content from tool input ──────────────────────────────────────
case "$TOOL_NAME" in
  Write)
    NEW_CONTENT="$(printf '%s' "$INPUT" | jq -r '.tool_input.content // ""' 2>/dev/null)"
    ;;
  Edit)
    NEW_CONTENT="$(printf '%s' "$INPUT" | jq -r '.tool_input.new_string // .tool_input.new_content // ""' 2>/dev/null)"
    ;;
  MultiEdit)
    NEW_CONTENT="$(printf '%s' "$INPUT" | jq -r '[.tool_input.edits[]?.new_string // ""] | join("\n")' 2>/dev/null)"
    ;;
esac

[ -z "$NEW_CONTENT" ] || [ "$NEW_CONTENT" = "null" ] && exit 0

# ── Scan for checkbox transitions ─────────────────────────────────────────────
# Detect lines that mark a checkbox as done: "- [x]" (case-insensitive x)
# Pattern: line starting with optional whitespace, then "- [x]" or "* [x]"
VIOLATIONS_FOUND=false
LINE_NUM=0

while IFS= read -r line; do
  LINE_NUM=$((LINE_NUM + 1))

  # Match checkbox-done patterns: "- [x]" or "* [x]" (case-insensitive)
  if printf '%s' "$line" | grep -qiE '^[[:space:]]*[-*][[:space:]]+\[[xX]\]'; then
    # Check if this line or immediate surrounding context contains (verified: ...)
    if printf '%s' "$line" | grep -qE '\(verified:[[:space:]]*[^)]+\)'; then
      # Has verification reference — all good
      _emit_metric "claim.passed" "$FILE_PATH" "$line" "$LINE_NUM"
    else
      # Missing (verified: ...) reference
      VIOLATIONS_FOUND=true
      _emit_metric "claim.failed" "$FILE_PATH" "$line" "$LINE_NUM"

      # Emit warning/error message
      printf '\n[plan-claim-validator] %s: %s L%d: checkbox marked [x] without (verified: …) reference\n' \
        "$([ "$COS_PLAN_VALIDATOR_MODE" = "block" ] && echo "ERROR" || echo "WARN")" \
        "$FILE_PATH" "$LINE_NUM" >&2
      printf '  Content: %s\n' "$line" >&2
      printf '  Expected format: - [x] task description (verified: ls path/to/proof)\n' >&2
      printf '  Per ADR-105 §3.2.\n\n' >&2
    fi
  fi
done <<< "$NEW_CONTENT"

# ── Enforce based on mode ─────────────────────────────────────────────────────
if $VIOLATIONS_FOUND; then
  if [ "$COS_PLAN_VALIDATOR_MODE" = "block" ]; then
    printf '[plan-claim-validator] BLOCK: refusing Edit/Write to plan file — checkbox(es) marked done without verification evidence.\n' >&2
    printf '  File: %s\n' "$FILE_PATH" >&2
    printf '  Add (verified: <command>) to each completed checkbox.\n' >&2
    exit 2
  fi
  # warn mode — allow through, already warned above
fi

exit 0
