#!/usr/bin/env bash
# SCOPE: both
# PURPOSE: Ensure engram serve daemon (port 7437) is running for ADR-071 lifecycle hooks
# EVENT: SessionStart
# EXIT_CODES: 0=advisory (always)
#
# ADR-071 lifecycle hooks (engram-reinforce-on-access.sh, engram-crystallize-on-session-end.sh)
# require the engram HTTP daemon at localhost:7437. If it's not running, reinforce()
# returns False silently. This launcher starts it when missing — idempotent, advisory,
# never blocks session start.
#
# Opt-out: COS_DISABLE_ENGRAM_AUTOSTART=1
# Override port: ENGRAM_PORT (defaults to 7437)
#
# Single-instance via pgrep — engram serve already refuses to bind a second time
# on the same port, so the worst case is a transient stderr message.

set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

# Opt-out
if [ "${COS_DISABLE_ENGRAM_AUTOSTART:-0}" = "1" ]; then
    exit 0
fi

# Skip if engram binary is missing (no engram = no lifecycle hooks anyway)
if ! command -v engram &>/dev/null; then
    exit 0
fi

PORT="${ENGRAM_PORT:-7437}"
PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"
RUNTIME_DIR="$PROJECT_DIR/.cognitive-os/runtime"
LOG_FILE="$RUNTIME_DIR/engram-daemon.log"

mkdir -p "$RUNTIME_DIR"

# ── Liveness probe: is the daemon already responding? ───────────────────────
if command -v curl &>/dev/null; then
    if curl -s --max-time 1 "http://127.0.0.1:${PORT}/health" 2>/dev/null | grep -q '"status":"ok"'; then
        exit 0
    fi
fi

# ── Process probe: any engram serve process running? ────────────────────────
if pgrep -f "engram serve" >/dev/null 2>&1; then
    # Process exists but health check failed — leave it alone (could be starting up)
    exit 0
fi

# ── Spawn the daemon (detached, output to log) ──────────────────────────────
nohup engram serve "$PORT" >>"$LOG_FILE" 2>&1 &
disown 2>/dev/null || true

exit 0
