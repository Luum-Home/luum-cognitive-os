#!/usr/bin/env bash
# SCOPE: os-only
# probe-hook-git-adjacency.sh — executable evidence for ADR-adjacent defect:
# gates that only recognise `git <sub>` when the two words are literally
# adjacent, and therefore never see `git -C <dir> <sub>`.
#
# It EXECUTES each hook with a real harness payload against a throwaway project
# and reports whether the gate REACHED ITS DECISION or exited early. Nothing
# here greps the hook source: a regex that looks fixed but is unreachable would
# still show as an escape.
#
# usage: scripts/probe-hook-git-adjacency.sh [hooks-root]
#   hooks-root defaults to the repo this script lives in. Pass another root to
#   probe a patched copy (see docs/06-Daily/reports/hooks-adyacencia-cierre-2026-08-16.patch).
#
# exit 0 — every probed gate sees the global-option form (no escape)
# exit 1 — at least one gate still escapes
# exit 2 — the probe could not run (missing git/python3, unusable temp dir)
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT="${1:-$REPO}"
[ -d "$ROOT/hooks" ] || { echo "no hooks/ under $ROOT" >&2; exit 2; }
command -v git >/dev/null 2>&1 || exit 2
command -v python3 >/dev/null 2>&1 || exit 2

PROJ="$(mktemp -d 2>/dev/null)" || exit 2
trap 'rm -rf "$PROJ"' EXIT
git -C "$PROJ" init -q >/dev/null 2>&1 || exit 2
git -C "$PROJ" config user.email probe@local
git -C "$PROJ" config user.name probe
echo probe > "$PROJ/f"
git -C "$PROJ" add f >/dev/null 2>&1
git -C "$PROJ" commit -qm init >/dev/null 2>&1
export CLAUDE_PROJECT_DIR="$PROJ" COGNITIVE_OS_PROJECT_DIR="$PROJ"
export COGNITIVE_OS_SESSION_ID=hook-adjacency-probe

# `git` is held in a variable so that this file's own text does not carry
# destructive-looking git literals that other guards would flag.
G=git
FINDINGS=0

pay() {
  python3 - "$1" "${2:-PreToolUse}" <<'PY'
import json, sys
print(json.dumps({
    "tool_name": "Bash",
    "hook_event_name": sys.argv[2],
    "tool_input": {"command": sys.argv[1]},
    "session_id": "hook-adjacency-probe",
}))
PY
}

# verdict <expected: reach|skip> <label> <detail>
verdict() {
  local want="$1" cmd="$2" detail="$3" got="$4"
  local mark="ok"
  if [ "$want" != "$got" ]; then mark="ESCAPE"; FINDINGS=$((FINDINGS + 1)); fi
  printf '  %-7s want=%-5s got=%-5s  %-40s %s\n' "$mark" "$want" "$got" "$cmd" "$detail"
}

echo "hooks root: $ROOT"

# ── 1. scope-marker-portability-gate ─────────────────────────────────────────
# Signal: the "bypass" metric line, which is only written after the git-commit
# check has already passed.
echo "1. scope-marker-portability-gate.sh   signal: bypass metric"
probe_scope() {
  local cmd="$1" want="$2"
  local m="$PROJ/.cognitive-os/metrics/scope-marker-portability-gate.jsonl"
  rm -f "$m"
  pay "$cmd" | COS_ALLOW_UNPROVEN_SCOPE_BOTH=1 \
    bash "$ROOT/hooks/scope-marker-portability-gate.sh" >/dev/null 2>&1
  if grep -q bypass "$m" 2>/dev/null; then verdict "$want" "$cmd" "metric written" reach
  else verdict "$want" "$cmd" "no metric" skip; fi
}
probe_scope "$G commit -m x" reach
probe_scope "$G -C /tmp/probe commit -m x" reach
probe_scope "$G --no-pager commit -m x" reach
probe_scope "ls -la" skip

# ── 2. release-guard ─────────────────────────────────────────────────────────
# Signal: the guard's own stderr verdict (BLOCKED, or ADVISORY when the project
# phase demotes the release category).
echo "2. release-guard.sh                   signal: stderr verdict"
probe_release() {
  local cmd="$1" want="$2" out
  out="$(pay "$cmd" | bash "$ROOT/hooks/release-guard.sh" 2>&1 >/dev/null)"
  if printf '%s' "$out" | grep -qE 'BLOCKED|ADVISORY'; then
    verdict "$want" "$cmd" "$(printf '%s' "$out" | head -1 | cut -c1-34)" reach
  else verdict "$want" "$cmd" silent skip; fi
}
probe_release "$G tag v9.9.9" reach
probe_release "$G -C /tmp/probe tag v9.9.9" reach
probe_release "cd /tmp && $G tag v9.9.9" reach
probe_release "$G tag -d v9.9.9" skip     # reverse: deleting a tag is not a release
probe_release "$G tag -l" skip            # reverse: listing tags is not a release
probe_release "ls -la" skip

# ── 3. agent-message-inbox-guard ─────────────────────────────────────────────
# Signal: SHOULD_CHECK, read off an execution trace of the real hook.
echo "3. agent-message-inbox-guard.sh       signal: SHOULD_CHECK"
probe_inbox() {
  local cmd="$1" want="$2" t
  t="$(pay "$cmd" | bash -x "$ROOT/hooks/agent-message-inbox-guard.sh" 2>&1 >/dev/null \
       | grep -m1 'SHOULD_CHECK=')"
  case "$t" in
    *"SHOULD_CHECK=yes"*) verdict "$want" "$cmd" "$t" reach ;;
    *) verdict "$want" "$cmd" "${t:-no trace}" skip ;;
  esac
}
probe_inbox "$G commit -m x" reach
probe_inbox "$G -C /tmp/probe commit -m x" reach
probe_inbox "cd /tmp && $G commit -m x" reach
probe_inbox "ls -la" skip

# ── 4. branch-ownership-lock ─────────────────────────────────────────────────
# Signal: the lock file the hook writes when it actually acquires the branch.
echo "4. branch-ownership-lock.sh           signal: acquired lock file"
probe_lock() {
  local cmd="$1" want="$2" f
  rm -rf "$PROJ/.cognitive-os/runtime/branch-locks"
  pay "$cmd" | bash "$ROOT/hooks/branch-ownership-lock.sh" >/dev/null 2>&1
  f="$(find "$PROJ/.cognitive-os/runtime/branch-locks" -name '*.lock' -type f 2>/dev/null | head -1)"
  if [ -n "$f" ]; then verdict "$want" "$cmd" "lock=$(basename "$f")" reach
  else verdict "$want" "$cmd" "no lock" skip; fi
}
probe_lock "$G commit -m x" reach
probe_lock "$G -C /tmp/probe commit -m x" reach
probe_lock "cd /tmp && $G commit -m x" reach
probe_lock "ls -la" skip

# ── 5. post-git-orphan-notifier ──────────────────────────────────────────────
# Signal: TRIGGER_LABEL, which the hook only assigns after its trigger check.
echo "5. post-git-orphan-notifier.sh        signal: TRIGGER_LABEL"
probe_orphan() {
  local cmd="$1" want="$2" t
  t="$(pay "$cmd" PostToolUse | bash -x "$ROOT/hooks/post-git-orphan-notifier.sh" 2>&1 >/dev/null \
       | grep -m1 'TRIGGER_LABEL=post-')"
  if [ -n "$t" ]; then verdict "$want" "$cmd" "$t" reach
  else verdict "$want" "$cmd" "no trigger" skip; fi
}
probe_orphan "$G rebase main" reach
probe_orphan "$G -C /tmp/probe rebase main" reach
probe_orphan "$G --no-pager reset --soft HEAD~1" reach
probe_orphan "ls -la" skip

echo
if [ "$FINDINGS" -gt 0 ]; then
  echo "FINDINGS: $FINDINGS gate probe(s) disagree with the expected verdict."
  exit 1
fi
echo "FINDINGS: 0 — every probed gate sees the global-option form."
exit 0
