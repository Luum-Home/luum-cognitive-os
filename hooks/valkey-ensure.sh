#!/usr/bin/env bash
# SCOPE: both
# valkey-ensure.sh — SessionStart hook
#
# If ORCHESTRATOR_MODE=executor is set, ensure Valkey is reachable before the
# session starts. Falls back gracefully — FallbackBus handles the degraded path.
#
# Strategy (ADR-042 — local daemon preferred):
#   1. Check TCP localhost:6379  (covers Docker Valkey OR local daemon on 6379)
#   2. If reachable: log and exit 0
#   3. If not reachable:
#      a. Try local daemon via cos-valkey-local.sh (prefers localhost, no Docker needed)
#      b. Re-check 6379 AND 6380 (local daemon may have started on 6380)
#      c. If still not reachable: try orb start + docker start (legacy Docker path)
#      d. Re-check TCP
#   4. If still not reachable: log warning. NEVER block the session —
#      agent_bus.py activates FallbackBus (file-based) automatically.
#
# When ORCHESTRATOR_MODE != executor: exit 0 silently (no OrbStack side-effects).
#
# Metrics emitted to .cognitive-os/metrics/valkey-health.jsonl:
#   event_type: reachable | local-daemon-started | docker-started | degraded
#   source: valkey-ensure

set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

# ── Guard: only act in executor mode ────────────────────────────────
MODE="${ORCHESTRATOR_MODE:-}"
if [ "$MODE" != "executor" ]; then
    exit 0
fi

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}"
VALKEY_HOST="${VALKEY_HOST:-127.0.0.1}"
VALKEY_PORT="${VALKEY_PORT:-6379}"
LOCAL_DAEMON_SCRIPT="$PROJECT_DIR/scripts/cos-valkey-local.sh"

# ── TCP probe (stdlib Python, portable, 0.5s timeout) ───────────────
_is_reachable() {
    local host="${1:-$VALKEY_HOST}"
    local port="${2:-$VALKEY_PORT}"
    python3 - "$host" "$port" <<'PYEOF'
import socket, sys
host, port = sys.argv[1], int(sys.argv[2])
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(0.5)
try:
    s.connect((host, port))
    s.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
PYEOF
}

# ── Probe both standard ports (6379 and 6380) ───────────────────────
_any_port_reachable() {
    _is_reachable "$VALKEY_HOST" 6379 || _is_reachable "$VALKEY_HOST" 6380
}

# ── Emit a MetricEvent to valkey-health.jsonl ────────────────────────
_emit_event() {
    local event_type="$1"
    local severity="${2:-info}"
    local detail="${3:-}"
    python3 - "$PROJECT_DIR" "$event_type" "$severity" "$detail" <<'PYEOF'
import sys, os
from pathlib import Path
project_dir, event_type, severity, detail = sys.argv[1:5]
try:
    sys.path.insert(0, project_dir)
    from lib.metric_event import MetricEvent, append_event
    p = Path(project_dir) / ".cognitive-os" / "metrics" / "valkey-health.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    ev = MetricEvent(
        source="valkey-ensure",
        event_type=event_type,
        severity=severity,
        payload={"detail": detail},
    )
    append_event(str(p), ev)
except Exception:
    pass  # Never let metric emission block the session
PYEOF
}

# ── Step 1: fast reachability check ─────────────────────────────────
if _is_reachable "$VALKEY_HOST" "$VALKEY_PORT"; then
    _emit_event "reachable" "info" "already up on $VALKEY_PORT"
    echo "[valkey-ensure] Valkey reachable at ${VALKEY_HOST}:${VALKEY_PORT}" >&2
    exit 0
fi

echo "[valkey-ensure] Valkey not reachable on port $VALKEY_PORT — attempting start..." >&2

# ── Step 2a: local daemon (ADR-042 — preferred over Docker) ─────────
if [ -x "$LOCAL_DAEMON_SCRIPT" ]; then
    echo "[valkey-ensure] Trying local daemon via cos-valkey-local.sh ..." >&2
    # exit 2 means binary not found — skip silently
    if bash "$LOCAL_DAEMON_SCRIPT" 2>/dev/null; then
        if _any_port_reachable; then
            _emit_event "local-daemon-started" "info" "started via cos-valkey-local.sh"
            echo "[valkey-ensure] Local daemon started successfully." >&2
            exit 0
        fi
    fi
fi

# ── Step 2b: orb start (if OrbStack installed) ───────────────────────
if command -v orb >/dev/null 2>&1; then
    orb start >/dev/null 2>&1 || true
    sleep 1
fi

# ── Step 2c: docker start for known container names (legacy path) ────
if command -v docker >/dev/null 2>&1; then
    for name in valkey cognitive-os-valkey; do
        docker start "$name" >/dev/null 2>&1 || true
    done
    sleep 1
fi

# ── Step 3: re-check after all start attempts ────────────────────────
if _any_port_reachable; then
    _emit_event "docker-started" "info" "auto-started via orb/docker"
    echo "[valkey-ensure] Valkey started via Docker/OrbStack." >&2
    exit 0
fi

# ── Step 4: graceful degradation — FallbackBus handles it ────────────
_emit_event "degraded" "warn" "unreachable after all start attempts; FallbackBus active"
echo "[valkey-ensure] Valkey unreachable after all start attempts — continuing with FallbackBus" >&2
exit 0  # NEVER block the session
