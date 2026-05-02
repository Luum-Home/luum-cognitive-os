#!/usr/bin/env bash
# SCOPE: both
# Portable edit guard for harnesses without Edit/Write hook parity.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-${CODEX_SESSION_ID:-${CLAUDE_SESSION_ID:-manual-session}}}"
TARGET=""
REASON="governed-edit"
MODE="exclusive-edit"
TASK_ID=""
COMMAND=()

usage() {
  cat <<'EOF'
Usage:
  scripts/cos-governed-edit.sh --task-id TASK --file path [--reason text] -- command...

Runs the ADR-116 governed edit preflight before executing a command:
  1. acquire the shared active task claim
  2. run cos_work_inventory.py --all --strict
  3. acquire the Cognitive OS edit lock

Use this from Codex/VS Code or other harnesses without Edit/Write hook parity.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --file) TARGET="${2:-}"; shift ;;
    --file=*) TARGET="${1#--file=}" ;;
    --task-id) TASK_ID="${2:-}"; shift ;;
    --task-id=*) TASK_ID="${1#--task-id=}" ;;
    --reason) REASON="${2:-}"; shift ;;
    --reason=*) REASON="${1#--reason=}" ;;
    --mode) MODE="${2:-exclusive-edit}"; shift ;;
    --mode=*) MODE="${1#--mode=}" ;;
    --session-id) SESSION_ID="${2:-}"; shift ;;
    --session-id=*) SESSION_ID="${1#--session-id=}" ;;
    --help|-h) usage; exit 0 ;;
    --) shift; COMMAND=("$@"); break ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

if [ -z "$TARGET" ]; then
  echo "cos-governed-edit: --file is required" >&2
  exit 2
fi
if [ -z "$TASK_ID" ] && [ "${COS_GOVERNED_EDIT_ALLOW_NO_TASK:-0}" != "1" ]; then
  echo "cos-governed-edit: --task-id is required (set COS_GOVERNED_EDIT_ALLOW_NO_TASK=1 only for emergency/manual probes)" >&2
  exit 2
fi

export COGNITIVE_OS_PROJECT_DIR="$PROJECT_DIR"
export CLAUDE_PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PROJECT_DIR}"
export COGNITIVE_OS_SESSION_ID="$SESSION_ID"

release_active_claim() {
  [ -z "$TASK_ID" ] && return 0
  python3 "$SCRIPT_DIR/cos_task_claims.py" --project-dir "$PROJECT_DIR" \
    release --task-id "$TASK_ID" --session-id "$SESSION_ID" >/dev/null 2>&1 || true
}

complete_active_claim() {
  [ -z "$TASK_ID" ] && return 0
  python3 "$SCRIPT_DIR/cos_task_claims.py" --project-dir "$PROJECT_DIR" \
    complete --task-id "$TASK_ID" --session-id "$SESSION_ID" >/dev/null 2>&1 || true
}

if [ -n "$TASK_ID" ]; then
  CLAIM_OUT=$(python3 "$SCRIPT_DIR/cos_task_claims.py" --project-dir "$PROJECT_DIR" \
    claim --task-id "$TASK_ID" --description "$REASON" --expected-file "$TARGET" --session-id "$SESSION_ID" 2>&1)
  CLAIM_RC=$?
  if [ "$CLAIM_RC" -eq 2 ]; then
    echo "ADR-116 ACTIVE TASK CLAIM BLOCK: task '$TASK_ID' is already claimed." >&2
    echo "$CLAIM_OUT" >&2
    exit 2
  elif [ "$CLAIM_RC" -ne 0 ]; then
    echo "$CLAIM_OUT" >&2
    exit "$CLAIM_RC"
  fi
fi

if [ "${COS_SKIP_GOVERNED_INVENTORY:-0}" != "1" ]; then
  INVENTORY_OUT=$(python3 "$SCRIPT_DIR/cos_work_inventory.py" --project-dir "$PROJECT_DIR" --all --strict --json 2>&1)
  INVENTORY_RC=$?
  if [ "$INVENTORY_RC" -ne 0 ]; then
    echo "ADR-116 GOVERNED PREFLIGHT BLOCK: cos_work_inventory.py --all --strict failed." >&2
    echo "$INVENTORY_OUT" >&2
    release_active_claim
    exit "$INVENTORY_RC"
  fi
fi

ACQUIRE_OUT=$(bash "$SCRIPT_DIR/edit-coop.sh" acquire "$TARGET" "$REASON" "$MODE" 2>&1)
ACQUIRE_RC=$?
if [ "$ACQUIRE_RC" -ne 0 ]; then
  echo "$ACQUIRE_OUT" >&2
  release_active_claim
  exit "$ACQUIRE_RC"
fi

release() {
  bash "$SCRIPT_DIR/edit-coop.sh" release "$TARGET" >/dev/null 2>&1 || true
  if [ "${COMMAND_RC:-0}" -eq 0 ]; then
    complete_active_claim
  else
    release_active_claim
  fi
}
trap release EXIT

if [ "${#COMMAND[@]}" -eq 0 ]; then
  echo "$ACQUIRE_OUT"
  echo "cos-governed-edit: lock acquired; no command supplied, releasing immediately." >&2
  exit 0
fi

"${COMMAND[@]}"
COMMAND_RC=$?
exit "$COMMAND_RC"
