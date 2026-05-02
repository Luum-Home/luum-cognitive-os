#!/usr/bin/env bash
# SCOPE: os-only
# prompt-quality.sh — Advisory prompt quality gate entrypoint.

set -uo pipefail

INPUT=$(cat 2>/dev/null || true)
PROMPT=$(printf '%s' "$INPUT" | jq -r '.prompt // .message // .tool_input.prompt // empty' 2>/dev/null || true)

if [ -z "$PROMPT" ]; then
  exit 0
fi

if [ "${#PROMPT}" -lt 8 ]; then
  echo "PROMPT QUALITY: prompt is very short; add goal, constraints, and expected output." >&2
fi

exit 0
