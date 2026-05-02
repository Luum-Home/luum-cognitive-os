#!/usr/bin/env bash
# SCOPE: both
# Create or switch to an isolated per-session branch for multi-agent work.
set -euo pipefail

REPO="."
BASE="HEAD"
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-}"
SLUG="work"
SWITCH=false
JSON=false
ALLOW_DIRTY=false

usage() {
  cat <<'USAGE'
Usage: bash scripts/cos-session-branch.sh [--repo PATH] [--base REF] [--session-id ID] [--slug TEXT] [--switch] [--allow-dirty] [--json]

Creates a deterministic branch name under session/<session-id>-<slug> so agents
work away from shared main/master. By default it refuses a dirty worktree and
prints the branch name without switching. Use --switch to git switch to it.
USAGE
}

json_escape() { python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$1"; }

slugify() {
  python3 -c 'import re,sys
raw = sys.argv[1].strip().lower()
slug = re.sub(r"[^a-z0-9._-]+", "-", raw).strip("-._")
print((slug or "work")[:48])' "$1"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --repo) REPO="${2:-}"; [ -n "$REPO" ] || { echo "--repo requires value" >&2; exit 2; }; shift ;;
    --repo=*) REPO="${1#--repo=}" ;;
    --base) BASE="${2:-}"; [ -n "$BASE" ] || { echo "--base requires value" >&2; exit 2; }; shift ;;
    --base=*) BASE="${1#--base=}" ;;
    --session-id) SESSION_ID="${2:-}"; [ -n "$SESSION_ID" ] || { echo "--session-id requires value" >&2; exit 2; }; shift ;;
    --session-id=*) SESSION_ID="${1#--session-id=}" ;;
    --slug) SLUG="${2:-}"; [ -n "$SLUG" ] || { echo "--slug requires value" >&2; exit 2; }; shift ;;
    --slug=*) SLUG="${1#--slug=}" ;;
    --switch) SWITCH=true ;;
    --allow-dirty) ALLOW_DIRTY=true ;;
    --json) JSON=true ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

if [ ! -d "$REPO/.git" ]; then
  echo "Not a git repository: $REPO" >&2
  exit 2
fi
REPO_ABS="$(cd "$REPO" && pwd -P)"

if [ -z "$SESSION_ID" ]; then
  if command -v uuidgen >/dev/null 2>&1; then
    SESSION_ID="$(uuidgen | tr '[:upper:]' '[:lower:]' | cut -c1-8)"
  else
    SESSION_ID="$(date +%s)-$$"
  fi
fi
SESSION_ID="$(slugify "$SESSION_ID")"
SLUG="$(slugify "$SLUG")"
BRANCH="session/${SESSION_ID}-${SLUG}"

if [ "$ALLOW_DIRTY" != true ] && [ -n "$(git -C "$REPO_ABS" status --porcelain=v1 --untracked-files=all)" ]; then
  echo "Refusing to create/switch session branch with a dirty worktree." >&2
  echo "Preserve or commit current WIP first, or pass --allow-dirty intentionally." >&2
  exit 3
fi

if ! git -C "$REPO_ABS" rev-parse --verify --quiet "$BASE^{commit}" >/dev/null; then
  echo "Base ref does not resolve to a commit: $BASE" >&2
  exit 2
fi
BASE_SHA="$(git -C "$REPO_ABS" rev-parse "$BASE^{commit}")"
ACTION="exists"
if ! git -C "$REPO_ABS" show-ref --verify --quiet "refs/heads/$BRANCH"; then
  git -C "$REPO_ABS" branch "$BRANCH" "$BASE_SHA"
  ACTION="created"
fi

if [ "$SWITCH" = true ]; then
  git -C "$REPO_ABS" switch "$BRANCH" >/dev/null
  ACTION="${ACTION}_switched"
fi

if [ "$JSON" = true ]; then
  printf '{"status":"PASS","action":%s,"repo":%s,"branch":%s,"base":%s,"base_sha":%s}\n' \
    "$(json_escape "$ACTION")" \
    "$(json_escape "$REPO_ABS")" \
    "$(json_escape "$BRANCH")" \
    "$(json_escape "$BASE")" \
    "$(json_escape "$BASE_SHA")"
else
  echo "Status: PASS"
  echo "Action: $ACTION"
  echo "Repo: $REPO_ABS"
  echo "Branch: $BRANCH"
  echo "Base: $BASE ($BASE_SHA)"
fi
