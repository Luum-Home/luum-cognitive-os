#!/usr/bin/env bash
# SCOPE: both
# orchestrator-claim-gate.sh — Cross-IDE PreToolUse gate for high-stakes closure claims.
#
# Runs on Bash tool invocations in any harness that can project Bash hooks. It
# blocks git commit/push attempts when staged plans or commit messages contain
# ADR-105 high-stakes claims without independent repo evidence.
set -uo pipefail

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"
MODE="${COS_ORCHESTRATOR_CLAIM_GATE_MODE:-block}"
INPUT="$(cat)"
[ -z "$INPUT" ] && exit 0
command -v jq >/dev/null 2>&1 || exit 0

TOOL_NAME="$(printf '%s' "$INPUT" | jq -r '.tool_name // ""' 2>/dev/null)"
[ "$TOOL_NAME" = "Bash" ] || exit 0

COMMAND="$(printf '%s' "$INPUT" | jq -r '.tool_input.command // .tool_input.cmd // ""' 2>/dev/null)"
[ -z "$COMMAND" ] || [ "$COMMAND" = "null" ] && exit 0

if ! printf '%s' "$COMMAND" | grep -Eq '(^|[;&|[:space:]])git([[:space:]]+(-C|--git-dir|--work-tree|-c)(=)?[^[:space:]]*)*[[:space:]]+(commit|push)\b'; then
  exit 0
fi

SCRIPT="$PROJECT_DIR/scripts/orchestrator_claim_gate.py"
[ -f "$SCRIPT" ] || SCRIPT="$(cd "$(dirname "$0")/.." && pwd)/scripts/orchestrator_claim_gate.py"
[ -f "$SCRIPT" ] || exit 0

if printf '%s' "$COMMAND" | grep -Eq '(^|[;&|[:space:]])git([[:space:]]+-[^[:space:]]+)*[[:space:]]+push\b'; then
  GATE_MODE="pre-push"
  # ADR-116 P4.2: subject collision detection before claim-gate claim check
  _COLLISION_LIB="$(cd "$(dirname "$0")" && pwd)/_lib/push-collision-check.sh"
  [ -f "$_COLLISION_LIB" ] && source "$_COLLISION_LIB" && run_push_collision_check "$PROJECT_DIR" || true
else
  GATE_MODE="pre-commit"
fi

OUTPUT="$(python3 "$SCRIPT" --project-dir "$PROJECT_DIR" --mode "$GATE_MODE" --command "$COMMAND" --metrics 2>&1)"
STATUS=$?
if [ "$STATUS" -ne 0 ]; then
  printf '%s\n' "$OUTPUT" >&2
  if [ "$MODE" = "warn" ]; then
    printf 'orchestrator-claim-gate: WARN mode — allowing command despite failed claim evidence.\n' >&2
    exit 0
  fi
  printf 'orchestrator-claim-gate: BLOCK — add independent bilateral evidence or leave the plan open.\n' >&2
  exit 2
fi

exit 0
