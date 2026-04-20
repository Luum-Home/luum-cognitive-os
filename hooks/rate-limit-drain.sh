#!/usr/bin/env bash
# SCOPE: project
# CONCERNS: rate-limiting, retry, queue-drain, non-blocking
# Rate Limit Drainer (D45 wiring) — PostToolUse:Bash, NEVER blocks.
#
# Closes the loop on the rate-limiter compounding-retry protection:
#   - lib/rate_limiter.py already enforces MAX_RETRY_COUNT, exponential
#     backoff, circuit breaker, and corruption recovery.
#
# This drainer:
#   1. Calls RateLimitQueue.dequeue_ready() after every Bash completes.
#   2. For each ready item: re-checks RateLimiter.check(action_type).
#        - If allowed now AND it's a safe bash_command: drainer-as-executor (gap A)
#          runs the command directly via subprocess.run(), writes audit to
#          rate-limit-executed.jsonl.
#        - If allowed but not safe/bash: emits RATE_LIMIT_READY to stderr.
#        - If still blocked: re-enqueues with retry_count = item.retry_count+1.
#          Library auto-drops items above MAX_RETRY_COUNT.
#   3. Always exit 0. Blocking PostToolUse would deadlock the original Bash.
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

# Write the Python drainer logic to a temp file to avoid heredoc + shell
# variable expansion issues (especially with regex chars in the script).
# mktemp syntax varies: BSD/macOS needs XXXXXX as suffix; -t flag for tmpdir.
_DRAIN_SCRIPT=$(mktemp /tmp/rate-limit-drainXXXXXX 2>/dev/null \
  || mktemp -t rate-limit-drain 2>/dev/null \
  || echo "/tmp/rate-limit-drain-$$.py")
trap 'rm -f "$_DRAIN_SCRIPT"' EXIT

cat > "$_DRAIN_SCRIPT" << 'PYEOF'
import json
import os
import re
import shlex
import subprocess
import sys
import time

PROJECT_DIR = os.environ.get("_DRAIN_PROJECT_DIR", ".")
PHASE = os.environ.get("_DRAIN_PHASE", "stabilization")
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

# ---------------------------------------------------------------------------
# Allowlist for safe subprocess execution (gap A safety guard).
# Only bash_command items matching a known-safe pattern are executed directly.
# Everything else falls back to the READY message for the orchestrator.
# ---------------------------------------------------------------------------

_SAFE_CMD_PATTERNS = (
    re.compile(r'^(echo|printf|cat|ls|grep|find|head|tail|wc|jq|python3?)\b'),
    re.compile(r'^bash\s+scripts/'),
    re.compile(r'^bash\s+hooks/'),
    re.compile(r'^pytest\b'),
    re.compile(r'^python3?\s+-m\s+pytest\b'),
    re.compile(r'^python3?\s+-c\b'),
)
_BLOCKED_CMD_PATTERNS = (
    re.compile(r'\brm\b.*-[rf]'),
    re.compile(r'\bgit\s+(push|reset|clean|checkout)\b'),
    re.compile(r'\beval\b'),
    re.compile(r'\bsource\b'),
    re.compile(r'[;&|`].*[;&|`]'),
    re.compile(r'>\s*/'),
    re.compile(r'dd\b.*of='),
)


def safe_to_execute(cmd):
    """Return True iff cmd is safe for subprocess execution."""
    if not cmd or len(cmd) > 2048:
        return False
    stripped = cmd.strip()
    for blocked in _BLOCKED_CMD_PATTERNS:
        if blocked.search(stripped):
            return False
    for allowed in _SAFE_CMD_PATTERNS:
        if allowed.match(stripped):
            return True
    return False


state_dir = os.path.join(PROJECT_DIR, ".cognitive-os")
rl = RateLimiter(
    state_path=os.path.join(state_dir, "rate-limit-state.json"),
    phase=PHASE,
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
executed = 0
metrics_path = os.path.join(state_dir, "metrics", "rate-limit-drain.jsonl")
executed_path = os.path.join(state_dir, "rate-limit-executed.jsonl")
os.makedirs(os.path.dirname(metrics_path), exist_ok=True)

with open(metrics_path, "a") as mf:
    for item in ready:
        action = item.get("action_type", "tool_call")
        retry_count = int(item.get("retry_count", 0))
        ctx = item.get("context", {}) or {}
        allowed, reason = rl.check(action)

        if allowed:
            # Gap A: attempt direct execution for safe bash_command items
            cmd_text = ctx.get("command", "")
            if action == "bash_command" and cmd_text and safe_to_execute(cmd_text):
                t0 = time.monotonic()
                try:
                    result = subprocess.run(
                        shlex.split(cmd_text),
                        capture_output=True,
                        text=True,
                        timeout=30,
                        cwd=PROJECT_DIR,
                        shell=False,
                    )
                    elapsed_ms = int((time.monotonic() - t0) * 1000)
                    executed += 1
                    audit_record = {
                        "ts": time.time(),
                        "command": cmd_text,
                        "retry_count": retry_count,
                        "exit_code": result.returncode,
                        "elapsed_ms": elapsed_ms,
                        "queue_id": item.get("queue_id"),
                        "stdout_snippet": result.stdout[:500],
                        "stderr_snippet": result.stderr[:200],
                    }
                    with open(executed_path, "a") as ef:
                        ef.write(json.dumps(audit_record) + "\n")
                    mf.write(json.dumps({
                        "ts": time.time(),
                        "event": "executed",
                        "action": action,
                        "retry_count": retry_count,
                        "exit_code": result.returncode,
                        "elapsed_ms": elapsed_ms,
                        "queue_id": item.get("queue_id"),
                    }) + "\n")
                except (subprocess.TimeoutExpired, OSError, ValueError) as exc:
                    ready_now.append((item, action))
                    mf.write(json.dumps({
                        "ts": time.time(),
                        "event": "exec_error",
                        "action": action,
                        "retry_count": retry_count,
                        "error": str(exc)[:200],
                        "queue_id": item.get("queue_id"),
                    }) + "\n")
            else:
                # Non-bash or unsafe command: emit READY for orchestrator
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

if executed > 0:
    sys.stderr.write(
        f"RATE_LIMIT_EXECUTED: {executed} bash_command(s) re-executed by drainer "
        f"(see .cognitive-os/rate-limit-executed.jsonl)\n"
    )

if dropped > 0:
    sys.stderr.write(
        f"RATE_LIMIT_DROPPED: {dropped} item(s) exceeded MAX_RETRY_COUNT="
        f"{MAX_RETRY_COUNT}; see .cognitive-os/rate-limit-dropped.jsonl\n"
    )
PYEOF

# Pass variables via environment to the Python script (avoids shell injection).
export _DRAIN_PROJECT_DIR="$_PROJECT_DIR"
export _DRAIN_PHASE="$PHASE"

python3 "$_DRAIN_SCRIPT" 2>/dev/null || true

# Always succeed — never block the original Bash completion path.
exit 0
