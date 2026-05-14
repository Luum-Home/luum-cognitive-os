#!/usr/bin/env bash
# SCOPE: os-only
# PreToolUse guard: blocks exfiltration-shaped external network shell commands.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_lib/common.sh"
check_disabled_env "network-egress-guard"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${COGNITIVE_OS_PROJECT_DIR:-$(pwd)}}"
POLICY="$PROJECT_DIR/manifests/network-egress-policy.yaml"
INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0
command -v jq >/dev/null 2>&1 || exit 0
TOOL_NAME="$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || true)"
[ "$TOOL_NAME" = "Bash" ] || exit 0
COMMAND="$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null || true)"
[ -z "$COMMAND" ] && exit 0
[ "${COS_ALLOW_NETWORK_EGRESS:-0}" = "1" ] && exit 0

RESULT="$(python3 "$PROJECT_DIR/scripts/network_egress_guard.py" --policy "$POLICY" --command "$COMMAND" 2>/dev/null || printf '{"block":false,"warn":false}')"
BLOCK="$(printf '%s' "$RESULT" | jq -r '.block // false' 2>/dev/null || echo false)"
WARN="$(printf '%s' "$RESULT" | jq -r '.warn // false' 2>/dev/null || echo false)"
if [ "$BLOCK" = "true" ]; then
  echo "=== NETWORK EGRESS GUARD: BLOCKED ===" >&2
  echo "External network command contains exfiltration indicators." >&2
  printf '%s\n' "$RESULT" >&2
  echo "Set COS_ALLOW_NETWORK_EGRESS=1 only after explicit human review." >&2
  exit 2
fi
if [ "$WARN" = "true" ]; then
  echo "=== NETWORK EGRESS GUARD: WARNING ===" >&2
  printf '%s\n' "$RESULT" >&2
fi
exit 0
