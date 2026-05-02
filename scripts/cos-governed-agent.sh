#!/usr/bin/env bash
# SCOPE: both
# Portable agent launcher guard for harnesses without Agent hook parity.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-${CODEX_SESSION_ID:-${CLAUDE_SESSION_ID:-manual-session}}}"
AGENT_ID="${COS_AGENT_ID:-governed-agent-$$}"
TASK_ID=""
SCOPE=""
TTL_SECONDS=1800
COMMAND=()

usage() {
  cat <<'EOF'
Usage:
  scripts/cos-governed-agent.sh --task-id TASK --scope "work" [--agent-id ID] [--session-id ID] -- command...

Acquires ADR-116 task claim before running an agent command, records work
ledger start/completion, and releases the claim on exit. Use this from Codex
or other harnesses that do not yet expose Claude-style Agent hooks.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --task-id) TASK_ID="${2:-}"; shift ;;
    --task-id=*) TASK_ID="${1#--task-id=}" ;;
    --scope) SCOPE="${2:-}"; shift ;;
    --scope=*) SCOPE="${1#--scope=}" ;;
    --agent-id) AGENT_ID="${2:-}"; shift ;;
    --agent-id=*) AGENT_ID="${1#--agent-id=}" ;;
    --session-id) SESSION_ID="${2:-}"; shift ;;
    --session-id=*) SESSION_ID="${1#--session-id=}" ;;
    --ttl-seconds) TTL_SECONDS="${2:-1800}"; shift ;;
    --ttl-seconds=*) TTL_SECONDS="${1#--ttl-seconds=}" ;;
    --help|-h) usage; exit 0 ;;
    --) shift; COMMAND=("$@"); break ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

if [ -z "$TASK_ID" ]; then
  echo "cos-governed-agent: --task-id is required" >&2
  exit 2
fi
if [ -z "$SCOPE" ]; then
  SCOPE="$TASK_ID"
fi

CLAIM_OUT=$(python3 "$SCRIPT_DIR/claim_task.py" --project-dir "$PROJECT_DIR" \
  acquire "$TASK_ID" --session-id "$SESSION_ID" --agent-id "$AGENT_ID" \
  --scope "$SCOPE" --ttl-seconds "$TTL_SECONDS" 2>&1)
CLAIM_RC=$?
if [ "$CLAIM_RC" -eq 2 ]; then
  echo "ADR-116 TASK CLAIM BLOCK: task '$TASK_ID' is already claimed." >&2
  echo "$CLAIM_OUT" >&2
  exit 2
elif [ "$CLAIM_RC" -ne 0 ]; then
  echo "$CLAIM_OUT" >&2
  exit "$CLAIM_RC"
fi

python3 "$SCRIPT_DIR/agent_work_ledger.py" --project-dir "$PROJECT_DIR" \
  record --agent-id "$AGENT_ID" --session-id "$SESSION_ID" \
  --task "$TASK_ID" --status started --scope "$SCOPE" >/dev/null 2>&1 || true

finish() {
  local rc="$1"
  local status="completed"
  [ "$rc" -eq 0 ] || status="aborted"
  python3 "$SCRIPT_DIR/agent_work_ledger.py" --project-dir "$PROJECT_DIR" \
    record --agent-id "$AGENT_ID" --session-id "$SESSION_ID" \
    --task "$TASK_ID" --status "$status" --scope "$SCOPE" >/dev/null 2>&1 || true
  python3 "$SCRIPT_DIR/claim_task.py" --project-dir "$PROJECT_DIR" \
    release "$TASK_ID" --session-id "$SESSION_ID" --agent-id "$AGENT_ID" >/dev/null 2>&1 || true
}

if [ "${#COMMAND[@]}" -eq 0 ]; then
  echo "$CLAIM_OUT"
  echo "cos-governed-agent: claim acquired; no command supplied, releasing immediately." >&2
  finish 0
  exit 0
fi

"${COMMAND[@]}"
RC=$?
finish "$RC"
exit "$RC"

