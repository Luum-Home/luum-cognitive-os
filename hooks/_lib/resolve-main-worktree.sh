#!/usr/bin/env bash
# SCOPE: os-only
# resolve-main-worktree.sh — Shared library: resolve the main worktree path.
#
# Usage:
#   source hooks/_lib/resolve-main-worktree.sh
#   TARGET=$(resolve_main_worktree "/path/to/project")
#
# Returns the absolute path of the worktree whose branch is "main" or "master",
# falling back to the first listed worktree. Echoes the result to stdout.
# Returns an empty string (exit 0) on any failure.

_rwt_find_worktree_for_branch() {
  local project_dir="$1"
  local target_branch="$2"
  local cur_path="" cur_branch=""

  while IFS= read -r line; do
    case "$line" in
      worktree\ *)  cur_path="${line#worktree }"; cur_branch="" ;;
      branch\ refs/heads/*)  cur_branch="${line#branch refs/heads/}" ;;
      "")
        if [ -n "$cur_path" ] && [ "$cur_branch" = "$target_branch" ]; then
          printf '%s' "$cur_path"
          return 0
        fi
        cur_path=""; cur_branch=""
        ;;
    esac
  done < <(git -C "$project_dir" worktree list --porcelain 2>/dev/null || true)
}

_rwt_first_worktree() {
  local project_dir="$1"
  git -C "$project_dir" worktree list --porcelain 2>/dev/null \
    | grep '^worktree ' | head -1 | sed 's/^worktree //' || true
}

resolve_main_worktree() {
  local project_dir="${1:-}"
  if [ -z "$project_dir" ]; then
    return 0
  fi

  local target=""
  target=$(_rwt_find_worktree_for_branch "$project_dir" "main")
  [ -z "$target" ] && target=$(_rwt_find_worktree_for_branch "$project_dir" "master")
  [ -z "$target" ] && target=$(_rwt_first_worktree "$project_dir")

  printf '%s' "$target"
}
