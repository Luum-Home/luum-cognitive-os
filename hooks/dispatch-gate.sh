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

# ─── Circuit breaker check ────────────────────────────────────────────────────

CB_BLOCKED=$(python3 -c "
import sys, os
sys.path.insert(0, os.environ.get('CLAUDE_PROJECT_DIR', '.'))
try:
    from lib.circuit_breaker import CircuitBreaker
    from lib.record_completion import classify_task_type
    desc = os.environ.get('_DISPATCH_DESC', 'general')
    task_type = classify_task_type(desc)
    cb = CircuitBreaker()
    if not cb.can_launch(task_type):
        print(f'OPEN:{task_type}')
    else:
        print('OK')
except Exception:
    print('OK')
" 2>/dev/null || echo "OK")

if [[ "$CB_BLOCKED" == OPEN:* ]]; then
    BLOCKED_TYPE="${CB_BLOCKED#OPEN:}"
    _log_event "circuit_open"
    echo "DISPATCH GATE: Circuit breaker OPEN for '${BLOCKED_TYPE}' tasks. Cooldown in effect." >&2
    echo "  Too many consecutive failures for this task type. Wait for cooldown or run different task type." >&2
    exit 2
fi

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

# Model recommendation (advisory, never blocks)
MODEL_ADVICE=$(python3 -c "
import sys, os
sys.path.insert(0, os.environ.get('CLAUDE_PROJECT_DIR', '.'))
try:
    from lib.dispatch_model_advisor import recommend_model, format_model_advice
    desc = '''${_STDIN_JSON:-{}}'''
    import json
    d = json.loads(desc) if desc.strip() else {}
    task_desc = d.get('tool_input', {}).get('description', d.get('tool_input', {}).get('prompt', '')[:100])
    rec = recommend_model(task_desc)
    print(format_model_advice(rec))
except Exception:
    print('')
" 2>/dev/null || echo "")

echo "DISPATCH GATE: Slot ${NEXT}/${MAX_AGENTS} allocated.${MODEL_ADVICE:+ $MODEL_ADVICE}" >&2
_log_event "allow"
exit 0
