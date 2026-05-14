#!/usr/bin/env bash
# SCOPE: os-only
# SessionStart hook: Worktree Nudge — Layer 1 of ADR-035 defense
#
# Detects if Claude Code was launched from inside a git worktree (non-main)
# and emits an additionalContext warning BEFORE any work begins. This is the
# earliest possible interception point, ensuring the user knows that sub-agent
# commits will land on the worktree branch, not main.
#
# Detection logic:
#   1. Check if .git in CWD is a file (worktree link) vs a directory (main worktree)
#   2. If a file, parse the gitdir path to confirm it's a worktree entry
#   3. Extract the branch and main worktree path from `git worktree list --porcelain`
#
# Output: stdout message for SessionStart additionalContext (Claude Code native)
# Logs to: .cognitive-os/metrics/worktree-nudges.jsonl
# Graceful degradation: always exits 0, even on git failure
# p95 latency target: <30ms
#
# Policy:
#   cognitive-os.yaml orchestration.sub_agent_cwd controls the current setting.
#   If set to "current", the nudge still fires (the policy doesn't prevent the
#   risk — it just means the user explicitly opted in to worktree commits).

set -uo pipefail

# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="session-start-worktree-nudge"
source "$(dirname "$0")/_lib/safe-jsonl.sh"

# ── Locate project root ──────────────────────────────────────────────────────
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
METRICS_DIR="$(_resolve_metrics_dir)"
NUDGES_LOG="$METRICS_DIR/worktree-nudges.jsonl"

# ── Check if .git is a file (worktree) or directory (main) ──────────────────
# In a git worktree, .git is a FILE containing "gitdir: /path/to/.git/worktrees/name"
# In the main worktree, .git is a DIRECTORY.
GIT_ENTRY="$PROJECT_DIR/.git"

if [ ! -e "$GIT_ENTRY" ]; then
  # Not a git repo at all — silent exit
  exit 0
fi

if [ -d "$GIT_ENTRY" ]; then
  # .git is a directory → this IS the main worktree, no nudge needed
  exit 0
fi

if [ ! -f "$GIT_ENTRY" ]; then
  # Neither file nor directory — unusual, silent exit
  exit 0
fi

# .git is a file → we are inside a worktree. Parse the gitdir line.
GITDIR_LINE=$(head -1 "$GIT_ENTRY" 2>/dev/null || true)
if [[ "$GITDIR_LINE" != "gitdir: "* ]]; then
  # Malformed .git file — silent exit
  exit 0
fi

# ── Confirmed: running from a non-main worktree ──────────────────────────────
CWD="$PROJECT_DIR"

# Get the current branch
CURRENT_BRANCH=$(git -C "$CWD" symbolic-ref --short HEAD 2>/dev/null || echo "unknown")

# Find the main worktree path via `git worktree list --porcelain`
# The first entry in the list is always the main worktree.
MAIN_WORKTREE=""
FIRST_PATH=""
IN_FIRST=true

while IFS= read -r line; do
  if [[ "$line" == "worktree "* ]]; then
    if [ "$IN_FIRST" = true ]; then
      FIRST_PATH="${line#worktree }"
      IN_FIRST=false
    fi
  fi
  # Stop after first blank line (end of first stanza)
  if [ -z "$line" ] && [ -n "$FIRST_PATH" ]; then
    MAIN_WORKTREE="$FIRST_PATH"
    break
  fi
done < <(git -C "$CWD" worktree list --porcelain 2>/dev/null || true)

# Fallback: if no blank line found, use FIRST_PATH
[ -z "$MAIN_WORKTREE" ] && MAIN_WORKTREE="$FIRST_PATH"

# ── Read current policy from cognitive-os.yaml ───────────────────────────────
CONFIG_FILE="$PROJECT_DIR/cognitive-os.yaml"
[ ! -f "$CONFIG_FILE" ] && CONFIG_FILE="$PROJECT_DIR/.cognitive-os/cognitive-os.yaml"

POLICY="isolated_worktree"  # default assumption
if [ -f "$CONFIG_FILE" ]; then
  extracted=$(grep -A5 '^orchestration:' "$CONFIG_FILE" 2>/dev/null \
    | grep 'sub_agent_cwd:' \
    | head -1 \
    | sed 's/.*sub_agent_cwd:[[:space:]]*//' \
    | sed 's/[[:space:]]*#.*//' \
    | tr -d '[:space:]' || true)
  [ -n "$extracted" ] && POLICY="$extracted"
fi

# ── Log the nudge event ───────────────────────────────────────────────────────
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo "unknown")
LOG_ENTRY=$(printf '{"timestamp":"%s","cwd":"%s","branch":"%s","main_worktree":"%s","policy":"%s"}' \
  "$TS" "$CWD" "$CURRENT_BRANCH" "${MAIN_WORKTREE:-unknown}" "$POLICY")
safe_jsonl_append "$NUDGES_LOG" "$LOG_ENTRY" || true

# ── Emit the warning to stdout ────────────────────────────────────────────────
# Claude Code SessionStart hooks print to stdout as additionalContext.
cat <<NUDGE

WARNING: WORKTREE DETECTED
You are running Claude Code from a git worktree: $CWD
Branch: $CURRENT_BRANCH
Main worktree: ${MAIN_WORKTREE:-unknown}

Sub-agents inherit this cwd. Commits from agents WILL land on branch
'$CURRENT_BRANCH', not on main, unless they explicitly use
\`git -C ${MAIN_WORKTREE:-<main-path>}\` or \`cd ${MAIN_WORKTREE:-<main-path>}\`
before each git command.

Suggestions:
  1. Prefer orchestration.sub_agent_cwd: isolated_worktree so write agents get
       dedicated ADR-223 worktrees and never shift the operator worktree HEAD.
  2. Launch Claude Code from main for direct operator commits:
       cd ${MAIN_WORKTREE:-<main-path>} && claude
  3. Use legacy orchestration.sub_agent_cwd: main_worktree only for single-agent
       sessions where rewriting git commands back to main is intentional.
  4. Set orchestration.sub_agent_cwd: current only if you WANT commits to land
       on this worktree branch.

Current policy (cognitive-os.yaml orchestration.sub_agent_cwd): $POLICY

NUDGE

exit 0
