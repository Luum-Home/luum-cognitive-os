#!/usr/bin/env bash
# SCOPE: os-only
# ADR-185: warn/block risky Bash/git boundaries when this session has unacked block messages.

set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${PROJECT_DIR:-${COGNITIVE_OS_PROJECT_DIR:-$(pwd)}}}"
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COS_ROOT="$(cd "$HOOK_DIR/.." && pwd)"
SCRIPT="$COS_ROOT/scripts/cos_agent_message.py"
[ -f "$SCRIPT" ] || exit 0

MODE="${COS_AGENT_MESSAGE_GUARD_MODE:-warn}"
[ "$MODE" = "off" ] && exit 0

SESSION_ID="${COGNITIVE_OS_SESSION_ID:-${CODEX_SESSION_ID:-${CLAUDE_SESSION_ID:-unknown}}}"
INPUT="$(cat 2>/dev/null || true)"

# Guard only risky Bash/git boundaries. If the harness invokes this without
# payload, keep the historical behavior and check anyway.
if [ -n "$INPUT" ] && command -v python3 >/dev/null 2>&1; then
  SHOULD_CHECK="$(python3 - "$INPUT" <<'PY' 2>/dev/null || echo yes
import json, re, sys
try:
    data=json.loads(sys.argv[1]) if sys.argv[1].strip() else {}
except Exception:
    print('yes'); raise SystemExit
name=str(data.get('tool_name') or data.get('tool') or '')
tool_input=data.get('tool_input') if isinstance(data.get('tool_input'), dict) else {}
cmd=str(tool_input.get('command') or data.get('command') or '')
if name and name != 'Bash':
    print('no'); raise SystemExit
risk = bool(re.search(r'(^|&&|;)\s*git\s+(commit|push|merge|rebase|cherry-pick|reset\s+--hard|stash\s+(apply|pop)|worktree\s+(add|remove)|branch\s+-D)\b', cmd))
print('yes' if risk or not cmd else 'no')
PY
)"
  [ "$SHOULD_CHECK" = "yes" ] || exit 0
fi

OUT_FILE="${TMPDIR:-/tmp}/cos-agent-message-guard.$$.$RANDOM.out"
ERR_FILE="${TMPDIR:-/tmp}/cos-agent-message-guard.$$.$RANDOM.err"
trap 'rm -f "$OUT_FILE" "$ERR_FILE"' EXIT

if python3 "$SCRIPT" --project-dir "$PROJECT_DIR" check --session-id "$SESSION_ID" >"$OUT_FILE" 2>"$ERR_FILE"; then
  exit 0
fi

cat "$ERR_FILE" >&2 || true
if [ "$MODE" = "block" ]; then
  echo "agent-message-inbox-guard: blocking risky operation until messages are acknowledged (COS_AGENT_MESSAGE_GUARD_MODE=block)." >&2
  exit 2
fi

echo "agent-message-inbox-guard: warning only; set COS_AGENT_MESSAGE_GUARD_MODE=block to enforce." >&2
exit 0
