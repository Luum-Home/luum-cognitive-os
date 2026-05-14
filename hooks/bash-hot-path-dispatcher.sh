#!/usr/bin/env bash
# SCOPE: os-only
# bash-hot-path-dispatcher.sh — default PreToolUse:Bash tier dispatcher.
#
# Keeps the interactive Bash hot path small without dropping governed agentic
# primitives. It runs P0/P1 Bash gates only when the command shape needs them:
# destructive shell, git boundaries, release paths, dependency mutations, and
# commit-time governance. Full profile still projects the exhaustive hook mesh.
#
# Exit: 0 allow, non-zero/2 propagates the first blocking child gate.

set -uo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$HOOK_DIR/.." && pwd)"
INPUT="$(cat 2>/dev/null || true)"

_extract_command() {
  if command -v python3 >/dev/null 2>&1; then
    HOOK_INPUT_JSON="$INPUT" python3 - <<'PY' 2>/dev/null || true
import json, os
try:
    data = json.loads(os.environ.get("HOOK_INPUT_JSON", "") or "{}")
except Exception:
    data = {}
if data.get("tool_name") and data.get("tool_name") != "Bash":
    print("")
else:
    tool_input = data.get("tool_input") or {}
    print(str(tool_input.get("command") or data.get("command") or ""))
PY
  fi
}

COMMAND="$(_extract_command)"
[ -n "$COMMAND" ] || exit 0

_run_gate() {
  local script="$1"
  local path="$PROJECT_DIR/$script"
  [ -x "$path" ] || [ -f "$path" ] || return 0

  local out err rc
  out="$(mktemp "${TMPDIR:-/tmp}/cos-bash-dispatch-out.XXXXXX")"
  err="$(mktemp "${TMPDIR:-/tmp}/cos-bash-dispatch-err.XXXXXX")"
  printf '%s' "$INPUT" | bash "$path" >"$out" 2>"$err"
  rc=$?
  if [ "$rc" -ne 0 ]; then
    [ -s "$out" ] && cat "$out"
    [ -s "$err" ] && cat "$err" >&2
    rm -f "$out" "$err" 2>/dev/null || true
    return "$rc"
  fi
  # Suppress allow-path hookSpecificOutput from child gates: the dispatcher may
  # run multiple gates and concatenating JSON hook outputs would break the
  # PreToolUse protocol. Blocking gates still surface their output above.
  rm -f "$out" "$err" 2>/dev/null || true
  return 0
}

_run_many() {
  local gate
  for gate in "$@"; do
    _run_gate "$gate" || return $?
  done
}

_matches() {
  printf '%s
' "$COMMAND" | grep -Eq "$1"
}

_is_git_boundary() {
  _matches '(^|[[:space:];|&()])git[[:space:]]+(add|commit|push|pull|checkout|switch|merge|rebase|reset|tag|stash|worktree|branch|restore|rm|mv)($|[[:space:];|&()])'
}

_is_git_commit() {
  _matches '(^|[[:space:];|&()])git[[:space:]]+commit($|[[:space:];|&()])'
}

_is_release_boundary() {
  _matches '(^|[[:space:];|&()])git[[:space:]]+tag($|[[:space:];|&()])' || \
  _matches '(^|[[:space:];|&()])(echo|printf|sed|perl)[^;&|]*[>[:space:]]VERSION($|[[:space:];|&()])'
}

_is_fs_mutation() {
  _matches '(^|[[:space:];|&()])(rm|rmdir|mv|ln)[[:space:]]' || \
  _matches '(^|[[:space:];|&()])find[[:space:]].*(-delete|xargs[[:space:]]+rm)'
}

_is_network_boundary() {
  _matches '(^|[[:space:];|&()])(curl|wget|nc|ncat|ssh|scp|rsync)[[:space:]]' || \
  _matches '(^|[[:space:];|&()])git[[:space:]]+(clone|fetch|pull|push)[[:space:]]'
}

_is_dependency_mutation() {
  _matches '(^|[[:space:];|&()])(npm|pnpm|yarn|pip|pip3|uv|poetry|cargo|go)[[:space:]]+(install|add|remove|update|get|mod|sync)($|[[:space:];|&()])' || \
  _matches '(^|[[:space:];|&()])brew[[:space:]]+(install|upgrade|uninstall)($|[[:space:];|&()])'
}

# P0: destructive/external boundaries on the default synchronous path.
if _is_network_boundary; then
  _run_gate "hooks/network-egress-guard.sh" || exit $?
fi

if _is_fs_mutation; then
  _run_many \
    "hooks/destructive-rm-blocker.sh" \
    "hooks/symlink-mutation-guard.sh" || exit $?
fi

if _is_git_boundary; then
  _run_many \
    "hooks/destructive-git-blocker.sh" \
    "hooks/untracked-work-preservation-guard.sh" \
    "hooks/direct-main-guard.sh" \
    "hooks/branch-ownership-lock.sh" \
    "hooks/cross-session-coordination-guard.sh" \
    "hooks/agent-message-inbox-guard.sh" || exit $?
fi

# P1: state-scoped governance gates. This does not depend on command shape:
# a high-confidence skill-router suggestion applies to the next Bash tool call
# even when the command itself is innocuous. Keeping it behind the dispatcher
# preserves the default one-hook projection while retaining mandatory skill
# invocation enforcement in Codex/Claude Bash hot paths.
_run_gate "hooks/orchestrator-skill-invocation-gate.sh" || exit $?

# P1: command-scoped governance gates.

if _is_git_commit; then
  _run_many \
    "hooks/git-commit-scope-guard.sh" \
    "hooks/orchestrator-claim-gate.sh" \
    "hooks/pre-commit-content-hash-dedupe.sh" \
    "hooks/scope-marker-portability-gate.sh" \
    "hooks/external-pattern-cleanroom-gate.sh" \
    "hooks/adoption-freeze-gate.sh" \
    "hooks/dependency-license-classifier.sh" \
    "hooks/research-to-runtime-firewall.sh" \
    "hooks/spdx-header-required.sh" \
    "hooks/external-cache-content-leak.sh" \
    "hooks/attribution-completeness-validator.sh" \
    "hooks/lib-symlink-divergence-detector.sh" \
    "hooks/legal-review-required-on-runtime-import.sh" \
    "hooks/pending-truth-staleness-gate.sh" || exit $?
fi

if _is_release_boundary; then
  _run_gate "hooks/release-guard.sh" || exit $?
fi

if _is_dependency_mutation; then
  _run_gate "hooks/skill-router-bash-gate.sh" || exit $?
fi

exit 0
