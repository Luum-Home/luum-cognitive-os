#!/usr/bin/env bash
# valkey-ensure.sh — SessionStart hook
#
# If ORCHESTRATOR_MODE=executor is set, ensure Valkey is reachable before the
# session starts. Falls back gracefully — FallbackBus handles the degraded path.
#
# Strategy:
#   1. Check TCP localhost:6379 (500ms timeout)
#   2. If reachable: log and exit 0
#   3. If not reachable:
#      a. Try `orb start` (starts OrbStack if installed but not running)
#      b. Try `docker start valkey` + `docker start langfuse-valkey`
#      c. Re-check TCP
#   4. If still not reachable: log warning. NEVER block the session —
#      agent_bus.py activates FallbackBus (file-based) automatically.
#
# When ORCHESTRATOR_MODE != executor: exit 0 silently (no OrbStack side-effects).
#
# Metrics emitted to .cognitive-os/metrics/valkey-health.jsonl:
#   event_type: reachable | started | degraded
#   source: valkey-ensure

set -uo pipefail

# ── Guard: only act in executor mode ────────────────────────────────
MODE="${ORCHESTRATOR_MODE:-}"
if [ "$MODE" != "executor" ]; then
    exit 0
fi

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}"
VALKEY_HOST="${VALKEY_HOST:-127.0.0.1}"
VALKEY_PORT="${VALKEY_PORT:-6379}"

# ── TCP probe (stdlib Python, portable, 0.5s timeout) ───────────────
_is_reachable() {
    python3 - "$VALKEY_HOST" "$VALKEY_PORT" <<'PYEOF'
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
if _is_reachable; then
    _emit_event "reachable" "info" "already up"
    echo "[valkey-ensure] Valkey reachable at ${VALKEY_HOST}:${VALKEY_PORT}" >&2
    exit 0
fi

echo "[valkey-ensure] Valkey not reachable — attempting start..." >&2

# ── Step 2a: orb start (if OrbStack installed) ───────────────────────
if command -v orb >/dev/null 2>&1; then
    orb start >/dev/null 2>&1 || true
    # Give OrbStack a moment to boot the VM
    sleep 1
fi

# ── Step 2b: docker start for known container names ──────────────────
if command -v docker >/dev/null 2>&1; then
    for name in valkey langfuse-valkey; do
        docker start "$name" >/dev/null 2>&1 || true
    done
    # Brief wait for container readiness
    sleep 1
fi

# ── Step 3: re-check after start attempts ────────────────────────────
if _is_reachable; then
    _emit_event "started" "info" "auto-started via orb/docker"
    echo "[valkey-ensure] Valkey started successfully at ${VALKEY_HOST}:${VALKEY_PORT}" >&2
    exit 0
fi

# ── Step 4: graceful degradation — FallbackBus handles it ────────────
_emit_event "degraded" "warn" "unreachable after start attempt; FallbackBus active"
echo "[valkey-ensure] Valkey unreachable after start attempts — continuing with FallbackBus" >&2
exit 0  # NEVER block the session
