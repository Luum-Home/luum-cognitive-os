#!/usr/bin/env bash
# SCOPE: project
# cos-valkey-local.sh — Start/stop a local Valkey/Redis daemon for the Agent Bus.
#
# Prefers `valkey-server` if installed; falls back to `redis-server` (Redis is
# protocol-compatible). If neither is installed, prints a detection notice and
# exits 2 — no system packages are installed by this script.
#
# Usage:
#   cos-valkey-local.sh           # start daemon (idempotent)
#   cos-valkey-local.sh --stop    # stop daemon
#   cos-valkey-local.sh --status  # print running state
#
# Port selection:
#   Tries 6379 first. If already bound by another process (e.g. Docker Valkey),
#   falls back to 6380. The chosen port is written to the PID file's companion
#   .port file so other scripts can discover it.
#
# PID file:  .cognitive-os/runtime/valkey.pid
# Port file: .cognitive-os/runtime/valkey.port
#
# Metrics: appends to .cognitive-os/metrics/valkey-health.jsonl
#
# ADR-042: Valkey local daemon — extract from docker (D34 partial)

set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_lib/local-service.sh"

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}"
RUNTIME_DIR="$PROJECT_DIR/.cognitive-os/runtime"
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
PID_FILE="$RUNTIME_DIR/valkey.pid"
PORT_FILE="$RUNTIME_DIR/valkey.port"
LOG_FILE="$RUNTIME_DIR/valkey-local.log"
LOCKDIR="$RUNTIME_DIR/valkey-local.lockdir"

mkdir -p "$RUNTIME_DIR" "$METRICS_DIR"

# ── Detect server binary ────────────────────────────────────────────────────
_server_binary() {
    if command -v valkey-server >/dev/null 2>&1; then
        echo "valkey-server"
    elif command -v redis-server >/dev/null 2>&1; then
        echo "redis-server"
    else
        echo ""
    fi
}

SERVER_BIN="$(_server_binary)"

# ── Metric helper ───────────────────────────────────────────────────────────
_emit_metric() {
    local event_type="$1"
    local severity="${2:-info}"
    local detail="${3:-}"
    local port="${4:-unknown}"
    python3 - "$PROJECT_DIR" "$event_type" "$severity" "$detail" "$port" <<'PYEOF' 2>/dev/null || true
import sys, json, time
from pathlib import Path
project_dir, event_type, severity, detail, port = sys.argv[1:6]
p = Path(project_dir) / ".cognitive-os" / "metrics" / "valkey-health.jsonl"
p.parent.mkdir(parents=True, exist_ok=True)
record = {
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "source": "cos-valkey-local",
    "event_type": event_type,
    "severity": severity,
    "connection_type": "local-daemon",
    "port": int(port) if port.isdigit() else port,
    "detail": detail,
}
with p.open("a") as f:
    f.write(json.dumps(record) + "\n")
PYEOF
}

# ── TCP port probe ──────────────────────────────────────────────────────────

# ── Check if our daemon is alive ────────────────────────────────────────────

# ── --status ────────────────────────────────────────────────────────────────
_status() {
    if _daemon_alive; then
        local pid port
        pid=$(cat "$PID_FILE")
        port=$(cat "$PORT_FILE" 2>/dev/null || echo "?")
        echo "[cos-valkey-local] RUNNING  pid=$pid  port=$port  binary=${SERVER_BIN:-unknown}"
    else
        echo "[cos-valkey-local] STOPPED"
    fi
}

# ── --stop ──────────────────────────────────────────────────────────────────
_stop() {
    if ! _daemon_alive; then
        echo "[cos-valkey-local] Not running — nothing to stop." >&2
        rm -f "$PID_FILE" "$PORT_FILE"
        exit 0
    fi
    local pid port
    pid=$(cat "$PID_FILE")
    port=$(cat "$PORT_FILE" 2>/dev/null || echo "?")
    echo "[cos-valkey-local] Stopping daemon pid=$pid port=$port ..." >&2
    kill "$pid" 2>/dev/null || true
    # Wait up to 5s for clean shutdown
    local waited=0
    while kill -0 "$pid" 2>/dev/null && [ "$waited" -lt 50 ]; do
        sleep 0.1
        waited=$((waited + 1))
    done
    if kill -0 "$pid" 2>/dev/null; then
        kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$PID_FILE" "$PORT_FILE"
    _emit_metric "stopped" "info" "daemon stopped" "$port"
    echo "[cos-valkey-local] Daemon stopped." >&2
    exit 0
}

# ── --start (default) ───────────────────────────────────────────────────────
_start() {
    # Binary check — graceful detection, no installation
    if [ -z "$SERVER_BIN" ]; then
        echo "[cos-valkey-local] DETECT: neither valkey-server nor redis-server found." >&2
        echo "[cos-valkey-local] Install via: brew install valkey  OR  brew install redis" >&2
        echo "[cos-valkey-local] Skipping local daemon start. Agent Bus will use Docker or FallbackBus." >&2
        _emit_metric "binary-not-found" "warn" "valkey-server and redis-server not installed" "none"
        exit 2
    fi

    # Single-instance guard (atomic mkdir lock, same pattern as reaper-heartbeat.sh)
    if ! mkdir "$LOCKDIR" 2>/dev/null; then
        echo "[cos-valkey-local] Another start is in progress — exiting." >&2
        exit 0
    fi
    trap 'rmdir "$LOCKDIR" 2>/dev/null || true' EXIT

    # Idempotent: if our daemon is already alive, report and exit
    if _daemon_alive; then
        local pid port
        pid=$(cat "$PID_FILE")
        port=$(cat "$PORT_FILE" 2>/dev/null || echo "?")
        echo "[cos-valkey-local] Already running pid=$pid port=$port — nothing to do." >&2
        exit 0
    fi

    # Remove stale PID/port files
    rm -f "$PID_FILE" "$PORT_FILE"

    # Port selection: prefer VALKEY_LOCAL_PORT env var, then 6379, then 6380.
    # In test environments the caller may set VALKEY_LOCAL_PORT to an ephemeral port.
    local preferred_port="${VALKEY_LOCAL_PORT:-}"
    local chosen_port=""
    local candidates=()
    if [ -n "$preferred_port" ]; then
        candidates=("$preferred_port" 6379 6380)
    else
        candidates=(6379 6380)
    fi

    for candidate in "${candidates[@]}"; do
        if ! _port_in_use "$candidate"; then
            chosen_port="$candidate"
            break
        else
            echo "[cos-valkey-local] Port $candidate is already bound — trying next." >&2
        fi
    done

    if [ -z "$chosen_port" ]; then
        echo "[cos-valkey-local] All candidate ports (${candidates[*]}) are in use. Cannot start local daemon." >&2
        _emit_metric "port-conflict" "warn" "all candidate ports in use" "none"
        exit 1
    fi

    echo "[cos-valkey-local] Starting $SERVER_BIN on 127.0.0.1:$chosen_port ..." >&2

    # Launch daemon in background
    "$SERVER_BIN" \
        --daemonize yes \
        --bind 127.0.0.1 \
        --port "$chosen_port" \
        --logfile "$LOG_FILE" \
        --save "" \
        --appendonly no \
        --maxmemory-policy noeviction \
        --pidfile "$PID_FILE" \
        2>&1

    # Wait for PID file to appear (up to 5s)
    local waited=0
    while [ ! -f "$PID_FILE" ] && [ "$waited" -lt 50 ]; do
        sleep 0.1
        waited=$((waited + 1))
    done

    if [ ! -f "$PID_FILE" ]; then
        echo "[cos-valkey-local] ERROR: daemon did not write PID file within 5s. Check log: $LOG_FILE" >&2
        _emit_metric "start-failed" "error" "PID file not created within 5s" "$chosen_port"
        exit 1
    fi

    local pid
    pid=$(cat "$PID_FILE")

    # Verify TCP reachable
    local ready=0
    waited=0
    while [ "$waited" -lt 30 ]; do
        if _port_in_use "$chosen_port"; then
            ready=1
            break
        fi
        sleep 0.1
        waited=$((waited + 1))
    done

    if [ "$ready" -eq 0 ]; then
        echo "[cos-valkey-local] ERROR: daemon started but port $chosen_port not reachable. Check log: $LOG_FILE" >&2
        _emit_metric "start-failed" "error" "port not reachable after 3s" "$chosen_port"
        exit 1
    fi

    # Write port file for client discovery
    echo "$chosen_port" > "$PORT_FILE"

    _emit_metric "started" "info" "local daemon started via $SERVER_BIN" "$chosen_port"
    echo "[cos-valkey-local] Daemon started. pid=$pid port=$chosen_port binary=$SERVER_BIN" >&2
}

# ── Dispatch ────────────────────────────────────────────────────────────────
case "${1:-}" in
    --stop)   _stop ;;
    --status) _status ;;
    --start|"") _start ;;
    *)
        echo "Usage: $0 [--start|--stop|--status]" >&2
        exit 1
        ;;
esac
