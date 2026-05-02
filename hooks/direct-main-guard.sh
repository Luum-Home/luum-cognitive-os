#!/usr/bin/env bash
# SCOPE: both
# direct-main-guard.sh — ADR-116 P2.1/P2.2 local branch-isolation policy.
# Local policy: agents block on main/master commits; direct main pushes block
# unless they are executed by the governed merge queue or explicit emergency env.
set -uo pipefail
PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"
INPUT=""
if [ ! -t 0 ]; then INPUT=$(cat 2>/dev/null || true); fi
TOOL_NAME=""; COMMAND=""
if [ -n "$INPUT" ] && command -v jq >/dev/null 2>&1; then
  TOOL_NAME=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || true)
  [ -n "$TOOL_NAME" ] && [ "$TOOL_NAME" != "Bash" ] && exit 0
  COMMAND=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // .tool_input.cmd // empty' 2>/dev/null || true)
elif [ -n "${CLAUDE_TOOL_INPUT:-}" ]; then
  COMMAND="$CLAUDE_TOOL_INPUT"
fi
[ -z "$COMMAND" ] && COMMAND="${COS_GIT_COMMAND:-${COS_DIRECT_MAIN_GUARD_COMMAND:-}}"
[ -z "$COMMAND" ] && exit 0
if printf '%s' "$COMMAND" | grep -Eq '(^|[;&|[:space:]])git([[:space:]]+(-C|--git-dir|--work-tree|-c)(=)?[^[:space:]]*)*[[:space:]]+commit\b'; then
  ACTION="commit"
elif printf '%s' "$COMMAND" | grep -Eq '(^|[;&|[:space:]])git([[:space:]]+(-C|--git-dir|--work-tree|-c)(=)?[^[:space:]]*)*[[:space:]]+push\b'; then
  ACTION="push"
else
  exit 0
fi
[ "${COS_ALLOW_DIRECT_MAIN:-0}" = "1" ] && exit 0
if ! git -C "$PROJECT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then exit 0; fi
BRANCH=$(git -C "$PROJECT_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
if [ "$ACTION" = "push" ] && [ -n "${COS_PRE_PUSH_REFS:-}" ]; then
  PUSHES_MAIN=false
  while read -r _local_ref _local_sha _remote_ref _remote_sha; do
    case "$_local_ref:$_remote_ref" in
      refs/heads/main:*|*:refs/heads/main|refs/heads/master:*|*:refs/heads/master)
        PUSHES_MAIN=true
        ;;
    esac
  done <<EOF
$COS_PRE_PUSH_REFS
EOF
  [ "$PUSHES_MAIN" = true ] || exit 0
fi
case "$BRANCH" in main|master) ;; *) exit 0 ;; esac
if [ "$ACTION" = "push" ]; then
  [ "${COS_ALLOW_DIRECT_PUSH:-0}" = "1" ] && exit 0
  [ "${COS_MERGE_QUEUE_WORKER:-0}" = "1" ] && exit 0
  [ "${COS_MERGE_TO_MAIN:-0}" = "1" ] && exit 0
  echo "[direct-main-guard] BLOCK: direct push from $BRANCH bypasses ADR-116 merge queue." >&2
  echo "Land through scripts/cos-merge-queue.sh + scripts/cos-merge-queue-worker.sh or scripts/merge-to-main.sh." >&2
  echo "Emergency operator bypass: COS_ALLOW_DIRECT_PUSH=1." >&2
  exit 2
fi
actor="${COS_ACTOR:-${COGNITIVE_OS_ACTOR:-}}"
if [ -z "$actor" ]; then
  if [ -n "${CLAUDE_AGENT_ID:-}" ] || [ -n "${CODEX_AGENT_ID:-}" ] || [ -n "${COGNITIVE_OS_AGENT_ID:-}" ] || [ -n "${COS_AGENT_ID:-}" ] || [ "${COGNITIVE_OS_KIND:-}" = "subagent" ] || [ "${COS_SESSION_KIND:-}" = "subagent" ]; then
    actor="agent"
  else
    actor="operator"
  fi
fi
case "$actor" in
  agent|subagent|autonomous|worker)
    echo "[direct-main-guard] BLOCK: autonomous/session agents may not commit directly to $BRANCH." >&2
    echo "Use a session branch and land through the ADR-116 merge queue / protected remote path." >&2
    echo "Bypass only for explicit operator emergencies: COS_ALLOW_DIRECT_MAIN=1." >&2
    exit 2
    ;;
esac
POLICY="${COS_OPERATOR_MAIN_POLICY:-warn}"
case "$POLICY" in
  allow) exit 0 ;;
  block)
    echo "[direct-main-guard] BLOCK: operator direct commit to $BRANCH is disabled by COS_OPERATOR_MAIN_POLICY=block." >&2
    echo "Use a session branch and merge queue, or set COS_ALLOW_DIRECT_MAIN=1 for a one-off emergency." >&2
    exit 2
    ;;
  warn|*)
    echo "[direct-main-guard] WARN: direct operator commit to $BRANCH bypasses ADR-116 local session isolation." >&2
    echo "Remote branch protection / merge queue must remain the authoritative guard before this reaches origin." >&2
    echo "Recommended: use a session branch and merge queue for coordinated work." >&2
    exit 0
    ;;
esac
