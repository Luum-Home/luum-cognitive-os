#!/usr/bin/env bash
# Shared local daemon probes. Callers provide PID_FILE in their environment.

_port_in_use() {
    local port="$1"
    python3 - "$port" <<'PY' 2>/dev/null
import socket
import sys

port = int(sys.argv[1])
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(0.3)
try:
    s.connect(("127.0.0.1", port))
    s.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
PY
}

_daemon_alive() {
    if [ ! -f "$PID_FILE" ]; then return 1; fi
    local pid
    pid=$(cat "$PID_FILE" 2>/dev/null || echo "")
    [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}
