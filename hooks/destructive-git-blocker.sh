#!/usr/bin/env bash
# SCOPE: project
# CONCERNS: safety, git-ops, adr-003-mechanism-c
# Destructive Git Op Blocker — PreToolUse Bash
#
# Intercepts bash commands about to run and blocks the destructive-git-op
# subset by default in BOTH agent and user contexts. Per ADR-055b (decision #6,
# r5-stash-residue closure), the previous warn-only behavior in user context
# was insufficient — stash-residue and other destructive ops in interactive
# orchestration caused the incident class documented in
# docs/reports/bug2-reset-cascade-forensics-2026-04-20.md §5.
#
# Blocked by default (exit 2):
#   - git stash pop | stash drop | stash apply
#   - git reset --hard
#   - git checkout -- <anything>  (incl. `checkout HEAD -- <path>` form)
#   - git clean -f[dx]
#   - git restore (any form)
#   - git revert (any form)
#   - git worktree (any subcommand)
#   - git branch -D (force-delete)
#   - git rebase --abort (state loss)
#
# Allowed always:
#   - git status, git diff, git log, git show, git blame, git rev-parse, …
#   - any non-git bash command
#
# Override mechanisms (ADR-055b):
#   - Per-command: append `--allow-destructive` token anywhere in the command
#   - Per-session: export COS_ALLOW_DESTRUCTIVE_GIT=1
#
# Bypass contexts (SO-internal — block does not apply):
#   - CI=1 (CI environment)
#   - PYTEST_CURRENT_TEST set (running under pytest)
#   - COS_GIT_BYPASS=1 (reaper, watchdog, sandbox operations)
#
# Agent context (CLAUDE_AGENT_ID set) retains exit 1 for backwards-compat with
# existing tests; user context uses exit 2 per ADR convention.
#
# Logs every block to:
#   .cognitive-os/metrics/git-op-blocks.jsonl
#
# Reference: ADR-003 Mechanism C, ADR-055b (block elevation).

set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="destructive-git-blocker"
source "$(dirname "$0")/_lib/safe-jsonl.sh"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${COGNITIVE_OS_PROJECT_DIR:-$(pwd)}}"
BLOCKS_LOG="$PROJECT_DIR/.cognitive-os/metrics/git-op-blocks.jsonl"

# Read stdin (best-effort)
INPUT=""
if [ ! -t 0 ]; then
  INPUT=$(cat 2>/dev/null || true)
fi

# Gate to Bash tool — other tools must not be blocked
TOOL_NAME=""
if [ -n "$INPUT" ] && command -v jq >/dev/null 2>&1; then
  TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || true)
  if [ -n "$TOOL_NAME" ] && [ "$TOOL_NAME" != "Bash" ]; then
    exit 0
  fi
fi

# Extract the command — jq preferred, regex fallback. CLAUDE_TOOL_INPUT may
# carry the command directly (used by tests / some harness plugins).
COMMAND=""
if [ -n "${CLAUDE_TOOL_INPUT:-}" ]; then
  COMMAND="$CLAUDE_TOOL_INPUT"
elif [ -n "$INPUT" ] && command -v jq >/dev/null 2>&1; then
  COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null || true)
fi

# No command, nothing to do
if [ -z "$COMMAND" ]; then
  exit 0
fi

# Pattern — note: extended regex, dollar-less because we match anywhere after the git invocation.
# ADR-003 R1 fix (2026-04-20 forensic): the original regex `checkout[[:space:]]+--` matched
# `git checkout -- foo` but NOT `git checkout HEAD -- foo` (the exact form that triggered the
# Sprint-2a incident per ADR-003 §Context line 10). The checkout alternative now matches both
# direct (`checkout -- <path>`) and via-ref (`checkout <ref> -- <path>`, e.g. HEAD, HEAD~1,
# <sha>, <branch>, <tag>) forms. `<ref>` may contain letters, digits, slash, dot, underscore,
# tilde, caret, hyphen.
DESTRUCTIVE_PATTERN='^[[:space:]]*git[[:space:]]+(stash[[:space:]]+(pop|drop|apply)|reset[[:space:]]+--hard|checkout[[:space:]]+(--|[A-Za-z0-9/._~^-]+[[:space:]]+--)|clean[[:space:]]+-f|restore|revert|worktree|branch[[:space:]]+-D|rebase[[:space:]]+--abort)'

# Test first line (commands may be multiline or pipelined — we inspect each sub-command
# crudely by splitting on shell separators).
FIRST_HIT=""
# Turn && || ; and pipe | into newlines, then test each segment
while IFS= read -r segment; do
  [ -z "$segment" ] && continue
  # strip leading whitespace
  trimmed="${segment#"${segment%%[![:space:]]*}"}"
  if echo "$trimmed" | grep -Eq "$DESTRUCTIVE_PATTERN"; then
    FIRST_HIT="$trimmed"
    break
  fi
done <<< "$(echo "$COMMAND" | tr '|&;' '\n')"

# No match → allow silently
if [ -z "$FIRST_HIT" ]; then
  exit 0
fi

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
AGENT_ID="${CLAUDE_AGENT_ID:-}"

# ── Agent-context detection (R4 hardening) ───────────────────────────────────
# Consider "agent context" if ANY of the following is true:
#   1. CLAUDE_AGENT_ID is non-empty
#   2. COGNITIVE_OS_SESSION_ID is non-empty
#   3. ORCHESTRATOR_MODE == executor
#   4. Parent process name matches claude or claude-code (best-effort)
_git_blocker_is_agent_context() {
  [ -n "${CLAUDE_AGENT_ID:-}" ]             && return 0
  [ -n "${COGNITIVE_OS_SESSION_ID:-}" ]     && return 0
  [ "${ORCHESTRATOR_MODE:-}" = "executor" ] && return 0
  local ppid_name
  ppid_name=$(ps -p $PPID -o comm= 2>/dev/null || true)
  if echo "$ppid_name" | grep -qiE '^claude(-code)?$'; then
    return 0
  fi
  return 1
}

# Extract the matched op name (stash pop, reset --hard, etc.) for the alert text
OP_NAME=$(echo "$FIRST_HIT" | awk '{
  if ($2=="stash") print "git stash " $3;
  else if ($2=="reset") print "git reset " $3;
  else if ($2=="checkout") print "git checkout --";
  else if ($2=="clean") print "git clean -f";
  else if ($2=="branch") print "git branch -D";
  else if ($2=="rebase") print "git rebase --abort";
  else print "git " $2;
}')

# One-line rationale per op (for override error message)
_op_rationale() {
  case "$1" in
    "git stash pop"|"git stash drop"|"git stash apply")
      echo "stash ops can re-enact prior state from user-context or pop the wrong entry (ADR-055b, r5)";;
    "git reset --hard")
      echo "unconditional working-tree + index discard; no reflog-only recovery for uncommitted work";;
    "git checkout --")
      echo "working-tree discard of specific paths; no recovery if changes were not committed";;
    "git clean -f")
      echo "force-delete untracked files including generated state and WIP";;
    "git restore")
      echo "discards working-tree changes (modern equivalent of `checkout --`)";;
    "git revert")
      echo "creates new commits that may conflict unexpectedly with in-flight work";;
    "git worktree")
      echo "worktree mutations can orphan sessions / detach HEAD in ways the OS does not track";;
    "git branch -D")
      echo "force-deletes branches with unmerged commits; recovery requires reflog lookup";;
    "git rebase --abort")
      echo "discards in-progress rebase state; partial work may be lost";;
    *)
      echo "destructive operation; irreversible without reflog recovery";;
  esac
}

# Escape command for JSON
esc_cmd=${COMMAND//\\/\\\\}
esc_cmd=${esc_cmd//\"/\\\"}
esc_cmd=$(echo "$esc_cmd" | head -c 500 | tr '\n\r' '  ')
esc_op=${OP_NAME//\"/\\\"}

# ── Override / bypass detection (ADR-055b) ───────────────────────────────────
# Per-command override: `--allow-destructive` token anywhere in the command
_has_allow_flag() {
  # Match --allow-destructive as a whole token (surrounded by whitespace or edges)
  echo "$COMMAND" | grep -Eq '(^|[[:space:]])--allow-destructive($|[[:space:]])'
}

# SO-internal bypass contexts (not user-initiated destructive ops)
_is_bypass_context() {
  [ "${CI:-}" = "1" ]                      && return 0
  [ "${CI:-}" = "true" ]                   && return 0
  [ -n "${PYTEST_CURRENT_TEST:-}" ]        && return 0
  [ "${COS_GIT_BYPASS:-}" = "1" ]          && return 0
  return 1
}

# Session-wide override
_has_session_override() {
  [ "${COS_ALLOW_DESTRUCTIVE_GIT:-}" = "1" ] && return 0
  return 1
}

# Bypass context — allow silently, log as bypassed.
# NOTE: bypass does NOT apply when an agent context is active. Agents running
# under pytest/CI must still be blocked; otherwise a malicious or buggy sub-agent
# could exploit the test harness env to destroy state.
if _is_bypass_context && ! _git_blocker_is_agent_context; then
  ENTRY=$(printf '{"timestamp":"%s","event":"bypassed","reason":"so_internal_context","op":"%s","command":"%s"}' \
    "$TIMESTAMP" "$esc_op" "$esc_cmd")
  safe_jsonl_append "$BLOCKS_LOG" "$ENTRY" 2>/dev/null || true
  exit 0
fi

# Explicit override — allow with audit log
if _has_session_override || _has_allow_flag; then
  override_reason="session_env"
  _has_allow_flag && override_reason="inline_flag"
  echo "" >&2
  echo "=== DESTRUCTIVE-GIT-BLOCKER: OVERRIDE ACCEPTED ===" >&2
  echo "Destructive op '$OP_NAME' allowed via $override_reason override." >&2
  echo "Command: $COMMAND" >&2
  echo "" >&2
  ENTRY=$(printf '{"timestamp":"%s","event":"override","reason":"%s","agent_id":"%s","op":"%s","command":"%s"}' \
    "$TIMESTAMP" "$override_reason" "$AGENT_ID" "$esc_op" "$esc_cmd")
  safe_jsonl_append "$BLOCKS_LOG" "$ENTRY" 2>/dev/null || true
  exit 0
fi

# No override + no bypass → BLOCK (both agent and user context)
RATIONALE=$(_op_rationale "$OP_NAME")

if _git_blocker_is_agent_context; then
  # Agent context → BLOCK exit 1 (backward compat with existing tests)
  echo "" >&2
  echo "=== DESTRUCTIVE-GIT-BLOCKER: BLOCKED (agent context) ===" >&2
  echo "BLOCKED: destructive git op '$OP_NAME' requires explicit user approval." >&2
  echo "Rationale: $RATIONALE" >&2
  echo "Use Edit tool to revert specific lines manually, or escalate to the user." >&2
  echo "Agent: $AGENT_ID" >&2
  echo "Command: $COMMAND" >&2
  echo "Override: set COS_ALLOW_DESTRUCTIVE_GIT=1 or append --allow-destructive to the command." >&2
  echo "Reference: ADR-003, ADR-055b (hooks/destructive-git-blocker.sh)" >&2
  echo "" >&2

  ENTRY=$(printf '{"timestamp":"%s","event":"blocked","context":"agent","agent_id":"%s","op":"%s","command":"%s"}' \
    "$TIMESTAMP" "$AGENT_ID" "$esc_op" "$esc_cmd")
  safe_jsonl_append "$BLOCKS_LOG" "$ENTRY" 2>/dev/null || true

  exit 1
fi

# User context → BLOCK exit 2 (ADR-055b — elevation from warn-only)
echo "" >&2
echo "=== DESTRUCTIVE-GIT-BLOCKER: BLOCKED (user context) ===" >&2
echo "BLOCKED: destructive git op '$OP_NAME' is blocked by default (ADR-055b, r5-stash-residue)." >&2
echo "Rationale: $RATIONALE" >&2
echo "Command: $COMMAND" >&2
echo "" >&2
echo "To proceed, use ONE of:" >&2
echo "  1. Inline flag:   append --allow-destructive to the command" >&2
echo "                    (e.g. 'git reset --hard HEAD~1 --allow-destructive')" >&2
echo "  2. Session env:   export COS_ALLOW_DESTRUCTIVE_GIT=1 (this shell only)" >&2
echo "" >&2
echo "Reference: docs/adrs/ADR-055b-destructive-git-block.md" >&2
echo "" >&2

ENTRY=$(printf '{"timestamp":"%s","event":"blocked","context":"user","agent_id":"","op":"%s","command":"%s"}' \
  "$TIMESTAMP" "$esc_op" "$esc_cmd")
safe_jsonl_append "$BLOCKS_LOG" "$ENTRY" 2>/dev/null || true

exit 2
