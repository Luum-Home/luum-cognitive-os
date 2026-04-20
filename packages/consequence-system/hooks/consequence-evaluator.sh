#!/usr/bin/env bash
# SCOPE: both
# consequence-evaluator.sh — PostToolUse hook on Agent
# CONCERNS: quality, governance, okr
#
# After every agent completion:
# 1. Extract trust score from output
# 2. Record performance
# 3. Evaluate consequence
# 4. Apply if needed (promote/warn/degrade/disable)
# 5. Log result
set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

source "$(dirname "$0")/_lib/common.sh"

# Auto-disabled at capability level 5
check_capability_level "consequence-evaluator"

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // ""')
[ "$TOOL_NAME" != "Agent" ] && exit 0

RESPONSE=$(echo "$INPUT" | jq -r '.tool_response // ""')
[ -z "$RESPONSE" ] && exit 0

# Extract trust score if present (from Trust Report)
SCORE=$(echo "$RESPONSE" | grep -oE 'Score: [0-9]+' | head -1 | grep -oE '[0-9]+' || echo "")
[ -z "$SCORE" ] && exit 0

# Extract task/skill info from prompt
TASK_DESC=$(echo "$INPUT" | jq -r '.tool_input.prompt // ""' 2>/dev/null | head -c 200 || echo "unknown")
# Sanitise single quotes for safe Python embedding
TASK_SAFE=$(echo "$TASK_DESC" | head -c 50 | tr -d "'" | tr -d '"' | tr '\n' ' ')

# Determine success based on score
if [ "$SCORE" -ge 60 ] 2>/dev/null; then
    SUCCESS="True"
else
    SUCCESS="False"
fi

# Evaluate consequence via Python
python3 -c "
import sys
sys.path.insert(0, '.')
from lib.consequence_engine import ConsequenceEngine, PerformanceRecord
from datetime import datetime, timezone

engine = ConsequenceEngine()
record = PerformanceRecord(
    agent_or_skill='${TASK_SAFE}',
    task_type='general',
    trust_score=${SCORE},
    success=${SUCCESS},
    cost_usd=0.0,
    tokens_used=0,
    retries=0,
    timestamp=datetime.now(timezone.utc).isoformat()
)

action = engine.evaluate(record)
engine.save_action(action)

if action.consequence.value in ('warn', 'degrade', 'disable'):
    applied = engine.apply_consequence(action)
    for a in applied:
        print(f'CONSEQUENCE: {a}', flush=True)
elif action.consequence.value == 'promote':
    applied = engine.apply_consequence(action)
    for a in applied:
        print(f'PROMOTED: {a}', flush=True)
" 2>/dev/null || true

exit 0
