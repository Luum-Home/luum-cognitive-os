#!/usr/bin/env bash
# CONCERNS: security, rate-limiting, resource-protection
# Rate Limiter — prevents token flooding and excessive tool usage.
# PreToolUse hook on Bash, Agent, Edit, Write.
# Blocks (exit 2) when rate limits are exceeded.
# Phase-aware: reads project phase from cognitive-os.yaml and applies modifier.
# On BLOCK: enqueues the action for automatic retry and outputs a structured
# message so the orchestrator can poll RateLimitQueue.dequeue_ready().
set -uo pipefail

source "$(dirname "$0")/_lib/common.sh"

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

# Check rate limit via Python (passing phase for modifier calculation)
RESULT=$(python3 -c "
import sys, os
sys.path.insert(0, '$_PROJECT_DIR')
os.environ.setdefault('CLAUDE_PROJECT_DIR', '$_PROJECT_DIR')
from lib.rate_limiter import RateLimiter, RateLimitQueue

rl = RateLimiter(
    state_path='$_PROJECT_DIR/.cognitive-os/rate-limit-state.json',
    phase='$PHASE',
)
allowed, reason = rl.check('$ACTION')

if not allowed:
    # Enqueue the blocked action for automatic retry
    queue = RateLimitQueue(
        state_path='$_PROJECT_DIR/.cognitive-os/rate-limit-queue.json',
        cooldown_seconds=rl.config.cooldown_seconds,
    )
    queue_id = queue.enqueue('$ACTION', {
        'description': '$TOOL_NAME action',
        'blocked_reason': reason,
    })
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
    rl.record('$ACTION')
    print('OK')
" 2>/dev/null || echo "OK")

if [[ "$RESULT" == *"BLOCKED"* ]]; then
    echo "RATE LIMIT:" >&2
    echo "$RESULT" >&2
    echo "" >&2
    # Show detailed limit status with queue info
    python3 -c "
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
