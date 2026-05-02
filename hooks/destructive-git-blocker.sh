#!/usr/bin/env bash
# SCOPE: both
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
#   - git reset (any form; mutates HEAD/index/worktree state)
#   - git checkout -- <anything>  (incl. `checkout HEAD -- <path>` form)
#   - git clean -f[dx]
#   - git restore (any form)
#   - git revert (any form)
#   - git worktree (any subcommand)
#   - git branch -D (force-delete)
#   - git rebase (any form; mutates history/worktree state)
#   - git pull --rebase (shared-worktree rebase/reset hazard)
#   - git commit / git push from protected main/master branches
#   - git push --force / git push -f  (force-push, 2026-05-02 extension)
#     NOTE: --force-with-lease is intentionally NOT blocked (safer alternative)
#
# Allowed always:
#   - git status, git diff, git log, git show, git blame, git rev-parse, …
#   - git push --force-with-lease (safer force push)
#   - any non-git bash command
#   - patterns appearing only inside `git commit -m "..."` message bodies
#     (false-positive fix: commit messages may document destructive ops without
#      the hook treating them as if the ops themselves were executed)
#
# Override mechanisms (ADR-055b):
#   - Per-command: append `--allow-destructive` token anywhere in the command
#   - Per-command: append `--allow-force-push` token (force-push-specific bypass)
#   - Per-session: export COS_ALLOW_DESTRUCTIVE_GIT=1
#   - Protected branch write bypass: export COS_ALLOW_MAIN_BRANCH_WRITE=1
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
DESTRUCTIVE_PATTERN='^[[:space:]]*git[[:space:]]+(stash[[:space:]]+(pop|drop|apply)|reset([[:space:]]|$)|pull([^;&|]*)[[:space:]]+--rebase([[:space:]]|$)|checkout[[:space:]]+(--|[A-Za-z0-9/._~^-]+[[:space:]]+--)|clean[[:space:]]+-f|restore|revert|worktree|branch[[:space:]]+-D|rebase([[:space:]]|$))'

# Force-push pattern (2026-05-02): matches `git push --force` and `git push -f` (with word
# boundary after -f to avoid matching -fast-forward or similar flags).
# INTENTIONALLY does NOT match --force-with-lease (safer alternative, allowed per ADR-055b).
FORCE_PUSH_PATTERN='^[[:space:]]*git[[:space:]]+push([[:space:]]+[^[:space:]]+)*[[:space:]]+(--force\b|-f\b)'

# ── Commit-message stripping (false-positive fix 2026-05-02) ─────────────────
# When a command is `git commit ... -m "..." ...` the quoted message body may
# reference destructive ops (e.g. "feat: documents git stash pop behavior").
# Stripping the -m argument before pattern-matching prevents false positives.
# Handles: -m "text", -m 'text', --message="text", --message 'text'.
# Strips all such argument values from the raw COMMAND before scanning.
_strip_commit_message_args() {
  local cmd="$1"
  # Only strip when the command looks like a git commit invocation
  if ! echo "$cmd" | grep -Eq '^[[:space:]]*git[[:space:]]+commit[[:space:]]'; then
    echo "$cmd"
    return
  fi
  # Strip -m "quoted" or -m 'quoted' (non-greedy: stops at first matching quote)
  # Also handles --message= variants
  # Use sed with basic extended regex; loop to strip multiple -m args
  local stripped="$cmd"
  # Remove -m "..." (double-quoted)
  stripped=$(echo "$stripped" | sed 's/-m[[:space:]]*"[^"]*"//g')
  # Remove -m '...' (single-quoted)
  stripped=$(echo "$stripped" | sed "s/-m[[:space:]]*'[^']*'//g")
  # Remove --message="..." (double-quoted)
  stripped=$(echo "$stripped" | sed 's/--message=[[:space:]]*"[^"]*"//g')
  # Remove --message='...' (single-quoted)
  stripped=$(echo "$stripped" | sed "s/--message=[[:space:]]*'[^']*'//g")
  echo "$stripped"
}

# Apply commit-message stripping before pattern scanning
COMMAND_SCAN=$(_strip_commit_message_args "$COMMAND")

# Test first line (commands may be multiline or pipelined — we inspect each sub-command
# crudely by splitting on shell separators).
FIRST_HIT=""
FIRST_HIT_TYPE=""
PROTECTED_BRANCH_HIT=""
PROTECTED_BRANCH=""
# Turn && || ; and pipe | into newlines, then test each segment
while IFS= read -r segment; do
  [ -z "$segment" ] && continue
  # strip leading whitespace
  trimmed="${segment#"${segment%%[![:space:]]*}"}"
  if echo "$trimmed" | grep -Eq "$DESTRUCTIVE_PATTERN"; then
    FIRST_HIT="$trimmed"
    FIRST_HIT_TYPE="destructive"
    break
  fi
  if echo "$trimmed" | grep -Eq '^[[:space:]]*git[[:space:]]+(commit|push)([[:space:]]|$)'; then
    current_branch=$(git -C "$PROJECT_DIR" branch --show-current 2>/dev/null || true)
    if echo "$current_branch" | grep -Eq '^(main|master)$'; then
      FIRST_HIT="$trimmed"
      FIRST_HIT_TYPE="protected_branch_write"
      PROTECTED_BRANCH_HIT="$trimmed"
      PROTECTED_BRANCH="$current_branch"
      break
    fi
  fi
  # Check force-push pattern; exclude --force-with-lease explicitly
  if echo "$trimmed" | grep -Eq "$FORCE_PUSH_PATTERN"; then
    if ! echo "$trimmed" | grep -q -- '--force-with-lease'; then
      FIRST_HIT="$trimmed"
      FIRST_HIT_TYPE="force_push"
      break
    fi
  fi
done <<< "$(echo "$COMMAND_SCAN" | tr '|&;' '\n')"

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
if [ "$FIRST_HIT_TYPE" = "force_push" ]; then
  OP_NAME="git push --force"
elif [ "$FIRST_HIT_TYPE" = "protected_branch_write" ]; then
  OP_NAME="git ${PROTECTED_BRANCH_HIT#git } on ${PROTECTED_BRANCH}"
else
  OP_NAME=$(echo "$FIRST_HIT" | awk '{
    if ($2=="stash") print "git stash " $3;
    else if ($2=="reset") print "git reset";
    else if ($2=="pull") print "git pull --rebase";
    else if ($2=="checkout") print "git checkout --";
    else if ($2=="clean") print "git clean -f";
    else if ($2=="branch") print "git branch -D";
    else if ($2=="rebase") print "git rebase";
    else print "git " $2;
  }')
fi

# One-line rationale per op (for override error message)
_op_rationale() {
  case "$1" in
    "git stash pop"|"git stash drop"|"git stash apply")
      echo "stash ops can re-enact prior state from user-context or pop the wrong entry (ADR-055b, r5)";;
    "git reset")
      echo "mutates HEAD/index/worktree state and can erase another session's staged or uncommitted work";;
    "git pull --rebase")
      echo "rebases the current worktree and can reset/overwrite another agent's in-flight edits; use scripts/cos-git-sync.sh or a session branch";;
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
    "git rebase")
      echo "rewrites local history and mutates the worktree; use an isolated session branch/worktree and explicit approval";;
    "git push --force")
      echo "force-push rewrites remote history; can permanently destroy commits other collaborators depend on; use --force-with-lease for a safer alternative";;
    *" on main"|*" on master")
      echo "committing or pushing directly from a protected shared branch bypasses per-session isolation; create a session branch first with scripts/cos-session-branch.sh";;
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

# Per-command override for force-push specifically: `--allow-force-push`
_has_allow_force_push_flag() {
  echo "$COMMAND" | grep -Eq '(^|[[:space:]])--allow-force-push($|[[:space:]])'
}

_has_allow_main_branch_flag() {
  echo "$COMMAND" | grep -Eq '(^|[[:space:]])--allow-main-branch($|[[:space:]])'
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

_has_main_branch_override() {
  [ "${COS_ALLOW_MAIN_BRANCH_WRITE:-}" = "1" ] && return 0
  _has_allow_main_branch_flag && return 0
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
if _has_session_override || _has_allow_flag || _has_allow_force_push_flag || { [ "$FIRST_HIT_TYPE" = "protected_branch_write" ] && _has_main_branch_override; }; then
  override_reason="session_env"
  _has_allow_flag && override_reason="inline_flag"
  _has_allow_force_push_flag && override_reason="inline_flag_force_push"
  if [ "$FIRST_HIT_TYPE" = "protected_branch_write" ] && _has_main_branch_override; then
    override_reason="main_branch_override"
  fi
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
if [ "$FIRST_HIT_TYPE" = "force_push" ]; then
  echo "     OR:           append --allow-force-push (force-push-specific bypass)" >&2
  echo "     SAFER:        use --force-with-lease instead of --force / -f" >&2
fi
if [ "$FIRST_HIT_TYPE" = "protected_branch_write" ]; then
  echo "     OR:           append --allow-main-branch, or export COS_ALLOW_MAIN_BRANCH_WRITE=1" >&2
  echo "     SAFER:        bash scripts/cos-session-branch.sh --slug <task> --switch" >&2
fi
echo "  2. Session env:   export COS_ALLOW_DESTRUCTIVE_GIT=1 (this shell only)" >&2
echo "" >&2
echo "Reference: docs/adrs/ADR-055b-destructive-git-block.md" >&2
echo "" >&2

ENTRY=$(printf '{"timestamp":"%s","event":"blocked","context":"user","agent_id":"","op":"%s","command":"%s"}' \
  "$TIMESTAMP" "$esc_op" "$esc_cmd")
safe_jsonl_append "$BLOCKS_LOG" "$ENTRY" 2>/dev/null || true

exit 2
