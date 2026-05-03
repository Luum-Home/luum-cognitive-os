#!/usr/bin/env bash
# SCOPE: os-only
# cos-pr-review.sh — local replacement for claude-pr-review.yml.
#
# Per ADR-131. Captures the diff and metadata for a PR, generates a review
# prompt the operator can paste into a Claude Code session (or process via a
# local agent), and optionally posts the resulting review back to the PR via
# `gh pr comment`.
#
# Usage:
#   bash scripts/cos-pr-review.sh prep <PR>
#       Prepares review inputs at .cognitive-os/pr-review/<PR>/.
#       Writes diff.patch, metadata.json, and review-prompt.md.
#       Prints next-step instructions.
#
#   bash scripts/cos-pr-review.sh post <PR> <review-file>
#       Posts <review-file> as a comment on the PR via `gh pr comment`.
#       Asks for confirmation first.
#
#   bash scripts/cos-pr-review.sh paths <PR>
#       Prints the on-disk paths used by prep/post for this PR.
#
# This script does NOT call any external LLM API. The maintainer drives the
# analysis through their existing Claude Code session, then posts the review
# back manually with the `post` subcommand. Aligns with ADR-131's decision to
# keep the per-PR review cost at zero by relying on the maintainer's existing
# IDE session rather than an API-billed action runner.

set -euo pipefail

REPO_ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

ACTION="${1:-}"
PR="${2:-}"

review_dir() {
  local pr="$1"
  echo "$REPO_ROOT/.cognitive-os/pr-review/$pr"
}

require_pr() {
  if [ -z "$PR" ]; then
    echo "ERROR: PR number required" >&2
    echo "Usage: $0 $ACTION <PR>" >&2
    exit 2
  fi
}

require_gh() {
  if ! command -v gh >/dev/null 2>&1; then
    echo "ERROR: gh CLI not installed (brew install gh)" >&2
    exit 2
  fi
}

cmd_prep() {
  require_pr
  require_gh

  local dir
  dir="$(review_dir "$PR")"
  mkdir -p "$dir"

  echo "[cos-pr-review] capturing PR #$PR into $dir"

  gh pr view "$PR" --json \
      number,title,author,baseRefName,headRefName,body,files,additions,deletions,changedFiles,labels \
      > "$dir/metadata.json"

  gh pr diff "$PR" > "$dir/diff.patch"

  local title author base head
  title="$(jq -r '.title' "$dir/metadata.json")"
  author="$(jq -r '.author.login' "$dir/metadata.json")"
  base="$(jq -r '.baseRefName' "$dir/metadata.json")"
  head="$(jq -r '.headRefName' "$dir/metadata.json")"
  local additions deletions changed
  additions="$(jq -r '.additions' "$dir/metadata.json")"
  deletions="$(jq -r '.deletions' "$dir/metadata.json")"
  changed="$(jq -r '.changedFiles' "$dir/metadata.json")"

  cat > "$dir/review-prompt.md" <<EOF
# PR #$PR review — $title

**Author:** $author
**Base:** $base ← **Head:** $head
**Diff:** $additions additions, $deletions deletions across $changed files

## Files changed
$(jq -r '.files[] | "- \(.path) (+\(.additions)/-\(.deletions))"' "$dir/metadata.json")

## Review prompt

You are an SR reviewer for the Cognitive OS project. Review the diff at
\`$dir/diff.patch\` and the PR body below. Focus on:

1. **Architecture compliance** — clean architecture, correct layers, no
   broken-window patterns, no scope creep.
2. **Security implications** — credential exposure, injection risks,
   destructive ops without confirmation, any of the OWASP top 10.
3. **Quality gates** — tests present and behavioral (not structural-only),
   docs updated where claims change, no committed TODOs.
4. **Scope proportionality** — do the changes match the stated task size,
   or is there hidden refactor / dead code / unrelated edits.

Produce findings with severity tiers: **BLOCKER**, **CONCERN**, **SUGGESTION**,
**QUESTION**. At least one finding is required — "looks good" is not an
acceptable review. End with a one-line verdict.

## PR body

$(jq -r '.body // ""' "$dir/metadata.json")

EOF

  cat <<EOF

[cos-pr-review] prep complete.

  Inputs:
    diff:       $dir/diff.patch
    metadata:   $dir/metadata.json
    prompt:     $dir/review-prompt.md

  Next step:
    1. Open $dir/review-prompt.md in your Claude Code session.
    2. Paste the review prompt + diff and produce the review.
    3. Save your review to $dir/review.md.
    4. Post it: bash scripts/cos-pr-review.sh post $PR $dir/review.md

EOF
}

cmd_post() {
  require_pr
  require_gh

  local file="${3:-${REVIEW_FILE:-}}"
  # Allow positional or env, since shell argv parsing is awkward here.
  if [ -z "${file:-}" ]; then
    file="$(review_dir "$PR")/review.md"
  fi

  if [ ! -f "$file" ]; then
    echo "ERROR: review file not found: $file" >&2
    echo "Run \`$0 prep $PR\` first, then save your review at $(review_dir "$PR")/review.md" >&2
    exit 1
  fi

  echo "About to post the following review to PR #$PR:"
  echo "  File: $file"
  echo "  Size: $(wc -c < "$file") bytes"
  echo
  echo "─── preview (first 30 lines) ───"
  head -30 "$file"
  echo "─── /preview ───"
  echo
  read -r -p "Post this comment to PR #$PR? [y/N] " confirm
  case "$confirm" in
    y|Y|yes|Yes)
      gh pr comment "$PR" --body-file "$file"
      echo "[cos-pr-review] posted to PR #$PR"
      ;;
    *)
      echo "[cos-pr-review] aborted; review file remains at $file"
      exit 0
      ;;
  esac
}

cmd_paths() {
  require_pr
  local dir
  dir="$(review_dir "$PR")"
  echo "  diff:     $dir/diff.patch"
  echo "  metadata: $dir/metadata.json"
  echo "  prompt:   $dir/review-prompt.md"
  echo "  review:   $dir/review.md (you write this)"
}

case "$ACTION" in
  prep)  cmd_prep ;;
  post)  cmd_post "$@" ;;
  paths) cmd_paths ;;
  ""|-h|--help|help)
    sed -n '/^# Usage:/,/^# This script/p' "$0" | sed 's/^# //; s/^#$//'
    exit 0
    ;;
  *)
    echo "Unknown subcommand: $ACTION" >&2
    echo "Usage: $0 [prep|post|paths] <PR>" >&2
    exit 2
    ;;
esac
