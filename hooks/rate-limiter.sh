#!/usr/bin/env bash
# SCOPE: both
# CONCERNS: security, rate-limiting, resource-protection
# Rate Limiter — prevents token flooding and excessive tool usage.
# PreToolUse hook on Bash, Agent, Edit, Write.
# Blocks (exit 2) when rate limits are exceeded.
# Phase-aware: reads project phase from cognitive-os.yaml and applies modifier.
# On BLOCK: enqueues the action for automatic retry and outputs a structured
# message so the orchestrator can poll RateLimitQueue.dequeue_ready().
#
# ───────────────────────────────────────────────────────────────────────────
# RATE-LIMITER FLOW (D45 — full end-to-end retry_count wiring)
# ───────────────────────────────────────────────────────────────────────────
#
#   Fresh user Bash → rate-limiter.sh (PreToolUse:Bash)
#     ├─ allowed: record + exit 0 (command runs)
#     └─ blocked: queue.enqueue(action, retry_count=$RATE_LIMIT_RETRY_COUNT)
#                 exit 2 (command blocked; orchestrator notified via stderr)
#
#   After every Bash → rate-limit-drain.sh (PostToolUse:Bash, NON-BLOCKING)
#     ├─ queue.dequeue_ready() returns items whose cooldown elapsed
#     ├─ for each item: re-check rl.check(action_type)
#     │   ├─ allowed now: emit RATE_LIMIT_READY message (orchestrator re-runs)
#     │   └─ still blocked: queue.enqueue(action, retry_count=item.retry_count+1)
#     │                     ↑ library drops if retry_count > MAX_RETRY_COUNT
#     └─ never exits non-zero (would deadlock the original Bash)
#
# Environment hand-off (when orchestrator re-runs a previously-queued action):
#   RATE_LIMIT_RETRY_COUNT — int, the retry_count of the dequeued item; the
#                            PreToolUse hook passes this to enqueue() so
#                            re-blocks are counted against the cap.
# ───────────────────────────────────────────────────────────────────────────
set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

source "$(dirname "$0")/_lib/common.sh"
# Runtime disable: DISABLE_HOOK_RATE_LIMITER=true skips this hook for the session.
check_disabled_env "rate-limiter"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COGNITIVE_OS_HOOK_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
if [ -z "${PYTHON_BIN:-}" ]; then
    if [ -n "${PYTHON:-}" ]; then
        PYTHON_BIN="$PYTHON"
    elif [ -x "$COGNITIVE_OS_HOOK_ROOT/.venv/bin/python" ]; then
        PYTHON_BIN="$COGNITIVE_OS_HOOK_ROOT/.venv/bin/python"
    else
        PYTHON_BIN="python3"
    fi
fi

# Skip in private mode
check_private_mode

# Read tool name from stdin
read_stdin_json
TOOL_NAME=$(echo "$_STDIN_JSON" | jq -r '.tool_name // ""' 2>/dev/null)

# Map tool to action type
case "$TOOL_NAME" in
    Agent|task|delegate) ACTION="agent_launch" ;;
    Bash)               ACTION="bash_command" ;;
    Write)              ACTION="file_write" ;;
    Edit)               ACTION="file_write" ;;
    *)                  ACTION="tool_call" ;;
esac

# Read project phase for phase-aware rate limiting
PHASE=$(get_phase "stabilization")

# D45: when this PreToolUse fires for a re-injected (previously-queued) action,
# the orchestrator/drainer is expected to set RATE_LIMIT_RETRY_COUNT to the
# retry_count of the dequeued item. Fresh user bash leaves it unset (=> 0).
RETRY_COUNT="${RATE_LIMIT_RETRY_COUNT:-0}"
# Defensive: must be a non-negative integer
case "$RETRY_COUNT" in
    ''|*[!0-9]*) RETRY_COUNT=0 ;;
esac

BLOCKED_COMMAND=""
BLOCKED_COMMAND_HASH=""
if [ "$ACTION" = "bash_command" ]; then
    BLOCKED_COMMAND=$(echo "$_STDIN_JSON" | jq -r '.tool_input.command // ""' 2>/dev/null)
    if [ -n "$BLOCKED_COMMAND" ]; then
        if command -v sha256sum >/dev/null 2>&1; then
            BLOCKED_COMMAND_HASH=$(printf '%s' "$BLOCKED_COMMAND" | sha256sum | cut -c1-16)
        else
            BLOCKED_COMMAND_HASH=$(printf '%s' "$BLOCKED_COMMAND" | shasum -a 256 | cut -c1-16)
        fi
    fi
fi
export COGNITIVE_OS_HOOK_ROOT
if [ -n "${COS_RATE_LIMIT_PRIORITY_LANE:-}" ]; then
    PRIORITY_LANE="$COS_RATE_LIMIT_PRIORITY_LANE"
elif [ "$RETRY_COUNT" != "0" ]; then
    PRIORITY_LANE="orchestrator"
else
    PRIORITY_LANE="operator"
fi

export RATE_LIMIT_BLOCKED_COMMAND="$BLOCKED_COMMAND"
export RATE_LIMIT_BLOCKED_COMMAND_HASH="$BLOCKED_COMMAND_HASH"
export RATE_LIMIT_PRIORITY_LANE="$PRIORITY_LANE"

# Check rate limit via Python (passing phase for modifier calculation)
RESULT=$("$PYTHON_BIN" -c "
import sys, os
sys.path.insert(0, os.environ['COGNITIVE_OS_HOOK_ROOT'])
os.environ.setdefault('CLAUDE_PROJECT_DIR', '$_PROJECT_DIR')
from lib.rate_limiter import RateLimiter, RateLimitQueue

rl = RateLimiter(
    state_path='$_PROJECT_DIR/.cognitive-os/rate-limit-state.json',
    phase='$PHASE',
)
allowed, reason = rl.check('$ACTION', priority_lane=os.environ.get('RATE_LIMIT_PRIORITY_LANE', 'normal'), signature=os.environ.get('RATE_LIMIT_BLOCKED_COMMAND_HASH') or None)

if not allowed:
    context = {
        'description': '$TOOL_NAME action',
        'blocked_reason': reason,
    }
    blocked_command = os.environ.get('RATE_LIMIT_BLOCKED_COMMAND', '')
    blocked_command_hash = os.environ.get('RATE_LIMIT_BLOCKED_COMMAND_HASH', '')
    if blocked_command:
        context['command'] = blocked_command
    if blocked_command_hash:
        context['command_hash'] = blocked_command_hash
    # Enqueue the blocked action for automatic retry.
    # D45: pass retry_count from the env hand-off so re-blocks are counted
    # against MAX_RETRY_COUNT. Fresh user bash → retry_count=0.
    queue = RateLimitQueue(
        state_path='$_PROJECT_DIR/.cognitive-os/rate-limit-queue.json',
        cooldown_seconds=rl.config.cooldown_seconds,
    )
    queue_id = queue.enqueue('$ACTION', context, retry_count=$RETRY_COUNT)
    queued_items = queue.peek()
    queued_count = len(queued_items)
    cooldown = rl.config.cooldown_seconds

    # Structured output for orchestrator
    print(f'RATE_LIMIT_QUEUED: $ACTION queued for retry in {cooldown}s.')
    print(f'Queue ID: {queue_id}')
    print(f'Queue position: {queued_count}')
    print(f'Queued items: {queued_count}')

    # Batch reduction suggestion
    suggestion = rl.suggest_reduction(queued_count)
    if suggestion:
        for line in suggestion.split(chr(10)):
            print(f'Suggestion: {line}')

    print(f'ORCHESTRATOR ACTION: Check queue with RateLimitQueue.dequeue_ready() after {cooldown}s')
    print(f'BLOCKED: {reason}')
else:
    rl.record('$ACTION', signature=os.environ.get('RATE_LIMIT_BLOCKED_COMMAND_HASH') or None)
    warnings = rl.warnings()
    for warning in warnings:
        print(f'RATE_LIMIT_WARNING: {warning}')
    print('OK')
" 2>/dev/null || echo "OK")

if [[ "$RESULT" == *"RATE_LIMIT_WARNING:"* ]]; then
    echo "$RESULT" | grep "^RATE_LIMIT_WARNING:" >&2 || true
fi

if [[ "$RESULT" == *"BLOCKED"* ]]; then
    # Preserve machine-parseable lines for orchestrator polling
    echo "$RESULT" >&2

    # Extract human-readable fields for actionable error block
    QUEUE_ID=$(echo "$RESULT" | grep -m1 "^Queue ID:" | cut -d' ' -f3-)
    QUEUE_DEPTH=$(echo "$RESULT" | grep -m1 "^Queued items:" | awk '{print $3}')
    COOLDOWN=$(echo "$RESULT" | grep -m1 "queued for retry in" | sed 's/.*retry in \([0-9]*\)s.*/\1/')
    BLOCKED_REASON=$(echo "$RESULT" | grep -m1 "^BLOCKED:" | sed 's/^BLOCKED: //')

    # Actionable UX block (UX2 improvement: "RATE LIMIT: bash_command limit exceeded" with no
    # context → labeled human-readable block with Action: line, ETA, queue cancel instructions)
    echo "" >&2
    echo "⚠️  Rate limit reached for $ACTION" >&2
    echo "    Reason:      ${BLOCKED_REASON:-unknown}" >&2
    echo "    Phase:       $PHASE" >&2
    [ -n "$COOLDOWN" ] && echo "    Next slot:   in ~${COOLDOWN}s" >&2
    [ -n "$QUEUE_DEPTH" ] && echo "    Queue:       ${QUEUE_DEPTH} commands pending${QUEUE_ID:+ (ID: $QUEUE_ID)}" >&2
    echo "    Action:      your command will retry automatically; cancel with Ctrl-C" >&2
    echo "    Diagnose:    run 'cos status' to see rate state anytime" >&2
    echo "" >&2

    # Show detailed limit status with queue info (kept for power users)
    "$PYTHON_BIN" -c "
import sys, os
sys.path.insert(0, '$_PROJECT_DIR')
os.environ.setdefault('CLAUDE_PROJECT_DIR', '$_PROJECT_DIR')
from lib.rate_limiter import RateLimiter, RateLimitQueue
rl = RateLimiter(
    state_path='$_PROJECT_DIR/.cognitive-os/rate-limit-state.json',
    phase='$PHASE',
)
queue = RateLimitQueue(
    state_path='$_PROJECT_DIR/.cognitive-os/rate-limit-queue.json',
)
print(rl.format_limit_status(queue=queue))
" 2>/dev/null >&2
    exit 2  # BLOCK
fi

exit 0
