#!/usr/bin/env bash
# audit-consumer-dependence.sh
#
# Pre-rename safety check. Before genericizing client-coupled tokens in this
# OS repo (Tier 1-4 of the case-study leak audit), run this against each
# consumer project to confirm whether the consumer relies on the literal
# strings as they appear in OS skill output, hook detection, or workflow
# CLI examples.
#
# A non-zero match count means the consumer has tooling that greps for the
# literal token. Renaming in the OS without a deprecation alias would break
# their pipeline.
#
# Usage:
#   scripts/audit-consumer-dependence.sh <consumer-repo-path> [token-file]
#
#   <consumer-repo-path>  absolute path to the consumer project repo
#   [token-file]          optional path to newline-separated tokens to
#                         search for; defaults to the curated list below
#
# Output:
#   - Stdout: per-token match count + first 3 sample paths
#   - Exit 0: no matches (safe to rename)
#   - Exit 1: at least one match (consumer depends on token; need alias)
#   - Exit 2: usage error
#
# Notes:
#   - Uses ripgrep if available, falls back to grep -r.
#   - Skips .git, node_modules, .venv, dist, build, vendor, target.
#   - Does NOT modify the consumer repo. Read-only.

set -euo pipefail

CONSUMER_REPO="${1:-}"
TOKEN_FILE="${2:-}"

if [[ -z "$CONSUMER_REPO" ]]; then
  echo "usage: $0 <consumer-repo-path> [token-file]" >&2
  exit 2
fi

if [[ ! -d "$CONSUMER_REPO" ]]; then
  echo "error: not a directory: $CONSUMER_REPO" >&2
  exit 2
fi

# Default tokens are public-safe placeholders. For real consumer audits, pass
# a private token file with the literal strings that would break consumer tooling
# if renamed without an alias.
DEFAULT_TOKENS=(
  "consumer-alpha"
  "consumer-beta"
  "service-alpha"
  "service-beta"
  "Consumer Alpha"
  "example-services/"
  "services/example"
  "service-gamma"
  "service-alpha-go"
)
if [[ -n "$TOKEN_FILE" ]]; then
  if [[ ! -f "$TOKEN_FILE" ]]; then
    echo "error: token file not found: $TOKEN_FILE" >&2
    exit 2
  fi
  mapfile -t TOKENS < <(grep -vE '^\s*(#|$)' "$TOKEN_FILE")
else
  TOKENS=("${DEFAULT_TOKENS[@]}")
fi

# Choose grep tool.
# Paths intentionally retained as case-study material (Tier 5 of the
# pre-public-readiness audit). These files name consumer tokens deliberately
# and are not subject to scrubbing.
TIER5_RETAINED=(
  "docs/business/case-study.md"
  "docs/business/open-source-design.md"
)

is_tier5_retained() {
  local rel="${1#$CONSUMER_REPO/}"
  for keep in "${TIER5_RETAINED[@]}"; do
    [[ "$rel" == "$keep" ]] && return 0
  done
  return 1
}

if command -v rg >/dev/null 2>&1; then
  search() {
    rg --no-config --hidden \
       --glob '!.git' --glob '!node_modules' --glob '!.venv' \
       --glob '!dist' --glob '!build' --glob '!vendor' --glob '!target' \
       --fixed-strings --files-with-matches \
       "$1" "$CONSUMER_REPO" 2>/dev/null || true
  }
else
  search() {
    grep -rl --binary-files=without-match \
      --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=.venv \
      --exclude-dir=dist --exclude-dir=build --exclude-dir=vendor \
      --exclude-dir=target \
      -F "$1" "$CONSUMER_REPO" 2>/dev/null || true
  }
fi

total_matches=0
echo "consumer-repo: $CONSUMER_REPO"
echo "tokens: ${#TOKENS[@]}"
echo

for tok in "${TOKENS[@]}"; do
  [[ -z "$tok" ]] && continue
  mapfile -t raw_hits < <(search "$tok")
  hits=()
  retained=0
  for h in "${raw_hits[@]}"; do
    if is_tier5_retained "$h"; then
      retained=$((retained + 1))
    else
      hits+=("$h")
    fi
  done
  count=${#hits[@]}
  if (( count > 0 )); then
    total_matches=$((total_matches + count))
    printf 'TOKEN %-25s  %d files (+%d Tier5-retained, ignored)\n' "\"$tok\"" "$count" "$retained"
    for sample in "${hits[@]:0:3}"; do
      printf '    %s\n' "${sample#$CONSUMER_REPO/}"
    done
    if (( count > 3 )); then
      printf '    ... (+%d more)\n' "$((count - 3))"
    fi
  else
    printf 'TOKEN %-25s  0 files\n' "\"$tok\""
  fi
done

echo
if (( total_matches == 0 )); then
  echo "RESULT: SAFE — no consumer files match. Rename without alias is OK."
  exit 0
else
  echo "RESULT: DEPENDENCY DETECTED — $total_matches matches across consumer repo."
  echo "        Add a deprecation alias before removing token from OS."
  exit 1
fi
