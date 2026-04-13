#!/usr/bin/env bash
# SCOPE: both
# Dequeue Notify — notifies orchestrator when agent slots free up after completion.
# Type: PostToolUse
# Matcher: Agent
#
# After an agent completes (freeing a slot), checks if the dispatch-gate metrics
# log has any recently blocked launches that could now proceed.
# Outputs a DISPATCH message to stderr so the orchestrator knows to retry queued tasks.
set -uo pipefail

source "$(dirname "$0")/_lib/common.sh"

# Only fires after Agent completions
require_tool "Agent" "task" "delegate"

# Skip in private mode
check_private_mode

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"

# ─── Read config ──────────────────────────────────────────────────────────────

MAX_AGENTS=$(python3 -c "
import yaml, os
cfg_path = os.path.join(os.environ.get('CLAUDE_PROJECT_DIR', '.'), 'cognitive-os.yaml')
try:
    with open(cfg_path) as f:
        cfg = yaml.safe_load(f) or {}
    print(cfg.get('resources', {}).get('compute', {}).get('max_parallel_agents', 5))
except Exception:
    print(5)
" 2>/dev/null || echo 5)

# ─── Count currently active agents ────────────────────────────────────────────

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

# ─── Check for recently blocked launches ──────────────────────────────────────

SLOTS_FREE=$(( MAX_AGENTS - ACTIVE ))

if [ "$SLOTS_FREE" -le 0 ] 2>/dev/null; then
    # No free slots — still at capacity, nothing to dequeue
    exit 0
fi

# Check dispatch-gate log for recent blocks (last 100 entries within last 10 minutes)
BLOCKED_INFO=$(python3 -c "
import json, os, time
metrics_path = os.path.join(
    os.environ.get('CLAUDE_PROJECT_DIR', '.'),
    '.cognitive-os/metrics/dispatch-gate.jsonl'
)
try:
    with open(metrics_path) as f:
        lines = f.readlines()
    # Look for recent blocked entries (last 10 minutes)
    cutoff = time.time() - 600
    blocked = []
    for line in lines[-100:]:
        try:
            entry = json.loads(line.strip())
            if entry.get('action') == 'block':
                desc = entry.get('description', '').strip()
                if desc:
                    blocked.append(desc)
        except Exception:
            pass
    if blocked:
        # Return the last blocked description as the next candidate
        print(f'{len(blocked)}:{blocked[-1]}')
    else:
        print('0:')
except FileNotFoundError:
    print('0:')
except Exception as e:
    print('0:')
" 2>/dev/null || echo "0:")

BLOCKED_COUNT=$(echo "$BLOCKED_INFO" | cut -d: -f1)
BLOCKED_DESC=$(echo "$BLOCKED_INFO" | cut -d: -f2-)

if [ "$BLOCKED_COUNT" -gt 0 ] 2>/dev/null && [ -n "$BLOCKED_DESC" ]; then
    echo "" >&2
    echo "DISPATCH: Slot freed (${ACTIVE}/${MAX_AGENTS} active). ${BLOCKED_COUNT} queued agent(s) ready to launch. Next: ${BLOCKED_DESC}" >&2
    echo "" >&2

    # Log the notification
    METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
    mkdir -p "$METRICS_DIR" 2>/dev/null || true
    TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || echo "unknown")
    printf '{"timestamp":"%s","active":%s,"max":%s,"slots_free":%s,"queued":%s,"next":"%s"}\n' \
        "$TS" "$ACTIVE" "$MAX_AGENTS" "$SLOTS_FREE" "$BLOCKED_COUNT" \
        "$(echo "$BLOCKED_DESC" | head -c 100 | tr '"' "'")" \
        >> "$METRICS_DIR/dequeue-notify.jsonl" 2>/dev/null || true
fi

exit 0
