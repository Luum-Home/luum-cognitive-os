#!/usr/bin/env bash
# SCOPE: both
# Safe no-rebase git synchronization for scripts.
# Default policy: fetch, fast-forward if possible, block divergence with diagnosis.
set -euo pipefail

REPO=""
REMOTE="origin"
BRANCH=""
ALLOW_MERGE=false
JSON=false

usage() {
  cat <<'EOF'
Usage: bash scripts/cos-git-sync.sh --repo PATH [--remote origin] [--branch BRANCH] [--merge] [--json]

Safe script-level git sync policy:
  1. git fetch REMOTE BRANCH
  2. if fast-forward is possible: git merge --ff-only REMOTE/BRANCH
  3. if local already contains remote: report up-to-date/local-ahead
  4. if histories diverged: block by default with diagnostic
  5. --merge explicitly permits a merge commit for divergence

This script never rebases and never force-pushes.
EOF
}

json_escape() {
  python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$1"
}

emit_json() {
  local status="$1" action="$2" repo="$3" branch="$4" remote_ref="$5" local_sha="$6" remote_sha="$7" base_sha="$8" message="$9"
  printf '{"status":%s,"action":%s,"repo":%s,"branch":%s,"remote_ref":%s,"local_sha":%s,"remote_sha":%s,"merge_base":%s,"message":%s}\n' \
    "$(json_escape "$status")" \
    "$(json_escape "$action")" \
    "$(json_escape "$repo")" \
    "$(json_escape "$branch")" \
    "$(json_escape "$remote_ref")" \
    "$(json_escape "$local_sha")" \
    "$(json_escape "$remote_sha")" \
    "$(json_escape "$base_sha")" \
    "$(json_escape "$message")"
}

emit_text() {
  local status="$1" action="$2" repo="$3" branch="$4" remote_ref="$5" local_sha="$6" remote_sha="$7" base_sha="$8" message="$9"
  echo "Status: $status"
  echo "Action: $action"
  echo "Repo: $repo"
  echo "Branch: $branch"
  echo "Remote ref: $remote_ref"
  echo "Local: $local_sha"
  echo "Remote: $remote_sha"
  echo "Merge-base: $base_sha"
  echo "$message"
}

emit() {
  if [ "$JSON" = true ]; then
    emit_json "$@"
  else
    emit_text "$@"
  fi
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --repo)
      REPO="${2:-}"; [ -n "$REPO" ] || { echo "--repo requires value" >&2; exit 2; }; shift ;;
    --repo=*) REPO="${1#--repo=}" ;;
    --remote)
      REMOTE="${2:-}"; [ -n "$REMOTE" ] || { echo "--remote requires value" >&2; exit 2; }; shift ;;
    --remote=*) REMOTE="${1#--remote=}" ;;
    --branch)
      BRANCH="${2:-}"; [ -n "$BRANCH" ] || { echo "--branch requires value" >&2; exit 2; }; shift ;;
    --branch=*) BRANCH="${1#--branch=}" ;;
    --merge) ALLOW_MERGE=true ;;
    --json) JSON=true ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

if [ -z "$REPO" ]; then
  echo "--repo is required" >&2
  usage >&2
  exit 2
fi
if [ ! -d "$REPO/.git" ]; then
  echo "Not a git repository: $REPO" >&2
  exit 2
fi

REPO_ABS="$(cd "$REPO" && pwd -P)"
if [ -z "$BRANCH" ]; then
  BRANCH="$(git -C "$REPO_ABS" branch --show-current 2>/dev/null || true)"
fi
if [ -z "$BRANCH" ]; then
  echo "Cannot infer branch for detached repository; pass --branch" >&2
  exit 2
fi

REMOTE_REF="refs/remotes/$REMOTE/$BRANCH"

git -C "$REPO_ABS" fetch "$REMOTE" "$BRANCH" --quiet

LOCAL_SHA="$(git -C "$REPO_ABS" rev-parse HEAD)"
REMOTE_SHA="$(git -C "$REPO_ABS" rev-parse "$REMOTE_REF")"
BASE_SHA="$(git -C "$REPO_ABS" merge-base HEAD "$REMOTE_REF")"

if [ "$LOCAL_SHA" = "$REMOTE_SHA" ]; then
  emit "PASS" "none" "$REPO_ABS" "$BRANCH" "$REMOTE_REF" "$LOCAL_SHA" "$REMOTE_SHA" "$BASE_SHA" "Already synchronized."
  exit 0
fi

if git -C "$REPO_ABS" merge-base --is-ancestor HEAD "$REMOTE_REF"; then
  git -C "$REPO_ABS" merge --ff-only "$REMOTE_REF" --quiet
  NEW_SHA="$(git -C "$REPO_ABS" rev-parse HEAD)"
  emit "PASS" "fast-forward" "$REPO_ABS" "$BRANCH" "$REMOTE_REF" "$LOCAL_SHA" "$REMOTE_SHA" "$BASE_SHA" "Fast-forwarded to $NEW_SHA."
  exit 0
fi

if git -C "$REPO_ABS" merge-base --is-ancestor "$REMOTE_REF" HEAD; then
  emit "WARN" "local-ahead" "$REPO_ABS" "$BRANCH" "$REMOTE_REF" "$LOCAL_SHA" "$REMOTE_SHA" "$BASE_SHA" "Local branch already contains remote and has extra commits; no pull/rebase performed."
  exit 0
fi

if [ "$ALLOW_MERGE" = true ]; then
  git -C "$REPO_ABS" merge --no-edit "$REMOTE_REF"
  NEW_SHA="$(git -C "$REPO_ABS" rev-parse HEAD)"
  emit "PASS" "merge" "$REPO_ABS" "$BRANCH" "$REMOTE_REF" "$LOCAL_SHA" "$REMOTE_SHA" "$BASE_SHA" "Divergence resolved with explicit merge commit $NEW_SHA."
  exit 0
fi

emit "BLOCK" "diverged" "$REPO_ABS" "$BRANCH" "$REMOTE_REF" "$LOCAL_SHA" "$REMOTE_SHA" "$BASE_SHA" "Local and remote histories diverged. No rebase was performed. Re-run with --merge to create an explicit merge commit, or resolve manually."
exit 3
