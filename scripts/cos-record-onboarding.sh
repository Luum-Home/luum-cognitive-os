#!/usr/bin/env bash
# SCOPE: os-only
# cos-record-onboarding.sh — Drive the M2 onboarding walkthrough non-interactively.
#
# Designed to be wrapped by `asciinema rec` so the operator can capture a
# reproducible recording of the fresh-clone → first-skill flow without typing
# each step. Each step has a guarded prompt-style header so the resulting
# .cast file looks like a paced human session, not a unattended script.
#
# Usage:
#   asciinema rec docs/05-Methodology/onboarding/walkthrough.cast \
#     --command "bash scripts/cos-record-onboarding.sh"
#
# Or interactively:
#   bash scripts/cos-record-onboarding.sh
#
# After recording: upload the .cast or convert via `agg` to GIF.
# The operator may also publish to asciinema.org and link from README.md.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PAUSE_BEFORE_STEP="${COS_RECORD_PAUSE:-1.5}"

_say() {
  printf '\n\033[1;36m# %s\033[0m\n' "$*"
  sleep "$PAUSE_BEFORE_STEP"
}

_run() {
  printf '\033[1;33m$ %s\033[0m\n' "$*"
  sleep 0.5
  bash -c "$*" 2>&1 | sed 's/^/  /'
  echo
}

cd "$REPO_ROOT"

_say "Step 1 — verify install"
_run "bash scripts/cos-status.sh 2>&1 | head -20 || true"

_say "Step 2 — list available skills"
_run "ls .claude/skills 2>/dev/null | head -10 || ls packages/*/skills | head -10"

_say "Step 3 — sample a skill (verification-before-completion)"
_run "find . -path '*/skills/verification-before-completion/SKILL.md' -not -path './.git/*' 2>/dev/null | head -1 | xargs head -10 2>/dev/null"

_say "Step 4 — show hook chain"
_run "ls hooks/*.sh 2>/dev/null | head -10"

_say "Step 5 — dry-run a destructive op (gets blocked)"
_run "git push --force 2>&1 | head -5 || true"

_say "Step 6 — view the readiness checklist"
_run "head -20 docs/09-Quality/legal/pre-public-readiness-checklist.md"

_say "Step 7 — show CONTRIBUTING for AI policy"
_run "head -15 CONTRIBUTING.md"

_say "Step 8 — license + FAQ link"
_run "head -2 LICENSE; echo '---'; grep 'license-faq' README.md | head -1"

_say "Walkthrough complete. See docs/05-Methodology/onboarding/walkthrough.md for the prose version."
