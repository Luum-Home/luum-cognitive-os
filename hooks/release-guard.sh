#!/usr/bin/env bash
# SCOPE: both
# release-guard.sh — PreToolUse hook on Bash
#
# Detects manual release patterns (echo > VERSION, git tag v*, manual version
# bumps) and blocks them, directing the user to `cos release` instead.
#
# Why: `cos release` automatically updates VERSION, CHANGELOG.md, docs/00-MOCs/entrypoints/INDEX.md,
# creates the git tag, and triggers auto-update of registered projects. Manual
# releases skip these steps, causing test failures and version inconsistencies.
#
# Type: PreToolUse (Bash)
# Exit: 0 = pass, 2 = block
set -euo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"
[ -f "$(dirname "${BASH_SOURCE[0]}")/_lib/governance-policy.sh" ] && source "$(dirname "${BASH_SOURCE[0]}")/_lib/governance-policy.sh"
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${COGNITIVE_OS_PROJECT_DIR:-$(pwd)}}"

# Read tool input from stdin
input=$(cat)
command=$(echo "$input" | jq -r '.tool_input.command // ""' 2>/dev/null || true)

[ -z "$command" ] && exit 0

# Extract only the FIRST line of the command to avoid matching heredoc content,
# commit messages, or multi-line strings that happen to contain "VERSION".
first_line=$(echo "$command" | head -1)

# ── Pattern 1: Writing directly to VERSION file ─────────────────────
# Matches: echo "0.3.4" > VERSION, printf "1.0" > VERSION, etc.
if echo "$first_line" | grep -qE '(echo|printf|cat|tee)\s+.*>\s*VERSION($|\s)'; then
  if type cos_governance_policy_allows_block >/dev/null 2>&1 && ! cos_governance_policy_allows_block release; then
    cos_governance_policy_advisory_message "release-guard" "release"
    exit 0
  fi
  echo "BLOCKED: Manual VERSION file modification detected." >&2
  echo "" >&2
  echo "  Use \`cos release --patch|--minor|--major\` instead." >&2
  echo "  It updates VERSION + CHANGELOG.md + docs/00-MOCs/entrypoints/INDEX.md + git tag + auto-update." >&2
  exit 2
fi

# ── Pattern 2: Manual git tag with version pattern ──────────────────
# Matches: git tag v0.3.4, git tag 1.0.0, etc.
# Does NOT match: git tag -d, git tag -l, or tags inside commit messages.
if echo "$first_line" | grep -qE '^git\s+tag\s+v?[0-9]+\.[0-9]+'; then
  if type cos_governance_policy_allows_block >/dev/null 2>&1 && ! cos_governance_policy_allows_block release; then
    cos_governance_policy_advisory_message "release-guard" "release"
    exit 0
  fi
  echo "BLOCKED: Manual git tag creation detected." >&2
  echo "" >&2
  echo "  Use \`cos release --patch|--minor|--major\` instead." >&2
  echo "  It creates the tag after updating all version references." >&2
  exit 2
fi

# ── Pattern 3: sed/perl modifying VERSION file directly ─────────────
if echo "$first_line" | grep -qE "^(sed|perl)\s.*\bVERSION\b"; then
  if type cos_governance_policy_allows_block >/dev/null 2>&1 && ! cos_governance_policy_allows_block release; then
    cos_governance_policy_advisory_message "release-guard" "release"
    exit 0
  fi
  echo "BLOCKED: Manual VERSION file modification detected." >&2
  echo "" >&2
  echo "  Use \`cos release --patch|--minor|--major\` instead." >&2
  exit 2
fi

exit 0
