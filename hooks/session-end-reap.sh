#!/usr/bin/env bash
# SCOPE: os-only
# session-end-reap.sh — Stop hook: invoke so-reaper at session end (ADR-028 D1.B)
#
# Registered under the Stop matcher in the default and full efficiency profiles.
# Calls so-reaper.sh which runs cleanup_expired() + detect_orphans() via the
# Python process registry.  Errors are swallowed so a reaper failure never
# breaks the session-end chain.

set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}"

bash "$PROJECT_DIR/scripts/so-reaper.sh" 2>&1 || true

exit 0
