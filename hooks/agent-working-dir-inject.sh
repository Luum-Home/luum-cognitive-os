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
# Cache: resolved path is stored in .cognitive-os/cwd-inject-cache.json.
#   On warm invocations (cache hit, .git/worktrees/ mtime unchanged) the git
#   worktree list call is skipped entirely, bringing p95 from ~40ms to <5ms.
#   Cache failures fall through to the uncached code path (graceful degradation).
#
# p95 latency target: <50 ms cold, <5 ms warm (cached).

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

json_escape() {
  local s="$1"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  s="${s//$'\n'/\\n}"
  s="${s//$'\r'/\\r}"
  s="${s//$'\t'/\\t}"
  printf '%s' "$s"
}

emit_additional_context() {
  local ctx escaped
  ctx="$1"
  escaped="$(json_escape "$ctx")"
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"%s"}}\n' "$escaped"
}

portable_stat_mtime_fast() {
  local path="$1" out
  if out="$(stat -f %m "$path" 2>/dev/null)"; then
    printf '%s\n' "$out"
  elif out="$(stat -c %Y "$path" 2>/dev/null)"; then
    printf '%s\n' "$out"
  else
    python3 -c "import os, sys; print(int(os.path.getmtime(sys.argv[1])))" "$path"
  fi
}

# ── Read stdin / detect Claude Code invocation ───────────────────────────────
INPUT=$(cat)
TOOL_NAME=""
case "$INPUT" in
  *'"tool_name"'*'"Agent"'*) TOOL_NAME="Agent" ;;
  *'"tool_name"'*'"task"'*) TOOL_NAME="task" ;;
  *'"tool_name"'*'"delegate"'*) TOOL_NAME="delegate" ;;
esac

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
  in_orchestration=0
  while IFS= read -r line; do
    case "$line" in
      orchestration:*) in_orchestration=1; continue ;;
      [![:space:]]*) [ "$in_orchestration" -eq 1 ] && break ;;
    esac
    if [ "$in_orchestration" -eq 1 ] && [[ "$line" == *sub_agent_cwd:* ]]; then
      extracted="${line#*:}"
      extracted="${extracted%%#*}"
      extracted="${extracted//[[:space:]]/}"
      [ -n "$extracted" ] && POLICY="$extracted"
      break
    fi
  done < "$CONFIG_FILE"
else
  log_event "yaml_missing" "cognitive-os.yaml not found"
  exit 0
fi

# ── Handle policy=current: no injection ─────────────────────────────────────
if [ "$POLICY" = "current" ]; then
  log_event "skip" "policy=current"
  exit 0
fi

# ── Cache helpers ────────────────────────────────────────────────────────────
# Cache file path — overridable by tests via CWD_INJECT_CACHE_FILE env var.
COS_DIR="$PROJECT_DIR/.cognitive-os"
CACHE_FILE="${CWD_INJECT_CACHE_FILE:-$COS_DIR/cwd-inject-cache.json}"

# Return the mtime of the .git/worktrees directory (as epoch seconds), or "0"
# if it does not exist. We use this as an invalidation key: if worktrees dir
# mtime changes, a new worktree was added/removed and the cache is stale.
_worktrees_mtime() {
  local wt_dir="$PROJECT_DIR/.git/worktrees"
  if [ -d "$wt_dir" ]; then
    portable_stat_mtime_fast "$wt_dir" 2>/dev/null || echo "0"
  else
    # No worktrees dir (single-worktree repo) — use mtime of .git itself as
    # a stable proxy; changes only when repo structure changes.
    portable_stat_mtime_fast "$PROJECT_DIR/.git" 2>/dev/null || echo "0"
  fi
}

# Try to read TARGET_DIR from cache.
# Sets TARGET_DIR (global) to the cached path on hit, leaves it empty on miss.
# Never exits non-zero — all errors fall through to uncached resolution.
_cache_read() {
  [ ! -f "$CACHE_FILE" ] && return 0

  local cache_content cached_path cached_mtime current_mtime
  cache_content="$(< "$CACHE_FILE")"
  if [[ "$cache_content" =~ \"path\"[[:space:]]*:[[:space:]]*\"([^\"]*)\" ]]; then
    cached_path="${BASH_REMATCH[1]}"
  else
    cached_path=""
  fi
  if [[ "$cache_content" =~ \"mtime\"[[:space:]]*:[[:space:]]*([0-9]+) ]]; then
    cached_mtime="${BASH_REMATCH[1]}"
  else
    cached_mtime=""
  fi

  [ -z "$cached_path" ] && return 0
  [ -z "$cached_mtime" ] && return 0

  current_mtime=$(_worktrees_mtime)

  # Cache is valid when stored mtime >= current mtime (no new worktree events)
  if [ "$cached_mtime" -ge "$current_mtime" ] 2>/dev/null; then
    TARGET_DIR="$cached_path"
  fi
  return 0
}

# Write TARGET_DIR to the cache file.
# Silently no-ops on any write error (graceful degradation).
_cache_write() {
  local path="$1"
  local mtime
  mtime=$(_worktrees_mtime)
  local ts
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo "unknown")"
  mkdir -p "$(dirname "$CACHE_FILE")" 2>/dev/null || return 0
  printf '{"path":"%s","mtime":%s,"cached_at":"%s"}\n' \
    "$(json_escape "$path")" "$mtime" "$ts" > "$CACHE_FILE" 2>/dev/null || true
}

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

# ── Attempt cache read (warm path) ───────────────────────────────────────────
# Only cache main_worktree resolutions — branch policy depends on the current
# HEAD which can change without touching .git/worktrees.
if [ "$POLICY" = "main_worktree" ]; then
  _cache_read || true  # never let cache errors abort the hook
fi

# ── Cold path: resolve via git if cache missed ───────────────────────────────
if [ -z "$TARGET_DIR" ]; then
  case "$POLICY" in
    main_worktree)
      TARGET_DIR=$(find_worktree_for_branch "main")
      [ -z "$TARGET_DIR" ] && TARGET_DIR=$(find_worktree_for_branch "master")
      [ -z "$TARGET_DIR" ] && TARGET_DIR=$(first_worktree)
      # Persist result to cache for next invocation
      [ -n "$TARGET_DIR" ] && _cache_write "$TARGET_DIR" || true
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
fi

if [ -z "$TARGET_DIR" ]; then
  log_event "resolve_failed" "policy=$POLICY"
  exit 0
fi

if [ "${CWD_INJECT_VERBOSE_METRICS:-0}" = "1" ]; then
  log_event "injected" "policy=$POLICY target=$TARGET_DIR"
fi

# ── Build and emit additionalContext ─────────────────────────────────────────
CONTEXT="WORKING DIR: $TARGET_DIR
(Auto-resolved by agent-working-dir-inject.sh per cognitive-os.yaml orchestration.sub_agent_cwd=$POLICY)
MUST scope git operations to this worktree, not the caller cwd.
Example: git -C \"$TARGET_DIR\" status
Alternative: cd \"$TARGET_DIR\" && git status
Use absolute paths under $TARGET_DIR.
Commits land on the branch checked out at $TARGET_DIR."

if [ "$HAS_VALID_INPUT" -eq 1 ]; then
  emit_additional_context "$CONTEXT"
else
  # Manual / test invocation — emit to stderr for diagnostic visibility
  printf '%s\n' "$CONTEXT" >&2
fi

exit 0
