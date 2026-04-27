#!/usr/bin/env bash
# SCOPE: os-only
# PURPOSE: <REQUIRED — one-line description of what this hook does>
# EVENT: <REQUIRED — PreToolUse | PostToolUse | UserPromptSubmit | Stop | SessionStart>
# MATCHER: <optional — tool name regex if PreToolUse/PostToolUse, e.g. Edit|Write>
# EXIT_CODES: 0=advisory/pass, 2=block (PreToolUse only)
#
# Behavior:
#   Default:     WARN to stderr (exit 0) — advisory only.
#   Strict mode: exit 2 (block) when COS_STRICT_<NAME>_VALIDATION=1.
#
# Input: JSON on stdin per Claude Code hook contract:
#   {"tool_input": {"file_path": "..."}, "tool_output": ...}
#
# Bash 3.x compatible.

set -euo pipefail

# Read JSON from stdin per Claude Code hook contract
INPUT="$(cat)"

# FAST PATH: skip processing if input doesn't contain the relevant trigger.
# Mirror the skill-frontmatter-validator pattern — avoid Python startup for
# the common case where this hook doesn't apply.
case "$INPUT" in
  *"<TRIGGER_SUBSTRING>"*) ;;
  *) exit 0 ;;
esac

# Parse file_path from JSON input
FILE_PATH="$(printf '%s' "$INPUT" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    ti = d.get('tool_input', d)
    print(ti.get('file_path', ''))
except Exception:
    print('')
" 2>/dev/null || true)"

# Only process files matching this hook's scope
if ! printf '%s' "$FILE_PATH" | grep -qE '<FILE_PATTERN_REGEX>'; then
    exit 0
fi

# File must exist and be readable
if [ ! -f "$FILE_PATH" ]; then
    exit 0
fi

# --- Validation logic ---
ISSUES=""

# TODO: add validation checks; append to ISSUES on failure, e.g.:
# if ! grep -q '## Required Section' "$FILE_PATH"; then
#     ISSUES="${ISSUES}missing ## Required Section\n"
# fi

if [ -z "$ISSUES" ]; then
    exit 0
fi

ISSUE_LIST="$(printf '%s' "$ISSUES" | tr '\n' ',' | sed 's/,$//' | sed 's/,/, /g')"
ARTIFACT_NAME="$(basename "$FILE_PATH")"

MSG="WARNING: <artifact type> contract violation: ${ISSUE_LIST} (file: ${ARTIFACT_NAME})"

# Write metrics (best-effort)
METRICS_DIR="${CLAUDE_PROJECT_DIR:-.}/.cognitive-os/metrics"
if mkdir -p "$METRICS_DIR" 2>/dev/null; then
    TIMESTAMP="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date '+%Y-%m-%dT%H:%M:%SZ')"
    printf '{"timestamp":"%s","file":"%s","issues":[%s]}\n' \
        "$TIMESTAMP" "$ARTIFACT_NAME" \
        "$(printf '%s' "$ISSUES" | python3 -c "import sys,json; lines=sys.stdin.read().strip().splitlines(); print(','.join(json.dumps(l) for l in lines if l))" 2>/dev/null || echo '""')" \
        >> "$METRICS_DIR/<hook-name>-warnings.jsonl" 2>/dev/null || true
fi

if [ "${COS_STRICT_<NAME>_VALIDATION:-0}" = "1" ]; then
    printf '%s\n' "$MSG" >&2
    exit 2
else
    printf '%s\n' "$MSG" >&2
    exit 0
fi
