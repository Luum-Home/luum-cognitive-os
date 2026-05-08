#!/usr/bin/env bash
# SCOPE: both
# direct-main-guard.sh — ADR-116 P2.1/P2.2 local branch-isolation policy.
# Local policy: agents block on main/master commits; direct main pushes block
# unless they are executed by the governed merge queue or explicit emergency env.
set -uo pipefail
[ -f "$(dirname "$0")/_lib/bypass-resolver.sh" ] && source "$(dirname "$0")/_lib/bypass-resolver.sh"
PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
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

_semantic_git_action() {
  command -v python3 >/dev/null || return 1
  python3 - "$1" <<'PY'
from __future__ import annotations

import shlex
import sys
from pathlib import Path

try:
    parts = shlex.split(sys.argv[1])
except ValueError:
    sys.exit(1)

try:
    git_idx = next(i for i, token in enumerate(parts) if token == "git" or Path(token).name == "git")
except StopIteration:
    sys.exit(1)

i = git_idx + 1
while i < len(parts):
    token = parts[i]
    if token in {"-C", "--git-dir", "--work-tree", "-c"}:
        i += 2
        continue
    if token.startswith("--git-dir=") or token.startswith("--work-tree="):
        i += 1
        continue
    sub = token
    args = parts[i + 1 :]
    break
else:
    sys.exit(1)

if sub == "commit":
    print("commit\tunknown")
    sys.exit(0)
if sub != "push":
    sys.exit(1)

protected_refs = {"main", "master", "refs/heads/main", "refs/heads/master"}
delete_mode = False
refspecs: list[str] = []
i = 0
while i < len(args):
    token = args[i]
    if token in {"--delete", "-d"}:
        delete_mode = True
        i += 1
        continue
    if token in {"-u", "--set-upstream", "--repo", "--receive-pack", "--exec"}:
        i += 2
        continue
    if token.startswith("-"):
        i += 1
        continue
    refspecs.append(token)
    i += 1

# First non-option is usually remote. Remaining tokens are refspecs.
push_specs = refspecs[1:] if refspecs else []
if delete_mode:
    pushes_protected = any(spec in protected_refs for spec in push_specs)
elif push_specs:
    pushes_protected = any(
        spec in protected_refs or spec.split(":", 1)[-1] in protected_refs
        for spec in push_specs
    )
else:
    # No explicit refspec: pushing current branch.
    pushes_protected = True

print(f"push\t{'protected' if pushes_protected else 'non_protected'}")
PY
}

if ! ACTION_INFO=$(_semantic_git_action "$COMMAND"); then
  ACTION_INFO=""
fi
if [ -z "$ACTION_INFO" ]; then
  exit 0
fi
ACTION=$(printf '%s' "$ACTION_INFO" | awk -F '\t' '{print $1}')
PUSH_TARGET_SCOPE=$(printf '%s' "$ACTION_INFO" | awk -F '\t' '{print $2}')
if ! git -C "$PROJECT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then exit 0; fi
BRANCH=$(git -C "$PROJECT_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")

_actor() {
  local actor="${COS_ACTOR:-${COGNITIVE_OS_ACTOR:-}}"
  if [ -z "$actor" ]; then
    if [ -n "${CLAUDE_AGENT_ID:-}" ] || [ -n "${CODEX_AGENT_ID:-}" ] || [ -n "${COGNITIVE_OS_AGENT_ID:-}" ] || [ -n "${COS_AGENT_ID:-}" ] || [ "${COGNITIVE_OS_KIND:-}" = "subagent" ] || [ "${COS_SESSION_KIND:-}" = "subagent" ]; then
      actor="agent"
    else
      actor="operator"
    fi
  fi
  printf '%s' "$actor"
}

_audit_direct_main_bypass() {
  local action="$1"
  local branch="$2"
  local reason="$3"
  local actor="$4"
  local metrics_file="$PROJECT_DIR/.cognitive-os/metrics/direct-main-bypass.jsonl"
  local entry
  entry=$(python3 - "$action" "$branch" "$reason" "$actor" "$COMMAND" <<'PY'
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

action, branch, reason, actor, command = sys.argv[1:6]
print(json.dumps({
    "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "hook": "direct-main-guard",
    "event": "direct_main_bypass",
    "action": action,
    "branch": branch,
    "actor": actor,
    "reason": reason,
    "command": command,
}, sort_keys=True))
PY
)
  if ! safe_jsonl_append "$metrics_file" "$entry"; then
    echo "[direct-main-guard] WARN: failed to write direct-main bypass audit." >&2
  fi
}

_require_bypass_reason() {
  local action="$1"
  local reason="${COS_DIRECT_MAIN_BYPASS_REASON:-${COS_BYPASS_REASON:-}}"
  if [ -z "$reason" ]; then
    echo "[direct-main-guard] BLOCK: $action bypass requires COS_DIRECT_MAIN_BYPASS_REASON or COS_BYPASS_REASON." >&2
    echo "Bypass must be one-off, scoped, and auditable; use the merge queue unless this is an emergency." >&2
    return 2
  fi
  printf '%s' "$reason"
}

_emit_vcs_receipt() {
  local event_type="$1"
  local trust="$2"
  local governed_path="$3"
  local outcome="$4"
  local receipt_script="$PROJECT_DIR/scripts/cos-action-receipt"
  [ -x "$receipt_script" ] || return 0
  command -v python3 >/dev/null 2>&1 || return 0
  local head_sha evidence_json
  head_sha="$(git -C "$PROJECT_DIR" rev-parse HEAD 2>/dev/null || true)"
  evidence_json=$(
    COS_RECEIPT_COMMAND="$COMMAND" \
    COS_RECEIPT_ACTION="$ACTION" \
    COS_RECEIPT_OUTCOME="$outcome" \
    python3 - <<'PY' 2>/dev/null || true
import json
import os
print(json.dumps({
    "hook": "direct-main-guard",
    "git_action": os.environ.get("COS_RECEIPT_ACTION", ""),
    "outcome": os.environ.get("COS_RECEIPT_OUTCOME", ""),
    "command": os.environ.get("COS_RECEIPT_COMMAND", ""),
}))
PY
  )
  [ -n "$evidence_json" ] || evidence_json='{"hook":"direct-main-guard"}'
  local args
  args=("$receipt_script" emit "$event_type" \
    --provider shell-git-hook \
    --source git-hook \
    --trust "$trust" \
    --project-dir "$PROJECT_DIR" \
    --branch "$BRANCH" \
    --governed-path "$governed_path" \
    --evidence-json "$evidence_json" \
    --append)
  [ -n "$head_sha" ] && args+=(--commit-sha "$head_sha")
  "${args[@]}" >/dev/null 2>&1 || true
}

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
elif [ "$ACTION" = "push" ] && [ "$PUSH_TARGET_SCOPE" = "non_protected" ]; then
  exit 0
fi
case "$BRANCH" in main|master) ;; *) exit 0 ;; esac
actor="$(_actor)"
if [ "$ACTION" = "push" ]; then
  if type cos_bypass_allows >/dev/null 2>&1 && cos_bypass_allows direct_push; then
    if ! reason="$(_require_bypass_reason direct-push)"; then exit 2; fi
    _audit_direct_main_bypass "push" "$BRANCH" "$reason" "$actor"
    _emit_vcs_receipt "vcs.bypass" "verified" "direct-main-guard" "direct-push-bypass"
    exit 0
  fi
  [ "${COS_MERGE_QUEUE_WORKER:-0}" = "1" ] && exit 0
  [ "${COS_MERGE_TO_MAIN:-0}" = "1" ] && exit 0
  echo "[direct-main-guard] BLOCK: direct push from $BRANCH bypasses ADR-116 merge queue." >&2
  echo "Land through scripts/cos-merge-queue.sh + scripts/cos-merge-queue-worker.sh or scripts/merge-to-main.sh." >&2
  echo "Emergency operator bypass requires BOTH:" >&2
  echo "  COS_ALLOW_DIRECT_PUSH=1" >&2
  echo "  COS_DIRECT_MAIN_BYPASS_REASON='<short audit reason>'" >&2
  _emit_vcs_receipt "vcs.push.blocked" "verified" "direct-main-guard" "direct-push-blocked"
  exit 2
fi
if type cos_bypass_allows >/dev/null 2>&1 && cos_bypass_allows direct_main; then
  if ! reason="$(_require_bypass_reason direct-commit)"; then exit 2; fi
  _audit_direct_main_bypass "commit" "$BRANCH" "$reason" "$actor"
  _emit_vcs_receipt "vcs.bypass" "verified" "direct-main-guard" "direct-commit-bypass"
  exit 0
fi
case "$actor" in
  agent|subagent|autonomous|worker)
    echo "[direct-main-guard] BLOCK: autonomous/session agents may not commit directly to $BRANCH." >&2
    echo "Use a session branch and land through the ADR-116 merge queue / protected remote path." >&2
    echo "Bypass requires BOTH COS_ALLOW_DIRECT_MAIN=1 and COS_DIRECT_MAIN_BYPASS_REASON='<short audit reason>' for explicit operator emergencies." >&2
    _emit_vcs_receipt "vcs.commit" "verified" "direct-main-guard" "direct-main-commit-blocked"
    exit 2
    ;;
esac
POLICY="${COS_OPERATOR_MAIN_POLICY:-warn}"
case "$POLICY" in
  allow) exit 0 ;;
  block)
    echo "[direct-main-guard] BLOCK: operator direct commit to $BRANCH is disabled by COS_OPERATOR_MAIN_POLICY=block." >&2
    echo "Use a session branch and merge queue, or set BOTH COS_ALLOW_DIRECT_MAIN=1 and COS_DIRECT_MAIN_BYPASS_REASON='<short audit reason>' for a one-off emergency." >&2
    exit 2
    ;;
  warn|*)
    echo "[direct-main-guard] WARN: direct operator commit to $BRANCH bypasses ADR-116 local session isolation." >&2
    echo "Remote branch protection / merge queue must remain the authoritative guard before this reaches origin." >&2
    echo "Recommended: use a session branch and merge queue for coordinated work." >&2
    exit 0
    ;;
esac
