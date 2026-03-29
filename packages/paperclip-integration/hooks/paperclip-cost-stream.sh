#!/usr/bin/env bash
# paperclip-cost-stream.sh — Stream cost events to Paperclip in real-time
# Trigger: PostToolUse on Agent
#
# After agent completion, reads cost-events.jsonl and pushes cumulative cost
# to Paperclip spend tracker when the delta since last push exceeds $0.10.
# Fire-and-forget — never blocks agent execution.

_HOOK_NAME="paperclip-cost-stream"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
set -uo pipefail

# Only run on Agent completions
INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // ""' 2>/dev/null)
[ "$TOOL_NAME" != "Agent" ] && exit 0

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
PAPERCLIP_URL="${COGNITIVE_OS_PAPERCLIP_URL:-http://localhost:3200}"
METRICS_DIR="$(_resolve_metrics_dir)"
COST_FILE="$METRICS_DIR/cost-events.jsonl"
LAST_PUSH_FILE="$METRICS_DIR/.paperclip-cost-last-push"

# No cost events? Skip.
[ -f "$COST_FILE" ] || exit 0
[ -s "$COST_FILE" ] || exit 0

# Threshold: only push when cumulative cost since last push exceeds $0.10
COST_THRESHOLD="0.10"

# Calculate cumulative cost
TOTAL_COST=$(jq -s '[.[].estimated_cost_usd // 0] | add // 0' "$COST_FILE" 2>/dev/null || echo 0)
TOTAL_TOKENS=$(jq -s '[.[] | ((.input_tokens // 0) + (.output_tokens // 0))] | add // 0' "$COST_FILE" 2>/dev/null || echo 0)
DOMINANT_MODEL=$(jq -s '[.[].model] | group_by(.) | sort_by(-length) | .[0][0] // "unknown"' "$COST_FILE" 2>/dev/null || echo "unknown")

# Read last pushed amount
LAST_PUSHED=0
[ -f "$LAST_PUSH_FILE" ] && LAST_PUSHED=$(cat "$LAST_PUSH_FILE" 2>/dev/null || echo 0)

# Calculate delta
DELTA=$(echo "$TOTAL_COST - $LAST_PUSHED" | bc 2>/dev/null || python3 -c "print(float('$TOTAL_COST') - float('$LAST_PUSHED'))" 2>/dev/null || echo 0)

# Check if delta exceeds threshold
SHOULD_PUSH=$(python3 -c "print('yes' if float('$DELTA') >= float('$COST_THRESHOLD') else 'no')" 2>/dev/null || echo "no")

[ "$SHOULD_PUSH" != "yes" ] && exit 0

# Fire-and-forget: push in background
(
  python3 -c "
import sys, os
sys.path.insert(0, '$PROJECT_DIR/lib')
os.environ.setdefault('COGNITIVE_OS_PAPERCLIP_URL', '$PAPERCLIP_URL')

try:
    from paperclip_client import PaperclipClient
    client = PaperclipClient()
    if not client.is_available():
        sys.exit(0)

    cost = float('$TOTAL_COST')
    tokens = int(float('$TOTAL_TOKENS'))
    model = $DOMINANT_MODEL if isinstance($DOMINANT_MODEL, str) else 'unknown'

    client.push_spend(cost, model, tokens)

    # Record last pushed amount
    with open('$LAST_PUSH_FILE', 'w') as f:
        f.write(str(cost))

except Exception:
    pass  # Fire-and-forget
" 2>/dev/null
) &

exit 0
