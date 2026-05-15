#!/usr/bin/env bash
# SCOPE: os-only
# Stop hook: run the Pyrefly pilot as an advisory signal after significant Python changes.
# Advisory only: exits 0 unless COS_PYREFLY_ENFORCE=1 is explicitly set for the runner.

set -uo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"
SCRIPT="$PROJECT_DIR/scripts/cos-pyrefly-pilot"

[ -x "$SCRIPT" ] || exit 0
command -v git >/dev/null 2>&1 || exit 0

cd "$PROJECT_DIR" 2>/dev/null || exit 0

# Run only when the current worktree has meaningful first-party Python changes.
changed_files="$(git diff --name-only -- '*.py' 2>/dev/null; git diff --cached --name-only -- '*.py' 2>/dev/null)"
changed_files="$(printf '%s
' "$changed_files" | sort -u | grep -E '^(lib|scripts|packages/agent-service/src)/.*\.py$' || true)"
[ -n "$changed_files" ] || exit 0

# Optional cooldown: avoid repeated Stop-hook reports during tight loops.
REPORT_DIR="$PROJECT_DIR/.cognitive-os/reports/pyrefly"
STATE_DIR="$PROJECT_DIR/.cognitive-os/state"
STAMP="$STATE_DIR/pyrefly-stop-advisory.last"
mkdir -p "$REPORT_DIR" "$STATE_DIR" 2>/dev/null || true
now="$(date +%s)"
cooldown="${COS_PYREFLY_STOP_COOLDOWN_SECONDS:-300}"
if [ -f "$STAMP" ]; then
  last="$(cat "$STAMP" 2>/dev/null || echo 0)"
  case "$last" in ''|*[!0-9]*) last=0 ;; esac
  if [ $((now - last)) -lt "$cooldown" ]; then
    exit 0
  fi
fi
printf '%s
' "$now" > "$STAMP" 2>/dev/null || true

printf 'PYREFLY_ADVISORY_STOP: Python changes detected; running advisory type-check.
' >&2
printf '%s
' "$changed_files" | sed 's/^/  - /' >&2

COS_PYREFLY_PRINT_REPORT=0 bash "$SCRIPT" --summary-only >&2 || true
exit 0
