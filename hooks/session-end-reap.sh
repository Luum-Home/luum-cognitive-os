#!/usr/bin/env bash
# session-end-reap.sh — Stop hook: invoke so-reaper at session end (ADR-028 D1.B)
#
# Registered under the Stop matcher in the default and full efficiency profiles.
# Calls so-reaper.sh which runs cleanup_expired() + detect_orphans() via the
# Python process registry.  Errors are swallowed so a reaper failure never
# breaks the session-end chain.

set -uo pipefail

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}"

bash "$PROJECT_DIR/scripts/so-reaper.sh" 2>&1 || true

exit 0
