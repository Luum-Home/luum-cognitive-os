#!/usr/bin/env bash
# SCOPE: os-only
# PostToolUse hook: normalize tool output into ACI observations and trajectory rows.

set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_lib/common.sh"
check_private_mode
check_disabled_env "aci-observation-capture"

command -v python3 >/dev/null 2>&1 || exit 0
command -v jq >/dev/null 2>&1 || exit 0
read_stdin_json
[ -z "$_STDIN_JSON" ] && exit 0

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
METRICS_DIR="$(resolve_session_dir)"
ACI_FILE="$METRICS_DIR/aci-observations.jsonl"
TRAJECTORY_FILE="$METRICS_DIR/agent-trajectory.jsonl"
ARTIFACT_DIR="$ROOT/.cognitive-os/artifacts/aci"
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-${CLAUDE_SESSION_ID:-${PPID:-0}}}"
TASK_ID="${COS_TASK_ID:-session-$SESSION_ID}"

PAYLOAD_JSON="$_STDIN_JSON" PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}" python3 - "$ACI_FILE" "$TRAJECTORY_FILE" "$ARTIFACT_DIR" "$SESSION_ID" "$TASK_ID" <<'PY'
import json
import os
import sys
from lib.aci_observation import normalize_observation
from lib.agent_trajectory import append_trajectory, event_from_aci
from lib.metric_event import MetricEvent, append_event

aci_file, trajectory_file, artifact_dir, session_id, task_id = sys.argv[1:6]
payload = json.loads(os.environ.get("PAYLOAD_JSON") or "{}")
tool = str(payload.get("tool_name") or payload.get("tool") or "unknown")
tool_input = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
response = payload.get("tool_response")
if isinstance(response, dict):
    output = response.get("content") or response.get("output") or response.get("text") or json.dumps(response, sort_keys=True)
    exit_code = int(response.get("exit_code", 0) or 0)
elif isinstance(response, list):
    output = "\n".join(str(item.get("text", item)) if isinstance(item, dict) else str(item) for item in response)
    exit_code = 0
else:
    output = "" if response is None else str(response)
    exit_code = int(payload.get("exit_code", 0) or 0)
obs = normalize_observation(
    tool=tool,
    command=str(tool_input.get("command", "")),
    output=output,
    exit_code=exit_code,
    artifact_dir=artifact_dir,
)
obs_dict = obs.to_dict()
append_event(aci_file, MetricEvent(source="aci-observation-capture", event_type="aci.observation", severity="info" if obs.status == "success" else "warn", payload=obs_dict))
append_trajectory(trajectory_file, event_from_aci(obs_dict, session_id=session_id, task_id=task_id))
PY

exit 0
