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

_emit_local_service_metric() {
    local metric_file="$1"
    local metric_source="$2"
    local event_type="$3"
    local severity="${4:-info}"
    local detail="${5:-}"
    local port="${6:-unknown}"
    python3 - "$PROJECT_DIR" "$metric_file" "$metric_source" "$event_type" "$severity" "$detail" "$port" <<'PY' 2>/dev/null || true
import json
import sys
import time
from pathlib import Path

project_dir, metric_file, metric_source, event_type, severity, detail, port = sys.argv[1:8]
p = Path(project_dir) / ".cognitive-os" / "metrics" / metric_file
p.parent.mkdir(parents=True, exist_ok=True)
record = {
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "source": metric_source,
    "event_type": event_type,
    "severity": severity,
    "connection_type": "local-daemon",
    "port": int(port) if port.isdigit() else port,
    "detail": detail,
}
with p.open("a", encoding="utf-8") as handle:
    handle.write(json.dumps(record) + "\n")
PY
}
