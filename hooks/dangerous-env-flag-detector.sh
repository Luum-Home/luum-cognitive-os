#!/usr/bin/env bash
# SCOPE: os-only
# SessionStart/PreToolUse advisory detector for active dangerous COS env flags.
set -uo pipefail
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${COGNITIVE_OS_PROJECT_DIR:-$(pwd)}}"
[ "${COS_DANGEROUS_ENV_DETECTOR_DISABLE:-0}" = "1" ] && exit 0
RESULT="$(python3 "$PROJECT_DIR/scripts/dangerous_env_flag_detector.py" --json 2>/dev/null || true)"
[ -z "$RESULT" ] && exit 0
COUNT="$(printf '%s' "$RESULT" | python3 -c 'import json,sys; print(len(json.load(sys.stdin).get("dangerous_flags",[])))' 2>/dev/null || echo 0)"
if [ "$COUNT" != "0" ]; then
  echo "=== DANGEROUS ENV FLAG DETECTOR: WARNING ===" >&2
  printf '%s\n' "$RESULT" >&2
fi
exit 0
