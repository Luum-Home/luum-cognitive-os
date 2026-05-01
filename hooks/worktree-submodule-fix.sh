#!/usr/bin/env bash
# SCOPE: project
# @manual-trigger: invoked manually after worktree operations; not a global default
# worktree-submodule-fix.sh — SessionStart hook
#
# Problem: git submodule .git files use relative paths (gitdir: ../../../.git/modules/...)
# that resolve incorrectly when running inside a worktree, because the worktree lives at
# a different filesystem depth than the main repo.
#
# Symptom: "fatal: not a git repository: ...relative path that doesn't exist..."
#
# Fix: Rewrite each submodule .git file with the absolute path to the main repo's
# .git/modules/<submodule> directory.
#
# This hook is idempotent and advisory: it only rewrites files whose current path
# cannot be resolved, and always exits 0.
#
# Related: Claude Code issue anthropics/claude-code#27201 (closed without fix)

set -euo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

# Only run if .git is a FILE (i.e., we're inside a worktree or submodule checkout).
# In a normal clone, .git is a directory.
GIT_FILE=".git"
if [[ ! -f "$GIT_FILE" ]]; then
  exit 0
fi

# Read the worktree's gitdir (e.g., "/path/to/repo/.git/worktrees/my-wt")
WORKTREE_GITDIR=$(sed 's/^gitdir: //' "$GIT_FILE")
if [[ -z "$WORKTREE_GITDIR" ]]; then
  exit 0
fi

# Resolve to absolute path if relative
if [[ "$WORKTREE_GITDIR" != /* ]]; then
  WORKTREE_GITDIR="$(cd "$(dirname "$GIT_FILE")/$WORKTREE_GITDIR" 2>/dev/null && pwd)" || exit 0
fi

# Walk up from the worktree gitdir to find the main .git directory.
# Worktree gitdir is typically: /main/repo/.git/worktrees/<name>
# We need:                       /main/repo/.git
MAIN_GIT_DIR=""
candidate="$WORKTREE_GITDIR"
while [[ "$candidate" != "/" ]]; do
  if [[ -f "$candidate/config" && -d "$candidate/objects" ]]; then
    # Check it's not itself a worktree gitdir (those have a "gitdir" file pointing back)
    if [[ ! -f "$candidate/gitdir" ]]; then
      MAIN_GIT_DIR="$candidate"
      break
    fi
  fi
  candidate="$(dirname "$candidate")"
done

if [[ -z "$MAIN_GIT_DIR" ]]; then
  exit 0
fi

# No .gitmodules means nothing to fix
if [[ ! -f ".gitmodules" ]]; then
  exit 0
fi

MODULES_DIR="$MAIN_GIT_DIR/modules"
if [[ ! -d "$MODULES_DIR" ]]; then
  exit 0
fi

patched=()

# Parse submodule paths from .gitmodules
while IFS= read -r line; do
  if [[ "$line" =~ ^[[:space:]]*path[[:space:]]*=[[:space:]]*(.+)$ ]]; then
    submodule_path="${BASH_REMATCH[1]}"
    submodule_path="${submodule_path#"${submodule_path%%[![:space:]]*}"}"  # ltrim
    submodule_path="${submodule_path%"${submodule_path##*[![:space:]]}"}"  # rtrim

    git_file="$submodule_path/.git"
    if [[ ! -f "$git_file" ]]; then
      continue
    fi

    current_content=$(cat "$git_file")
    current_path="${current_content#gitdir: }"

    # Resolve the current path relative to the submodule directory
    resolved=""
    if [[ "$current_path" == /* ]]; then
      resolved="$current_path"
    else
      resolved="$(cd "$submodule_path" && cd "$current_path" 2>/dev/null && pwd)" || true
    fi

    # If the path already resolves correctly, skip
    if [[ -n "$resolved" && -d "$resolved" ]]; then
      continue
    fi

    # Compute the correct absolute path: $MAIN_GIT_DIR/modules/<submodule_path>
    correct_path="$MODULES_DIR/$submodule_path"
    if [[ ! -d "$correct_path" ]]; then
      continue
    fi

    # Rewrite the .git file with the absolute path
    printf 'gitdir: %s\n' "$correct_path" > "$git_file"
    patched+=("$(basename "$submodule_path")")
  fi
done < ".gitmodules"

if [[ ${#patched[@]} -gt 0 ]]; then
  names=$(IFS=", "; echo "${patched[*]}")
  echo "Worktree submodule fix: patched ${#patched[@]} submodule .git files ($names)"
fi

exit 0
