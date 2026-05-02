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
COMMAND=()

usage() {
  cat <<'EOF'
Usage:
  scripts/cos-governed-edit.sh --file path [--reason text] -- command...

Acquires the Cognitive OS edit lock before running a command and releases it on
exit. Use this from Codex or other harnesses without Edit/Write hook parity.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --file) TARGET="${2:-}"; shift ;;
    --file=*) TARGET="${1#--file=}" ;;
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

export COGNITIVE_OS_PROJECT_DIR="$PROJECT_DIR"
export CLAUDE_PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PROJECT_DIR}"
export COGNITIVE_OS_SESSION_ID="$SESSION_ID"

ACQUIRE_OUT=$(bash "$SCRIPT_DIR/edit-coop.sh" acquire "$TARGET" "$REASON" "$MODE" 2>&1)
ACQUIRE_RC=$?
if [ "$ACQUIRE_RC" -ne 0 ]; then
  echo "$ACQUIRE_OUT" >&2
  exit "$ACQUIRE_RC"
fi

release() {
  bash "$SCRIPT_DIR/edit-coop.sh" release "$TARGET" >/dev/null 2>&1 || true
}
trap release EXIT

if [ "${#COMMAND[@]}" -eq 0 ]; then
  echo "$ACQUIRE_OUT"
  echo "cos-governed-edit: lock acquired; no command supplied, releasing immediately." >&2
  exit 0
fi

"${COMMAND[@]}"
