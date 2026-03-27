#!/usr/bin/env bash
# Rate Limit Protection — PreToolUse hook on Agent
#
# Before EVERY agent launch, check rate limit status.
# - >95%: BLOCK (exit 2) with resume instructions
# - >80%: WARN with status
# - >50%: INFO (silent, logged only)
#
# Override: RATE_LIMIT_OVERRIDE=true
# Author: luum

set -euo pipefail

# Skip if override is set
if [[ "${RATE_LIMIT_OVERRIDE:-false}" == "true" ]]; then
    exit 0
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
METRICS_DIR="${PROJECT_DIR}/.cognitive-os/metrics"
COST_EVENTS="${METRICS_DIR}/cost-events.jsonl"
RATE_LIMIT_LOG="${METRICS_DIR}/rate-limit-checks.jsonl"

mkdir -p "$METRICS_DIR"

# Count tokens used in the last hour from cost-events.jsonl
HOURLY_LIMIT="${RATE_LIMIT_HOURLY_TOKENS:-5000000}"
AGENTS_LIMIT="${RATE_LIMIT_MAX_AGENTS:-30}"

TOKENS_USED=0
AGENTS_USED=0
CUTOFF_EPOCH=$(date -v-1H +%s 2>/dev/null || date -d '1 hour ago' +%s 2>/dev/null || echo 0)

if [[ -f "$COST_EVENTS" ]]; then
    while IFS= read -r line; do
        [[ -z "$line" ]] && continue
        ts=$(echo "$line" | python3 -c "
import sys, json
from datetime import datetime, timezone
try:
    e = json.load(sys.stdin)
    t = datetime.fromisoformat(e.get('timestamp',''))
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    print(int(t.timestamp()))
except: print(0)
" 2>/dev/null || echo 0)
        if [[ "$ts" -ge "$CUTOFF_EPOCH" ]]; then
            tok=$(echo "$line" | python3 -c "
import sys, json
try:
    e = json.load(sys.stdin)
    print(e.get('total_tokens', 0) or (e.get('input_tokens',0) + e.get('output_tokens',0)))
except: print(0)
" 2>/dev/null || echo 0)
            TOKENS_USED=$((TOKENS_USED + tok))
            is_agent=$(echo "$line" | python3 -c "
import sys, json
try:
    e = json.load(sys.stdin)
    print(1 if e.get('action') == 'agent_launch' else 0)
except: print(0)
" 2>/dev/null || echo 0)
            AGENTS_USED=$((AGENTS_USED + is_agent))
        fi
    done < "$COST_EVENTS"
fi

# Calculate percentage
if [[ "$HOURLY_LIMIT" -gt 0 ]]; then
    PCT=$((TOKENS_USED * 100 / HOURLY_LIMIT))
else
    PCT=0
fi

# Log the check
echo "{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"tokens_used\":$TOKENS_USED,\"limit\":$HOURLY_LIMIT,\"pct\":$PCT,\"agents\":$AGENTS_USED}" >> "$RATE_LIMIT_LOG"

# Decision
if [[ "$PCT" -ge 95 ]]; then
    echo "RATE LIMIT REACHED (${PCT}%). Auto-pausing agent launches." >&2
    echo "Tokens: ${TOKENS_USED}/${HOURLY_LIMIT} | Agents: ${AGENTS_USED}/${AGENTS_LIMIT}" >&2
    echo "To force continue: set RATE_LIMIT_OVERRIDE=true" >&2
    exit 2
elif [[ "$AGENTS_USED" -ge "$AGENTS_LIMIT" ]]; then
    echo "RATE LIMIT: Agent launch limit reached (${AGENTS_USED}/${AGENTS_LIMIT} this hour)." >&2
    exit 2
elif [[ "$PCT" -ge 80 ]]; then
    echo "WARNING: ${PCT}% of hourly token limit used (${TOKENS_USED}/${HOURLY_LIMIT})." >&2
    echo "${AGENTS_USED} agents launched this hour. Consider pausing." >&2
    exit 0
fi

# <50% or 50-80%: silent pass
exit 0
