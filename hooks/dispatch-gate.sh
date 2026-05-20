#!/usr/bin/env bash
# SCOPE: os-only
# CONCERNS: concurrency, resource-protection, workload-scheduling
# Dispatch Gate — controls agent launch concurrency.
# PreToolUse hook on Agent.
# Blocks (exit 2) when max_parallel_agents slots are all in use.
# Must run BEFORE rate-limiter.sh and agent-prelaunch.sh.
set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

source "$(dirname "$0")/_lib/common.sh"

# Only fires on Agent launches
require_tool "Agent" "task" "delegate"

# Skip in private mode
check_private_mode
# Runtime disable: DISABLE_HOOK_DISPATCH_GATE=true skips this hook for the session
check_disabled_env "dispatch-gate"

# ─── Read stdin once ──────────────────────────────────────────────────────────

read_stdin_json


_enqueue_blocked_agent() {
    local block_reason="$1"
    local detail_line="$2"
    local queue_result
    queue_result=$(PYTHONPATH="$_PROJECT_DIR${PYTHONPATH:+:$PYTHONPATH}" COGNITIVE_OS_PROJECT_DIR="$_PROJECT_DIR" COS_DISPATCH_STDIN="${COS_DISPATCH_STDIN:-{}}" python3 - <<'PYQUEUE' 2>/dev/null
import json, os, re
try:
    from lib.queue_drainer import QueueDrainer
    stdin_raw = os.environ.get("COS_DISPATCH_STDIN", "{}")
    try:
        d = json.loads(stdin_raw) if stdin_raw.strip() else {}
    except Exception:
        d = {}
    tool_input = d.get("tool_input", {}) if isinstance(d, dict) else {}
    if not isinstance(tool_input, dict):
        tool_input = {}
    prompt = tool_input.get("prompt", "") or tool_input.get("description", "") or tool_input.get("task", "")
    prompt = str(prompt).strip()
    if not prompt:
        raise ValueError("missing Agent prompt/description/task; refusing to enqueue unrelaunchable Agent launch")
    description = (prompt[:100]) if prompt else "agent task"
    model_match = re.search(r"model[\":\s]+([a-z]+)", prompt[:200].lower())
    model = model_match.group(1) if model_match else "sonnet"
    if model not in ("opus", "sonnet", "haiku"):
        model = "sonnet"
    queue_path = os.path.join(os.environ["COGNITIVE_OS_PROJECT_DIR"], ".cognitive-os", "tasks", "dispatch-queue.json")
    tasks_path = os.path.join(os.environ["COGNITIVE_OS_PROJECT_DIR"], ".cognitive-os", "tasks", "active-tasks.json")
    drainer = QueueDrainer(queue_path=queue_path, tasks_path=tasks_path)
    agent_id = drainer.enqueue(prompt=prompt, description=description, model=model, priority=5)
    pos = drainer.position_in_queue(agent_id)
    total = drainer.queue_length(status="queued")
    print(f"{agent_id}:{pos}:{total}")
except Exception as e:
    print(f"error:{e}")
PYQUEUE
) || queue_result="error:python-failed"
    if [[ "$queue_result" == error:* ]]; then
        cat >&2 <<EOF
DISPATCH GATE: Agent launch blocked — ${block_reason}.
  ${detail_line}
  Could not enqueue: ${queue_result#error:}
  Agent will not be retried automatically.
EOF
    else
        local queue_id rest queue_pos queue_total
        queue_id="${queue_result%%:*}"
        rest="${queue_result#*:}"
        queue_pos="${rest%%:*}"
        queue_total="${rest##*:}"
        cat >&2 <<EOF
DISPATCH GATE: Agent launch blocked — ${block_reason}.
  ${detail_line}
  Agent enqueued — position ${queue_pos} of ${queue_total} in dispatch queue.
  Queue ID: ${queue_id}
  Will launch when the gate clears; drain with QueueDrainer.get_ready_agents().
EOF
    fi
}

# ─── Validation capsule: block new agents in the validating worktree ─────────
VALIDATION_LOCK_LIB="$(dirname "$0")/_lib/validation-lock.sh"
if [ -f "$VALIDATION_LOCK_LIB" ]; then
    # shellcheck source=/dev/null
    source "$VALIDATION_LOCK_LIB"
    if cos_validation_lock_active "$_PROJECT_DIR"; then
        _msg=$(cos_validation_lock_message "$_PROJECT_DIR" 2>/dev/null || echo "validation capsule active")
        COS_DISPATCH_STDIN="${_STDIN_JSON:-{}}" _enqueue_blocked_agent "validation capsule active" "${_msg}"
        exit 2
    fi
fi

# ─── Single Python pass: config + active tasks + skill + CE + CB + routing ───
# Replaces 7 sequential python3 cold starts with one.

GATE_JSON=$(echo "${_STDIN_JSON:-{}}" | python3 "$(dirname "$0")/_lib/dispatch_gate_check.py" 2>/dev/null \
    || echo '{"max_agents":5,"active":0,"skill_name":"","disabled":false,"model_override":"","cb_blocked":false,"cb_task_type":"","model_directive":"MODEL_ADVICE: sonnet","model_advice":"Model: sonnet (default)","log_desc":"","error":"python-failed"}')

MAX_AGENTS=$(echo "$GATE_JSON" | jq -r '.max_agents // 5')
ACTIVE=$(echo "$GATE_JSON"     | jq -r '.active // 0')
SKILL_NAME=$(echo "$GATE_JSON" | jq -r '.skill_name // ""')
DISABLED=$(echo "$GATE_JSON"   | jq -r '.disabled // false')
MODEL_OVERRIDE=$(echo "$GATE_JSON" | jq -r '.model_override // ""')
CB_BLOCKED=$(echo "$GATE_JSON" | jq -r '.cb_blocked // false')
CB_TASK_TYPE=$(echo "$GATE_JSON" | jq -r '.cb_task_type // ""')
MODEL_DIRECTIVE=$(echo "$GATE_JSON" | jq -r '.model_directive // "MODEL_ADVICE: sonnet"')
MODEL_ADVICE_LINE=$(echo "$GATE_JSON" | jq -r '.model_advice // "Model: sonnet (default)"')
LOG_DESC=$(echo "$GATE_JSON"   | jq -r '.log_desc // ""')

# ─── Log helper ───────────────────────────────────────────────────────────────

_log_event() {
    local action="$1"
    local metrics_dir="$_PROJECT_DIR/.cognitive-os/metrics"
    mkdir -p "$metrics_dir" 2>/dev/null || true
    local ts
    ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || echo "unknown")
    printf '{"timestamp":"%s","active":%s,"max":%s,"action":"%s","description":"%s"}\n' \
        "$ts" "$ACTIVE" "$MAX_AGENTS" "$action" "$LOG_DESC" \
        >> "$metrics_dir/dispatch-gate.jsonl" 2>/dev/null || true
}

# ─── Consequence Engine: DISABLE check ───────────────────────────────────────

if [ -n "$SKILL_NAME" ]; then
    if [ "$DISABLED" = "true" ]; then
        _log_event "consequence_disabled"
        echo "DISPATCH GATE: Skill '$SKILL_NAME' is DISABLED by consequence engine." >&2
        echo "  Run /optimize-skill $SKILL_NAME to fix it, then re-enable via ConsequenceEngine.re_enable_skill()." >&2
        exit 2
    fi

    if [ -n "$MODEL_OVERRIDE" ]; then
        echo "DISPATCH GATE: Skill '$SKILL_NAME' is DEGRADED — use model '$MODEL_OVERRIDE' (one tier down)." >&2
        _log_event "consequence_degrade"
    fi
fi

# ─── Circuit breaker check ────────────────────────────────────────────────────

if [ "$CB_BLOCKED" = "true" ]; then
    _log_event "circuit_open"
    echo "DISPATCH GATE: Circuit breaker OPEN for '${CB_TASK_TYPE}' tasks. Cooldown in effect." >&2
    echo "  Too many consecutive failures for this task type. Wait for cooldown or run different task type." >&2
    exit 2
fi

# ─── Decision ─────────────────────────────────────────────────────────────────

if [ "$ACTIVE" -ge "$MAX_AGENTS" ] 2>/dev/null; then
    _log_event "block"

    COS_DISPATCH_STDIN="${_STDIN_JSON:-{}}" _enqueue_blocked_agent "${ACTIVE}/${MAX_AGENTS} slots in use" "Capacity gate is full."
    exit 2
fi

# Slots available — allow the launch
NEXT=$((ACTIVE + 1))

# ─── Check if the skill is DISABLED via model directive ───────────────────────

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
