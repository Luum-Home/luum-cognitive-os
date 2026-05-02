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
declare -a EXPECTED_FILES=()

usage() {
  cat <<'EOF'
Usage:
  scripts/cos-governed-agent.sh --task-id TASK --scope "work" [--expected-file path] [--agent-id ID] [--session-id ID] -- command...

Runs the ADR-116 governed preflight before executing an agent command:
  1. acquire the shared active task claim (.cognitive-os/tasks/active-claims.json)
  2. acquire the runtime claim lease
  3. run cos_work_inventory.py --all --strict

Use this from Codex/VS Code or other harnesses that do not yet expose
Claude-style Agent hooks.
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
    --expected-file) EXPECTED_FILES+=("${2:-}"); shift ;;
    --expected-file=*) EXPECTED_FILES+=("${1#--expected-file=}") ;;
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

release_active_claim() {
  python3 "$SCRIPT_DIR/cos_task_claims.py" --project-dir "$PROJECT_DIR" \
    release --task-id "$TASK_ID" --session-id "$SESSION_ID" >/dev/null 2>&1 || true
}

complete_active_claim() {
  python3 "$SCRIPT_DIR/cos_task_claims.py" --project-dir "$PROJECT_DIR" \
    complete --task-id "$TASK_ID" --session-id "$SESSION_ID" >/dev/null 2>&1 || true
}

ACTIVE_ARGS=(--project-dir "$PROJECT_DIR" claim --task-id "$TASK_ID" --description "$SCOPE" --session-id "$SESSION_ID")
for expected in "${EXPECTED_FILES[@]+"${EXPECTED_FILES[@]}"}"; do
  ACTIVE_ARGS+=(--expected-file "$expected")
done
ACTIVE_OUT=$(python3 "$SCRIPT_DIR/cos_task_claims.py" "${ACTIVE_ARGS[@]}" 2>&1)
ACTIVE_RC=$?
if [ "$ACTIVE_RC" -eq 2 ]; then
  echo "ADR-116 ACTIVE TASK CLAIM BLOCK: task '$TASK_ID' is already claimed." >&2
  echo "$ACTIVE_OUT" >&2
  exit 2
elif [ "$ACTIVE_RC" -ne 0 ]; then
  echo "$ACTIVE_OUT" >&2
  exit "$ACTIVE_RC"
fi

RUNTIME_ARGS=(--project-dir "$PROJECT_DIR" acquire "$TASK_ID" --session-id "$SESSION_ID" --agent-id "$AGENT_ID" --scope "$SCOPE" --ttl-seconds "$TTL_SECONDS")
for expected in "${EXPECTED_FILES[@]+"${EXPECTED_FILES[@]}"}"; do
  RUNTIME_ARGS+=(--expected-file "$expected")
done
CLAIM_OUT=$(python3 "$SCRIPT_DIR/claim_task.py" "${RUNTIME_ARGS[@]}" 2>&1)
CLAIM_RC=$?
if [ "$CLAIM_RC" -eq 2 ]; then
  echo "ADR-116 TASK CLAIM BLOCK: task '$TASK_ID' is already claimed." >&2
  echo "$CLAIM_OUT" >&2
  release_active_claim
  exit 2
elif [ "$CLAIM_RC" -ne 0 ]; then
  echo "$CLAIM_OUT" >&2
  release_active_claim
  exit "$CLAIM_RC"
fi

if [ "${COS_SKIP_GOVERNED_INVENTORY:-0}" != "1" ]; then
  INVENTORY_OUT=$(python3 "$SCRIPT_DIR/cos_work_inventory.py" --project-dir "$PROJECT_DIR" --all --strict --json 2>&1)
  INVENTORY_RC=$?
  if [ "$INVENTORY_RC" -ne 0 ]; then
    echo "ADR-116 GOVERNED PREFLIGHT BLOCK: cos_work_inventory.py --all --strict failed." >&2
    echo "$INVENTORY_OUT" >&2
    release_active_claim
    python3 "$SCRIPT_DIR/claim_task.py" --project-dir "$PROJECT_DIR" \
      release "$TASK_ID" --session-id "$SESSION_ID" --agent-id "$AGENT_ID" >/dev/null 2>&1 || true
    exit "$INVENTORY_RC"
  fi
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
  if [ "$rc" -eq 0 ]; then
    complete_active_claim
  else
    release_active_claim
  fi
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
