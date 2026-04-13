#!/usr/bin/env bash
# SCOPE: both
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

# ─── Consequence Engine: DISABLE / DEGRADE check ─────────────────────────────
# Extract skill name from description field (first word is the skill slug).
SKILL_NAME=$(echo "${_STDIN_JSON:-{}}" | python3 -c "
import sys, json, re
try:
    d = json.load(sys.stdin)
    desc = d.get('tool_input', {}).get('description', '') or d.get('tool_input', {}).get('prompt', '')
    # Use first word or first slash-command as skill name
    m = re.match(r'[/]?([a-zA-Z0-9_-]+)', desc.strip())
    print(m.group(1).lower() if m else '')
except Exception:
    print('')
" 2>/dev/null || echo "")

if [ -n "$SKILL_NAME" ]; then
    # Check DISABLE — blocks launch
    DISABLED=$(python3 -c "
import sys, os
sys.path.insert(0, os.environ.get('CLAUDE_PROJECT_DIR', '.'))
try:
    from lib.consequence_engine import ConsequenceEngine
    e = ConsequenceEngine()
    print('DISABLED' if e.is_skill_disabled('$SKILL_NAME') else 'OK')
except Exception:
    print('OK')
" 2>/dev/null || echo "OK")

    if [ "$DISABLED" = "DISABLED" ]; then
        _log_event "consequence_disabled"
        echo "DISPATCH GATE: Skill '$SKILL_NAME' is DISABLED by consequence engine." >&2
        echo "  Run /optimize-skill $SKILL_NAME to fix it, then re-enable via ConsequenceEngine.re_enable_skill()." >&2
        exit 2
    fi

    # Check DEGRADE — model override advisory (non-blocking)
    MODEL_OVERRIDE=$(python3 -c "
import sys, os
sys.path.insert(0, os.environ.get('CLAUDE_PROJECT_DIR', '.'))
try:
    from lib.consequence_engine import ConsequenceEngine
    e = ConsequenceEngine()
    override = e.get_model_override('$SKILL_NAME')
    print(override if override else '')
except Exception:
    print('')
" 2>/dev/null || echo "")

    if [ -n "$MODEL_OVERRIDE" ]; then
        echo "DISPATCH GATE: Skill '$SKILL_NAME' is DEGRADED — use model '$MODEL_OVERRIDE' (one tier down)." >&2
        _log_event "consequence_degrade"
    fi
fi

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

    # ── Enqueue the blocked agent into the dispatch queue ──────────────────
    QUEUE_RESULT=$(python3 -c "
import json, sys, os
sys.path.insert(0, os.environ.get('CLAUDE_PROJECT_DIR', '.'))
try:
    from lib.queue_drainer import QueueDrainer
    stdin_raw = '''${_STDIN_JSON:-{}}'''
    try:
        d = json.loads(stdin_raw) if stdin_raw.strip() else {}
    except Exception:
        d = {}
    tool_input = d.get('tool_input', {})
    prompt = tool_input.get('prompt', '') or tool_input.get('description', '')
    description = (prompt[:100]) if prompt else 'agent task'

    # Extract model from prompt if specified, default to sonnet
    import re as _re
    model_match = _re.search(r'model[\":\s]+([a-z]+)', prompt[:200].lower())
    model = model_match.group(1) if model_match else 'sonnet'
    if model not in ('opus', 'sonnet', 'haiku'):
        model = 'sonnet'

    drainer = QueueDrainer()
    agent_id = drainer.enqueue(
        prompt=prompt,
        description=description,
        model=model,
        priority=5,
    )
    pos = drainer.position_in_queue(agent_id)
    total = drainer.queue_length(status='queued')
    print(f'{agent_id}:{pos}:{total}')
except Exception as e:
    print(f'error:{e}')
" 2>/dev/null || echo "error:python-failed")

    if [[ "$QUEUE_RESULT" == error:* ]]; then
        cat >&2 <<EOF
DISPATCH GATE: Agent launch blocked (${ACTIVE}/${MAX_AGENTS} slots in use).
  Could not enqueue: ${QUEUE_RESULT#error:}
  Agent will not be retried automatically.
EOF
    else
        QUEUE_ID="${QUEUE_RESULT%%:*}"
        REST="${QUEUE_RESULT#*:}"
        QUEUE_POS="${REST%%:*}"
        QUEUE_TOTAL="${REST##*:}"
        cat >&2 <<EOF
DISPATCH GATE: Agent launch blocked (${ACTIVE}/${MAX_AGENTS} slots in use).
  Agent enqueued — position ${QUEUE_POS} of ${QUEUE_TOTAL} in dispatch queue.
  Queue ID: ${QUEUE_ID}
  Will launch when a slot frees up. Orchestrator: check queue on next task completion.
EOF
    fi
    exit 2
fi

# Slots available — allow the launch
NEXT=$((ACTIVE + 1))

# ─── Model routing: consequence check + budget-aware directive ────────────────

MODEL_ROUTING=$(python3 -c "
import sys, os, json
sys.path.insert(0, os.environ.get('CLAUDE_PROJECT_DIR', '.'))
try:
    from lib.dispatch_model_advisor import recommend_model, format_model_directive, format_model_advice

    raw = '''${_STDIN_JSON:-{}}'''
    d = json.loads(raw) if raw.strip() else {}
    tool_input = d.get('tool_input', {})
    task_desc = (
        tool_input.get('description', '')
        or tool_input.get('prompt', '')[:200]
    )

    # Extract skill name hint from prompt (e.g. /sdd-apply or skill invocation)
    import re as _re
    skill_match = _re.search(r'skill[:\s]+([a-zA-Z0-9_-]+)', task_desc[:300])
    skill_name = skill_match.group(1) if skill_match else None

    rec = recommend_model(task_desc, skill_name=skill_name)
    directive = format_model_directive(rec)
    advice = format_model_advice(rec)
    # Output: DIRECTIVE|ADVICE_LINE
    print(directive + '|' + advice)
except Exception as e:
    print('MODEL_ADVICE: sonnet|Model: sonnet (default, error: ' + str(e)[:60] + ')')
" 2>/dev/null || echo "MODEL_ADVICE: sonnet|Model: sonnet (default)")

MODEL_DIRECTIVE="${MODEL_ROUTING%%|*}"
MODEL_ADVICE_LINE="${MODEL_ROUTING##*|}"

# Check if the skill is DISABLED by the consequence engine
if [[ "$MODEL_DIRECTIVE" == MODEL_DISABLED:* ]]; then
    DISABLED_REASON="${MODEL_DIRECTIVE#MODEL_DISABLED: }"
    _log_event "disabled"
    cat >&2 <<EOF
DISPATCH GATE: Agent launch BLOCKED — skill is DISABLED.
  Reason: ${DISABLED_REASON}
  Run /optimize-skill to rewrite and re-enable.
EOF
    exit 2
fi

echo "DISPATCH GATE: Slot ${NEXT}/${MAX_AGENTS} allocated." >&2
# Output the model directive on a separate line for easy parsing by the orchestrator
if [[ -n "$MODEL_DIRECTIVE" ]]; then
    echo "$MODEL_DIRECTIVE" >&2
fi
echo "  ${MODEL_ADVICE_LINE}" >&2
_log_event "allow"
exit 0
