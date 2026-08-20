#!/usr/bin/env bash
# SCOPE: both
# project-root.sh — single source of truth for "which directory is the project root".
#
# Usage:
#   source "$(dirname "${BASH_SOURCE[0]}")/_lib/project-root.sh"
#   PROJECT_DIR="$(cos_project_root)"
#
# Why this exists:
#   Hooks used to derive their fallback root as
#       PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
#   For a hook living in <root>/hooks/ that resolves to the PARENT of the
#   repository; for the same file at <root>/packages/<pkg>/hooks/ it resolves to
#   <root>/packages. Neither is the project root. Claude Code always exports
#   CLAUDE_PROJECT_DIR, so the fallback never fires there; it fires under
#   codex/opencode/bare invocation, where nobody is watching.
#
# Resolution order:
#   1. COGNITIVE_OS_PROJECT_DIR   (harness-agnostic override)
#   2. CODEX_PROJECT_DIR
#   3. CLAUDE_PROJECT_DIR
#   4. Structural anchor: this library's own PHYSICAL location. Every hook
#      reaches this file through <root>/hooks/_lib/ — package hook dirs expose
#      _lib as a symlink to ../../../hooks/_lib, so `pwd -P` collapses every
#      invocation path onto the one canonical directory. Two segments up from
#      <root>/hooks/_lib is <root>, by construction.
#
# Deliberately NOT used as the anchor:
#   - "$0" / "${BASH_SOURCE[0]}" of the CALLING hook: varies with invocation
#     path — that is precisely the bug being fixed.
#   - "$(pwd)" or `git rev-parse --show-toplevel` from the cwd: a hook may run
#     with any cwd, including inside a worktree or a nested repository.

[ "${_COS_PROJECT_ROOT_SH_LOADED:-}" = "true" ] && return 0
_COS_PROJECT_ROOT_SH_LOADED="true"

# Physical directory of THIS file (symlinks resolved by `pwd -P`).
_COS_PROJECT_ROOT_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

# Two path segments up from <root>/hooks/_lib.
_COS_PROJECT_ROOT_ANCHORED="${_COS_PROJECT_ROOT_LIB_DIR%/*/*}"

cos_project_root() {
  if [ -n "${COGNITIVE_OS_PROJECT_DIR:-}" ]; then
    printf '%s\n' "$COGNITIVE_OS_PROJECT_DIR"
  elif [ -n "${CODEX_PROJECT_DIR:-}" ]; then
    printf '%s\n' "$CODEX_PROJECT_DIR"
  elif [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
    printf '%s\n' "$CLAUDE_PROJECT_DIR"
  else
    printf '%s\n' "$_COS_PROJECT_ROOT_ANCHORED"
  fi
}
