#!/usr/bin/env bash
# SCOPE: os-only
# ADR-182: release all branch locks held by this session on Stop.
set -uo pipefail
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${COGNITIVE_OS_PROJECT_DIR:-$(pwd)}}"
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COS_ROOT="$(cd "$HOOK_DIR/.." && pwd)"
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-${CODEX_SESSION_ID:-${CLAUDE_SESSION_ID:-unknown}}}"
[ -f "$COS_ROOT/scripts/cos_branch_lock.py" ] || exit 0
python3 "$COS_ROOT/scripts/cos_branch_lock.py" --project-dir "$PROJECT_DIR" --session-id "$SESSION_ID" release-all >/dev/null 2>&1 || true
exit 0
