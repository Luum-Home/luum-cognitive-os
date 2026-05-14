#!/usr/bin/env bash
# SCOPE: os-only
# Token Budget Monitor — PreToolUse hook on Agent
#
# Monitors API token consumption before every agent launch.
# - >95%: BLOCK (exit 2) with resume instructions
# - >80%: WARN with status
# - >50%: INFO (silent, logged only)
#
# Renamed from rate-limit-protection.sh (which monitored token budget, not action rate).
# For action-count rate limiting see lib/rate_limiter.py.
# Override: RATE_LIMIT_OVERRIDE=true
# Author: luum

set -euo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"
source "$(dirname "${BASH_SOURCE[0]}")/_lib/portable.sh"

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
CUTOFF_EPOCH=$(python3 -c "import time; print(int(time.time()) - 3600)")

if [[ -f "$COST_EVENTS" ]]; then
    read -r TOKENS_USED AGENTS_USED < <(python3 - "$COST_EVENTS" "$CUTOFF_EPOCH" <<'PYEOF'
import sys
from datetime import datetime, timezone

filepath, cutoff_str = sys.argv[1], sys.argv[2]
cutoff = int(cutoff_str)
tokens_used = 0
agents_used = 0

try:
    import json
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            try:
                t = datetime.fromisoformat(e.get('timestamp', ''))
                if t.tzinfo is None:
                    t = t.replace(tzinfo=timezone.utc)
                ts = int(t.timestamp())
            except Exception:
                ts = 0
            if ts >= cutoff:
                tok = e.get('total_tokens', 0) or (e.get('input_tokens', 0) + e.get('output_tokens', 0))
                tokens_used += tok or 0
                if e.get('action') == 'agent_launch':
                    agents_used += 1
except Exception:
    pass

print(tokens_used, agents_used)
PYEOF
    ) 2>/dev/null || true
    TOKENS_USED="${TOKENS_USED:-0}"
    AGENTS_USED="${AGENTS_USED:-0}"
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
