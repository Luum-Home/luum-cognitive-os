#!/usr/bin/env bash
# SCOPE: project
# cos-postgres-local.sh — Manage a local PostgreSQL cluster for Cognitive OS.
#
# Uses pg_ctl to manage a local cluster in .cognitive-os/runtime/postgres-data/.
# The cluster is initialised on first run (--init or implicit on --start).
# If pg_ctl is not installed, the script exits 2 (graceful skip) — no system
# packages are installed by this script.
#
# Usage:
#   cos-postgres-local.sh             # start daemon (idempotent; inits on first run)
#   cos-postgres-local.sh --init      # initialise data dir only (does not start)
#   cos-postgres-local.sh --start     # start daemon (idempotent)
#   cos-postgres-local.sh --stop      # stop daemon (fast mode)
#   cos-postgres-local.sh --status    # print running state
#
# Port: 5433 (avoids collision with system Postgres on 5432).
#   Override via POSTGRES_LOCAL_PORT env var.
#
# Data dir:  .cognitive-os/runtime/postgres-data/
# PID file:  .cognitive-os/runtime/postgres.pid
# Port file: .cognitive-os/runtime/postgres.port
# Log file:  .cognitive-os/runtime/postgres-local.log
#
# Metrics: appends to .cognitive-os/metrics/postgres-health.jsonl
#
# ADR-045: PostgreSQL local daemon — extract from docker (D34)

set -uo pipefail

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}"
RUNTIME_DIR="$PROJECT_DIR/.cognitive-os/runtime"
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
DATA_DIR="$RUNTIME_DIR/postgres-data"
PID_FILE="$RUNTIME_DIR/postgres.pid"
PORT_FILE="$RUNTIME_DIR/postgres.port"
LOG_FILE="$RUNTIME_DIR/postgres-local.log"
LOCKDIR="$RUNTIME_DIR/postgres-local.lockdir"

DEFAULT_PORT="${POSTGRES_LOCAL_PORT:-5433}"

mkdir -p "$RUNTIME_DIR" "$METRICS_DIR"

# ── Detect pg_ctl binary ────────────────────────────────────────────────────
_pgctl_binary() {
    if command -v pg_ctl >/dev/null 2>&1; then
        echo "pg_ctl"
    else
        # Homebrew locations
        for pg_ver in 17 16 15 14; do
            local candidate="/opt/homebrew/opt/postgresql@${pg_ver}/bin/pg_ctl"
            if [ -x "$candidate" ]; then
                echo "$candidate"
                return
            fi
            candidate="/usr/local/opt/postgresql@${pg_ver}/bin/pg_ctl"
            if [ -x "$candidate" ]; then
                echo "$candidate"
                return
            fi
        done
        echo ""
    fi
}

PGCTL_BIN="$(_pgctl_binary)"

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
p = Path(project_dir) / ".cognitive-os" / "metrics" / "postgres-health.jsonl"
p.parent.mkdir(parents=True, exist_ok=True)
record = {
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "source": "cos-postgres-local",
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
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null
}

# ── Check if our daemon is alive ────────────────────────────────────────────
_daemon_alive() {
    if [ ! -f "$PID_FILE" ]; then return 1; fi
    local pid
    pid=$(cat "$PID_FILE" 2>/dev/null || echo "")
    [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

# ── --init ──────────────────────────────────────────────────────────────────
_init() {
    if [ -z "$PGCTL_BIN" ]; then
        echo "[cos-postgres-local] DETECT: pg_ctl not found in PATH or Homebrew." >&2
        echo "[cos-postgres-local] Install via: brew install postgresql@17" >&2
        _emit_metric "binary-not-found" "warn" "pg_ctl not installed" "none"
        exit 2
    fi

    if [ -d "$DATA_DIR/global" ]; then
        echo "[cos-postgres-local] Data dir $DATA_DIR already initialised — skipping initdb." >&2
        return 0
    fi

    echo "[cos-postgres-local] Initialising PostgreSQL cluster at $DATA_DIR ..." >&2

    # Use initdb directly for better control over locale/encoding
    local initdb_bin
    initdb_bin="$(dirname "$PGCTL_BIN")/initdb"
    if [ ! -x "$initdb_bin" ]; then
        echo "[cos-postgres-local] ERROR: initdb not found at $initdb_bin" >&2
        exit 1
    fi

    "$initdb_bin" \
        -D "$DATA_DIR" \
        --encoding=UTF8 \
        --locale=C \
        --auth=trust \
        --username="${POSTGRES_LOCAL_USER:-$(whoami)}" \
        >> "$LOG_FILE" 2>&1

    local rc=$?
    if [ "$rc" -ne 0 ]; then
        echo "[cos-postgres-local] ERROR: initdb failed (exit $rc). Check log: $LOG_FILE" >&2
        _emit_metric "init-failed" "error" "initdb exit $rc" "none"
        exit 1
    fi

    _emit_metric "initialized" "info" "cluster initialised at $DATA_DIR" "none"
    echo "[cos-postgres-local] Cluster initialised." >&2
}

# ── --status ────────────────────────────────────────────────────────────────
_status() {
    if _daemon_alive; then
        local pid port
        pid=$(cat "$PID_FILE")
        port=$(cat "$PORT_FILE" 2>/dev/null || echo "?")
        echo "[cos-postgres-local] RUNNING  pid=$pid  port=$port  data=$DATA_DIR"
    else
        echo "[cos-postgres-local] STOPPED"
    fi
}

# ── --stop ──────────────────────────────────────────────────────────────────
_stop() {
    if ! _daemon_alive; then
        echo "[cos-postgres-local] Not running — nothing to stop." >&2
        rm -f "$PID_FILE" "$PORT_FILE"
        exit 0
    fi
    local pid port
    pid=$(cat "$PID_FILE")
    port=$(cat "$PORT_FILE" 2>/dev/null || echo "?")
    echo "[cos-postgres-local] Stopping daemon pid=$pid port=$port ..." >&2

    if [ -n "$PGCTL_BIN" ] && [ -d "$DATA_DIR" ]; then
        "$PGCTL_BIN" stop -D "$DATA_DIR" -m fast >> "$LOG_FILE" 2>&1 || true
    fi

    # Wait up to 10s for clean shutdown
    local waited=0
    while kill -0 "$pid" 2>/dev/null && [ "$waited" -lt 100 ]; do
        sleep 0.1
        waited=$((waited + 1))
    done
    if kill -0 "$pid" 2>/dev/null; then
        kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$PID_FILE" "$PORT_FILE"
    _emit_metric "stopped" "info" "daemon stopped" "$port"
    echo "[cos-postgres-local] Daemon stopped." >&2
    exit 0
}

# ── --start (default) ───────────────────────────────────────────────────────
_start() {
    # Binary check — graceful detection, no installation
    if [ -z "$PGCTL_BIN" ]; then
        echo "[cos-postgres-local] DETECT: pg_ctl not found." >&2
        echo "[cos-postgres-local] Install via: brew install postgresql@17" >&2
        echo "[cos-postgres-local] Skipping local daemon start. PostgreSQL will use Docker or be unavailable." >&2
        _emit_metric "binary-not-found" "warn" "pg_ctl not installed" "none"
        exit 2
    fi

    # Single-instance guard (atomic mkdir lock)
    if ! mkdir "$LOCKDIR" 2>/dev/null; then
        echo "[cos-postgres-local] Another start is in progress — exiting." >&2
        exit 0
    fi
    trap 'rmdir "$LOCKDIR" 2>/dev/null || true' EXIT

    # Idempotent: if our daemon is already alive, report and exit
    if _daemon_alive; then
        local pid port
        pid=$(cat "$PID_FILE")
        port=$(cat "$PORT_FILE" 2>/dev/null || echo "?")
        echo "[cos-postgres-local] Already running pid=$pid port=$port — nothing to do." >&2
        exit 0
    fi

    # Remove stale PID/port files
    rm -f "$PID_FILE" "$PORT_FILE"

    # Initialise data dir if needed
    if [ ! -d "$DATA_DIR/global" ]; then
        _init
    fi

    # Port selection: prefer POSTGRES_LOCAL_PORT env var, then 5433, then 5434.
    local chosen_port=""
    local candidates=("$DEFAULT_PORT" 5434)

    for candidate in "${candidates[@]}"; do
        if ! _port_in_use "$candidate"; then
            chosen_port="$candidate"
            break
        else
            echo "[cos-postgres-local] Port $candidate is already bound — trying next." >&2
        fi
    done

    if [ -z "$chosen_port" ]; then
        echo "[cos-postgres-local] All candidate ports (${candidates[*]}) are in use. Cannot start local daemon." >&2
        _emit_metric "port-conflict" "warn" "all candidate ports in use" "none"
        exit 1
    fi

    echo "[cos-postgres-local] Starting PostgreSQL on 127.0.0.1:$chosen_port ..." >&2

    "$PGCTL_BIN" start \
        -D "$DATA_DIR" \
        -l "$LOG_FILE" \
        -o "-p $chosen_port -h 127.0.0.1" \
        >> "$LOG_FILE" 2>&1

    local rc=$?
    if [ "$rc" -ne 0 ]; then
        echo "[cos-postgres-local] ERROR: pg_ctl start failed (exit $rc). Check log: $LOG_FILE" >&2
        _emit_metric "start-failed" "error" "pg_ctl exit $rc" "$chosen_port"
        exit 1
    fi

    # Retrieve PID from postmaster.pid
    local waited=0
    while [ ! -f "$DATA_DIR/postmaster.pid" ] && [ "$waited" -lt 50 ]; do
        sleep 0.1
        waited=$((waited + 1))
    done

    local daemon_pid=""
    if [ -f "$DATA_DIR/postmaster.pid" ]; then
        daemon_pid=$(head -1 "$DATA_DIR/postmaster.pid")
    fi

    # Verify TCP reachable (up to 10s)
    local ready=0
    waited=0
    while [ "$waited" -lt 100 ]; do
        if _port_in_use "$chosen_port"; then
            ready=1
            break
        fi
        sleep 0.1
        waited=$((waited + 1))
    done

    if [ "$ready" -eq 0 ]; then
        echo "[cos-postgres-local] ERROR: daemon started but port $chosen_port not reachable after 10s. Check log: $LOG_FILE" >&2
        _emit_metric "start-failed" "error" "port not reachable after 10s" "$chosen_port"
        exit 1
    fi

    # Write PID and port files for client discovery
    echo "${daemon_pid:-unknown}" > "$PID_FILE"
    echo "$chosen_port" > "$PORT_FILE"

    _emit_metric "started" "info" "local cluster started via pg_ctl" "$chosen_port"
    echo "[cos-postgres-local] Daemon started. pid=${daemon_pid:-?} port=$chosen_port data=$DATA_DIR" >&2
}

# ── Dispatch ────────────────────────────────────────────────────────────────
case "${1:-}" in
    --init)   _init ;;
    --stop)   _stop ;;
    --status) _status ;;
    --start|"") _start ;;
    *)
        echo "Usage: $0 [--init|--start|--stop|--status]" >&2
        exit 1
        ;;
esac
