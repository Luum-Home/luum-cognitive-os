#!/usr/bin/env bash
# SCOPE: both
# Serialize landing to main through a single-writer merge queue.
set -euo pipefail

REPO="${COS_MERGE_REPO:-$(pwd)}"
REMOTE="${COS_MERGE_REMOTE:-origin}"
MAIN_BRANCH="${COS_MAIN_BRANCH:-main}"
VALIDATE_CMD="${COS_MERGE_VALIDATE_CMD:-python3 scripts/derived_artifact_gate.py}"
DRY_RUN=false

usage() {
  cat <<'EOF'
Usage: scripts/merge_to_main.sh [--repo PATH] [--remote origin] [--main main] [--validate CMD] [--dry-run]

Acquires .cognitive-os/runtime/main-merge.lock, rebases the current branch on
REMOTE/MAIN, runs validation, fast-forwards main, and pushes. This is the
single-writer path for agent landings to main.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --repo) REPO="${2:-}"; shift 2 ;;
    --remote) REMOTE="${2:-}"; shift 2 ;;
    --main) MAIN_BRANCH="${2:-}"; shift 2 ;;
    --validate) VALIDATE_CMD="${2:-}"; shift 2 ;;
    --dry-run) DRY_RUN=true; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

REPO="$(cd "$REPO" && pwd -P)"
LOCK_DIR="$REPO/.cognitive-os/runtime/main-merge.lock"
QUEUE_FILE="$REPO/.cognitive-os/runtime/main-merge-queue.jsonl"
mkdir -p "$(dirname "$LOCK_DIR")"

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "main merge already in progress: $LOCK_DIR" >&2
  exit 75
fi
cleanup() { rmdir "$LOCK_DIR" 2>/dev/null || true; }
trap cleanup EXIT

branch="$(git -C "$REPO" rev-parse --abbrev-ref HEAD)"
if [ "$branch" = "$MAIN_BRANCH" ]; then
  echo "Refusing to land from $MAIN_BRANCH directly; use a session branch." >&2
  exit 2
fi
if [ -n "$(git -C "$REPO" status --porcelain=v1 --untracked-files=no)" ]; then
  echo "Refusing merge queue landing with tracked dirty worktree." >&2
  exit 3
fi
printf '{"timestamp":"%s","branch":"%s","pid":%s,"status":"started"}\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$branch" "$$" >> "$QUEUE_FILE"

git -C "$REPO" fetch "$REMOTE" "$MAIN_BRANCH"
git -C "$REPO" rebase "$REMOTE/$MAIN_BRANCH"
(
  cd "$REPO"
  eval "$VALIDATE_CMD"
)
if [ "$DRY_RUN" = true ]; then
  echo "merge_to_main: dry-run passed for $branch onto $REMOTE/$MAIN_BRANCH"
  exit 0
fi
git -C "$REPO" switch "$MAIN_BRANCH"
git -C "$REPO" merge --ff-only "$branch"
git -C "$REPO" push "$REMOTE" "$MAIN_BRANCH"
printf '{"timestamp":"%s","branch":"%s","pid":%s,"status":"pushed"}\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$branch" "$$" >> "$QUEUE_FILE"
