#!/usr/bin/env bash
# SCOPE: project
# CONCERNS: rate-limiting, retry, queue-drain, non-blocking
# Rate Limit Drainer (D45 wiring) — PostToolUse:Bash, NEVER blocks.
#
# Closes the loop on the rate-limiter compounding-retry protection:
#   - lib/rate_limiter.py already enforces MAX_RETRY_COUNT, exponential
#     backoff, circuit breaker, and corruption recovery — but only IF
#     callers pass retry_count > 0 on re-enqueue.
#   - hooks/rate-limiter.sh (PreToolUse) was always passing retry_count=0
#     because nothing was incrementing it on the hook path.
#
# This drainer fixes that by:
#   1. Calling RateLimitQueue.dequeue_ready() after every Bash completes.
#   2. For each ready item: re-checking RateLimiter.check(action_type).
#        - If allowed now: emits RATE_LIMIT_READY message to stderr so the
#          orchestrator knows it can re-run the action (it sets
#          RATE_LIMIT_RETRY_COUNT=item.retry_count when re-launching).
#        - If still blocked: re-enqueues with retry_count = item.retry_count+1.
#          The library auto-drops items above MAX_RETRY_COUNT and writes
#          rate-limit-dropped.jsonl with the reason.
#   3. Always exit 0. Blocking the PostToolUse would deadlock the original
#      Bash command's completion path.
set -uo pipefail

# Respect killswitch
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"
source "$(dirname "$0")/_lib/common.sh"

check_private_mode

# Only act on Bash completions — other tools have their own flow
read_stdin_json
TOOL_NAME=$(echo "$_STDIN_JSON" | jq -r '.tool_name // ""' 2>/dev/null)
[ "$TOOL_NAME" = "Bash" ] || exit 0

PHASE=$(get_phase "stabilization")

# Drain the queue. Bounded work — never loops forever.
# Output (to stderr) is informational only; no exit-2.
python3 - <<PYEOF 2>/dev/null || true
import json
import os
import sys
import time

PROJECT_DIR = "${_PROJECT_DIR}"
sys.path.insert(0, PROJECT_DIR)
os.environ.setdefault("CLAUDE_PROJECT_DIR", PROJECT_DIR)

try:
    from lib.rate_limiter import (
        MAX_RETRY_COUNT,
        RateLimiter,
        RateLimitQueue,
    )
except Exception:
    sys.exit(0)

state_dir = os.path.join(PROJECT_DIR, ".cognitive-os")
rl = RateLimiter(
    state_path=os.path.join(state_dir, "rate-limit-state.json"),
    phase="${PHASE}",
)
queue = RateLimitQueue(
    state_path=os.path.join(state_dir, "rate-limit-queue.json"),
    cooldown_seconds=rl.config.cooldown_seconds,
)

ready = queue.dequeue_ready()
if not ready:
    sys.exit(0)

ready_now = []
re_queued = 0
dropped = 0
metrics_path = os.path.join(state_dir, "metrics", "rate-limit-drain.jsonl")
os.makedirs(os.path.dirname(metrics_path), exist_ok=True)

with open(metrics_path, "a") as mf:
    for item in ready:
        action = item.get("action_type", "tool_call")
        retry_count = int(item.get("retry_count", 0))
        ctx = item.get("context", {}) or {}
        allowed, reason = rl.check(action)

        if allowed:
            ready_now.append((item, action))
            mf.write(json.dumps({
                "ts": time.time(),
                "event": "ready",
                "action": action,
                "retry_count": retry_count,
                "queue_id": item.get("queue_id"),
                "description": ctx.get("description", ""),
            }) + "\n")
        else:
            # Re-enqueue with retry_count+1. The library:
            #   - applies exponential backoff (cooldown * 2^retry_count)
            #   - drops items where retry_count > MAX_RETRY_COUNT and writes
            #     rate-limit-dropped.jsonl with reason=retry_cap_exceeded.
            new_retry = retry_count + 1
            new_id = queue.enqueue(
                action,
                {**ctx, "blocked_reason": reason},
                retry_count=new_retry,
            )
            if new_id:
                re_queued += 1
                mf.write(json.dumps({
                    "ts": time.time(),
                    "event": "re_enqueued",
                    "action": action,
                    "retry_count": new_retry,
                    "queue_id": new_id,
                    "reason": reason,
                }) + "\n")
            else:
                # enqueue() returned "" → item dropped (over retry cap)
                dropped += 1
                mf.write(json.dumps({
                    "ts": time.time(),
                    "event": "dropped",
                    "action": action,
                    "retry_count": new_retry,
                    "max_retry_count": MAX_RETRY_COUNT,
                    "reason": "retry_cap_exceeded",
                    "original_context": ctx,
                }) + "\n")

# Surface ready items so orchestrator can re-launch (informational, stderr).
if ready_now:
    sys.stderr.write("\n")
    sys.stderr.write(
        f"RATE_LIMIT_READY: {len(ready_now)} queued action(s) eligible to retry\n"
    )
    for item, action in ready_now[:5]:
        desc = (item.get("context", {}) or {}).get("description", "")
        sys.stderr.write(
            f"  - {action} (retry_count={item.get('retry_count', 0)}, "
            f"queue_id={item.get('queue_id')}): {desc[:80]}\n"
        )
    sys.stderr.write(
        "  Orchestrator: re-launch with RATE_LIMIT_RETRY_COUNT=<item.retry_count>\n"
    )
    sys.stderr.write("\n")

if dropped > 0:
    sys.stderr.write(
        f"RATE_LIMIT_DROPPED: {dropped} item(s) exceeded MAX_RETRY_COUNT="
        f"{MAX_RETRY_COUNT}; see .cognitive-os/rate-limit-dropped.jsonl\n"
    )

PYEOF

# Always succeed — never block the original Bash completion path.
exit 0
