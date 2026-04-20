#!/usr/bin/env bash
# SCOPE: both
# PreToolUse hook on Agent — injects a WORKING DIR directive into every sub-agent's
# additionalContext so that agents started from inside a git worktree still commit
# to, and write files under, the correct directory.
#
# Policy is driven by cognitive-os.yaml → orchestration.sub_agent_cwd:
#   current       — no injection (sub-agent inherits parent cwd as-is)
#   main_worktree — resolve the worktree whose branch is the repo default branch
#                   (origin/HEAD short-name, fallback: "main"). Inject its path.
#   branch        — inject the primary worktree for the currently-checked-out branch.
#
# Output: hookSpecificOutput.additionalContext JSON on stdout (Claude Code native).
# Graceful degradation: exits 0 silently on any failure; logs reason to
#   .cognitive-os/metrics/cwd-inject.jsonl
#
# p95 latency target: <50 ms (git + yaml read only, no network calls).

set -euo pipefail

# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

# ── Locate project root ──────────────────────────────────────────────────────
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-}"
if [ -z "$PROJECT_DIR" ]; then
  PROJECT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || true)"
fi
if [ -z "$PROJECT_DIR" ]; then
  exit 0
fi

# ── Metrics helper ───────────────────────────────────────────────────────────
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
METRICS_FILE="$METRICS_DIR/cwd-inject.jsonl"

log_event() {
  local event="$1"
  local detail="${2:-}"
  mkdir -p "$METRICS_DIR" 2>/dev/null || true
  local ts
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo "unknown")"
  printf '{"timestamp":"%s","event":"%s","detail":"%s"}\n' \
    "$ts" "$event" "$detail" >> "$METRICS_FILE" 2>/dev/null || true
}

# ── Read stdin / detect Claude Code invocation ───────────────────────────────
INPUT=$(cat)
TOOL_NAME=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || true)

# Only process Agent tool calls (task / delegate are aliases used in some setups)
if [ -n "$TOOL_NAME" ] && [ "$TOOL_NAME" != "Agent" ] && \
   [ "$TOOL_NAME" != "task" ] && [ "$TOOL_NAME" != "delegate" ]; then
  exit 0
fi

HAS_VALID_INPUT=0
if [ -n "$TOOL_NAME" ]; then
  HAS_VALID_INPUT=1
fi

# ── Read policy from cognitive-os.yaml ──────────────────────────────────────
CONFIG_FILE="$PROJECT_DIR/cognitive-os.yaml"
[ ! -f "$CONFIG_FILE" ] && CONFIG_FILE="$PROJECT_DIR/.cognitive-os/cognitive-os.yaml"

POLICY="main_worktree"  # safe default
if [ -f "$CONFIG_FILE" ]; then
  extracted=$(grep -A5 '^orchestration:' "$CONFIG_FILE" 2>/dev/null \
    | grep 'sub_agent_cwd:' \
    | head -1 \
    | sed 's/.*sub_agent_cwd:\s*//' \
    | sed 's/\s*#.*//' \
    | tr -d '[:space:]' || true)
  if [ -n "$extracted" ]; then
    POLICY="$extracted"
  fi
else
  log_event "yaml_missing" "cognitive-os.yaml not found"
  exit 0
fi

# ── Handle policy=current: no injection ─────────────────────────────────────
if [ "$POLICY" = "current" ]; then
  log_event "skip" "policy=current"
  exit 0
fi

# ── Parse worktree list once ─────────────────────────────────────────────────
# Returns path for the first worktree whose branch matches $1, or empty string.
find_worktree_for_branch() {
  local target_branch="$1"
  local wt_path="" cur_path="" cur_branch=""

  while IFS= read -r line; do
    case "$line" in
      worktree\ *)  cur_path="${line#worktree }"; cur_branch="" ;;
      branch\ refs/heads/*)  cur_branch="${line#branch refs/heads/}" ;;
      "")
        if [ -n "$cur_path" ] && [ "$cur_branch" = "$target_branch" ]; then
          wt_path="$cur_path"
          break
        fi
        cur_path=""; cur_branch=""
        ;;
    esac
  done < <(git -C "$PROJECT_DIR" worktree list --porcelain 2>/dev/null || true)

  printf '%s' "$wt_path"
}

# Returns the first non-bare worktree path (fallback).
first_worktree() {
  git -C "$PROJECT_DIR" worktree list --porcelain 2>/dev/null \
    | grep '^worktree ' | head -1 | sed 's/^worktree //' || true
}

TARGET_DIR=""

case "$POLICY" in
  main_worktree)
    # The primary/main worktree is always the FIRST entry in `git worktree list`.
    # We prefer the worktree whose branch matches "main" or "master", but fall back
    # to the first entry to avoid the expensive `git symbolic-ref` call.
    TARGET_DIR=$(find_worktree_for_branch "main")
    [ -z "$TARGET_DIR" ] && TARGET_DIR=$(find_worktree_for_branch "master")
    [ -z "$TARGET_DIR" ] && TARGET_DIR=$(first_worktree)
    ;;
  branch)
    current_branch=$(git -C "$PROJECT_DIR" symbolic-ref --short HEAD 2>/dev/null || true)
    if [ -n "$current_branch" ]; then
      TARGET_DIR=$(find_worktree_for_branch "$current_branch")
    fi
    # Fallback: project dir
    [ -z "$TARGET_DIR" ] && TARGET_DIR="$PROJECT_DIR"
    ;;
  *)
    log_event "unknown_policy" "$POLICY"
    exit 0
    ;;
esac

if [ -z "$TARGET_DIR" ]; then
  log_event "resolve_failed" "policy=$POLICY"
  exit 0
fi

log_event "injected" "policy=$POLICY target=$TARGET_DIR"

# ── Build and emit additionalContext ─────────────────────────────────────────
CONTEXT="WORKING DIR: $TARGET_DIR
(Auto-resolved by agent-working-dir-inject.sh per cognitive-os.yaml orchestration.sub_agent_cwd=$POLICY)
Use absolute paths under this directory. Commits land on the branch checked out at that path."

if [ "$HAS_VALID_INPUT" -eq 1 ]; then
  # Prefer jq (no python3 startup cost); fall back to python3 if jq unavailable.
  if command -v jq >/dev/null 2>&1; then
    jq -n \
      --arg ctx "$CONTEXT" \
      '{hookSpecificOutput:{hookEventName:"PreToolUse",additionalContext:$ctx}}'
  else
    printf '%s' "$CONTEXT" | python3 -c "
import json, sys
ctx = sys.stdin.read()
out = {'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'additionalContext': ctx}}
sys.stdout.write(json.dumps(out))
"
  fi
else
  # Manual / test invocation — emit to stderr for diagnostic visibility
  printf '%s\n' "$CONTEXT" >&2
fi

exit 0
