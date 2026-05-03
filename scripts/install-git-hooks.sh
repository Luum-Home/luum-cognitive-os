#!/usr/bin/env bash
# SCOPE: os-only
# install-git-hooks.sh — wire up the tracked git-hooks/ directory.
#
# Per ADR-131. Sets git's core.hooksPath to point at git-hooks/ so the tracked
# pre-push hook (and any future tracked hooks) take effect without copying
# files into .git/hooks/.
#
# Idempotent: re-running just confirms the configuration.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

if [ ! -d git-hooks ]; then
  echo "ERROR: git-hooks/ directory missing under $REPO_ROOT" >&2
  exit 1
fi

# Ensure the tracked hooks are executable. Permissions can drift on clone.
find git-hooks -type f -not -name '*.md' -exec chmod +x {} +

current="$(git config --local core.hooksPath || true)"

if [ "$current" = "git-hooks" ]; then
  echo "[install-git-hooks] core.hooksPath already set to git-hooks/. No change."
  exit 0
fi

git config --local core.hooksPath git-hooks
echo "[install-git-hooks] core.hooksPath -> git-hooks/"
echo
echo "Installed hooks:"
ls -1 git-hooks/ | sed 's/^/  - /'
echo
echo "To bypass for a single push: git push --no-verify"
echo "To skip via env: COS_PRE_PUSH_SKIP=1 git push"
echo "To run full tier: COS_PRE_PUSH_TIER=full git push"
