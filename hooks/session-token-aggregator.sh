#!/usr/bin/env bash
# SCOPE: os-only
# Stop hook: aggregate real token usage from the session transcript and append
# a cost event (is_estimate: false, source: "transcript") to cost-events.jsonl.
#
# Async-safe: runs in the background after session end. Dedup is handled in
# the Python script -- repeated fires for the same session are no-ops.
# @on-demand: Stop-hook telemetry runs only when the harness supplies a session
# transcript; synthetic behavior coverage lives in tests/behavior/test_aggregate_session_tokens.py.
#
# Killswitch: honours DISABLE_HOOK_SESSION_TOKEN_AGGREGATOR=1 for emergency
# suppression (e.g. when running integration tests against fixture transcripts).

set -uo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

[ "${DISABLE_HOOK_SESSION_TOKEN_AGGREGATOR:-}" = "1" ] && exit 0

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"
SCRIPT="$PROJECT_DIR/scripts/aggregate_session_tokens.py"

[ -f "$SCRIPT" ] || exit 0
command -v python3 >/dev/null 2>&1 || exit 0

cd "$PROJECT_DIR" 2>/dev/null || exit 0

python3 "$SCRIPT" >&2 || true
exit 0
