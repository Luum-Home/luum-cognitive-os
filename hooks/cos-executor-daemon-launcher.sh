#!/usr/bin/env bash
# SCOPE: os-only
# cos-executor-daemon-launcher.sh — SessionStart hook: start cos-executor daemon (ADR-034).
# Renamed from cos-executor-heartbeat.sh (v0.15): this script launches a daemon, not a heartbeat.
# Backwards-compat symlink: hooks/cos-executor-heartbeat.sh -> cos-executor-daemon-launcher.sh
#
# Starts scripts/cos-executor.py --daemon once per project. Single-instance
# guard is inside the Python daemon itself (cos-executor.pid file).
# On first run, also exports ORCHESTRATOR_MODE=executor for this session's
# banner detection via .cognitive-os/runtime/orchestrator-mode.

set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}"
DAEMON="$PROJECT_DIR/scripts/cos-executor.py"
RUNTIME_DIR="$PROJECT_DIR/.cognitive-os/runtime"
mkdir -p "$RUNTIME_DIR"

# Graceful degradation: missing script is not an error at session start.
if [ ! -f "$DAEMON" ]; then
  exit 0
fi

# Python must be available. If not, silently skip — this is advisory infra.
if ! command -v python3 >/dev/null 2>&1; then
  exit 0
fi

# Start (idempotent — cos-executor.py --daemon no-ops if pid file valid).
python3 "$DAEMON" --daemon >/dev/null 2>&1 || true

echo "[cos-executor-heartbeat] daemon ensured (ADR-034 live streaming)" >&2
exit 0
