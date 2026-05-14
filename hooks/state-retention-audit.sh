#!/usr/bin/env bash
# SCOPE: os-only
# state-retention-audit.sh — ADR-199 retention drift monitor.
# Read-only by default; use scripts/state_retention_audit.py --reap --execute for
# operator-approved cleanup.

set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"
SCRIPT="$PROJECT_DIR/scripts/state_retention_audit.py"

[ -x "$SCRIPT" ] || exit 0
python3 "$SCRIPT" --project-dir "$PROJECT_DIR" --reap 2>&1 | head -40 || true
exit 0
