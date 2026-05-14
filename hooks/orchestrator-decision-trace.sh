#!/usr/bin/env bash
# SCOPE: os-only
# PostToolUse hook: Orchestrator Decision Trace
#
# Fires on every Agent tool call and cross-references the agent prompt against
# the most-recent skill-suggestion entry for this session. Records whether the
# orchestrator followed, declined, or received no skill suggestion.
#
# Event:  PostToolUse
# Matcher: Agent
# Type:   command
# Async:  true
# Exit:   always 0
#
# Output: .cognitive-os/metrics/orchestrator-decision-trace.jsonl
# Schema: {ts, session_id, agent_prompt_hash, suggested_skill,
#          suggested_confidence, agent_subagent_type,
#          agent_description_short, decision, reason}
#
# Killswitch env: DISABLE_HOOK_ORCHESTRATOR_DECISION_TRACE=1
#
# Latency budget: <100ms.

source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"
_HOOK_NAME="orchestrator-decision-trace"
source "$(dirname "$0")/_lib/common.sh"

# Always exit 0 — this hook is observability-only
trap 'exit 0' ERR

check_disabled_env "orchestrator-decision-trace"
check_private_mode

# Only fire for Agent tool calls
read_stdin_json
TOOL_NAME=$(stdin_field '.tool_name' '')
[ "$TOOL_NAME" = "Agent" ] || exit 0

# Skip if python3 or jq not available
if ! command -v python3 >/dev/null 2>&1 || ! command -v jq >/dev/null 2>&1; then
  exit 0
fi

_SESSION_ID="${COGNITIVE_OS_SESSION_ID:-${CLAUDE_SESSION_ID:-unknown}}"

# Extract agent fields from stdin JSON
_AGENT_SUBAGENT_TYPE=$(echo "$_STDIN_JSON" | jq -r '.tool_input.subagent_type // empty' 2>/dev/null || true)
_AGENT_DESCRIPTION=$(echo "$_STDIN_JSON" | jq -r '.tool_input.description // empty' 2>/dev/null || true)
_AGENT_PROMPT=$(echo "$_STDIN_JSON" | jq -r '.tool_input.prompt // .tool_input.task // empty' 2>/dev/null || true)

# Trim description to 120 chars for the log
_AGENT_DESC_SHORT="${_AGENT_DESCRIPTION:0:120}"

# Pass data via env to Python to avoid shell injection
PROJECT_DIR="$_PROJECT_DIR" \
  _ODT_SESSION="$_SESSION_ID" \
  _ODT_SUBAGENT_TYPE="$_AGENT_SUBAGENT_TYPE" \
  _ODT_DESC_SHORT="$_AGENT_DESC_SHORT" \
  _ODT_PROMPT="$_AGENT_PROMPT" \
  python3 - <<'PYEOF' 2>/dev/null || true
import os
import sys
import json
import hashlib
import datetime

project = os.environ.get("PROJECT_DIR", ".")
sys.path.insert(0, project)

session_id    = os.environ.get("_ODT_SESSION", "unknown")
subagent_type = os.environ.get("_ODT_SUBAGENT_TYPE", "")
desc_short    = os.environ.get("_ODT_DESC_SHORT", "")
agent_prompt  = os.environ.get("_ODT_PROMPT", "")

prompt_hash = hashlib.sha256(agent_prompt.encode()).hexdigest()[:16] if agent_prompt else "empty"

# Read the most-recent skill-suggestion entry for this session or within last 5 min
metrics_dir = os.path.join(project, ".cognitive-os", "metrics")
suggestion_log = os.path.join(metrics_dir, "skill-suggestion.jsonl")

suggested_skill = None
suggested_confidence = None
recent_invoke_command = None

if os.path.exists(suggestion_log):
    now = datetime.datetime.now(datetime.timezone.utc)
    cutoff = now - datetime.timedelta(minutes=5)
    last_entry = None
    try:
        with open(suggestion_log) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                # Match by session or by recency (within 5 min)
                ts_str = e.get("ts", "")
                try:
                    ts = datetime.datetime.fromisoformat(ts_str)
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=datetime.timezone.utc)
                except Exception:
                    ts = None
                if e.get("session_id") == session_id or (ts and ts >= cutoff):
                    if e.get("threshold_met"):
                        last_entry = e
    except Exception:
        pass

    if last_entry:
        suggested_skill      = last_entry.get("skill_name")
        suggested_confidence = last_entry.get("confidence")
        recent_invoke_command = last_entry.get("invoke_command")

# Heuristic decision detection
if suggested_skill is None:
    decision = "no_suggestion"
    reason = None
else:
    # Match: agent prompt contains the invoke_command string, OR
    #        agent description mentions skill name
    combined = (agent_prompt + " " + desc_short).lower()
    invoke_lc = (recent_invoke_command or "").lower()
    skill_lc  = (suggested_skill or "").lower()

    if invoke_lc and invoke_lc in combined:
        decision = "matched"
        reason = f"agent prompt contains '{recent_invoke_command}'"
    elif skill_lc and skill_lc in combined:
        decision = "matched"
        reason = f"agent description mentions '{suggested_skill}'"
    else:
        decision = "declined"
        reason = "agent prompt does not reference suggested skill"

entry = {
    "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "session_id": session_id,
    "agent_prompt_hash": prompt_hash,
    "suggested_skill": suggested_skill,
    "suggested_confidence": suggested_confidence,
    "agent_subagent_type": subagent_type,
    "agent_description_short": desc_short,
    "decision": decision,
    "reason": reason,
}

os.makedirs(metrics_dir, exist_ok=True)
trace_log = os.path.join(metrics_dir, "orchestrator-decision-trace.jsonl")
with open(trace_log, "a") as f:
    f.write(json.dumps(entry) + "\n")
PYEOF

exit 0
