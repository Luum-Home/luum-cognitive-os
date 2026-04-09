#!/usr/bin/env bash
# CONCERNS: concurrency, resource-protection, workload-scheduling
# Dispatch Gate — controls agent launch concurrency.
# PreToolUse hook on Agent.
# Blocks (exit 2) when max_parallel_agents slots are all in use.
# Must run BEFORE rate-limiter.sh and agent-prelaunch.sh.
set -uo pipefail

source "$(dirname "$0")/_lib/common.sh"

# Only fires on Agent launches
require_tool "Agent" "task" "delegate"

# Skip in private mode
check_private_mode

# ─── Read config ──────────────────────────────────────────────────────────────

MAX_AGENTS=$(python3 -c "
import yaml, os, sys
cfg_path = os.path.join(os.environ.get('CLAUDE_PROJECT_DIR', '.'), 'cognitive-os.yaml')
try:
    with open(cfg_path) as f:
        cfg = yaml.safe_load(f) or {}
    print(cfg.get('resources', {}).get('compute', {}).get('max_parallel_agents', 5))
except Exception:
    print(5)
" 2>/dev/null || echo 5)

# ─── Count in_progress agents ─────────────────────────────────────────────────

ACTIVE=$(python3 -c "
import json, os
tasks_path = os.path.join(
    os.environ.get('CLAUDE_PROJECT_DIR', '.'),
    '.cognitive-os/tasks/active-tasks.json'
)
try:
    with open(tasks_path) as f:
        data = json.load(f)
    count = sum(1 for t in data.get('tasks', []) if t.get('status') == 'in_progress')
    print(count)
except Exception:
    print(0)
" 2>/dev/null || echo 0)

# ─── Log helper ───────────────────────────────────────────────────────────────

_log_event() {
    local action="$1"
    local metrics_dir="$_PROJECT_DIR/.cognitive-os/metrics"
    mkdir -p "$metrics_dir" 2>/dev/null || true
    local ts
    ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || echo "unknown")
    # Extract short description from stdin JSON if available
    local desc
    desc=$(echo "${_STDIN_JSON:-{}}" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    prompt = d.get('tool_input', {}).get('prompt', '') or d.get('tool_input', {}).get('description', '')
    print(prompt[:100].replace('\"','\\\\\"'))
except Exception:
    print('')
" 2>/dev/null || echo "")
    printf '{"timestamp":"%s","active":%s,"max":%s,"action":"%s","description":"%s"}\n' \
        "$ts" "$ACTIVE" "$MAX_AGENTS" "$action" "$desc" \
        >> "$metrics_dir/dispatch-gate.jsonl" 2>/dev/null || true
}

# ─── Decision ─────────────────────────────────────────────────────────────────

if [ "$ACTIVE" -ge "$MAX_AGENTS" ] 2>/dev/null; then
    _log_event "block"
    cat >&2 <<EOF
DISPATCH GATE: Agent launch blocked (${ACTIVE}/${MAX_AGENTS} slots in use).
Task queued. Will launch when a slot frees up.
EOF
    exit 2
fi

# Slots available — allow the launch
NEXT=$((ACTIVE + 1))
echo "DISPATCH GATE: Slot ${NEXT}/${MAX_AGENTS} allocated." >&2
_log_event "allow"
exit 0
