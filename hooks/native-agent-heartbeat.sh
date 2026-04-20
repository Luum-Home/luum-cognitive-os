#!/usr/bin/env bash
# SCOPE: os-only
# native-agent-heartbeat.sh — PreToolUse:Agent + PostToolUse:Agent hook
#
# Bridges native Claude Code Agent tool_use events to AgentBusMetrics heartbeat
# records. Fills the gap when ORCHESTRATOR_MODE is NOT "executor" — the default
# native Agent path bypasses the executor adapter so agent-heartbeat.jsonl
# stays empty.
#
# ADR-028b D1.C — SLO 9 requires agent heartbeats; this hook provides them.
#
# Behaviour:
#   PreToolUse:Agent  — alive=True  → emits agent_launched MetricEvent
#   PostToolUse:Agent — alive=False → emits agent_completed MetricEvent
#
# The Python driver calls AgentBusMetrics.on_heartbeat_event() which handles
# deduplication (first alive=True → agent_launched; alive=False → agent_completed).

set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}"

# Read stdin into a temp file so Python can load it safely (avoids shell quoting issues)
TMP=$(mktemp /tmp/native-agent-heartbeat-XXXXXX.json)
trap 'rm -f "$TMP"' EXIT
cat > "$TMP"

python3 - "$TMP" "$PROJECT_DIR" <<'PYEOF' 2>/dev/null || true
import json, os, sys, time
from pathlib import Path

stdin_file = sys.argv[1]
project_dir = sys.argv[2]
sys.path.insert(0, project_dir)

try:
    with open(stdin_file) as f:
        data = json.load(f)
except Exception:
    data = {}

# Detect Pre vs Post: PostToolUse carries "tool_response"; PreToolUse does not
is_post = "tool_response" in data

agent_id = (
    data.get("tool_use_id")
    or data.get("tool_input", {}).get("tool_use_id")
    or "native-agent-unknown"
)
session_id = os.environ.get("COGNITIVE_OS_SESSION_ID", "")
ts = time.time()
alive = not is_post   # True on launch (Pre), False on completion (Post)

heartbeat_payload = {
    "type": "heartbeat",
    "agent_id": agent_id,
    "session_id": session_id,
    "alive": alive,
    "timestamp_epoch": ts,
    "phase": "completed" if is_post else "launched",
    "tokens_used": 0,
    "source": "native-agent-heartbeat-hook",
}

# 1. Write to FallbackBus so subscribers / scan_fallback_dir also see it
fallback_dir = Path(project_dir) / ".cognitive-os/agent-bus"
agent_dir = fallback_dir / agent_id
agent_dir.mkdir(parents=True, exist_ok=True)
hb_file = agent_dir / "heartbeat.jsonl"
with open(hb_file, "a") as fh:
    fh.write(json.dumps(heartbeat_payload) + "\n")

# 2. Fire AgentBusMetrics to emit the canonical MetricEvent to agent-heartbeat.jsonl
from lib.agent_bus_metrics import AgentBusMetrics
metrics = AgentBusMetrics(
    metrics_path=str(Path(project_dir) / ".cognitive-os/metrics/agent-heartbeat.jsonl")
)
metrics.on_heartbeat_event({
    "agent_id": agent_id,
    "session_id": session_id,
    "alive": alive,
    "timestamp_epoch": ts,
    "tokens_used": 0,
})
PYEOF

exit 0
