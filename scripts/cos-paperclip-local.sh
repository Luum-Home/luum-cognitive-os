#!/usr/bin/env bash
# SCOPE: project
# cos-paperclip-local.sh — Start/stop a local Paperclip daemon for Cognitive OS.
#
# Paperclip is a Node.js-based agent coordination platform. This script
# manages a local instance when the `paperclip` binary (or `npx paperclip`)
# is installed. If neither is found, the script exits 2 (graceful skip) —
# no system packages are installed by this script.
#
# Usage:
#   cos-paperclip-local.sh           # start daemon (idempotent)
#   cos-paperclip-local.sh --stop    # stop daemon
#   cos-paperclip-local.sh --status  # print running state
#
# Port selection:
#   Tries 3200 first (Paperclip default). If already bound, falls back to
#   3201. The chosen port is written to the PID file's companion .port file
#   so other scripts and paperclip_client.py can discover it.
#
# PID file:  .cognitive-os/runtime/paperclip.pid
# Port file: .cognitive-os/runtime/paperclip.port
#
# Metrics: appends to .cognitive-os/metrics/paperclip-health.jsonl
#
# ADR-043: Paperclip local daemon — extract from docker (D34 partial)

set -uo pipefail

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}"
RUNTIME_DIR="$PROJECT_DIR/.cognitive-os/runtime"
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
PID_FILE="$RUNTIME_DIR/paperclip.pid"
PORT_FILE="$RUNTIME_DIR/paperclip.port"
LOG_FILE="$RUNTIME_DIR/paperclip-local.log"
LOCKDIR="$RUNTIME_DIR/paperclip-local.lockdir"

mkdir -p "$RUNTIME_DIR" "$METRICS_DIR"

# ── Detect server binary ────────────────────────────────────────────────────
_server_binary() {
    if command -v paperclip >/dev/null 2>&1; then
        echo "paperclip"
    elif command -v npx >/dev/null 2>&1 && npx --yes paperclip --version >/dev/null 2>&1; then
        echo "npx paperclip"
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
p = Path(project_dir) / ".cognitive-os" / "metrics" / "paperclip-health.jsonl"
p.parent.mkdir(parents=True, exist_ok=True)
record = {
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "source": "cos-paperclip-local",
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
_port_in_use() {
    local port="$1"
    python3 -c "
import socket, sys
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(0.3)
try:
    s.connect(('127.0.0.1', $port))
    s.close()
    sys.exit(0)   # port is reachable
except Exception:
    sys.exit(1)   # port not in use
" 2>/dev/null
}

# ── Check if our daemon is alive ────────────────────────────────────────────
_daemon_alive() {
    if [ ! -f "$PID_FILE" ]; then return 1; fi
    local pid
    pid=$(cat "$PID_FILE" 2>/dev/null || echo "")
    [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

# ── --status ────────────────────────────────────────────────────────────────
_status() {
    if _daemon_alive; then
        local pid port
        pid=$(cat "$PID_FILE")
        port=$(cat "$PORT_FILE" 2>/dev/null || echo "?")
        echo "[cos-paperclip-local] RUNNING  pid=$pid  port=$port  binary=${SERVER_BIN:-unknown}"
    else
        echo "[cos-paperclip-local] STOPPED"
    fi
}

# ── --stop ──────────────────────────────────────────────────────────────────
_stop() {
    if ! _daemon_alive; then
        echo "[cos-paperclip-local] Not running — nothing to stop." >&2
        rm -f "$PID_FILE" "$PORT_FILE"
        exit 0
    fi
    local pid port
    pid=$(cat "$PID_FILE")
    port=$(cat "$PORT_FILE" 2>/dev/null || echo "?")
    echo "[cos-paperclip-local] Stopping daemon pid=$pid port=$port ..." >&2
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
    echo "[cos-paperclip-local] Daemon stopped." >&2
    exit 0
}

# ── --start (default) ───────────────────────────────────────────────────────
_start() {
    # Binary check — graceful detection, no installation
    if [ -z "$SERVER_BIN" ]; then
        echo "[cos-paperclip-local] DETECT: paperclip binary not found (not in PATH, not via npx)." >&2
        echo "[cos-paperclip-local] Install via: npm install -g @paperclip-ai/paperclip  OR  npx @paperclip-ai/paperclip" >&2
        echo "[cos-paperclip-local] Skipping local daemon start. Dashboard will use Docker or be unavailable." >&2
        _emit_metric "binary-not-found" "warn" "paperclip binary not installed" "none"
        exit 2
    fi

    # Single-instance guard (atomic mkdir lock)
    if ! mkdir "$LOCKDIR" 2>/dev/null; then
        echo "[cos-paperclip-local] Another start is in progress — exiting." >&2
        exit 0
    fi
    trap 'rmdir "$LOCKDIR" 2>/dev/null || true' EXIT

    # Idempotent: if our daemon is already alive, report and exit
    if _daemon_alive; then
        local pid port
        pid=$(cat "$PID_FILE")
        port=$(cat "$PORT_FILE" 2>/dev/null || echo "?")
        echo "[cos-paperclip-local] Already running pid=$pid port=$port — nothing to do." >&2
        exit 0
    fi

    # Remove stale PID/port files
    rm -f "$PID_FILE" "$PORT_FILE"

    # Port selection: prefer PAPERCLIP_LOCAL_PORT env var, then 3200, then 3201.
    local preferred_port="${PAPERCLIP_LOCAL_PORT:-}"
    local chosen_port=""
    local candidates=()
    if [ -n "$preferred_port" ]; then
        candidates=("$preferred_port" 3200 3201)
    else
        candidates=(3200 3201)
    fi

    for candidate in "${candidates[@]}"; do
        if ! _port_in_use "$candidate"; then
            chosen_port="$candidate"
            break
        else
            echo "[cos-paperclip-local] Port $candidate is already bound — trying next." >&2
        fi
    done

    if [ -z "$chosen_port" ]; then
        echo "[cos-paperclip-local] All candidate ports (${candidates[*]}) are in use. Cannot start local daemon." >&2
        _emit_metric "port-conflict" "warn" "all candidate ports in use" "none"
        exit 1
    fi

    echo "[cos-paperclip-local] Starting $SERVER_BIN on 127.0.0.1:$chosen_port ..." >&2

    # Launch Paperclip daemon in background; write PID manually since Paperclip
    # does not support --pidfile natively.
    PAPERCLIP_PORT="$chosen_port" \
    PAPERCLIP_HOST="127.0.0.1" \
    PAPERCLIP_DEPLOYMENT_MODE="${PAPERCLIP_DEPLOYMENT_MODE:-authenticated}" \
    PAPERCLIP_DEPLOYMENT_EXPOSURE="private" \
    PAPERCLIP_HOME="${PAPERCLIP_HOME:-$PROJECT_DIR/.cognitive-os/runtime/paperclip-data}" \
        $SERVER_BIN \
        > "$LOG_FILE" 2>&1 &

    local daemon_pid="$!"
    echo "$daemon_pid" > "$PID_FILE"

    # Verify TCP reachable (up to 15s — Node.js startup is slower than redis)
    local ready=0
    local waited=0
    while [ "$waited" -lt 150 ]; do
        if _port_in_use "$chosen_port"; then
            ready=1
            break
        fi
        # Check process is still alive
        if ! kill -0 "$daemon_pid" 2>/dev/null; then
            echo "[cos-paperclip-local] ERROR: daemon process exited prematurely. Check log: $LOG_FILE" >&2
            rm -f "$PID_FILE"
            _emit_metric "start-failed" "error" "process exited prematurely" "$chosen_port"
            exit 1
        fi
        sleep 0.1
        waited=$((waited + 1))
    done

    if [ "$ready" -eq 0 ]; then
        echo "[cos-paperclip-local] ERROR: daemon started but port $chosen_port not reachable after 15s. Check log: $LOG_FILE" >&2
        kill "$daemon_pid" 2>/dev/null || true
        rm -f "$PID_FILE"
        _emit_metric "start-failed" "error" "port not reachable after 15s" "$chosen_port"
        exit 1
    fi

    # Write port file for client discovery
    echo "$chosen_port" > "$PORT_FILE"

    _emit_metric "started" "info" "local daemon started via $SERVER_BIN" "$chosen_port"
    echo "[cos-paperclip-local] Daemon started. pid=$daemon_pid port=$chosen_port binary=$SERVER_BIN" >&2
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
