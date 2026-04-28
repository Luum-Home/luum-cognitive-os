#!/usr/bin/env bash
# SCOPE: both
# SessionStart hook: cached host tooling doctor.
#
# This hook schedules a lightweight host tooling check without blocking agent
# startup. It is intentionally advisory: it records what is broken, but does not
# install tools, mutate user-level MCP config, or run pytest automatically.

set -uo pipefail

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"
RUNTIME_DIR="$PROJECT_DIR/.cognitive-os/runtime"
REPORT_DIR="$PROJECT_DIR/.cognitive-os/reports/host-tools"
STATE_FILE="$RUNTIME_DIR/host-tool-doctor.state.json"
LATEST_REPORT="$REPORT_DIR/latest.txt"
INTERVAL_SECONDS="${COS_HOST_TOOL_DOCTOR_INTERVAL_SECONDS:-86400}"
TIMEOUT_SECONDS="${COS_HOST_TOOL_DOCTOR_TIMEOUT_SECONDS:-30}"
PROFILE="${COS_HOST_TOOL_DOCTOR_PROFILE:-${COGNITIVE_OS_PROFILE:-default}}"

if [ "${COS_HOST_TOOL_DOCTOR_DISABLE:-0}" = "1" ]; then
  exit 0
fi

mkdir -p "$RUNTIME_DIR" "$REPORT_DIR" 2>/dev/null || exit 0

now_epoch="$(date +%s)"
last_epoch="0"
if [ -f "$STATE_FILE" ] && command -v python3 >/dev/null 2>&1; then
  last_epoch="$(python3 - "$STATE_FILE" <<'PYEOF' 2>/dev/null || echo 0
import json
import sys
from pathlib import Path

try:
    payload = json.loads(Path(sys.argv[1]).read_text())
    print(int(payload.get("last_run_epoch", 0)))
except Exception:
    print(0)
PYEOF
)"
fi

if [ "${COS_HOST_TOOL_DOCTOR_FORCE:-0}" != "1" ]; then
  age=$((now_epoch - ${last_epoch:-0}))
  if [ "$age" -ge 0 ] && [ "$age" -lt "$INTERVAL_SECONDS" ]; then
    exit 0
  fi
fi

resolve_source_root() {
  if [ -x "$PROJECT_DIR/scripts/cos-doctor-tools.sh" ]; then
    printf '%s\n' "$PROJECT_DIR"
    return 0
  fi

  if [ -f "$PROJECT_DIR/.cognitive-os/install-meta.json" ] && command -v python3 >/dev/null 2>&1; then
    python3 - "$PROJECT_DIR/.cognitive-os/install-meta.json" <<'PYEOF' 2>/dev/null
import json
import sys
from pathlib import Path

try:
    source = json.loads(Path(sys.argv[1]).read_text()).get("source", "")
except Exception:
    source = ""
if source:
    print(source)
PYEOF
  fi
}

SOURCE_ROOT="$(resolve_source_root | head -1)"
DOCTOR_SCRIPT="$SOURCE_ROOT/scripts/cos-doctor-tools.sh"

write_state() {
  local status="$1"
  local exit_code="$2"
  local message="$3"
  python3 - "$STATE_FILE" "$now_epoch" "$status" "$exit_code" "$message" "$LATEST_REPORT" <<'PYEOF' 2>/dev/null || true
import json
import sys
from pathlib import Path

state, epoch, status, exit_code, message, report = sys.argv[1:7]
Path(state).write_text(json.dumps({
    "last_run_epoch": int(epoch),
    "status": status,
    "exit_code": int(exit_code),
    "message": message,
    "report": report,
}, indent=2) + "\n")
PYEOF
}

if [ ! -x "$DOCTOR_SCRIPT" ]; then
  {
    echo "WARN host tool doctor unavailable"
    echo "project_dir=$PROJECT_DIR"
    echo "source_root=${SOURCE_ROOT:-unresolved}"
    echo "expected=$DOCTOR_SCRIPT"
  } > "$LATEST_REPORT"
  if command -v python3 >/dev/null 2>&1; then
    write_state "warning" 0 "cos-doctor-tools.sh unavailable"
  fi
  exit 0
fi

run_doctor() {
  if command -v python3 >/dev/null 2>&1; then
    python3 - "$DOCTOR_SCRIPT" "$PROJECT_DIR" "$PROFILE" "$TIMEOUT_SECONDS" "$LATEST_REPORT" "$STATE_FILE" <<'PYEOF'
import json
import os
import subprocess
import sys
import time
from pathlib import Path

doctor, project_dir, profile, timeout_s, report, state = sys.argv[1:7]
env = os.environ.copy()
env["COGNITIVE_OS_PROJECT_DIR"] = project_dir
cmd = ["bash", doctor, "--profile", profile]
started = int(time.time())

try:
    result = subprocess.run(
        cmd,
        cwd=project_dir,
        env=env,
        text=True,
        capture_output=True,
        timeout=int(timeout_s),
    )
    output = result.stdout
    if result.stderr:
        output += "\n[stderr]\n" + result.stderr
    exit_code = result.returncode
    status = "pass" if exit_code == 0 else "fail"
    message = f"cos-doctor-tools.sh exited {exit_code}"
except subprocess.TimeoutExpired as exc:
    output = (exc.stdout or "") + (exc.stderr or "")
    output += f"\nFAIL host tool doctor timed out after {timeout_s}s\n"
    exit_code = 124
    status = "timeout"
    message = f"cos-doctor-tools.sh timed out after {timeout_s}s"

Path(report).write_text(output)
Path(state).write_text(json.dumps({
    "last_run_epoch": started,
    "status": status,
    "exit_code": exit_code,
    "message": message,
    "report": report,
}, indent=2) + "\n")
PYEOF
  else
    COGNITIVE_OS_PROJECT_DIR="$PROJECT_DIR" bash "$DOCTOR_SCRIPT" --profile "$PROFILE" > "$LATEST_REPORT" 2>&1
    rc=$?
    write_state "unknown" "$rc" "python3 unavailable; state may be incomplete"
  fi
}

if [ "${COS_HOST_TOOL_DOCTOR_FOREGROUND:-0}" = "1" ]; then
  run_doctor >/dev/null 2>&1 || true
else
  (run_doctor >/dev/null 2>&1 || true) &
fi

exit 0
