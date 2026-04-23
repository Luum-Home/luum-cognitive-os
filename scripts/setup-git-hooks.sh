#!/usr/bin/env bash
# SCOPE: project
# setup-git-hooks.sh — Install git hooks in the COS repo for auto-update
#
# Installs a post-merge hook that automatically updates all registered
# COS installations when the OS repo is pulled/updated.
#
# Usage:
#   bash scripts/setup-git-hooks.sh           # install hooks
#   bash scripts/setup-git-hooks.sh --remove  # remove hooks
#   bash scripts/setup-git-hooks.sh --status  # check if hooks are installed
#
# Safe: does NOT overwrite existing post-merge hooks. If one exists,
# it appends the auto-update call.
#
# Bash 3.x compatible (no associative arrays, no bash 4+ features).
# Author: luum
set -euo pipefail

COS_SOURCE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PORTABLE_SH="$COS_SOURCE_DIR/hooks/_lib/portable.sh"
if [ -f "$PORTABLE_SH" ]; then
  source "$PORTABLE_SH"
else
  # Degrade gracefully in minimal test or fixture repos that copy only scripts/.
  portable_sed_inplace() {
    local expr="$1"
    local file="$2"
    if command -v python3 >/dev/null 2>&1; then
      python3 - "$expr" "$file" <<'PYEOF'
import os
import re
import sys

expr = sys.argv[1]
path = sys.argv[2]
with open(path, "r", errors="replace") as fh:
    lines = fh.readlines()

result = []
m = re.match(r'^/(.*)/,/(.*)/d$', expr)
if m:
    start_pat = re.compile(m.group(1))
    end_pat = re.compile(m.group(2))
    in_range = False
    for line in lines:
      if not in_range and start_pat.search(line):
        in_range = True
        continue
      if in_range:
        if end_pat.search(line):
          in_range = False
        continue
      result.append(line)
else:
    result = lines

tmp = path + ".portable.tmp"
with open(tmp, "w", errors="replace") as fh:
    fh.writelines(result)
os.replace(tmp, path)
PYEOF
    else
      sed -i.bak "$expr" "$file" && rm -f "${file}.bak"
    fi
  }
fi

# Resolve the active hooks directory.
#
# git honors `core.hooksPath` over `.git/hooks` when both exist. If we install
# into `.git/hooks` while the repo has `core.hooksPath=.githooks`, the hooks
# we install never fire — silent breakage. Prefer the configured path.
#
# `git config --get` returns non-zero when the key is unset; we treat that
# as "no override" and fall back to `.git/hooks`.
_resolve_hooks_dir() {
  local configured
  configured="$(git -C "$COS_SOURCE_DIR" config --get core.hooksPath 2>/dev/null || true)"
  if [ -n "$configured" ]; then
    case "$configured" in
      /*) printf '%s\n' "$configured" ;;
      *)  printf '%s/%s\n' "$COS_SOURCE_DIR" "$configured" ;;
    esac
  else
    printf '%s/.git/hooks\n' "$COS_SOURCE_DIR"
  fi
}

GIT_HOOKS_DIR="$(_resolve_hooks_dir)"
POST_MERGE_HOOK="$GIT_HOOKS_DIR/post-merge"
PRE_PUSH_HOOK="$GIT_HOOKS_DIR/pre-push"
MARKER="# COS_AUTO_UPDATE"

# ── Parse args ─────────────────────────────────────────────────────
ACTION="install"
for arg in "$@"; do
  case "$arg" in
    --remove) ACTION="remove" ;;
    --status) ACTION="status" ;;
    --help|-h)
      echo "Usage: bash scripts/setup-git-hooks.sh [--remove|--status]"
      echo ""
      echo "  (default)  Install the post-merge hook for auto-updating projects"
      echo "  --remove   Remove the COS auto-update from post-merge hook"
      echo "  --status   Check if the hook is installed"
      exit 0
      ;;
    *)
      echo "Unknown option: $arg" >&2
      exit 1
      ;;
  esac
done

# ── Verify we're in a git repo ─────────────────────────────────────
if [ ! -d "$COS_SOURCE_DIR/.git" ]; then
  echo "Error: Not a git repository: $COS_SOURCE_DIR" >&2
  exit 1
fi

# ── Status check ───────────────────────────────────────────────────
if [ "$ACTION" = "status" ]; then
  for hook_file in "$POST_MERGE_HOOK" "$PRE_PUSH_HOOK"; do
    hook_name=$(basename "$hook_file")
    if [ -f "$hook_file" ] && grep -qF "$MARKER" "$hook_file" 2>/dev/null; then
      echo "COS auto-update ($hook_name): INSTALLED"
    else
      echo "COS auto-update ($hook_name): NOT INSTALLED"
    fi
  done
  exit 0
fi

# ── Helper: remove COS block from a hook file ────────────────────
_remove_cos_block() {
  local hook_file="$1"
  local hook_name
  hook_name=$(basename "$hook_file")

  if [ ! -f "$hook_file" ]; then
    echo "No $hook_name hook found. Nothing to remove."
    return 0
  fi

  if ! grep -qF "$MARKER" "$hook_file" 2>/dev/null; then
    echo "$hook_name hook exists but does not contain COS auto-update."
    return 0
  fi

  portable_sed_inplace "/$MARKER BEGIN/,/$MARKER END/d" "$hook_file"

  non_empty_lines=$(grep -cv '^\s*$\|^#!/' "$hook_file" 2>/dev/null || echo 0)
  if [ "$non_empty_lines" -eq 0 ]; then
    rm -f "$hook_file"
    echo "Removed $hook_name hook (was COS-only)."
  else
    echo "Removed COS auto-update block from $hook_name hook."
  fi
}

# ── Remove ─────────────────────────────────────────────────────────
if [ "$ACTION" = "remove" ]; then
  _remove_cos_block "$POST_MERGE_HOOK"
  _remove_cos_block "$PRE_PUSH_HOOK"
  exit 0
fi

# ── Helper: install COS block into a hook file ───────────────────
_install_cos_block() {
  local hook_file="$1"
  local hook_name
  hook_name=$(basename "$hook_file")

  if [ -f "$hook_file" ] && grep -qF "$MARKER" "$hook_file" 2>/dev/null; then
    echo "COS auto-update ($hook_name): already installed."
    return 0
  fi

  # The hook content — pre-push runs in background after push completes
  local hook_block
  if [ "$hook_name" = "pre-push" ]; then
    hook_block=$(cat << 'HOOKEOF'

# COS_AUTO_UPDATE BEGIN — Do not edit this block manually
# Auto-updates all registered COS installations after git push completes.
# Runs in background so the push is not delayed, and uses the new HEAD.
# Skips feature branches so registered projects are not upgraded from
# unmerged work. Main/master and tag pushes are allowed.
# Installed by: bash scripts/setup-git-hooks.sh
# Remove with:  bash scripts/setup-git-hooks.sh --remove
_COS_DIR="$(git rev-parse --show-toplevel 2>/dev/null)"
_COS_PUSH_ALLOWED=false
while read -r _local_ref _local_sha _remote_ref _remote_sha; do
  _tag_ref="${_local_ref#refs/tags/}"
  if [ "$_local_ref" = "refs/heads/main" ] || \
     [ "$_local_ref" = "refs/heads/master" ] || \
     [ "$_tag_ref" != "$_local_ref" ]; then
    _COS_PUSH_ALLOWED=true
  fi
done
if [ "$_COS_PUSH_ALLOWED" = true ] && [ -n "$_COS_DIR" ] && [ -f "$_COS_DIR/scripts/auto-update-projects.sh" ]; then
  (sleep 2 && echo "" && echo "[COS] Updating projects after push..." && \
   bash "$_COS_DIR/scripts/auto-update-projects.sh" 2>&1 | sed 's/^/[COS] /') &
else
  echo "[COS] Auto-update skipped for this push (only main/master/tag pushes propagate)." >&2
fi
# COS_AUTO_UPDATE END
HOOKEOF
    )
  else
    hook_block=$(cat << 'HOOKEOF'

# COS_AUTO_UPDATE BEGIN — Do not edit this block manually
# Auto-updates all registered COS installations after git pull/merge.
# Installed by: bash scripts/setup-git-hooks.sh
# Remove with:  bash scripts/setup-git-hooks.sh --remove
_COS_DIR="$(git rev-parse --show-toplevel 2>/dev/null)"
if [ -n "$_COS_DIR" ] && [ -f "$_COS_DIR/scripts/auto-update-projects.sh" ]; then
  echo ""
  echo "[COS] Checking for projects to update..."
  bash "$_COS_DIR/scripts/auto-update-projects.sh" 2>&1 | sed 's/^/[COS] /'
fi
# COS_AUTO_UPDATE END
HOOKEOF
    )
  fi

  if [ -f "$hook_file" ]; then
    echo "$hook_block" >> "$hook_file"
    echo "Appended COS auto-update to existing $hook_name hook."
  else
    cat > "$hook_file" << 'SHEBANG'
#!/usr/bin/env bash
SHEBANG
    echo "$hook_block" >> "$hook_file"
    chmod +x "$hook_file"
    echo "Created $hook_name hook with COS auto-update."
  fi
}

# ── Install ────────────────────────────────────────────────────────
mkdir -p "$GIT_HOOKS_DIR"

_install_cos_block "$POST_MERGE_HOOK"
_install_cos_block "$PRE_PUSH_HOOK"

echo ""
echo "Hooks directory: $GIT_HOOKS_DIR"
echo ""
echo "Auto-update triggers:"
echo "  git pull  -> post-merge  (users pulling updates)"
echo "  git push  -> pre-push    (maintainers pushing changes)"
echo ""
echo "All registered COS installations will be updated on either event."
