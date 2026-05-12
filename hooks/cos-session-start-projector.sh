#!/usr/bin/env bash
# SCOPE: os-only
# ADR-275 — Wrapper invoking scripts/cos-session-start-projector (Python).
# SessionStart hook. Non-blocking; projector exits 0 always.

set -uo pipefail

_HOOK_NAME="cos-session-start-projector"

# Kill-switch + disable-env honour (consistent with other SO hooks)
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh" 2>/dev/null || true
type check_disabled_env >/dev/null 2>&1 && check_disabled_env "$_HOOK_NAME"

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"

# Python projector emits to stderr by default; the wrapper just delegates.
# Exits 0 on success or absence of the projector (silent no-op).
if [ -x "$PROJECT_DIR/scripts/cos-session-start-projector" ]; then
  exec python3 "$PROJECT_DIR/scripts/cos-session-start-projector"
fi
exit 0
