#!/usr/bin/env bash
# SCOPE: project
# CONCERNS: safety, git-ops, adr-003-mechanism-c
# Destructive Git Op Blocker — PreToolUse Bash
#
# Intercepts bash commands about to run and blocks the destructive-git-op
# subset when the call originates from a sub-agent (CLAUDE_AGENT_ID set).
#
# Blocked in agent context (exit 1):
#   - git stash pop | stash drop | stash apply
#   - git reset --hard
#   - git checkout -- <anything>
#   - git clean -f
#   - git restore (any form)
#   - git revert (any form)
#   - git worktree (any subcommand)
#
# Allowed always:
#   - git status, git diff, git log, git show, git blame, git rev-parse, …
#   - any non-git bash command
#
# User/orchestrator context (no CLAUDE_AGENT_ID): warn on stderr, allow.
#
# Logs every block AND every allowed-with-warning to:
#   .cognitive-os/metrics/git-op-blocks.jsonl
#
# Reference: ADR-003 Mechanism C.

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
DESTRUCTIVE_PATTERN='^[[:space:]]*git[[:space:]]+(stash[[:space:]]+(pop|drop|apply)|reset[[:space:]]+--hard|checkout[[:space:]]+(--|[A-Za-z0-9/._~^-]+[[:space:]]+--)|clean[[:space:]]+-f|restore|revert|worktree)'

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

# Extract the matched op name (stash pop, reset --hard, etc.) for the alert text
OP_NAME=$(echo "$FIRST_HIT" | awk '{
  if ($2=="stash") print "git stash " $3;
  else if ($2=="reset") print "git reset " $3;
  else if ($2=="checkout") print "git checkout --";
  else if ($2=="clean") print "git clean -f";
  else print "git " $2;
}')

# Escape command for JSON
esc_cmd=${COMMAND//\\/\\\\}
esc_cmd=${esc_cmd//\"/\\\"}
esc_cmd=$(echo "$esc_cmd" | head -c 500 | tr '\n\r' '  ')
esc_op=${OP_NAME//\"/\\\"}

if [ -n "$AGENT_ID" ]; then
  # Agent context → BLOCK
  echo "" >&2
  echo "=== DESTRUCTIVE-GIT-BLOCKER: BLOCKED ===" >&2
  echo "BLOCKED: destructive git op '$OP_NAME' requires explicit user approval." >&2
  echo "Use Edit tool to revert specific lines manually, or escalate to the user." >&2
  echo "Agent: $AGENT_ID" >&2
  echo "Command: $COMMAND" >&2
  echo "Reference: ADR-003 (hooks/destructive-git-blocker.sh)" >&2
  echo "" >&2

  ENTRY=$(printf '{"timestamp":"%s","event":"blocked","agent_id":"%s","op":"%s","command":"%s"}' \
    "$TIMESTAMP" "$AGENT_ID" "$esc_op" "$esc_cmd")
  safe_jsonl_append "$BLOCKS_LOG" "$ENTRY" 2>/dev/null || true

  exit 1
fi

# Orchestrator / user context → WARN but allow
echo "" >&2
echo "=== DESTRUCTIVE-GIT-BLOCKER: WARN ===" >&2
echo "Destructive git op detected ('$OP_NAME'). Allowed because no agent context is active." >&2
echo "Command: $COMMAND" >&2
echo "" >&2

ENTRY=$(printf '{"timestamp":"%s","event":"warned","agent_id":"","op":"%s","command":"%s"}' \
  "$TIMESTAMP" "$esc_op" "$esc_cmd")
safe_jsonl_append "$BLOCKS_LOG" "$ENTRY" 2>/dev/null || true

exit 0
