#!/usr/bin/env bash
# cos-session-spawn.sh — ADR-098 Phase D4: smart multi-session launcher
#
# Detects existing concurrent COS sessions on the current repo and either:
#   - Recommends + creates a git worktree if another session is active, OR
#   - Launches claude directly if no concurrent session is detected.
#
# Usage:
#   bash scripts/cos-session-spawn.sh [claude-args...]
#   COS_FORCE_WORKTREE=1 bash scripts/cos-session-spawn.sh   # always create worktree
#   COS_SKIP_WORKTREE=1  bash scripts/cos-session-spawn.sh   # always skip worktree
#
# Environment overrides:
#   COS_ACTIVE_SESSION_WINDOW_SECONDS  — recency window for "active" sessions (default: 1800)
#   COS_FORCE_WORKTREE                 — skip detection, always offer worktree
#   COS_SKIP_WORKTREE                  — skip detection, launch directly
#   COS_WORKTREE_BRANCH_PREFIX         — prefix for auto-generated branch names (default: session)
#
# Conventions follow git-coop.sh/_resolve_project_dir pattern.
set -uo pipefail

# ── Resolve project root (mirrors edit-coop.sh _resolve_project_dir) ──────────
_resolve_project_dir() {
  if [ -n "${CLAUDE_PROJECT_DIR:-}" ];       then printf '%s' "$CLAUDE_PROJECT_DIR";       return; fi
  if [ -n "${COGNITIVE_OS_PROJECT_DIR:-}" ]; then printf '%s' "$COGNITIVE_OS_PROJECT_DIR"; return; fi
  local dir
  dir="$(pwd)"
  while [ "$dir" != "/" ]; do
    if [ -f "$dir/cognitive-os.yaml" ] || [ -d "$dir/.claude" ]; then
      printf '%s' "$dir"
      return
    fi
    dir="$(dirname "$dir")"
  done
  printf '%s' "$(pwd)"
}

PROJECT_DIR="$(_resolve_project_dir)"
COOP="$PROJECT_DIR/scripts/edit-coop.sh"
SESSIONS_DIR="$PROJECT_DIR/.cognitive-os/sessions"
ACTIVE_WINDOW="${COS_ACTIVE_SESSION_WINDOW_SECONDS:-1800}"   # 30 min
BRANCH_PREFIX="${COS_WORKTREE_BRANCH_PREFIX:-session}"

# ── Count active sessions ─────────────────────────────────────────────────────
_count_active_sessions() {
  [ -d "$SESSIONS_DIR" ] || { printf '0'; return; }

  # A session is "active" if its directory was modified within ACTIVE_WINDOW seconds.
  # Using find with -newer against a reference file is portable across macOS/Linux.
  local ref_file
  ref_file="$(mktemp)"
  # Backdate the reference file so that "newer than ref" == modified recently.
  # On macOS: touch -t [[CC]YY]MMDDhhmm[.ss] or use Python for portability.
  local cutoff_epoch
  cutoff_epoch=$(( $(date -u +%s) - ACTIVE_WINDOW ))
  python3 -c "
import os, time
os.utime('$ref_file', (float('$cutoff_epoch'), float('$cutoff_epoch')))
" 2>/dev/null || touch "$ref_file"

  local count
  count="$(find "$SESSIONS_DIR" -maxdepth 1 -type d -newer "$ref_file" 2>/dev/null | wc -l | tr -d ' ')"
  rm -f "$ref_file"
  printf '%s' "$count"
}

# ── Count lock-holding sessions ───────────────────────────────────────────────
_count_lock_sessions() {
  [ -x "$COOP" ] || { printf '0'; return; }
  local json
  json="$(bash "$COOP" status 2>/dev/null)" || { printf '0'; return; }
  python3 -c "
import json, sys
try:
    data = json.loads('''$json''')
    sessions = {lock.get('session','') for lock in data.get('locks',[])}
    sessions.discard('')
    print(len(sessions))
except Exception:
    print(0)
" 2>/dev/null || printf '0'
}

# ── Generate a unique worktree path and branch name ───────────────────────────
_new_worktree_name() {
  local ts
  ts="$(date +%s)"
  local repo_name
  repo_name="$(basename "$PROJECT_DIR")"
  printf '%s--%s-%s' "$repo_name" "$BRANCH_PREFIX" "$ts"
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
  # Override shortcuts.
  if [ "${COS_SKIP_WORKTREE:-}" = "1" ]; then
    echo "[cos-session-spawn] COS_SKIP_WORKTREE=1: launching claude directly" >&2
    exec claude "$@"
  fi

  local active_count lock_count
  active_count="$(_count_active_sessions)"
  lock_count="$(_count_lock_sessions)"

  local recommend_worktree=0

  if [ "${COS_FORCE_WORKTREE:-}" = "1" ]; then
    recommend_worktree=1
    echo "[cos-session-spawn] COS_FORCE_WORKTREE=1: worktree recommendation forced" >&2
  elif [ "$active_count" -gt 1 ] || [ "$lock_count" -gt 0 ]; then
    recommend_worktree=1
  fi

  if [ "$recommend_worktree" -eq 0 ]; then
    echo "[cos-session-spawn] no concurrent sessions detected (active=$active_count, lock_holders=$lock_count)" >&2
    echo "[cos-session-spawn] launching claude directly" >&2
    exec claude "$@"
  fi

  # Recommend worktree.
  local wt_name
  wt_name="$(_new_worktree_name)"
  local wt_path
  wt_path="$(dirname "$PROJECT_DIR")/$wt_name"
  local branch="$BRANCH_PREFIX-$(date +%s)"

  echo "" >&2
  echo "============================================================" >&2
  echo " COS: Concurrent sessions detected" >&2
  echo "   Active sessions (last ${ACTIVE_WINDOW}s): $active_count" >&2
  echo "   Sessions holding edit locks:              $lock_count" >&2
  echo "" >&2
  echo " Recommended: use a git worktree so each session operates" >&2
  echo " on a physically distinct set of files (no lock contention)." >&2
  echo "" >&2
  echo "   Proposed worktree: $wt_path" >&2
  echo "   Branch:            $branch" >&2
  echo "" >&2
  echo " Command that would be run:" >&2
  echo "   git -C \"$PROJECT_DIR\" worktree add \"$wt_path\" -b \"$branch\"" >&2
  echo "   cd \"$wt_path\" && claude $*" >&2
  echo "============================================================" >&2
  echo "" >&2

  # Prompt unless stdin is not a terminal (CI / pipe context → skip prompt).
  local ans="n"
  if [ -t 0 ]; then
    printf 'Create worktree now? [Y/n]: '
    read -r ans </dev/tty || ans="n"
  else
    echo "[cos-session-spawn] non-interactive: skipping worktree creation, launching directly" >&2
    exec claude "$@"
  fi

  case "$ans" in
    ""|[Yy]*)
      echo "[cos-session-spawn] creating worktree..." >&2
      if ! git -C "$PROJECT_DIR" worktree add "$wt_path" -b "$branch" 2>&1; then
        echo "[cos-session-spawn] ERROR: worktree creation failed; launching claude in current dir" >&2
        exec claude "$@"
      fi
      echo "[cos-session-spawn] worktree created: $wt_path" >&2
      echo "[cos-session-spawn] launching claude in worktree..." >&2
      cd "$wt_path"
      exec claude "$@"
      ;;
    *)
      echo "[cos-session-spawn] worktree declined; launching claude in current dir" >&2
      exec claude "$@"
      ;;
  esac
}

main "$@"
